"""
Agendador: decide se o turno/horário atual deve publicar hoje.

Regras (mudou 04/08/2026, pedido do usuário: "6 publicações diárias, duas
por turno todos os dias, como no perfil de frases" — mesmo padrão do
lembrei-instagram):
- Todo dia, os 3 turnos (manhã/tarde/noite) publicam sempre — sem ciclo
  de quantidade nem exclusão de turno do dia anterior (isso era da regra
  antiga, removida).
- Cada turno publica 2 vezes por dia, escolhidas dentre os 3 candidatos
  fixos de HORARIOS_POR_TURNO — a JANELA de quais 2 rotaciona por dia
  (mesma fórmula do lembrei-instagram/scripts/agendador.py:
  horarios_de_hoje), pra não ser sempre os 2 mesmos horários.

Determinístico por data (semente = a própria data), não mais um arquivo
de estado persistido — cada disparo do GitHub Actions roda numa máquina
limpa, sem estado compartilhado entre execuções, então o plano do dia
precisa ser recalculável puro a partir da data.

03/08/2026: voltou aos horários originais (sem adiantar 1h) — o
`schedule:` nativo do GitHub Actions foi desativado (atrasava de forma
imprevisível e gastava minutos à toa) e substituído por um Google Apps
Script externo que chama workflow_dispatch nos horários exatos abaixo.
O candidato "14:50" continua como "14:55" — colide com um horário do
garimpinhos (14:50), então fica assim mesmo revertendo o resto.

Cada um dos 9 horários (3 turnos x 3 candidatos) é uma tarefa separada no
GitHub Actions (o Apps Script já dispara todos os 9 todo dia — mudar
pra "2 de 3 por turno" não exige nenhum ajuste lá, só aqui):
    python scripts/agendador.py manha 08:15
    python scripts/agendador.py manha 09:00
    python scripts/agendador.py manha 09:45
    python scripts/agendador.py tarde 14:00
    python scripts/agendador.py tarde 14:55
    python scripts/agendador.py tarde 15:40
    python scripts/agendador.py noite 19:30
    python scripts/agendador.py noite 20:15
    python scripts/agendador.py noite 21:00

Se o horário não estiver entre os 2 sorteados pra esse turno hoje,
encerra sem fazer nada (todo turno sempre está "no plano" agora).
"""

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
DATA_EPOCA = date(2026, 7, 27)  # dia 0 da rotação de horários (sem efeito na quantidade, todo dia é 2 por turno)

# Candidatos fixos por turno — migrados das janelas reais de RandomDelay
# do Windows (manhã 08:00-10:25, tarde 13:45-16:10, noite 19:15-21:25).
HORARIOS_POR_TURNO = {
    "manha": ["08:15", "09:00", "09:45"],
    "tarde": ["14:00", "14:55", "15:40"],
    "noite": ["19:30", "20:15", "21:00"],
}

ETAPAS_PIPELINE = [
    "scripts/00_selecionar_regiao.py",
    "scripts/01_pesquisar.py",
    "scripts/02_gerar_copy.py",
    "scripts/03_gerar_visual.py",
    "scripts/04_publicar.py",
]


def _horarios_do_turno_hoje(turno: str, dia: date) -> list[str]:
    """
    2 dos 3 candidatos fixos do turno, com a JANELA deslizando por dia —
    mesma fórmula do lembrei-instagram/scripts/agendador.py
    (horarios_de_hoje): garante variedade dia a dia mesmo com só 3
    candidatos (a janela de 2 "roda" pelos 3 em sequência: dias 0,1,2,3...
    começam nos índices 0,2,1,0,...).
    """
    candidatos = HORARIOS_POR_TURNO[turno]
    n = len(candidatos)
    indice_dia = (dia - DATA_EPOCA).days
    inicio = (indice_dia * 2) % n
    return [candidatos[inicio % n], candidatos[(inicio + 1) % n]]


def plano_de_hoje(dia: date) -> dict:
    """
    Plano determinístico pra uma data — todo dia os 3 turnos publicam,
    2 vezes cada (pedido do usuário, 04/08/2026: "6 publicações diárias,
    duas por turno todos os dias, como no perfil de frases").
    """
    horarios_hoje = {turno: _horarios_do_turno_hoje(turno, dia) for turno in TURNOS}
    return {"data": dia.isoformat(), "quantidade": 6, "turnos": TURNOS[:], "horarios": horarios_hoje}


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

    if horario_atual not in plano["horarios"].get(turno_atual, []):
        print(f"Horários sorteados hoje pro turno '{turno_atual}' são {plano['horarios'].get(turno_atual)}, não inclui {horario_atual}. Encerrando.")
        sys.exit(0)

    print(f"Turno '{turno_atual}' às {horario_atual} confirmado. Rodando o pipeline...")
    rodar_pipeline()
    print(f"Turno '{turno_atual}' concluído.")
