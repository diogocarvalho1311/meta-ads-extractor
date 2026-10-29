import json, os, sqlite3, sys, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from d1_metricas import D1MetricsClient,SCHEMA,record_from_row,iso_date,upsert_statement

class LocalAPI:
    def __init__(self):
        self.dbs={c:sqlite3.connect(':memory:') for c in SCHEMA}
        for c,db in self.dbs.items():
            db.row_factory=sqlite3.Row
            if c=='lucri':db.executescript((ROOT/'cloudflare/schema-lucri-ads.sql').read_text(encoding='utf-8'))
            db.executescript((ROOT/f'cloudflare/schema-{c}.sql').read_text(encoding='utf-8'))
    def query(self,db,sql,params=()):return [dict(r) for r in self.dbs[db].execute(sql,params)]
    def batch(self,db,statements):
        with self.dbs[db]:
            for s in statements:self.dbs[db].execute(s['sql'],s['params'])
        return []

class NoGoogle:
    def values_get(self,*args,**kw):return {'google':True}

class MigrationTests(unittest.TestCase):
    def setUp(self):
        backend = patch.dict(os.environ, {'METRICAS_BACKEND': 'd1'})
        backend.start()
        self.addCleanup(backend.stop)
        self.api=LocalAPI()
        self.client=D1MetricsClient({'SHEETS_ID_LUCRI_METRICAS':'lucri','SHEETS_ID_CWBKIDS_METRICAS':'cwbkids','D1_DATABASE_ID_LUCRI':'lucri','D1_DATABASE_ID_CWBKIDS':'cwbkids'},NoGoogle())
        self.client.api=self.api
    def tearDown(self):
        for db in self.api.dbs.values(): db.close()
    def sample(self,spec,day='20/10/2026'):
        return [day if f=='data' else 'id-1' if f in spec['text'] else 'SIM' if f=='destino_link' else 0.25 if f in spec['percent'] else 10 for f in spec['fields']]
    def test_all_nineteen_tables_and_every_column(self):
        for client,tabs in SCHEMA.items():
            for title,s in tabs.items():
                with self.subTest(client=client,table=title):
                    row=self.sample(s)
                    self.client.values_append(client,title+'!A1',[row])
                    values=self.client.values_get(client,title+'!A1:AZ100')['values']
                    self.assertEqual(values[0],s['headers'])
                    self.assertEqual(len(values),2)
                    dbrow=self.api.query(client,'SELECT * FROM '+s['table'])[0]
                    self.assertEqual(dbrow['data'],'2026-10-20')
                    for f in s['percent']:
                        if f not in s['generated']:self.assertEqual(dbrow[f],25)
    def test_idempotence_and_crm_preservation(self):
        tab='META ADS - CAMPANHAS';s=SCHEMA['lucri'][tab];row=self.sample(s)
        row[s['fields'].index('leads_qualificados')]=3
        row[s['fields'].index('nome_exibicao')]='Nome manual'
        self.client.values_append('lucri',tab+'!A1',[row])
        row[s['fields'].index('leads_qualificados')]=0;row[s['fields'].index('nome_exibicao')]=''
        row[s['fields'].index('investimento')]=90
        self.client.values_append('lucri',tab+'!A1',[row])
        rows=self.api.query('lucri','SELECT * FROM ads_meta_campanhas')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['leads_qualificados'],3)
        self.assertEqual(rows[0]['cplq'],30);self.assertEqual(rows[0]['nome_exibicao'],'Nome manual')
    def test_updates_crm_and_generated_cost(self):
        tab='META ADS - CAMPANHAS';s=SCHEMA['lucri'][tab];row=self.sample(s)
        self.client.values_append('lucri',tab+'!A1',[row])
        self.client.values_update('lucri',tab+'!K2:L2',[[2,1]])
        self.client.values_update('lucri',tab+'!S2',[['=IF(K2=0;"";T2/K2)']])
        r=self.api.query('lucri','SELECT * FROM ads_meta_campanhas')[0]
        self.assertEqual(r['leads_qualificados'],2);self.assertEqual(r['cplq'],5)
    def test_separates_years_and_serial_date_reading(self):
        tab='NUVEMSHOP';s=SCHEMA['cwbkids'][tab]
        self.client.values_append('cwbkids',tab+'!A1',[self.sample(s,'20/10/2025'),self.sample(s)])
        rows=self.client.values_get('cwbkids',tab+'!A2:A5')['values']
        self.assertEqual(rows,[['20/10/2025'],['20/10/2026']])
        raw=self.client.values_get('cwbkids',tab+'!A2:A5',value_render_option='UNFORMATTED_VALUE')['values']
        self.assertEqual(iso_date(raw[0][0]),'2025-10-20')
    def test_other_sheets_stay_on_google(self):
        self.assertTrue(self.client.values_get('catalogo','PRODUTOS!A1:A5')['google'])
    def test_bound_values_and_compound_keys(self):
        tab='GOOGLE ADS - TERMOS DE BUSCA';s=SCHEMA['cwbkids'][tab];row=self.sample(s)
        row[1]="x'); DROP TABLE ads_google_termos; --"
        self.client.values_append('cwbkids',tab+'!A1',[row,row])
        self.assertEqual(len(self.api.query('cwbkids','SELECT * FROM ads_google_termos')),1)
    def test_nuvem_partial_dates_preserve_manual_revenue(self):
        tab = 'NUVEMSHOP'
        self.client.upsert_records('cwbkids', tab, [{'data': '2026-10-20', 'receita_total_da_loja': 500, 'pedidos_totais_da_loja': 4}])
        self.client.upsert_records('cwbkids', tab, [{'data': '2026-10-19', 'sessoes': 70}, {'data': '2026-10-20', 'sessoes': 90}])
        records = self.api.query('cwbkids', 'SELECT * FROM nuvemshop ORDER BY data')
        self.assertEqual(records[0]['sessoes'], 70)
        self.assertEqual(records[1]['sessoes'], 90)
        self.assertEqual(records[1]['receita_total_da_loja'], 500)
        self.assertEqual(records[1]['pedidos_totais_da_loja'], 4)

    def test_real_meta_importer_layout_for_both_clients(self):
        import contextlib, io
        from meta_from_extension import process_lucri, process_cwbkids, CLIENTES
        name = 'Campanha de teste'
        common = {'date':'2026-10-20','impressoes':100,'cliques':10,'gasto':30,'leads':1,'pv':5,'alcance':80,'plays':60}
        payload = {
            'campanhas': [dict(common, nome=name, objetivo='OUTCOME_LEADS')],
            'conjuntos': [dict(common, campanha=name, nome='Conjunto')],
            'anuncios': [dict(common, campanha=name, conjunto='Conjunto', nome='Anuncio')],
        }
        class Analytics:
            def fetch_by_campaign(self, *_):
                return {name:{'page_views':5,'add_to_cart':4,'begin_checkout':3,'purchases':2,'revenue':90}}
        with contextlib.redirect_stdout(io.StringIO()):
            process_lucri(payload,self.client,'lucri',{'campaigns':{},'adsets':{},'ads':{}},CLIENTES['1111111111111111'])
            process_cwbkids(payload,self.client,'cwbkids',{'campaigns':{},'adsets':{},'ads':{}},CLIENTES['222222222222222'],Analytics())
        lucri=self.api.query('lucri','SELECT * FROM ads_meta_campanhas')[0]
        cwb=self.api.query('cwbkids','SELECT * FROM ads_meta_campanhas')[0]
        self.assertEqual(lucri['leads'],1)
        self.assertEqual(lucri['investimento'],30)
        self.assertEqual(cwb['compras'],2)
        self.assertEqual(cwb['ctr_pct'],10)
        self.assertEqual(cwb['receita'],90)

    def test_crm_updates_by_key_without_redundant_writes(self):
        from lucri_crm_notion_sync import process_tab, norm
        import contextlib,io
        tab='META ADS - CAMPANHAS';spec=SCHEMA['lucri'][tab]
        row=self.sample(spec)
        self.client.values_append('lucri',tab+'!A1',[row])
        key=(norm('20/10/2026'),norm('id-1'))
        with contextlib.redirect_stdout(io.StringIO()):
            process_tab(self.client,'lucri',tab,[1,2],{key:2},{key:1},True)
        record=self.api.query('lucri','SELECT * FROM ads_meta_campanhas')[0]
        self.assertEqual(record['leads_qualificados'],2)
        self.assertEqual(record['leads_fechados'],1)
        self.assertEqual(record['cplq'],5)
        with patch.object(self.api,'batch',wraps=self.api.batch) as calls, contextlib.redirect_stdout(io.StringIO()):
            process_tab(self.client,'lucri',tab,[1,2],{key:2},{key:1},True)
            calls.assert_not_called()

    def test_invalid_date_and_unknown_tab_fail(self):
        with self.assertRaises(ValueError):iso_date('31/02/2026')
        with self.assertRaises(ValueError):self.client.values_get('lucri','INVALID!A1:A9')
    def test_cwb_meta_purchases_are_stored(self):
        tab='META ADS - CAMPANHAS';s=SCHEMA['cwbkids'][tab];row=self.sample(s);row[-1]=3
        self.client.values_append('cwbkids',tab+'!A1',[row])
        r=self.api.query('cwbkids','SELECT compras FROM ads_meta_campanhas')[0]
        self.assertEqual(r['compras'],3)

if __name__=='__main__':unittest.main()
