"""Sorteio do formato do post do dia (carrossel ou imagem única).

Decidido na etapa 2 (antes de gerar o copy) porque o conteúdo da legenda
muda conforme o formato: em "imagem_unica" só a capa é publicada, então a
legenda precisa ser autossuficiente (explica o conteúdo + CTA); em
"carrossel" o conteúdo já é explicado ao longo dos slides, então a legenda
pode ser mais enxuta, focada em palavras-chave.
"""

import random


def escolher_formato_post() -> str:
    """Sorteia o formato do post do dia: carrossel ou imagem única (50/50)."""
    return random.choice(["carrossel", "imagem_unica"])
