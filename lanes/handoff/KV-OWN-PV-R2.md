# KV-OWN-PV-R2 handoff (Opus 5.5, started 11-24 09:35 PST; successor of KV-OWN-PV). ONE job: A5t6 row (1) stations on pv_v4/pv_v4n SE legs.
## Facts
- Cause: o_vport_E_N_vo_p (512b) + o_vport_E_N_vo_d2_p (v4 256b / v4n 128b bound) have NO internal_stations row in A5t3 cbee82715bca; bins -> E-face bout one cycle, 753/756 um. Lanes L2720/L2721 (pv_S_4->4e), L2730/L2731 (pv_N_4->4e).
- Probe kits (A5t3, epyc11 kw43-wave-1109/.../KV-D29/private/KV-ALLFIX/kv3_pv_v4_1124043356, kv3_pv_v4n_1124043438): stopped at 3_place; geom GRT ended at extra iter 4/50 -> no GRT census number.
## Lane dir epyc11 /srv/opentallas-scratch2/claude/kv-own-pv-r2
- ROWS_KV-OWN-PV-R2-V4LEGS.py 75d57fa0e1f4 (cwd = launch tree; data embedded from grp_v4*.json measured place + bound RTL bit maps).
- jobA.sh: A5t3 + row -> reprice -> fill -> LATREGEN check -> census -> PRE (+diff vs A5t3 pre.log) -> G0. Out A5t3v4/. Logs intel2 ~/tmp/kvownpvr2/jobA2.otrun.log
- tree/ = ot-tree-fork of kv-allfix/grow/tree (fork2.otrun.log). jobB.sh = scoped strict bind --types kv3_pv_v4,kv3_pv_v4n, out bind_V4LEGS/.
- ot-run needs --stage for every path outside --dir named in the command.
## Log
- 09:55 row rc0: L2720 0->2, L2721 0->1, L2730 0->2, L2731 0->1; max hop 326. Posted CAUSE+ROW DRAFT.
- 10:3x PRE = A5t3 set (0 new) after fixing 2 GEOM-STATION-IN-CORE (regs_um now real bank centres); row ce6761dc6ef7, plan 7112b2fc4e5e.
- 11:2x G0 PASS (g0_V4LEGS); A/B scoped bind: base 0 err, row 30 R8_STALE.
- 12:2x jobR: r8-prepass -> regen (regen/regen.py, resolve.py, apply.py; lane tree) pv_v 321c805aa876 -> 1a1c15ce11ef (80 regen), rebind 0 errors (bindr/). Posted ROW-REBASED. Lane tree inputs now hold regenerated tables. JOB DONE; waiting only on KV-ALLFIX A5t6 compose.
