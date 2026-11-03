# S81 svc_lo idx fit (DIE-S81-51/MEM, 2026-11-03)

Right-sized landing / queue memories of the paired index reader `dsdv_idx_rg3` in the 7 svc_lo types
(`svc_lo_dsdv_svc_rs__t1..t6`, `svc_lo_dsdv_svc_rs_w__t1`). Shared sources are untouched: the closure tool
(`tools/die_plan/s81_svc_memory_closure.py --form v2`) generates the closure child `dsdv_idx_rg3_fit` from the
kit's own `portfix178/dsdv_idx_rg3.sv` (`tools/die_plan/s81_svc_idx_fit.py`), renames the one bound instance
`dsdv_idx_rg3 #(` -> `dsdv_idx_rg3_fit #(` (count-checked, idempotent), adds `dsdv_idx_fit_mem.sv` and the new macro
views, and drops the original reader from the kit lists when nothing else instantiates it. svc_hi: no reader, unchanged.

| memory | old | new | why it is enough |
|---|---|---|---|
| lf x2 (`u_mem`) | 1024x256 | 256x256_m1 | `wa = lf_wn[LFW-1:0]`, `ra = lfr_a`, LFW = 8 (LFD 256) |
| h0 x4 (`u_h0`) | 1024x256 | 768x256_m2 | `lw_a` is `{2'b00,..}` / `{5'b01000,..}` / `{2'b10,..}` (< 768); `s_row`, `c_row` same forms |
| h1 x4 (`u_h1`) | 1024x256 | 256x256_m1 | written only with `lw_h1 = !sc && bt[0]`, same edge as the `{2'b00,..}` form of `lw_a`; `ra = c_row = {2'b00,..}` |
| iq | 1024x256 | 1024x35_m4 | full depth, data width IW = 35 (wd above is constant 0) |
| sq | 1024x256 | 1024x39_m4 | full depth, SW = 39 |
| mq | 1024x256 | 128x23_m1 | ring written every edge at `mw`, read at `mw - (EL+KR-1)` = `mw - 123`: the word read was written 123 < 128 edges earlier in both forms (mod 128 = mod 1024 on the low 7 bits); within 123 edges of reset both read unwritten words and `o_v1 = mq_q[MW] && warm` masks them (warm after 126 edges, reset with `mw`) |

Every precondition (the `lw_a` / `lw_h1` assignments, `s_row` / `c_row`, the mq read offset, LFW) is checked on the
source text by `s81_svc_idx_fit.py`; any other source sha is refused. Both kit source shas (dd5695c1e6c0 main,
54e3d3ebf8a9 kit-wave-14d/15) give the identical fit body (the older `16'(wc)` cast, KIT_PREFLIGHT YC1, is emitted
in main's `{12'd0, wc}` form; `wc` is `reg [3:0]`).

Area a type: 13 x 1024x256 (160.1k um2) -> 6 x 256x256_m1 + 4 x 768x256 + 1024x35 + 1024x39 + 128x23 (~67k um2).

## Gate
`run_lock.sh OUT` (heavy, via ot-run): S81-IDX3R campaign bench with every reader an `idx_lock` (kit reader drives,
fit child compared on every output every edge, macro models), reader 0 also runs the behavioural fit control m0 and
7 size mutants (h0 512, h1 128, mq 64, iq -1 bit, sq meta dropped, lf 64, h0 256). Gate: verdicts as expected, 0
mismatches on all readers, m0 = 0, every mutant detected, coverage counters non-zero, longest case >= 20k cycles.
Result: RESULT_PLACEHOLDER
