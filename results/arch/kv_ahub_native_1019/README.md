# AHUB a7 source and native binding review

The CLOSED leaf is timing evidence for source `c6c412b4c250192dbf1124198d7e44fb80e01bca`, record `0770ddeba`. Its reported TT setup is +8.48 ps, FF hold +8.83 ps, DRC 0. SS sensitivity is -354.82 ps. This packet does **not** qualify the KV parent binding.

`6d71d97e9` imports the exact `qkd_ahub_static_dw.sv` body and seven-calendar s4o bench. The retained root-select stage, RX stage and two reciprocal-return stages require publication at reciprocal issue +75 edges. `kv_static_programme.attention_calendar` now prices this die-specific law before selecting PV_START/R and checking a fixed service slot. The shared native reference remains +73. The W-face relay emits one edge earlier internally, retaining the compiled FR export edge. No static slot is stretched silently.

The qkd_ahub_core support file differs from the old closure lineage in unrelated legacy modules. Its `ot_qkd_drly` dependency is byte-identical. The other five listed support source files are byte-identical to the CLOSED source. All seven source hashes are recorded in `native_review.json`.

`77c52192f` repairs two concrete binding audit gaps: the actual CLOSED JSON uses sized SV literals (`64'hffddffdeffdcffdc`, `32'hfffffff9`), and a die instance overriding only Z_IN_STRIDE still uses AP/FR defaults. The audit now parses these literals and records default-only instances for comparison. Malformed/out-of-range literals remain errors.

The following parent obligations remain open:

- Exact native LEF is 734.4 x **540** um. Recovery source uses 734.4 x **561.6**. Closed source spec also says 540; its historical prose still mentions the older outline.
- Exact CLOSED parameters are Z_IN_STRIDE=4, AP_OFS=[-36,-36,-34,-35] (WS,WN,ES,EN), FR_OFS=-7. Actual GEN7 `port_bind_v2/die_bound.v` overrides only Z_IN_STRIDE=4. The completed actual seam table must establish the needed offsets. A different parameter binding needs its own physically qualified view.
- Parent currently places grouped ports at spec range centres. Native scalar pins differ: ck centre x359.004/y539.958; rst_n x301.980/y539.958; hs_start x196.572/y539.958, while hs_cal_lo[0] is x410.652/y539.958. Grouping the hs word at one centre cannot establish native geometry or per-bit reach.
- Actual routed `insertion.json` uses 6_final.odb and SPEF. TT boundary extrema across 625 flops are 914.5..1003.4 ps (88.9 ps); FF 717.5..770.3 (52.8 ps). This is a clock qualification gap, despite the CLOSED timing verdict. Parent-relative matching and actual per-path native clocks remain required; absolute insertion alone is not a reason to reject or split the tile.
- Native children are four ot_nhb_zh and one ot_qkh_recip_leaf. This packet does not claim a new licensed SRAM native-contact audit; any opaque child descendants still require their existing native records.
- Actual parent TT/FF timing, loop data/clock pairing and reset release remain required after exact native frame/pins and offsets are incorporated. GEN7 is preserved as a source/age diagnostic and is not patched in place.

Fleet component validation lives at `ot-epyc6:/srv/opentallas-scratch/claude/codex-kv-ahub-native-1019`. Initial setup failures (missing pytest, then missing immutable image/law/macro inputs) are preserved separately. None ran RTL or yielded a PASS. The final driver executes the three calendar checks directly and runs the exact imported Verilator 5.050 s4o positive and root-select-bypass mutant.

Final source-compatible proof: all three calendar checks and all three closed-parameter checks PASS. Verilator 5.050 s4o positive PASS: seven calendars, 680 Z words, seven FR pulses and seven 32-beat results; m11 root-select relay bypass FAIL: 235 errors, first cycle 1860. Logs and the exact positive source manifest are included.

Actual routed native pin audit **FAILS**: canonical `pinreg_audit` functions applied to exact record TT Liberty and 6_final insertion report launch 458.07915 ps at fr_rz[18] (286 outputs over 220 ps), capture 225.07728 ps at ap3[42] (304 inputs over 190 ps), zero combinational pins. The measured native reference is 953.3 ps. A uniform parent compensation would need C >=1191.37915 ps for launch and C <=918.22272 ps for capture, so no uniform value meets both budgets. TT spread also exceeds 80 ps. `routed_native_metrics.json` records hashes, raw metrics and the infeasible interval. A fresh structural successor must address real input/output geometry and clock matching; changing the recorded clock reference cannot qualify this leaf. No new route was launched.
