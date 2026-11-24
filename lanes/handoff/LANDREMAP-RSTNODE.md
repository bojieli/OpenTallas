# LANDREMAP-RSTNODE handoff (11-23 22:1x PST)
Job: landing_remap rewrites tap reset node names (rst_n_t<i>) after a grow / re-floor. DONE.
- Landed main 29d2fff35ccd (commit 4603e459d7a): tools/die_plan/landing_remap.py (rstnode_* functions, pass at the end of every
  --resets mode, --resets rstnode = pass alone, receipt rstnodes / rstnode_unresolved) + test_landing_remap_rstnode.py (13 tests).
- Proof epyc11 /srv/opentallas-scratch2/claude/landremap-rstnode/prove (prove.sh, prove2.sh, cmp.py):
  A: A1b cf1eadc2cb91 -> A3g b258e3e34f22 --resets rstnode == e186567f8dd6 (exact JSON), hroot 27 finals t11->t12, io_ft_v1 5 chains, 0 unresolved.
  B: default resel, --types hroot,io_ft_v1: raw branches equal hand row (resel also republishes io_ft_v1 collector_tree, existing behaviour).
  D/E/Q no-op: A1b->e186567f8dd6, A1b->A1b, QC s29 V0E->itself unchanged. C: A3g->A3g rebuilds the 5 stale io_ft_v1 chains (A3g is stale).
- Lane clones: epyc10 + epyc11 /srv/opentallas-scratch2/claude/landremap-rstnode/wt.
- Open: PRECHECK-DERIVED-DROP to align its stale-name check with rstnode_map/rstnode_apply (dry run on a copy).
