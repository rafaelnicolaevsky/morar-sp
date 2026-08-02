"""
Histórico local de temas+viés já publicados — guardrail pra nunca repetir a
mesma combinação (ex.: dois posts seguidos sobre "valorização por transporte"
com o mesmo ângulo). Tema pode se repetir ao longo do tempo (é normal um
nicho ter temas recorrentes), o que não pode repetir é tema+viés juntos.
"""

import json
from pathlib import Path

ARQUIVO_HISTORICO = Path(__file__).resolve().parent.parent.parent / "logs" / "temas_publicados.json"
LIMITE_HISTORICO_NO_PROMPT = 30


def carregar_historico() -> list[dict]:
    if not ARQUIVO_HISTORICO.exists():
        return []
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        return json.load(f)


def temas_recentes_para_prompt(limite: int = LIMITE_HISTORICO_NO_PROMPT) -> list[dict]:
    return carregar_historico()[-limite:]


def registrar_tema(
    tema: str,
    vies: str,
    pilar: str,
    data: str,
    categoria: str | None = None,
    vies_estrutural: str | None = None,
    bairro_alvo: str | None = None,
) -> None:
    """
    Chamado só depois da publicação confirmar de verdade (ver 04_publicar.py).
    `categoria` (gastronomia/entretenimento/cultura/lazer/festivais) e
    `vies_estrutural` (comprador/vendedor/investidor_*) e `bairro_alvo` vêm
    da seleção de pauta do dia (ver utils/selecao_pauta.py) — pedido do
    usuário, 01/08/2026, pra rastrear repetição de categoria/bairro, não
    só de tema+viés livre.
    """
    historico = carregar_historico()
    historico.append({
        "tema": tema,
        "vies": vies,
        "pilar": pilar,
        "data": data,
        "categoria": categoria,
        "vies_estrutural": vies_estrutural,
        "bairro_alvo": bairro_alvo,
    })
    ARQUIVO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)
