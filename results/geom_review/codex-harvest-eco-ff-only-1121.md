# HARVEST-ECO FF-only review, 2026-11-21

Type slw_sc_v1__cl64543eaf__cl5e017c6f, QC N3 attempt 2. Existing routed checkpoint and sign-off are in the Intel1 recover1120 seed.

Reviewed placement, GRT congestion and detailed-route wire images at intel1:/srv/opentallas-scratch2/claude/qc-hold-0030-kits/recover1120/slw_sc_v1__cl64543eaf__cl5e017c6f/run/layout_review/{place/layout.png,grt/congestion.png,route/wires.png}.

One core sits in the east half with open routing channels on every side. The strongest congestion is at its southwest corner alongside a dense tap cluster. Horizontal signal corridors wrap around the macro. West-edge pins have long vertical feeders along the outer aisle. No new pin or macro placements, added relays or tap changes are proposed. Color views show signal congestion. The existing route sign-off reports DRC 0, TT setup -36.33 ps and internal FF hold -6.87 ps.

PASS for the one targeted internal FF pad ECO on this reviewed seed. Use the existing 833 ps TT/FF sign-off and LEC. Read the resulting route and congestion before further attempts. The other two HARVEST types need their own reviews before an FF-only trial.
