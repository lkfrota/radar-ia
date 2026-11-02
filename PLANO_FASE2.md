# Fase 2 — sugestão de fontes (planejado em 2026-11-01, execução a partir de ~2026-11-12)

## Gatilho para começar
Pelo menos 10 dias de rodadas e ~40 reações (em `estado/pesos.json`: temas/fontes com peso diferente de zero).
Antes disso não há base: sugerir fonte sem sinal seria chute.

## 1. Sugerir fontes novas (por citação — decidido; busca na web fica descartada por ora)
- Durante a coleta, extrair os domínios dos links citados dentro dos itens com nota alta
  (ou que receberam "Quero mais assim"/"Útil"). Guardar contagem em `estado/citacoes.json`.
- Um domínio vira candidato quando: ≥3 citações em itens bons, não está em `config/fontes.json`,
  não está numa lista de ignorados (redes sociais, github.com, arxiv.org genérico, etc.).
- Para cada candidato, procurar feed RSS (`<link rel="alternate" type="application/rss+xml">`);
  sem feed, marcar "sem RSS (exige leitor de página)".
- Aparece na página Configurar, seção "Fontes sugeridas", com botões **Adicionar** / **Ignorar**.
  Nada entra na lista sem clique do usuário.

## 2. Sugerir retirar fontes
- Fonte com peso ≤ -0.3 (vários "Fonte fraca"), ou com 0 itens publicados em 30 dias,
  aparece em Configurar como "Candidata a remover", com **Remover** / **Manter**.

## 3. O que isto custa
- Sem chamada extra ao Gemini (só contagem e leitura de HTML). Cota diária gratuita é 20 chamadas/modelo.

## Pontos em aberto
- Confirmar que a lista de ignorados cobre o ruído típico (testar com o primeiro `citacoes.json`).
- Decidir se o filtro de relevância das sugestões precisa de IA (provavelmente não no início).
