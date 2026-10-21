# QW-S5-XHEAD 10-21: qfd_dv_s5_xhead3, structural successor of the slice2 column head leaf

Predecessor: `qfd_dv_s5_xhead` (rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv @5949f90af, instantiated as u_xh0..3 by
qfd_dv_s5b_su8p2_lp). Mapped census FAIL 75 drivers > 32 (foff rotate selects 2,177-2,585, fep 1,707, g_q 877, g_pin
759, phd 516, ...). Bounded-netlist successor xheadJ: native 32 but 771.8 ps depth (buffer trees). Neither gateable.

New master `rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv` (same ports, values unchanged): input stage P + kept per-consumer copy
bank R, retimed window pipeline (no adder after adder), W+-1 copies replaced by fb-+1 compares, first_abs by start +
per-epoch k/3k, read sequencer "now" selects registered one edge ahead (descriptor write forwarded), answer delay lines
end in per-chunk kept one-hot copies, retag before the output flops, ot_rst_relay reset (12 kept regional copies).

| evidence | result |
|---|---|
| native census (ORFS-image yosys + ot_keep_regs hook, tools/ref_tile/native_census.py) | PASS, 0 > 32, max 32 (`native/`) |
| textbook depth | 365.1 ps / 12 levels (was 481.8 old leaf, 771.8 xheadJ); in->out 0, reg->out 0, in->reg 0 |
| mapped | 12,127 flops, 6,098 um2 (old 7,916 flops / 5,744 um2) |
| lockstep bench V5.050 (`rtl/test/qwen_dv/s5/xhead3/run.sh OUT pass`) | 8/8 PASS (cid 0/5/22/63 x 2 seeds, ~149k compares each, 17 resets, ~850 ops incl. pooled/forwarded/faults) `bench/pass_runs.log` |
| mutants retag / rot / poolw / fwd | all FAIL (witness/mut_*.log) |

PRICE (static schedule): +1 edge on every a_d path (fill -> leaf write, go/ib -> corridor DX 14 -> 15, read request issue),
+1 reset release (3 edges, l_rst_n too). lq answers and fault_i -> fault keep their latency; intra-column relative
timing (FILL_LEAD 5, QD 8, TDM) unchanged; throughput unchanged. Bench: new(t+1) == old(t), lq/fault_i one edge later.

BIND: the parent instantiates `qfd_dv_s5_xhead`; switching u_xh0..3 to `qfd_dv_s5_xhead3` (identical ports) adds the +1
edge to the corridor words cw_n*/cw_s* and the x-leaf write/read buses of regions r_hc0..3 (compiler NOTICE).
Kits: physical/ref_tile/qfd_dv_s5_xhead3 (216 x 432) + qfd_dv_s5_xhead3b (259.2 x 518.4 fallback), pin-bound (5,726 pins).

Gate try 1 (b9e2576f3, ORFS synthesis): PRE_GATE_NATIVE_CENSUS_REFUSED 24 drivers (max 98): e_pool (per-row start
select pushed into 96 ANDs) and b_k / b_k3 (per-row-element integrity adders). Fix: per-4-row kept e_pool copies; the
integrity check reduced exactly to start + 4k - 1 >= 128 (k != 0) per row (max over elements, no 8-bit wrap) with kept
per-4-row 4k-1 copies. Re-benched 8/8 PASS + 4 mutants FAIL, census PASS max 32, depth 365.1 ps.
Gate try 2 (1d69a8a52): census refused e_poolc[*][2] 98 loads (dynamically indexed kept array -> memory, copies merged).
Fix: per-epoch plain vectors e_poolc0/e_poolc1. Re-benched 8/8 PASS + 4 mutants FAIL, local census PASS max 32, 365.1 ps / 11 lv.
