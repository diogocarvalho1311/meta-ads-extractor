// Content script - roda na página do Meta Ads Manager
// Extrai token + accountId e pede ao background para buscar nomes via Graph API

function getCredentials() {
  const activeAccount = new URL(location.href).searchParams.get("act");
  const entries = performance.getEntriesByType("resource");
  // Entradas recentes primeiro; evita reutilizar a conta anterior ao trocar no Manager.
  for (const entry of entries.slice().reverse()) {
    let url;
    try { url = new URL(entry.name); } catch { continue; }
    if (!url.pathname.includes("am_tabular")) continue;
    const token = url.searchParams.get("access_token");
    const accountId = url.pathname.match(/act_(\d+)/)?.[1];
    if (token && accountId && (!activeAccount || activeAccount === accountId)) {
      return { token, accountId };
    }
  }
  return null;
}

// Expõe função para o popup chamar via chrome.tabs.sendMessage
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id || !msg) return;
  if (msg.type === "GET_CREDENTIALS") {
    const creds = getCredentials();
    sendResponse(creds ? { ok: true, ...creds } : { ok: false, error: "Abra o Ads Manager e aguarde carregar os anúncios" });
  }
});
