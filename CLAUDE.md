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
  Plano (não feito): coleta local agendada que envia os artigos ao repositório. Hoje a fonte falha e aparece no aviso da página.
- x.ai/news: 403 (Cloudflare); fonte cadastrada como inativa.
- RSS do YouTube é instável; usa-se a página do canal + oEmbed + descrição.
- Cron do GitHub atrasa horas. O usuário disse (2026-11-01) que o horário não importa, só 1 rodada por dia.
- O repositório é público (decisão do usuário): perfil e fontes ficam visíveis.

## Decisões do usuário
- 2026-11-01: sem link no site pessoal (`lkfrota/lincoln`); sem inscrição automática em newsletters.
- 2026-11-01: reações descritivas (quero mais / útil / já conhecia / fora do foco / fonte fraca) no lugar de
  like/dislike/lido. Substitui a 1ª versão (👍/👎 + "lido"), que misturava tema e fonte.
- 2026-11-01: página com teto de 15 itens; sai o de menor nota para dar vez a novos.

## Próximo passo planejado
`PLANO_FASE2.md` — sugerir fontes novas por citação e sugerir remoção. Começar por volta de 2026-11-12.
