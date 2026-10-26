# FLOW-CANARY takeover 17:13

Source: actual hub main c51d6d93039d; own sparse scratch2 worktree epyc1:/srv/opentallas-scratch2/claude/wt/codex-canary-1713, branch codex/canary-1713. No new heavy jobs launched.

| Item | Current / jobs | Failure and next owner |
|---|---|---|
| HBM TKM canonical359 / AB e68 | inherited live FF GRT hold repair, 11803/15066 pads, WNS −107.14/−98.65 at first read | Clock depth ~522ps vs250; CLOCK/TRUNK structural successor. INFRA owns liveness/locks, no inherited mutation. |
| HBM SRAM c51 | terminal, no route | Actual postcts Tcl crash `ot_pinreg_set` undefined: HBM generator omitted pinreg_measure.tcl. READY c3ba1b9fb8 fixes HBM and same modern S81 legacy dependency. Current spec INFO grt_gate=false masks stage; overall still FAIL, source diagnosis retained. |
| QC coll_ftm c51 | terminal FF gate −167.66ps/2324 | Known production21tap structural input/control hold; Qwen+CLOCK own plan/control/receiver correction. No replay. |
| HEAD c51 | terminal insertion TT216.86/FF173.49 FAIL | Tap pre-pass default remains opt-in; no current default-on approval. Parent FLOW/CLOCK owns shared clock correction. |
| S81 latest2cf25 | terminal insertion TT226.54/dev23.46 FAIL, FF183.35 PASS | Same insertion deficit; no waiver. |
| KV type c51 17:02 | inherited live | Collect terminal; INFRA owns operations. |
| KV core c51 17:02 | inherited live, preflight544pins PASS | Collect current physical signoff. Current main already fixes vectorclock/reset-role false face cover; no duplicate patch. |
| KV ffgrt A/B976d | terminal16:55, routed TT−57.66/254EP FF−1.01/1; DRC/DRV/pair PASS | OldFF-builtCTS bug fixed and reset recovery now+257.81MET. True global TT line[38]→g_d[0].u_b/u_ca.r[105] fanout/decode, FF internalr[65]→err[0]. KV cores explicitly owns structural check vs current source. A/B copied checker has missingface_guard import and oldbound-ff rejection; not canonicalPASS. Signoff libraries are old wildcard sessions, diagnostic-only version qualification. |

READY c3ba1b9fb8: core helper packaging; two focused runtime packaging/Tcl availability tests PASS. Source only; no P&R reroute, no changed timing/clock/RTL/cycles. Parent root merges.

2026-10-25 17:26 PDT: READY corebundle adoption codex/core-bundle-1713@4d2faeb22e, own sparse epyc1scratch2 wt/codex-core-bundle-1713. BasePROTO f8931b1446 + c3ba dependency cherry38823db92d; six packaging/runtime testsPASS. No gen_phys edits. Parent root owns integration. Next one read-only exactnative qualification of retainedKV ffgrt AB afteractualimage review; no reroute or canarybinding.
