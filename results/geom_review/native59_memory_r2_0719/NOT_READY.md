# Parked at Claude reset: NOT READY

Current helper has snapped macro origins on an8.64um lattice. Exact FT packing with8physical memories completed21slots,max actual paired-bit hop364.99um, scratch plan_ft_r2.json/ft_ledger_r2.json. No place or route launched. Plan data has not been adopted into any release plan.

Critical discoveries immediately before parking:

- The original placement review incorrectly assumed SRAM read ports on the RIGHT edge. Actual LEF rd_out[0] and subsequent read pins are on LEFT. The left column must be MY and right column R0 to face read data toward central mux. Current helper STILL has R0 left/MY right: DO NOT ADOPT it.
- Actual kit M4/M5 track offset0.024,pitch0.048um, while SRAM signal pin rectangles0.000..0.024 or y0.768..0.792 have centres at0.012 modulo0.048. An additional origin offset0.012um on bothaxes appears necessary to align centres, but MUST be checked for all transformed signal/clock pins. This has NOT been implemented or verified. Current8.64um snap alone is insufficient evidence of access.
- After fixing orientation/origins, rerun exact FT siting (shared macro obstacle fix0302d3b06a), render and inspect channels/pin access/clock/PDN, and reprice any station count changes before adopting. Existing scratch21slot exact packing is provisional with the old orientation/origins.
- No RTL/new storage/data cycles changed. Existing8writer banks occupy101966.688um2. Future FT count changes may add cycles and require model/bind update.

Branch codex/qc-native59-0719 contains main3947653943 + native helper cherryc3d06bcdcf + shared obstacle cherryc4211ef67a + this parkingWIP. It is NOT a merge candidate. Existing original PASS-COND review remains historical and did not authorize route.
