---
projeto: Morar SP
perfil_instagram: morar_sp
nome_exibicao: Dicas de Imóveis SP
nicho: Mercado imobiliário (compra/venda, investimento em imóveis, dados e tendências) + vida e atrações de bairro em SP
publico: ICP misto — ver seção "Público-alvo (ICP)"
---

# Configuração do projeto

## Público-alvo (ICP)

- **50% moradores/visitantes frequentes de bairros específicos** — pessoas que já
  moram perto ou frequentam a região pelas suas atrações (gastronomia, cultura,
  eventos, lazer), potenciais candidatas a morar ali. Este é o pilar dominante:
  o algoritmo deve entregar o conteúdo para quem já circula fisicamente pela
  região retratada.
- **25% investidor pessoa física** — quer diversificar patrimônio via imóveis/FIIs,
  conteúdo mais analítico (dados, comparações, leitura de mercado).
- **25% comprador de primeiro imóvel** — planejando a compra do imóvel próprio,
  conteúdo prático (financiamento, documentação, dicas de compra).
- **Fora do ICP por enquanto:** corretores/profissionais do setor.

Posicionamento do perfil: **friendly e não comercial**. O objetivo agora é
audiência e engajamento — monetização é decisão futura (ver seção
"Monetização").

## Ângulo editorial

Três pilares:

1. **Atrações e vida no bairro** (pilar dominante, ~50% do conteúdo) —
   gastronomia, cultura, eventos, lazer e diferenciais da região em foco do
   momento. A região não é fixa: é escolhida pela etapa 0 do pipeline
   (`scripts/00_selecionar_regiao.py`) com base no nível de interesse atual
   (menções recentes de atração/lifestyle no Google News), revisado a cada 15
   dias. **70% do conteúdo deste pilar vai na região principal, 30% nas
   secundárias** — ver `config/regiao_foco.json` para o estado atual.
2. **Compra/venda de imóveis** (~25%) — corretores, imóvel próprio, dicas práticas.
3. **Investimento imobiliário** (~25%) — FIIs, aluguel, valorização, leitura de mercado.

Fora do escopo por enquanto: construção/reforma/decoração.

## Formato de conteúdo

- Carrossel para Instagram (feed)
- Templates rotativos:
  - "Você sabia" (curiosidade)
  - Comparativo (ex: financiamento vs consórcio)
  - Opinião de mercado (dado + leitura)
- Estilo visual: **variado** (mistura editorial/dados, humor/meme, informativo) — sem fórmula fixa única

## Regra de despersonalização (obrigatória)

Ao processar uma pauta que cite empresa, marca ou imóvel específico:
- **Não bloquear** a pauta
- **Reescrever** removendo o nome da empresa/marca/imóvel, mantendo o dado ou insight genérico
- Exemplo: "Construtora X anunciou reajuste de 8%" → "reajustes de até 8% têm sido registrados no setor"

Também evitar, mesmo de forma genérica:
- Promessas de rentabilidade específicas
- Recomendação direta de compra/investimento (sempre framing informativo, não conselho financeiro)

**Exceção — pilar de atrações e vida no bairro:** nomes de lugares públicos
(parques, praças, festivais, ruas, equipamentos culturais) **não são
despersonalizados** — citar "Festa das Cerejeiras no Parque do Carmo" é o
próprio conteúdo, não uma promoção de marca. A regra de despersonalização
vale para empresas/marcas privadas (construtoras, imobiliárias, restaurantes
específicos como propaganda), não para atrações e espaços públicos do bairro.

## Frequência

- Pesquisa de tendências: **diária**
- Publicação: a definir (sugestão inicial: 1 post/dia)

## Publicação (Instagram Graph API)

- App Meta: "Morar SP"
- Conta Instagram: morar_sp (ID: 17841438460511613)
- Nome do app Instagram: Morar SP-IG (ID: 1296129422598897)
- Status do app: Em desenvolvimento (conta cadastrada como testadora)
- Permissões ativas: instagram_business_basic, instagram_business_manage_comments,
  instagram_business_manage_messages, instagram_business_content_publish (pronto pra teste)
- Business Manager: Meus Garimpinhos

## Monetização (não implementar ainda)

Em aberto entre: venda de espaço publicitário, afiliado/lead, ou venda da conta.
Decisão adiada até o conteúdo mostrar tração.
