"""
Data "de hoje" fixada no fuso de Brasília (UTC-3, sem horário de verão
desde 2019) — não o fuso do servidor onde o script roda.

Achado real, 01/08/2026: rodando no GitHub Actions (servidor em UTC),
date.today() calculou o dia errado toda vez que rodava entre 21h e meia-
noite BRT (ainda 00h-03h do dia seguinte em UTC), quebrando a
consistência entre scripts/agendador.py (decide o plano do dia) e os
demais scripts do pipeline (nomeiam arquivos/pastas pelo dia). Rodando
localmente sempre funcionou, por coincidência — o notebook já fica em
BRT.
"""

from datetime import date, datetime, timedelta, timezone

FUSO_BRT = timezone(timedelta(hours=-3))


def hoje_brt() -> date:
    return datetime.now(FUSO_BRT).date()
