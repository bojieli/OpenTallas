# KV-RSTREACH handoff (Opus 5.5, COORD 11-23 22:45 PST)
Job: PRE RSTREACH FAILs on KV A4b (01311e0c5cce) outside pv (KV-PV-RSTRELAY) and hroot/io_ft_v1 names (KV-RSTNAME-REMAP). ONE row.
## Scope (A4b plan-only derived_drop = 22 FAIL, all mine; + bound FSTART hub_C/hub_Wi/sys_SD/_v1)
- (a) FSTART no raw branches: hub_C (no cland_tstart_in: no origin branch), hub_Wi, sys_SD, sys_SD_v1 -> full derive.
- (c) stale base legs: hg, hg_v1__r8 x3, hg_v1p2, hg_v1p3 x3, hg_v1p4, hg_v1p5, hgi_v3, hgi_v6, pc__ x4, pc_v3, hub_Ei, hub_Wo -> re-derive SAME consumer set.
- (b) START raw re-point: hroot 226, hub_Wo 42, pv_v1n 47 -> reach_rules._fix_raw_edges (nearest same-edge leaf tap).
## Files
- epyc10 /srv/opentallas-scratch2/claude/kv-rstreach: ROWS_KV-RSTREACH.py, row.sh OUT RTL [PLAN], dd.sh TAG PLAN [ELAB], runs/.
- epyc11 same dir: tree (ot-tree-fork of kv-allfix/grow/tree), gate.sh TAG PLAN TYPES (PRE rt 9b19 + elab + scoped strict + derived_drop + LATCHECK), A1b_plan.json (dd base).
- Row input RTL = kv-allfix/grow/gate_A4b/bind/rtl (ALLFIX full strict of A4b).
## Log
- 22:4x TAKING. A4b plan-only dd: 22 FAIL. Row drafted; dry on A3g bind RTL.
- 23:1x (b) START re-point works (hroot 228/hub_Wo 42/pv_v1n 47 -> 0). hub_C slow -> route memo + straight-line prune. hub_Wi 14 consumers need 405 hops (co-sited tree). Branched types: bound cland_start_raw is a copy -> use common last original. kv3_hg* ft0_o/o_ectl kf,rq pocket -> last copy at nearest legal site (58.32, ~245).
- 23:3x ROW b1d007efa962 on A4b (bind1 RTL snapshot epyc10 kv-rstreach/rtl_A4b_bind1): 23 raw types 688 br 2296 copies max hop 404.6 + START 3 types -> r2 91859c83c90e. Gate A4b_r2 on epyc11 running (gate.sh; types list incl hroot, pv_v1n).
- 23:28 COORD: target is now A5 (A6 reach FAIL no skip). ALLFIX A5fix/f2.json (epyc11 kv-allfix/grow/A5fix, F1 remap + F2 START) leaves 19 = my (c) set. Next: row on f2.json with LAUNCH=kv-allfix/grow/launch_cced8, RTL = gate_A5/bind/rtl after bind2 emits (epyc11 row.sh has LAUNCH env). Then gate on A5.
- 23:5x CORRECTIONS: A4b RTL was from gate_A4b bind2 mid-emit (never completed). Tool max_hop went to shifted target; real hub_Wi 406.7 -> A4b dd 1 FAIL. 317/317 START re-points keep depth.
- RULING FABLE 6605dfb7 (COORD adopts, replaces 404.6): hub_Wi <=390 else one added relay (not expressible in literal copies: report). No >300 on other types.
- v8 ROWS_KV-RSTREACH_v8.py 886fafd8f1be. epyc11 kv-rstreach/a5row3.sh (base RTL from a5row.sh a5/base; old unit oth-ubuntu-4018735-1795506526 cancelled after RC_BASE_BIND). Base A5r 41044638cda3, rt d97edba9f3a3, tree5. hops.py = independent leg audit. LATCHECK needs FULL bind (+r8_refresh in tree5). Forks only under ot-run; refusal -> post text.
- TODO: read hub_Wi probe reset recovery; A6 re-site tree <=300 if it misses.
- 00:0x COORD: START <=390 accepted, LATCHECK on full strict. v9 17cfe81b9955 (START >300 -> nearest same-depth tap; supersedes v8), a5row3.sh 6a1f006f69b8 = row, PRE, scoped strict, dd, FULL strict + r8_refresh, LATCHECK. GENDRY 77 lines diff 0 vs A4b base.
- 00:1x COORD ruled A5s (A5r minus FTLOCKUP/STREETSTN); row replays on A5s plan when ALLFIX posts sha; strict+LATCHECK from A5s; 01:30 withdrawn until new ETA from A5s sha. A5r plan-level job CANCELLED (does not transfer), duplicate control cancelled. No result from A5r.
- Chain method: genchain.py (solve from plan) + chaincmp.py control: A4b on rt 9b19 = 23/23 SAME; d97ed control queued on epyc11 (load cap); MUST be 23/23 before the row RTL is used. First try on epyc10 failed only for missing tree data. 13/23 chains differ A4b->A5r. hub_C raw name PROVISIONAL (bind picks). a5plan.sh = row+audit+PRE template: repoint PIN/AB/T/rt to A5s (tree must be a fresh ot-tree-fork under ot-run; refusal -> post).
- eW_sidecar alert: both forks clean 668fe4614b79.
- 00:3x chain control 23/23 on d97ed and on A5s rt 7e0794724813. epyc11 a5s.sh PLAN SHA ASBUILT RT12 TREE ctl_7e0.txt staged (NO r8 refresh: KV-ALLFIX 00:30; not yet launched). Needs A5s plan sha + KV-ALLFIX sidecar guard PASS, then fresh fork under ot-run.
