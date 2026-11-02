# radar-ia — contexto para sessões futuras

Digest diário de novidades em IA, filtrado pelo perfil do Lincoln. Código aqui; páginas publicadas em
https://lkfrota.github.io/radar-ia/ (GitHub Pages, pasta `docs/`). Rodada diária: `.github/workflows/diario.yml`.
Visão geral e decisões da conversa de criação (2026-10-29 a 2026-11-01) resumidas abaixo.

## Como funciona
coletar (`src/coletar.py`) → triagem em lote (`pontuar.py`) → seleção por cotas e redação (`montar.py`)
→ HTML (`templates/`, `main.py`). Reações do usuário viram arquivos em `feedback/` (gravados pela página
via token no navegador) e são aplicadas na rodada seguinte por `pesos.py`. `RADAR_FAKE=1` roda sem chave.
Estado em `estado/` (vistos, pendentes, pesos). Perfil e fontes editáveis em `config/` ou na página Configurar.

## Fatos não óbvios (não redescobrir)
- Gemini grátis: **20 chamadas/dia por modelo**. Triagem e redação usam o modelo lite; Flash completo deu 504/503.
- Leitura de vídeo pelo Gemini é lenta e instável: no máximo 1 por dia, 1 tentativa. Os demais usam a descrição do vídeo.
- **The Batch dá 403 nos servidores do GitHub** (IP de nuvem), em qualquer endereço. Funciona na máquina do usuário.
  Solução (2026-11-02): `local/coletar_batch.py` roda no computador dele (timer systemd às 13h — mudado de 6h em 2026-11-02 —, `local/instalar_timer.sh`,
  instalado pelo usuário) e grava `entradas/the-batch.json`, lido como fonte do tipo `arquivo`.
- x.ai/news: 403 (Cloudflare); fonte cadastrada como inativa.
- RSS do YouTube é instável; usa-se a página do canal + oEmbed + descrição.
- Cron do GitHub atrasa horas. O usuário disse (2026-11-01) que o horário não importa, só 1 rodada por dia.
- O repositório é público (decisão do usuário): perfil e fontes ficam visíveis.

## Decisões do usuário
- 2026-11-01: sem link no site pessoal (`lkfrota/lincoln`); sem inscrição automática em newsletters.
- 2026-11-01: reações descritivas (quero mais / útil / já conhecia / fora do foco) no lugar de
  like/dislike/lido. Substitui a 1ª versão (👍/👎 + "lido"), que misturava tema e fonte.
- 2026-11-02: removido o botão "Fonte fraca" (julgar a fonte por um item é injusto). A fonte recebe só uma fração
  do sinal das outras reações (`pesos.py`, EFEITOS); sua qualidade emerge do acúmulo. Substitui a opção de 2026-11-01.
- 2026-11-01: página com teto de 15 itens; sai o de menor nota para dar vez a novos.

## Próximo passo planejado
`PLANO_FASE2.md` — sugerir fontes novas por citação e sugerir remoção. Começar por volta de 2026-11-12.

## Estado ao encerrar a sessão de criação (2026-11-02)
- **Verificado:** coleta de todas as fontes; rodadas reais na nuvem em 30/10, 31/10 e 01/11 terminaram bem; reações
  novas ("Útil") chegam ao repositório; timer local instalado e a coleta de teste do The Batch chegou ao GitHub.
- **Não verificado:** (1) a página nunca foi vista num navegador por mim (capturas de tela deram timeout; só HTML e
  sintaxe do `app.js` foram conferidos; o usuário a usa e não relatou defeito); (2) a primeira rodada na nuvem com a versão
  final (The Batch por arquivo, 4 reações, teto de 15) — acontece depois de 2026-11-02; conferir o log se a página estranhar.
- **Pendente de decisão do usuário:** mover o cron da nuvem (hoje 9:17 UTC, atrasa horas) para depois das 13h de Brasília
  (~16:30 UTC) para o artigo do The Batch chegar no mesmo dia; hoje chega com 1 dia de atraso. xAI: recomendei não coletar
  (403 também na máquina dele; cobertura indireta por HN/Anthropic/The Batch); ele não decidiu em contrário.
- **Pendências de método (não feitas):** (a) a triagem em `pontuar.py` é exatamente o caso "IA que só produz decisão"
  da lista de ferramentas em avaliação do CLAUDE.md global (Jev, ver `~/.claude/referencias/jev-typesafe.md`); a sessão
  de criação não levou isso ao usuário. Comparar exigiria conta de API (Haiku) que ele não tem. (b) `GEMINI_MODEL*` usam aliases
  `-latest` e a rodada não registra modelo nem versão do prompt: o método de maturidade (`~/.claude/referencias/maturidade-de-projetos-com-ia.md`)
  pede registrar isso desde o início; fixar os modelos e gravar modelo/prompt por rodada em `estado/`.
- **Próximo passo:** `PLANO_FASE2.md` por volta de 2026-11-12 (o usuário dispensou lembrete: ele abre sessão aqui).
