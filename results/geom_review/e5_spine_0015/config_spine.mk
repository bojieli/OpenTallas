# CLOCK-RESET E5-SPINE (claude/e5-spine-0015, 2026-10-26 00:13 PDT): spine/rib trunk replaces the H-tree.
# Spine x=166 um (logic column) from midpoint, spine points on channel rows with repeater sites, ribs to hubs (<=8 taps),
# <=12 rib legs per spine cluster, one repeater count per level (RMAX 60), no balancing wire. Local trees as E5-EQ.
export OT_DTSH_TOPOLOGY = spine
export OT_DTSH_SPINE_X = 166
export OT_DTSH_SPINE_YS = 15,76,216,261,300,356,400,452
export OT_DTSH_SPINE_HUB = 8
export OT_DTSH_SPINE_RIBCAP = 12
export OT_DTSH_RMAX_UM = 60
