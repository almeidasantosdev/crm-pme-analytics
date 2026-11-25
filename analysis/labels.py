"""Rótulos de exibição. Códigos no dado ficam em inglês; a prosa é pt-BR."""

CHANNEL = {
    "organic": "Orgânico",
    "referral": "Indicação",
    "google_ads": "Google Ads",
    "linkedin_ads": "LinkedIn Ads",
    "event": "Evento",
    "outbound": "Outbound",
    "partner": "Parceiro",
    "email": "E-mail",
}

PORTE = {
    "mei": "MEI",
    "micro": "Microempresa",
    "pequena": "Pequena",
    "media": "Média",
}

SECTOR = {
    "comercio_varejo": "Comércio varejista",
    "comercio_atacado": "Comércio atacadista",
    "servicos_profissionais": "Serviços profissionais",
    "industria": "Indústria",
    "tecnologia": "Tecnologia",
    "saude": "Saúde",
    "educacao": "Educação",
    "alimentacao": "Alimentação",
    "logistica": "Logística",
    "construcao": "Construção",
    "agronegocio": "Agronegócio",
    "beleza_bem_estar": "Beleza e bem-estar",
}

PLAN = {
    "essencial": "Essencial",
    "profissional": "Profissional",
    "enterprise": "Enterprise",
}

STAGE = {
    "qualificacao": "Qualificação",
    "proposta": "Proposta",
    "negociacao": "Negociação",
    "ganho": "Ganho",
}

SEGMENT = {
    "champion": "Campeões",
    "loyal": "Leais",
    "promising": "Promissores",
    "recent": "Recentes",
    "at_risk": "Em risco",
    "hibernating": "Hibernando",
    "regular": "Regulares",
}

CHURN_REASON = {
    "preco": "Preço",
    "produto": "Produto",
    "suporte": "Suporte",
    "concorrente": "Concorrente",
    "encerrou_atividade": "Encerrou a atividade",
    "baixo_uso": "Baixo uso",
}

LOSS_REASON = {
    "preco": "Preço",
    "concorrente": "Concorrente",
    "sem_budget": "Sem orçamento",
    "sem_fit": "Sem aderência",
    "sem_resposta": "Sem resposta",
    "timing": "Timing",
}

ROLE = {
    "decision_maker": "Decisor",
    "champion": "Influenciador",
    "user": "Usuário",
    "finance": "Financeiro",
}

UF_NAME = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapá",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "PA": "Pará",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "PR": "Paraná",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RO": "Rondônia",
    "RR": "Roraima",
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "SE": "Sergipe",
    "SP": "São Paulo",
    "TO": "Tocantins",
}

MONTH_PT = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)


def label(mapping: dict[str, str], code: str) -> str:
    return mapping.get(code, code)
