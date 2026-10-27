KV-RTL-MODDUP 2026-10-27 (COORD ruling 10:44: no MODDUP_ALLOW, fix the RTL).

PROBLEM. ot_qkvd_kcmd_tap had two different definitions on main 60b5ddf523:
  A rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv   (41a81a4ca 10-11 00:20): 1 register stage, c_v filters op 0/1,
    DESC -> {0, n = 1,024, ROW0 + layer}; G/ST are identity params only.
  B rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv:169 (5a884f8b0 10-11 00:11, adopted from an ended orphan session):
    2 stages on the command (v_q/d_q then c_v/c_d), per-PC n = 4*(16*(T>>9)+(m>>3)+((m&7)>G)) from params G/ST.
  Verilator keeps the first file read, yosys -overwrite the last.

INTENDED COPY = A (ot_qkvd_kcmd_tap.sv). Evidence:
  * Every PC controller instance passes ONLY .ROW0 (qkd_ctrl_strip qkd_ctrl_pc, qkd_ctrl_pc_host(_pinvalid), 
    qkd_ctrl_pc_host_static_core / qkd_ctrl_pc_sched, qkd_ctrl_pc_sched_nc, qkd_kvpc_s_sched). Under B every PC would
    compute n with G = ST = 0, i.e. the wrong sector count on 7 of 8 groups at T < 8,192. B's arithmetic cannot be what
    the controllers were built for.
  * The kit face-port transform physical/die_plan/qwen_kvsys/cores/harden/kvspc_face_ports.py (all current
    qkd_kvs_pc / qkd_kvs_pc_h_head_p kits) replaces u_tap with "exactly the old tap c_v / c_d registers: 0 cycles":
    one pin flop kq, c_v = kq_v && op in {0,1}, c_d = {0, 1024, ROW0 + layer}. That is A, bit for bit.
  * All PC benches/gates (physical/qkd_ctrl_strip/bench.sh, tools/qwen_host/*gate.sh, kv_plan_leaves_1023,
    static_kv benches, kv_ctl10, mu_qwen lists) list only ot_qkvd_kcmd_tap.sv; the static-schedule stream bench
    checks every tap's descriptor as {1,024, layer} at T = 8,192 (the price point), which is A's contract.
FIX: B deleted from ot_qkvd_kv_desc.sv (unreferenced in that file; a header note points to the one definition).
  No instance or port change; no rename needed (nothing needs per-PC n).

BENCHES (intel2 /srv/opentallas-scratch2/claude/kv-rtl-moddup-1027, Verilator 5.050):
  stream tb_hbm_stream_bw SELF=1 CONS=1 WR_EN=1 WSETP=0 (issuer -> FIFO -> 16 relays -> 32 taps -> head):
    pre-fix (lists kv_desc.sv first -> Verilator MODDUP kept B!): PASS worst 1,074,176 ps, max go-after-attn 58,368 ps
    post-fix (A):                                                  PASS worst 1,074,176 ps, max go-after-attn 57,344 ps
      (GO one hclk earlier = B's extra stage), tap_desc 1152 tap_bad 0, issuer_fault 0; all layers <= 1,165 ns step.
    mutants post-fix: DMUT=1 FAIL over_need 35; DMUT=3 FAIL tap_bad 1152. plain bench PASS sectors_bad 0.
  qkd_ctrl_strip bench (A only, unchanged input): pc PASS 3/3 straps (PC 0/13/31); mut1 FAIL 2851, mut2 FAIL 28;
    kc (+3-tap chain) PASS 12000 tap commands exact; mut1 FAIL 13847.
  kv_plan_leaves PC subset: qkd_static_kv_pc_path_fan_nc_b_head_p v0/v17 PASS, mut CAUGHT;
    qkd_kvs_pc_h_head_p mut CAUGHT but v0/v17 FAIL (pc__po mismatch from cyc 32). PRE-EXISTING and unrelated: its
    compile list holds only ot_qkvd_kcmd_tap.sv (identical input before/after this fix), and it FAILs the same on the
    tree before 4b7e0e6443 (pc_leaves_preboot_4b7e0e6443p.res) -> KV-CORES (stale _p leaf vs current kvs_pc_h).
  check_moddup.py (TOK-QK-5) on the actual B48 die-slice vl.f: pre FAIL 1 duplicate (ot_qkvd_kcmd_tap); with the
    fixed kv_desc.sv PASS 0 duplicates (343 sources).

KIT / VIEW CENSUS (netlist_census.tsv: every *synth*/1_2_yosys/1_synth_odb netlist under KV scratch dirs on
intel2/intel1/epyc2 with any tap trace; kitrtl_census.tsv: every kit RTL file defining the module):
  * Netlists with a tap: only qkd_kvs_pc and qkd_kvs_pc_h_head_p kits (path-kv pc2/pc3/pc5/pc833, codex-kv-cores-1309
    /0809, kv-cores-pv2, kv-cores-1025r r3). All carry A: transformed kits have the kq_v/kq_d pin flops and 0 v_q/d_q;
    the pre-transform r3/base kit has u_tap.{o_v,o_d[31:0],c_v,c_d[0..6,29,30]} = A's 1-stage set (c_d[29] = n bit 10
    = 1,024; B would leave n bits 19..28 and 33 v_q/d_q flops). 0 netlists contain B.
  * kv3_head_eighth_e1/e5 (the only SIGNED KV views), PV kits, sys_c, hg/hgi/hroot/io/hub: no module that instantiates
    the tap (only the PC controllers do); e1 r6 netlist 0 tap refs.
  * Kits whose kit RTL carries B as DEAD text (via a kv_desc.sv copy; no instance): kv3_astk(+_EN/_ES/_WN/_WS), qkd_ahub,
    qkd_kvs_ctl, many vehicle/src trees. Their netlists have 0 tap refs -> logic unchanged, no re-synthesis; only a
    source-hash change on the next regen.
  => NO kit or signed view needs re-synthesis for this fix. Bench evidence that ran via a list with kv_desc.sv first
     (tests/rtl/run_hbm_stream_bw.sh) ran B; it is re-proved here on A.
