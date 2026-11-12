"""Interface Streamlit de MaintAI : explorer les données, puis demander une prédiction à l'API.

Lancement (depuis la racine du projet) : python -m streamlit run ui/app.py
"""
import sys
from pathlib import Path

# `streamlit run` n'ajoute au sys.path que le dossier du script, ici ui/ : le paquet
# maintai/ reste donc invisible et `import maintai` échoue avec ModuleNotFoundError.
# On ajoute la racine du projet, calculée depuis __file__ (ui/app.py -> ui/ -> racine)
# et non depuis le dossier courant, pour que l'app se lance depuis n'importe où.
# À noter : pytest, lui, n'a pas besoin de ce correctif grâce à `pythonpath = .` dans pytest.ini.
RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

# Les imports suivent ce correctif, donc ils ne sont pas tout en haut du fichier :
# les noqa: E402 signalent aux linters que c'est volontaire et non un oubli.
import httpx  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from maintai.client import APIError, MaintaiClient  # noqa: E402
from maintai.config import FEATURES, get_settings  # noqa: E402

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

# ---------------------------------------------------------------------------
# Sprint 1 : explorer les données
# ---------------------------------------------------------------------------
with onglet_donnees:
    # Le chemin vient de la configuration (variable MAINTAI_DATA_PATH), jamais codé en dur :
    # les tests peuvent ainsi pointer vers un CSV temporaire sans toucher au code.
    df = charger(get_settings().data_path)

    # --- 1. Trois indicateurs côte à côte ---------------------------------
    # st.columns(3) découpe la largeur en trois ; chaque colonne est un conteneur
    # sur lequel on appelle .metric() au lieu de st.metric() pour y placer le contenu.
    col_releves, col_taux, col_temp = st.columns(3)
    # f"{len(df)}" : on formate nous-mêmes en texte, sinon Streamlit afficherait
    # l'entier avec un séparateur de milliers ("2 000") au lieu de "2000".
    col_releves.metric("Relevés", f"{len(df)}")
    # failure vaut 0 ou 1 : sa moyenne est donc directement le taux de panne.
    # Le format .1% multiplie par 100 et ajoute le signe % (0.0485 -> "4.9%").
    col_taux.metric("Taux de panne", f"{df.failure.mean():.1%}")
    col_temp.metric("Température moyenne", f"{df.temperature_c.mean():.1f} °C")

    # --- 2. Choix de la variable à étudier --------------------------------
    # On propose FEATURES (défini dans config.py) et non la liste des colonnes du CSV :
    # c'est le contrat d'entrée du modèle, et cela exclut la cible "failure".
    variable = st.selectbox("Variable à étudier", FEATURES)

    # --- 3. Taux de panne par tranche de cette variable -------------------
    # pd.cut découpe une variable continue en 8 tranches d'égale largeur : on passe
    # d'une valeur par machine à des groupes comparables entre eux.
    tranches = pd.cut(df[variable], bins=8)
    # On groupe par tranche et on prend la moyenne de failure = le taux de panne du groupe.
    # observed=True n'affiche que les tranches réellement présentes dans les données.
    taux_par_tranche = df.groupby(tranches, observed=True)["failure"].mean()
    # pd.cut renvoie des objets Interval, qu'Arrow (le format d'échange de Streamlit)
    # ne sait pas sérialiser : on remplace l'index par du texte "borne – borne".
    taux_par_tranche.index = [f"{t.left:.0f} – {t.right:.0f}" for t in taux_par_tranche.index]
    st.caption(f"Taux de panne par tranche de {variable}")
    # L'index sert d'axe X et les valeurs d'axe Y : une Series suffit, pas besoin de DataFrame.
    st.bar_chart(taux_par_tranche)

    # --- 4. Nuage de points température / vibration, coloré par panne -----
    # .assign ajoute la colonne sur une copie : le DataFrame mis en cache par charger()
    # n'est pas modifié (le modifier polluerait tous les reruns suivants).
    # On convertit 0/1 en texte car, avec une colonne numérique, Streamlit applique un
    # dégradé continu ; avec du texte il donne deux couleurs franchement distinctes.
    nuage = df.assign(etat=df.failure.map({0: "normal", 1: "panne"}))
    st.caption("Température et vibration, selon l'état de la machine")
    st.scatter_chart(nuage, x="temperature_c", y="vibration_mm_s", color="etat")


# ---------------------------------------------------------------------------
# Sprint 2 : demander une prédiction à l'API
# ---------------------------------------------------------------------------
with onglet_prediction:
    # st.form regroupe les champs : le script n'est relancé qu'au clic sur le bouton,
    # et non à chaque mouvement de curseur — donc un seul appel à l'API par envoi.
    with st.form("releve"):
        releve = {
            "temperature_c": st.slider("Température (°C)", -40.0, 150.0, 72.0),
            "vibration_mm_s": st.slider("Vibration (mm/s)", 0.0, 50.0, 6.0),
            "load_pct": st.slider("Charge (%)", 0.0, 100.0, 85.0),
            "runtime_hours": st.number_input("Heures de fonctionnement", 0, 100_000, 15000),
        }
        envoye = st.form_submit_button("Prédire")

    # envoye ne vaut True que sur le rerun déclenché par le bouton du formulaire.
    if envoye:
        # L'URL et la clé viennent de la barre latérale : l'interface ne sait rien du modèle,
        # elle ne parle qu'à l'API. `cle or None` transforme un champ vide en None, pour que
        # le client n'envoie pas un en-tête X-API-Key vide.
        api = MaintaiClient(url, api_key=cle or None)
        try:
            resultat = api.predict(releve)
        # Deux pannes de nature différente, donc deux messages différents.
        # APIError : l'API a bien répondu, mais elle refuse (401 clé invalide,
        # 422 relevé hors bornes, 503 modèle non chargé). L'utilisateur peut corriger
        # lui-même -> st.warning (jaune), avec le code et le message renvoyés par l'API.
        except APIError as erreur:
            st.warning(f"L'API a refusé le relevé (code {erreur.status_code}) : {erreur.detail}")
        # httpx.HTTPError : aucune réponse (serveur éteint, mauvaise URL, délai dépassé).
        # Le relevé n'est pas en cause, c'est une panne technique -> st.error (rouge).
        except httpx.HTTPError:
            st.error("API injoignable : vérifiez l'URL et que le serveur est démarré.")
        # Le bloc else ne s'exécute que si aucune exception n'a été levée : l'affichage du
        # résultat reste donc hors du try, et un bug d'affichage ne serait pas confondu
        # avec une erreur de l'API.
        else:
            # L'API renvoie une probabilité entre 0 et 1 ; on l'affiche en pourcentage entier.
            pct = round(resultat["failure_probability"] * 100)
            st.metric("Probabilité de panne", f"{pct} %")
            # Le seuil de décision est fixé par le serveur (MAINTAI_THRESHOLD) et renvoyé dans
            # la réponse : l'interface l'affiche, mais ne décide pas à la place du modèle.
            seuil = resultat["threshold"]
            if resultat["alert"]:
                st.error(f"⚠️ ALERTE : panne probable (seuil {seuil:.0%}) — planifier une maintenance.")
            else:
                st.success(f"Fonctionnement normal (probabilité sous le seuil de {seuil:.0%}).")
            # Afficher la version du modèle : indispensable pour savoir, plus tard,
            # quel modèle a produit telle prédiction.
            st.caption(f"Modèle : {resultat['model_version']}")
