# PRECHECK-DERIVED-DROP handoff (Opus 5.5; COORD split 11-23 21:36 PST)
Job: PRE FAIL classes for derived plan sections a re-floor / grow / tap rewrite leaves stale. ONE job.
## Code
- tools/die_plan/derived_drop.py (RSTREACH + DERIVEDNAME) + test_derived_drop.py + plan_gate_pre.py hook (CLASSES, check() before ADVISORY, base = remap base, bind RTL = --elab-dir else <plan dir>/bind_of_record).
- Lane clones: intel2 (commit wip, rebased on main 29d2fff), epyc10/epyc9/epyc7 (main + git apply tmp/dd.patch; files re-copied from localhost scratchpad).
- DERIVEDNAME b = landing_remap --resets rstnode oracle (COORD ruling 22:xx, 29d2fff35c): anything the pass changes = FAIL.
- RSTREACH: START/local raw hops (reach_rules.raw_hops, G0 R-REACH-5 at FAIL), FSTART raw coverage (bound cland_start_raw site from bind RTL = FAIL; plan-only L1 radius = WARN since face-flop role is a bind fact; kv3_pv*e have no face flops).
## Proof runs (dd_run.sh TAG PLAN TREE BASE [ELAB]; runs/<TAG>.log)
- epyc10: kv_A3g_base (A3g b258e3e34f22, base A1b cf1eadc2cb91, elab gate_A3g/bind), kv_A3g_rstrelay (3d130f381902), kv_R1 (RSTNAME e186567f8dd6, copied to inputs/).
- epyc9: s81_c7a_tail(_v2) 90698b2ec067 vs s81_lostart(_v2) a39888d9ebe1, base J8 plan_h2_2249, tree amd1_tree.
- epyc7: qc_c1b_v2 (62ce8aba0292), qc_c1c_sul1_v2, head_r18g_v2 (base r18f).
## Findings so far (v1, RSTREACH valid)
- KV A3g: 15 pv FSTART FAIL bound (pv_v3 rst_n_t111 11/11 co-sited, 2027 um) -> PASS on 3d130f381902. New: hub_C (rst_n_t32 drives 56/80 FSTART >405, 3595 um), hub_Wi (45/74, 2705), sys_SD/_v1 (2/2, 828/752); START raw pointers stale hroot 226 (1750 um), hub_Wo 42 (2016), pv_v1n 47 (1417); raw branch base->copy0 legs 414-817 um on hg/hgi/pc/hub_Ei/hub_Wo/hroot (base relay moved ~112 um = grow).
## Next
- read v2 runs, land via ot-push-main, post PRECHECK, KV-ALLFIX, FABLE-RC-KV; findings to owners (S81-ALLFIX-INT, QC-ALLFIX, HEAD-R18).
