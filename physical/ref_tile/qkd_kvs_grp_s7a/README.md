# qkd_kvs_grp_s7a (KV-GRP7 10-20, K.STA.GRP) -- s7 branch slices, 388.8 x 388.8

Top qkd_kvs_grp_s6c: the SAME bounded-driver netlist as the s6 kits (rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s6c.sv), +0 cycles; floorplan + pin plan only.
Why: all four s6 gates FAILED trial GRT (323/280/128/111): the NE ring stack sat 31 um from the 99%-pinned E face and the W
rings' 256-b read words had to cross that ring column to reach their E pins (overflow = cap-0 M4 gcells at the stack's E edge).
s7 = four W->E slices, one per PC branch b (netlist-traced map: results/rtl/qwen_kv_die/kvs_grp_s7_1020/branch_map.json):
W pins i_pc<b> -> row macro b (x 43.2, MY: rd_out + 137 wd_in on its E face) -> out_data flops -> ring b as two staggered 4-macro
stacks A (k0..3, x 168.048, low) / B (k4..7, x 217.728, high), MY -> exit flops at the E pins (io_flop_at_pins) -> E pins of branch b.
rows abut N-S in pairs (b0+b1, b2+b3; no N/S row pins), one 22.5 um middle corridor, 20 um to N/S faces. E pins regrouped per branch by exact io_tcl (physical/qkd_kvs_kits/qkd_kvs_grp_s7a_io.tcl; krsp/rsp copies of macro k
bit-interleaved; b0,b1 | meta+kreq+vreq | b2,b3, bottom->top); W/N/S pins = the s6a gate's legal placement (scaled for 432).
No ring column in front of the E face (macro-free E strip x 237..389); ring A's word passes column B in B's low corridor, ring B's
write word passes column A in A's high corridor; no ring word crosses another branch.

SAFE checklist (pre-gate):
1 Pins: face registers as s6 (two kept exit copies, exit flops at pins); 2-stage reset landing in source. PASS (unchanged RTL)
2 Reach: planned i_pc -> row E-face wd_in <= ~210 um, row -> ring <= ~110, ring read -> E exit <= ~250 um (was ~381). PASS (plan; gate GRT/cones check)
3 Fanout: native census of the mapped netlist = s6 census (identical qkd_kvs_grp_s6c.sv): max 32 loads, 0 violations (s6 gates' native_census +
  Codex 429fbd7c7 four mapped censuses PASS max32/0 viol); the gate re-runs native_census. PASS
4 Depth: unchanged s6 logic. PASS
5 Storage: payload delay in 32 SRAM macros, rows 4 x 32 kb SRAM, no flop array > 2 kb. PASS
6 Floorplan: macros >= 20 um from N/S pin faces, >= 20 um channels (ref_tile gen: no FAIL); E/W pin density 5.65/um (388.8) or
  5.08/um (432) on M4, <= 6/um; aspect 1.0 / 1.11; ring origins on the 0.048 track grid (not 43.2: Codex 429fbd7c7 showed the
  43.2-lattice ring model infeasible for reach). PASS (lattice waived with reason)
7 Clock: spine ck+hck, pad 0 (s6 variant a); pin-flop spread <= 80 TT+FF checked at the gate. PENDING gate
8 Schedule: static, +0 cycles. PASS
Benches: unchanged s6 (kvs_grp_safe6c_bench.py m0 PASS / m1 m2 FAIL witnesses results/rtl/qwen_kv_die/kvs_grp_s6_1020/b2).
