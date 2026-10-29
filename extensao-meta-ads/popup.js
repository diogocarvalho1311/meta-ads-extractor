const statusEl = document.getElementById("status");

function setStatus(msg, type = "") {
  statusEl.textContent = msg;
  statusEl.className = type;
}

function getAction(actions, type) {
  return parseInt(actions?.find(a => a.action_type === type)?.value || "0");
}

function getLeads(actions) {
  return getAction(actions, "lead")
    || getAction(actions, "onsite_conversion.lead_grouped");
}

// /insights retorna campos planos (sem sub-objeto insights)
function parseCampanhas(raw) {
  return raw.map(c => {
    const cli = getAction(c.actions, "link_click");
    const pv  = getAction(c.actions, "landing_page_view");
    return {
      date: c.date_start,
      nome: c.campaign_name,
      impressoes: parseInt(c.impressions || 0),
      cliques: cli,
      pv,
      leads: getLeads(c.actions),
      gasto: parseFloat(c.spend || 0),
      objetivo: c.objective || "",
      id: c.campaign_id,
    };
  });
}

function parseConjuntos(raw) {
  return raw.map(c => {
    const cli = getAction(c.actions, "link_click");
    const pv  = getAction(c.actions, "landing_page_view");
    return {
      date: c.date_start,
      campanha: c.campaign_name,
      nome: c.adset_name,
      impressoes: parseInt(c.impressions || 0),
      alcance: parseInt(c.reach || 0),
      cliques: cli,
      frequencia: parseFloat(c.frequency || 0),
      pv,
      leads: getLeads(c.actions),
      gasto: parseFloat(c.spend || 0),
      campaign_id: c.campaign_id,
      id: c.adset_id,
    };
  });
}

function parseAnuncios(raw) {
  return raw.map(a => {
    const cli   = getAction(a.actions, "link_click");
    const plays = getAction(a.video_p25_watched_actions, "video_view");
    return {
      date: a.date_start,
      campanha: a.campaign_name,
      conjunto: a.adset_name,
      nome: a.ad_name,
      impressoes: parseInt(a.impressions || 0),
      alcance: parseInt(a.reach || 0),
      cliques: cli,
      plays,
      leads: getLeads(a.actions),
      gasto: parseFloat(a.spend || 0),
      campaign_id: a.campaign_id,
      adset_id: a.adset_id,
      id: a.ad_id,
    };
  });
}

async function getTabAndCreds() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url || new URL(tab.url).origin !== "https://adsmanager.facebook.com") {
    return { error: "Abra o Meta Ads Manager primeiro." };
  }
  let creds;
  try {
    creds = await chrome.tabs.sendMessage(tab.id, { type: "GET_CREDENTIALS" });
  } catch {
    return { error: "Erro ao contatar a página. Recarregue o Ads Manager." };
  }
  if (!creds?.ok) return { error: creds?.error || "Credenciais não encontradas." };
  return { tab, creds };
}

function bindAction(id, action) {
  document.getElementById(id).addEventListener("click", async () => {
    const controls = document.querySelectorAll("button, select");
    controls.forEach(control => { control.disabled = true; });
    try {
      await action();
    } catch {
      setStatus("Não foi possível concluir. Confira a conexão e recarregue o Ads Manager para tentar novamente.", "err");
    } finally {
      controls.forEach(control => { control.disabled = false; });
    }
  });
}

bindAction("btn-test", async () => {
  const datePreset = document.getElementById("date-preset").value;
  setStatus("Buscando credenciais...");

  const { creds, error } = await getTabAndCreds();
  if (error) { setStatus(error, "err"); return; }

  setStatus(`Account ${creds.accountId} OK.\nBuscando métricas (${datePreset})...`);

  const result = await chrome.runtime.sendMessage({
    type: "FETCH_ADS_WITH_METRICS",
    accountId: creds.accountId,
    token: creds.token,
    datePreset,
  });

  if (!result?.ok) { setStatus("Erro na Graph API:\n" + result?.error, "err"); return; }

  const ads = parseAnuncios(result.ads);

  setStatus(
    `Sucesso! ${ads.length} anúncio(s) com dados.\n` +
    `\nPrimeiros 3:\n` +
    ads.slice(0, 3).map(a =>
      `• ${a.nome}\n  imp:${a.impressoes} leads:${a.leads} R$${a.gasto}`
    ).join("\n"),
    "ok"
  );
});

bindAction("btn-export", async () => {
  const datePreset = document.getElementById("date-preset").value;
  setStatus("Buscando todos os níveis (campanhas, conjuntos, anúncios)...");

  const { creds, error } = await getTabAndCreds();
  if (error) { setStatus(error, "err"); return; }

  const result = await chrome.runtime.sendMessage({
    type: "FETCH_ALL_METRICS",
    accountId: creds.accountId,
    token: creds.token,
    datePreset,
  });

  if (!result?.ok) { setStatus("Erro:\n" + result?.error, "err"); return; }

  const payload = {
    accountId: result.accountId,
    datePreset: result.datePreset,
    campanhas: parseCampanhas(result.campanhas),
    conjuntos: parseConjuntos(result.conjuntos),
    anuncios: parseAnuncios(result.anuncios),
  };

  const nc = payload.campanhas.length;
  const nj = payload.conjuntos.length;
  const na = payload.anuncios.length;

  // Salva como arquivo JSON na pasta Downloads
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url  = URL.createObjectURL(blob);

  const CLIENT_NAMES = {
    "1111111111111111": "lucri",
    "222222222222222":  "cwbkids",
  };
  const cliente = CLIENT_NAMES[payload.accountId] || payload.accountId;

  const hoje = new Date().toISOString().slice(0, 10).replace(/-/g, "");

  // Período: usa as datas reais dos dados quando disponíveis
  const allDates = [...(payload.campanhas || []), ...(payload.conjuntos || []), ...(payload.anuncios || [])]
    .map(x => x.date).filter(Boolean).sort();
  let periodo;
  if (allDates.length) {
    const ini = allDates[0].replace(/-/g, "");
    const fim = allDates[allDates.length - 1].replace(/-/g, "");
    periodo = ini === fim ? ini : `${ini}-${fim}`;
  } else {
    periodo = payload.datePreset || "periodo";
  }

  const filename = `meta_${cliente}_${hoje}_${periodo}.json`;
  try {
    await chrome.downloads.download({ url, filename, saveAs: false });
  } finally {
    URL.revokeObjectURL(url);
  }

  setStatus(
    `Salvo em Downloads!\n${nc} campanhas · ${nj} conjuntos · ${na} anúncios\n\nArquivo: ${filename}\n\nAgora rode:\npython scripts/meta_from_extension.py`,
    "ok"
  );
});
