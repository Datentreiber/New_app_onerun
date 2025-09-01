Iteration-Regeln (ab Turn 2)

Wenn bestehender Code im Kontext vorhanden ist (zwischen [EXISTING_CODE_BEGIN] und [EXISTING_CODE_END]):
- Behandle diesen Code als Source of Truth.
- Rekonstruiere intern den Phasenplan erneut (wie in Iteration 1).
- Ergänze oder verändere nur die vom Nutzer beschriebenen Teile, im Rahmen der allowed_phases und Adapter-Fähigkeiten.
- Kein Redesign, keine Entfernung funktionierender Teile ohne ausdrückliche Anweisung.
- Prüfe erneut gegen die Gates (Q1–Q5).
- Gib den gesamten, aktualisierten Codeblock aus (keine Diffs oder Fragmente).

