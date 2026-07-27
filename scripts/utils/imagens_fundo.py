"""
Busca de foto de fundo para os slides via Unsplash API.

Cascata de fallback (do mais específico ao mais genérico) e degradação
graciosa: se não houver UNSPLASH_ACCESS_KEY configurada, ou a API falhar, ou
nenhuma busca retornar resultado, retorna None — o slide cai pro fundo
sólido de cor (comportamento original), sem quebrar o pipeline.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_API_BASE = "https://api.unsplash.com"
TIMEOUT = 15

QUERIES_POR_PILAR = {
    "atracao": "brazil urban neighborhood street",
    "compra_venda": "modern apartment building architecture",
    "investimento": "city skyline business district",
}
QUERY_GENERICA_FINAL = "são paulo cityscape"


def _buscar_foto(query: str) -> dict | None:
    if not UNSPLASH_ACCESS_KEY:
        return None
    try:
        resposta = requests.get(
            f"{UNSPLASH_API_BASE}/search/photos",
            params={"query": query, "per_page": 1, "orientation": "portrait"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=TIMEOUT,
        )
        resposta.raise_for_status()
        resultados = resposta.json().get("results", [])
        return resultados[0] if resultados else None
    except requests.RequestException:
        return None


def _registrar_download(foto: dict) -> None:
    """Exigido pelas diretrizes de uso da API do Unsplash ao exibir uma foto."""
    url_download = (foto.get("links") or {}).get("download_location")
    if not url_download:
        return
    try:
        requests.get(
            url_download,
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        pass


def buscar_foto_de_fundo(pilar: str, termo_especifico: str | None) -> str | None:
    """
    Retorna a URL de uma foto de fundo, tentando do termo mais específico
    (normalmente as palavras-chave em inglês geradas pela etapa 2 pro
    assunto exato da pauta) ao mais genérico do pilar, e por fim um
    genérico absoluto. Retorna None se nada for encontrado ou a API não
    estiver disponível/configurada.
    """
    tentativas = []
    if termo_especifico:
        tentativas.append(termo_especifico)
    tentativas.append(QUERIES_POR_PILAR.get(pilar, QUERY_GENERICA_FINAL))
    tentativas.append(QUERY_GENERICA_FINAL)

    for query in tentativas:
        foto = _buscar_foto(query)
        if foto:
            _registrar_download(foto)
            return foto["urls"]["regular"]
    return None
