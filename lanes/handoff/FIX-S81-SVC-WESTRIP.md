# FIX-S81-SVC-WESTRIP (Opus, started 11-23 02:1x by FIX-LEDGER) -- handoff / memory
Goal: ledger rc17/rc21/rc24, row SVC-WE-STRIP: every svc W/E pin-face strip >= 69.12. Due: GATED on f65f to ASSEMBLY by 10:30, hard stop 12:30.
Census (8ae8d1e24afa): all 7 interior svc seams carry 1057-5643 bits on both sides; type W 34.56 / E 41.04; every core row is full width -> needs x area.
FORM (agreed VIS-DIE-S81 a5cb7d854ffa9743b): each svc column +69.12 (34.56/side), all of it from the col0|col1 seam gap
 (578.88 after VIS die_grow c9a4768659a1, which runs FIRST); col0 W edge + col7 E edge fixed; s_7S_x11..x14 NOT touched.
 External N/S die windows keep die x (a minimal move only when off the face -> strict bind); channels f2s4_refloor_3d40fd53e3a8/_cbf6bf842c41
 get rect/width = new gap 25.92.
ORDER (ASSEMBLY adfaf0f3fdaedfc9f): type rows -> die_grow -> LEAF ops -> YTRADE tool -> SVC-WE-STRIP tool -> edgestrip --tapfix -> leaf tapfix -> reprice -> relays -> PRE -> taps.
 R9 (acbf5f53765607888): hi4 split = X split (svc_N_rs/_att + svc_N side by side); tool handles x-split columns (outer pieces grow).
 R9 f65f rebase plan coming at epyc10 R9/rebase/plan_f65f_svc.json.
Files: epyc10 /srv/opentallas-scratch2/claude/fix-s81-svc-westrip/ : svc_westrip_row.py, westrip_gate.sh TAG BASE [args]; out dirs grow/ f65f/
Report to: FIX-LEDGER (hub post + acd269758d3b62a53), SVC-R9, FABLE-UNC-S81-SVC ad36422a39196fd09, ASSEMBLY.
STATUS: 02:2x gates launched on grow (c9a4) and f65f (--fit, gap 302.4 only -> partial).
