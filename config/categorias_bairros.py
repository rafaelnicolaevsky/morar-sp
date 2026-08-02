"""
Categorias do pilar "Atrações e vida no bairro" + tabela de afinidade
bairro×categoria/viés — pedido do usuário, 01/08/2026: parar de tratar
"atração" como um balaio genérico (causava repetição de tema e de
bairro) e trazer categorias reais de conteúdo, cada uma com os bairros
de maior afinidade real — inspirado em referências como @oquefazersp
("gastronomia | experiências | cultura").

Nomes de bairro usados aqui são sempre os 96 distritos OFICIAIS (ver
config/distritos_sp.py) — nomes comerciais/informais (Vila Madalena,
Jardins, Faria Lima, Vila Olímpia) ficam de fora pra poder cruzar com o
ranking de menções do Google News (scripts/00_selecionar_regiao.py), que
só conhece distrito oficial. "Vila Madalena" e "Jardins" viram Pinheiros
e Jardim Paulista; "Faria Lima"/"Vila Olímpia" viram Itaim Bibi.

Curada uma vez, revisar de vez em quando (mesmo espírito do ranking de
região, que também é revisado periodicamente) — não é pesquisada a cada
execução.
"""

# Soma 50 — mesmo peso que "atracao" já tinha no mix 50/25/25 do ICP
# (ver config/config.md). Gastronomia mais alta por ser historicamente o
# tipo de conteúdo de maior engajamento em perfis de cidade/bairro.
PESOS_CATEGORIAS_ATRACAO = {
    "gastronomia": 14,
    "entretenimento": 10,
    "cultura": 10,
    "lazer": 10,
    "festivais": 6,
}

# Palavras-chave pra filtrar/direcionar a busca de notícias por categoria
# (ver scripts/01_pesquisar.py) — cada categoria busca por assunto
# próprio, não mais um filtro genérico de "parece atração".
PALAVRAS_CHAVE_CATEGORIA = {
    "gastronomia": ["restaurante", "bar", "café", "gastronomia", "food truck", "brunch", "cardápio"],
    "entretenimento": ["show", "cinema", "balada", "vida noturna", "stand-up", "teatro musical", "casa de shows"],
    "cultura": ["museu", "exposição", "teatro", "arte", "galeria", "arquitetura", "centro cultural"],
    "lazer": ["parque", "passeio", "família", "ar livre", "trilha", "praça"],
    "festivais": ["festival", "feira", "evento", "festa popular"],
}

# Bairros (distrito oficial) de maior afinidade real por categoria —
# baseado em conhecimento real de SP + referências de perfis do nicho.
AFINIDADE_BAIRRO_CATEGORIA = {
    "gastronomia": ["Jardim Paulista", "Pinheiros", "Itaim Bibi", "Vila Mariana", "Mooca", "Moema"],
    "entretenimento": ["Pinheiros", "Itaim Bibi", "Consolação", "Vila Mariana"],
    "cultura": ["Jardim Paulista", "Pinheiros", "Sé", "Bela Vista"],
    "lazer": ["Vila Mariana", "Moema", "Alto de Pinheiros", "Morumbi"],
    "festivais": ["Liberdade", "Pinheiros", "Sé", "Moema"],
}

# Viés estrutural do pilar de imóveis — alterna explicitamente o ângulo
# (pedido do usuário: "se for imóveis, um post pelo lado do vendedor,
# outro pelo lado do comprador"), cada um com bairros de maior afinidade
# real pro perfil que esse viés atrai.
VIESES_POR_PILAR = {
    "compra_venda": ["comprador", "vendedor"],
    "investimento": ["investidor_aluguel", "investidor_valorizacao"],
}

AFINIDADE_BAIRRO_VIES = {
    "comprador": ["Vila Mariana", "Saúde", "Tatuapé", "Vila Prudente"],
    "vendedor": ["Itaim Bibi", "Pinheiros", "Vila Mariana", "Moema"],
    "investidor_aluguel": ["Butantã", "Vila Mariana", "Itaim Bibi"],
    "investidor_valorizacao": ["Itaim Bibi", "Pinheiros", "Moema"],
}
