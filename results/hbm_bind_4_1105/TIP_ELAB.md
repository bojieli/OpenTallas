# Tip elaboration bound (HBM-BIND-4, 06:53 PST 11-05)

Sources and plan: fb1ec2d898 RTL, plan e891fa51a5. Strict bind: 48 UNPLANNED, 42,407 b, tied/undriven/multi 0, same error list as the frozen netlist.
Chain: bind.py elab with the coll parents read in full (replaces splice_coll donor; qhub already read in full), dead_scorer_loop_index, normalize_mem, fused_lower_tree_splice, rename.py.
Known limits: normalize_mem stopped at its map-home step, so it wrote no receipt. Its netlist output was used; the frozen map supplies homes after rename.
rename.py ranks equal-signature cells; 14 net-bijection mismatches remain, inside ot_hbm_hc_bank_static (2) and ot_hbm_hc_qcen_static (12).
RTL after fb1ec2d898 touches leaf bodies only (read, not elaborated). bind.py verify has not run: it needs a clean bind.
