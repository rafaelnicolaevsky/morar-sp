"""
Etapa 3: Geração visual do carrossel.

Responsável por:
- Ler o copy gerado na etapa 2 (conteudo/posts-YYYY-MM-DD/copy.md)
- Renderizar cada slide em HTML/CSS e converter em PNG via Playwright
- Salvar em conteudo/posts-YYYY-MM-DD/carrossel/slide-N.png

Identidade visual (aprovada em revisão de design, ver histórico do projeto):
- Fontes: Stack Sans Headline (títulos, peso 700) e Stack Sans Text (corpo, peso 200)
- Paleta: fundo creme, texto cinza-escuro, cor de destaque por pilar
  (atrações de bairro = verde, compra/venda = azul, investimento = laranja)
- Eyebrow: pill com fundo na cor do pilar, texto branco, 12pt
- Título: sempre cinza-escuro, 50pt, quebra de linha automática (nunca conta
  de palavras fixa — ver _quebrar_titulos)
- Corpo: sempre 18pt, peso 200
- Duas variantes de layout, sorteadas por carrossel (todas as fatias do
  mesmo post usam a mesma variante, para coerência visual):
  - "esquerda": bloco a 70% da área útil, alinhado à esquerda, centralizado
    na vertical no canvas inteiro
  - "centro": bloco a 90% da área útil, centralizado na horizontal,
    posicionado na metade inferior do layout (não centralizado no canvas
    inteiro)
- Margem de 80px em todo o canvas (1080x1350)

Papel de cada card no carrossel:
- Capa (1º slide): eyebrow + título (do copy.md) + corpo + rodapé (@handle)
- Intermediários (2º ao penúltimo): sem eyebrow, sem rodapé; se o texto
  abrir com **negrito**, esse trecho vira um mini-título (mesmo estilo do
  h1 da capa) e o resto é corpo — senão, é só corpo (ver
  _extrair_titulo_intermediario)
- Último slide: eyebrow + corpo (sem título) + rodapé (@handle)
- Rodapé (@handle) aparece só na capa e no último slide, alinhado como o
  bloco de conteúdo (canto esquerdo na variante "esquerda", centralizado
  na variante "centro") — sem contador de slide
"""

import os
import random
import re
from datetime import date

from playwright.sync_api import sync_playwright

LARGURA_CANVAS = 1080
ALTURA_CANVAS = 1350

CORES_POR_PILAR = {
    "atracao": "tema-verde",
    "compra_venda": "tema-azul",
    "investimento": "tema-laranja",
}

EYEBROW_POR_PILAR = {
    "atracao": "Atrações de bairro",
    "compra_venda": "Compra e venda",
    "investimento": "Investimento",
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Stack+Sans+Headline:wght@700&family=Stack+Sans+Text:wght@200;400&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --cream: #F2DFC5;
  --dark-gray: #3E4247;
  --blue-dark: #3B76C0;
  --green-dark: #6C8A1F;
  --orange-dark: #E8611F;
}

body { font-family: 'Stack Sans Text', sans-serif; }

.slide {
  width: 1080px;
  height: 1350px;
  background: var(--cream);
  padding: 80px;
  display: flex;
  flex-direction: column;
  position: relative;
}

.slide.alinhado-esquerda {
  justify-content: center;
  align-items: flex-start;
  text-align: left;
}
.slide.alinhado-esquerda .conteudo { width: 70%; }

.slide.alinhado-centro { justify-content: flex-start; }
.slide.alinhado-centro .metade-inferior {
  position: absolute;
  top: 50%;
  left: 80px;
  right: 80px;
  bottom: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.slide.alinhado-centro .conteudo { width: 90%; }

.eyebrow {
  font-family: 'Stack Sans Text', sans-serif;
  font-weight: 400;
  font-size: 16px; /* 12pt */
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 32px;
  color: #FFFFFF;
  padding: 12px 24px;
  border-radius: 100px;
  display: inline-block;
}

h1 {
  font-family: 'Stack Sans Headline', sans-serif;
  font-weight: 700;
  font-size: 66.7px; /* 50pt */
  line-height: 1.2;
  margin-bottom: 44px;
  color: var(--dark-gray);
}

p {
  font-family: 'Stack Sans Text', sans-serif;
  font-weight: 200;
  font-size: 24px; /* 18pt */
  line-height: 1.6;
  color: var(--dark-gray);
}

.footer {
  position: absolute;
  bottom: 80px;
  left: 80px;
  right: 80px;
  font-family: 'Stack Sans Text', sans-serif;
  font-weight: 400;
  font-size: 24px;
  color: var(--dark-gray);
  opacity: 0.6;
}
.footer.alinhado-esquerda { text-align: left; }
.footer.alinhado-centro { text-align: center; }

.tema-verde .eyebrow { background: var(--green-dark); }
.tema-azul .eyebrow { background: var(--blue-dark); }
.tema-laranja .eyebrow { background: var(--orange-dark); }
"""

# JS injetado uma vez na página: quebra de linha de título.
# - "esquerda": guloso por largura real, ate 4 palavras/linha
# - "centro": balanceado por numero de caracteres, ate 6 palavras/linha,
#   com fallback para o metodo guloso se o balanceamento nao couber na coluna
# Ambos os caminhos corrigem "viuva" (ultima linha com 1 palavra so).
JS_QUEBRA_TITULO = r"""
function __medirFabrica(el) {
  const cs = getComputedStyle(el);
  const medidor = document.createElement('span');
  medidor.style.position = 'absolute';
  medidor.style.visibility = 'hidden';
  medidor.style.whiteSpace = 'nowrap';
  medidor.style.fontFamily = cs.fontFamily;
  medidor.style.fontWeight = cs.fontWeight;
  medidor.style.fontSize = cs.fontSize;
  document.body.appendChild(medidor);
  return {
    medir: (t) => { medidor.textContent = t; return medidor.getBoundingClientRect().width; },
    limpar: () => medidor.remove(),
  };
}

function __combinacoes(arr, k) {
  if (k === 0) return [[]];
  if (arr.length === 0) return [];
  const [p, ...r] = arr;
  return [...__combinacoes(r, k - 1).map(c => [p, ...c]), ...__combinacoes(r, k)];
}

function __corrigirViuva(linhas, medir, larguraMax) {
  if (linhas.length > 1 && linhas[linhas.length - 1].length === 1) {
    const ultima = linhas[linhas.length - 1];
    const penultima = linhas[linhas.length - 2];
    if (penultima.length > 1) {
      const candidata = penultima[penultima.length - 1];
      const novaUltima = [candidata, ...ultima];
      if (medir(novaUltima.join(' ')) <= larguraMax) {
        penultima.pop();
        linhas[linhas.length - 1] = novaUltima;
      }
    }
  }
  return linhas;
}

function __quebraGulosa(palavras, medir, larguraMax, maxPalavrasPorLinha) {
  const linhas = [];
  let atual = [];
  for (const p of palavras) {
    if (atual.length === 0) { atual.push(p); continue; }
    const tentativa = [...atual, p].join(' ');
    if (medir(tentativa) <= larguraMax && atual.length < maxPalavrasPorLinha) atual.push(p);
    else { linhas.push(atual); atual = [p]; }
  }
  if (atual.length) linhas.push(atual);
  return linhas;
}

function __quebraBalanceada(palavras, maxPorLinha) {
  const n = palavras.length;
  const numLinhas = Math.max(1, Math.ceil(n / maxPorLinha));
  const base = Math.floor(n / numLinhas);
  const extra = n % numLinhas;
  const fatiar = (tamanhos) => {
    const l = []; let i = 0;
    for (const t of tamanhos) { l.push(palavras.slice(i, i + t)); i += t; }
    return l;
  };
  let melhor = null, melhorSpread = Infinity;
  for (const posicoes of __combinacoes([...Array(numLinhas).keys()], extra)) {
    const tamanhos = Array(numLinhas).fill(base);
    for (const p of posicoes) tamanhos[p] += 1;
    const linhas = fatiar(tamanhos);
    const comps = linhas.map(l => l.join(' ').length);
    const spread = Math.max(...comps) - Math.min(...comps);
    if (spread < melhorSpread) { melhorSpread = spread; melhor = linhas; }
  }
  return melhor;
}

window.__quebrarTitulo = function (h1el, modo) {
  const container = h1el.closest('.conteudo');
  const larguraMax = container.getBoundingClientRect().width;
  const palavras = h1el.textContent.trim().split(/\s+/);
  const { medir, limpar } = __medirFabrica(h1el);

  let linhas;
  if (modo === 'centro') {
    const balanceada = __quebraBalanceada(palavras, 6);
    const cabemTodas = balanceada.every(l => medir(l.join(' ')) <= larguraMax);
    linhas = cabemTodas ? balanceada : __quebraGulosa(palavras, medir, larguraMax, 6);
  } else {
    linhas = __quebraGulosa(palavras, medir, larguraMax, 4);
  }
  linhas = __corrigirViuva(linhas, medir, larguraMax);

  limpar();
  h1el.innerHTML = linhas.map(l => l.join(' ')).join('<br>');
};
"""


def ler_copy_do_dia() -> str:
    hoje = date.today().isoformat()
    caminho = f"conteudo/posts-{hoje}/copy.md"
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def parse_copy(copy_md: str) -> dict:
    """Extrai pilar/template, título, slides (numerados) e legenda do copy.md da etapa 2."""
    cabecalho = re.search(r"<!--\s*pilar:\s*(\w+)\s*\|\s*template:\s*(\w+)\s*-->", copy_md)
    pilar = cabecalho.group(1) if cabecalho else "compra_venda"

    titulo_match = re.search(r"(?m)^# (.+)$", copy_md)
    titulo = titulo_match.group(1).strip() if titulo_match else ""

    secoes = re.split(r"(?m)^## (.+)$", copy_md)
    pares = list(zip(secoes[1::2], secoes[2::2]))

    slides, legenda = [], ""
    for nome, corpo in pares:
        corpo = corpo.strip()
        if nome.strip().lower().startswith("slide"):
            slides.append(corpo)
        elif nome.strip().lower().startswith("legenda"):
            legenda = corpo

    return {"pilar": pilar, "titulo": titulo, "slides": slides, "legenda": legenda}


def escolher_estilo_visual() -> str:
    """Sorteia a variante de layout do carrossel (mesma variante em todas as fatias)."""
    return random.choice(["esquerda", "centro"])


def _markdown_basico_para_html(texto: str) -> str:
    """Converte **negrito** e quebras de linha simples do markdown gerado na etapa 2."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
    return texto.replace("\n", "<br>")


def _extrair_titulo_intermediario(corpo: str) -> tuple[str, str]:
    """
    Cards intermediários não têm título próprio no copy.md, mas costumam
    abrir com um trecho em **negrito** (ex.: "📄 **FIIs de papel**\nInvestem
    em..."). Esse trecho vira o mini-título do card (mesmo estilo do h1 da
    capa); o resto do texto vira corpo. Se não houver negrito na primeira
    linha, o card fica só com corpo, como já acontecia antes.
    """
    primeira_linha, _, resto = corpo.partition("\n")
    if not re.search(r"\*\*(.+?)\*\*", primeira_linha):
        return "", corpo
    titulo = re.sub(r"\*\*(.+?)\*\*", r"\1", primeira_linha).strip()
    return titulo, resto.strip()


def _montar_html_slide(tema: str, alinhamento: str, eyebrow: str, titulo: str, corpo: str,
                        mostrar_eyebrow: bool, mostrar_footer: bool) -> str:
    bloco_eyebrow = f'<div class="eyebrow">{eyebrow}</div>' if mostrar_eyebrow else ""
    bloco_titulo = f"<h1>{titulo}</h1>" if titulo else ""
    corpo_html = _markdown_basico_para_html(corpo)
    conteudo = f'<div class="conteudo">{bloco_eyebrow}{bloco_titulo}<p>{corpo_html}</p></div>'

    if alinhamento == "centro":
        corpo_slide = f'<div class="metade-inferior">{conteudo}</div>'
    else:
        corpo_slide = conteudo

    footer = f'<div class="footer alinhado-{alinhamento}">@morar_sp</div>' if mostrar_footer else ""

    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="slide {tema} alinhado-{alinhamento}">
  {corpo_slide}
  {footer}
</div>
</body>
</html>"""


def gerar_carrossel(dados_copy: dict, estilo: str) -> list[str]:
    """Gera as imagens do carrossel e retorna a lista de caminhos dos arquivos."""
    tema = CORES_POR_PILAR.get(dados_copy["pilar"], "tema-azul")
    eyebrow = EYEBROW_POR_PILAR.get(dados_copy["pilar"], dados_copy["pilar"])
    total = len(dados_copy["slides"])

    hoje = date.today().isoformat()
    pasta = f"conteudo/posts-{hoje}/carrossel"
    os.makedirs(pasta, exist_ok=True)

    caminhos = []
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": LARGURA_CANVAS, "height": ALTURA_CANVAS})

        for i, texto_slide in enumerate(dados_copy["slides"], start=1):
            eh_primeiro = i == 1
            eh_ultimo = i == total
            eh_intermediario = not eh_primeiro and not eh_ultimo

            if eh_primeiro:
                titulo_slide, corpo_slide = dados_copy["titulo"], texto_slide
            elif eh_intermediario:
                titulo_slide, corpo_slide = _extrair_titulo_intermediario(texto_slide)
            else:  # ultimo
                titulo_slide, corpo_slide = "", texto_slide

            mostrar_eyebrow = not eh_intermediario
            mostrar_footer = eh_primeiro or eh_ultimo

            html = _montar_html_slide(
                tema, estilo, eyebrow, titulo_slide, corpo_slide,
                mostrar_eyebrow, mostrar_footer,
            )
            pagina.set_content(html)
            pagina.wait_for_timeout(300)  # tempo pra fonte do Google Fonts carregar

            pagina.add_script_tag(content=JS_QUEBRA_TITULO)
            h1 = pagina.query_selector("h1")
            if h1:
                h1.evaluate("(el, modo) => window.__quebrarTitulo(el, modo)", estilo)

            caminho = f"{pasta}/slide-{i}.png"
            pagina.query_selector(".slide").screenshot(path=caminho)
            caminhos.append(caminho)

        navegador.close()

    return caminhos


if __name__ == "__main__":
    copy_md = ler_copy_do_dia()
    dados_copy = parse_copy(copy_md)
    estilo = escolher_estilo_visual()
    print(f"Estilo sorteado: {estilo} | Pilar: {dados_copy['pilar']}")

    caminhos = gerar_carrossel(dados_copy, estilo)
    print(f"Carrossel gerado: {caminhos}")
