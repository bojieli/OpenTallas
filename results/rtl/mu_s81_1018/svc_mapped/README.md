# MU.TOK.DS2 -- svc_rs 2-user gate on mapped memories (SRAM_MACRO=1)

Source commit 97704bf25 (tools/s81_dv/svc_rs/mu_bench.sh + check_mu.py, tb_dsdv_svc_rs.sv), Verilator 5.050, ot-epyc5
(fleet run dir /srv/opentallas-scratch/codex/mu-s81-svc-97704bf25/out/mu). Gate verdict (otrun_client.log):

    SVCRS_MU_GATE PASS component_only=1 user1_shift=8192

| log | what | verdict line |
|---|---|---|
| default.log   | single job, defaults (regression)              | SVCRS ... T=46 ... verdict=PASS |
| single_u0.log | user 0 alone                                   | SVCRS ... T=46 ... verdict=PASS |
| single_u1.log | user 1 alone (T=428, nsel 300)                 | SVCRS ... T=428 ... verdict=PASS |
| mu.log        | users 0 and 1 back to back, user 1 start +8192 | SVCRS_MU users=0,1 job0=PASS job1=PASS verdict=PASS |
| mut_sb.log    | mutant mumut=1: job 1 WIN_LOAD SB = user 0's SB0 | SVCRS_MU ... job0=PASS job1=FAIL verdict=FAIL (expected) |
| mut_user.log  | mutant mumut=2: job 1 WIN_LOAD user = U0 (user 0 window ring) | SVCRS_MU ... job0=PASS job1=FAIL verdict=FAIL (expected) |

Both mutants fail only user 1 (sc/se/pv errors) and leave user 0 bit-exact: the per-user region bases separate the users.
component_only=1: the service on its own (not the die); grade = measured, component.
