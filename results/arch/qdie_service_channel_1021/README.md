# Native59 service channel source candidate

The source plan opens the south and east service gaps from 108 to 216 um. It moves native59 north by 108 um; the system face, D2D, KV PHY and north bump row follow north to preserve their clearances. The embedding provider and system face move east by 108 um. Clock endpoint identities, source masters, shapes, arrays and all reserved pads remain intact.

`receiver_plan.json` binds the prior plan SHA256 and lists all nine moved origins. Planned die remains 32983.2 x 25984.8 um within the 33000 x 26000 um reticle. No new source-macro overlap appears against the complete prior receiver plan.

`captured_terminal_model.json` preserves all 58 distinct actual blocking rectangles from r20 MAIN's native59 embedding terminal receipt. Translating the 274 original candidate sites north with the receiving pin leaves 41 candidates unoccupied against the captured reservations and source macro obstacles. This is a local model, not a placement PASS: reservations outside the old receipt, final corridor predicates, root geometry, clock phase, route reach and actual transport ages require the new full GEN. The source and occupancy hashes are recorded in the artifacts. No reservation was deleted and no search or acceptance threshold changed.

The next MAIN/fallback source keeps exact lctx1/L_CONTEXTS=1 and qualifies the separately measured QB_ALIGN1/QB_LOCAL321 tuple. Later source-qualified L-context wrappers require their own explicit boundary ages and source pinning.
