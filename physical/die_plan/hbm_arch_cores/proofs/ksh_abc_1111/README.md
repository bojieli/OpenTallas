# kshare splitstrap forms A/B/C proofs (HBM-CORES-B 11-11, DIE-HBM-100 approval; DO_NOT_COUNT pilot)

RTL: rtl/hbm_accel/loader/service_native/ot_hbm_svc_vm_kshare_splitstrap.sv, each form behind its own define. Recipe keys
`ot_hbm_svc_vm_kshare_splitstrap__v8e478a__abc` (SELREP+VMSTG+WCNT2+SRDL) and `..__v700685__wcnt2` (WCNT2).

- A `OT_KSH_VMSTG`: VM response stage ring -> u_fill (classes rp(slice4)->hf 3, rp->u_fill.mem 24, st->u_fill.mem 38).
  fill_* +1 hbm edge, VM tag fault term +1 hbm edge.
- B `OT_KSH_WCNT2`: WB lane count over 2 stream edges (we2->wq3 17; v700685 sm_s/we2->wq3 15). WB window +1 stream edge.
- C `OT_KSH_SRDL`: u_d skid with 16-bit slices and a late pop select (u_bin_g_kr_rdy->u_d.out_data 64). No edge change.

Proofs (results.txt):
- default netlists unchanged: yosys EQ of the core (KRL1=1) new vs selrep-branch RTL, no define and OT_KSH_SELREP.
- C: yosys EQ ot_hbm_svc_pin_skid2_srl == ot_hbm_svc_pin_skid2 (W=277). Negative OT_KSH_MUT_C fails.
- A: EQ_CYCLE_SHIFTED (gold = selrep VM branch + one register on the FIFO write/tag fault; FIFO accepting).
  Negative OT_KSH_MUT_A fails. Back-pressure: eq/tb_bpA.sv, 300k cycles, random f_r: same write sequence, no overflow.
- B: EQ_CYCLE_SHIFTED (gold = wq3/wv3 + one register). Negative OT_KSH_MUT_B fails.
- Lock-step: run_lock.sh on the quadrant system bench (tb_hbm_svc_wb_kshare_splitstrap_q, real wb_kport, 32 controllers,
  DRAM) with a shadow reference core per dut core; 4 seeds per configuration, >=120k hbm cycles each.
  A: K-port outputs cycle exact, u_fill write/hf = reference +1 hbm edge, fill words equal in order; fill_v moves +1/+2
  stream edges (2-sync CDC uncertainty unchanged: one hbm edge = 1.23 stream edges in the bench).
  B: u_wcmd write = reference +1 stream edge.  C/default: everything cycle exact.  ABC/B700: system bench PASS.
  Mutants A/B/C FAIL on every seed.
