// Compartilhado por toda página de métrica que lê a planilha real (ver
// ../../sheets-ref.md). Mesma lógica do dashboard v1 (../../index.html),
// só que fatorada pra não duplicar em cada página nova do 2.0.

const SID = '18ONfwZPeeeXF6UiuhSQzrQZSaximdRQNRjhPRfXLaNA';
const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

function normalizeText(value) {
  return String(value || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
}
function col(obj, ...names) {
  if (!obj) return null;
  const keys = Object.keys(obj);
  for (const name of names) {
    const nName = normalizeText(name);
    const found = keys.find(k => normalizeText(k) === nName);
    if (found) return found;
    const part = keys.find(k => normalizeText(k).includes(nName) || nName.includes(normalizeText(k)));
    if (part) return part;
  }
  return null;
}
// Resolve o valor de uma linha tentando várias colunas em ordem (ex.: nome de
// exibição customizado, senão nome bruto da campanha/conjunto). Diferente de
// col() — que resolve pra UMA coluna do cabeçalho pra todas as linhas —, aqui
// cada linha pode "cair" pro próximo nome se o valor dela estiver vazio, o
// que importa porque a coluna de nome de exibição existe no cabeçalho mas
// nem sempre é preenchida pelo sync (fica em branco linha a linha).
function rowText(row, ...names) {
  for (const name of names) {
    const k = col(row, name);
    if (k && row[k] != null && String(row[k]).trim() !== '') return row[k];
  }
  return '';
}
function num(val) {
  if (val === null || val === undefined) return null;
  if (typeof val === 'number') return isNaN(val) ? null : val;
  const s = String(val).trim().replace(/[%\s]/g, '').replace(/^[^0-9-]+/, '');
  if (!s || s === '-' || s === '—' || s === 'N/A') return null;
  let r;
  if (s.includes(',') && s.includes('.')) r = s.replace(/\./g, '').replace(',', '.');
  else if (s.includes(',')) r = s.replace(',', '.');
  else r = s;
  const n = parseFloat(r);
  return isNaN(n) ? null : n;
}
function dateFromRow(row, dK) {
  if (!dK || !row[dK]) return null;
  const raw = String(row[dK]).trim();
  const parts = raw.split('/');
  if (parts.length < 2) return null;
  const day = parseInt(parts[0]);
  if (isNaN(day) || day < 1 || day > 31) return null;
  const mPart = parts[1].trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\./g, '');
  let mIdx = -1;
  const mNum = parseInt(mPart);
  if (!isNaN(mNum) && mNum >= 1 && mNum <= 12) mIdx = mNum - 1;
  else mIdx = MONTHS.findIndex(m => m.startsWith(mPart.slice(0, 3)) || mPart.startsWith(m.slice(0, 3)));
  if (mIdx === -1) return null;
  // O banco contém vários anos; datas DD/MM sem ano são da planilha corrente.
  const year = parts[2] ? (/^\d{4}$/.test(parts[2].trim()) ? Number(parts[2]) : NaN) : new Date().getFullYear();
  if (!Number.isInteger(year) || year < 1900 || year > 2100) return null;
  const date = new Date(year, mIdx, day);
  return date.getFullYear() === year && date.getMonth() === mIdx && date.getDate() === day ? date : null;
}
function parseCSVRows(csv) {
  const records = [];
  let row = [], field = '', inQ = false;
  for (let i = 0; i < csv.length; i++) {
    const c = csv[i], n = csv[i + 1];
    if (inQ) {
      if (c === '"' && n === '"') { field += '"'; i++; }
      else if (c === '"') { inQ = false; }
      else { field += c; }
    } else {
      if (c === '"') { inQ = true; }
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n') { row.push(field); records.push(row); row = []; field = ''; }
      else if (c !== '\r') { field += c; }
    }
  }
  if (field !== '' || row.length) { row.push(field); records.push(row); }
  if (!records.length) return [];
  const headers = records[0];
  return records.slice(1)
    .map(r => { const obj = {}; headers.forEach((h, i) => { obj[h.trim()] = r[i] !== undefined ? r[i] : null; }); return obj; })
    .filter(r => Object.values(r).some(v => v !== null && v !== ''));
}
function sum(arr) { return arr.filter(x => x !== null && !isNaN(x)).reduce((a, b) => a + b, 0); }
function avg(arr) { const v = arr.filter(x => x !== null && !isNaN(x)); return v.length ? sum(v) / v.length : null; }
function rate(numArr, denArr) { const den = sum(denArr); return den ? (sum(numArr) / den) * 100 : null; }
function fmt(n) { return n == null ? '—' : Math.round(n).toLocaleString('pt-BR'); }
// Total Watch Time vem em segundos e costuma ser um número grande (soma de
// muitos posts) — em minutos inteiros fica mais fácil de ler (não precisa
// de segundos nessa escala).
function fmtMin(seconds) { return seconds == null ? '—' : fmt(seconds / 60) + 'min'; }
// Duração de um post (curta, geralmente < 3min) — "1,5min" não existe de
// verdade (ninguém fala assim), então formata como "1min 30s" (ou só "45s"
// quando é menos de um minuto).
function fmtDuration(seconds) {
  if (seconds == null) return '—';
  const total = Math.round(seconds);
  const m = Math.floor(total / 60), s = total % 60;
  return m === 0 ? `${s}s` : `${m}min ${String(s).padStart(2, '0')}s`;
}
function pct(n, digits = 1) { return n == null ? '—' : n.toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits }) + '%'; }

// Último "Total" não-vazio de um bloco de rede na aba [SEGUIDORES] (colT =
// coluna do Total nesse bloco, ver PLATFORMS em seguidores.js) — usado pro
// benchmark de engajamento por faixa de seguidores (classifyEngagement),
// que precisa do tamanho atual da conta.
function latestFollowerTotal(monthlyRows, colT) {
  if (!monthlyRows || !monthlyRows.length) return null;
  for (let i = monthlyRows.length - 1; i >= 0; i--) {
    const v = monthlyRows[i] && num(monthlyRows[i]['col' + colT]);
    if (v != null) return v;
  }
  return null;
}

// Benchmark de taxa de engajamento por faixa de seguidores (referência de
// mercado passada pelo usuário) — thresholds em % (mesma escala do campo
// engagementRate/pct()), do maior pro menor dentro de cada faixa.
const ENGAGEMENT_BENCHMARKS = [
  { max: 1000,     excelente: 8,   bom: 5,   mediano: 3 },
  { max: 5000,     excelente: 6,   bom: 4,   mediano: 2.5 },
  { max: 10000,    excelente: 5,   bom: 3.5, mediano: 2 },
  { max: 50000,    excelente: 4,   bom: 2.5, mediano: 1.5 },
  { max: 100000,   excelente: 3,   bom: 2,   mediano: 1 },
  { max: 500000,   excelente: 2.5, bom: 1.5, mediano: 0.8 },
  { max: Infinity, excelente: 1.5, bom: 0.8, mediano: 0.4 },
];

// rate em % (mesma escala do card "Taxa de engajamento"); followerCount
// pode ser null (sem total de seguidores carregado ainda) — nesse caso não
// dá pra classificar. Escala de cor good→warning→serious→critical segue a
// ordem Excelente→Bom→Mediano→Baixo (do badge existente, style.css).
function classifyEngagement(rate, followerCount) {
  if (rate == null || followerCount == null) return null;
  const tier = ENGAGEMENT_BENCHMARKS.find(t => followerCount <= t.max);
  if (rate >= tier.excelente) return { label: 'Excelente', cls: 'good' };
  if (rate >= tier.bom) return { label: 'Bom', cls: 'warning' };
  if (rate >= tier.mediano) return { label: 'Mediano', cls: 'serious' };
  return { label: 'Baixo', cls: 'critical' };
}

// Abas que já moram no banco metricas-lucri (D1, ver functions/api/tiktok/,
// functions/api/instagram/ e
// metricas-lucri/): quem pede essa aba recebe as linhas do banco no MESMO
// formato do CSV da planilha (mesmos cabeçalhos, números em pt-BR, % como
// "11,1%", data "DD/MM") — por isso nenhuma página que lê a aba precisa
// mudar. Se o banco falhar, cai pra planilha de antes.
const BANCO_ABAS = {
  TIKTOK: { api: '/api/tiktok/posts', conta: 'lucrifinancas', linha: linhaTikTok },
  GUI: { api: '/api/tiktok/posts', conta: 'oguicarvalho', linha: linhaTikTokGui },
  INSTAGRAM: { api: '/api/instagram/posts', conta: 'lucrifinancas', linha: linhaInstagram },
  STORIES: { api: '/api/stories/posts', conta: 'lucrifinancas', linha: linhaStories, prep: ordemNasSequencias },
  YOUTUBE: { api: '/api/youtube/posts', conta: 'lucrifinancas', linha: linhaYoutube },
};
const BANCO_DIAS = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];
const bTxt = v => (v == null ? '' : String(v));
const bDec = (v, casas = 2) => (v == null ? '' : String(Math.round(v * 10 ** casas) / 10 ** casas).replace('.', ','));
const bPct = v => (v == null ? '' : bDec(v, 1) + '%');
function bDataCampos(p) {
  const [ano, mes, dia] = p.data.split('-');
  return {
    MES: p.mes ? p.mes[0].toUpperCase() + p.mes.slice(1) : '',
    DATA: `${dia}/${mes}/${ano}`,
    DIA: BANCO_DIAS[new Date(Number(ano), Number(mes) - 1, Number(dia)).getDay()],
  };
}

function linhaTikTok(p, ranking) {
  const d = bDataCampos(p);
  return {
    'ID': p.id, 'NOME': bTxt(p.nome), 'TIPO': bTxt(p.tipo), 'MES': d.MES, 'DATA': d.DATA, 'DIA': d.DIA,
    'HORARIO': bTxt(p.horario), 'VIEWS': bTxt(p.views), 'ALCANCE': bTxt(p.alcance),
    'DIF ABS': p.views != null && p.alcance != null ? String(p.views - p.alcance) : '',
    'TAXA REPLAY': bPct(p.taxa_replay_pct), 'INTERAÇÕES': bTxt(p.interacoes),
    'LIKES': bTxt(p.likes), 'COMENTS': bTxt(p.coments), 'SHARES': bTxt(p.shares), 'SAVE': bTxt(p.saves),
    'DURAÇÃO (S)': bDec(p.duracao_s), 'MÉDIA(S)': bDec(p.media_s), 'TOTAL (S)': bDec(p.total_s),
    'TAXA DE VIEW': bPct(p.taxa_view), 'Retenção [RLS]': bPct(p.retencao_rls_pct), 'Retenção [EST]': bPct(p.retencao_est_pct),
    'SEGUIDORES': bPct(p.seguidores_pct), 'Ñ SEGUIDORES': bPct(p.nao_seguidores_pct),
    'NOVOS ESPEC': bPct(p.novos_espec_pct), 'VOLTA ESPEC': bPct(p.volta_espec_pct),
    'SEGUIDOR': bTxt(p.seguidor), 'RANKING DE PERFORMANCE': bTxt(ranking),
    'ATUALIZAÇÃO': bTxt(p.atualizacao), 'OBS': bTxt(p.obs), 'PONTUAÇÃO FINAL': bDec(p.pontuacao_final, 1),
  };
}

// Na aba GUI da planilha o TIPO era a editoria (CASE, EMPREENDEDORISMO…) e
// carrossel era "CARROSEL" — os gráficos do Gui agrupam por isso e o
// calcRetention reconhece carrossel por /carro/. Mantém o mesmo formato.
function linhaTikTokGui(p, ranking) {
  const tipo = p.tipo === 'Carrossel' ? 'CARROSEL' : bTxt(p.editoria).toUpperCase();
  return { ...linhaTikTok(p, ranking), 'TIPO': tipo };
}

// ENGAJAMENTO - PERFIL fica vazio aqui (precisa do total de seguidores, que não
// mora no banco de posts) — a página Instagram calcula quando precisa.
function linhaInstagram(p, ranking) {
  const d = bDataCampos(p);
  return {
    'ID': bTxt(p.id), 'NOME': bTxt(p.nome), 'TIPO': bTxt(p.tipo), 'MES': d.MES, 'DATA': d.DATA,
    'HORARIO': bTxt(p.horario), 'VIEWS': bTxt(p.views), 'ALCANCE': bTxt(p.alcance),
    'VIEWS_SEGUI': bPct(p.views_seguidores_pct), 'LIKES': bTxt(p.likes), 'COMENTS': bTxt(p.coments),
    'SHARES': bTxt(p.shares), 'REPOST': bTxt(p.repost), 'SAVE': bTxt(p.saves),
    'DURAÇÃO (S)': bDec(p.duracao_s), 'MÉDIA(S)': bDec(p.media_s), 'TOTAL (S)': bDec(p.total_s),
    'Fonte de Views': bTxt(p.fonte_views).toUpperCase(), 'SEGUIDOR': bTxt(p.seguidor),
    'VISITA AO PERFIL': bTxt(p.visita_perfil), 'COPY': bTxt(p.copy), 'Att': bTxt(p.atualizacao), 'DIA': d.DIA,
    'VIEWS_NÃO SEGUI': bPct(p.views_nao_seguidores_pct), 'TAXA REPLAY': bPct(p.taxa_replay_pct),
    'INTERAÇÕES': bTxt(p.interacoes), 'RATE_LIKE': bPct(p.rate_like_pct), 'RATE_COMENTÁRIOS': bPct(p.rate_coments_pct),
    'RATE_SHARES': bPct(p.rate_shares_pct), 'RATE_SAVE': bPct(p.rate_save_pct),
    'Percentual assistido': bPct(p.percentual_assistido_pct), 'Retenção [EST]': bPct(p.retencao_est_pct),
    'Retenção [RLS]': bPct(p.retencao_rls_pct), 'ENGAJAMENTO - POST': bPct(p.engajamento_post_pct),
    'ENGAJAMENTO - PERFIL': '', 'Ranking': bTxt(ranking), 'Pontuação Final': bDec(p.pontuacao_final, 1),
  };
}

// Stories/YouTube não têm coluna mes (a planilha tinha): vem da data.
const BANCO_MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
function bDataSemMes(p) {
  const d = bDataCampos(p);
  return { ...d, MES: BANCO_MESES[Number(p.data.slice(5, 7)) - 1] };
}

// ORDEM da aba STORIES = posição do story dentro da sequência (por data e horário).
function ordemNasSequencias(posts) {
  const porSeq = {};
  [...posts].sort((a, b) => `${a.data} ${a.horario || ''}`.localeCompare(`${b.data} ${b.horario || ''}`) || a.id - b.id)
    .forEach(p => { const k = p.sequencia || `#${p.id}`; porSeq[k] = (porSeq[k] || 0) + 1; p.ordem = porSeq[k]; });
}

function linhaStories(p) {
  const d = bDataSemMes(p);
  return {
    'NOME': bTxt(p.nome), 'SEQUENCIA': bTxt(p.sequencia), 'ORDEM': bTxt(p.ordem), 'TIPO': bTxt(p.tipo), 'MES': d.MES,
    'DATA': d.DATA, 'DIA': d.DIA, 'HORARIO': bTxt(p.horario), 'VIEWS': bTxt(p.views), 'INTERAÇÕES': bTxt(p.interacoes),
    'ATIVIDADES NO PERFIL': bTxt(p.atividades_perfil), 'VIEWS SEGUIDORES': bPct(p.views_seguidores_pct),
    'VIEWS NÃO SEGUIDORES': bPct(p.views_nao_seguidores_pct), 'ALCANCE': bTxt(p.alcance), 'RETENÇÃO': bPct(p.retencao_pct),
    'CURTIDAS': bTxt(p.curtidas), 'RESPOSTAS': bTxt(p.respostas), 'COMPARTILHAMENTOS': bTxt(p.compartilhamentos),
    'NAVEGAÇÃO': bTxt(p.navegacao), 'AVANÇO': bTxt(p.avanco), 'VOLTAR': bTxt(p.voltar), 'PROXIMO STORY': bTxt(p.proximo_story),
    'SAIU': bTxt(p.saiu), 'SEGUIR': bTxt(p.seguir), 'AO PERFIL': bTxt(p.ao_perfil), 'Figurinhas': bTxt(p.figurinhas),
  };
}

function linhaYoutube(p) {
  const d = bDataSemMes(p);
  return {
    'ID': bTxt(p.id_video), 'NOME': bTxt(p.nome), 'TIPO': bTxt(p.tipo), 'MES': d.MES, 'DATA': d.DATA, 'DIA': d.DIA,
    'HORARIO': bTxt(p.horario), 'VIEWS': bTxt(p.views), 'INTENCIONAL': bTxt(p.intencional), 'DURAÇÃO': bDec(p.duracao_s),
    'MÉDIA': bDec(p.media_s), 'TOTAL': bDec(p.total_s), 'RETENÇÃO': bPct(p.retencao_pct ?? (p.duracao_s > 0 && p.media_s != null ? p.media_s * 100 / p.duracao_s : null)), 'LIKES': bTxt(p.likes),
    'COMENTARIOS': bTxt(p.coments), 'INSCRITOS': bTxt(p.inscritos), 'POR VIEWS': '', '1.000 Views': '', 'CURTIDAS': '', 'Att': bTxt(p.atualizacao),
  };
}

async function fetchBancoRows(aba) {
  const cfg = BANCO_ABAS[aba];
  const resp = await fetch(`${cfg.api}?conta=${cfg.conta}`, { cache: 'no-store' });
  if (!resp.ok) throw new Error('HTTP ' + resp.status);
  const posts = (await resp.json()).posts || [];
  if (!posts.length) throw new Error('banco vazio');
  if (cfg.prep) cfg.prep(posts);
  // Ranking = posição pela pontuação final (1 = melhor), igual RANK.EQ da planilha.
  const ranking = new Map([...posts].filter(p => p.pontuacao_final != null)
    .sort((a, b) => b.pontuacao_final - a.pontuacao_final).map((p, i) => [p.id, i + 1]));
  // Mais antigo primeiro, igual a ordem da planilha.
  return posts.slice().reverse().map(p => cfg.linha(p, ranking.get(p.id)));
}

// Trafego pago e GA4 agora sao lidos do D1; falhas nao usam a planilha antiga.
const TRAFEGO_D1_ABAS = {
  "META ADS - CAMPANHAS": "meta-campanhas",
  "META ADS - CONJUNTOS DE ANÚNCIO": "meta-conjuntos",
  "META ADS - ANÚNCIOS": "meta-anuncios",
  "GOOGLE ADS - CAMPANHAS": "google-campanhas",
  "GOOGLE ADS - GRUPOS DE ANÚNCIO": "google-grupos",
  "GOOGLE ADS - TERMOS DE BUSCA": "google-termos",
  "GOOGLE ADS - PALAVRAS-CHAVE": "google-palavras",
  "GA4 - PÁGINAS": "ga4-paginas",
  "GA4 - QUIZ LP PADRÃO": "ga4-quiz-lp",
  "GA4 - QUIZ TYPEFORM": "ga4-quiz-typeform"
};
async function fetchTrafegoD1Rows(tab) {
  const response = await fetch(`/api/trafego/${TRAFEGO_D1_ABAS[tab]}?format=sheet`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`D1: HTTP ${response.status}`);
  const payload = await response.json();
  if (!payload.ok || !Array.isArray(payload.rows)) throw new Error('Resposta D1 invalida.');
  return payload.rows;
}

async function fetchSheetRows(sheetName, sid) {
  if (sid === "1kzLgUiOyn0oM_2YZ3k6o3k6kWVoTCOm-w_CVYMK5QGY" && TRAFEGO_D1_ABAS[sheetName]) return fetchTrafegoD1Rows(sheetName);
  if (!sid && BANCO_ABAS[sheetName]) {
    try { return await fetchBancoRows(sheetName); }
    catch (e) { console.warn(`${sheetName}: banco não respondeu, lendo a planilha.`, e); }
  }
  const url = `https://docs.google.com/spreadsheets/d/${sid || SID}/gviz/tq?tqx=out:csv&sheet=${encodeURIComponent(sheetName)}`;
  const resp = await fetch(url, { cache: 'no-store' });
  if (!resp.ok) throw new Error('HTTP ' + resp.status);
  const text = await resp.text();
  const rows = parseCSVRows(text);
  if (!rows.length) throw new Error('planilha vazia');
  return rows;
}

// Mesmo parser do v1 (ver 4.DASHBOARD/index.html) — usado só quando
// precisamos de `range`/`headers=0` (células fixas, sem cabeçalho), caso em
// que o endpoint CSV não serve porque não dá pra pedir um recorte de células.
function parseGViz(data, useRaw) {
  const tbl = data.table;
  if (!tbl || !tbl.cols) return [];
  const seen = {};
  const hdrs = tbl.cols.map((c, i) => {
    const base = c.label || 'col' + i;
    seen[base] = (seen[base] || 0) + 1;
    return seen[base] === 1 ? base : `${base}_${i}`;
  });
  return (tbl.rows || []).map(row => {
    if (!row || !row.c) return null;
    const obj = {};
    row.c.forEach((cell, i) => {
      if (!cell) { obj[hdrs[i]] = null; return; }
      obj[hdrs[i]] = useRaw
        ? (cell.v !== undefined ? cell.v : null)
        : (cell.f !== undefined && cell.f !== null ? cell.f : cell.v);
    });
    return obj;
  }).filter(r => r && Object.values(r).some(v => v !== null && v !== ''));
}

// Fetch JSONP de um `range` de células fixas (ex: 'B5:T16', sem cabeçalho) —
// mesma técnica do v1 (script tag + callback), necessária porque o endpoint
// CSV não aceita `range=`. Colunas viram `col0`, `col1`, ... quando `headers=0`.
let jsonpSeq = 0;
function loadSheetRange(sheetName, range, useRaw, sid, timeoutMs) {
  if (sheetName === '[SEGUIDORES]' && !sid) {
    return seguidoresDoBanco(range).catch(e => {
      console.warn('[SEGUIDORES]: banco não respondeu, lendo a planilha.', e);
      return loadSheetRangeGViz(sheetName, range, useRaw, sid, timeoutMs);
    });
  }
  return loadSheetRangeGViz(sheetName, range, useRaw, sid, timeoutMs);
}

// Aba [SEGUIDORES] mora no banco metricas-lucri (functions/api/seguidores.js)
// desde 13/10/2026. Devolve as linhas no MESMO formato do range da planilha
// (col0, col1…), pra nenhuma página mudar. A planilha é a de 2026.
// - 'B5:T16': 12 meses, 4 blocos de 5 colunas (mês, ganho, perda, total, vazio)
//   na ordem Instagram, TikTok, YouTube, TikTok Gui.
// - 'C18:E19' / 'H18:J19' / 'M18:O19' / 'R18:T19': total atual de cada rede.
const SEG_BANCO_ANO = 2026;
const SEG_BLOCOS = [['lucrifinancas', 'instagram'], ['lucrifinancas', 'tiktok'],
  ['lucrifinancas', 'youtube'], ['oguicarvalho', 'tiktok']];
const SEG_TOTAL_RANGES = ['C18:E19', 'H18:J19', 'M18:O19', 'R18:T19'];
const SEG_MESES = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO',
  'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
let segBancoPromise = null;

async function seguidoresDoBanco(range) {
  const bloco = SEG_TOTAL_RANGES.indexOf(range);
  if (range !== 'B5:T16' && bloco < 0) throw new Error('range sem banco: ' + range);
  if (!segBancoPromise) {
    segBancoPromise = fetch(`/api/seguidores?ano=${SEG_BANCO_ANO}`, { cache: 'no-store' })
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(d => {
        if (!d.seguidores || !d.seguidores.length) throw new Error('banco vazio');
        return d.seguidores;
      });
    segBancoPromise.catch(() => { segBancoPromise = null; });
  }
  const linhas = await segBancoPromise;
  const doBloco = ([conta, rede]) => linhas.filter(l => l.conta === conta && l.rede === rede);

  if (bloco >= 0) {
    const comTotal = doBloco(SEG_BLOCOS[bloco]).filter(l => l.total != null);
    return comTotal.length ? [{ col0: comTotal[comTotal.length - 1].total, col1: null, col2: null }] : [];
  }
  return SEG_MESES.map((nome, i) => {
    const row = {};
    SEG_BLOCOS.forEach((b, j) => {
      const l = doBloco(b).find(x => x.mes === i + 1) || {};
      row['col' + (j * 5)] = nome;
      row['col' + (j * 5 + 1)] = l.ganho ?? null;
      row['col' + (j * 5 + 2)] = l.perda ?? null;
      row['col' + (j * 5 + 3)] = l.total ?? null;
      if (j < 3) row['col' + (j * 5 + 4)] = null;
    });
    return row;
  });
}

function loadSheetRangeGViz(sheetName, range, useRaw, sid, timeoutMs) {
  return new Promise((resolve, reject) => {
    const cb = '_cb_' + sheetName.replace(/\W/g, '_') + '_' + Date.now() + '_' + (++jsonpSeq);
    const sheetParam = sheetName.startsWith('gid:') ? `gid=${sheetName.slice(4)}` : `sheet=${encodeURIComponent(sheetName)}`;
    const url = `https://docs.google.com/spreadsheets/d/${sid || SID}/gviz/tq`
      + `?tqx=out:json;responseHandler:${cb}&${sheetParam}`
      + `&range=${encodeURIComponent(range)}&headers=0`;
    const el = document.createElement('script');
    const t = setTimeout(() => { reject(new Error('timeout:' + sheetName)); cleanup(); }, timeoutMs || 18000);
    function cleanup() { clearTimeout(t); delete window[cb]; if (el.parentNode) el.parentNode.removeChild(el); }
    window[cb] = data => { cleanup(); try { resolve(parseGViz(data, useRaw)); } catch (e) { reject(e); } };
    el.onerror = () => { reject(new Error('script-error:' + sheetName)); cleanup(); };
    document.head.appendChild(el);
    el.src = url;
  });
}

// Retenção por fórmula (pedido do usuário, substitui a coluna "Retenção
// [RLS]" da planilha, que fica 0% até alguém preencher manualmente depois):
// Carrossel = Interações / Alcance; Reels = Média Segundos Assistido /
// Duração do Reels. Ambas em %.
function calcRetention(type, reach, interactions, avgWatch, duration) {
  const isCarrossel = /carro/i.test(type || '');
  if (isCarrossel) return reach ? (interactions / reach) * 100 : null;
  return duration ? (avgWatch / duration) * 100 : null;
}

function delta(cur, prev) {
  if (cur == null || prev == null || prev === 0) return null;
  return ((cur - prev) / prev) * 100;
}

// `p.date` é sempre uma string "AAAA-MM-DD" (ver toRows/dateFromRow). `new
// Date('AAAA-MM-DD')` interpreta como meia-noite UTC, mas period.start/end
// (period.js) vêm de cliques de calendário em horário local — comparar os
// dois direto desalinha em algumas horas (fuso do Brasil) e faz um período de
// um único dia excluir a própria linha daquele dia. Parseia como data local
// pra bater com o lado do período.
function parseDateOnlyLocal(s) {
  const [y, m, d] = String(s).split('-').map(Number);
  return new Date(y, m - 1, d);
}

function windowPosts(posts, endDate, days) {
  const end = new Date(endDate);
  const start = new Date(end); start.setDate(start.getDate() - (days - 1));
  return posts.filter(p => { const d = parseDateOnlyLocal(p.date); return d >= start && d <= end; });
}

// Filtra por um período do seletor global (period.js) — {start, end}, cada
// um podendo ser null. Sem start nem end = "Todos os dados" (retorna tudo).
function filterByPeriod(posts, period) {
  if (!period || (!period.start && !period.end)) return posts;
  const start = period.start || new Date(0);
  const end = period.end || new Date(8640000000000000);
  return posts.filter(p => { const d = parseDateOnlyLocal(p.date); return d >= start && d <= end; });
}

// Filtra linhas CRUAS da planilha (não o shape já normalizado de posts) por
// índice de mês do calendário (0-11), ignorando o ano — mesmo conceito do
// v1 (usado pela IA pra montar contexto "mês atual vs. mês anterior").
// Autodetecta a coluna de data via col('DATA'/'DIA').
function filterByMonthIdx(rows, mIdx) {
  if (!rows || !rows.length) return [];
  const dK = col(rows[0], 'DATA', 'DIA');
  return rows.filter(r => { const d = dateFromRow(r, dK); return d && d.getMonth() === mIdx; });
}

// Conta posts (shape já normalizado, com `.date` "AAAA-MM-DD") por mês
// calendário — feature que existia no v1 ("posts totais da rede por mês"),
// sempre sobre TODOS os posts carregados (não respeita o período livre do
// topo, é uma visão histórica completa). Meses sem nenhum post não entram
// no resultado (evita barra zerada isolada quando falta dado antigo).
const MONTHS_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
function postsByMonth(posts) {
  const counts = {};
  posts.forEach(p => { const key = p.date.slice(0, 7); counts[key] = (counts[key] || 0) + 1; });
  const keys = Object.keys(counts).sort();
  return {
    labels: keys.map(k => `${MONTHS_ABREV[Number(k.slice(5, 7)) - 1]}/${k.slice(2, 4)}`),
    values: keys.map(k => counts[k]),
  };
}

// Soma Ganho/Perda REAIS da aba [SEGUIDORES] (monthlyRows = uma linha por
// mês do ano corrente, mesmo shape de SEG_MONTHLY_RANGE) pros meses
// TOTALMENTE cobertos pelo período selecionado (seletor global, period.js).
// A aba só tem granularidade mensal — diferente de somar a coluna
// SEGUIDOR/INSCRITOS de cada vídeo (isso mede quem a rede atribui àquele
// post específico, não o crescimento real da conta), então um período
// parcial que não fecha um mês inteiro (ex: "últimos 7 dias") não tem como
// ser exato e essa função retorna null nesse caso. "Todos os dados" (period
// sem start/end) inclui todo mês com valor.
// Cada rede ocupa um bloco de 5 colunas — colT é a coluna do Total, Ganho
// fica em colT-2 e Perda em colT-1 (mesma convenção de seguidores.js).
function seguidoresGrowthForPeriod(monthlyRows, colT, period) {
  if (!monthlyRows || !monthlyRows.length) return null;
  const year = new Date().getFullYear();
  const all = !period || (!period.start && !period.end);
  let ganho = 0, perda = 0, any = false;
  monthlyRows.forEach((r, i) => {
    if (!r || !r.col0 || !String(r.col0).trim()) return;
    if (!all) {
      const monthStart = new Date(year, i, 1);
      const monthEnd = new Date(year, i + 1, 0);
      if (!(period.start <= monthStart && period.end >= monthEnd)) return;
    }
    const g = r['col' + (colT - 2)], p = r['col' + (colT - 1)];
    if (g != null) { ganho += g; any = true; }
    if (p != null) { perda += p; any = true; }
  });
  return any ? { ganho, perda, saldo: ganho - perda } : null;
}

// Equivalentes de latestFollowerTotal/seguidoresGrowthForPeriod, mas lendo
// direto do banco (`historico_seguidores` via /api/historico/seguidores) em
// vez da aba [SEGUIDORES] da planilha — mesma semântica, shape diferente
// (linha por mês já vem como {network,year,month,ganho,perda,total}, não
// precisa de colT posicional).
async function fetchHistSeguidores(network, year) {
  const res = await fetch(`/api/historico/seguidores?network=${encodeURIComponent(network)}&year=${encodeURIComponent(year)}`);
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

function histSegLatestTotal(rows) {
  if (!rows || !rows.length) return null;
  const sorted = [...rows].sort((a, b) => a.month - b.month);
  for (let i = sorted.length - 1; i >= 0; i--) {
    if (sorted[i].total != null) return sorted[i].total;
  }
  return null;
}

// ---------- Paginação genérica de tabelas administrativas ----------
// Usada por listas que só crescem (posts lançados em editar-dados.html,
// histórico de seguidores em seguidores.html) — navegação clássica
// Anterior/Próxima com números de página, não "carregar mais"/scroll
// infinito, porque aqui o padrão certo é o de uma lista administrativa
// com filtro/ordenação recuperáveis (ver
// https://camaraux.com.br/padroes-de-ux/paginacao-tabelas-usar-configurar/),
// não um feed de descoberta.
function paginateRows(rows, page, pageSize) {
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * pageSize;
  return { pageRows: rows.slice(start, start + pageSize), page: safePage, totalPages, total: rows.length };
}

// Números de página visíveis com reticências (máx. 7 itens: primeira,
// última, atual ±1, resto colapsa em "…") — evita listar dezenas de
// botões quando a tabela cresce muito.
function pagerRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const set = new Set([1, total, current - 1, current, current + 1]);
  const arr = [...set].filter(p => p >= 1 && p <= total).sort((a, b) => a - b);
  const out = [];
  arr.forEach((p, i) => { if (i > 0 && p - arr[i - 1] > 1) out.push('…'); out.push(p); });
  return out;
}

// Renderiza os controles de paginação num container e liga o clique —
// `onChange(novaPagina)` fica a cargo de quem chama re-renderizar a tabela.
function renderPager(container, page, totalPages, onChange) {
  if (!container) return;
  if (totalPages <= 1) { container.innerHTML = ''; return; }
  const nums = pagerRange(page, totalPages);
  container.innerHTML = `
    <nav class="pager" aria-label="Paginação">
      <button type="button" class="pager-btn" data-pg="${page - 1}" ${page === 1 ? 'disabled' : ''}>Anterior</button>
      ${nums.map(p => p === '…'
        ? `<span class="pager-ellipsis">…</span>`
        : `<button type="button" class="pager-btn pager-num${p === page ? ' active' : ''}" data-pg="${p}"${p === page ? ' aria-current="page"' : ''}>${p}</button>`
      ).join('')}
      <button type="button" class="pager-btn" data-pg="${page + 1}" ${page === totalPages ? 'disabled' : ''}>Próxima</button>
    </nav>`;
  container.querySelectorAll('[data-pg]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = Number(btn.dataset.pg);
      if (target >= 1 && target <= totalPages) onChange(target);
    });
  });
}

function histSegGrowthForPeriod(rows, period) {
  if (!rows || !rows.length) return null;
  const year = new Date().getFullYear();
  const all = !period || (!period.start && !period.end);
  let ganho = 0, perda = 0, any = false;
  rows.forEach(r => {
    const i = r.month - 1; // month é 1-12
    if (!all) {
      const monthStart = new Date(year, i, 1);
      const monthEnd = new Date(year, i + 1, 0);
      if (!(period.start <= monthStart && period.end >= monthEnd)) return;
    }
    if (r.ganho != null) { ganho += r.ganho; any = true; }
    if (r.perda != null) { perda += r.perda; any = true; }
  });
  return any ? { ganho, perda, saldo: ganho - perda } : null;
}
