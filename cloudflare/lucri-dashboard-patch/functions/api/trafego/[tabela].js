// Dados agregados de trafego. O CRM com dados pessoais nao e exposto.
import { metricRows, readMetricTable } from '../../_trafego-reader.js';
import { SCHEMA } from '../../_trafego-schema.js';
const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store', 'X-Metrics-Source': 'cloudflare-d1' }
});
export async function onRequestGet({ request, env, params }) {
  const spec = SCHEMA[params.tabela];
  if (!spec) return json({ ok: false, erro: 'Tabela nao disponivel.' }, 404);
  if (!env.METRICAS_DB) return json({ ok: false, erro: 'Binding METRICAS_DB ausente.' }, 500);
  const p = new URL(request.url).searchParams;
  const from = p.get('de'), to = p.get('ate');
  for (const value of [from, to]) if (value && !/^\d{4}-\d{2}-\d{2}$/.test(value)) return json({ ok: false, erro: 'Data invalida.' }, 400);
  try {
    const records = await readMetricTable(env.METRICAS_DB, spec, from, to);
    return json(p.get('format') === 'sheet'
      ? { ok: true, rows: metricRows(spec, records, true) }
      : { ok: true, linhas: records });
  } catch {
    return json({ ok: false, erro: 'Nao foi possivel ler o D1.' }, 502);
  }
}
