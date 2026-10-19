# smh_int8_t1 -- SAFE hard tile of the SM INT8 packet-ingress adapter (LH-SMATT/INT8, 10-19, COORD 0ki)

Top `ot_smh_int8_tile` (rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv), instantiated by `ot_hbm_accel_smh_attn #(.ENABLE_INT8(1))`
as `g_int8.g_hard.u_int8` (ENABLE_INT8 2 keeps the soft reference `ot_smh_static_int8`, benches only).
GEN2e (tools/hbm_die_v16/d4g_layers/l13_int8.py) sets ENABLE_INT8 1 on all 16 SMs of the d4g release die.

## What changed in the SM when ENABLE_INT8 = 1 (item 1 of the task)
- The INT8 logic sits ONLY in the smh_attn parent glue (`g_int8`, between the SM `packet` port and `u_front`).
  `ot_hbm_sm_attn_front_static` and every hard child keep their RTL and parameters: fc_t / fc_b are instantiated with
  `ENABLE_INT8(0)` hard-coded inside `ot_smh_static_front`; fc_xl, fc_xr/fc_xr2, xs, tct, tcl_gu, bdc, pvm are untouched.
  So NO closed child view changes; the substantial new logic (~2.65k flops + 64 converter lanes) becomes this new hard
  child, and the parent keeps a 1099-bit 2:1 merge mux (selects from this tile's kept `o_sel` copies) + the 2-flop sticky
  schedule-fault glue.
- The smh_attn parent itself has no closed view (H.STA.BLK.14 / 14.3: landed-parent form claude/hf5c-1018, region `f`
  = front); this tile goes into region `f`, between the SM packet-ingress landing and `u_fl` (front feed `s1_w`).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS. RTL registers every input (p_v[21:0] kept copies, p_tag, p_codes) and every output is a register (r_v, r_tag,
  r_data, r_sel[34:0]); flow pin_regs off with that reason (a flow pin register would add a cycle). rst_n: flow
  reset_landing 2 stages (assert + release +2 cycles: a scheduled constant; the compiler issues no INT8 line within 4
  edges of reset release).
2 Reach: PASS by placement contract. Tile 237.6 x 129.6 um; the parent must place it in region f with its N face <= 405 um
  from the SM packet landing and its S face <= 405 um from u_fl's feed (s1_w) -- the parent mux is one AO cell per bit.
3 Fanout: PASS by construction. i_v pin -> 22 kept flops; pend[g] -> 32 lane-mux bits; pend_s/p_v copies -> <= 18 o_sel
  flops; control copy -> 21; o_sel[k] serves 32 parent mux bits (35 copies); no data enables (o_data/hi_codes load every
  edge). (* keep *) on a non-parameterised module (no paramod rename); gate high_fanout checks the netlist.
4 Depth: PASS (est.): one stage = 2:1 select + 8-bit negate + priority encode + shift (~12 levels); no comb in->out.
5 Storage: PASS. 512-bit hi_codes holds one line for one edge; no runtime-indexed array, no delay line >= 3.
6 Floorplan: no macros. Pin-bound outline: 1,035 pins N (4.36/um), 1,070 pins S (4.50/um) <= 6/um, aspect 1.83, one
  full-width std-cell band. Util is far below 40 % (synthesis area in gate_result.json): WAIVER requested (pin-bound relay
  tile, like fc_xr2 / idx collar); the alternative (fold pins onto 4 faces, 129.6 sq.) would cross data paths inside.
7 Clock: single leaf root on the W face centre (register mass = N input band + S output band); pin-flop spread <= 80 ps
  TT+FF to be read from the --cts gate; io_hold_margin 0.03; no hard children.
8 Schedule: PASS. Cycle-exact with ot_smh_static_int8 (low beat +2, high beat +3: already priced by SMB-INT8 / d4g Qwen
  price, measured 3206/2161/12422/6278 vs 3418.6/2394.6/12634.6/6490.6); static, no ready/credit; overlap = parent
  sticky schedule_fault (sim $fatal). Only new constant: reset release +2 (landing).

## Benches (Verilator 5.050, fleet)
- rtl/hbm_accel/sm/static/test/run_smh_int8_tile_bench.sh: lockstep vs ot_smh_static_int8 behind the exact smh_attn merge
  mux, random legal calendar, all 256 codes, reset bursts. exact PASS checked=19985 beats=13181 lines=6596;
  mutants pend / sign / tag FAIL (witnesses results/arch/lhsmatt_int8_1019/bench/).
- Parent: tools/hbm_layer_vehicle/run_qwen_sm_mv_unit.sh (Qwen D4G8 L0 SM.MATVEC on smh_attn ENABLE_INT8 1 = this tile).
