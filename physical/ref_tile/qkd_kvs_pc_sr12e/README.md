# qkd_kvs_pc_sr12e (SQ-PCH-P MAIN, 2026-10-21) -- KV PC tile (TOP qkd_kvs_pc), structural successor of PC sr10b / sr11a / sr11b

Why: PC sr10b terminal (GRT overflow 0, but ck pin-flop spread TT 116.2 / FF 105.0 ps > 80); PC sr11a terminal GRT-0183;
PC sr11b (recursive geometric independent spines for ck / hck instead of sink CTS) GRT hold NON-CONVERGING:
-17.495 ps at u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.down.g_sram.u_mem.g_b[3].u_m/wd_in[12], TNS flat -193.6, 10.3k hold
buffers (spine makes the SRAM write clock early vs. launch).  The PC_H sibling with the same RTL decode closed CTS with the
sr10e recipe (3f1cbf3f7: CTS hold +0.06 / setup -5.04 from -163.7, ck boundary spread TT 71 / FF 65, hck 55; GRT setup
+87.4, hold guard converging).  qkd_kvs_pc carries the identical i_grp / i_grp_h decode (only i_prev / o_prev chain ports
and the u_embr return hop differ), so the same class applies.

Fix (ported from PC_H sr10e):
- RTL: qkd_kvs_pc lands i_grp (33 b, ck) and i_grp_h (95 b, hck) in kept face registers i_grp_q / i_grp_h_q before the
  expected_put / cal_go lookahead decode (+1 edge each, priced, handed to the die schedule like fi_q / ki_q / ebr_q).  The
  kept wq_rp one-hot / es_v_qb clone copies (native census max 32) are in the shared clone file and apply as-is.
- Clock: standard sink CTS, 8 sinks / 20 um clusters, 2 levels, 20 um buffer spacing (no spines).
- SRAM-edge guard OT_MEG_DEPTH_UM 2.4 / OT_MEG_OUT_UM 1.2; hold / IO hold margin 50 ps; OT_HOLD_STOP cleared.
- Geometry and pins = PC sr10b (267.84 x 300.24 um, 23 banks, column B 4/4/3 with 21.4 um channels, tq stack x 108.0,
  i_prev / o_prev on the S face).

## SAFE 8-point review
1 Pins FIXED: i_grp / i_grp_h kept face registers (all other ports keep the sr10b pin stages; 2 RESETN loads per landed port).
  Faces as sr10b (S face i_prev 2.5-72.4 / o_prev 73.4-257.3 / ko 258.5-265.3; <= ~4 pins/um).
2 Reach PASS: same 23-bank frame, every registered hop < 405 um (sr9/sr10 placed reach; gate rechecks).
3 Fanout PASS: face register -> existing AND3 lookahead copies (<= 32); kept clone copies; native census max 32 is the gate receipt.
4 Depth FIXED: the IO-budget input -> lookahead decode cones start at a local flop (was -35.6 .. -163.7 ps TT on PC_H).
5 Storage PASS: 23 native dual-clock 32x64 SRAM banks on the lattice, std-cell channels >= 21 um.
6 Floorplan: sr10b geometry (util ~33-36 %, pin-bound frame), 5.4 um halo, 2.4 / 1.2 um macro-edge guard.
7 Clock FIXED: sink CTS 8 / 20 um instead of sr10b default CTS (spread 116 / 105) and sr11b spines (hold non-converging);
  ck / hck local trees, spread <= 80 TT+FF measured by the gate.
8 Reset: unchanged landed 2-stage rst_n / hrst_n; face registers carry no reset (pure pin copies).

Benches (existing, Verilator 5.050): see lanes/SQ-PCH-P.md (kvpc_tile_pc m0 PASS with REF i_grp / i_grp_h delayed one edge;
mutants m4 / m5 / m7 / m8 FAIL as required).  Unit benches unchanged (face registers are in the tile top only).
Schedule cost: +1 edge on i_grp (ck) and i_grp_h (hck) at the PC face (die schedule must add it, as PC_H sr10e).
