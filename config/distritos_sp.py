"""
Lista oficial dos 96 distritos administrativos do município de São Paulo.

Fonte: Lei municipal nº 13.399/2002 (divisão em subprefeituras/distritos),
conferida via Wikipédia (Lista de subprefeituras do município de São Paulo).

Usada como universo de candidatos no ranking de "região de interesse"
(scripts/00_selecionar_regiao.py) — qualquer distrito pode vencer, não há
lista pré-filtrada por potencial.
"""

DISTRITOS_SP = [
    "Alto de Pinheiros", "Anhanguera", "Aricanduva", "Artur Alvim", "Barra Funda",
    "Bela Vista", "Belém", "Bom Retiro", "Brasilândia", "Brás", "Butantã",
    "Cachoeirinha", "Cambuci", "Campo Belo", "Campo Grande", "Campo Limpo",
    "Cangaíba", "Capão Redondo", "Carrão", "Casa Verde", "Cidade Ademar",
    "Cidade Dutra", "Cidade Líder", "Cidade Tiradentes", "Consolação", "Cursino",
    "Ermelino Matarazzo", "Freguesia do Ó", "Grajaú", "Guaianases", "Iguatemi",
    "Ipiranga", "Itaim Bibi", "Itaim Paulista", "Itaquera", "Jabaquara", "Jaguara",
    "Jaguaré", "Jaraguá", "Jardim Helena", "Jardim Paulista", "Jardim São Luís",
    "Jardim Ângela", "Jaçanã", "José Bonifácio", "Lajeado", "Lapa", "Liberdade",
    "Limão", "Mandaqui", "Marsilac", "Moema", "Mooca", "Morumbi", "Parelheiros",
    "Pari", "Parque do Carmo", "Pedreira", "Penha", "Perdizes", "Perus",
    "Pinheiros", "Pirituba", "Ponte Rasa", "Raposo Tavares", "República",
    "Rio Pequeno", "Sacomã", "Santa Cecília", "Santana", "Santo Amaro",
    "Sapopemba", "Saúde", "Socorro", "São Domingos", "São Lucas", "São Mateus",
    "São Miguel Paulista", "São Rafael", "Sé", "Tatuapé", "Tremembé", "Tucuruvi",
    "Vila Andrade", "Vila Curuçá", "Vila Formosa", "Vila Guilherme", "Vila Jacuí",
    "Vila Leopoldina", "Vila Maria", "Vila Mariana", "Vila Matilde",
    "Vila Medeiros", "Vila Prudente", "Vila Sônia", "Água Rasa",
]

# Distritos cujo nome também é uma palavra comum do português (ou homônimo
# frequente), o que gera falsos positivos em busca por menção de texto.
# Para esses, a busca de interesse exige o termo "bairro" junto ao nome.
NOMES_AMBIGUOS = {
    "Liberdade", "Saúde", "República", "Socorro", "Penha", "Limão", "Consolação",
    "Sé", "Belém", "Moema", "Carrão", "Lapa",
}
