"""
Mini-Helfer: Preset-vis_params mit evtl. benötigten Bands aus invariants zusammenführen.
Wirft eine klare ValueError, wenn 'bands' erforderlich ist und kein Default herleitbar ist.
"""

from typing import Dict, Any

def merge_vis_params(preset_vis: Dict[str, Any], invariants: Dict[str, Any], preset_id: str | None = None) -> Dict[str, Any]:
    """
    Purpose:
        Merged vis_params zurückgeben. Falls 'bands' fehlt, versuchen aus invariants eine sinnvolle
        Voreinstellung zu nehmen (z. B. bei S2 via 'map_params' + 'default_viz_type').
    Args:
        preset_vis: dict mit min/max/palette/opacity/... (evtl. ohne 'bands')
        invariants: UC-Invarianten (z. B. map_params:{name->[B1,B2,B3]}, default_viz_type)
        preset_id: optionale Kennung (nur für Fehlermeldungen)
    Returns:
        dict mit vollständigen vis_params (inkl. 'bands', falls sinnvoll)
    Side-effects:
        Keine.
    """
    vis = dict(preset_vis) if preset_vis else {}

    # Bands-Ableitung (z. B. Sentinel-2)
    if "bands" not in vis:
        mp = invariants.get("map_params")
        if isinstance(mp, dict) and mp:
            dv = invariants.get("default_viz_type")
            if dv and dv in mp:
                vis["bands"] = mp[dv]
            elif len(mp) == 1:
                vis["bands"] = next(iter(mp.values()))
            else:
                raise ValueError(
                    f"vis_params fehlen 'bands' und invariants enthalten mehrere map_params ohne default_viz_type."
                    f"{' (Preset: ' + str(preset_id) + ')' if preset_id else ''}"
                )

    # Minimal-Checks
    for k in ("min", "max", "palette"):
        if k not in vis:
            raise ValueError(f"vis_params fehlen Schlüssel '{k}'.{' (Preset: ' + str(preset_id) + ')' if preset_id else ''}")

    return vis
