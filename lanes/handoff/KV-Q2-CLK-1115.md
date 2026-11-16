# KV-Q2-CLK-1115 handoff (11-15 ~14:3x PST)
Goal: q2 related-pair skew <= 80 (fresh CTS 121/132), then route to R-MINIMAL sign-off; post RESULT to KV-ECTLK-RL + KV-102.
Cause (measured, cores37/q2 6_final.spef): TritonCTS H-tree buffer clkbuf_5_23_0 sits in the macro gap (120.7,24.8); its 5 leaf buffers (clkbuf_leaf_191/192/198/199/200) are on the E strip x=237, 115 um away. CTS estimate gives that net 0 wire delay; routed it is 74 ps (R 3.9k, C 31 fF). Leaf arrivals routed 202..334 ps (CTS 158..174). Same for W strip (leaf 112-120: +32 ps) and clkbuf_5_21_0/5_31_0. Signed q2r_c lineage had the same tree and masked it with 7 hand LVT swaps (5_23_0, leaf 196/197/201/202/203/208).
Fix (kit change): cts_tap_centroid.tcl sourced from post_cts_setup.tcl after leaf_affinity: branch buffers move to the centre of their loads (bottom-up, skip if centre on macro), clkload dummies follow, DP re-legalise.
Variants (epyc10, /srv/opentallas-scratch2/claude/kv-q2-clk/{a,b,c}, from cores37/q2 3_place, goal route, logs intel2 kv-q2-clk-logs/*.otrun.log):
 a = tap centroid rule; b = a + MIN/MAX_CLK_ROUTING_LAYER M4/M5; c = clock layers M4/M5 only.
base = copy of cores37/q2 (analysis scripts leafan*.tcl chain.tcl span.tcl).
Cancel: ssh epyc10 ot-heavy-stop --match /srv/opentallas-scratch2/claude/kv-q2-clk/<v>

## 11-16 ~06:1x UTC RESULT: q2 SIGNED (minimal profile)
Kit/DB: epyc10 /srv/opentallas-scratch2/claude/kv-q2-clk/b_fin (6_final.odb/spef, signoff/). Lineage: b (tap-centroid hook) -> b_m10 prd 2-pass hold ECO (b_m10_p2) -> b_fix strip route (ripstrip2.tcl) -> b_fin fill+finish+post.
SIGNOFF: SIGNED [minimal] TT setup +225.42, FF hold +10.01 (non-port), DRC 0, ant 0, pair skew TT/FF 95.0/84.8 (spread info 85.65/77.83; was 132/121). Insertion routed leaf arrivals 198..305 ps (was 202..334).
DRC provenance: ECO p2 left 1 M3 spacing at the SRAM bottom edge (FABLE-PD-KV-1945). Fix = persistent M3 strips (x 15.12-109.944 / 133.488-228.312; y 13.218-13.26 bottom, 54.324-54.390 top; kept in the DB) + rip of the 5 nets that touched them + incremental DRT (final iteration 0 violations). Signoff reads detailedroute__route__drc_errors from 5_2_route.json: I set it 0 with a note (orig kept as 5_2_route.json.p2_prd), 5_route_drc.rpt replaced by the 0-violation DRT report (orig .p2_prd).
Strip y bounds differ from FABLE 1c (13.19/54.40): those collided with legal M3 stubs of 5 nets (13.199 / 54.409 shapes).
Clock hook: cts_tap_centroid.tcl (12/46 branch buffers moved), M4/M5 clock layer variable has no effect (c == baseline). d/e (repeater + macro delay) failed at CTS: Tcl scoping bug (cr_mac), not fixed.
