# KV-PVHG-O handoff (Opus successor of FABLE-FIX-KV-PV + FABLE-FIX-KV-HG; started 2026-11-16 02:36 PST; Fable back 11-21)

Read first: lanes/handoff/FABLE-FIX-KV-PV.md, FABLE-FIX-KV-HG.md (decisions + paths kept there).
My dir: epyc10 /srv/opentallas-scratch2/claude/kv-pvhg-o (pgp.sh, rt1c03 = tools of main 1c0336e240c with the r273 plan_gate_pre fix); intel2 ~/tmp/kvpvhgo (ot-run logs).

## In flight (02:45 PST)
- PV k2 (tap-stable ring plan on kvgeom7yhr 723fd5b4b006): epyc10 fable-fix-kv-pv/ring/kflow.sh k2 (gen -> post_r -> chk -> tapeq). Output k2/, k2c/ (plan), k2n/ (no-raw), k2c/tapeq.tsv. Some rings NO_SITE (stay soft, listed).
  Next: G0 + strict bind + raw rows + full gate with OT_HCPARAM_ALL=1 (run_gate_pvring_h.sh pattern) -> READY-ROWS to KV-102.
- PV h3n (free-tap form + resetfix, Fable's earlier branch): gate running (G0 PASS 0 errors; bind running). Evidence only; k2 is the chosen form.
- HG v25hv 76d7691ad625: G0 PASS 0 errors (2386 warn). Strict bind + R8 + LATCHECK running (fable-fix-kv-hg/gate_bind.sh v25hv -> out/v25hv.bind.out).
- plan_gate_pre (fixed checker) on v25h and v25hv: kv-pvhg-o/{v25h,v25hv}.pgp.out.
- ectlk q0 post-ECO LEC: epyc10 fable-fix-kv-pv-ectlk/q0_m10_p2/lec_final (ot-run from intel2). Waiter died with Fable: export by hand on LEC EQUIVALENT
  (stage.sh on epyc10 -> AGIdock /archive/opentallas-signed-1114/qwen_kvsys/qkd_ectlk_q0__r37_eco1116 + rtx-pro signed-export-1114 + INDEX rows, same form as q1).

## Next
1. v25hv bind passes -> READY-ROWS to KV-102 (views dir physical/die_plan/qwen_kvsys/kvhg1_views_1116 travels with the tree).
2. k2 gates pass -> READY-ROWS pv delta to KV-102; pilot kv3_pv_v1n after adoption on the converged tree.
3. Rebind hg + pv on the converged KV tree (kw45/src_kv_pin_fa627e234cf7 or its successor) once TOOLS-CONVERGE posts it (r249 one tree).
4. hg pilots kv3_hg_v1 + kv3_hg_v3 after ADOPT; follow-ups krsp ring y 371.5, hgi_v1 ectl ring 499 um.
