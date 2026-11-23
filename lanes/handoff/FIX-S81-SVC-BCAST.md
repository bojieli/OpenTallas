# FIX-S81-SVC-BCAST handoff (Opus; started by FIX-LEDGER 11-23 ~02:0x PST)
Goal: ledger rc16 / row SVC-BCAST-STAGE: RTL replication of svc broadcast drivers (one copy per core row, same cycle), LEC maps dups.
Deadline: gated rows to S81-J6-ASSEMBLY-R5 by 10:30 (Wave A, f65f); hard stop 12:30. Co-owner/reviewer FABLE-UNC-S81-SVC (ad36422a39196fd09). Owner lane SVC-R9 acbf5f53765607888. FIX-LEDGER agent acd269758d3b62a53.
Lane clone: epyc10 /srv/opentallas-scratch2/claude/fix-s81-svc-bcast/repo (main 6734f6deff0 at clone). tmp: .../fix-s81-svc-bcast/tmp
Drivers (R8 hi4 place smells, epyc7 opus-fix-s81-svc-r8-north/hi4_place_only/{rest_review/gpl_render,att_review/gpl_render_r9}/smells.json):
- rest: g_u_rsv_u_src_aa4db9e7 = 2-bit sync in dsdv_svc_rs_c (src line ~140 of j7_hi4 form), q[0] fo 9736, q[1] fo 378 (sync reset w_u_rsv_u_3_Y)
- rest: src_99f4c3e7 q[16] fo 1018; driver_pp_v fo 1026; src_235caab2 fo 269
- att: u_bin_i_attn_o0_p q[805] fo 1796 (cut-bus landing bit 805); _059875_ fo 2048
- att: u_eng e_iv / e_ibank[2:0] (ot_hdc_v41x_attn_s E register) fo 32 hcores each
Status: investigating RTL.
## 03:3x status (epyc10 lane clone, uncommitted)
ROOT CAUSE rest q[0] fo 9736: yosys opt_merge merged the IDENTICAL 2-flop reset synchronisers of rs_c / sx_hrow / smq / SO target / PC (same D=1, clk, async rst) into ONE pair -> one flop resets ~10k flops over the piece. att q[805] = the slice rn crossing the hi4 cut (bit 805 of attn_o0 bundle) -> 1796 loads in att.
RTL (all opt-in -DOT_SVC_BCAST; without it byte-identical behaviour):
- dsdv_svc_rs.sv rs_c: kept (kreg) sync stage1 rs0 + 3 kept stage-2 copies rn/rn_up/rn_z (same D, same edge); u_att gets rs0.
- dsdv_svc_att.sv: rn_a / rn_e kept stage-2 copies from its rst_n (= rs0 in-slice -> same edge as rn).
- dsdv_svc_sx_hrow, ot_s81_su_smq, dsdv_sm_so_target, dsfd_svc_pc: sync as kreg (no cross-module merge).
- ot_s81_svc_attn_s (the OT_SVC_MERGE_H4 engine) TREP: per-tile kreg copies of {ld_v, iv, ld_mode, ld_w2v, ld_bank, ibank, ld_grp} (same D, 0 cycles), per-tile reset relay (+1) for transposer/tile/merge. Not band form.
Benches (ot-run epyc10, OT_LANE set): ls_srx0_hc / ls_srx0 (svc_bcast_lockstep.py, ref vs BCAST strict lockstep + mutant), rsb (rs_bench_pl 16-slice tail46/short300 + trace diff), lec (lec.py mini kits rs_t/pc/smq).
Split form: R9 overlay copies dsdv_svc_rs_c_j7_hi4 / dsdv_svc_att_j7_hi4 need the same edits (patchers in fix-s81-svc-bcast/tmp/p_sync.py, p_att.py).
FABLE-UNC staging rd_data -> 4 tr net: = existing S81-A1 SRX lever (-DOT_SVC_SRX=n, compiler PIO/KPV +n); TREP supports SRX>0.
