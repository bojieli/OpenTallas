# S81-KV-CALENDAR handoff (Opus 5.5), 11-24 01:50 PST
Clone: epyc10 /srv/opentallas-scratch2/claude/S81-KV-CALENDAR/wt (epyc11 copy at same path is stale, unused).
DONE on main:
- 4a65e809159b t2 seam dates: kv_bank_contract.kv_timing(seam_in, seam_out, vp_sr); programme kv_seam; receipt f6e09fa91356 (v5d, seam 2+2, VLAT 5). t2 done KV 1134 GK 1029 CN 1222 IK 1062 CP 399.
- db85d2420311 port-free check (busy low at capture + done_age + 1); all old-date mutants incl. old_GK caught at VLAT 4 and 5.
- 256f1a201c75 lep_rip.py per-type RIP table + trace check (c8: lepe_mu_LP t2 3, lepe_nh_mus_LP t1 3, lepw_mu_LP t2 1, lepw_mus_LP t2 1, _C 0).
Receipts: results/token_pass/s81_kv_t2b_seam_1124, results/token_pass/s81_lep_rip_1124.
OPEN (not assigned to me): LATCHECK ri lane K + lep_ri_rip(type) on the 4 LP types (BIND-ELAB-PAR / S81-ALLFIX-INT).
No live units.

- 2026-11-24 02:0x PST LEP-RIP-LATCHECK done: main f3fa519f642e (lane_asbuilt_latency lep_ri_cycles + LEP_RIP_UNDECLARED; lep_rip --kit-config). J8 lepw_mus_LP t2 kit REFUSED. Draft c8 ri rows results/token_pass/s81_lep_rip_1124/c8_ri_lane_row_draft.json. Posted d5359b69. No live units; nothing owed.

- 2026-11-24 05:47 PST ROW-REBASED posted 5d443553. Row plan epyc11 /srv/opentallas-scratch2/claude/S81-KV-CALENDAR/row/tree/physical/die_plan/s81/j9tail_c8/p6w_riprow.json 8d573399d729 (base p6u_hops2 94eb2af6a4f5), ops row/lep_rip_row{,.replace}.ops.json, mkrow.py regenerates on any base. PRE PASS; LATCHECK 4 ku PASS on emitted RTL; scoped strict bind (unit oth-ubuntu-3884580, log row/gate/scope_bind.log, rowbind2.otrun.log) still in post-emit checks. ROS LATCHECK main ea07ea39274a posted 4bef615b (open: unit_i0[10:0]/lepk_i0[0] bypass ROS). Earlier: f3fa519f642e RIP LATCHECK, ae8b6816bc30 OT_REPO_ROOT.
