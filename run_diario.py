"""
Orquestrador do pipeline diário: pesquisa -> copy -> visual -> publicação.

Roda cada etapa em sequência. Se uma etapa falhar, o pipeline para e
registra o erro — não publica conteúdo incompleto.

Ainda não implementado — esqueleto para revisão de arquitetura.
"""

import subprocess
import sys

ETAPAS = [
    "scripts/01_pesquisar.py",
    "scripts/02_gerar_copy.py",
    "scripts/03_gerar_visual.py",
    "scripts/04_publicar.py",
]


def rodar_pipeline():
    for etapa in ETAPAS:
        print(f"\n--- Rodando {etapa} ---")
        resultado = subprocess.run([sys.executable, etapa])
        if resultado.returncode != 0:
            print(f"Pipeline interrompido: falha em {etapa}")
            sys.exit(1)
    print("\nPipeline concluído com sucesso.")


if __name__ == "__main__":
    rodar_pipeline()
