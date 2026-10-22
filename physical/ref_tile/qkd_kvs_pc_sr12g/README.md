# qkd_kvs_pc_sr12g (SQ-PCH2 MAIN, 2026-10-21) -- KV PC tile (TOP qkd_kvs_pc) = sr12e + native-census fix

Why: sr12e gate (3067ffbe0, ot-agidock128 qkd_kvs_pc_sr12e-20261021-183130) REFUSED at native census: one driver over 32 --
OR2 _114862_ = !(row_fire && c_op == ACT && c_s), the so_* load enable in u_pc.u_pce.u_path.u_ctrl.u_sched.u_ctl.core.on, 41 pins
(so_row[18:0] / so_b / so_v operand muxes). Synthesis perturbation of the shared enable (PC_H sr10e census max 32 on the same file).

Fix (rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_clones_1019.sv): three kept leaf copies so_ld_c[2:0] (ot_kvpc5_and2,
keep_hierarchy), one per load group: [0] so_v + so_b, [1] so_row[9:0], [2] so_row[18:10]. Identical logic, 0 cycles.
Benches V5.050 (same harness as sr12e): kvpc_tile_pc m0 PASS (20000 edges, 528046 checks, 0 err), m4 FAIL 2986, m5 FAIL 8213,
m7 FAIL 7476 (20k), m8 FAIL 621; DNR tile m0 PASS -- identical counts to sr12e.

Everything else = sr12e (see ../qkd_kvs_pc_sr12e/README.md).

## SAFE 8-point review
1 Pins FIXED: i_grp / i_grp_h kept face registers (all other ports keep the sr10b pin stages; 2 RESETN loads per landed port).
  Faces as sr10b (S face i_prev 2.5-72.4 / o_prev 73.4-257.3 / ko 258.5-265.3; <= ~4 pins/um).
2 Reach PASS: same 23-bank frame, every registered hop < 405 um (sr9/sr10 placed reach; gate rechecks).
3 Fanout FIXED (so_ld_c kept copies, census 41 -> <=32); face register -> existing AND3 lookahead copies (<= 32); kept clone copies; native census max 32 is the gate receipt.
4 Depth FIXED: the IO-budget input -> lookahead decode cones start at a local flop (was -35.6 .. -163.7 ps TT on PC_H).
5 Storage PASS: 23 native dual-clock 32x64 SRAM banks on the lattice, std-cell channels >= 21 um.
6 Floorplan: sr10b geometry (util ~33-36 %, pin-bound frame), 5.4 um halo, 2.4 / 1.2 um macro-edge guard.
7 Clock FIXED: sink CTS 8 / 20 um instead of sr10b default CTS (spread 116 / 105) and sr11b spines (hold non-converging);
  ck / hck local trees, spread <= 80 TT+FF measured by the gate.
8 Reset: unchanged landed 2-stage rst_n / hrst_n; face registers carry no reset (pure pin copies).

Benches (existing, Verilator 5.050): see lanes/SQ-PCH-P.md (kvpc_tile_pc m0 PASS with REF i_grp / i_grp_h delayed one edge;
mutants m4 / m5 / m7 / m8 FAIL as required).  Unit benches unchanged (face registers are in the tile top only).
Schedule cost: +1 edge on i_grp (ck) and i_grp_h (hck) at the PC face (die schedule must add it, as PC_H sr10e).
