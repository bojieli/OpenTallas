# TYPE-S81-GRTCAP handoff (2026-11-14 09:10 PST)
## Findings
- kv_leaf__t4 a10 (job 6653494b40bf): GRT full route converged in 1900 s, overflow 0/0/0 (6.52% usage). The 21.6 ks cap hit in post-GRT repair_design (OT_MAXWIRE 120 um, 349,319 nets; 237k done in 19.7 ks, ~12 nets/s, single thread; est ~29 ks total). Slow but progressing, NOT congestion. Lift cap.
- serdes__t2 (job 8a83667edb33, a27): cap hit in post-GRT HOLD repair at hold ws -180 ps, setup -101 ps, TNS -64029; a27 geometry TT -1101 (KP4 island misplaced, bare-wire paths). Lifting the cap would not close it; the fix is the HARD-S81-SERDES-1 redesign (template + cone defines, kitC/H2/G3 in flight, owner Codex). No cap-only relaunch of a27 (same inputs).
## Run
- Private form A: kit copy epyc2:/srv/opentallas-scratch3/claude/type-s81-grtcap/gen/ot_s81sl_kv_leaf__t4 (from epyc9 a10 gen, config.mk mtime preserved so RESYNTH-GUARD is quiet) + export OT_GRT_POST_MAX_S = 0. Unit type-s81-grtcap-kvt4-a on intel2, log ~/type-s81-grtcap-logs/kvt4_a.log, ot-run --hosts epyc2,intel1 route 48 8.
- Next: on pass (DRC 0, TT setup >= -42, FF hold >= 0) add AUTO-RESIGN row, archive DB+view+signoff.json to AGIdock /archive/opentallas-signed-1114/s81/ot_s81sl_kv_leaf__t4/ and rtx-pro ~/signed-export-1114/.
