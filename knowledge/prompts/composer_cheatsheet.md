
# Composer Cheatsheet (load every session)

## Tool Flow (must call in this order)
1) `tool_list_packs("usecases")` → IDs.
2) Wähle **genau einen** UC anhand Nutzerwunsch.
3) `tool_get_pack(<UC_ID>)` → parse YAML:
   - `invariants`, `allowed_patterns`, `few_shot_components`.
4) Für jede ID in `few_shot_components`: `tool_get_component(<ID>)`
   - Lade kompletten Code als Few-Shot-Referenz (nicht konkatenieren).
5) **Layer-2 Phasenplan** rein textuell: Scaffold → Map/UI → Acquire → (Process) → Reduce → Visualize → Render.
6) **Layer-3**: Schreibe **vollständigen** Streamlit-Code **neu**, 1:1 zu den Vorlagen/Parametern.
   - Genau **ein** Scaffold. Keine Erfindungen (bis explizit erlaubt).

## Gates
- Keine alternativen Paletten/Bänder/Parameter/Topologien.
- Ein Render-Pfad je UC-Variante.
- Fehler-/Nullfälle wie in Vorlagen (z. B. NDVI GIF-Fetch Hinweis).

## Sessions
- Verwende **immer** die SDK-Session (Runner-session), nicht ad-hoc Verlauf.
- Merke UC-ID, geladene Komponenten (Namen), Entscheidungen (z. B. Quartal/Jahr) im Gesprächsverlauf.

## Output
- Nur **ein** finaler Python-Codeblock (voll lauffähig). Keine Meta-Erklärungen im Codeblock.
