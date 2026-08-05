"""
Etapa 3: Geração visual do carrossel.

Responsável por:
- Ler o copy gerado na etapa 2 (conteudo/posts-YYYY-MM-DD/copy.md)
- Renderizar cada slide em HTML/CSS e converter em PNG via Playwright
- Salvar em conteudo/posts-YYYY-MM-DD/carrossel/slide-N.png

Identidade visual (aprovada em revisão de design, ver histórico do projeto):
- Fontes: Big Shoulders (títulos, peso 800 — trocado de Stack Sans Headline em
  01/08/2026, aprovado pelo usuário entre 3 propostas testadas) e Stack Sans
  Text (corpo, peso 200 — sem mudança)
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
- Fundo: foto (Unsplash, buscada pelas palavras-chave em inglês que a etapa 2
  gera pro assunto específico da pauta — ver campo "## Imagem" do copy.md),
  mesma foto em todos os slides do post (varia só entre posts diferentes).
  Overlay sorteado por card (exceto a capa, que é sempre "gradiente"), dois
  modos pra não repetir sempre o mesmo tratamento — "gradiente" principal
  (70% dos demais cards) e "box" secundário (30%):
  - "gradiente": preto em gradiente, fixo em 75% embaixo (nunca 100%) até
    0% em cima, sem blur — foto nítida no topo. Na variante "esquerda" o
    bloco de texto é deslocado pra baixo (justify-content: flex-end) pra
    cair onde o gradiente está mais forte — a "centro" já fica na metade
    inferior e não desloca na horizontal nem na vertical além disso.
  - "box": cartão colorido (85%, cor da linha editorial) só atrás do bloco
    de texto, resto da foto em cor natural
  Texto branco com leve sombra nos dois modos. Se não houver foto disponível
  (sem chave configurada, API fora, sem resultado), cai pro fundo sólido
  creme com texto cinza-escuro — ver scripts/utils/imagens_fundo.py

Papel de cada card no carrossel (contrato de formato definido na etapa 2):
- Capa (1º slide): eyebrow + título geral (do copy.md) + corpo + rodapé (@handle)
- Intermediários (2º ao penúltimo): sem eyebrow, sem rodapé; mini-título
  OBRIGATÓRIO (marcado com '### ' no copy.md) + corpo opcional
- Último slide: eyebrow + mini-título OBRIGATÓRIO que é um CTA (curtir,
  comentar, compartilhar ou salvar — pode ser pergunta) + corpo opcional
  + rodapé (@handle)
- Rodapé (@handle) aparece só na capa e no último slide, alinhado como o
  bloco de conteúdo (canto esquerdo na variante "esquerda", centralizado
  na variante "centro") — sem contador de slide
"""

import os
import random
import re
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.utils.data_brt import hoje_brt
from scripts.utils.formato import escolher_formato_post
from scripts.utils.imagens_fundo import buscar_foto_de_fundo
from scripts.utils.regiao import carregar_regiao_foco

LARGURA_CANVAS = 1080
ALTURA_CANVAS = 1350

# Cor e eyebrow por CATEGORIA (pilar "atracao") ou por PILAR (imóveis) —
# pedido do usuário, 01/08/2026: cada categoria de atração tem sua própria
# cor (não mais um verde único genérico pro pilar inteiro).
TEMA_POR_CATEGORIA = {
    "gastronomia": "tema-gastronomia",
    "entretenimento": "tema-entretenimento",
    "cultura": "tema-cultura",
    "lazer": "tema-lazer",
    "festivais": "tema-festivais",
}
TEMA_POR_PILAR = {
    "compra_venda": "tema-compra-venda",
    "investimento": "tema-investimento",
}

EYEBROW_POR_CATEGORIA = {
    "gastronomia": "Gastronomia",
    "entretenimento": "Entretenimento",
    "cultura": "Cultura",
    "lazer": "Lazer",
    "festivais": "Festivais",
}
EYEBROW_POR_PILAR = {
    "compra_venda": "Compra e venda",
    "investimento": "Investimento",
}


def tema_e_eyebrow(dados_copy: dict) -> tuple[str, str]:
    """Resolve a classe de tema (cor) e o texto do eyebrow — por categoria no pilar 'atracao', por pilar nos demais."""
    pilar = dados_copy["pilar"]
    if pilar == "atracao":
        categoria = dados_copy.get("categoria") or ""
        return (
            TEMA_POR_CATEGORIA.get(categoria, "tema-cultura"),
            EYEBROW_POR_CATEGORIA.get(categoria, "Atrações de bairro"),
        )
    return TEMA_POR_PILAR.get(pilar, "tema-compra-venda"), EYEBROW_POR_PILAR.get(pilar, pilar)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders:wght@800&family=Stack+Sans+Text:wght@200;400&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --cream: #F2DFC5;
  --dark-gray: #3E4247;
  --cor-gastronomia: #FFD738;
  --cor-entretenimento: #FF8138;
  --cor-cultura: #21ED98;
  --cor-lazer: #B9FF38;
  --cor-festivais: #FF4561;
  --cor-compra-venda: #6738FF;
  --cor-investimento: #FF38E4;
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

.slide.tem-foto {
  background-size: cover;
  background-position: center;
}
.slide.tem-foto h1,
.slide.tem-foto p,
.slide.tem-foto .footer {
  color: #FFFFFF;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.45);
}
.slide.tem-foto .footer { opacity: 0.95; }

/* Modo "box": cartão colorido (85%) só atrás do bloco de texto — o resto
   da foto fica em cor natural. Alterna com o modo "cheio" a cada card. */
.slide.tem-foto.overlay-box .conteudo {
  padding: 48px;
  border-radius: 28px;
}
.slide.tema-gastronomia.tem-foto.overlay-box .conteudo { background: rgba(255, 215, 56, 0.85); }
.slide.tema-entretenimento.tem-foto.overlay-box .conteudo { background: rgba(255, 129, 56, 0.85); }
.slide.tema-cultura.tem-foto.overlay-box .conteudo { background: rgba(33, 237, 152, 0.85); }
.slide.tema-lazer.tem-foto.overlay-box .conteudo { background: rgba(185, 255, 56, 0.85); }
.slide.tema-festivais.tem-foto.overlay-box .conteudo { background: rgba(255, 69, 97, 0.85); }
.slide.tema-compra-venda.tem-foto.overlay-box .conteudo { background: rgba(103, 56, 255, 0.85); }
.slide.tema-investimento.tem-foto.overlay-box .conteudo { background: rgba(255, 56, 228, 0.85); }

/* Modo "cheio": cor do pilar (85%) cobrindo o slide inteiro, sem cartão. */
.slide.tem-foto.overlay-cheio::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
}
.slide.tema-gastronomia.tem-foto.overlay-cheio::before { background: rgba(255, 215, 56, 0.85); }
.slide.tema-entretenimento.tem-foto.overlay-cheio::before { background: rgba(255, 129, 56, 0.85); }
.slide.tema-cultura.tem-foto.overlay-cheio::before { background: rgba(33, 237, 152, 0.85); }
.slide.tema-lazer.tem-foto.overlay-cheio::before { background: rgba(185, 255, 56, 0.85); }
.slide.tema-festivais.tem-foto.overlay-cheio::before { background: rgba(255, 69, 97, 0.85); }
.slide.tema-compra-venda.tem-foto.overlay-cheio::before { background: rgba(103, 56, 255, 0.85); }
.slide.tema-investimento.tem-foto.overlay-cheio::before { background: rgba(255, 56, 228, 0.85); }
.slide.tem-foto.overlay-cheio .conteudo { position: relative; z-index: 1; }
.slide.tem-foto.overlay-cheio .metade-inferior { z-index: 1; }
.slide.tem-foto.overlay-cheio .footer { z-index: 1; }

/* Modo "gradiente": preto em gradiente (85% embaixo, nunca 100%,
   sustentado até 45% de altura, só depois esmaecendo pra 0% no topo) —
   achado real: título de 3-4 linhas em imagem única alcança bem acima da
   metade da peça, e um fade linear simples (0%->100%) já ficava fraco
   demais na parte de cima do título sobre fotos com muito detalhe claro
   (ex.: papel/gráficos). Segurar a opacidade por mais altura garante
   contraste em qualquer quantidade de linhas do título, sem escurecer o
   topo da foto (que continua visível/nítido). */
.slide.tem-foto.overlay-gradiente::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.85) 0%, rgba(0, 0, 0, 0.85) 45%, rgba(0, 0, 0, 0) 100%);
  z-index: 0;
}
.slide.tem-foto.overlay-gradiente .conteudo { position: relative; z-index: 1; }
.slide.tem-foto.overlay-gradiente .metade-inferior { z-index: 1; }
.slide.tem-foto.overlay-gradiente .footer { z-index: 1; }

/* No modo gradiente, desloca o bloco pra baixo na variante "esquerda" (a
   "centro" já fica na metade inferior por padrão, não precisa de ajuste) —
   assim o texto cai onde o gradiente está mais forte/legível. */
.slide.overlay-gradiente.alinhado-esquerda {
  justify-content: flex-end;
  padding-bottom: 220px;
}

/* Modo "sólido": sem foto nenhuma, fundo 100% na cor do pilar — usado pra
   alternar com os cards com foto no carrossel, pra não repetir a mesma
   imagem em todos os cards (capa nunca usa esse modo). */
.slide.solido.tema-gastronomia { background: var(--cor-gastronomia); }
.slide.solido.tema-entretenimento { background: var(--cor-entretenimento); }
.slide.solido.tema-cultura { background: var(--cor-cultura); }
.slide.solido.tema-lazer { background: var(--cor-lazer); }
.slide.solido.tema-festivais { background: var(--cor-festivais); }
.slide.solido.tema-compra-venda { background: var(--cor-compra-venda); }
.slide.solido.tema-investimento { background: var(--cor-investimento); }
.slide.solido h1,
.slide.solido p,
.slide.solido .footer {
  color: #FFFFFF;
}
.slide.solido .footer { opacity: 0.95; }
.slide.solido .eyebrow {
  background: transparent;
  border: 2px solid #FFFFFF;
}
/* Mesmo ajuste de contraste do eyebrow (fundos claros), agora pro modo
   sólido inteiro — texto branco não lê em cima de amarelo/verde-limão. */
.slide.solido.tema-gastronomia h1, .slide.solido.tema-gastronomia p, .slide.solido.tema-gastronomia .footer, .slide.solido.tema-gastronomia .eyebrow,
.slide.solido.tema-entretenimento h1, .slide.solido.tema-entretenimento p, .slide.solido.tema-entretenimento .footer, .slide.solido.tema-entretenimento .eyebrow,
.slide.solido.tema-cultura h1, .slide.solido.tema-cultura p, .slide.solido.tema-cultura .footer, .slide.solido.tema-cultura .eyebrow,
.slide.solido.tema-lazer h1, .slide.solido.tema-lazer p, .slide.solido.tema-lazer .footer, .slide.solido.tema-lazer .eyebrow {
  color: var(--dark-gray);
  border-color: var(--dark-gray);
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
  /* 150px (não 80px, igual ao .footer) — reserva uma faixa exclusiva pra
     assinatura @morar_sp, senão o CTA podia colidir com ela quando o
     conteúdo (título+corpo) crescia bastante (achado real, 01/08/2026). */
  bottom: 150px;
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
  font-family: 'Big Shoulders', sans-serif;
  font-weight: 800;
  font-size: 78px; /* medido empiricamente pra ocupar volume equivalente ao Stack Sans Headline com o mesmo texto */
  line-height: 1.15;
  margin-bottom: 44px;
  color: var(--dark-gray);
}

p {
  font-family: 'Stack Sans Text', sans-serif;
  font-weight: 200;
  font-size: 24px; /* 18pt */
  line-height: 1.6;
  color: var(--dark-gray);
  /* Espaço ANTES (do título) e DEPOIS (do CTA, quando houver, ou da
     assinatura) iguais — pedido do usuário, 01/08/2026. margin-top bate
     com o margin-bottom do h1 (colapsa sem mudar nada); margin-bottom
     colapsa com o margin-top do .cta-legenda (24px) pro maior dos dois
     (44px), equilibrando os dois lados do texto. */
  margin-top: 44px;
  margin-bottom: 44px;
}

.cta-legenda {
  font-family: 'Stack Sans Text', sans-serif;
  font-weight: 700;
  font-size: 20px;
  /* margin-top ZERADO de propósito (não removido — sem isso herdava os
     44px da regra genérica de "p", já que .cta-legenda também é uma tag
     <p>). O espaço acima do CTA já vem do margin-bottom do corpo (44px,
     mesmo valor do espaço abaixo do título) — somar os dois desequilibrava
     (achado real, 01/08/2026). */
  margin-top: 0;
  margin-bottom: 24px;
  letter-spacing: 0.02em;
  display: inline-block;
  padding: 12px 20px;
  border: 2px solid currentColor;
  border-radius: 16px;
}

.destaque {
  /* Palavra(s) mais importante(s) do título, na cor do eyebrow/categoria —
     pedido do usuário, 01/08/2026. */
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.45);
}
.tema-gastronomia .destaque { color: var(--cor-gastronomia); }
.tema-entretenimento .destaque { color: var(--cor-entretenimento); }
.tema-cultura .destaque { color: var(--cor-cultura); }
.tema-lazer .destaque { color: var(--cor-lazer); }
.tema-festivais .destaque { color: var(--cor-festivais); }
.tema-compra-venda .destaque { color: var(--cor-compra-venda); }
.tema-investimento .destaque { color: var(--cor-investimento); }

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

.tema-gastronomia .eyebrow { background: var(--cor-gastronomia); }
.tema-entretenimento .eyebrow { background: var(--cor-entretenimento); }
.tema-cultura .eyebrow { background: var(--cor-cultura); }
.tema-lazer .eyebrow { background: var(--cor-lazer); }
.tema-festivais .eyebrow { background: var(--cor-festivais); }
.tema-compra-venda .eyebrow { background: var(--cor-compra-venda); }
.tema-investimento .eyebrow { background: var(--cor-investimento); }

/* Fundos claros (amarelo/verde-limão) não têm contraste suficiente com
   texto branco no eyebrow — troca pra escuro nessas categorias (medido
   por luminância, achado real, 01/08/2026). Festivais (#FF4561) e os 2
   pilares de imóveis (roxo/magenta) são escuros o bastante, mantêm branco. */
.tema-gastronomia .eyebrow,
.tema-entretenimento .eyebrow,
.tema-cultura .eyebrow,
.tema-lazer .eyebrow {
  color: var(--dark-gray);
  text-shadow: none;
}
"""

# JS injetado uma vez na página: quebra de linha de título E do corpo
# (pedido do usuário, 01/08/2026 — mesma regra pros dois).
# - Quebra SEMPRE nos dois-pontos (":") primeiro — cada trecho separado por
#   ":" vira seu próprio grupo de linhas, nunca misturado.
# - Dentro de cada grupo: "esquerda" é guloso por largura real (até
#   maxPalavrasPorLinha), "centro" é balanceado por número de caracteres
#   (linhas com quantidade semelhante de palavras), com fallback pro guloso
#   se o balanceamento não couber na coluna.
# - Corrige "viúva" (última linha do grupo com 1 palavra só) dentro de cada
#   grupo separadamente — nunca puxa palavra de um grupo pro outro.
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

function __balancearEmNLinhas(palavras, numLinhas) {
  const n = palavras.length;
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

// Acha o MENOR número de linhas (começando em 1) cuja divisão balanceada
// cabe de verdade na largura disponível — em vez de um teto fixo de
// palavras/linha, que quebrava em mais linhas do que o necessário (achado
// real, 01/08/2026: um corpo de 18 palavras virou 3 linhas quando cabia
// em 2). Sempre a divisão com quantidade mais parecida de palavras por
// linha, pra esse número mínimo de linhas.
function __quebraBalanceadaAuto(palavras, medir, larguraMax) {
  for (let numLinhas = 1; numLinhas <= palavras.length; numLinhas++) {
    const linhas = __balancearEmNLinhas(palavras, numLinhas);
    if (linhas.every(l => medir(l.join(' ')) <= larguraMax)) return linhas;
  }
  return [palavras]; // não deveria chegar aqui
}

function __quebraBalanceada(palavras, maxPorLinha) {
  const n = palavras.length;
  const numLinhas = Math.max(1, Math.ceil(n / maxPorLinha));
  const melhor = __balancearEmNLinhas(palavras, numLinhas);
  return melhor;
}

window.__quebrarTexto = function (el, modo, maxPalavrasPorLinha) {
  const container = el.closest('.conteudo') || el.parentElement;
  const estiloContainer = getComputedStyle(container);
  const paddingH = parseFloat(estiloContainer.paddingLeft) + parseFloat(estiloContainer.paddingRight);
  const larguraMax = container.getBoundingClientRect().width - paddingH;
  const { medir, limpar } = __medirFabrica(el);

  // Preserva qualquer <span class="destaque">...</span> já presente no HTML
  // (palavra em destaque, ver 02_gerar_copy.py) — quebra pelo texto puro,
  // depois reaplica o span nas palavras que originalmente estavam dentro dele.
  const htmlOriginal = el.innerHTML;
  const marcador = document.createElement('div');
  marcador.innerHTML = htmlOriginal;
  const palavrasDestaque = new Set(
    Array.from(marcador.querySelectorAll('.destaque')).flatMap(s => s.textContent.trim().split(/\s+/))
  );

  // Quebra SEMPRE nos sinais de pontuação (dois-pontos, ponto, interrogação,
  // exclamação, ponto-e-vírgula) primeiro — cada trecho vira um grupo
  // independente de linhas, nunca mistura conteúdo de lados diferentes do
  // sinal (pedido do usuário, 01/08/2026).
  const grupos = el.textContent.trim().split(/(?<=[:.!?;])\s+/).filter(g => g.length > 0);

  // Regra fixa (pedido do usuário, 01/08/2026): quebra em sinal + equilíbrio
  // por número de linhas mínimo vale IGUAL pros dois alinhamentos —
  // "centro" e "esquerda" só mudam o CSS de posição/texto, nunca a lógica
  // de quebra de linha.
  let todasLinhas = [];
  for (const grupo of grupos) {
    const palavras = grupo.trim().split(/\s+/);
    let linhas = __quebraBalanceadaAuto(palavras, medir, larguraMax);
    linhas = __corrigirViuva(linhas, medir, larguraMax);
    todasLinhas.push(...linhas);
  }

  limpar();
  el.innerHTML = todasLinhas.map(linha => linha.map(palavra => {
    const limpa = palavra.replace(/[.,!?:;]+$/, '');
    return palavrasDestaque.has(limpa) ? `<span class="destaque">${palavra}</span>` : palavra;
  }).join(' ')).join('<br>');
};

// Compat: mantém o nome antigo, só pro título (4 esquerda / 6 centro palavras por linha).
window.__quebrarTitulo = function (h1el, modo) {
  window.__quebrarTexto(h1el, modo, modo === 'centro' ? 6 : 4);
};
"""


def ler_copy_do_dia() -> str:
    hoje = hoje_brt().isoformat()
    caminho = f"conteudo/posts-{hoje}/copy.md"
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def parse_copy(copy_md: str) -> dict:
    """Extrai pilar/template, título, slides (numerados) e legenda do copy.md da etapa 2."""
    # Sem exigir "-->" logo após template — o cabeçalho pode ter mais campos
    # depois (framework_legenda, tema, vies), e exigir o fechamento ali
    # fazia esse regex nunca bater (bug real: pilar sempre caía no fallback
    # "compra_venda", mesmo em posts de outros pilares).
    cabecalho = re.search(r"<!--\s*pilar:\s*(\w+)\s*\|\s*template:\s*(\w+)", copy_md)
    pilar = cabecalho.group(1) if cabecalho else "compra_venda"

    # Formato decidido na etapa 2 (antes de gerar o copy, pra legenda já sair
    # adequada) e salvo no cabeçalho. copy.md gerado antes desse campo existir
    # não tem "formato:" — nesse caso, None sinaliza pro __main__ sortear como
    # fallback (comportamento antigo).
    formato_match = re.search(r"formato:\s*(\w+)", copy_md)
    formato = formato_match.group(1) if formato_match else None

    destaque_match = re.search(r"destaque_titulo:\s*(.*?)\s*-->", copy_md)
    destaque_titulo = destaque_match.group(1) if destaque_match else ""

    categoria_match = re.search(r"categoria:\s*(.*?)\s*\|", copy_md)
    categoria = categoria_match.group(1) if categoria_match else ""

    titulo_match = re.search(r"(?m)^# (.+)$", copy_md)
    titulo = titulo_match.group(1).strip() if titulo_match else ""

    # O modelo às vezes esquece o cabeçalho "## Slide 1" e cola o corpo do
    # slide 1 direto após o título geral. Se sobrar conteúdo substantivo
    # entre o título e a primeira "## " seção, é o corpo do slide 1 perdido
    # — recuperamos aqui em vez de deixar o parser descartar silenciosamente.
    corpo_apos_titulo = copy_md[titulo_match.end():] if titulo_match else copy_md
    corpo_orfao_slide1 = re.split(r"(?m)^## ", corpo_apos_titulo, maxsplit=1)[0].strip()

    secoes = re.split(r"(?m)^## (.+)$", copy_md)
    pares = list(zip(secoes[1::2], secoes[2::2]))

    slides, legenda, termo_imagem = [], "", ""
    for nome, corpo in pares:
        corpo = corpo.strip()
        if nome.strip().lower().startswith("slide"):
            slides.append(corpo)
        elif nome.strip().lower().startswith("legenda"):
            legenda = corpo
        elif nome.strip().lower().startswith("imagem"):
            termo_imagem = corpo.strip().strip('"').strip("'")

    if corpo_orfao_slide1:
        slides.insert(0, corpo_orfao_slide1)

    return {
        "pilar": pilar, "titulo": titulo, "slides": slides,
        "legenda": legenda, "termo_imagem": termo_imagem, "formato": formato,
        "destaque_titulo": destaque_titulo, "categoria": categoria,
    }


def escolher_estilo_visual() -> str:
    """Sorteia a variante de layout do carrossel (mesma variante em todas as fatias)."""
    return random.choice(["esquerda", "centro"])


def _aplicar_destaque(titulo: str, destaque_titulo: str) -> str:
    """
    Envolve o período de destaque (ver '## Destaque do título' na etapa 2)
    num <span class="destaque"> — pedido do usuário, 01/08/2026: colorir
    o trecho mais importante do título na cor do eyebrow/pilar. Desde
    04/08/2026, sempre um PERÍODO INTEIRO (da maiúscula que abre a frase
    até o ponto/sinal que a separa da próxima), não mais 1-3 palavras
    soltas. Match exato (case-sensitive, o prompt pede cópia literal); se
    não achar a substring no título, devolve sem destaque (degradação
    graciosa, nunca quebra o post por causa disso).
    """
    if not destaque_titulo or destaque_titulo not in titulo:
        return titulo
    return titulo.replace(destaque_titulo, f'<span class="destaque">{destaque_titulo}</span>', 1)


def _markdown_basico_para_html(texto: str) -> str:
    """Converte **negrito** e quebras de linha simples do markdown gerado na etapa 2."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
    return texto.replace("\n", "<br>")


def _extrair_titulo_e_corpo(texto_slide: str) -> tuple[str, str]:
    """
    A partir do 2º slide, o copy.md (etapa 2) traz um mini-título obrigatório
    marcado com '### ' na primeira linha (no último slide, esse mini-título é
    o CTA) e um corpo opcional nas linhas seguintes.

    Fallback (copy.md gerado antes desse contrato, ou o modelo esquecendo o
    '### '): se a primeira linha tiver **negrito**, vira o mini-título; senão
    o texto inteiro fica só como corpo, sem título.
    """
    primeira_linha, _, resto = texto_slide.partition("\n")
    primeira_linha = primeira_linha.strip()

    if primeira_linha.startswith("### "):
        return primeira_linha[4:].strip(), resto.strip()

    if re.search(r"\*\*(.+?)\*\*", primeira_linha):
        titulo = re.sub(r"\*\*(.+?)\*\*", r"\1", primeira_linha).strip()
        return titulo, resto.strip()

    return "", texto_slide


def _montar_html_slide(tema: str, alinhamento: str, eyebrow: str, titulo: str, corpo: str,
                        mostrar_eyebrow: bool, mostrar_footer: bool, foto_url: str | None,
                        modo_overlay: str, mostrar_cta_legenda: bool = False,
                        usar_foto: bool = True) -> str:
    bloco_eyebrow = f'<div class="eyebrow">{eyebrow}</div>' if mostrar_eyebrow else ""
    bloco_titulo = f"<h1>{titulo}</h1>" if titulo else ""
    corpo_html = _markdown_basico_para_html(corpo)
    bloco_corpo = f"<p>{corpo_html}</p>" if corpo.strip() else ""
    # Post de imagem única: o resto do conteúdo só existe na legenda, então a
    # capa precisa deixar isso explícito — sem esse aviso, quem vê o post não
    # sabe que precisa abrir a legenda pra entender o assunto por completo.
    bloco_cta_legenda = '<p class="cta-legenda">→ Continua na legenda</p>' if mostrar_cta_legenda else ""
    conteudo = f'<div class="conteudo">{bloco_eyebrow}{bloco_titulo}{bloco_corpo}{bloco_cta_legenda}</div>'

    if alinhamento == "centro":
        corpo_slide = f'<div class="metade-inferior">{conteudo}</div>'
    else:
        corpo_slide = conteudo

    footer = f'<div class="footer alinhado-{alinhamento}">@morar_sp</div>' if mostrar_footer else ""

    # "solido" força fundo na cor do pilar mesmo com foto_url disponível —
    # é o que permite alternar cards com foto e cards sem foto no mesmo
    # carrossel (ver guardrail de legibilidade/repetição em config.md).
    if foto_url and usar_foto:
        classe_foto = f" tem-foto overlay-{modo_overlay}"
        estilo_foto = f' style="background-image: url(\'{foto_url}\');"'
    elif not foto_url:
        classe_foto = ""
        estilo_foto = ""
    else:
        classe_foto = " solido"
        estilo_foto = ""

    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="slide {tema} alinhado-{alinhamento}{classe_foto}"{estilo_foto}>
  {corpo_slide}
  {footer}
</div>
</body>
</html>"""


def gerar_carrossel(dados_copy: dict, estilo: str, formato: str = "carrossel") -> list[str]:
    """
    Gera as imagens do post e retorna a lista de caminhos dos arquivos.
    formato="carrossel": gera todos os slides. formato="imagem_unica": gera
    só a capa (título geral + corpo do slide 1), como post de imagem única.
    """
    tema, eyebrow = tema_e_eyebrow(dados_copy)
    slides_a_gerar = dados_copy["slides"][:1] if formato == "imagem_unica" else dados_copy["slides"]
    total = len(slides_a_gerar)

    # Prioriza o termo de busca gerado pela etapa 2 (específico do assunto da
    # pauta, ex.: "cherry blossom park festival"). Fallback pra região em
    # foco (copy.md gerado antes desse campo existir) — buscar_foto_de_fundo
    # já cuida do fallback genérico por pilar se nada disso existir/achar.
    termo_especifico = dados_copy.get("termo_imagem") or None
    if not termo_especifico and dados_copy["pilar"] == "atracao":
        try:
            termo_especifico = carregar_regiao_foco()["regiao_principal"]
        except FileNotFoundError:
            termo_especifico = None
    foto_url = buscar_foto_de_fundo(dados_copy["pilar"], termo_especifico)

    hoje = hoje_brt().isoformat()
    pasta = f"conteudo/posts-{hoje}/carrossel"
    os.makedirs(pasta, exist_ok=True)

    # Limpa slides de uma geração anterior no mesmo dia (ex.: se o post tinha
    # 6 slides antes e agora tem 5, o slide-6.png antigo ficaria órfão na
    # pasta e seria publicado por engano junto com o carrossel novo).
    for arquivo_antigo in Path(pasta).glob("slide-*.png"):
        arquivo_antigo.unlink()

    caminhos = []
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": LARGURA_CANVAS, "height": ALTURA_CANVAS})

        for i, texto_slide in enumerate(slides_a_gerar, start=1):
            eh_primeiro = i == 1
            eh_ultimo = i == total
            eh_intermediario = not eh_primeiro and not eh_ultimo

            if eh_primeiro:
                titulo_slide, corpo_slide = _aplicar_destaque(dados_copy["titulo"], dados_copy["destaque_titulo"]), texto_slide
            else:  # intermediario ou ultimo (CTA) — ambos tem mini-titulo obrigatorio, corpo opcional
                titulo_slide, corpo_slide = _extrair_titulo_e_corpo(texto_slide)

            mostrar_eyebrow = not eh_intermediario
            mostrar_footer = eh_primeiro or eh_ultimo
            if eh_primeiro:
                modo_overlay = "gradiente"  # obrigatório na capa
            else:
                modo_overlay = random.choices(["gradiente", "box"], weights=[70, 30], k=1)[0]

            # Capa sempre com foto (obrigatório). Demais cards alternam entre
            # foto e sólido na cor do pilar (índice ímpar = foto, par =
            # sólido) — pra não repetir a mesma imagem em todos os cards do
            # carrossel (guardrail de legibilidade/repetição, config.md).
            usar_foto = eh_primeiro or i % 2 == 1

            mostrar_cta_legenda = eh_primeiro and formato == "imagem_unica"

            html = _montar_html_slide(
                tema, estilo, eyebrow, titulo_slide, corpo_slide,
                mostrar_eyebrow, mostrar_footer, foto_url, modo_overlay,
                mostrar_cta_legenda, usar_foto,
            )
            pagina.set_content(html)
            pagina.wait_for_timeout(300)  # tempo pra fonte do Google Fonts carregar

            pagina.add_script_tag(content=JS_QUEBRA_TITULO)
            h1 = pagina.query_selector("h1")
            if h1:
                h1.evaluate("(el, modo) => window.__quebrarTexto(el, modo, modo === 'centro' ? 6 : 4)", estilo)
            corpo_p = pagina.query_selector("p:not(.cta-legenda)")
            if corpo_p:
                corpo_p.evaluate("(el, modo) => window.__quebrarTexto(el, modo, modo === 'centro' ? 8 : 6)", estilo)

            caminho = f"{pasta}/slide-{i}.png"
            pagina.query_selector(".slide").screenshot(path=caminho)
            caminhos.append(caminho)

        navegador.close()

    return caminhos


if __name__ == "__main__":
    copy_md = ler_copy_do_dia()
    dados_copy = parse_copy(copy_md)
    estilo = escolher_estilo_visual()
    # Formato normalmente já vem decidido do cabeçalho (etapa 2, pra legenda
    # sair adequada); só sorteia aqui como fallback pra copy.md antigo.
    formato = dados_copy["formato"] or escolher_formato_post()
    print(f"Formato: {formato} | Estilo: {estilo} | Pilar: {dados_copy['pilar']}")

    caminhos = gerar_carrossel(dados_copy, estilo, formato)
    print(f"Carrossel gerado: {caminhos}")
