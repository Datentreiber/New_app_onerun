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

import geemap
import streamlit as st
from geemap.foliumap import Map  # häufig genutzt in Render-Komponenten

# Page-Konfiguration
st.set_page_config(
    page_title="<INSERT APP TITLE HERE>",
    page_icon="🌡️",
    layout="wide",
)

@st.cache_data
def ee_authenticate(token_name: str = "EARTHENGINE_TOKEN") -> None:
    """Init Earth Engine via geemap; cached to avoid repeated init."""
    geemap.ee_initialize(token_name=token_name)
