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
- **25% investidor pessoa física** — quer comprar imóvel para alugar (renda
  passiva via aluguel, não FIIs/fundos/ações), conteúdo mais analítico
  (rentabilidade, comparações, leitura de mercado).
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
2. **Compra/venda de imóveis** (~25%) — corretores, **imóvel próprio pra morar**,
   dicas práticas de compra/financiamento.
3. **Comprar para alugar** (~25%) — imóvel como investimento de renda (NÃO
   FIIs/fundos/ações): rentabilidade de aluguel, aluguel tradicional vs.
   temporada, custos ocultos de ser proprietário-locador (IPTU, condomínio,
   vacância, manutenção), retorno total (aluguel + valorização), como
   escolher um imóvel bom pra alugar, financiamento de segundo imóvel,
   gestão de inquilino/contrato.

**Diferença entre os pilares 2 e 3:** pilar 2 é sobre comprar pra morar
(o imóvel é onde o comprador vai viver); pilar 3 é sobre comprar pra ser
dono e alugar pra terceiros (o imóvel é fonte de renda).

Fora do escopo por enquanto: construção/reforma/decoração.

## Formato de conteúdo

- Carrossel para Instagram (feed)
- Templates rotativos (escolhidos conforme o pilar da pauta do dia):
  - "Você sabia" (curiosidade) — pilares compra/venda e investimento
  - Comparativo (ex: financiamento vs consórcio) — pilar compra/venda
  - Opinião de mercado (dado + leitura) — pilar investimento
  - "Descubra o bairro" (gancho de atração/evento → convite sutil a conhecer a região) — pilar atrações de bairro
- Estilo visual: **variado** (mistura editorial/dados, humor/meme, informativo) — sem fórmula fixa única

## Regras de redação (obrigatórias)

- **Nunca usar travessão (—)** em nenhum texto gerado (título, slides ou
  legenda). Reescrever a frase ou usar vírgula/ponto no lugar.
- **Estrutura do carrossel**: capa (título geral + corpo) → slides
  intermediários (mini-título obrigatório + corpo opcional) → último slide
  (CTA obrigatório como mini-título — curtir, comentar, compartilhar ou
  salvar, pode ser em forma de pergunta — + corpo opcional).

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

## Publicação (Instagram API — login direto do Instagram)

- App Meta: "Morar SP"
- Conta Instagram: morar_sp (Instagram-scoped User ID: 25952830001081792)
- Host da API: graph.instagram.com (não graph.facebook.com — não é fluxo
  de Facebook Login, é "API do Instagram com login direto")
- Nome do app Instagram: Morar SP-IG (ID: 1296129422598897)
- Status do app: Em desenvolvimento (conta cadastrada como testadora)
- Permissões ativas: instagram_business_basic, instagram_business_manage_comments,
  instagram_business_manage_messages, instagram_business_content_publish (pronto pra teste)
- Business Manager: Meus Garimpinhos

## Monetização (não implementar ainda)

Em aberto entre: venda de espaço publicitário, afiliado/lead, ou venda da conta.
Decisão adiada até o conteúdo mostrar tração.
