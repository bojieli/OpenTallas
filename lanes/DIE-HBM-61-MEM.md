# DIE-HBM-61/MEM (helper of DIE-HBM-61): RE-FORM classes (3) pin-bound and (4) macro channels
Started 2026-11-03 06:38 PST. Worktree epyc2:/home/ubuntu/scratch-root/claude/die-hbm-61-mem/repo, branch claude/die-hbm-61-mem-1103 (from origin/main a37abb76a7c).

## 2026-11-03 07:39 PST state
- Class 4 finding (d44o kit netlists, yosys mem.json): every HBM SRAM instance ties repair pins to 0; all but sfustore tie w_mask_in constant; most 64x512 use only W of 512 bits (hfd_ep 306, q3_edge/cp_rxs llr 141/138, cp_rxs 30/16); sfustore uses 128x256 as 512x32 (lane mask + read mux).
- Form: right-width r0c0 masters with ONE mask pin, pins split read-port W face / write-port E face, same 1r1w one-cycle contract (0 added cycles). Builder tools/mem_compiler/build_hbm_rightwidth_1103.py -> physical/asap7_memory_macros_v2/*_r0c0_g* (7 masters, v2 track-aligned, verified).
- RTL: leaf instantiation behind `ifdef OT_HBM_RW_MACROS (HBM RE-FORM recipe define only; all other builds unchanged): ot_hep_rx_store.sv (hfd_ep), ot_qkvd_d2d_llr.sv (q3_edge, cp_rxs; shared with qwen -> define-gated).
- Plan-time channel fit: physical/die_plan/hbm/mem_reform_1103/channel_fit.{py,json}.
- EQ: physical/die_plan/hbm/mem_reform_1103/eq/run_eq_hep.sh (lockstep r2c2 vs rw + 3 mutants).
- OWNER 07:0x via DIE-HBM-61: channels/fill/aspect advisory; KW-FIX-4 relaunched pslice_c5, sfustore_hw, cxport_ij_q, q2n2_vm, q3_edge, rootctl_am, bfqg on current kits -> my forms for those only if they fail sign-off. Priority: hfd_ep_static (5 types), host_cp_rxs, keybuf_slice, vm_wr_q_t_lanes4, q3_vm.
