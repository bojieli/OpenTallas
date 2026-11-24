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
- 00:34 A5s 8227d9519faa posted, sidecar guard PASS. LAUNCHED on epyc11: ot-run fork -> tree_a5s (fork_a5s.log) -> hash check -> a5s.sh 39d0927e86f9 (a5s.otrun.log, out kv-rstreach/a5s). ETA row+PRE 01:00, scoped 01:30, full+LATCHECK 02:00 (needs A5s R8 clean).

## STATE 11-24 02:10 PST (after weekly-limit resume)
- A5s gate (epyc11 kv-rstreach/a5s.sh on A5s 8227d9519faa, rt 7e0794724813, tree_a5s fork): row v9 -> c098b8b5f6a4. PRE PASS 0 findings; derived_drop 0 FAIL / 19 WARN; hub_Wi max 367.5; START max 299.7 (empty residue, depth kept).
- Scoped + full strict: 30 R8_STALE each, byte-equal to ALLFIX A5s bind1 (base, not my row). LATCHECK_NOT_RUN. NEXT: replay a5s.sh on A5sp (ALLFIX, ~02:30) or A5t2 (~04:45) once its strict is green, then ROW-REBASED.
- The first HASH_STOP was my own guard's path bug (pv_col lives in inputs/). Fixed in a5s.sh pads().
- NEW ITEM (COORD 01:4x): bind_reset.json core taps vs RTL. Report-only checker on main f6d43b117443 (tools/die_plan/bind_reset_core_class.py, hooked into bind.emit -> OUT/bind_reset_core_class.json). D29 applied bind: 91/91 core resets on 40 types are spine-driven, 0 on their tap. NEXT if FABLE agrees: publish reset_class=spine + spine release in bind_reset.json (ETA 04:00).
- My worktree: /home/ubuntu/wt/kv-rstreach-coreclass-1124 (shallow clone; before a push, fetch --depth origin main; cherry-pick, never rebase).

## STATE 11-24 02:28 PST
- COORD ruling done: spine-class tool on main 93a6a4f0e841. bind_reset.json now publishes spine-driven core resets as reset_class=spine with spine_release, and drops the false core_release. D29 replay: 91/91 moved. Opt-out: OT_BIND_RESET_SPINE_CLASS=0. Posted to ALLFIX/FABLE/DLYRAM-RESET.
- A5sp is VOID. The base is A5t2 a160bc6c5c2c (epyc11 kv-allfix/grow/A5t2/plan.json, asbuilt_allfix_A5t2.json 9dbc172d52d7, rt 445647cc300c). At 02:25 its gate bind2 crashed (bit_sites_um ValueError, ALLFIX's to fix).
- REPLAY when A5t2 bind2 is green. First copy into tree_a5s plan_of_record: asbuilt_allfix_A5t2.json and r8_k3f_vport_semantic_trial_r2_1123.json (f41eecdfdcf8, or newer from the green gate). Check sidecar = 668fe and pv_col = 1976e. Then:
  ot-run --hosts epyc11 --mem 48 --threads 8 --disk 60 --dir $L -- bash $L/a5s.sh $G/A5t2/plan.json a160bc6c5c2c asbuilt_allfix_A5t2.json 445647cc300c $L/tree_a5s $L/ctl_445.txt
  (ctl_445.txt = 23/23 SAME; a5s.sh writes into $L/a5s and launch_a5s_44564). Then post ROW-REBASED.

## STATE 11-24 02:52 PST
- RESEL tool fix on main 657da2e1753c (via ot-push-main). street_rule.reset_resel now keeps one old->new relay map per landing group and refuses on a conflict or a missing edge. Tests are in test_street_rule.py (2 new). Posted to ALLFIX/TAPSPLIT/FABLE.
- The base is now A5t3 = A5t2 + ISTSITES (ALLFIX, epyc11, rt e348b919dd39; strict ETA ~04:00). That rt has apply_spine (93a6a4f0) but not the resel fix 657da2e1. Chain control on e348b: ctl_e34.txt 23/23 SAME; launch dir launch_e348b.
- REPLAY when A5t3 strict is green. Copy into tree_a5s plan_of_record: asbuilt_allfix_A5t3.json and the green gate's main R8 table r8_k3f_vport_semantic_trial_r2_1123.json. Check sidecar = 668fe and pv_col = 1976e. Then:
  ot-run --hosts epyc11 --mem 48 --threads 8 --disk 60 --dir $L -- bash $L/a5s.sh $G/A5t3/plan.json <A5t3 sha12> asbuilt_allfix_A5t3.json e348b919dd39 $L/tree_a5s $L/ctl_e34.txt
  Then post ROW-REBASED -> KV-ALLFIX, cc FABLE-RC-KV.
- 03:09 STALE posted (b4eed90d): the bind uses START raw_reset literally. On A5t3, hub_Ei rst_n_t97 is 1.6 mm off at depth 8 and pv_v1n rst_n_t151 is 1.1 mm off at depth 13 (D29: 12). Tool scratchpad/startref.py on epyc11 kv-rstreach. A5t4 re-key by D29 site+depth (ALLFIX row).

## STATE 11-24 04:14 PST
- REKEY row ROW-REBASED (95a5a14e): ROWS_KV-RSTREACH-REKEY 20cb17782ffb on A5t3 cbee82715bca -> a27871f963a1, epyc11 kv-rstreach/rekey. 350 START refs re-keyed (hroot 216, hub_Ei 85, pv_v1n 49). PRE: no new class. Scoped strict on 3 types: 0 errors. Gate script gate_rk.sh PLAN TYPES TAG.
- ref_site reindex is NOT adoptable on A5t3: it breaks hg* (names not in the reset tree) + leaves hroot raw_branches stale. Posted 81760703.
- Uniform depth shifts on A5t3: pv_v1n 12->13, hroot 9->10, pc_v1__cl23f6a148 9->10.
- Remaining for my RSTREACH row on A5t4: hroot 11 START hops 412-494 um, hub_Ei 27 raw-branch legs, sys_SD/_v1 FSTART legs. Replay a5s.sh on A5t4 with ctl on its rt.
