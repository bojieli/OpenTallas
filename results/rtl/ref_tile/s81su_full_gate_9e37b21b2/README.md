# s81su_full composition gate at 9e37b21b2 (branch claude/el1013-s81su-qual)

Hierarchical SU slab `dsfd_sp_su_h`, full shape, `tools/s81_suhc/su_gate.py run --shape full --hier` (DPI float models),
RTL with the pin-registered split taps (SW: `ot_s81_su_swtl` + `ot_s81_su_swth`; QB: `ot_s81_su_qbtl` + `ot_s81_su_swth`).
ot-epyc4, 2026-10-13. Exact: golden_L0 / golden_L2 / stress_0 PASS 0 / 1722 rows, 3,149 cycles.

Job cycles at the slab pins (start -> done, `run_full_dpi_m0_a0_h.json` `job_cycles`, identical in the three runs):
QN (kind 0) 301, KV (1) 357, QB (2) 167 and 167, SW (3) 353, SE (4) 387 and 466, SO (5) 303 and 303.

This record carries the positive run only; mutant 5 (stale denominator) runs in every loop job bound to the gate
(`tools/ref_tile/composition_gates.json` `s81su_full`). It is the measured basis of the accepted-cost rows SU.QB,
SU.SW and SU.SO; it does not qualify any tile (that is the routed-top gate `s81su_tiles`).
