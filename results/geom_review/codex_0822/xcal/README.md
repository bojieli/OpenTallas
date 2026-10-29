# XCAL reset landing review

2026-10-29 08:26 PDT, independent Codex reviewer. Source kit:
intel1:/srv/opentallas-scratch2/claude/hbm-cores-kits-12/k5/kits/ot_hbm_svc_sm_xcal_rel_t_59bcf8ea762e-_k12d16v,
claude/hbm-cores-kits-12-1029@ce37f720e6, placed view AUTO-GEOM 2cb60c16adfe.

Personally viewed `auto_geom.png`: four SRAMs leave a W logic column, central
horizontal/vertical streets, and an open N strip. Clock entry sits in the central
street junction. There is no macro wall across the logic column or cells on the
macros. The dense W column matches the W bus pins. Channel projection warnings
are understood against the existing zero-overflow run.

Verdict: CONCUR with GEOM-57 FAIL as-is for the reset landing. The current
rst_n pin to reset flop distance is 200.02 um; all other pin distances are <=7 um
(existing measured auto_geom.json and GEOM-57 trace). This is a local placement
defect with an available structural repair: anchor u_fcore.rst_q, and its partner
if present, in the free N strip beside rst_n around x115..125/y213..224. The
picture shows sufficient strip space without moving any macro or changing the
pin table. Re-place and review the new pin-to-reset and reset-to-load reach;
the owner should confirm legal rows/PG there. Do not route the conflicted view.

No new probe, rule, RTL, clock or latency change. Existing r2r max322.49 um,
0 arcs >405, and zero cells on macros are recorded in the attached measurement.
This review does not claim CTS or sign-off.
