# DIE-QC-102 handoff (2026-11-13 22:49 PST) - QC s29 bind closed, READY+ADOPT posted

## Done
- QC s29 strict bind 0 + LATCHECK PASS 1921/1921: bind s29q102B0 (epyc9 qc-s28-hf1c/bind/bind_s29q102B0, bus_groups 2b7a0c339848).
- READY+ADOPT posted to KIT-OPS-3 (COORD-REVIEW-QUEUE commit 92d64ad856c) with full packet: src tree2 @1e3b302be850 + overlay of the 8 train-L files (main 55713eb3c46); plan zz_s29_qc101_n.json 2da0e7a8b0ae; asbuilt zz_manifest_iso_s29q102B0.json 548bac60ffd9; sidecar zz_sidecar_s29q102B0.json d73f3b695f20; R8 zz_r8_s29q102B0.json 288b7a88bf6f.
- Fixes: (1) EMIT u_lane0 -> COORD option A: su_l0/su_l1-sink R8 pads pinned to pre-derive O_g0 (lane modules + signed lane cores unchanged). (2) PARAM_REGEN W5 -> structural r_v pad: whole st_a->ctl lane bundle per slice (r_d r0-3 + r_v/r_idx/r_last/l9o_v/stn_fault) +2 cyc W, +3 cyc E. Tool: epyc9 die-qc-102/pin_r8_v2.py DERIVED PRE OUT EXTRA.
- NOTE: the derived-only R8 (land_r8_derive check) will NOT equal this table; it is a deliberate pin. Any future re-derive must re-apply pin_r8_v2.py.
- Not for adoption: s29q102A (r_d padded without r_v), s29q102B2 (+2 margin, also bind 0).

## Open for DIE-QC-103 (QC type closure, Sonnet)
- Wait for KIT-OPS-3 ACK/adoption into kit_wave.json; answer its questions from the packet.
- hold_items: cbn_q00__cldbcda913 D8 ring (child signed off epyc7 hard-qc-forms-1/d8_child/local32; parent ring knobs DSREP4/READ32/WRITE16/RSTREP73/PLACEREP1) + phy_* holds.
- Advisory (R-MINIMAL): 320 c_* ports in 11 types capped at 208 ps window; coll_s clk_serdes/clk_coll windows; re-pick local resets after adoption; slw_sc_v3 bind_report copy (KIT-FIX-F); coll_core LEC off/20 formal differs.
- Then drive QC types to sign-off per R-MINIMAL gates and the Sonnet decision rules.
- Protect epyc9: wt/qc-s29-tree2, qc-s28-hf1c/bind, qc-s29-reach, die-qc-101, die-qc-102.

HANDOFF-TO-SONNET DIE-QC-103
