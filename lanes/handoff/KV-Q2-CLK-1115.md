# KV-Q2-CLK-1115 handoff (11-15 ~14:3x PST)
Goal: q2 related-pair skew <= 80 (fresh CTS 121/132), then route to R-MINIMAL sign-off; post RESULT to KV-ECTLK-RL + KV-102.
Cause (measured, cores37/q2 6_final.spef): TritonCTS H-tree buffer clkbuf_5_23_0 sits in the macro gap (120.7,24.8); its 5 leaf buffers (clkbuf_leaf_191/192/198/199/200) are on the E strip x=237, 115 um away. CTS estimate gives that net 0 wire delay; routed it is 74 ps (R 3.9k, C 31 fF). Leaf arrivals routed 202..334 ps (CTS 158..174). Same for W strip (leaf 112-120: +32 ps) and clkbuf_5_21_0/5_31_0. Signed q2r_c lineage had the same tree and masked it with 7 hand LVT swaps (5_23_0, leaf 196/197/201/202/203/208).
Fix (kit change): cts_tap_centroid.tcl sourced from post_cts_setup.tcl after leaf_affinity: branch buffers move to the centre of their loads (bottom-up, skip if centre on macro), clkload dummies follow, DP re-legalise.
Variants (epyc10, /srv/opentallas-scratch2/claude/kv-q2-clk/{a,b,c}, from cores37/q2 3_place, goal route, logs intel2 kv-q2-clk-logs/*.otrun.log):
 a = tap centroid rule; b = a + MIN/MAX_CLK_ROUTING_LAYER M4/M5; c = clock layers M4/M5 only.
base = copy of cores37/q2 (analysis scripts leafan*.tcl chain.tcl span.tcl).
Cancel: ssh epyc10 ot-heavy-stop --match /srv/opentallas-scratch2/claude/kv-q2-clk/<v>
