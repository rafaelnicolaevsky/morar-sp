"""
Etapa 4: Publicação do post no Instagram via API.

Responsável por:
- Ler a legenda (etapa 2) e as imagens (etapa 3) do dia — 1 imagem = post de
  imagem única, mais de 1 = carrossel (a etapa 3 decide o formato do dia)
- Hospedar as imagens no repo público morar-sp-midia (a API exige image_url
  público, não aceita upload de arquivo local) — ver utils/hospedagem_midia.py
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
    criar_container_imagem_unica,
    esperar_container_pronto,
    publicar_container,
)
from scripts.utils.historico_temas import registrar_tema
from scripts.utils.hospedagem_midia import publicar_imagens_no_repo_midia


def ler_copy_do_dia() -> str:
    hoje = date.today().isoformat()
    with open(f"conteudo/posts-{hoje}/copy.md", "r", encoding="utf-8") as f:
        return f.read()


def ler_legenda_do_dia(copy_md: str) -> str:
    # Precisa parar só na próxima seção "## " ou no fim do arquivo, nunca no
    # fim da primeira linha — usar "$" junto de re.MULTILINE (sem lookahead)
    # casava no fim da primeira linha da legenda, cortando o resto do texto
    # (lista de sinais, explicação, hashtags) fora do post publicado.
    match = re.search(r"^## Legenda\s*\n(.+?)(?=\n## |\Z)", copy_md, re.DOTALL | re.MULTILINE)
    if not match:
        raise ValueError("Não encontrei a seção '## Legenda' no copy.md de hoje.")
    return match.group(1).strip()


def ler_cabecalho_do_dia(copy_md: str) -> dict:
    """
    Lê pilar/tema/vies (+ categoria/vies_estrutural/bairro_alvo, ver
    utils/selecao_pauta.py) do cabeçalho HTML comment gerado pela etapa
    2 — usado pra registrar no histórico.
    """
    cabecalho = re.search(
        r"<!--.*?pilar:\s*(\w+).*?tema:\s*(.+?)\s*\|\s*vies:\s*(.+?)\s*"
        r"\|\s*categoria:\s*(.*?)\s*\|\s*vies_estrutural:\s*(.*?)\s*\|\s*bairro_alvo:\s*(.*?)\s*-->",
        copy_md, re.DOTALL,
    )
    if not cabecalho:
        return {"pilar": "", "tema": "", "vies": "", "categoria": "", "vies_estrutural": "", "bairro_alvo": ""}
    return {
        "pilar": cabecalho.group(1),
        "tema": cabecalho.group(2),
        "vies": cabecalho.group(3),
        "categoria": cabecalho.group(4),
        "vies_estrutural": cabecalho.group(5),
        "bairro_alvo": cabecalho.group(6),
    }


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
    Path("logs").mkdir(parents=True, exist_ok=True)
    with open("logs/publicacoes.md", "a", encoding="utf-8") as f:
        f.write(f"\n## {hoje}\n{resultado}\n")


if __name__ == "__main__":
    copy_md = ler_copy_do_dia()
    legenda = ler_legenda_do_dia(copy_md)
    cabecalho = ler_cabecalho_do_dia(copy_md)
    caminhos_imagens = listar_imagens_do_dia()

    print(f"Hospedando {len(caminhos_imagens)} imagem(ns) no repo morar-sp-midia...")
    imagens_urls = publicar_imagens_no_repo_midia(caminhos_imagens)

    if len(imagens_urls) == 1:
        print("Post de imagem única — criando container...")
        container_pai = criar_container_imagem_unica(imagens_urls[0], legenda)
    else:
        print("Criando containers de mídia do carrossel...")
        container_ids = [criar_container_imagem(url) for url in imagens_urls]
        print("Criando container do carrossel...")
        container_pai = criar_container_carrossel(container_ids, legenda)

    print("Aguardando processamento da mídia...")
    esperar_container_pronto(container_pai)

    print("Publicando...")
    resultado = publicar_container(container_pai)

    registrar_log(resultado)

    if cabecalho["tema"] and cabecalho["vies"]:
        registrar_tema(
            cabecalho["tema"], cabecalho["vies"], cabecalho["pilar"], date.today().isoformat(),
            categoria=cabecalho["categoria"] or None,
            vies_estrutural=cabecalho["vies_estrutural"] or None,
            bairro_alvo=cabecalho["bairro_alvo"] or None,
        )
        print(f"Tema/viés registrados no histórico: {cabecalho['tema']} | {cabecalho['vies']}")

    # Marca a pasta do dia como publicada de verdade — só chega aqui se
    # tudo acima rodou sem exceção. scripts/limpar_execucoes_antigas.py só
    # apaga pastas com esse marcador, nunca um dia que falhou.
    (Path(f"conteudo/posts-{date.today().isoformat()}") / ".publicado").touch()

    print(f"Publicado: {resultado}")
