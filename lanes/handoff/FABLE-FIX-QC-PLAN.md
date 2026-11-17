# FABLE-FIX-QC-PLAN handoff (QC S4q9m plan chain -> CB16-qualifying bind)

## 2026-11-17 03:3x start
- Scope: M4 (zz_s29_qc103_s4q9m4.json 32bba5467a18, side 5787a70f3b01) to a bind meeting CB16: 0 errors, extra e2f94854 468/468, R8 pinned PASS, column pads <= 9, LATCHECK 1921/1921, hcparam 0, G0 0 latency.
- Decision (1): 5 new st_a masters (COORD + FABLE-CLOSURE-STRATEGY-0320); no restore in M. From N: st_a/st_b QFT params = equality constraint at compose time.
- Live work of others, not duplicated: QC-PLAN-M4 replay E2 oth-ubuntu-1550993 (knee-hc/gates/m4_prebind_1117), G0 m4_1117/gates/g0; QC-TYPES-R builds the 5 masters; QC-CLK-R2 recuts 3 sle_st_b_v1 rows.
- My dir: E2 /srv/opentallas-scratch3/claude/fable-fix-qc-plan/ (replay v3 copy + runs).
- Next: review replay coverage holes; add chain-manifest, kit-rtl/cm/kp/latcheck-CLI and CB16-criteria stages; launch M4BR/BQ via ot-run --priority plan only on a clean replay with the rows folded.
