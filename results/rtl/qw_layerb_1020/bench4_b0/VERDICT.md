# TOK.QW.BENCH.4 reference rebuild verdict (QW-LAYERB 10-20): DROP -- the 10-13 reference cycles are stale

Question: do the 10-13 Qwen reference-core layer cycles (L0 6,151 / chained 5,480 / head 3,048,
results/rtl/qwen_layer_tput_1013) stand, and should the reference be rebuilt on the current GEN netlist?

B0 = the literal 10-13 recipe (10-13 source 30b6440b5, unguarded Verilator 5.050 copy, no --unroll-count), ot-epyc5
lb2qc-ref-1018, script lb2qc_ref4.sh (QW-REFB1, launched 10-18 22:59). Result (collected 10-20 22:40, files here):
- build rc=0 (893 s); NBA in-place scan: INPLACE_NBA_LOOPS=4 in the die model (t_rd_sectors / kvw_ce / st_rsp_stall /
  u_kv n; nbaguardB0.log) -> the 10-13 recipe compiles a miscompiled (guard-dirty) model.
- runL0 rc=1 (returncode 3): exact false, layer_x_mismatches 16,384 (all 4 dies), writeback not drained, timeout at
  cyc 9,001; OPTRACE stops at prog_a=20 cyc 3,094 (me_busy forever, stall_kv 713) -- byte-identical to A (10-13 src,
  5.050 + unroll 4096) and C (10-18 src), runA/runC on claude/qw-refb1-1018.
- B1 (5.032) is not buildable (unroll >3075 at me_array_w12 g_xq; with --unroll-count 8192 hier blocks reject -G).

Decision table (pending_results line 640): "hangs at op 20 -> 10-13 unreproducible: withdrawal stands".
So no configuration -- clean or guard-dirty, 10-13 or 10-18 source -- reproduces 6,151 exact; the 10-13 numbers are
WITHDRAWN for good.

Why no rebuild "on GEN2": the reference core is the old monolithic TP4 ROM die (ot_qwen_rom_rt_die_w12, single die
type, 10-13). It has no counterpart in the two-die split release (compute dv2f20g5r2b + KV die): there is no
qwen_rom_fulltoken harness for the split GEN netlists, and the release layer cycles come from per-stage benches on the
current RTL/netlist (TOKSIM-QW composer + QW-TOKSCHED ledger 23314a50c, XT1g on the g5r2b die-netlist carve). Rebuilding
an old-architecture reference would only reproduce a design that is not shipped. BENCH.4 is dropped; the 10-13
reference numbers must not be quoted anywhere.

Fleet cleanup: the reference build/src dirs on ot-epyc5 lb2qc-ref-1018 (bldA/bldB0/bldC/srcA/srcC/srcR/v5050raw, ~7 GB)
deleted after this commit (logs kept here and on claude/qw-refb1-1018).
