"""
Utilitários compartilhados de região de foco: busca no Google News e
classificação de relevância de atração/lifestyle, além da leitura do
estado gerado por scripts/00_selecionar_regiao.py.
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

USER_AGENT = "Mozilla/5.0 (compatible; MorarSP-Pesquisa/1.0)"
TIMEOUT = 15

CAMINHO_ESTADO = Path(__file__).resolve().parent.parent.parent / "config" / "regiao_foco.json"

# Google News RSS não filtra bem queries booleanas compostas (OR/parênteses
# tendem a cair num fallback genérico). Por isso a busca é sempre simples
# (nome do distrito) e a triagem por relevância é feita no título, aqui.
PALAVRAS_ATRACAO = [
    "restaurante", r"bar(?:es)?\b", "casa noturna", "parque", "evento", "festival",
    "festa", "gastronomia", "cultura", "cultural", "lazer", "turismo",
    "feira", "atração", "show", "exposição", "inaugura", "aniversário",
    "edição", "praça", "museu", "gastronômic", "loja", "compras", "shopping",
]
PALAVRAS_NEGATIVAS = [
    "morre", "morte", "morto", "incêndio", "acidente", "crime", "polícia",
    "assalto", "tiroteio", "preso", "presa", "investigação", "homicídio",
    "furto", "roubo", "estupro", "operação policial", "corpo",
]


def _contem_palavra(texto: str, palavras: list[str]) -> bool:
    # \b (borda de palavra) no início evita que "cultura" dê match dentro de
    # outra palavra maior; "bar" tem borda nos dois lados (mas aceita
    # "bares") para não casar com nomes de distrito como "Barra Funda".
    return any(re.search(rf"\b{palavra}", texto) for palavra in palavras)


def relevante_para_atracao(titulo: str) -> bool:
    texto = titulo.lower()
    if _contem_palavra(texto, PALAVRAS_NEGATIVAS):
        return False
    return _contem_palavra(texto, PALAVRAS_ATRACAO)


def buscar_mencoes_google_news(query: str, janela_dias: int) -> list[dict]:
    """Busca notícias recentes (últimos `janela_dias` dias) no Google News. Retorna {titulo, link, data}."""
    url = "https://news.google.com/rss/search"
    params = {"q": query, "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"}
    resposta = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resposta.raise_for_status()

    raiz = ET.fromstring(resposta.content)
    limite = datetime.now(tz=None).astimezone() - timedelta(days=janela_dias)

    itens = []
    for item in raiz.findall(".//item"):
        data_texto = item.findtext("pubDate")
        if not data_texto:
            continue
        try:
            data_pub = parsedate_to_datetime(data_texto)
        except (TypeError, ValueError):
            continue
        if data_pub >= limite:
            itens.append({
                "titulo": item.findtext("title") or "",
                "link": item.findtext("link") or "",
                "data": data_texto,
            })
    return itens


def carregar_regiao_foco() -> dict:
    """Lê config/regiao_foco.json. Levanta erro claro se a etapa 0 ainda não rodou."""
    if not CAMINHO_ESTADO.exists():
        raise FileNotFoundError(
            "config/regiao_foco.json não existe. Rode scripts/00_selecionar_regiao.py primeiro."
        )
    with open(CAMINHO_ESTADO, encoding="utf-8") as f:
        return json.load(f)
