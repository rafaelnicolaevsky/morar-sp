"""
Etapa 2: Geração de texto/copy do post a partir da pauta pesquisada.

Responsável por:
- Ler a pesquisa do dia (pesquisa/tendencias-YYYY-MM-DD.md)
- Selecionar um template (você sabia / comparativo / opinião de mercado)
- Aplicar a regra de despersonalização (remover nomes de empresas/marcas
  específicas, mantendo o dado genérico) — ver config/config.md
- Salvar o copy gerado em conteudo/posts-YYYY-MM-DD/copy.md

Ainda não implementado — esqueleto para revisão de arquitetura.
"""

from datetime import date
import os


TEMPLATES = ["voce_sabia", "comparativo", "opiniao_de_mercado"]


def ler_pesquisa_do_dia() -> str:
    """Lê o arquivo de pesquisa gerado na etapa 1."""
    hoje = date.today().isoformat()
    caminho = f"pesquisa/tendencias-{hoje}.md"
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def despersonalizar(texto: str) -> str:
    """
    Reescreve o texto removendo nomes de empresas/marcas/imóveis específicos,
    mantendo o dado ou insight genérico. Ver regra em config/config.md.
    A implementar: lógica de reescrita (via prompt de geração).
    """
    raise NotImplementedError("Implementar reescrita de despersonalização")


def gerar_copy(pauta: str, template: str) -> str:
    """Gera o texto/copy do post com base na pauta e no template escolhido."""
    raise NotImplementedError("Implementar geração de copy")


def salvar_copy(texto: str) -> str:
    hoje = date.today().isoformat()
    pasta = f"conteudo/posts-{hoje}"
    os.makedirs(pasta, exist_ok=True)
    caminho = f"{pasta}/copy.md"
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    return caminho


if __name__ == "__main__":
    pauta = ler_pesquisa_do_dia()
    copy_bruto = gerar_copy(pauta, template=TEMPLATES[0])
    copy_final = despersonalizar(copy_bruto)
    caminho = salvar_copy(copy_final)
    print(f"Copy salvo em: {caminho}")
