"""
Funções reutilizáveis para chamadas à Instagram API (login direto do
Instagram, não Facebook Login — por isso o host é graph.instagram.com e o
ID de conta é o Instagram-scoped User ID, não um ID de Página do Facebook).

Usa variáveis de ambiente (.env) para credenciais — nunca hardcode o token.

Fluxo de publicação de carrossel (referência da API):
1. Criar um "container" de mídia para cada imagem do carrossel
   (POST /{ig-user-id}/media com image_url + is_carousel_item=true)
2. Criar o container "pai" do carrossel
   (POST /{ig-user-id}/media com media_type=CAROUSEL + children=[ids])
3. Publicar o container
   (POST /{ig-user-id}/media_publish com creation_id={container_id})
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
GRAPH_API_BASE = "https://graph.instagram.com/v21.0"
TIMEOUT = 30
TENTATIVAS_STATUS = 15
PAUSA_ENTRE_TENTATIVAS = 3  # segundos


def _post(caminho: str, params: dict) -> dict:
    resposta = requests.post(f"{GRAPH_API_BASE}/{caminho}", data=params, timeout=TIMEOUT)
    corpo = resposta.json()
    if resposta.status_code >= 400:
        erro = corpo.get("error", {})
        raise RuntimeError(
            f"Erro na Graph API ({resposta.status_code}) em {caminho}: "
            f"{erro.get('message', corpo)}"
        )
    return corpo


def criar_container_imagem(image_url: str) -> str:
    """Cria um container de mídia para uma imagem do carrossel. Retorna o container ID."""
    corpo = _post(f"{ACCOUNT_ID}/media", {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": ACCESS_TOKEN,
    })
    return corpo["id"]


def criar_container_imagem_unica(image_url: str, legenda: str) -> str:
    """Cria o container de um post de imagem única (não é item de carrossel). Retorna o container ID."""
    corpo = _post(f"{ACCOUNT_ID}/media", {
        "image_url": image_url,
        "caption": legenda,
        "access_token": ACCESS_TOKEN,
    })
    return corpo["id"]


def criar_container_carrossel(container_ids: list[str], legenda: str) -> str:
    """Cria o container pai do carrossel. Retorna o container ID."""
    corpo = _post(f"{ACCOUNT_ID}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(container_ids),
        "caption": legenda,
        "access_token": ACCESS_TOKEN,
    })
    return corpo["id"]


def esperar_container_pronto(container_id: str) -> None:
    """
    A Graph API processa a mídia (baixa a image_url, gera o preview) de
    forma assíncrona depois de criar o container. Publicar cedo demais dá
    'Media ID is not available' — por isso espera o status_code virar
    FINISHED antes de seguir pro media_publish.
    """
    for tentativa in range(1, TENTATIVAS_STATUS + 1):
        resposta = requests.get(
            f"{GRAPH_API_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": ACCESS_TOKEN},
            timeout=TIMEOUT,
        )
        corpo = resposta.json()
        status = corpo.get("status_code")

        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} falhou no processamento: {corpo}")
        if tentativa < TENTATIVAS_STATUS:
            time.sleep(PAUSA_ENTRE_TENTATIVAS)

    raise RuntimeError(f"Container {container_id} não ficou pronto a tempo (último status: {status})")


def publicar_container(container_id: str) -> dict:
    """Publica o container final. Retorna a resposta da API (inclui o post ID)."""
    return _post(f"{ACCOUNT_ID}/media_publish", {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN,
    })
