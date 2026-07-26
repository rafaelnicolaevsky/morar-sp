"""
Etapa 1: Pesquisa de tendências e dados do mercado imobiliário.

Responsável por:
- Buscar notícias/dados recentes do setor (compra/venda, investimento, mercado geral)
- Salvar o resultado bruto em pesquisa/tendencias-YYYY-MM-DD.md
"""

import re
import xml.etree.ElementTree as ET
from datetime import date

import requests

USER_AGENT = "Mozilla/5.0 (compatible; MorarSP-Pesquisa/1.0)"
TIMEOUT = 15

# Feeds específicos do nicho (sem necessidade de filtro por palavra-chave)
FEEDS_NICHO = [
    ("Compra/venda e mercado imobiliário", "https://www.infomoney.com.br/tudo-sobre/mercado-imobiliario/feed/"),
    ("Investimento (FIIs e afins)", "https://www.infomoney.com.br/onde-investir/feed/"),
]

# Feeds gerais de economia — aplicamos filtro por palavra-chave (no título) para achar pautas do nicho
FEEDS_GERAIS = [
    ("Mercado geral (economia)", "https://g1.globo.com/dynamo/economia/rss2.xml"),
]

PALAVRAS_CHAVE_NICHO = [
    "imóvel", "imóveis", "imobiliário", "imobiliária",
    "aluguel", "financiamento imobiliário", "fipezap",
    "fii", "fundo imobiliário", "fundos imobiliários",
    "consórcio", "valorização de imóveis",
]

MAX_ITENS_POR_FEED = 5
TAMANHO_MAX_RESUMO = 280


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


def pesquisar_tendencias() -> str:
    """
    Retorna um bloco de texto (markdown) com as pautas encontradas no dia,
    agrupadas por categoria editorial.
    """
    hoje = date.today().isoformat()
    secoes = [f"# Pesquisa de tendências — {hoje}\n"]

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

    return "\n".join(secoes)


def salvar_pesquisa(conteudo: str) -> str:
    """Salva o resultado da pesquisa em pesquisa/tendencias-YYYY-MM-DD.md"""
    hoje = date.today().isoformat()
    caminho = f"pesquisa/tendencias-{hoje}.md"
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return caminho


if __name__ == "__main__":
    resultado = pesquisar_tendencias()
    caminho = salvar_pesquisa(resultado)
    print(f"Pesquisa salva em: {caminho}")
