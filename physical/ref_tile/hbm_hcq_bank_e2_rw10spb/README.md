# hbm_hcq_bank_e2_rw10spb -- HC ring bank E2, all-root symmetric clock distribution (HBM-OWN/HC 10-21)

Base kit hbm_hcq_bank_e2_rw9sp (same RTL, ports, outline, children, pins, bands, ring source WR3 + witness results/rtl/hbm_hc_ring_1021_rw8/ring_rw8_m0.log).
Failure being fixed: E2 rw9sp/spb (8eafe4ec3): single-root clk spine repaired clk to TT31.0/38.9, next generic root clk_w0 TT84.5 ps over all 1035 sinks strict-80 FAIL (evidence 223093a43). Original rw8/rw8b glue clk 110.7/92.9.
Fix = the CB rw9sp method (00bd33bb0, results/arch/hbm_hc_cb_clock_1021): every one of the 23 declared glue roots (OT_SPINE_PORTS, OT_SPINE_CTS_REST 0)
gets local centre-bbox symmetric bisection beyond a repeated common trunk (150 um segments), leaves 40 um / max 4 sinks (FALLBACK); independent hard entries keep their
exact original delivery and Liberty clock refs; the unchanged hybrid wrapper still checks every root under strict 80 ps TT/FF. Clock-only change.

## SAFE 8-point review (owner 10-19 / 10-21)
1 Pins/reset: unchanged registered faces, two-stage control reset landing, per-consumer kept copies (base kit). PASS.
2 Reach: unchanged landed row/data hops; clock trunks segmented at 150 um (< 405). PASS.
3 Fanout: base mapped netlist native32 PASS (max 32); clock-buffer topology only, no functional change. PASS (gate native census re-runs before layout).
4 Depth: functional logic unchanged; base data STA not the failure class. PASS.
5 Storage: SRAM macros / lane hard views unchanged, on lattice, std-cell bands unchanged. PASS.
6 Floorplan: same outline/children/channels as base (gate fill ~48 %, square-ish); MACRO_ROWS_HALO 5.4 from current gen. PASS.
7 Clock: FIXED -- the failing class (asymmetric generic distribution across 100s of um on several roots) replaced on ALL roots, not just the first failing one; strict 80 ps within each root TT+FF retained; io_hold_margin 0.03.
8 Schedule: static, 0 new cycles/edges, same ports. PASS.
Parallel pair: e2_rw9sp family MAIN (60/8) + FALLBACK (40/4) gated together; bind first CLOSED.
