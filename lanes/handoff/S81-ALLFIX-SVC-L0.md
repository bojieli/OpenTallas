# S81-ALLFIX-SVC [L0] sub-unit: svc_hi L0 fixture check (FABLE-RC-ALL ef3b30f8 (c): native replay with mutant on restored L0 fixtures)
Work dir epyc7 /srv/opentallas-scratch2/claude/s81-allfix-svc/l0 (lane clone of main 9f3deddc069 in repo/, sparse).
Recipe = ALLQ bench of record (epyc7 tok-verify-2/recovery1116/allq_current1116_r4/run.sh) on current main RTL:
 1. dv_layer_fixtures.py --layer L0 from restored checkpoint dba1be0a + golden ctx1048576_seed20260930 (stage_fix.sh): all shard checks true, 171/171 files = results/rtl/s81_layer_tput_1018/fixtures/L0.sha256.json; vs bench-of-record L0: only meta.json differs (source pins/paths).
 2. lower_svc.py --fixtures L0 --timing-profile closing_allq (stage_img.sh): img_closing (H16 = bench of record form), img_h8 (--heads 8 = as-built), img_h8_srx7xs (engine row, OT_SVC_NATIVE_RT2_CALENDAR=1).
 3. run_svc_bench.sh (tb_svc_lower, 16 dsdv_svc_rs, closing hcores, ALLQ+SMT) base s1/s2 + compiler mutants (stage_bench.sh): bench_a (H16), bench_c (H8 as-built defs OT_SVC_H8 H8_REUSE_RT2 MERGE_H4 GP=1076), bench_b (H8 + SRX7 XS BCAST calendar). driver3.sh / driver3.log.
Cut-free: no OT_SVC_ATTCUT / CUT_D in any arm. J8 asbuilt_run.json svc defines = ALLQ, ATTN_HCORE, ATT_MEM_MACRO, H8, H8_REUSE_RT2, MERGE_H4, GP=1076 (no ATTCUT) -> J8 records cut-free.
