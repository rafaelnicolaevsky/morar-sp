"""
Funções reutilizáveis para chamadas à Instagram Graph API.

Usa variáveis de ambiente (.env) para credenciais — nunca hardcode o token.

Fluxo de publicação de carrossel (referência da API):
1. Criar um "container" de mídia para cada imagem do carrossel
   (POST /{ig-user-id}/media com image_url + is_carousel_item=true)
2. Criar o container "pai" do carrossel
   (POST /{ig-user-id}/media com media_type=CAROUSEL + children=[ids])
3. Publicar o container
   (POST /{ig-user-id}/media_publish com creation_id={container_id})

Ainda não implementado — esqueleto para revisão de arquitetura.
"""

import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def criar_container_imagem(image_url: str) -> str:
    """Cria um container de mídia para uma imagem do carrossel. Retorna o container ID."""
    raise NotImplementedError("Implementar chamada POST /media (is_carousel_item)")


def criar_container_carrossel(container_ids: list[str], legenda: str) -> str:
    """Cria o container pai do carrossel. Retorna o container ID."""
    raise NotImplementedError("Implementar chamada POST /media (media_type=CAROUSEL)")


def publicar_container(container_id: str) -> dict:
    """Publica o container final. Retorna a resposta da API (inclui o post ID)."""
    raise NotImplementedError("Implementar chamada POST /media_publish")
