# FABLE-FIX-KV-LOCKUP-INERT handoff (updated 11-25, lane RESUMED by COORD ruling)

Goal: reset_replicate `lockup_regions` has no effect in real KV strict binds (hgi_v2__cle0015330: 11 tail copies + "rest" 40 loads instead of 18).

## Known (11-22)
- HGI-R6 wrapper binds (gen/bind_dump_all.py, runpy + early `import reset_replicate`) give 18 with and without private HOME: HOME is not the cause.
- My UNWRAPPED probe bind (R6h plan 64ec19c3d027, rt fda4eaad0e94, unit oth-ubuntu-3304862-1795344180): LOCKUP copies 11 rest 1. Fault reproduced.
- Text handed to reset_replicate.apply is identical in both; so the difference is wrapper vs no wrapper (import order / runpy / forked emit workers).
- epyc8 lane clone + probe log were cleaned; nothing of mine is running.

## Plan (COORD ruling 11-25)
1. Check hub + an A5t8 hgi bound text for the replica count. Fixed -> post CLOSE with evidence, stop.
2. Else: own fork via ot-tree-fork, one instrumented bind without the wrapper then with it (ot-run --priority die --hosts epyc12 --disk 5), find the import-order / runpy difference, fix on main + test, ot-push-main.

## State: CLOSED 11-25 (symptom fixed on A5t8; no code change by this lane)
- Evidence: epyc12 /srv/opentallas-scratch2/claude/kv-allfix/a5t8/gate_A5t8/bind/rtl (A5t8 strict gate bind, unwrapped, parallel emit j=8, 11-25 16:54Z):
  all 11 kv3_hgi* types 18 tail copies, 0 "rest"; all 12 kv3_hg* types 25 copies, 0 "rest". hgi_v2__cle0015330: u_head2_e0 copy has 5 loads and
  u_lk_nk_head2_e0_* rst_n latches read rs_ri_head2_u_score_rst_n_r0 (the e0 copy). The bind's 4 EMIT errors are on hroot/hub_Eo/hub_Wo/pv_v7e, not hg/hgi.
- NOT explained: reset_replicate.py is byte-identical (31580a4bad8f) to the 11-22 inert binds, so the change is upstream (bind.py or plan rows since R6h).
  Root cause of the 11-22 inert case was never found; no regression test exists for it.
- Suggested guard (not done): gate scripts grep hg/hgi bound text for "core rest: reset spine" == 0 after each strict bind.
- Nothing of this lane is running; no fork, clone or kit exists.
