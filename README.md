# Morar SP — Perfil automatizado de Instagram (imobiliário)

Pipeline de conteúdo 100% automatizado para o perfil `@morar_sp` ("Dicas de
Imóveis SP"), cobrindo pesquisa de tendências, geração de conteúdo e
publicação via Instagram Graph API.

## Status: em construção (experimento)

## Fluxo

```
00_selecionar_regiao.py → 01_pesquisar.py → 02_gerar_copy.py → 03_gerar_visual.py → 04_publicar.py
```

Orquestrado por `run_diario.py`.

## Configuração

1. Copie `.env.example` para `.env` e preencha os tokens/chaves (Instagram,
   `ANTHROPIC_API_KEY` e `UNSPLASH_ACCESS_KEY` — opcional, sem ela o
   carrossel cai pro fundo sólido de cor)
2. Instale dependências: `pip install -r requirements.txt`
3. Instale o navegador do Playwright (usado pela etapa 3 pra renderizar os slides): `playwright install chromium`
4. Clone o repositório `morar-sp-midia` como pasta irmã deste projeto (ou
   ajuste `MIDIA_REPO_PATH` no `.env`) — é onde as imagens do carrossel são
   hospedadas publicamente (raw.githubusercontent.com) pra Graph API conseguir
   buscá-las
5. Regras de conteúdo e tom estão em `config/config.md`

## Estrutura

- `config/` — regras do projeto (nicho, tom, despersonalização)
- `pesquisa/` — output diário da pesquisa de tendências
- `conteudo/` — copy e imagens geradas por dia
- `scripts/` — lógica de cada etapa do pipeline
- `logs/` — histórico de publicações
