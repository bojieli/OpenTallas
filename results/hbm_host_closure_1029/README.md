# HOST inherited LEC diagnosis

The h4 source proof finished after 11,585.3 seconds: UNPROVEN, 16,827 compare points, 16,702 proved, 122 differ, three undecided. This is not an equivalence pass or a confirmed functional counterexample.

All 122 differing points are codec q_pin next-state functions. Every cone has exactly two unmatched state inputs: one RTL SRAM dout register and one anonymous gate FF. There are 84 bits from bank0 and 38 from bank1. The exact bijection is recorded as UNTRUSTED hints. No hint has been proved or adopted. The existing LEC tool can test such hints by induction using its --reuse option on a NEW output directory; a false hint is dropped, never waived.

The other three cones are epoch_abort (901 support points and three gold X sources), and p_tx_v/rx_v (898 support points, no unmatched state keys), which reached solver limits. These remain open. No X waiver, reset extension, changed source, or repeated full HOST proof was used. The coordinator directed no new old-profile full LEC.

Runtime: epyc2:/srv/opentallas-scratch2/claude/codex-hbm-host-1029/kits_h4/ot_hbm_host_cp_rxs_b41d079f0d99-_c25b_h4/lec. The original AIGs, maps, verdict and solver logs are retained there. The compact diagnosis generator reads lec.json and emits this exact candidate mapping without modifying the proof or source.
