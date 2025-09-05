# blocks/components/util/scaffold.py
"""
Purpose
-------
Setzt die Streamlit Page-Konfiguration und stellt eine gecachte Earth Engine
Initialisierung via geemap bereit. Keine Use-Case-spezifischen Konstanten.

Contracts
---------
- st.set_page_config(...) wird bei Import gesetzt.
- ee_authenticate(token_name: str = "EARTHENGINE_TOKEN") -> None
  Initialisiert EE genau einmal (Caching durch @st.cache_data).

Args
----
token_name : str
    Name der Umgebungsvariable/Credential-Quelle für geemap.ee_initialize.

Returns
-------
None

Side Effects
------------
Setzt die Streamlit-Page-Konfiguration. EE-Session wird initialisiert (gecached).

Notes
-----
- Keine UI- oder GEE-spezifischen Presets hier hinterlegen.
- Keine weiteren Abhängigkeiten hinzufügen.
"""

import json
import ee
import geemap
import streamlit as st
from geemap.foliumap import Map  # häufig genutzt in Render-Komponenten

# Page-Konfiguration
st.set_page_config(
    page_title="<INSERT APP TITLE HERE>",
    page_icon="🌡️",
    layout="wide",
)

def _parse_key_from_secrets():
    """
    Akzeptiert sowohl:
      - st.secrets["EE_PRIVATE_KEY"] als JSON-String
      - oder bereits als Dict (z. B. wenn per TOML-Block eingefügt)
    """
    key_val = st.secrets.get("EE_PRIVATE_KEY")
    if key_val is None:
        raise RuntimeError("EE_PRIVATE_KEY fehlt in streamlit secrets.")
    if isinstance(key_val, dict):
        return key_val
    if isinstance(key_val, str):
        key_val_str = key_val.strip()
        # Manche UIs speichern dreifach gequotete Strings → einfach json.loads versuchen
        return json.loads(key_val_str)
    raise RuntimeError("EE_PRIVATE_KEY hat unbekanntes Format (weder str noch dict).")

@st.cache_data
def ee_authenticate(token_name: str = "EARTHENGINE_TOKEN") -> None:
    """
    Initialisiert Earth Engine einmalig anhand der Streamlit-Cloud-Secrets.
    Erwartete Keys:
      - EE_PROJECT
      - EE_SERVICE_ACCOUNT
      - EE_PRIVATE_KEY  (ganzer JSON-Inhalt des Service-Account-Keys)
    Hinweis: Der Parameter token_name bleibt für Rückwärtskompatibilität erhalten,
    wird hier aber nicht verwendet (Secrets-basierte Initialisierung).
    """
    if st.session_state.get("_ee_ready"):
        return

    project = st.secrets.get("EE_PROJECT")
    service_account = st.secrets.get("EE_SERVICE_ACCOUNT")

    if not project:
        raise RuntimeError("EE_PROJECT fehlt in streamlit secrets.")
    if not service_account:
        raise RuntimeError("EE_SERVICE_ACCOUNT fehlt in streamlit secrets.")

    key_dict = _parse_key_from_secrets()

    # Credentials aufbauen und EE initialisieren
    credentials = ee.ServiceAccountCredentials(email=service_account, key_data=json.dumps(key_dict))
    ee.Initialize(credentials=credentials, project=project)

    st.session_state["_ee_ready"] = True
