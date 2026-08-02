"""
Etapa 1: Pesquisa de tendências e dados do mercado imobiliário.

Responsável por:
- Buscar notícias/dados recentes do setor (compra/venda, investimento, mercado geral)
- Buscar atrações/lifestyle da região de foco do dia (definida pela etapa 0),
  70% da região principal e 30% das secundárias
- Salvar o resultado bruto em pesquisa/tendencias-YYYY-MM-DD.md
"""

import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.distritos_sp import NOMES_AMBIGUOS
from config.categorias_bairros import PALAVRAS_CHAVE_CATEGORIA
from scripts.utils.regiao import buscar_mencoes_google_news, relevante_para_categoria
from scripts.utils.selecao_pauta import carregar_ou_selecionar_pauta_do_dia

USER_AGENT = "Mozilla/5.0 (compatible; MorarSP-Pesquisa/1.0)"
TIMEOUT = 15

# Feeds específicos do nicho (sem necessidade de filtro por palavra-chave)
FEEDS_NICHO = [
    ("Compra/venda e mercado imobiliário", "https://www.infomoney.com.br/tudo-sobre/mercado-imobiliario/feed/"),
]

# Feeds gerais de economia — aplicamos filtro por palavra-chave (no título) para achar pautas do nicho
FEEDS_GERAIS = [
    ("Mercado geral (economia)", "https://g1.globo.com/dynamo/economia/rss2.xml"),
]

PALAVRAS_CHAVE_NICHO = [
    "imóvel", "imóveis", "imobiliário", "imobiliária",
    "aluguel", "alugar", "locação", "financiamento imobiliário", "fipezap",
    "consórcio", "valorização de imóveis",
]

# Pilar "comprar para alugar": busca dedicada no Google News (não é FII/fundo,
# é imóvel físico como fonte de renda via locação)
PALAVRAS_CHAVE_ALUGUEL = [
    "aluguel", "alugar", "locação", "locatário", "inquilino",
    "proprietário", "rentabilidade", "renda com imóvel",
]
QUERY_INVESTIMENTO_ALUGUEL = "aluguel de imóveis"
JANELA_INVESTIMENTO_DIAS = 10
MAX_ITENS_INVESTIMENTO = 5

MAX_ITENS_POR_FEED = 5
TAMANHO_MAX_RESUMO = 280

JANELA_ATRACOES_DIAS = 10
MAX_ITENS_CATEGORIA = 7


RE_BOILERPLATE_WORDPRESS = re.compile(r"\s*The post .+ appeared first on .+?\.\s*$")


def _limpar_texto(texto: str) -> str:
    """Remove tags HTML, boilerplate de feed WordPress e normaliza espaços."""
    sem_tags = re.sub(r"<[^>]+>", " ", texto)
    sem_boilerplate = RE_BOILERPLATE_WORDPRESS.sub("", sem_tags)
    sem_espacos = re.sub(r"\s+", " ", sem_boilerplate).strip()
    if len(sem_espacos) > TAMANHO_MAX_RESUMO:
        sem_espacos = sem_espacos[:TAMANHO_MAX_RESUMO].rsplit(" ", 1)[0] + "…"
    return sem_espacos


def _buscar_feed(url: str) -> list[dict]:
    """Baixa e faz o parse de um feed RSS. Retorna lista de itens {titulo, link, resumo, data}."""
    resposta = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resposta.raise_for_status()

    raiz = ET.fromstring(resposta.content)
    itens = []
    for item in raiz.findall(".//item"):
        titulo = _limpar_texto(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        resumo = _limpar_texto(item.findtext("description") or "")
        data_pub = (item.findtext("pubDate") or "").strip()
        if titulo:
            itens.append({"titulo": titulo, "link": link, "resumo": resumo, "data": data_pub})
    return itens


def _relevante(item: dict) -> bool:
    # Só o título: a descrição de alguns feeds gerais traz o corpo inteiro da
    # matéria, e citações de passagem (ex.: "venda de imóveis ociosos" numa
    # notícia sobre estatais) geram falsos positivos se buscarmos nela também.
    titulo = item["titulo"].lower()
    return any(palavra in titulo for palavra in PALAVRAS_CHAVE_NICHO)


def _formatar_secao(categoria: str, itens: list[dict]) -> str:
    if not itens:
        return f"## {categoria}\n\n_Nenhuma pauta encontrada hoje._\n"

    linhas = [f"## {categoria}\n"]
    for item in itens[:MAX_ITENS_POR_FEED]:
        linhas.append(f"- **{item['titulo']}**")
        if item["resumo"]:
            linhas.append(f"  {item['resumo']}")
        linhas.append(f"  Fonte: {item['link']}")
        linhas.append("")
    return "\n".join(linhas)


def _buscar_categoria_no_bairro(distrito: str, categoria: str, limite: int) -> list[dict]:
    """
    Busca pautas de uma categoria específica (gastronomia/entretenimento/
    cultura/lazer/festivais) no bairro-alvo escolhido pela seleção de
    pauta do dia (ver utils/selecao_pauta.py) — substitui a busca
    genérica de "atração" por bairro (pedido do usuário, 01/08/2026).
    """
    query = f'"{distrito}" bairro São Paulo' if distrito in NOMES_AMBIGUOS else f'"{distrito}" São Paulo'
    try:
        itens = buscar_mencoes_google_news(query, JANELA_ATRACOES_DIAS)
    except (requests.RequestException, ET.ParseError):
        return []

    palavras = PALAVRAS_CHAVE_CATEGORIA[categoria]
    relevantes = [item for item in itens if relevante_para_categoria(item["titulo"], palavras)]
    formatados = [
        {"titulo": _limpar_texto(item["titulo"]), "link": item["link"], "resumo": ""}
        for item in relevantes[:limite]
    ]
    return formatados


def _secao_investimento_aluguel() -> str:
    """Pilar 'comprar para alugar': imóvel físico como fonte de renda via locação (não FII/fundo/ação)."""
    try:
        itens = buscar_mencoes_google_news(QUERY_INVESTIMENTO_ALUGUEL, JANELA_INVESTIMENTO_DIAS)
    except (requests.RequestException, ET.ParseError):
        itens = []

    relevantes = [
        item for item in itens
        if any(palavra in item["titulo"].lower() for palavra in PALAVRAS_CHAVE_ALUGUEL)
    ]
    formatados = [
        {"titulo": _limpar_texto(item["titulo"]), "link": item["link"], "resumo": ""}
        for item in relevantes[:MAX_ITENS_INVESTIMENTO]
    ]
    return _formatar_secao("Investimento (comprar para alugar)", formatados)


def _secao_atracao_categoria(pauta: dict) -> str:
    """
    Busca pautas SÓ se o pilar sorteado pra hoje (ver utils/selecao_pauta.py)
    for "atracao" — a categoria (gastronomia/entretenimento/cultura/lazer/
    festivais) e o bairro-alvo já vêm decididos pela seleção de pauta,
    escolhido pela tabela de afinidade categoria×bairro (pedido do
    usuário, 01/08/2026 — substitui a busca genérica de "atração" por
    região em alta).
    """
    if pauta["pilar"] != "atracao":
        return "## Atrações e vida no bairro\n\n_Pilar de hoje não é atração — ver seção do pilar sorteado._\n"

    categoria = pauta["categoria"]
    bairro_alvo = pauta["bairro_alvo"]
    itens = _buscar_categoria_no_bairro(bairro_alvo, categoria, MAX_ITENS_CATEGORIA)
    return _formatar_secao(f"Atrações e vida no bairro — {categoria} em {bairro_alvo}", itens)


def pesquisar_tendencias(pauta: dict) -> str:
    """
    Retorna um bloco de texto (markdown) com as pautas encontradas no dia,
    agrupadas por categoria editorial. `pauta` vem de
    utils/selecao_pauta.carregar_ou_selecionar_pauta_do_dia() — a mesma
    pauta usada por scripts/02_gerar_copy.py.
    """
    hoje = date.today().isoformat()
    secoes = [f"# Pesquisa de tendências — {hoje}\n"]

    secoes.append(_secao_atracao_categoria(pauta))

    for categoria, url in FEEDS_NICHO:
        try:
            itens = _buscar_feed(url)
        except (requests.RequestException, ET.ParseError) as erro:
            secoes.append(f"## {categoria}\n\n_Falha ao buscar feed: {erro}_\n")
            continue
        secoes.append(_formatar_secao(categoria, itens))

    for categoria, url in FEEDS_GERAIS:
        try:
            itens = [item for item in _buscar_feed(url) if _relevante(item)]
        except (requests.RequestException, ET.ParseError) as erro:
            secoes.append(f"## {categoria}\n\n_Falha ao buscar feed: {erro}_\n")
            continue
        secoes.append(_formatar_secao(categoria, itens))

    secoes.append(_secao_investimento_aluguel())

    return "\n".join(secoes)


def salvar_pesquisa(conteudo: str) -> str:
    """Salva o resultado da pesquisa em pesquisa/tendencias-YYYY-MM-DD.md"""
    hoje = date.today().isoformat()
    Path("pesquisa").mkdir(parents=True, exist_ok=True)
    caminho = f"pesquisa/tendencias-{hoje}.md"
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return caminho


if __name__ == "__main__":
    pauta = carregar_ou_selecionar_pauta_do_dia()
    if pauta["pilar"] == "atracao":
        print(f"Pauta de hoje: {pauta['pilar']} | categoria: {pauta['categoria']} | bairro-alvo: {pauta['bairro_alvo']}")
    else:
        print(f"Pauta de hoje: {pauta['pilar']} | viés: {pauta['vies_estrutural']} | bairro-alvo: {pauta['bairro_alvo']}")

    resultado = pesquisar_tendencias(pauta)
    caminho = salvar_pesquisa(resultado)
    print(f"Pesquisa salva em: {caminho}")
