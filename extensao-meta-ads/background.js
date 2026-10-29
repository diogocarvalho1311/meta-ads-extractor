// Background service worker - faz requests ao Graph API sem interferência do SW do Meta

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id || !msg || typeof msg !== "object") return;
  if (msg.type === "FETCH_ADS_WITH_METRICS") {
    fetchInsightsLevel(msg.accountId, msg.token, msg.datePreset, "ad")
      .then(result => sendResponse({ ok: true, ads: result }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (msg.type === "FETCH_ALL_METRICS") {
    fetchAllLevels(msg.accountId, msg.token, msg.datePreset)
      .then(result => sendResponse({ ok: true, ...result }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }
});

// Endpoint /insights com level= garante filtragem de data correta
const CAMP_FIELDS  = "campaign_id,campaign_name,objective,impressions,clicks,spend,actions";
const ADSET_FIELDS = "campaign_id,campaign_name,adset_id,adset_name,impressions,reach,clicks,spend,frequency,actions";
const AD_FIELDS    = "campaign_id,campaign_name,adset_id,adset_name,ad_id,ad_name,impressions,reach,clicks,spend,frequency,actions,video_p25_watched_actions";

async function fetchAllLevels(accountId, token, datePreset) {
  const [campanhas, conjuntos, anuncios] = await Promise.all([
    fetchInsightsLevel(accountId, token, datePreset, "campaign"),
    fetchInsightsLevel(accountId, token, datePreset, "adset"),
    fetchInsightsLevel(accountId, token, datePreset, "ad"),
  ]);
  return { accountId, datePreset, campanhas, conjuntos, anuncios };
}

async function fetchInsightsLevel(accountId, token, datePreset, level) {
  if (!/^\d+$/.test(String(accountId)) || typeof token !== "string" || !token) {
    throw new Error("Conta ou sessão inválida. Recarregue o Ads Manager.");
  }
  if (!["today", "yesterday", "last_7d", "last_30d"].includes(datePreset)
      || !["campaign", "adset", "ad"].includes(level)) {
    throw new Error("Período ou nível inválido.");
  }
  const fields = level === "campaign" ? CAMP_FIELDS
               : level === "adset"   ? ADSET_FIELDS
               : AD_FIELDS;

  const all = [];
  const seen = new Set();
  let cursor;
  while (true) {
    const params = new URLSearchParams({
      level, date_preset: datePreset, time_increment: "1", fields,
      limit: "500", access_token: token,
    });
    if (cursor) params.set("after", cursor);
    let resp, data;
    try {
      resp = await fetch(`https://graph.facebook.com/v22.0/act_${accountId}/insights?${params}`, {
        signal: AbortSignal.timeout(30000),
      });
      data = await resp.json();
    } catch {
      // Não repassa erros de rede que podem conter a URL com token.
      throw new Error(`[${level}] Falha de conexão ou resposta inválida. Tente novamente.`);
    }
    if (!resp.ok || data.error) {
      const code = Number(data.error?.code) || resp.status;
      throw new Error(`[${level}] Meta recusou a consulta (código ${code}). Confira a sessão e as permissões.`);
    }
    if (!Array.isArray(data.data)) throw new Error(`[${level}] Resposta de métricas inválida.`);
    all.push(...data.data);
    if (!data.paging?.next) break;
    cursor = data.paging.cursors?.after;
    if (!cursor || seen.has(cursor)) throw new Error(`[${level}] Paginação inválida; exportação interrompida para evitar dados incompletos.`);
    seen.add(cursor);
  }
  return all;
}
