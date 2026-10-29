# Roteiro de apresentação

## Abertura — 30 segundos

“Desenvolvi uma automação para reduzir o trabalho manual de consolidar métricas de tráfego pago. A peça principal é uma extensão Chrome que parte da sessão do Ads Manager, exporta campanhas, conjuntos e anúncios por dia e alimenta um fluxo de importação e análise.”

## Diferencial — 30 segundos

“Quando não tinha disponível a configuração de uma integração própria com a Meta, adaptei o fluxo para usar a sessão autenticada do navegador. Não preciso configurar um app próprio ou copiar um token manualmente. Tecnicamente, a extensão ainda consulta a Graph API e respeita o acesso que a conta tem.”

## Demonstração — 1 minuto

1. Execute `python demo.py` e abra o endereço local indicado.
2. Mostre a aba Meta Ads, os indicadores e o filtro de período. Use outubro de 2026 para esta amostra.
3. Abra `examples/meta-demo.json` e mostre as três listas: campanhas, conjuntos e anúncios.
4. Explique que o painel Python recebe esse formato e coordena a gravação em Sheets ou D1.

Para mostrar a extensão de verdade, use somente uma conta autorizada. Aguarde a exportação terminar com o popup aberto. Evite gravar a tela de credenciais, ferramentas de rede ou dados reais dos clientes.

## Engenharia — 30 segundos

“Separei coleta, transformação, armazenamento e visualização. A extensão pagina os resultados e evita exportações incompletas em caso de erro. O projeto inclui testes com dados simulados e SQLite em memória. Para o portfólio, separei o código dos dados operacionais e preparei uma demo sem credenciais.”

Não apresente números da demonstração como resultados comerciais reais. A demo mostra a experiência de consulta; não executa a coleta da Meta nem as integrações externas.
