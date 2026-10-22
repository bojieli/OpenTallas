# hbm_hc_tail_child_k4b -- HC Sinkhorn tail child FALLBACK (HBM-ELEM13/HC-TAIL 10-21)

Successor of k3 (gate agidock128 ref_gate/hbm_hc_tail_child_k3-20261021-045705: TT placement -300 ps, CTS SS -363 ps at the
Sinkhorn sticky fault flop; FF hold stall -39.7 ps / 5 R2R after 24.6k hold buffers). Classification: steady quotient Q3
segment (27-b equality z1/z2, carry select, mf mux, exponent range compare) -> range -> 16-way s_bad OR -> flt/fault, 1,938
cut flops tile-wide, 22 levels + 9 placement buffers.  Fix: ot_hdc_sinkhorn_cp SQO 1 (tail SKP 2) registers the steady
quotient y/range (QO, as step-0 B already does); D 16 -> SDIV 17; CAP 699, L 989 (+493 over L 496; root TE 2 -> 495).
FALLBACK difference: equal-delay symmetric clock spine (clock_spine.tcl OT_SPINE_SYM 1, LEAF_N 16) from a clk pin at the S-face centre (193 um), against the k3 hold stall (outlier long-wire leaf +74 ps, all-flop spread 89.5 TT).

Source: rtl/hbm_accel/generic/peers/static_hc/native/ot_hbm_hc_tail_child_static_k4.v (sha256 fd280897...e68d), RTL 95d9345b5,
recipe results/rtl/hbm_hc_root_safe_1020/tail_child_hc10/nl.sh (MAPPED=k4 ... k4f 17 1 2 495 1040: per-module ABC map, constant-identity
fold tools/hbm_hc/const_identity_fold.py, bound_fanout_clone --limit 24 tag g_skcp, retained re-synth, compact): 46,835 flops,
6,906 clones, 532k cells (k3 717k), max loads 24; native census with main's constant-identity rule (45386657d) PASS max 24.
First k4/k4b gates (17:37) FAILED pre-floorplan native census on the unfolded netlist: 290 drivers > 32 (max 181) through
constant-input identity cells (rule landed on main 16:23; k3 would fail it too) -> fold added, regated.
Benches (Verilator 5.050, ot-epyc5): RTL lockstep PASS 48 (child = unit + 495); MUT1 row-max FAIL 44/48; SKP 2 at SDIV 16
FAIL 48/48 (proves the added cut).  Native lockstep of the netlist + native32 census: hc10 (pending at commit).

SAFE 8-point: see spec.json job.purpose (pins PASS, reach 388.8 < 405, fanout clone 24, depth fixed no MCP, storage no
array > 2 kb, floorplan util ~0.48 no macros, clock one root, reset control-only regional relay; schedule +493 edges).
