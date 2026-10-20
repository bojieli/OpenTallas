# REFILL-1725/QWLAYER: Qwen MU control-plane regression on today's changed sources (Verilator 5.050)

Cohorts (staged ot-epyc6 /srv/opentallas-scratch/claude/refill-1725/QWLAYER/<cohort>/{src,out}; one per head because
GEN3c 864d10c8e and SYSFACE3 83fc1f355 conflict in qfd_sys_face.sv, qfd_sys_face_record_port.sv, d2d_cal_image_mu.svh, qwen_rom_fulldie_b3r2.py):
ctlm4 = claude/qw-ctlm4-1019 d60ab0461 (CTLM safe4, includes SRAM3 p192 lineage), sysface3 = 83fc1f355, gen3c = 864d10c8e (QW-GEN2 6bca9694c + GEN3),
ctlm3 = 7e683685c (bisect only). Legs: launch.sh. Datapath legs (amix/slice/coll, layer vector cuts) not rerun: the 24 tb_qfd_dv2
sources are byte-identical 0d4c9808f..864d10c8e, so the 28ebdeac7 layer-stage replay (33,798 ISA words PASS) already covers the current GEN.

Snapshot 18:11 (snapshot_1811.txt; witnesses witness_1811.tgz):
- PASS all cohorts: host, hroot, kv, sl_DHUSER, sysface MU0 (+MU1 on sysface3/gen3c), tok (sysface3), ctlm_rest on gen3c (LANDED_LOCKSTEP 0 mismatches).
- REGRESSION ctlm3/ctlm4: ctlm_rest prog_m0_landed LANDED_LOCKSTEP FAIL compared=18068 mismatches=1254 (NU4 landed cluster vs NU1 flat);
  already on 7e683685c (CTLM3 reset-release lineage); gen3c PASS 18071/0.
- REGRESSION ctlm4: opseg_pass MUT0 FAIL d2d_ctx C1 mu faulted (opf (80546,'0000',0)); ctlm3 bisect leg pending.
- BENCH ctlm4: kvctx does not build (tb_mu_kvctx.f lacks rtl/qwen_dv/qfd_mu_context_guard.sv now used by qfd_tt_ctlm_dv).
- STALE sysface3/gen3c: committed d2d_cal_image_mu.svh != compiler (D2D_MU=1); kvctx positive FAIL C8 (sysface3) / C10+C8 (gen3c).
  QW-TOK3 fixes (975074bdd image, dedf4c794 C8 probe) live only on claude/qw-tok3-calmu-1019, not on these heads.
- INVALID ctlm4 sysface_mu1: its bench predates D2D_MU (ran MU0; mutants 6/7 undefined). Not a verdict.
- Pending at snapshot: ctlm_nsl12 x3, opseg_mut (ctlm4), ctlm3 opseg_pass. Rerun collect.sh for terminal values.
