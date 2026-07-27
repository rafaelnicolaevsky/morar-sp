"""
Agendador: decide se o turno atual deve publicar hoje.

Regras (definidas com o usuário):
- Ciclo de quantidade por dia: 2, 1, 2, 1, 2, 1... (nunca muda de ordem)
- 3 turnos possíveis: manhã, tarde, noite
- A cada dia, sorteia quais turnos publicam (respeitando a quantidade do
  ciclo), evitando repetir o(s) turno(s) usado(s) no dia anterior
- A variação de horário DENTRO de cada turno é responsabilidade das
  próprias tarefas do Agendador de Tarefas do Windows (RandomDelay) — este
  script só decide "publica ou não" pro turno que o chamou

Rodado 3x ao dia pelo Agendador de Tarefas do Windows, uma vez por turno:
    python scripts/agendador.py manha
    python scripts/agendador.py tarde
    python scripts/agendador.py noite

Se o turno chamado não estiver no plano de hoje, encerra sem fazer nada.
Se estiver, roda o pipeline completo (00 a 04).
"""

import json
import random
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_ESTADO = RAIZ / "config" / "agenda_estado.json"

TURNOS = ["manha", "tarde", "noite"]
DATA_EPOCA = date(2026, 7, 27)  # dia 1 do ciclo (2 posts) — hoje (26/07) já foi publicado manualmente

ETAPAS_PIPELINE = [
    "scripts/00_selecionar_regiao.py",
    "scripts/01_pesquisar.py",
    "scripts/02_gerar_copy.py",
    "scripts/03_gerar_visual.py",
    "scripts/04_publicar.py",
]


def _quantidade_do_dia(hoje: date) -> int:
    """Ciclo 2-1-2-1... a partir da DATA_EPOCA (dia 0 = 2 posts, dia 1 = 1 post, ...)."""
    dias_desde_epoca = (hoje - DATA_EPOCA).days
    return 2 if dias_desde_epoca % 2 == 0 else 1


def _carregar_estado() -> dict | None:
    if not CAMINHO_ESTADO.exists():
        return None
    with open(CAMINHO_ESTADO, encoding="utf-8") as f:
        return json.load(f)


def _salvar_estado(estado: dict) -> None:
    CAMINHO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def plano_de_hoje(hoje: date) -> dict:
    """Retorna o plano de turnos de hoje, calculando (e persistindo) na primeira chamada do dia."""
    estado_anterior = _carregar_estado()
    if estado_anterior and estado_anterior.get("data") == hoje.isoformat():
        return estado_anterior

    quantidade = _quantidade_do_dia(hoje)
    turnos_ontem = set(estado_anterior.get("turnos", [])) if estado_anterior else set()

    # A exclusão de "turno de ontem" só é matematicamente possível (e faz
    # sentido) em dias de 1 post: excluir até 2 turnos de um total de 3
    # ainda deixa 1 candidato válido. Em dias de 2 posts, excluir os 2
    # turnos de ontem deixaria só 1 candidato pra preencher 2 vagas — o que
    # forçaria reincluir os mesmos turnos excluídos, virando um padrão fixo
    # e previsível (o oposto do que "variar" pede). Por isso, dias de 2
    # posts sorteiam livremente entre os 3 turnos, sem exclusão.
    if quantidade == 1:
        candidatos = [t for t in TURNOS if t not in turnos_ontem] or TURNOS[:]
        turnos_hoje = [random.choice(candidatos)]
    else:
        turnos_hoje = random.sample(TURNOS, quantidade)

    novo_estado = {
        "data": hoje.isoformat(),
        "quantidade": quantidade,
        "turnos": turnos_hoje,
        "turnos_publicados": [],
    }
    _salvar_estado(novo_estado)
    return novo_estado


def rodar_pipeline() -> None:
    for etapa in ETAPAS_PIPELINE:
        print(f"\n--- Rodando {etapa} ---")
        resultado = subprocess.run([sys.executable, etapa], cwd=RAIZ)
        if resultado.returncode != 0:
            print(f"Pipeline interrompido: falha em {etapa}")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in TURNOS:
        print(f"Uso: python agendador.py <{'|'.join(TURNOS)}>")
        sys.exit(1)

    turno_atual = sys.argv[1]
    hoje = date.today()
    plano = plano_de_hoje(hoje)

    print(f"Plano de hoje ({hoje}): {plano['quantidade']} post(s), turnos: {plano['turnos']}")

    if turno_atual not in plano["turnos"]:
        print(f"Turno '{turno_atual}' não está no plano de hoje. Encerrando sem publicar.")
        sys.exit(0)

    print(f"Turno '{turno_atual}' confirmado. Rodando o pipeline...")
    rodar_pipeline()

    estado = _carregar_estado()
    estado["turnos_publicados"].append(turno_atual)
    _salvar_estado(estado)
    print(f"Turno '{turno_atual}' concluído.")
