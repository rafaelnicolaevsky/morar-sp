"""
Apaga pastas de post antigas (conteudo/posts-<YYYY-MM-DD>/) com mais de
DIAS_RETENCAO dias — só as que têm o marcador ".publicado" (escrito por
scripts/04_publicar.py só depois da publicação completar sem exceção).
Dias que falharam ou nunca chegaram a publicar nunca têm esse marcador,
então nunca são apagados — é o único rastro local pra debugar o que deu
errado.

As imagens em si não se perdem: já foram hospedadas permanentemente no
repo morar-sp-midia (ver utils/hospedagem_midia.py) antes da publicação
confirmar. O que se apaga aqui é só a cópia local de trabalho.

Diferente dos outros projetos da família (garimpinhos, fernanda_machado_ia,
rafanico-instagram, lembrei-instagram): morar-sp não usa pasta por
execução com timestamp, usa uma pasta por DIA (conteudo/posts-<data>/,
sem scripts/utils/execucao.py) — publica no máximo 1x por dia. Por isso
não existe marcador de "execução atual" pra proteger; a pasta de HOJE é
protegida só por comparação de nome mesmo.
"""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.utils.data_brt import hoje_brt

RAIZ_CONTEUDO = Path(__file__).resolve().parent.parent / "conteudo"

DIAS_RETENCAO = 15


def limpar() -> None:
    pasta_hoje = f"posts-{hoje_brt().isoformat()}"
    limite = time.time() - DIAS_RETENCAO * 86400
    apagadas, mantidas_sem_marcador, mantidas_recentes = 0, 0, 0

    for pasta in sorted(RAIZ_CONTEUDO.glob("posts-*")):
        if not pasta.is_dir():
            continue
        if pasta.name == pasta_hoje:
            continue

        marcador = pasta / ".publicado"
        if not marcador.exists():
            mantidas_sem_marcador += 1
            continue

        if marcador.stat().st_mtime > limite:
            mantidas_recentes += 1
            continue

        shutil.rmtree(pasta)
        apagadas += 1
        print(f"Apagada: {pasta.name}")

    print(
        f"\nResumo: {apagadas} apagada(s), {mantidas_recentes} publicada(s) "
        f"ainda dentro dos {DIAS_RETENCAO} dias, {mantidas_sem_marcador} "
        f"sem marcador de publicação (nunca apagadas)."
    )


if __name__ == "__main__":
    limpar()
