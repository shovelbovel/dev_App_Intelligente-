"""Interface Streamlit de MaintAI : explorer les données, puis demander une prédiction à l'API.

Lancement (depuis la racine du projet) : python -m streamlit run ui/app.py
"""
import httpx
import pandas as pd
import streamlit as st

from maintai.client import APIError, MaintaiClient
from maintai.config import FEATURES, TARGET, get_settings

st.set_page_config(page_title="MaintAI", page_icon="🔧")
st.title("MaintAI · prédiction de panne")


@st.cache_data
def charger(path) -> pd.DataFrame:
    # Lu une seule fois : Streamlit relance tout le script à chaque clic
    return pd.read_csv(path)


with st.sidebar:
    url = st.text_input("URL de l'API", "http://localhost:8000")
    cle = st.text_input("Clé API", type="password")

onglet_donnees, onglet_prediction = st.tabs(["Données", "Prédiction"])

# Sprint 1 : explorer les données
with onglet_donnees:
    df = charger(get_settings().data_path)

    # Les trois indicateurs : volume, taux de panne, température moyenne
    col_releves, col_taux, col_temp = st.columns(3)
    col_releves.metric("Relevés", f"{len(df)}")
    col_taux.metric("Taux de panne", f"{df[TARGET].mean():.1%}")
    col_temp.metric("Température moyenne", f"{df['temperature_c'].mean():.1f} °C")

    variable = st.selectbox("Variable à examiner", FEATURES)

    # pd.cut découpe la variable en tranches ; la moyenne de la cible y donne le taux de panne
    taux = df.groupby(pd.cut(df[variable], bins=8), observed=True)[TARGET].mean()
    taux.index = taux.index.astype(str)  # Arrow ne sait pas sérialiser des intervalles
    st.caption(f"Taux de panne par tranche de « {variable} »")
    st.bar_chart(taux)

    st.caption("Température et vibration, selon l'état de la machine")
    st.scatter_chart(
        df.assign(etat=df[TARGET].map({0: "normal", 1: "panne"})),
        x="temperature_c",
        y="vibration_mm_s",
        color="etat",
    )


# Sprint 2 : demander une prédiction à l'API
with onglet_prediction:
    with st.form("releve"):
        releve = {
            "temperature_c": st.slider("Température (°C)", -40.0, 150.0, 72.0),
            "vibration_mm_s": st.slider("Vibration (mm/s)", 0.0, 50.0, 6.0),
            "load_pct": st.slider("Charge (%)", 0.0, 100.0, 85.0),
            "runtime_hours": st.number_input("Heures de fonctionnement", 0, 100_000, 15000),
        }
        envoye = st.form_submit_button("Prédire")

    if envoye:
        api = MaintaiClient(url, api_key=cle)
        try:
            resultat = api.predict(releve)
        except APIError as e:
            # L'API a répondu, mais elle refuse : clé invalide (401) ou relevé hors bornes (422)
            st.warning(f"L'API a refusé la demande (code {e.status_code}) : {e.detail}")
        except httpx.HTTPError:
            st.error(f"API injoignable : vérifiez qu'elle est lancée et que l'URL « {url} » est correcte.")
        else:
            seuil = resultat["threshold"]
            st.metric("Probabilité de panne", f"{round(resultat['failure_probability'] * 100)} %")
            if resultat["alert"]:
                st.error(f"ALERTE : probabilité au-dessus du seuil de {seuil:.0%}, maintenance à planifier.")
            else:
                st.success(f"Fonctionnement normal : probabilité sous le seuil de {seuil:.0%}.")
            st.caption(f"Modèle {resultat['model_version']}")
