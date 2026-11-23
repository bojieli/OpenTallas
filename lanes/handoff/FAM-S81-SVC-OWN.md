# FAM-S81-SVC-OWN handoff (Sonnet; started 11-22 11:1x; resumed 17:2x)
Types: svc_hi rs t4,t5; svc_lo rs t3,t6; svc_hi pvso_entry t1. All FAIL place PLAN on event 18a2688b741 (J7 plan a6771d121e95), 10:06-10:29.
Cause (all five): PLAN-SRC-MACRO. J7 plan places att capture macros (u_bound.g_u_rsv_NN_u_u_att_land_capture/pmem_capture/pvq_capture, u_rsv.u_att.u_eng tr) but kit-RTL memory closure (s81_svc_memory_closure.py) returned NOT_APPLICABLE (bound lacks native helper ot_bind_native_9c28130c..., count 0), so those instances never exist. pvso_entry t1 also has extra-u path nesting. Not infra; a relaunch on J7 fails identically (prelint rows 10:45/17:22 are advisory only).
Existing fix: OPUS-FIX-S81-SVC-R9 (adopted all svc rows) hi4 att fit + J8 "SVC scoped primary" (+42 rows, PRE/strict/LAT947 PASS, G0 unchanged 58, preview 53ad14f1fc91), FIX-SYNC-S81 CLAND svc ops (j8_cland_svc_ops.json). Respace bind FAILED 13:39 -> respace rows to J9. R9 bind_r9c died OOM 16:22; hi4_face_e7 died 15:15.
Plan: no duplicate rows, no private kit until J8 compose outcome is known; map each type to J8 SVC rows, relaunch on J8 apply (11-23 04:15). Other svc types (rs t3 hi, lo t4) RUNNING gen.

## 11-22 18:0x
- Cause: PLAN-SRC-MACRO = J7 plan places pmem/stage2/tr/land/pvq capture macros; bound has native pmem+land+staging but no pvq, so memory closure NOT_APPLICABLE. R9 +42 rows do not cover the 5 types.
- Built: plan_svc5_v2 (drop pvq) / v2b (drop pvq+land) PRE PASS; plan_svc5_j7.json (J7 base, drop pvq+land, tr paths) for the proof. fit tool on main e589d7c0e6 (s81_svc_att_fit_all.py + s81_svc_memory_att_fit.sh); rt e589d7c0e609 on all hosts.
- Proof: private-spec lo t3 running (epyc7 fork, goal route, rt e589d7c0e609), out spec_lo3. Land stays soft: measure kit cell count.
- COORD 18:0x: R9 makes the closure per-helper (replaces my witness script). NO more per-type witness code. Keep lo t3 proof for cell count; when R9 tool lands re-run lo t3 on it, then relaunch the 5 types.
