"""
Relatório semanal de insights — busca os posts publicados nos últimos 7
dias via Graph API do Instagram, pega as métricas de cada um (alcance,
curtidas, comentários, salvamentos, compartilhamentos) e adiciona uma
linha por post na aba deste projeto na planilha "INSIGHTS"
(compartilhada entre os 5 projetos de Instagram, uma aba por projeto).

Rodado 1x por semana (ver .github/workflows/insights.yml, toda
segunda-feira de manhã) — cobre a semana anterior inteira.

Idempotente por post_id: não duplica linha se um post já foi registrado
numa rodada anterior (ex.: reprocessamento manual).
"""

import os
from datetime import datetime, timedelta, timezone

import gspread
import requests
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
GRAPH_API_BASE = "https://graph.instagram.com/v21.0"
TIMEOUT = 30

INSIGHTS_SHEET_ID = os.getenv("INSIGHTS_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "config/google-service-account.json")
ESCOPOS = ["https://www.googleapis.com/auth/spreadsheets"]

# Nome da aba deste projeto na planilha INSIGHTS — ÚNICA linha que muda
# entre os 5 projetos (garimpinhos/morar_sp/lembrei/rafanico/fernanda).
ABA = "morar_sp"

DIAS_JANELA = 7
METRICAS = ["reach", "likes", "comments", "saved", "shares"]
CABECALHO = [
    "data_publicacao", "post_id", "permalink", "tipo_midia",
    "legenda_resumida", "alcance", "curtidas", "comentarios",
    "salvamentos", "compartilhamentos",
]


def _buscar_posts_da_semana() -> list[dict]:
    """Lista de mídia mais recente primeiro — pagina até achar um post
    mais velho que a janela ou acabar o feed."""
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS_JANELA)
    posts, url = [], f"{GRAPH_API_BASE}/{ACCOUNT_ID}/media"
    params = {
        "fields": "id,timestamp,permalink,caption,media_product_type",
        "limit": 50,
        "access_token": ACCESS_TOKEN,
    }

    while url:
        resposta = requests.get(url, params=params, timeout=TIMEOUT)
        resposta.raise_for_status()
        dados = resposta.json()

        parou = False
        for item in dados.get("data", []):
            publicado_em = datetime.fromisoformat(item["timestamp"].replace("+0000", "+00:00"))
            if publicado_em < limite:
                parou = True
                break
            posts.append(item)

        if parou:
            break
        url = dados.get("paging", {}).get("next")
        params = {}  # a URL "next" já vem com todos os parâmetros embutidos

    return posts


def _buscar_metricas(post_id: str) -> dict:
    """Busca as métricas configuradas; se alguma não for suportada pro tipo
    de mídia (ex.: 'shares' em alguns formatos antigos), tenta de novo sem
    ela em vez de falhar o post inteiro."""
    metricas = list(METRICAS)
    while metricas:
        resposta = requests.get(
            f"{GRAPH_API_BASE}/{post_id}/insights",
            params={"metric": ",".join(metricas), "access_token": ACCESS_TOKEN},
            timeout=TIMEOUT,
        )
        if resposta.status_code == 200:
            valores = {m["name"]: m["values"][0]["value"] for m in resposta.json().get("data", [])}
            return {m: valores.get(m, "") for m in METRICAS}

        corpo = resposta.json().get("error", {}).get("message", "")
        metrica_invalida = next((m for m in metricas if m in corpo), None)
        if not metrica_invalida:
            raise RuntimeError(f"Falha ao buscar insights de {post_id}: {corpo}")
        print(f"  Métrica '{metrica_invalida}' não suportada por esse post — removendo e tentando de novo.")
        metricas.remove(metrica_invalida)

    return {m: "" for m in METRICAS}


def _abrir_aba():
    credenciais = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=ESCOPOS)
    cliente = gspread.authorize(credenciais)
    planilha = cliente.open_by_key(INSIGHTS_SHEET_ID)
    try:
        return planilha.worksheet(ABA)
    except gspread.WorksheetNotFound:
        ws = planilha.add_worksheet(title=ABA, rows=500, cols=len(CABECALHO))
        ws.append_row(CABECALHO)
        return ws


def _ids_ja_registrados(aba) -> set[str]:
    valores = aba.col_values(2)  # coluna post_id
    return set(valores[1:])  # pula o cabeçalho


if __name__ == "__main__":
    posts = _buscar_posts_da_semana()
    print(f"{len(posts)} post(s) publicado(s) nos últimos {DIAS_JANELA} dias.")

    aba = _abrir_aba()
    ja_registrados = _ids_ja_registrados(aba)

    linhas_novas = []
    for post in posts:
        if post["id"] in ja_registrados:
            print(f"  {post['id']} já registrado — pulando.")
            continue

        metricas = _buscar_metricas(post["id"])
        legenda = (post.get("caption") or "").replace("\n", " ")[:80]
        linhas_novas.append([
            post["timestamp"][:10],
            post["id"],
            post.get("permalink", ""),
            post.get("media_product_type", ""),
            legenda,
            metricas["reach"],
            metricas["likes"],
            metricas["comments"],
            metricas["saved"],
            metricas["shares"],
        ])
        print(f"  {post['id']} ({post['timestamp'][:10]}): alcance={metricas['reach']} curtidas={metricas['likes']}")

    if linhas_novas:
        aba.append_rows(linhas_novas)
        print(f"{len(linhas_novas)} linha(s) nova(s) adicionada(s) na aba '{ABA}'.")
    else:
        print("Nada novo pra registrar.")
