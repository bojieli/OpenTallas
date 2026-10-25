S81/RTLSPLIT 2026-10-24/25 evidence (branch claude/s81-rtlsplit-1024r, base claude/s81-kits-1024r@cf3c66ab82 + leafplan r9
claude/s81-leafplan-1024r@9694c8d9f1).  Fleet runs only (ot-run; epyc1 / epyc2; Verilator 5.050; ORFS Yosys + slang).
Run dir: epyc1:/srv/opentallas-scratch2/claude/s81-rtlsplit (src/ snapshot, kits/, runs/, logs/).

RTL (COORD C3 400k-cell cap; plan spec physical/die_plan/s81/cores/leaf/split.py):
- rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv: ot_s81sl_ve_m (r/a pin flops, order check, mul4, add8 -> o; m_v / m_pre /
  m_hh / m_kk / m_dd output flops), ot_s81sl_ve_s (m_* pin flops, quad pack, chunk8 x3, trees x3 -> p),
  ot_s81sl_ve_sp = the leaf's u_ve (u_m / u_s, ot_s81sl_ve ports; fault = f_m | f_s).
- rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv: ot_s81sl_vn_a (h half 0, norm lanes 0..3, chain adders 1..3 -> c_v / c_s
  output flops, y lanes 0..3), ot_s81sl_vn_b (h half 1, lanes 4..7, c_* pin flops, chain adders 4..7, beat tree -> p,
  y lanes 4..7 + y_v / y_i), shared ot_s81sl_vn_ng4 (4 lanes of ot_hbm_norm_grp G8) + ot_s81sl_vn_rf8;
  ot_s81sl_vn_sp = the leaf's u_vn (u_a / u_b; hq_d / hq_v / fault ORed, y = {y_b, y_a}).
- ot_s81sl_leaf (ot_s81sl_slice.sv) instantiates ot_s81sl_ve_sp u_ve / ot_s81sl_vn_sp u_vn: instance paths
  u_lf.u_ve.u_m / u_s and u_lf.u_vn.u_a / u_b = core_conns.json.  The unsplit ot_s81sl_ve / ot_s81sl_vn stay in the same
  files (miter references); every existing source list picks the split modules up unchanged.
- Every partition pin registered on both sides; static schedule; reset = per-core ot_rst_relay regions (control only).

Cycle cost: +2 edges on the ve reduce stream (p_*) and on vn's p (p_v / p_d) only; ve add stream (o_*), vn y / y_v / y_i,
hq and h writes unchanged edge for edge.  Measured: ve golden reduce 129 -> 131 cyc, beat go_to_partial 115 -> 117.

Spec deltas vs the leafplan r9 tables (both applied to the plan here):
- vn c_s[31] DROPPED (OWNER DECISION 8): acc3 is a sum of 4 squares, its sign bit is constant 0 (raw yosys of the first
  vn_a: c_s[31] on TIELO -> face_guard shared FAIL).  RTL c_s[30:0]; inputs/const_pins_dropped.json gains
  ot_s81sl_vn_{a,b}{,_xm} c_s[31]; split.py now applies drop_const_pins.drop() before writing (tables / LEF stubs
  regenerated: vn_a 917 -> 916 pins, vn_b 954 -> 953; split_cores.json updated).
- vn x / w stores: an 8-word flop register file per half (ot_s81sl_vn_rf8, NV = 8 words, registered read, read-before-
  write, same latency) instead of a half-width SRAM: no 128-bit macro exists, and the group used 8 of the 128x256
  macro's 128 words.  Each half keeps its 128x256 h-store macro.  Ports unaffected.

Results:
- cells.txt: yosys cells ve_m 219,961 / ve_s 222,043 / vn_a 183,977 / vn_b 200,485 (all < 300k; cap 400k).
- face_guard/: raw yosys + synth-ODB face_guard PASS: ve_m 1260/1260, ve_s 486/486, vn_a 914/914, vn_b 951/951
  (planned bits = plan pin tables, missing 0 / extra 0).  Kits: tools/s81_slice/rtlsplit_mk_kits.py (closed ve / vn kit
  hooks, plan pins), run_kit.sh synth.
- split_ports.log: tools/s81_slice/split_port_check.py: RTL ports (names / widths / directions) == plan tables and stub
  LEF directions for all 8 views (incl. _xm).  drop_const_pins.py and split.py re-runs idempotent.
- gates/ (tools/s81_slice/rtlsplit_gate.sh):
  vemit0 PASS: tb_s81sl_ve_spmiter, split vs r5 ve, p 2 edges late, o same edge, fault bracket, golden bit exact, random
    init + 8 in-flight resets.  Mutants caught: vemit1 (MUT 1 mul4 key), vemit3 (MUT 3 ring select), vemitmv
    (OT_S81SL_SPMUT_MV: ve_s quad valid from the pin).  MUT 2 (tree pairs) is NOT detected -- pre-existing: the unsplit
    r5 ve_miter.sh MUT 2 is blind too (pre_existing_r5_mut2_blind.log).
  vnmit0 PASS: tb_s81sl_vn_spmiter, split vs unsplit vn, 40k random static-schedule cycles (824 norms, 380 p, 10,919 y,
    3,891 hq), hq / y / fault same edge, p 2 edges late, 0 mismatches.  Mutants caught: vnmitc1 (c_s pin unregistered),
    vnmithq (vn_a answers both halves).
  beat PASS (go_to_partial 117), beattree mutant caught; leaf0 PASS / leaf1 mutant caught; leafeng0 PASS / leafeng7
    mutant caught (leaf_eng_bench.sh had lost ot_s81sl_ve_fp.sv from its source list: fixed).
  plan: run_v4.sh G0 PASS 0 errors, G0C 180/180 types, 0 errors.
