import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { test } from 'node:test';

const source = name => readFileSync(new URL(`../extensao-meta-ads/${name}`, import.meta.url), 'utf8');
function background(fetch) {
  const context = vm.createContext({ fetch, URLSearchParams, AbortSignal,
    chrome: { runtime: { id: 'test', onMessage: { addListener() {} } } } });
  vm.runInContext(source('background.js'), context);
  return context;
}
const response = data => ({ ok: true, status: 200, json: async () => data });

test('paginação continua mesmo com menos de 500 registros e codifica cursor/token', async () => {
  const urls = [];
  const ctx = background(async url => {
    urls.push(new URL(url));
    return response(urls.length === 1
      ? { data: [{ ad_id: '1' }], paging: { next: 'https://example.invalid/unused', cursors: { after: 'a+b&c' } } }
      : { data: [{ ad_id: '2' }] });
  });
  const rows = await ctx.fetchInsightsLevel('123', 'test+&token', 'yesterday', 'ad');
  assert.equal(rows.length, 2);
  assert.equal(urls[1].hostname, 'graph.facebook.com');
  assert.equal(urls[1].searchParams.get('after'), 'a+b&c');
  assert.equal(urls[1].searchParams.get('access_token'), 'test+&token');
  assert.equal(urls[1].searchParams.get('time_increment'), '1');
});
test('cursor repetido falha em vez de exportar parcialmente ou entrar em loop', async () => {
  const ctx = background(async () => response({ data: [], paging: { next: 'next', cursors: { after: 'same' } } }));
  await assert.rejects(ctx.fetchInsightsLevel('123', 'test', 'today', 'campaign'), /Paginação inválida/);
});
test('erros de transporte e Meta não vazam token', async () => {
  for (const fetch of [
    async () => { throw Error('https://graph.facebook.com/?access_token=PRIVATE'); },
    async () => ({ ok: false, status: 403, json: async () => ({ error: { code: 190, message: 'PRIVATE' } }) }),
  ]) {
    const ctx = background(fetch);
    await assert.rejects(ctx.fetchInsightsLevel('123', 'PRIVATE', 'today', 'ad'), err => !err.message.includes('PRIVATE'));
  }
});
test('entrada inválida falha antes da rede e estrutura inválida não vira export vazio', async () => {
  let calls = 0;
  const ctx = background(async () => { calls++; return response({}); });
  await assert.rejects(ctx.fetchInsightsLevel('123/other', 'test', 'today', 'ad'));
  await assert.rejects(ctx.fetchInsightsLevel('123', 'test', 'all_time', 'ad'));
  assert.equal(calls, 0);
  await assert.rejects(ctx.fetchInsightsLevel('123', 'test', 'today', 'ad'), /Resposta de métricas inválida/);
});
test('troca de conta utiliza a sessão recente da conta ativa', () => {
  let listener;
  const entry = (id, token) => ({ name: `https://graph.facebook.com/v22.0/act_${id}/am_tabular?access_token=${token}` });
  const ctx = vm.createContext({ URL, location: { href: 'https://adsmanager.facebook.com/?act=123' },
    performance: { getEntriesByType: () => [entry('123', 'old'), entry('123', 'new'), entry('456', 'other')] },
    chrome: { runtime: { id: 'test', onMessage: { addListener(fn) { listener = fn; } } } } });
  vm.runInContext(source('content.js'), ctx);
  assert.equal(ctx.getCredentials().token, 'new');
  ctx.location.href = 'https://adsmanager.facebook.com/?act=789';
  assert.equal(ctx.getCredentials(), null);
  let replied = false;
  listener({ type: 'GET_CREDENTIALS' }, { id: 'foreign' }, () => { replied = true; });
  assert.equal(replied, false);
});

function popup(chrome) {
  const elements = new Map();
  for (const id of ['status', 'btn-test', 'btn-export', 'date-preset']) {
    elements.set(id, { value: 'yesterday', addEventListener(_, fn) { this.click = fn; } });
  }
  const controls = ['btn-test', 'btn-export', 'date-preset'].map(id => elements.get(id));
  const ctx = vm.createContext({ chrome, URL, Blob, console,
    document: { getElementById: id => elements.get(id), querySelectorAll: () => controls } });
  vm.runInContext(source('popup.js'), ctx);
  return { ctx, elements, controls };
}
test('popup restaura controles após falha de comunicação', async () => {
  const { elements, controls } = popup({ tabs: { query: async () => { throw Error('offline'); } } });
  await elements.get('btn-export').click();
  assert.equal(elements.get('status').className, 'err');
  assert.ok(controls.every(c => c.disabled === false));
});
test('popup mantém o contrato de métricas e exporta JSON sem token', async () => {
  let download, payload;
  const raw = { date_start: '2026-10-28', campaign_name: 'Campanha demo', campaign_id: 'demo',
    impressions: '1000', spend: '30.50', actions: [{ action_type: 'link_click', value: '25' }, { action_type: 'lead', value: '3' }] };
  const { ctx, elements } = popup({ tabs: { query: async () => [{ id: 1, url: 'https://adsmanager.facebook.com/' }],
    sendMessage: async () => ({ ok: true, accountId: '999999', token: 'PRIVATE' }) },
    runtime: { sendMessage: async () => ({ ok: true, accountId: '999999', datePreset: 'yesterday', campanhas: [raw], conjuntos: [], anuncios: [] }) },
    downloads: { download: async value => { download = value; payload = await (await fetch(value.url)).json(); } } });
  assert.equal(ctx.parseCampanhas([raw])[0].gasto, 30.5);
  await elements.get('btn-export').click();
  assert.match(download.filename, /^meta_999999_\d{8}_20261028\.json$/);
  assert.equal(payload.campanhas[0].leads, 3);
  assert.ok(!JSON.stringify(payload).includes('PRIVATE'));
  assert.equal(elements.get('status').className, 'ok');
});
