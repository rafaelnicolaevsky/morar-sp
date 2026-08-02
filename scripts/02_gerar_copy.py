"""
Etapa 2: Geração de texto/copy do post a partir da pauta pesquisada.

Responsável por:
- Ler a pesquisa do dia (pesquisa/tendencias-YYYY-MM-DD.md) e dividi-la por pilar
  (atrações de bairro / compra-venda / investimento)
- Sortear o pilar do post de hoje, respeitando o mix do ICP (50/25/25 —
  ver config/config.md), com fallback para outro pilar se o sorteado não
  tiver pauta disponível
- Gerar o copy via API da Anthropic, seguindo o template do pilar
- Aplicar a regra de despersonalização (segunda chamada de revisão) — ver
  config/config.md
- Salvar o copy gerado em conteudo/posts-YYYY-MM-DD/copy.md
"""

import os
import random
import re
import sys
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.utils.formato import escolher_formato_post
from scripts.utils.historico_temas import temas_recentes_para_prompt
from scripts.utils.selecao_pauta import carregar_ou_selecionar_pauta_do_dia

load_dotenv()

MODELO = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
# Teto de output enxuto — o post inteiro (título + slides + legenda +
# metadados) cabe bem dentro disso depois do corte de capa/slides
# intermediários. thinking fica desligado nas duas chamadas (thinking vem
# ligado por padrão na claude-sonnet-5 e consumiria esse teto sem gerar
# texto de saída) — seguro aqui porque não há uso de tools, só texto.
# 1024 truncou de verdade num teste real (seção "## Viés" cortada no meio);
# 1536 dá a margem que faltava sem perder a economia (ainda ~98,8% menor
# que o teto de 128000 tokens da API).
MAX_TOKENS_TETO = 1536

TEMPLATES_POR_PILAR = {
    "atracao": ["descubra_bairro", "achado_local"],
    "compra_venda": ["voce_sabia", "comparativo", "dica_pratica"],
    "investimento": ["voce_sabia", "opiniao_de_mercado", "dica_pratica"],
}
# Templates que NÃO dependem de pauta pesquisada — geram conteúdo evergreen
# direto (guia prático, listicle). Mantêm o pilar disponível mesmo em dias
# sem nenhuma notícia/pauta relevante encontrada.
TEMPLATES_SEM_PAUTA = {"dica_pratica"}

TEMPLATE_INSTRUCOES = {
    "voce_sabia": (
        "Formato 'Você sabia': abre com uma curiosidade ou dado surpreendente sobre "
        "o tema, expande com 2-4 slides de contexto, fecha com uma reflexão ou "
        "pergunta pro público."
    ),
    "comparativo": (
        "Formato comparativo: compara duas opções relacionadas ao tema (ex: "
        "financiamento vs consórcio, comprar vs alugar). 1 slide de introdução, "
        "2-3 slides comparando lado a lado, 1 slide de conclusão neutra — sem "
        "recomendar uma opção."
    ),
    "opiniao_de_mercado": (
        "Formato opinião de mercado: apresenta um dado/tendência recente do setor "
        "e uma leitura do que isso significa pro público. Framing informativo, "
        "nunca recomendação de investimento. Se o dado/gancho vier de outra cidade "
        "(ex.: um dado do Rio de Janeiro), use só como abertura rápida — o grosso "
        "do post (a maioria dos slides e a conclusão) precisa ser sobre o "
        "equivalente em São Paulo, não sobre a cidade de origem do dado."
    ),
    "descubra_bairro": (
        "Formato 'Descubra o bairro': abre com um gancho sobre a atração/evento/"
        "lugar do bairro em foco, 2-3 slides mostrando por que vale a pena "
        "conhecer/curtir essa região, fecha conectando (de forma sutil, sem tom "
        "de venda) com a ideia de morar por perto."
    ),
    "achado_local": (
        "Formato 'Achado local': destaca um estabelecimento/lugar/evento ESPECÍFICO "
        "do bairro em foco que está em alta ou vale a pena conhecer (ex.: "
        "'hamburgueria da Zona Leste com tema retrô atrai fila nos fins de semana', "
        "'até 30/08, churrascaria X promove rodízio kids grátis'). Abre com o "
        "gancho concreto (nome do TIPO de lugar + diferencial, sem inventar nome "
        "de marca privada — aplica despersonalização normalmente), 2-3 slides "
        "mostrando o que torna esse lugar/ação especial, fecha conectando com a "
        "vida no bairro. Se a pauta trouxer prazo/data de validade de uma "
        "promoção, cite — nunca invente prazo que a pauta não deu."
    ),
    "dica_pratica": (
        "Formato 'dica prática' — LISTICLE EVERGREEN, não depende de notícia/pauta "
        "do dia: gere de 3 a 5 dicas práticas, específicas e acionáveis sobre o "
        "tema do pilar (ex.: negociar preço de venda de imóvel, documentação de "
        "compra, como avaliar se o aluguel está caro, sinais de que vale renegociar "
        "o financiamento, o que olhar antes de comprar pra alugar). Título com "
        "número (ex.: '5 dicas pra...', 'como saber se..'). Cada slide intermediário "
        "= 1 dica objetiva, sem enrolação — precisa ser útil o bastante pra alguém "
        "salvar mesmo sem contexto de notícia nenhuma."
    ),
}

TEMPLATES = ["voce_sabia", "comparativo", "opiniao_de_mercado", "descubra_bairro", "achado_local", "dica_pratica"]

# Frameworks de copywriting pra legenda (caption) — cada um baseado em
# retórica/heurística de decisão validada, não fórmula genérica. Objetivo:
# se o CTA pede pra ler a legenda, a legenda precisa entregar conteúdo de
# verdade, não um teaser vazio.
FRAMEWORKS_POR_PILAR = {
    "atracao": ["curiosidade_fechada", "antes_depois_ponte", "reciprocidade"],
    "compra_venda": ["dado_mecanismo_relevancia", "pas", "reciprocidade"],
    "investimento": ["dado_mecanismo_relevancia", "pas"],
}
FRAMEWORK_LEGENDA_INSTRUCOES = {
    "pas": (
        "Framework PAS — Problema, Agitação, Solução (base: aversão à perda). "
        "1) Nomeie o problema ou dado central do post. 2) Agitação: explique "
        "por que isso importa de verdade — o mecanismo por trás, não só o "
        "fato. 3) Feche com a implicação prática pro leitor. Não invente "
        "solução mágica, o objetivo é explicar, não vender."
    ),
    "dado_mecanismo_relevancia": (
        "Framework Dado → Mecanismo → Relevância (base: necessidade de "
        "fechamento cognitivo). 1) Retome o dado/gancho central do post. "
        "2) Explique O PORQUÊ por trás dele — a causa, o mecanismo real "
        "(isso é obrigatório: nunca deixe o 'porquê' apenas insinuado ou "
        "subentendido). 3) Traduza pra relevância prática de quem lê."
    ),
    "curiosidade_fechada": (
        "Framework Loop de Curiosidade Fechado (base: efeito Zeigarnik / "
        "curiosity gap). Abra com uma pergunta ou lacuna de informação, mas "
        "RESPONDA por completo dentro da própria legenda — nunca deixe a "
        "resposta dependendo de reler os slides ou ficando só implícita."
    ),
    "antes_depois_ponte": (
        "Framework Antes-Depois-Ponte / BAB (base: contraste e ancoragem). "
        "1) Antes: como a região/situação era vista ou o que parecia. "
        "2) Depois: o que mudou, o que foi descoberto ou o que está "
        "rolando agora. 3) Ponte: o que isso significa pra quem lê (ex.: "
        "quem mora perto, quem pensa em se mudar)."
    ),
    "reciprocidade": (
        "Framework Reciprocidade (base: princípio de Cialdini). Entregue um "
        "insight ou dica de valor real ANTES do CTA — quem ler precisa sair "
        "sabendo algo útil mesmo sem interagir. O CTA vem como continuação "
        "natural do valor entregue, nunca como pedido isolado e vazio."
    ),
}


def ler_pesquisa_do_dia() -> str:
    """Lê o arquivo de pesquisa gerado na etapa 1."""
    hoje = date.today().isoformat()
    caminho = f"pesquisa/tendencias-{hoje}.md"
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def _dividir_por_pilar(pesquisa_md: str) -> dict[str, str]:
    """Agrupa as seções (## título) da pesquisa do dia por pilar editorial."""
    partes = re.split(r"(?m)^## (.+)$", pesquisa_md)
    pares = list(zip(partes[1::2], partes[2::2]))  # (titulo_secao, corpo_secao)

    blocos: dict[str, list[str]] = {"atracao": [], "compra_venda": [], "investimento": []}
    for titulo, corpo in pares:
        if titulo.startswith("Atrações e vida no bairro"):
            blocos["atracao"].append(corpo.strip())
        elif titulo.startswith("Compra/venda e mercado imobiliário") or titulo.startswith("Mercado geral"):
            blocos["compra_venda"].append(corpo.strip())
        elif titulo.startswith("Investimento"):
            blocos["investimento"].append(corpo.strip())

    return {pilar: "\n\n".join(corpos) for pilar, corpos in blocos.items()}


def _secao_tem_conteudo(corpo: str) -> bool:
    """Uma seção só tem conteúdo real se sobrar alguma linha que não seja o placeholder '_..._'."""
    linhas_uteis = [
        linha for linha in corpo.strip().splitlines()
        if linha.strip() and not re.fullmatch(r"_.+_", linha.strip())
    ]
    return len(linhas_uteis) > 0


def _pilar_disponivel(pilar: str, secoes: dict[str, str]) -> bool:
    """Um pilar segue disponível mesmo sem pauta do dia, se tiver template evergreen (ver TEMPLATES_SEM_PAUTA)."""
    if _secao_tem_conteudo(secoes.get(pilar, "")):
        return True
    return any(t in TEMPLATES_SEM_PAUTA for t in TEMPLATES_POR_PILAR[pilar])


def selecionar_template(pilar: str, secoes: dict[str, str]) -> tuple[str, bool]:
    """
    Sorteia o template dentro do pilar já decidido pela seleção de pauta
    do dia (ver utils/selecao_pauta.py — o pilar não é mais sorteado
    aqui). Retorna também `tem_pauta` — quando False, o template
    sorteado é sempre um dos evergreen (TEMPLATES_SEM_PAUTA), e a pauta
    passada pro modelo fica vazia.
    """
    tem_pauta = _secao_tem_conteudo(secoes.get(pilar, ""))
    if not tem_pauta and not _pilar_disponivel(pilar, secoes):
        raise RuntimeError(f"Pilar '{pilar}' sem pauta e sem template evergreen disponível hoje.")

    templates_possiveis = (
        TEMPLATES_POR_PILAR[pilar] if tem_pauta
        else [t for t in TEMPLATES_POR_PILAR[pilar] if t in TEMPLATES_SEM_PAUTA]
    )
    template = random.choice(templates_possiveis)
    return template, tem_pauta


def _bloco_historico_temas() -> str:
    historico = temas_recentes_para_prompt()
    if not historico:
        return "(nenhum post publicado ainda)"
    linhas = []
    for h in historico:
        extra = ""
        if h.get("categoria"):
            extra = f", categoria: {h['categoria']}"
        elif h.get("vies_estrutural"):
            extra = f", viés estrutural: {h['vies_estrutural']}"
        if h.get("bairro_alvo"):
            extra += f", bairro: {h['bairro_alvo']}"
        linhas.append(f"- tema: {h['tema']} | viés: {h['vies']} (pilar: {h['pilar']}{extra}, {h['data']})")
    return "\n".join(linhas)


def _instrucao_categoria_ou_vies(pauta: dict) -> str:
    """
    Instrução explícita do ângulo de hoje — categoria (pilar atração) ou
    viés estrutural (pilares de imóveis) — pedido do usuário, 01/08/2026:
    escrever de fato do ponto de vista certo (ex.: comprador vs vendedor),
    não deixar o modelo decidir livremente.
    """
    bairro_alvo = pauta["bairro_alvo"]
    if pauta["pilar"] == "atracao":
        categoria = pauta["categoria"]
        return (
            f"Categoria de hoje: **{categoria}**. Bairro-alvo: **{bairro_alvo}** "
            f"(escolhido por ter afinidade real com {categoria}, não é aleatório). "
            f"O post precisa ser genuinamente sobre {categoria} nesse bairro — "
            f"não misture com outra categoria (ex.: se a categoria é gastronomia, "
            f"não vire um post sobre um museu do bairro)."
        )

    vies = pauta["vies_estrutural"]
    rotulos = {
        "comprador": "ponto de vista de quem está COMPRANDO o primeiro imóvel",
        "vendedor": "ponto de vista de quem está VENDENDO um imóvel",
        "investidor_aluguel": "ponto de vista de quem investe pra RENDA VIA ALUGUEL (não FII/fundo/ação)",
        "investidor_valorizacao": "ponto de vista de quem investe mirando VALORIZAÇÃO do imóvel no tempo",
    }
    return (
        f"Viés estrutural de hoje: escreva do {rotulos[vies]}. Bairro-alvo: "
        f"**{bairro_alvo}** (escolhido por ter afinidade real com esse perfil "
        f"de público). Todo o post — capa, slides e legenda — precisa manter "
        f"esse ponto de vista específico, não o genérico do pilar."
    )


def _montar_prompt_sistema(template: str, pilar: str, tem_pauta: bool, formato: str, pauta_do_dia: dict) -> str:
    with open("config/config.md", "r", encoding="utf-8") as f:
        regras_projeto = f.read()

    instrucao_pauta = (
        "A partir da pauta fornecida"
        if tem_pauta
        else "Este template é EVERGREEN — não há pauta/notícia do dia pra esse "
             "post, gere o conteúdo direto do zero, com base em conhecimento "
             "geral confiável do nicho (nunca invente dado estatístico "
             "específico tipo 'X% dos compradores...' sem fonte real)"
    )

    instrucao_formato = (
        "O post de hoje vai ao ar como IMAGEM ÚNICA — só a capa (slide 1) é "
        "publicada, os outros slides não aparecem pra quem vê o post. Por "
        "isso o corpo da capa (ver instrução do slide 1 abaixo) fica bem "
        "curto, só um gancho de curiosidade — TODO o desenvolvimento real "
        "(o raciocínio, os pontos, o contexto) mora exclusivamente na "
        "legenda. Por isso a legenda precisa ser MAIOR, DETALHADA e "
        "EXPLICATIVA: 3 a 5 parágrafos curtos e separados, cobrindo o "
        "conteúdo completo que num carrossel ficaria espalhado pelos "
        "slides intermediários — sem a legenda, ninguém teria acesso a "
        "esse conteúdo, então não economize substância nela."
        if formato == "imagem_unica"
        else "O post de hoje vai ao ar como CARROSSEL — o conteúdo (os "
             "pontos, o raciocínio) já é explicado ao longo dos slides. A "
             "legenda pode ser MENOR (2 a 3 parágrafos curtos), sem repetir "
             "o carrossel inteiro: foca em complementar com contexto e nas "
             "palavras-chave de SEO."
    )

    return f"""Você escreve o conteúdo do perfil de Instagram @morar_sp.

Regras do projeto (config/config.md):
{regras_projeto}

{_instrucao_categoria_ou_vies(pauta_do_dia)}

Temas e viés JÁ PUBLICADOS — não repita a mesma combinação tema+viés. O
tema pode voltar a aparecer (é normal um nicho ter temas recorrentes, tipo
"valorização por transporte"), mas o VIÉS (o ângulo específico, o que a
pauta de hoje diz de diferente sobre esse tema) precisa ser outro:
{_bloco_historico_temas()}

Formato do post: carrossel de Instagram. {instrucao_pauta}, gere
entre 4 e 7 slides, com esta estrutura fixa:

- **Slide 1 (capa)**: usa o título geral do carrossel (a ideia central) +
  um corpo de até {30 if formato != "imagem_unica" else 15} palavras (ou ~{120 if formato != "imagem_unica" else 60}
  caracteres). Esse corpo AMPLIA a visão que o título já apresentou (mais
  contexto, mais stakes, por que isso importa agora) — ele NUNCA responde
  ou resolve o que o título colocou; a resposta/desenvolvimento fica
  {"pra legenda (é o ÚNICO lugar onde ela existe nesse formato)" if formato == "imagem_unica" else "pros slides seguintes e pra legenda"}.
  {"Nesse formato a imagem tem só um objetivo: gerar curiosidade suficiente pra fazer quem vê querer ler a legenda — quanto mais econômico e intrigante, melhor, sem virar telegráfico a ponto de não fazer sentido sozinho." if formato == "imagem_unica" else "Precisa ter substância real (curiosidade, tensão, um dado), nunca uma frase telegráfica de poucas palavras."}
- **Slides intermediários (do 2º ao penúltimo)**: SÓ o MINI-TÍTULO
  obrigatório (curto, poucas palavras) — SEM corpo, nenhuma linha de
  texto abaixo do mini-título. O slide 2 especificamente NÃO pode repetir
  a ideia da capa: ele é o próximo passo do raciocínio (uma provocação,
  uma pergunta que cria tensão, ou o primeiro elo de uma sequência
  lógica). Cada mini-título seguinte avança um passo novo do argumento —
  a sequência de mini-títulos, lida sozinha (sem nenhum corpo), já precisa
  contar a lógica do post do início ao fim.
- **Último slide**: mini-título é um CTA obrigatório — chame pra curtir,
  comentar, compartilhar ou salvar o post. Pode vir como pergunta pra
  encaixar o CTA de forma mais natural (ex.: "Já foi? Salva esse post pra
  quando for" / "Mora por perto? Comenta aqui"). Corpo opcional e, se
  usado, curto. O CTA precisa fazer sentido com o que o post REALMENTE
  desenvolveu — nunca um CTA genérico ou desconectado do conteúdo (ex.:
  chamar pra "salvar as dicas" só faz sentido se o post de fato listou
  dicas).

Coerência: o post inteiro (capa → slides → CTA → legenda) segue uma
sequência lógica de raciocínio, sem saltos — cada parte constrói em cima
da anterior, do gancho da capa até o fechamento da legenda.

Foco geográfico: São Paulo (a cidade em geral ou um bairro/região
específica) é sempre a PROTAGONISTA do post — é o que faz o algoritmo do
Instagram entregar o conteúdo pra audiência certa. Se a pauta usa outra
cidade como gancho ou comparação (ex.: um dado do Rio de Janeiro), essa
outra cidade pode aparecer como contexto breve, mas o post não pode ficar
com mais espaço dedicado a ela do que a São Paulo — o argumento central,
a maior parte dos slides e a conclusão sempre voltam o foco pra SP.

Template desta pauta: {TEMPLATE_INSTRUCOES[template]}

Além disso, gere uma legenda (caption) do post — ela precisa ser rica em
conteúdo de verdade, não um teaser vazio: se o CTA do post pede pra ler a
legenda, salvar ou comentar, quem ler precisa sair sabendo algo que os
slides sozinhos não cobriram por completo. Regra especialmente importante
quando o post explica um dado/tendência (ex.: "aluguel subiu X%"): a
legenda é o lugar de explicar o PORQUÊ por trás do dado, não só repetir o
fato.

Escolha, entre os frameworks de copywriting abaixo, qual se encaixa MELHOR
na pauta específica de hoje (não escolha por padrão/hábito — analise o que
a pauta realmente pede: tem um dado a explicar? uma lacuna de curiosidade
pra fechar? um contraste antes/depois? algo pra dar de valor antes do CTA?):

{chr(10).join(f"- **{nome}**: {instrucao}" for nome, instrucao in FRAMEWORK_LEGENDA_INSTRUCOES.items() if nome in FRAMEWORKS_POR_PILAR[pilar])}

{instrucao_formato}

Legenda: coerente com o framework escolhido, e com SUBSTÂNCIA de verdade.
Estruture em parágrafos CURTOS (1-2 frases cada), cada um avançando uma
ideia — nunca um bloco denso. Não alongue por alongar; corte qualquer
frase que não agregue. Sempre termine com um CTA explícito (curtir,
comentar, compartilhar ou salvar) antes das hashtags — mesmo no
carrossel, que já tem CTA no último slide, repita brevemente na legenda.

Formatação da legenda: uma linha em branco entre cada parágrafo, pra ficar
escaneável e fácil de ler rápido no feed.

SEO/algoritmo: o Instagram indexa o TEXTO da legenda pra busca e
recomendação — inclua naturalmente (nunca forçado/robótico) os termos que
alguém pesquisaria pra achar esse post: tipo de imóvel + bairro/região +
ação (ex.: "alugar apartamento na Vila Mariana", "comprar imóvel na Zona
Leste", "financiamento imobiliário SP"). Pelo menos 1-2 dessas combinações
devem aparecer no corpo da legenda (não só nas hashtags) — isso é o que
faz o post aparecer pra quem busca ativamente por esse assunto, não só pra
quem já segue o perfil.

Hashtags: de 3 a 5, relacionadas ao contexto real do post — combine
bairro/região + tema + pilar ({pilar}) + o assunto específico do
conteúdo (ex.: uma do bairro citado, uma do tema central, uma do
pilar/nicho, uma do ângulo/viés de hoje) — nunca hashtags redundantes que
dizem basicamente a mesma coisa. Sem tom comercial. IMPORTANTE: as
hashtags vão como a ÚLTIMA linha dentro da própria seção "## Legenda"
(mesmo bloco de texto, não uma seção nova) — nunca esqueça de incluí-las,
isso é parte obrigatória da legenda.

Por fim, gere 3-5 palavras-chave EM INGLÊS pra buscar uma foto de fundo no
Unsplash que combine com o ASSUNTO ESPECÍFICO do post (não um termo genérico
de "São Paulo" ou do pilar) — ex.: se o post é sobre a Festa das Cerejeiras
no Parque do Carmo, use algo como "cherry blossom park festival", não
"são paulo city". Se o post for sobre FIIs, algo como "real estate fund
building" em vez de "finance". Pense no assunto real da pauta.

Declare também, de forma explícita e curta:
- "Tema": o assunto central do post (ex.: "valorização por transporte
  público", "Festa das Cerejeiras no Parque do Carmo") — pode se repetir
  com outros posts ao longo do tempo, é só uma etiqueta do assunto.
- "Viés": o ângulo específico de hoje sobre esse tema (ex.: "o metrô
  valoriza, mas o barulho da obra desvaloriza no curto prazo" é diferente
  de "quem compra antes do metrô abrir historicamente sai ganhando") —
  este é o que NÃO pode repetir a combinação com o tema (ver histórico
  acima).
- "Destaque do título": 1 a 3 palavras — copiadas EXATAMENTE como aparecem
  no título geral (mesma grafia/acentuação) — que são a palavra ou
  palavras mais importantes do título, pra receberem cor de destaque na
  imagem. Escolha a palavra que carrega o gancho/tensão central (ex.: no
  título "46ª Festa das Cerejeiras: por que esse evento nunca sai de
  moda?", destacar "nunca sai de moda" ou só "moda" — não destaque
  artigos/preposições soltos, e nunca destaque o bairro/região sozinho se
  ele não for o ponto central da frase).

Responda SOMENTE em markdown, neste formato exato (### só aparece do
slide 2 em diante — o slide 1 não usa, ele já tem o título geral do "#").
IMPORTANTE: o cabeçalho "## Slide 1" é OBRIGATÓRIO mesmo o slide 1 não
tendo mini-título — nunca cole o corpo do slide 1 direto depois do "#
[Título]" sem esse cabeçalho, isso quebra o parser:
# [Título geral do carrossel]

## Slide 1
[corpo do slide 1]

## Slide 2
### [mini-título do slide 2]
[corpo opcional]

## Slide N (último slide)
### [CTA do último slide]
[corpo opcional]

## Legenda
[texto da legenda]

## Framework
[nome do framework escolhido pra legenda, exatamente como listado acima — ex: dado_mecanismo_relevancia]

## Imagem
[palavras-chave em inglês pra busca de foto, ex: "cherry blossom park festival"]

## Tema
[etiqueta curta do assunto central]

## Viés
[ângulo específico de hoje sobre esse tema]

## Destaque do título
[1 a 3 palavras, copiadas exatamente como aparecem no título geral]
"""


def _extrair_texto(resposta) -> str:
    # claude-sonnet-5 pode incluir blocos de "thinking" antes do texto final;
    # content[0] não é garantidamente o bloco de texto.
    for bloco in resposta.content:
        if bloco.type == "text":
            return bloco.text
    raise RuntimeError("Resposta da API não contém bloco de texto.")


def _remover_preambulo(texto: str) -> str:
    """
    O modelo às vezes inclui um comentário antes do markdown (ex.: 'o texto já
    está de acordo...'), mesmo instruído a não fazer isso. Como o formato de
    saída sempre começa com '# [Título]', cortamos tudo antes da primeira
    linha de título — assim nenhum comentário vaza pro post publicado.
    """
    match = re.search(r"(?m)^# .+$", texto)
    return texto[match.start():] if match else texto


TENTATIVAS_SEM_TRAVESSAO = 3  # instrução no prompt não é garantia — checagem real aqui


def gerar_copy(pauta: str, template: str, pilar: str, tem_pauta: bool, formato: str, pauta_do_dia: dict) -> str:
    """Gera o texto/copy do post com base na pauta e no template; o modelo escolhe o framework da legenda."""
    client = anthropic.Anthropic()
    mensagem = f"Pauta de hoje:\n\n{pauta}" if tem_pauta else "Gere o post evergreen (sem pauta do dia pra esse template)."
    texto = ""
    for tentativa in range(1, TENTATIVAS_SEM_TRAVESSAO + 1):
        resposta = client.messages.create(
            model=MODELO,
            max_tokens=MAX_TOKENS_TETO,
            thinking={"type": "disabled"},
            system=_montar_prompt_sistema(template, pilar, tem_pauta, formato, pauta_do_dia),
            messages=[{"role": "user", "content": mensagem}],
        )
        texto = _remover_preambulo(_extrair_texto(resposta))
        if "—" not in texto:
            return texto
        print(f"Geração contém travessão (tentativa {tentativa}/{TENTATIVAS_SEM_TRAVESSAO}) — gerando de novo...")

    print("Travessão persistiu após todas as tentativas — substituindo por vírgula como última garantia.")
    return texto.replace("—", ",")


def _extrair_secao(texto: str, nome_secao: str) -> tuple[str, str]:
    """Extrai uma seção '## <nome_secao>' do texto gerado (metadado, não vai pro post). Retorna (conteúdo, texto_sem_a_secao)."""
    match = re.search(rf"(?m)^## {nome_secao}\s*\n(.+?)\s*(?=\n##|\Z)", texto, re.DOTALL)
    if not match:
        return "não identificado", texto
    conteudo = match.group(1).strip()
    texto_limpo = texto[:match.start()] + texto[match.end():]
    return conteudo, re.sub(r"\n{3,}", "\n\n", texto_limpo)


def _extrair_framework_escolhido(texto: str) -> tuple[str, str]:
    return _extrair_secao(texto, "Framework")


def _extrair_tema_e_vies(texto: str) -> tuple[str, str, str, str]:
    """Extrai '## Tema', '## Viés' e '## Destaque do título'. Retorna (tema, vies, destaque, texto_sem_as_secoes)."""
    tema, texto = _extrair_secao(texto, "Tema")
    vies, texto = _extrair_secao(texto, "Viés")
    destaque, texto = _extrair_secao(texto, "Destaque do título")
    return tema, vies, destaque, texto


def despersonalizar(texto: str) -> str:
    """
    Segunda passada de revisão: reescreve o texto removendo nomes de empresas/
    marcas/imóveis privados específicos, mantendo o dado ou insight genérico.
    Lugares públicos (parques, festivais, ruas) NÃO são removidos — exceção
    documentada em config/config.md.

    Blindagem: o modelo às vezes (intermitente) ignora a instrução de
    devolver o texto completo e responde só uma confirmação tipo "já está
    de acordo" — sem isso, esse post ia pro ar com esse resumo em vez do
    conteúdo de verdade. Se a resposta não parece um copy.md válido
    (não começa com "# " ou não tem as seções essenciais), descarta a
    revisão e usa o texto original sem despersonalizar.
    """
    client = anthropic.Anthropic()
    system = (
        "Você revisa textos do perfil @morar_sp antes da publicação. Aplique a regra "
        "de despersonalização do projeto: remova nomes de empresas/marcas/imóveis "
        "privados específicos, mantendo o dado ou insight genérico (ex.: 'Construtora "
        "X anunciou reajuste de 8%' vira 'reajustes de até 8% têm sido registrados no "
        "setor'). NÃO remova nomes de lugares públicos (parques, praças, festivais, "
        "ruas, equipamentos culturais) — essa é a exceção documentada, citar esses "
        "nomes é o próprio conteúdo do pilar de bairro.\n\n"
        "IMPORTANTE: SEMPRE devolva o texto INTEIRO, do título '# ' até a seção "
        "'## Viés' no final, mesmo que nada precise mudar — NUNCA responda só "
        "confirmando que está tudo certo, isso quebra o pipeline (o texto "
        "revisado É o post que vai pro ar). Responda SOMENTE com o markdown "
        "completo, sem comentário nenhum antes ou depois."
    )
    resposta = client.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS_TETO,
        thinking={"type": "disabled"},
        system=system,
        messages=[{"role": "user", "content": texto}],
    )
    revisado = _remover_preambulo(_extrair_texto(resposta))

    valido = revisado.strip().startswith("#") and "## Legenda" in revisado and len(revisado) >= len(texto) * 0.6
    if not valido:
        print("AVISO: revisão de despersonalização veio incompleta/inválida — usando o texto original sem revisar.")
        return texto
    return revisado


def salvar_copy(
    texto: str, pilar: str, template: str, framework_legenda: str, tema: str, vies: str, formato: str,
    pauta_do_dia: dict, destaque_titulo: str = "",
) -> str:
    hoje = date.today().isoformat()
    pasta = f"conteudo/posts-{hoje}"
    os.makedirs(pasta, exist_ok=True)
    caminho = f"{pasta}/copy.md"
    categoria = pauta_do_dia.get("categoria") or ""
    vies_estrutural = pauta_do_dia.get("vies_estrutural") or ""
    bairro_alvo = pauta_do_dia.get("bairro_alvo") or ""
    cabecalho = (
        f"<!-- pilar: {pilar} | template: {template} | formato: {formato} "
        f"| framework_legenda: {framework_legenda} | tema: {tema} | vies: {vies} "
        f"| categoria: {categoria} | vies_estrutural: {vies_estrutural} | bairro_alvo: {bairro_alvo} "
        f"| destaque_titulo: {destaque_titulo} -->\n\n"
    )
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(cabecalho + texto)
    return caminho


if __name__ == "__main__":
    pauta_do_dia = carregar_ou_selecionar_pauta_do_dia()
    pilar = pauta_do_dia["pilar"]

    pesquisa_do_dia = ler_pesquisa_do_dia()
    secoes = _dividir_por_pilar(pesquisa_do_dia)
    template, tem_pauta = selecionar_template(pilar, secoes)
    formato = escolher_formato_post()
    if pilar == "atracao":
        print(f"Pilar: {pilar} | Categoria: {pauta_do_dia['categoria']} | Bairro-alvo: {pauta_do_dia['bairro_alvo']} | Template: {template} | Evergreen: {not tem_pauta} | Formato: {formato}")
    else:
        print(f"Pilar: {pilar} | Viés: {pauta_do_dia['vies_estrutural']} | Bairro-alvo: {pauta_do_dia['bairro_alvo']} | Template: {template} | Evergreen: {not tem_pauta} | Formato: {formato}")

    pauta = secoes[pilar] if tem_pauta else ""
    copy_bruto = gerar_copy(pauta, template=template, pilar=pilar, tem_pauta=tem_pauta, formato=formato, pauta_do_dia=pauta_do_dia)
    copy_revisado = despersonalizar(copy_bruto)
    framework_legenda, copy_sem_framework = _extrair_framework_escolhido(copy_revisado)
    tema, vies, destaque_titulo, copy_final = _extrair_tema_e_vies(copy_sem_framework)
    print(f"Framework da legenda escolhido pelo modelo: {framework_legenda}")
    print(f"Tema: {tema} | Viés: {vies} | Destaque do título: {destaque_titulo}")

    caminho = salvar_copy(copy_final, pilar, template, framework_legenda, tema, vies, formato, pauta_do_dia, destaque_titulo)
    print(f"Copy salvo em: {caminho}")
