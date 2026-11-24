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
