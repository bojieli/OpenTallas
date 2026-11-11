# phyrev_1111 (DIE-KV-97, 2026-11-11): kv3_phy / kv3_phy_v1 PHY output-bus station order

Blocker fix for kv3_phy 481ef93659a1 a11 (routed TT -238.78, 904 endpoints): the 6 o_phy_Q__sN_* internal_stations were
written face -> core while data flows core -> face, so kit_istations put station 0 next to the face (zig-zag, last hop
~870 um). event.py swaps from_um/to_um and reverses regs_um on those entries only (same sites, same cycles; EQ by
construction). Realised hops on o_phy_Q__sN_piN_d3: 24 / 292 / 292 / 292 um.

On kvr2_rh 6e1ad24c -> b6f0eb9f (epyc7 /srv/opentallas-scratch2/claude/dkv97/kvcut/phyrev/plan_c.json). 12 entries.
