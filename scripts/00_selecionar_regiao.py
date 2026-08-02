"""
Etapa 0: Seleção da região de foco editorial.

O perfil mira 50% do público em moradores/visitantes frequentes de bairros
específicos (atraídos pelos diferenciais da região), 25% investidores e 25%
compradores de primeiro imóvel. Para o pilar de bairro, a região de foco não
é fixa: é definida pelo nível de interesse do momento (menções recentes na
mídia sobre atrações/lifestyle, não menções genéricas — senão notícia de
crime/tragédia distorce o ranking), com 70% do conteúdo na região principal
e 30% nas secundárias.

Revisão: no máximo a cada 15 dias (config/regiao_foco.json guarda a data da
última revisão). Rodar sem --forcar em dias normais é barato: só lê o estado
salvo. A revisão de verdade dispara ~96 buscas no Google News, uma por
distrito — por isso só deve rodar quinzenalmente.
"""

import sys
import time
from datetime import date
from pathlib import Path

import requests
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.distritos_sp import DISTRITOS_SP, NOMES_AMBIGUOS
from scripts.utils.data_brt import hoje_brt
from scripts.utils.regiao import CAMINHO_ESTADO, buscar_mencoes_google_news, relevante_para_atracao

PAUSA_ENTRE_BUSCAS = 0.3
DIAS_ENTRE_REVISOES = 15
JANELA_MENCOES_DIAS = 14
NUM_SECUNDARIAS = 2


def _query_para_distrito(distrito: str) -> str:
    if distrito in NOMES_AMBIGUOS:
        return f'"{distrito}" bairro São Paulo'
    return f'"{distrito}" São Paulo'


def _ranquear_distritos() -> list[dict]:
    """Consulta o Google News para cada distrito e ranqueia por menções de atração/lifestyle."""
    ranking = []
    for distrito in DISTRITOS_SP:
        query = _query_para_distrito(distrito)
        try:
            itens = buscar_mencoes_google_news(query, JANELA_MENCOES_DIAS)
        except (requests.RequestException, ET.ParseError):
            itens = []
        mencoes_atracao = sum(1 for item in itens if relevante_para_atracao(item["titulo"]))
        ranking.append({
            "distrito": distrito,
            "mencoes_atracao": mencoes_atracao,
            "mencoes_totais": len(itens),
        })
        time.sleep(PAUSA_ENTRE_BUSCAS)

    ranking.sort(key=lambda item: item["mencoes_atracao"], reverse=True)
    return ranking


def _carregar_estado() -> dict | None:
    if not CAMINHO_ESTADO.exists():
        return None
    import json
    with open(CAMINHO_ESTADO, encoding="utf-8") as f:
        return json.load(f)


def _salvar_estado(estado: dict) -> None:
    import json
    CAMINHO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def _precisa_revisar(estado: dict | None) -> bool:
    if estado is None:
        return True
    data_revisao = date.fromisoformat(estado["data_revisao"])
    return (hoje_brt() - data_revisao).days >= DIAS_ENTRE_REVISOES


def selecionar_regiao(forcar: bool = False) -> dict:
    """Retorna o estado atual de região de foco, revisando se necessário."""
    estado = _carregar_estado()

    if not forcar and not _precisa_revisar(estado):
        return estado

    ranking = _ranquear_distritos()
    principal = ranking[0]
    secundarias = ranking[1:1 + NUM_SECUNDARIAS]

    novo_estado = {
        "regiao_principal": principal["distrito"],
        "regioes_secundarias": [item["distrito"] for item in secundarias],
        "data_revisao": hoje_brt().isoformat(),
        "top_10_ranking": ranking[:10],
    }
    _salvar_estado(novo_estado)
    return novo_estado


if __name__ == "__main__":
    forcar_revisao = "--forcar" in sys.argv
    resultado = selecionar_regiao(forcar=forcar_revisao)
    print(f"Região principal (70%): {resultado['regiao_principal']}")
    print(f"Regiões secundárias (30%): {', '.join(resultado['regioes_secundarias'])}")
    print(f"Última revisão: {resultado['data_revisao']}")
