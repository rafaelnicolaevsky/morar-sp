"""
Etapa 4: Publicação do carrossel no Instagram via Graph API.

Responsável por:
- Ler o copy e as imagens do carrossel gerados nas etapas anteriores
- Publicar via utils/api_instagram.py
- Registrar o resultado em logs/publicacoes.md

Ainda não implementado — esqueleto para revisão de arquitetura.

IMPORTANTE: as imagens do carrossel precisam estar acessíveis publicamente
via URL (a Graph API não aceita upload direto de arquivo local para este
endpoint) — isso implica hospedar as imagens geradas em algum lugar
acessível (ex: bucket público, CDN) antes de publicar. Ponto em aberto
a resolver antes de implementar esta etapa.
"""

from datetime import date

from utils.api_instagram import (
    criar_container_imagem,
    criar_container_carrossel,
    publicar_container,
)


def ler_conteudo_do_dia():
    hoje = date.today().isoformat()
    with open(f"conteudo/posts-{hoje}/copy.md", "r", encoding="utf-8") as f:
        legenda = f.read()
    # A implementar: listar imagens em conteudo/posts-{hoje}/carrossel/
    imagens_urls: list[str] = []
    return legenda, imagens_urls


def registrar_log(resultado: dict) -> None:
    hoje = date.today().isoformat()
    with open("logs/publicacoes.md", "a", encoding="utf-8") as f:
        f.write(f"\n## {hoje}\n{resultado}\n")


if __name__ == "__main__":
    legenda, imagens_urls = ler_conteudo_do_dia()

    container_ids = [criar_container_imagem(url) for url in imagens_urls]
    container_pai = criar_container_carrossel(container_ids, legenda)
    resultado = publicar_container(container_pai)

    registrar_log(resultado)
    print(f"Publicado: {resultado}")
