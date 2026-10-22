# KV MU merge regression on claude/kv-gen8-1019 @06a659135 (KV-TOK 2026-10-19)

Source = git archive 06a6591351fb (rtl, physical/asap7_memory_macros{,_v2}, tools, results subsets) + bench-only overlay from 97cd2e0dd
(tb_mu_kv_boot.sv SystemVerilog string filename; lint_mu_kv_tiles.f +3 MU boot modules). Production RTL = 06a659135 unchanged.
Same six legs and cases as MUKVREG2 @219049242 (launch.sh); head = the same pre-MU tree (MU0 identity). Fleet ot-epyc8, Verilator 5.050, unpinned ot-run.
Excludes the attention vehicles (KV-TOK g7/g8 vehicles).

**Result: 102 checked cases, 102 as expected after harness repair, 0 unexpected.**

| group | leg | expect | got | evidence |
|---|---|---|---|---|
| host | tb_qkd_host_ctl_mu | PASS | PASS | PASS qkd_host_ctl MU users4 steps400 in-order one-edge retire after all 8 dies, hc user=pos[17:16], max outsta |
| host | tb_qkd_host_mu_out | PASS | PASS | PASS host MU_OUT users4 steps18 CQ entries12 per-user in order (slot/tag/pos/token/ngen/kind), hc user=pos[17: |
| host | tb_qkd_kv_mu_rowoff | PASS | PASS | PASS users4 x stages36 x positions8192 identities1179648 sectors9437184 unique-addresses9437184 alias0 inverse |
| kv | tb_mu_kv_writer_rows | PASS | PASS | PASS MU_KV_WRITE_ROWS users4 x layers36 x positions8192 (stage-interleaved) words4718592 sectors9437184 unique |
| kv | tb_mu_kv_pc_path_rows | PASS | PASS | PASS MU_KV_READ_ROWS users4 layers3 pc13 acts 48/48/48/48 row=64+l+256u exact, users disjoint, all other outpu |
| kv | lint_mu_kv_tiles (list incl. 3 MU boot modules, 97cd2e0dd) | PASS | PASS | run in leg kvboot |
| kv | ex tb_qkd_kv_mu_rowoff (MU0) | PASS | PASS | PASS users4 x stages36 x positions8192 identities1179648 sectors9437184 unique-addresses9437184 alias0 inverse |
| kv | ex kvplan_ci_nc_gate (MU0) | PASS | PASS | PASS KVPLAN_CI_NC_LOCKSTEP_EXACT_OBSERVED_MUTANTS_PARENT_ELABORATES |
| hroot | tb_mu_hroot_e2e | PASS | PASS | PASS MU_HROOT_E2E rounds=3 steps=12 writer_stages=432 rows=64+l+256u epochs={seq14,user2} retire=acceptance or |
| hroot | tb_mu_hroot_collide | PASS | PASS | PASS MU_HROOT_COLLIDE: user 1 on user 0's frame slot -> KV programme collision fault code 10 |
| hroot | tb_mu_lprg_lockstep | PASS | PASS | PASS MU_LPRG_LOCKSTEP seed=7 mu0_cmp=5597 mu1_cmp=5593 events=804 (MU0 == original; MU1 user 0 gap 0 == origin |
| hroot | tb_mu_lprg_lockstep_s2 | PASS | PASS | PASS MU_LPRG_LOCKSTEP seed=1234 mu0_cmp=5102 mu1_cmp=5098 events=807 (MU0 == original; MU1 user 0 gap 0 == ori |
| hroot | ex_endpoint | PASS | PASS | PASS HOST_NATIVE_CANCEL checks=146 requests=27 credits=18 |
| hroot | ex_endpoint_mu0 | PASS | PASS | PASS HOST_NATIVE_CANCEL checks=146 requests=27 credits=18 |
| hroot | ex_lifecycle | PASS | PASS | PASS collected lifecycle identity/drains/POST/latecancel/participant/wrap/recovery |
| hroot | ex_lifecycle_mu0 | PASS | PASS | PASS collected lifecycle identity/drains/POST/latecancel/participant/wrap/recovery |
| hroot | lint_guard_mu | PASS | PASS | PASS LINT_GUARD_MU qkd_hr_core_guard (u_rank__u_native = qkd_host_native_token_endpoint_cancel_mu, MU 1) |
| host | MU0 identity tb_qkd_host_ctl (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_ctrl8_composed (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_control_capture (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_control_composed (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_control_prompt (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_control_role (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_control_service (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_control_token_service (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_fullcontrol_packet (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_fullcontrol (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_program_loader (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_prompt_packet (MU tree vs pre-MU tree) | identical | identical |  |
| host | MU0 identity tb_qkd_host_prompt_ue (MU tree vs pre-MU tree) | identical | identical |  |
| host | mutant cm1  /ERR retire 0 at/ | FAIL | FAIL (regex hit) | ERR retire 0 at |
| host | mutant cm2  /ERR fault mode 1 bit 87 first 0001/ | FAIL | FAIL (regex hit) | ERR fault mode 1 bit 87 first 0001 |
| host | mutant cm3  /ERR start 1 gen .* user 0/1/ | FAIL | FAIL (regex hit) | ERR start 1 gen 2/2 user 0/1 |
| host | mutant cm4  /ERR retire 1 at/ | FAIL | FAIL (regex hit) | ERR retire 1 at |
| host | mutant cm5  /ERR fault mode 2 bit 84 first 0000/ | FAIL | FAIL (regex hit) | ERR fault mode 2 bit 84 first 0000 |
| host | mutant hm1  /ERR retire slot/ | FAIL | FAIL (regex hit) | ERR retire slot |
| host | mutant hm2  /ERR start user 0 pos 0/0 busy 1/ | FAIL | FAIL (regex hit) | ERR start user 0 pos 0/0 busy 1 |
| host | mutant hm3  /ERR start user 0 .* busy 1/ | FAIL | FAIL (regex hit) | ERR start user 0 pos 0/0 busy 1 |
| host | mutant hm4  /ERR retire slot 2/ | FAIL | FAIL (regex hit) | ERR retire slot 2 |
| host | mutant rm1  /FAIL user0 layer0 pos0 .* nalias8/ | FAIL | FAIL (regex hit) | FAIL user0 layer0 pos0 errors272 nalias8 |
| host | mutant rm2  /FAIL non-KV command changed/ | FAIL | FAIL (regex hit) | FAIL non-KV command changed |
| kv | mutant mw1  /FAIL user. layer0 pos0 errors272 nalias8/ | FAIL | FAIL (regex hit) | FAIL user1 layer0 pos0 errors272 nalias8 |
| kv | mutant mw2  /FAIL user1 layer0 pos0 errors8/ | FAIL | FAIL (regex hit) | FAIL user1 layer0 pos0 errors8 |
| kv | mutant mw3  /FAIL user. layer0 pos0 errors272/ | FAIL | FAIL (regex hit) | FAIL user0 layer0 pos0 errors272 |
| kv | mutant mk1  /FAIL MU_KV_READ_ROWS act_bad=144 disjoint_bad=288/ | FAIL | FAIL (regex hit) | FAIL MU_KV_READ_ROWS act_bad=144 disjoint_bad=288 |
| kv | mutant mk2  /FAIL MU_KV_READ_ROWS act_bad=96/ | FAIL | FAIL (regex hit) | FAIL MU_KV_READ_ROWS act_bad=96 |
| kv | mutant mk3  /FAIL MU_KV_READ_ROWS act_bad=96 disjoint_bad=64/ | FAIL | FAIL (regex hit) | FAIL MU_KV_READ_ROWS act_bad=96 disjoint_bad=64 |
| hroot | mutant ep1  /ERR cyc \d+ endpoint protocol_fault/ | FAIL | FAIL (regex hit) | ERR cyc 491 endpoint protocol_fault |
| hroot | mutant ep2  /retire late \(waited for global drains/ | FAIL | FAIL (regex hit) | retire late (waited for global drains |
| hroot | mutant al1  /allocator epoch != \{seq14\[user\], user\}/ | FAIL | FAIL (regex hit) | allocator epoch != {seq14[user], user} |
| hroot | mutant al2  /allocator never ready for this user/ | FAIL | FAIL (regex hit) | allocator never ready for this user |
| hroot | mutant kp1  /ERR cyc \d+ KV programme fault/ | FAIL | FAIL (regex hit) | ERR cyc 531 KV programme fault |
| hroot | mutant kp2  /user token without 36 writer stages/ | FAIL | FAIL (regex hit) | user token without 36 writer stages |
| hroot | mutant kp3  /FAIL MU_HROOT_COLLIDE: no collision fault/ | FAIL | FAIL (regex hit) | FAIL MU_HROOT_COLLIDE: no collision fault |
| bootage | attn mut=0 PL=37 FD=49 FMUT=6  /^KVBA_ATTN FAIL / | FAIL | FAIL (regex hit) | KVBA_ATTN FAIL PL=37 FD=49 mut=0 fmut=6 checks=6651 errors=4979 cmds=24 clean_ok=18/18 start_pv=24 invalid_cau |
| bootage | attn mut=0 PL=37 FD=49 FMUT=7  /^KVBA_ATTN FAIL / | FAIL | FAIL (regex hit) | KVBA_ATTN FAIL PL=37 FD=49 mut=0 fmut=7 checks=6651 errors=0 cmds=24 clean_ok=18/18 start_pv=24 invalid_caught |
| bootage | attn mut=4 PL=37 FD=49 FMUT=0  /^KVBA_ATTN FAIL / | FAIL | FAIL (regex hit) | KVBA_ATTN FAIL PL=37 FD=49 mut=4 fmut=0 checks=6651 errors=48 cmds=24 clean_ok=18/18 start_pv=24 invalid_caugh |
| bootage | attn mut=5 PL=37 FD=49 FMUT=0  /^KVBA_ATTN FAIL / | FAIL | FAIL (regex hit) | KVBA_ATTN FAIL PL=37 FD=49 mut=5 fmut=0 checks=6651 errors=0 cmds=24 clean_ok=18/18 start_pv=24 invalid_caught |
| bootage | calgen mut=6 Q=57 R=87 F=49  /^KVBA_CALGEN FAIL / | FAIL | FAIL (regex hit) | KVBA_CALGEN FAIL Q=57 R=87 F=49 mut=6 checks=8204 errors=8192 fault_errors=0 dones=8192 phase_c=3/3 |
| bootage | calgen mut=7 Q=57 R=87 F=49  /^KVBA_CALGEN FAIL / | FAIL | FAIL (regex hit) | KVBA_CALGEN FAIL Q=57 R=87 F=49 mut=7 checks=8204 errors=8195 fault_errors=0 dones=8192 phase_c=3/3 |
| bootage | dcfg mut=6  /^KVBA_DCFG FAIL / | FAIL | FAIL (regex hit) | KVBA_DCFG FAIL mut=6 checks=20 errors=3 negatives=3/3 |
| bootage | dcfg mut=7  /^KVBA_DCFG FAIL / | FAIL | FAIL (regex hit) | KVBA_DCFG FAIL mut=7 checks=20 errors=16 negatives=3/3 |
| bootage | pvctl mut=1 A=108  /^KVBA_PVCTL FAIL / | FAIL | FAIL (regex hit) | KVBA_PVCTL FAIL A=108 mut=1 L=107 checks=6266 errors=5035 ref_faults=0 cmds=12 invalid_caught=2/2 |
| bootage | pvctl mut=2 A=108  /^KVBA_PVCTL FAIL / | FAIL | FAIL (regex hit) | KVBA_PVCTL FAIL A=108 mut=2 L=107 checks=6266 errors=0 ref_faults=0 cmds=12 invalid_caught=1/2 |
| bootage | vport mut=6 D=0 R=16  /^KVBA_VPORT FAIL / | FAIL | FAIL (regex hit) | KVBA_VPORT FAIL D=0 R=16 mut=6 checks=8000 errors=6961 ref_fault_cycles=0 words=1952 invalid_caught=3/3 |
| bootage | vport mut=7 D=3 R=17  /^KVBA_VPORT FAIL / | FAIL | FAIL (regex hit) | KVBA_VPORT FAIL D=3 R=17 mut=7 checks=8000 errors=7997 ref_fault_cycles=0 words=1944 invalid_caught=3/3 |
| bootage | vport mut=8 D=0 R=16  /^KVBA_VPORT FAIL / | FAIL | FAIL (regex hit) | KVBA_VPORT FAIL D=0 R=16 mut=8 checks=8000 errors=0 ref_fault_cycles=0 words=1952 invalid_caught=1/3 |
| bootage | attn mut=0 PL=0 FD=1 FMUT=0 | PASS | PASS | KVBA_ATTN PASS PL=0 FD=1 mut=0 fmut=0 checks=4777 cmds=24 clean=18 |
| bootage | attn mut=0 PL=37 FD=49 FMUT=0 | PASS | PASS | KVBA_ATTN PASS PL=37 FD=49 mut=0 fmut=0 checks=6651 cmds=24 clean=18 |
| bootage | calgen mut=0 Q=28 R=76 F=1 | PASS | PASS | KVBA_CALGEN PASS Q=28 R=76 F=1 mut=0 checks=8204 dones=8192 fault_from_T=0 |
| bootage | calgen mut=0 Q=57 R=87 F=49 | PASS | PASS | KVBA_CALGEN PASS Q=57 R=87 F=49 mut=0 checks=8204 dones=8192 fault_from_T=0 |
| bootage | dcfg mut=0 | PASS | PASS | KVBA_DCFG PASS mut=0 checks=20 |
| bootage | pvctl mut=0 A=108 | PASS | PASS | KVBA_PVCTL PASS A=108 mut=0 L=107 checks=6266 cmds=12 |
| bootage | pvctl mut=0 A=95 | PASS | PASS | KVBA_PVCTL PASS A=95 mut=0 L=94 checks=6347 cmds=12 |
| bootage | vport mut=0 D=0 R=16 | PASS | PASS | KVBA_VPORT PASS D=0 R=16 mut=0 checks=8000 words=1952 |
| bootage | vport mut=0 D=0 R=8 | PASS | PASS | KVBA_VPORT PASS D=0 R=8 mut=0 checks=8000 words=1968 |
| bootage | vport mut=0 D=15 R=31 | PASS | PASS | KVBA_VPORT PASS D=15 R=31 mut=0 checks=8000 words=1892 |
| bootage | vport mut=0 D=3 R=17 | PASS | PASS | KVBA_VPORT PASS D=3 R=17 mut=0 checks=8000 words=1944 |
| boot | tb_mu_kv_boot /^PASS MU_KV_BOOT/ | PASS | PASS | PASS MU_KV_BOOT |
| boot | kb_sealwrong /layer programme not configured .*lprg fault 04/ | FAIL | FAIL (regex hit) | layer programme not configured by the boot path (configured 0, lprg fault 04 |
| boot | kb_gapnot /layer programme not configured .*lprg fault 01/ | FAIL | FAIL (regex hit) | layer programme not configured by the boot path (configured 0, lprg fault 01 |
| boot | kb_u0gap /user 0 differs from MU 0/ | FAIL | FAIL (regex hit) | user 0 differs from MU 0 |
| boot | kb_collide /layer programme / dispatcher fault .*lprg fault 10/ | FAIL | FAIL (regex hit) | layer programme / dispatcher fault cyc 8087 (rel 7071) mu mask 201 ref mask 201 epoch 0000 lprg fault 10 |
| peer | tb_mu_peer_e2e | PASS | PASS | MU_PEER tb_mu_peer_e2e rc=0: PASS MU_PEER_E2E users=4 rounds=3 steps=12 posts=12 rank_requests=96 peer_starts= |
| peer | tb_mu_peer_abort | PASS | PASS | MU_PEER tb_mu_peer_abort rc=0: PASS MU_PEER_ABORT cancels=3 (u0 terminated identity, u1+u2 live) posts=15 afte |
| peer | lint_peer_mu | PASS | PASS | MU_PEER lint_peer_mu: PASS LINT_PEER_MU qkd_hr_core_peer (root__u_coordinator = qkd_host_tp8_coordinator_mu, u |
| peer | ex_peer_lifecycle | PASS | PASS | MU_PEER ex_peer_lifecycle rc=0: PASS HOST_PEER_LIFECYCLE protocol_boundary=1 real_cohort=8 real_result_returns |
| peer | ex_peer_lifecycle_mu0 | PASS | PASS | MU_PEER ex_peer_lifecycle_mu0 rc=0: PASS HOST_PEER_LIFECYCLE protocol_boundary=1 real_cohort=8 real_result_ret |
| peer | ex_lifecycle | PASS | PASS | MU_PEER ex_lifecycle rc=0: PASS collected lifecycle identity/drains/POST/latecancel/participant/wrap/recovery |
| peer | ex_lifecycle_mu0 | PASS | PASS | MU_PEER ex_lifecycle_mu0 rc=0: PASS collected lifecycle identity/drains/POST/latecancel/participant/wrap/recov |
| peer | ex_tsvc | PASS | PASS | MU_PEER ex_tsvc rc=0: PASS token service epoch all8 pendingACK/actualBAR/barriers UNQUALIFIED capture256 q4/fa |
| peer | ex_tsvc_mu0 | PASS | PASS | MU_PEER ex_tsvc_mu0 rc=0: PASS token service epoch all8 pendingACK/actualBAR/barriers UNQUALIFIED capture256 q |
| peer | ts1 /ERR cyc [0-9]+ token service fault/ | FAIL | FAIL (regex hit) | ERR cyc 558 token service fault |
| peer | ts2 /ERR cyc [0-9]+ token service fault/ | FAIL | FAIL (regex hit) | ERR cyc 6023 token service fault |
| peer | co1 /ERR cyc [0-9]+ coordinator fault/ | FAIL | FAIL (regex hit) | ERR cyc 562 coordinator fault |
| peer | lc1 /POST late \(waited for a global die drain/ | FAIL | FAIL (regex hit) | POST late (waited for a global die drain |
| peer | cd1 /codec 1 post 0/ | FAIL | FAIL (regex hit) | codec 1 post 0 |
| peer | cd2 /ERR cyc [0-9]+ coordinator fault/ | FAIL | FAIL (regex hit) | ERR cyc 561 coordinator fault |
| peer | pc1 /POST late \(waited for a global die drain/ | FAIL | FAIL (regex hit) | POST late (waited for a global die drain |
| peer | ep3 /POST late \(waited for a global die drain/ | FAIL | FAIL (regex hit) | POST late (waited for a global die drain |
| peer | sv1 /codec 0 post 1/ | FAIL | FAIL (regex hit) | codec 0 post 1 |
| peer | ab1 /abort: not all three retained users cancelled/ | FAIL | FAIL (regex hit) | abort: not all three retained users cancelled |
