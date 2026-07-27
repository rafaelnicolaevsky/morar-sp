"""
Etapa 4: Publicação do carrossel no Instagram via Graph API.

Responsável por:
- Ler a legenda (etapa 2) e as imagens do carrossel (etapa 3) do dia
- Hospedar as imagens no repo público morar-sp-midia (a Graph API exige
  image_url público, não aceita upload de arquivo local) — ver
  utils/hospedagem_midia.py
- Publicar via utils/api_instagram.py
- Registrar o resultado em logs/publicacoes.md
"""

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.utils.api_instagram import (
    criar_container_carrossel,
    criar_container_imagem,
    publicar_container,
)
from scripts.utils.hospedagem_midia import publicar_imagens_no_repo_midia


def ler_legenda_do_dia() -> str:
    hoje = date.today().isoformat()
    with open(f"conteudo/posts-{hoje}/copy.md", "r", encoding="utf-8") as f:
        copy_md = f.read()

    match = re.search(r"(?m)^## Legenda\s*\n(.+?)\s*$", copy_md, re.DOTALL)
    if not match:
        raise ValueError("Não encontrei a seção '## Legenda' no copy.md de hoje.")
    return match.group(1).strip()


def listar_imagens_do_dia() -> list[str]:
    hoje = date.today().isoformat()
    pasta = Path(f"conteudo/posts-{hoje}/carrossel")
    imagens = sorted(
        pasta.glob("slide-*.png"),
        key=lambda p: int(re.search(r"\d+", p.stem).group()),
    )
    if not imagens:
        raise FileNotFoundError(f"Nenhuma imagem encontrada em {pasta}.")
    return [str(p) for p in imagens]


def registrar_log(resultado: dict) -> None:
    hoje = date.today().isoformat()
    with open("logs/publicacoes.md", "a", encoding="utf-8") as f:
        f.write(f"\n## {hoje}\n{resultado}\n")


if __name__ == "__main__":
    legenda = ler_legenda_do_dia()
    caminhos_imagens = listar_imagens_do_dia()

    print(f"Hospedando {len(caminhos_imagens)} imagens no repo morar-sp-midia...")
    imagens_urls = publicar_imagens_no_repo_midia(caminhos_imagens)

    print("Criando containers de mídia...")
    container_ids = [criar_container_imagem(url) for url in imagens_urls]

    print("Criando container do carrossel...")
    container_pai = criar_container_carrossel(container_ids, legenda)

    print("Publicando...")
    resultado = publicar_container(container_pai)

    registrar_log(resultado)
    print(f"Publicado: {resultado}")
