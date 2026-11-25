"""Dashboard da base fictícia de CRM da Nexora."""

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Nexora · CRM PME",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).parent
navigation = st.navigation(
    [
        st.Page(APP_DIR / "views" / "inicio.py", title="Início", url_path="inicio", default=True),
        st.Page(APP_DIR / "views" / "funil.py", title="Funil", url_path="funil"),
        st.Page(APP_DIR / "views" / "receita.py", title="Receita e MRR", url_path="receita"),
        st.Page(APP_DIR / "views" / "retencao.py", title="Retenção e coortes", url_path="retencao"),
        st.Page(APP_DIR / "views" / "segmentacao.py", title="Segmentação", url_path="segmentacao"),
    ]
)
navigation.run()
