# Gates (Grenzen, Einmaligkeit, Kombinatorik)

## Einmaligkeit
- **Scaffold** (Imports, Page-Config, EE-Auth) erscheint **genau einmal** und **immer zuerst**.
- **Acquire**: pro gewählter UC-Variante **genau eine** Datenbeschaffung.
- **Render**: pro App **genau ein** konsistenter Render-Pfad der gewählten UC-Variante.

## Kombinatorik
- **Process/Normalize/Mask** nur, wenn in der UC vorgesehen (z. B. LST-QA-Maske, S2 `/10000`).
- **Visualize** nutzt **exakt** die definierten Paletten/Min-Max/Band-Triplets; **keine** Alternativen.
- **Render** muss zur UC-Variante passen (Split-Map rechts, Charts, GIF, Expander – wie in Vorlagen).

## Benennungen & Zustände
- Bewahre die **Original-Bezeichner** (z. B. `no2_vis`, `MAP_PARAMS`, `ghsl_vis`).
- Nutze `st.session_state` nur wie in den Vorlagen (z. B. `zoom_level` setzen/auslesen).

## Fehlerfälle
- Bei externen Ressourcen (z. B. NDVI-GIF) zeige die **vorgesehene** Fehlermeldung/Guidance.
- Bei leeren Kollektionen (z. B. S2 in seltenen Quartalen) weise **textuell** auf andere Zeiträume/Orte hin.

## Keine Erfindungen
- Keine neuen Konstanten, Paletten, Bänder, Alternativ-Pipelines.
- Keine Mischformen aus UC-Varianten.
- Keine zusätzliche UI, die nicht in der Vorlage existiert.

