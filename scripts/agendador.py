"""
Agendador: decide se o turno/horário atual deve publicar hoje.

Regras (definidas com o usuário):
- Ciclo de quantidade por dia: 2, 1, 2, 1, 2, 1... (nunca muda de ordem)
- 3 turnos possíveis: manhã, tarde, noite
- A cada dia, sorteia quais turnos publicam (respeitando a quantidade do
  ciclo), evitando repetir o(s) turno(s) usado(s) no dia anterior
- Horário exato dentro de cada turno: sorteado entre 3 candidatos fixos
  por turno (ver HORARIOS_POR_TURNO) — migrado de RandomDelay do Windows
  Task Scheduler (01/08/2026, mudança pro GitHub Actions, que não tem
  equivalente nativo de "atraso aleatório").

Determinístico por data (semente = a própria data), não mais um arquivo
de estado persistido (config/agenda_estado.json) — pedido implícito da
migração pro GitHub Actions: cada disparo roda numa máquina limpa, sem
estado compartilhado entre execuções, então o plano do dia (e do dia
anterior, pra excluir o turno de ontem) precisa ser recalculável puro a
partir da data, sem depender de arquivo nenhum. A exclusão de "turno de
ontem" recalcula o plano de ontem com a MESMA função (profundidade
máxima 1 — o ciclo 2-1-2-1 nunca tem dois dias de 1 post seguidos).

Horários adiantados em 1h em 02/08/2026 (pedido do usuário) — o GitHub
Actions atrasa gatilhos cron de forma imprevisível (~1h-1h45 observado
no primeiro dia real). Aproveitado pra também mover o candidato
"14:50" pra "13:55" (antes do adiantamento) — colidia com um horário
do garimpinhos, que também usa 14:50.

Cada um dos 9 horários (3 turnos x 3 candidatos) é uma tarefa separada
no Agendador de Tarefas do Windows / GitHub Actions:
    python scripts/agendador.py manha 07:15
    python scripts/agendador.py manha 08:00
    python scripts/agendador.py manha 08:45
    python scripts/agendador.py tarde 13:00
    python scripts/agendador.py tarde 13:55
    python scripts/agendador.py tarde 14:40
    python scripts/agendador.py noite 18:30
    python scripts/agendador.py noite 19:15
    python scripts/agendador.py noite 20:00

Se o turno não estiver no plano de hoje, ou o horário não for o sorteado
pra esse turno hoje, encerra sem fazer nada.
"""

import random
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Fuso de Brasília fixo (não o fuso do servidor) — mesmo achado do
# scripts/utils/data_brt.py, duplicado aqui (não importado) de propósito:
# agendador.py precisa ficar 100% biblioteca padrão, sem sys.path.insert
# nem dependência de scripts.utils, porque a checagem leve do CI
# (_ci_checar_horario.py) importa este módulo ANTES de instalar qualquer
# dependência.
FUSO_BRT = timezone(timedelta(hours=-3))


def hoje_brt() -> date:
    return datetime.now(FUSO_BRT).date()


TURNOS = ["manha", "tarde", "noite"]
DATA_EPOCA = date(2026, 7, 27)  # dia 1 do ciclo (2 posts)

# Candidatos fixos por turno — migrados das janelas reais de RandomDelay
# do Windows (manhã 08:00-10:25, tarde 13:45-16:10, noite 19:15-21:25).
HORARIOS_POR_TURNO = {
    "manha": ["07:15", "08:00", "08:45"],
    "tarde": ["13:00", "13:55", "14:40"],
    "noite": ["18:30", "19:15", "20:00"],
}

ETAPAS_PIPELINE = [
    "scripts/00_selecionar_regiao.py",
    "scripts/01_pesquisar.py",
    "scripts/02_gerar_copy.py",
    "scripts/03_gerar_visual.py",
    "scripts/04_publicar.py",
]


def _quantidade_do_dia(dia: date) -> int:
    """Ciclo 2-1-2-1... a partir da DATA_EPOCA (dia 0 = 2 posts, dia 1 = 1 post, ...)."""
    dias_desde_epoca = (dia - DATA_EPOCA).days
    return 2 if dias_desde_epoca % 2 == 0 else 1


def plano_de_hoje(dia: date) -> dict:
    """Plano determinístico de turnos+horários pra uma data — semente = a própria data."""
    rnd = random.Random(f"plano-morarsp-{dia.isoformat()}")
    quantidade = _quantidade_do_dia(dia)

    # A exclusão de "turno de ontem" só é matematicamente possível (e faz
    # sentido) em dias de 1 post: excluir até 2 turnos de um total de 3
    # ainda deixa 1 candidato válido. Em dias de 2 posts, sorteia livremente
    # entre os 3 turnos, sem exclusão (ver histórico do projeto).
    if quantidade == 1:
        turnos_ontem = set(plano_de_hoje(dia - timedelta(days=1))["turnos"])
        candidatos = [t for t in TURNOS if t not in turnos_ontem] or TURNOS[:]
        turnos_hoje = [rnd.choice(candidatos)]
    else:
        turnos_hoje = rnd.sample(TURNOS, quantidade)

    horarios_hoje = {turno: rnd.choice(HORARIOS_POR_TURNO[turno]) for turno in turnos_hoje}

    return {"data": dia.isoformat(), "quantidade": quantidade, "turnos": turnos_hoje, "horarios": horarios_hoje}


def rodar_pipeline() -> None:
    for etapa in ETAPAS_PIPELINE:
        print(f"\n--- Rodando {etapa} ---")
        resultado = subprocess.run([sys.executable, etapa], cwd=RAIZ)
        if resultado.returncode != 0:
            print(f"Pipeline interrompido: falha em {etapa}")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in TURNOS:
        print(f"Uso: python agendador.py <{'|'.join(TURNOS)}> <HH:MM>")
        sys.exit(1)

    turno_atual, horario_atual = sys.argv[1], sys.argv[2]
    hoje = hoje_brt()
    plano = plano_de_hoje(hoje)

    print(f"Plano de hoje ({hoje}): {plano['quantidade']} post(s), turnos: {plano['turnos']}, horarios: {plano['horarios']}")

    if turno_atual not in plano["turnos"]:
        print(f"Turno '{turno_atual}' não está no plano de hoje. Encerrando sem publicar.")
        sys.exit(0)

    if plano["horarios"].get(turno_atual) != horario_atual:
        print(f"Horário sorteado hoje pro turno '{turno_atual}' é {plano['horarios'].get(turno_atual)}, não {horario_atual}. Encerrando.")
        sys.exit(0)

    print(f"Turno '{turno_atual}' às {horario_atual} confirmado. Rodando o pipeline...")
    rodar_pipeline()
    print(f"Turno '{turno_atual}' concluído.")
