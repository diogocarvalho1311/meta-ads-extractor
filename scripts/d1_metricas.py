"""Compatibilidade dos coletores legados com tabelas D1 nativas.

Somente as duas bases de metricas usam D1; planilhas de produtos/precos continuam
no Google. Datas internas ISO com ano. Nenhum fallback silencioso para Sheets.
"""
import json
import os
import re
from datetime import date,timedelta
from pathlib import Path
from cloudflare_rest import Cloudflare
ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/'cloudflare/schema.json').read_text(encoding='utf-8'))
EPOCH=date(1899,12,30)

def d1_enabled(env=None):
    if env is not None: return os.environ.get('METRICAS_BACKEND',env.get('METRICAS_BACKEND','sheets')).lower()=='d1'
    value=os.environ.get('METRICAS_BACKEND')
    if value is None:
        text=(ROOT/'.env').read_text(encoding='utf-8-sig')
        match=re.search(r'^METRICAS_BACKEND\s*=\s*[\"\']?([a-zA-Z0-9_]+)',text,re.M)
        value=match[1] if match else 'sheets'
    return value.lower()=='d1'

def iso_date(value):
    if isinstance(value,(int,float)): return (EPOCH+timedelta(days=int(value))).isoformat()
    for pattern in ('%Y-%m-%d','%d/%m/%Y'):
        from datetime import datetime
        try: return datetime.strptime(str(value),pattern).date().isoformat()
        except ValueError: pass
    raise ValueError(f'Data invalida: {value!r}; use AAAA-MM-DD ou DD/MM/AAAA.')

def letter(index):
    result='';index+=1
    while index: index,rem=divmod(index-1,26);result=chr(65+rem)+result
    return result

def column(text):
    value=0
    for c in text: value=value*26+ord(c)-64
    return value-1

def parse_range(value):
    tab,cells=value.rsplit('!',1);tab=tab.strip("'").replace("''", "'")
    match=re.fullmatch(r'([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?',cells)
    if not match: raise ValueError('Faixa A1 nao suportada: '+cells)
    a,r,b,end=match.groups()
    return tab,column(a),int(r)-1,column(b or a)+1,int(end or r)

def record_from_row(spec,row,raw=False):
    record={}
    for i,field in enumerate(spec['fields']):
        if field in spec['generated']: continue
        value=row[i] if i<len(row) else None
        if value in ('',None): value=None
        elif field=='data': value=iso_date(value)
        elif field in spec['text']: value=str(value)
        elif field=='destino_link': value=int(str(value).upper() in ('SIM','TRUE','1'))
        elif isinstance(value,str) and value.startswith('='): raise ValueError('Formula inesperada em '+field)
        else:
            if isinstance(value,bool): value=int(value)
            if not isinstance(value,(int,float)):
                try: value=float(str(value).replace('R$','').replace('%','').replace('.','').replace(',','.').strip())
                except ValueError: raise ValueError('Numero invalido na coluna '+field) from None
            if field in spec['percent']: value=value*100
        record[field]=value
    if any(record.get(k) in (None,'') for k in spec['keys']): raise ValueError('Linha sem chave em '+spec['table'])
    return record

def upsert_statement(spec,record,preserve_crm=False):
    record=dict(record)
    if preserve_crm:
        for field in ('leads_qualificados','leads_fechados','nome_exibicao'):
            if not record.get(field): record.pop(field,None)
    fields=list(record)
    updates=[f'"{f}"=COALESCE(excluded."{f}","{f}")' for f in fields if f not in spec['keys']]
    updates.append("atualizacao=datetime('now')")
    sql=f'INSERT INTO {spec["table"]} ('+','.join('"'+f+'"' for f in fields)+') VALUES ('+','.join('?' for _ in fields)+') ON CONFLICT ('+','.join(spec['keys'])+') DO UPDATE SET '+','.join(updates)
    return {'sql':sql,'params':[record[f] for f in fields]}

class D1MetricsClient:
    is_d1=True
    def __init__(self,env,google_client):
        self.env=env;self.google=google_client;self.api=None;self.cache={}
        self.clients={env[k]:c for c,k in [('lucri','SHEETS_ID_LUCRI_METRICAS'),('cwbkids','SHEETS_ID_CWBKIDS_METRICAS')] if env.get(k)}
    def _client(self,sheet): return self.clients.get(sheet)
    def _db(self,sheet): return self.env['D1_DATABASE_ID_'+self.clients[sheet].upper()]
    def _api(self):
        if self.api is None:self.api=Cloudflare(self.env)
        return self.api
    def _spec(self,sheet,tab):
        try:return SCHEMA[self.clients[sheet]][tab]
        except KeyError:raise ValueError('Tabela de metricas nao mapeada: '+tab) from None
    def _rows(self,sheet,tab):
        key=(sheet,tab)
        if key not in self.cache:
            spec=self._spec(sheet,tab)
            self.cache[key]=self._api().query(self._db(sheet),f'SELECT * FROM {spec["table"]} ORDER BY '+','.join(['data']+[k for k in spec['keys'] if k!='data']))
        return self.cache[key]
    def get(self,sheet):
        if not self._client(sheet):return self.google.get(sheet)
        return {'sheets':[{'properties':{'title':tab,'sheetId':s['gid']}} for tab,s in SCHEMA[self.clients[sheet]].items()]}
    def get_tab_gid(self,sheet,tab):
        if not self._client(sheet):return self.google.get_tab_gid(sheet,tab)
        return self._spec(sheet,tab)['gid']
    def values_get(self,sheet,range_,value_render_option=None):
        if not self._client(sheet):return self.google.values_get(sheet,range_,value_render_option=value_render_option)
        tab,c0,r0,c1,r1=parse_range(range_);spec=self._spec(sheet,tab)
        rows=[spec['headers']]
        for record in self._rows(sheet,tab):
            row=[]
            for field in spec['fields']:
                value=record.get(field)
                if value is None:value=''
                elif field=='data':
                    d=date.fromisoformat(value)
                    value=(d-EPOCH).days if value_render_option=='UNFORMATTED_VALUE' else d.strftime('%d/%m/%Y')
                elif field=='destino_link':value='SIM' if value else 'NÃO'
                elif field in spec['percent']:value=value/100
                row.append(value)
            rows.append(row)
        values=[]
        for row in rows[r0:r1]:
            cells=row[c0:c1]
            while cells and cells[-1] in ('',None):cells.pop()
            values.append(cells)
        while values and not values[-1]:values.pop()
        return {'range':range_,'values':values}
    def upsert_records(self, sheet, tab, records):
        """Grava campos nativos por chave, sem depender da posicao das linhas."""
        spec = self._spec(sheet, tab)
        statements = []
        for record in records:
            if any(k not in record for k in spec['keys']):
                raise ValueError('Registro sem chave em ' + tab)
            if set(record) - set(spec['fields']):
                raise ValueError('Coluna desconhecida em ' + tab)
            values = {k: v for k, v in record.items() if k not in spec['generated']}
            if 'data' in values: values['data'] = iso_date(values['data'])
            statements.append(upsert_statement(spec, values))
        for i in range(0, len(statements), 250):
            self._api().batch(self._db(sheet), statements[i:i+250])
        self.cache.pop((sheet, tab), None)

    def update_records(self, sheet, tab, records):
        """Atualiza campos por chave; nao tenta inserir registros incompletos."""
        spec = self._spec(sheet, tab)
        statements = []
        for record in records:
            if any(k not in record for k in spec['keys']) or set(record) - set(spec['fields']):
                raise ValueError('Chave ou coluna invalida em ' + tab)
            values = dict(record)
            if 'data' in values: values['data'] = iso_date(values['data'])
            patch = {k: v for k, v in values.items() if k not in spec['keys'] and k not in spec['generated']}
            if not patch: continue
            sql = f'UPDATE {spec["table"]} SET '+','.join('"'+k+'"=?' for k in patch)+",atualizacao=datetime('now') WHERE "+' AND '.join('"'+k+'"=?' for k in spec['keys'])
            statements.append({'sql': sql, 'params': list(patch.values())+[values[k] for k in spec['keys']]})
        for i in range(0, len(statements), 250):
            self._api().batch(self._db(sheet), statements[i:i+250])
        if statements: self.cache.pop((sheet, tab), None)

    def existing_keys(self,sheet,tab):
        if not self._client(sheet):return self.google.existing_keys(sheet,tab)
        # Upsert pela chave real: permite atualizar dias recentes e distingue anos.
        return set()
    def values_append(self,sheet,range_,rows,value_input_option='USER_ENTERED'):
        if not self._client(sheet):return self.google.values_append(sheet,range_,rows,value_input_option=value_input_option)
        tab,_,_,_,_=parse_range(range_);spec=self._spec(sheet,tab)
        if rows and list(rows[0])==spec['headers']:rows=rows[1:]
        start=len(self._rows(sheet,tab))+2
        statements=[upsert_statement(spec,record_from_row(spec,r),preserve_crm=spec['table'].startswith('ads_')) for r in rows]
        for i in range(0,len(statements),250):self._api().batch(self._db(sheet),statements[i:i+250])
        self.cache.pop((sheet,tab),None)
        return {'updates':{'updatedRange':f"'{tab}'!A{start}:{letter(len(spec['headers'])-1)}{start+max(0,len(rows)-1)}"}}
    def values_update(self,sheet,range_,rows,value_input_option='USER_ENTERED'):
        return self.values_batch_update(sheet,[{'range':range_,'values':rows}],value_input_option)
    def values_batch_update(self,sheet,data,value_input_option='RAW'):
        if not self._client(sheet):return self.google.values_batch_update(sheet,data,value_input_option=value_input_option)
        statements=[];changed=set()
        for part in data:
            tab,c0,r0,_,_=parse_range(part['range']);spec=self._spec(sheet,tab);records=self._rows(sheet,tab)
            for offset,cells in enumerate(part['values']):
                idx=r0+offset-1
                if idx==-1:
                    for j,v in enumerate(cells):
                        if v!=spec['headers'][c0+j]:raise ValueError('Alteracao de cabecalho requer atualizar cloudflare/schema.json.')
                    continue
                if idx>=len(records):raise ValueError('Linha inexistente no D1; use values_append para inserir.')
                record=records[idx];patch={}
                for j,value in enumerate(cells):
                    field=spec['fields'][c0+j]
                    if field in spec['generated']:continue
                    if isinstance(value,str) and value.startswith('='):raise ValueError('Formula nao suportada no D1.')
                    if field=='data':value=iso_date(value)
                    elif field in spec['percent'] and value not in ('',None):value=float(value)*100
                    patch[field]=value if value!='' else None
                if patch:
                    sql=f'UPDATE {spec["table"]} SET '+','.join('"'+f+'"=?' for f in patch)+",atualizacao=datetime('now') WHERE "+' AND '.join('"'+k+'"=?' for k in spec['keys'])
                    statements.append({'sql':sql,'params':list(patch.values())+[record[k] for k in spec['keys']]})
                    changed.add((sheet,tab))
        for i in range(0,len(statements),250):self._api().batch(self._db(sheet),statements[i:i+250])
        for key in changed:self.cache.pop(key,None)
        return {'totalUpdatedRows':len(statements)}
    def append_and_format(self,sheet,gid,tab,rows,percent_cols,currency_cols,date_col=1):
        return self.values_append(sheet,tab+'!A1',rows) if self._client(sheet) else self.google.append_and_format(sheet,gid,tab,rows,percent_cols,currency_cols,date_col)
    def sort_tabs_by_date(self,sheet,tabs,date_col_idx=1):
        if not self._client(sheet):return self.google.sort_tabs_by_date(sheet,tabs,date_col_idx)
    def batch_update(self,sheet,body):
        if not self._client(sheet):return self.google.batch_update(sheet,body)
        for operation in body:
            if set(operation)&{'repeatCell','sortRange','autoResizeDimensions','updateSheetProperties','updateBorders'}:continue
            if 'addSheet' in operation:self._spec(sheet,operation['addSheet']['properties']['title']);continue
            if 'deleteDimension' in operation:
                r=operation['deleteDimension']['range']
                if r['dimension']!='ROWS':raise ValueError('Remocao de colunas nao suportada.')
                tab=next(t for t,s in SCHEMA[self.clients[sheet]].items() if s['gid']==r['sheetId']);spec=self._spec(sheet,tab)
                records=self._rows(sheet,tab)[r['startIndex']-1:r['endIndex']-1]
                self._api().batch(self._db(sheet),[{'sql':f'DELETE FROM {spec["table"]} WHERE '+' AND '.join('"'+k+'"=?' for k in spec['keys']),'params':[row[k] for k in spec['keys']]} for row in records])
                self.cache.pop((sheet,tab),None);continue
            raise ValueError('Operacao Sheets nao suportada no D1: '+','.join(operation))
        return {'replies':[]}
    def __getattr__(self,name):return getattr(self.google,name)
