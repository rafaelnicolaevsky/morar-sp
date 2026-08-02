"""
Hospedagem das imagens do carrossel no repositório morar-sp-midia (público),
pra virarem URLs consumíveis via raw.githubusercontent.com pela Instagram
Graph API (que exige image_url público, não aceita upload de arquivo local).
"""

import os
import subprocess
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

TENTATIVAS_VERIFICACAO = 6
PAUSA_ENTRE_TENTATIVAS = 5  # segundos

MIDIA_REPO_PATH = Path(os.getenv("MIDIA_REPO_PATH", "../morar-sp-midia")).resolve()
MIDIA_REPO_URL_RAW = "https://raw.githubusercontent.com/rafaelnicolaevsky/morar-sp-midia/main"

GIT_USER_NAME = os.getenv("GIT_USER_NAME", "rafaelnicolaevsky")
GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "")
if not GIT_USER_EMAIL:
    raise RuntimeError("GIT_USER_EMAIL não definido (.env local ou secret no CI).")


def _rodar_git(args: list[str]) -> str:
    resultado = subprocess.run(
        ["git", "-c", f"user.name={GIT_USER_NAME}", "-c", f"user.email={GIT_USER_EMAIL}", *args],
        cwd=MIDIA_REPO_PATH, capture_output=True, text=True,
        # Sem isso, o Windows abre uma janela de console nova só pro git
        # quando chamado a partir de um processo sem console — achado
        # real, 31/07/2026 (visível sob login Interactive, invisível mas
        # ainda desnecessário sob S4U).
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    saida = resultado.stdout + resultado.stderr
    if resultado.returncode != 0 and "nothing to commit" not in saida:
        raise RuntimeError(f"git {' '.join(args)} falhou em {MIDIA_REPO_PATH}: {saida}")
    return saida


def publicar_imagens_no_repo_midia(caminhos_imagens: list[str]) -> list[str]:
    """
    Copia as imagens do carrossel do dia para o repo morar-sp-midia, commita e
    dá push. Retorna as URLs públicas (raw.githubusercontent.com), na mesma
    ordem das imagens de entrada.
    """
    if not MIDIA_REPO_PATH.exists():
        raise FileNotFoundError(
            f"Repositório de mídia não encontrado em {MIDIA_REPO_PATH}. "
            "Ajuste MIDIA_REPO_PATH no .env se o caminho for outro."
        )

    hoje = date.today().isoformat()
    pasta_destino = MIDIA_REPO_PATH / "posts" / hoje
    pasta_destino.mkdir(parents=True, exist_ok=True)

    urls = []
    for caminho_origem in caminhos_imagens:
        nome_arquivo = Path(caminho_origem).name
        destino = pasta_destino / nome_arquivo
        destino.write_bytes(Path(caminho_origem).read_bytes())
        urls.append(f"{MIDIA_REPO_URL_RAW}/posts/{hoje}/{nome_arquivo}")

    _rodar_git(["add", "-A"])
    _rodar_git(["commit", "-m", f"Imagens do post {hoje}"])
    _rodar_git(["push"])

    for url in urls:
        _esperar_url_disponivel(url)

    return urls


def _esperar_url_disponivel(url: str) -> None:
    """
    A Graph API busca a imagem imediatamente ao criar o container, mas o
    raw.githubusercontent.com pode levar alguns segundos pra refletir o push.
    Espera a URL responder 200 antes de seguir, com algumas tentativas.
    """
    for tentativa in range(1, TENTATIVAS_VERIFICACAO + 1):
        try:
            resposta = requests.head(url, timeout=10)
            if resposta.status_code == 200:
                return
        except requests.RequestException:
            pass
        if tentativa < TENTATIVAS_VERIFICACAO:
            time.sleep(PAUSA_ENTRE_TENTATIVAS)

    raise RuntimeError(f"URL não ficou disponível a tempo: {url}")
