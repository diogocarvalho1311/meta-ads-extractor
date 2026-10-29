# Extensão Meta Ads Extractor

A extensão usa a sessão já autenticada do Ads Manager e exporta métricas diárias para um arquivo JSON. Não pede login próprio nem envia dados para um servidor do projeto.

## Fluxo

1. `content.js` procura o recurso `am_tabular` carregado pela página e identifica a sessão da conta ativa.
2. `popup.js` solicita a coleta ao service worker e apresenta o resultado.
3. `background.js` consulta `/v22.0/act_<conta>/insights`, com `time_increment=1`, nos níveis `campaign`, `adset` e `ad`.
4. O popup normaliza a resposta e baixa o JSON, sem incluir o token da sessão no arquivo.

O token é usado em memória e na requisição à Meta. A extensão não o grava em `chrome.storage`. Quem inspeciona o navegador ainda pode observar as requisições da própria sessão; o token deve ser tratado como credencial.

## Instalação e uso

Abra `chrome://extensions`, habilite o Modo do desenvolvedor e carregue esta pasta sem compactação. Abra `https://adsmanager.facebook.com/`, aguarde carregar, selecione o período no popup e exporte. Recarregue a página se instalou a extensão com o Manager já aberto.

Mantenha o popup aberto até o download ser solicitado. Consultas têm limite de 30 segundos por página. Uma falha em qualquer nível impede a criação de um JSON parcial.

## Permissões

| Permissão | Finalidade |
| --- | --- |
| `activeTab` | Interação com a aba ativa ao abrir a extensão |
| `downloads` | Salvar o JSON em Downloads |
| `adsmanager.facebook.com` | Executar o content script no Manager |
| `graph.facebook.com` | Consultar os dados de Insights |

As permissões `storage` e `scripting` foram removidas porque não eram usadas. Não há telemetria nem dependências externas no código da extensão.

## Métricas e períodos

Todos os níveis incluem data, nomes, IDs, impressões, cliques no link, leads e investimento. Campanhas incluem objetivo e visualizações de página; conjuntos incluem alcance, frequência e visualizações de página; anúncios incluem alcance e visualizações de vídeo a 25%. O campo interno `plays` representa essas visualizações a 25%, conforme a consulta atual.

Alcance diário não deve ser somado como alcance único de um período. A extensão exporta registros por dia, e a interpretação dos indicadores deve considerar a granularidade e a atribuição da plataforma.

## Quando algo falhar

- **Sessão não encontrada:** aguarde o Manager carregar os anúncios, confirme a conta e recarregue a aba.
- **Meta recusou a consulta:** verifique a sessão e as permissões; a extensão não remove restrições da conta.
- **Tempo esgotado:** tente um período menor e confirme a conexão.
- **Após atualizar os arquivos:** clique em Recarregar em `chrome://extensions` e recarregue o Manager.
