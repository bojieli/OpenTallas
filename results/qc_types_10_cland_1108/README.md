# QC-TYPES-10/CLAND 11-08: class (M) STALE COLLECTOR TREE, landing raw resets wired by NAME into another tree

Proven failure: slw_fe_v1__clfe325744__cldb4efe33 a7 G2 TT -269.56, u_rrl_45/q -> 44 BUFs -> u_cland_reset_rst_n_t29/D.

## Diagnosis
Per type three trees exist (KW-FIX-27): the bind emits the reset relays from RT.for_type(plan) (it never reads
landing_contract.collector_tree for QC: bind.py reads it only for reset.consumer_localization, unused on QC); the
collectors, their sources (sidecar collector.types[T].local_sources/children, tap indices) and the kit placement
(landing_placement.tcl) use the plan/sidecar collector tree.  55 of 88 bound QC types have collector_tree != bound tree.
The collector tree is self-consistent and legal; only the landing RESETS are looked up by name in the bound body.

census2.py on bind_v4w (driver site vs placed site, every landing raw reset):
- u_cland_reset_* copies: 396 > 405 um in 50 types (max 3474 um)
- u_cland_collect_* rst_n reusing a same-named bound relay: 719 in 53 types
- ring raw copies u_cland_rst_<bus>: 680 in 80 types: ring_taps() returned the 2-entry 'glue' clock.taps list on
  tap_mode 'density' types, so every ring took rst_n_t0/t1.

Setting collector_tree := bound tree was rejected as not minimal: 373 sources in 40 types would move and 5 rerooted
collectors (slw_stm_v1__cle34a73c3, slw_su_c__cl92142dac, slw_su_l0 x2, slw_su_l1__cla2a78701) are refused by
reattach_sources.

## Fix
1. tools/die_plan/landing_collector.py: raw_reset reuses a bound wire only when its relay is the collector-tree relay
   (same site within 1 um and same depth, from the body's '// ... depth D @ (x, y)'); else the copy chain along the
   collector tree (cycle-equal, every hop a legal collector-tree edge).  check_local_resets (called by build_local)
   fails closed on any copy/collector reset that is not its collector-tree parent/own reset.  Agreeing trees: no change.
2. tools/die_plan/clock_landings.py ring_taps: tap_mode 'density' uses reset_tree._taps (the index space rst_n_t<i>
   has).  Scan of the 5 wave plans: only QC changes (68 types).
3. Plan event plan_qc53v4m_cland on v4w (e5dc7eacb745), mk_cland_event.py: landing_contract.group_rects_um
   ['u_cland_rst_<bus>'] for the 127 ring raw copies whose kit site (collector-tree site of the source tap) is > 405 um
   from their new bound d relay: the d relay's own site when the ring face is within 405 um, else a point on the d->face
   path keeping both hops <= 405 um, clear of hard cores.  Only group_rects_um keys change (asserted).

## Result (census2 on the re-bind)
copies 0 > 405, collectors 0 > 405, rings 6 > 405 in 3 types (coll_core 1, coll_ftn 3, native59 2: no tap_mode with a
clock.taps list that is not the reset tree's index space either, and the nearest bound tap is 743-1026 um from the face:
residual, open).  Reset trees (tree_sha256) unchanged on all 116 reset_tree.json.

Files: census2.py, mk_cland_event.py, event_report.json, run_bind_cland.sh / run_bind_v4m.sh (strict bind on the
bind_v4w producer tools src_d95ec + this patch, mkfarm.sh + patch_d95ec.py), run_dry.sh, run_tests.sh, rtldiff.py.

## Staged (identical on epyc4, epyc2, epyc5, epyc6, intel1)
- plan: /srv/opentallas-scratch2/claude/qct10/cland/plan/plan_qc53v4m_cland.json (sha256 3132ffe03528..., base v4w
  e5dc7eacb745), with plan/cores (= qct9/cores, 37 files)
- bind: /srv/opentallas-scratch2/claude/qct10/cland/bind_v4m_cland (strict, BIND rc 0, errors 0; rtl digest 73d78bc9ea70
  on all 5 hosts; .sv identical to the v4w re-bind bind_cland)
- affected types (bound RTL or group_rects_um changed): affected.json, 100 types.
- dry: validate PASS 0 errors; G0C FAIL 29 -> 29 errors (same bad types), clean 114 -> 114, 5 WARN values changed
  (geom_tap_sinks x3, geom_clock_reach x2); types / designs / pin rows identical (dry_compare.txt).
- tests: full tools/die_plan pytest base 352bbd4c89a vs tip in one partial tree: TIP-ONLY 0, BASE-ONLY 0, +4 passed.
