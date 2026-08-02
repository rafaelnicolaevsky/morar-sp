"""
Seleção da pauta do dia — pilar, categoria (pilar "atracao") ou viés
estrutural (pilares de imóveis) e bairro-alvo. Pedido do usuário,
01/08/2026: parar de tratar "atração" como um balaio genérico (causava
repetição de tema e bairro) e trazer categorias reais + bairros de maior
afinidade real por categoria/viés, em vez de bairro genérico "em alta"
pra qualquer tipo de conteúdo.

Fluxo: pilar sorteado no mix 50/25/25 do ICP (mesma proporção de sempre,
ver config/config.md) -> dentro do pilar, sorteia categoria (atração) ou
alterna viés estrutural (imóveis, nunca repete o último: comprador ->
vendedor -> comprador...) -> escolhe o bairro-alvo pela tabela de
afinidade (config/categorias_bairros.py), preferindo um bairro que
também esteja em alta no ranking de menções
(scripts/00_selecionar_regiao.py) quando houver interseção — senão
sorteia dentro da lista de afinidade evitando repetir o bairro do post
imediatamente anterior.

Categoria PODE se repetir entre posts (é normal um nicho ter categorias
recorrentes) — o que garante variedade de verdade é o viés/bairro/tipo
de conteúdo mudando a cada vez, não forçar rotação de categoria (pedido
explícito do usuário).

A seleção é feita 1x por dia e persistida em conteudo/posts-YYYY-MM-DD/
pauta.json — scripts/01_pesquisar.py e scripts/02_gerar_copy.py leem a
MESMA pauta (nunca sorteiam separadamente, senão pesquisa e copy
poderiam sair sobre pilares diferentes).
"""

import json
import random
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

from config.categorias_bairros import (
    AFINIDADE_BAIRRO_CATEGORIA,
    AFINIDADE_BAIRRO_VIES,
    PESOS_CATEGORIAS_ATRACAO,
    VIESES_POR_PILAR,
)
from scripts.utils.data_brt import hoje_brt
from scripts.utils.historico_temas import temas_recentes_para_prompt
from scripts.utils.regiao import carregar_regiao_foco

PESOS_PILARES = {"atracao": 50, "compra_venda": 25, "investimento": 25}


def _caminho_pauta_do_dia() -> Path:
    hoje = hoje_brt().isoformat()
    return RAIZ / "conteudo" / f"posts-{hoje}" / "pauta.json"


def selecionar_pilar() -> str:
    pilares = list(PESOS_PILARES)
    pesos = [PESOS_PILARES[p] for p in pilares]
    return random.choices(pilares, weights=pesos, k=1)[0]


def _ultimo_vies_do_pilar(pilar: str) -> str | None:
    """Último viés estrutural usado nesse pilar, pra alternar comprador<->vendedor etc."""
    for entrada in reversed(temas_recentes_para_prompt()):
        if entrada.get("pilar") == pilar and entrada.get("vies_estrutural"):
            return entrada["vies_estrutural"]
    return None


def _ultimo_bairro() -> str | None:
    for entrada in reversed(temas_recentes_para_prompt()):
        if entrada.get("bairro_alvo"):
            return entrada["bairro_alvo"]
    return None


def selecionar_categoria_atracao() -> str:
    """Sorteia a categoria (gastronomia/entretenimento/cultura/lazer/festivais), respeitando os pesos."""
    categorias = list(PESOS_CATEGORIAS_ATRACAO)
    pesos = [PESOS_CATEGORIAS_ATRACAO[c] for c in categorias]
    return random.choices(categorias, weights=pesos, k=1)[0]


def selecionar_vies_imovel(pilar: str) -> str:
    """Alterna o viés estrutural do pilar de imóveis (comprador<->vendedor, etc) — nunca repete o último."""
    candidatos = VIESES_POR_PILAR[pilar]
    ultimo = _ultimo_vies_do_pilar(pilar)
    disponiveis = [v for v in candidatos if v != ultimo] or candidatos
    return random.choice(disponiveis)


def selecionar_bairro_alvo(categoria_ou_vies: str, tabela_afinidade: dict[str, list[str]]) -> str:
    """
    Escolhe o bairro-alvo dentro da lista de afinidade da categoria/viés,
    preferindo um que também esteja em alta no ranking de menções
    (scripts/00_selecionar_regiao.py) quando houver interseção — senão
    sorteia evitando repetir o bairro do post imediatamente anterior.
    """
    candidatos = tabela_afinidade[categoria_ou_vies]

    try:
        ranking = carregar_regiao_foco().get("top_10_ranking", [])
        bairros_em_alta = {item["distrito"] for item in ranking if item.get("mencoes_atracao", 0) > 0}
    except FileNotFoundError:
        bairros_em_alta = set()

    intersecao = [b for b in candidatos if b in bairros_em_alta]
    pool = intersecao if intersecao else candidatos

    ultimo = _ultimo_bairro()
    disponiveis = [b for b in pool if b != ultimo] or pool
    return random.choice(disponiveis)


def _selecionar_pauta_do_dia() -> dict:
    pilar = selecionar_pilar()

    if pilar == "atracao":
        categoria = selecionar_categoria_atracao()
        bairro_alvo = selecionar_bairro_alvo(categoria, AFINIDADE_BAIRRO_CATEGORIA)
        return {"pilar": pilar, "categoria": categoria, "vies_estrutural": None, "bairro_alvo": bairro_alvo}

    vies = selecionar_vies_imovel(pilar)
    bairro_alvo = selecionar_bairro_alvo(vies, AFINIDADE_BAIRRO_VIES)
    return {"pilar": pilar, "categoria": None, "vies_estrutural": vies, "bairro_alvo": bairro_alvo}


def carregar_ou_selecionar_pauta_do_dia() -> dict:
    """
    Garante que a pauta do dia é sorteada só 1x e compartilhada entre
    01_pesquisar.py e 02_gerar_copy.py (nunca sorteiam separadamente).
    """
    caminho = _caminho_pauta_do_dia()
    if caminho.exists():
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)

    pauta = _selecionar_pauta_do_dia()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(pauta, f, ensure_ascii=False, indent=2)
    return pauta
