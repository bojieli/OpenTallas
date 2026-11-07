plan_qc53_candidate_v4 = v3 + fix-only START raw reset re-pick (COORD 22:2x, DIE-QC-85 11-06).
Why: START4 stored relay names picked on the v2 trees. The tap class and resite renumber those relays. In v3, 9 types
fail bind (name gone) and more pass silently with a moved relay (wrong site/depth). 18 types, 391 references.
What changes: only raw_reset / landing_local_resets raw (and that copy xy) on references whose relay moved, using the
START4 rule: nearest non-exported non-port live relay; local copies keep depth(raw)+1 == old consumer reset depth.
Stage xy, depths and stage counts stay. reset.relay_resite_crossing = true (tool default is now off).
Rerun: dump_pre.py dumps the bound type bodies before landing emission; repoint.py reads them. Bind inputs need the
Codex START4 runtime manifest (qc_start_1106/runtime/{asbuilt,sidecar}.json), which is not on main.
