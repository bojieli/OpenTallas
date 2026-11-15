# S81-SVC-H16 handoff (successor of S81-B3-SVC), 2026-11-14 PST

## Result
EMPTY geometry delta: the v2g svc geometry has no H16 form, and B6c1's H16 svc rows are already legal.
Delta file (epyc7): /srv/opentallas-scratch2/claude/s81-svc-h16/svc_h16_delta.json (sha12 ecd675ba9ac3)
  types {}, sidecar_rows {}, latency_rows {}; base ev/B6c1.json ae869d5e0b7d, ev/side_B6c1.json 7293070650f7. Merged plan == B6c1 byte for byte.

## Measured on B6c1 (H16), 16 svc types (script mk.py / aud.py in the same dir)
- Every type: 0 overlap, 0 out-of-bounds, hard+SRAM area fraction 0.70-0.73.
- H16 hard cores per type: 72 (64 ot_s81c_attn_hcore + 8 dsdv_svc_sx_hrow), nothing else. v2g (H8): 66 hi / 98 lo hard providers
  (smc smr trx sml smd merge_h4 idx_hslice_fp), SRAM 76 hi / 97 lo; B6c1: 45 hi / 66 lo. pvso t1/t2 keep 72 hard + 181 SRAM.
- Die B6c1 32244.48 x 25980.48; reticle 33000 x 26000: Y spare 19.52 um, X 755.52 um. No room to grow svc outlines (v2g lo 2998.08 vs B6c1 2980.8 already).
- B3x2b/B3x2d H16 strict bind RC0, no svc error. 

## Not carried (all H8-specific)
lo 98+97 row pack; hi/lo 1702.08 width; pvso g_h[8..15] drop; t7 u_rg3 rename + rg3_nq dissolve; 13 declared_ties
(OT_SVC_H8 / HSLICE_FASTPAD defines); t6 +1 ft station and 3 latency rows (lo re-pack consequence).
## Carried
-DOT_SVC_ATT_MEM_MACRO value-less + dsdv_idx_rg2.sv: B6c bind DEFS_ADD + kit VERILOG_DEFINES, no plan row.

## Open for DIE-S81-92 / TYPE-SVCMEM
- After the B6c bind with the define: if TIED rows appear on rg2_m1k / mem_ar / v41x_dly ports, re-prove from declared_ties_svc_h8_b3svc.json
  (patchset epyc7 s81-b3-svc/patchset_b3svc), map instance names to the H16 netlist.
- R-CAP is separate: H16 flat svc type about 4.1 M cells (S81-CORES-2 11-13) vs 400k tool cap; the owner's 11-14 cell-cap removal applies. Not measured again here.
- S81-B3-SVC bind b3 on v2g: 9 CLK-class errors only (col_h9 tap radius, 3 lo collector reach); moot on H16.
No job of mine running.

G0: merged plan == B6c1 (identity delta), so DIE-S81-92 G0 run/b/B6c1g (started 20:48 PST, still running at 22:1x) is the proof; read its g0.log/rc. Not re-run.
