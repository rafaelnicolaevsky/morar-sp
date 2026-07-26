"""
Etapa 3: Geração visual do carrossel.

Responsável por:
- Ler o copy gerado na etapa 2
- Gerar as imagens do carrossel (estilo variado: editorial/dados, humor/meme,
  informativo — sem fórmula fixa única, ver config/config.md)
- Salvar em conteudo/posts-YYYY-MM-DD/carrossel/slide-N.png

Ainda não implementado — esqueleto para revisão de arquitetura.
Abordagem provável: template HTML -> renderização em PNG (pipeline já
validado em outros projetos), ou geração via lib de imagem direta.
"""

from datetime import date
import os


def ler_copy_do_dia() -> str:
    hoje = date.today().isoformat()
    caminho = f"conteudo/posts-{hoje}/copy.md"
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def escolher_estilo_visual() -> str:
    """
    Escolhe aleatoriamente ou de forma rotativa um estilo visual
    (editorial/dados, humor/meme, informativo) para variar o feed.
    """
    raise NotImplementedError("Implementar seleção de estilo visual")


def gerar_carrossel(copy: str, estilo: str) -> list[str]:
    """
    Gera as imagens do carrossel e retorna a lista de caminhos dos arquivos.
    """
    raise NotImplementedError("Implementar geração do carrossel")


if __name__ == "__main__":
    hoje = date.today().isoformat()
    pasta = f"conteudo/posts-{hoje}/carrossel"
    os.makedirs(pasta, exist_ok=True)

    copy = ler_copy_do_dia()
    estilo = escolher_estilo_visual()
    caminhos = gerar_carrossel(copy, estilo)
    print(f"Carrossel gerado: {caminhos}")
