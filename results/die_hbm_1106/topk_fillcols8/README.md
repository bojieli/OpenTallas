# Topk fill-column replicas: source qualification

Opt-in FILL_GROUPS=8 gives eight three-bit fill replicas, one per eight-bit column of every64-bit record. Master fill remains the count/carry control. Each replica samples original n[2:0] on the original edge, reset and clear/ingest priority; this adds zero latency. This is a column partition of the existing shared barrel shift, not eight complete copies of the wide datapath. Default FILL_GROUPS=0 remains the original structure. The top pd3 composition forwards this parameter without changing clocks, ports or writer edges.

Real source matches retained E2 topk kit fa4a6c51ad35 tiles SHA0f283047182d011de2c051f23b876be5e08b83f2bc6d63df61138c281e3bc882. Actual CTS worst path u_ing.fill[1] to o_wd[4077] has -438.08ps: QN704.71 to first datapath gate1559.45ps traverses approximately849ps of fanout/place buffering. Arrival1873.78, capture clock1439.24. Existing ten-hour GRT progress is untouched.

Actual full-ingest RTL lockstep PASS304checked cycles, with reset and clear+ingest. MUT7 flips first active local fill bit, MUT8 samples stale master fill; both caughtcycle14. Initial mutants at column0 were insensitive because the flit format fixes its low16bits tozero; retain that FAIL rather than claiming an effective negative control. Corrected mutants target active column2. Production MUT0 unchanged by this diagnostic correction.

The first native sizing probe omitted canonical ot_keep_regs.tcl; it measured98723std/11659.31982um2 but folded all replicas, so it is not a qualified physical form. Actual retained kit already exports SYNTH_CANONICALIZE_TCL=/work/ot_keep_regs.tcl, which propagates keep-wire intent onto actual flop cells. Corrected native mapping uses this existing hook. No shared synthesis-flow changes. Kept final counts and actual distinct-copy report pending.

Physical geometry/clock/PG and placement of copies remain to be reviewed on a fresh private candidate. No P&R launched. Existing source snapshot/job E5 /srv/opentallas-scratch2/claude/codex-topk-fill-1106; proper map unit3171966-1793974272, proof unit3124388-1793974120.
