"""Listas usadas só para fabricar a base. Não são cadastros reais."""

from analysis.labels import CHANNEL, PLAN, PORTE, SECTOR

# Ordem fixa: a sequência do gerador aleatório depende dela.
CHANNELS = tuple(CHANNEL)
PORTES = tuple(PORTE)
SECTORS = tuple(SECTOR)
PLANS = tuple(PLAN)

CHANNEL_WEIGHTS = {
    "organic": 16,
    "referral": 11,
    "google_ads": 23,
    "linkedin_ads": 14,
    "event": 7,
    "outbound": 15,
    "partner": 8,
    "email": 6,
}

# Probabilidades condicionais: P(MQL), P(SQL|MQL), P(opp|SQL), P(ganho|opp).
CHANNEL_CONVERSION = {
    "organic": (0.46, 0.60, 0.78, 0.50),
    "referral": (0.70, 0.72, 0.84, 0.58),
    "google_ads": (0.28, 0.42, 0.70, 0.32),
    "linkedin_ads": (0.34, 0.50, 0.74, 0.40),
    "event": (0.42, 0.56, 0.80, 0.44),
    "outbound": (0.24, 0.52, 0.72, 0.36),
    "partner": (0.52, 0.62, 0.80, 0.48),
    "email": (0.20, 0.38, 0.66, 0.28),
}

# Investimento mensal de mídia/programa. Zero significa "sem mídia rastreada",
# não custo econômico zero. Evento só nos meses de feira.
CHANNEL_SPEND = {
    "organic": 0,
    "referral": 0,
    "google_ads": 24000,
    "linkedin_ads": 16000,
    "event": 0,
    "outbound": 7000,
    "partner": 5500,
    "email": 1200,
}
EVENT_MONTHS = {3, 6, 8, 11}
EVENT_SPEND = 18000

PORTE_WEIGHTS = {"mei": 14, "micro": 34, "pequena": 36, "media": 16}
PORTE_WIN = {"mei": 0.78, "micro": 0.94, "pequena": 1.08, "media": 1.20}
PORTE_RISK = {"mei": 1.55, "micro": 1.18, "pequena": 0.92, "media": 0.70}

SECTOR_WEIGHTS = {
    "comercio_varejo": 18,
    "comercio_atacado": 8,
    "servicos_profissionais": 14,
    "industria": 8,
    "tecnologia": 7,
    "saude": 8,
    "educacao": 6,
    "alimentacao": 9,
    "logistica": 6,
    "construcao": 7,
    "agronegocio": 5,
    "beleza_bem_estar": 4,
}
SECTOR_RISK = {
    "comercio_varejo": 1.12,
    "comercio_atacado": 1.04,
    "servicos_profissionais": 0.90,
    "industria": 1.00,
    "tecnologia": 0.84,
    "saude": 0.95,
    "educacao": 1.00,
    "alimentacao": 1.22,
    "logistica": 1.06,
    "construcao": 1.20,
    "agronegocio": 1.08,
    "beleza_bem_estar": 1.16,
}

CHANNEL_RISK = {
    "organic": 0.86,
    "referral": 0.72,
    "google_ads": 1.22,
    "linkedin_ads": 1.05,
    "event": 0.98,
    "outbound": 1.12,
    "partner": 0.90,
    "email": 1.24,
}

# Receita anual fictícia, na faixa usual de cada porte (LC 123 / uso de mercado).
REVENUE_RANGE = {
    "mei": (28000, 81000),
    "micro": (81000, 360000),
    "pequena": (360000, 4800000),
    "media": (4800000, 28000000),
}
EMPLOYEE_RANGE = {
    "mei": (1, 1),
    "micro": (2, 9),
    "pequena": (10, 49),
    "media": (50, 220),
}

PLAN_WEIGHTS = {
    "mei": (("essencial", 82), ("profissional", 18)),
    "micro": (("essencial", 52), ("profissional", 48)),
    "pequena": (("essencial", 22), ("profissional", 55), ("enterprise", 23)),
    "media": (("profissional", 38), ("enterprise", 62)),
}
PLAN_MRR = {
    ("mei", "essencial"): 149,
    ("mei", "profissional"): 249,
    ("micro", "essencial"): 249,
    ("micro", "profissional"): 449,
    ("pequena", "essencial"): 449,
    ("pequena", "profissional"): 890,
    ("pequena", "enterprise"): 1890,
    ("media", "profissional"): 1490,
    ("media", "enterprise"): 4290,
}

# Sazonalidade comercial simples: março, agosto e novembro mais cheios; dezembro curto.
MONTH_SEASON = {
    1: 0.86,
    2: 0.93,
    3: 1.16,
    4: 1.02,
    5: 1.05,
    6: 0.96,
    7: 0.90,
    8: 1.12,
    9: 1.00,
    10: 1.05,
    11: 1.20,
    12: 0.76,
}

UF_WEIGHTS = {
    "SP": 28,
    "MG": 12,
    "RJ": 10,
    "RS": 7,
    "PR": 7,
    "SC": 5,
    "BA": 5,
    "PE": 4,
    "CE": 3,
    "GO": 3,
    "DF": 2,
    "ES": 2,
    "PA": 2,
    "MT": 1.5,
    "MS": 1.2,
    "AM": 1.2,
    "RN": 1,
    "PB": 1,
    "AL": 0.8,
    "SE": 0.6,
    "PI": 0.6,
    "MA": 0.8,
    "RO": 0.4,
    "TO": 0.4,
    "AC": 0.3,
    "AP": 0.3,
    "RR": 0.2,
}

CITIES = {
    "AC": ["Rio Branco", "Cruzeiro do Sul"],
    "AL": ["Maceió", "Arapiraca"],
    "AM": ["Manaus"],
    "AP": ["Macapá"],
    "BA": ["Salvador", "Feira de Santana", "Vitória da Conquista"],
    "CE": ["Fortaleza", "Juazeiro do Norte", "Sobral"],
    "DF": ["Brasília"],
    "ES": ["Vitória", "Vila Velha", "Serra"],
    "GO": ["Goiânia", "Anápolis", "Rio Verde"],
    "MA": ["São Luís", "Imperatriz"],
    "MG": ["Belo Horizonte", "Uberlândia", "Juiz de Fora", "Montes Claros"],
    "MS": ["Campo Grande", "Dourados"],
    "MT": ["Cuiabá", "Rondonópolis"],
    "PA": ["Belém", "Ananindeua", "Santarém"],
    "PB": ["João Pessoa", "Campina Grande"],
    "PE": ["Recife", "Olinda", "Caruaru"],
    "PI": ["Teresina", "Parnaíba"],
    "PR": ["Curitiba", "Londrina", "Maringá", "Cascavel"],
    "RJ": ["Rio de Janeiro", "Niterói", "Petrópolis"],
    "RN": ["Natal", "Mossoró"],
    "RO": ["Porto Velho", "Ji-Paraná"],
    "RR": ["Boa Vista"],
    "RS": ["Porto Alegre", "Caxias do Sul", "Pelotas", "Canoas"],
    "SC": ["Florianópolis", "Joinville", "Blumenau", "Chapecó"],
    "SE": ["Aracaju"],
    "SP": ["São Paulo", "Campinas", "Ribeirão Preto", "Santos", "Sorocaba", "São José dos Campos"],
    "TO": ["Palmas", "Araguaína"],
}

NAME_PREFIXES = [
    "Alta",
    "Brisa",
    "Campo",
    "Delta",
    "Estrela",
    "Fonte",
    "Girassol",
    "Horizonte",
    "Lagoa",
    "Monte",
    "Norte",
    "Oliva",
    "Pampa",
    "Raiz",
    "Serra",
    "Trilha",
    "Verde",
    "Vila",
    "Zelo",
    "Atalaia",
]
NAME_CORES = [
    "Alimentos",
    "Auto",
    "Casa",
    "Digital",
    "Engenharia",
    "Farma",
    "Grãos",
    "Hotel",
    "Info",
    "Jurídico",
    "Log",
    "Móveis",
    "Nuvem",
    "Obras",
    "Peças",
    "Redes",
    "Saúde",
    "Têxtil",
    "Urbano",
    "Varejo",
]

FIRST_NAMES = [
    "Ana",
    "Bruno",
    "Camila",
    "Diego",
    "Elena",
    "Felipe",
    "Helena",
    "Igor",
    "Juliana",
    "Kaique",
    "Larissa",
    "Marina",
    "Nicolas",
    "Olivia",
    "Paulo",
    "Renata",
    "Sofia",
    "Thiago",
    "Ursula",
    "Vitor",
    "Wanda",
    "Yasmin",
]
LAST_NAMES = [
    "Martins",
    "Carvalho",
    "Rocha",
    "Almeida",
    "Duarte",
    "Nogueira",
    "Pires",
    "Batista",
    "Fernandes",
    "Gomes",
    "Lima",
    "Moreira",
    "Azevedo",
    "Barbosa",
    "Cardoso",
    "Dias",
    "Farias",
    "Mendes",
]

OWNERS = [
    "Ana Martins",
    "Bruno Carvalho",
    "Camila Rocha",
    "Diego Alves",
    "Elena Duarte",
    "Felipe Nogueira",
    "Helena Pires",
    "Igor Batista",
]

STAGE_PROBABILITY = {
    "qualificacao": 0.18,
    "proposta": 0.42,
    "negociacao": 0.67,
    "ganho": 1.0,
}
