"""
Checagem leve (só biblioteca padrão, sem dependências instaladas) usada
pelo workflow .github/workflows/publicar.yml pra decidir, ANTES de
instalar Playwright/etc., se o turno/horário do gatilho atual deve
publicar de verdade — evita gastar minutos do GitHub Actions à toa
(mesmo padrão do Garimpinhos, 01/08/2026).

Uso: TURNO=manha HORARIO=08:15 python scripts/_ci_checar_horario.py
Imprime "true" ou "false" (stdout), nada mais.
"""

import os
from datetime import date

from agendador import plano_de_hoje

if __name__ == "__main__":
    hoje = date.today()
    turno = os.environ["TURNO"]
    horario = os.environ["HORARIO"]
    plano = plano_de_hoje(hoje)
    deve_publicar = turno in plano["turnos"] and plano["horarios"].get(turno) == horario
    print("true" if deve_publicar else "false")
