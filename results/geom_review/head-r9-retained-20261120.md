# HEAD r9 retained route review, 2026-11-20

Viewed the exact original E10 r9 attempt's placement and GRT maps for hd_ctl_n, hd_spn_eshim_rx, hd_spn_eshim_tx, hd_spn_wshim_tx, hd_st_n3_transit and hd_st_n3_turn. The original images are in `head-crossing-1119/kw_r9/items/<type>/gen/<type>/run/layout_review`. The contact sheets are [placement](head-r9-retained-placed-20261120.png) and [GRT](head-r9-retained-grt-20261120.png).

- hd_ctl_n has boundary bands on the north and west with isolated fan-out clusters. The route-pressure map shows diffuse stripes across the core and no concentrated central choke point.
- The east shims are narrow vertical corridors with edge pin bands. Receive pressure appears at the opposing edges. Transmit has an annotated upper-edge cluster and a localized clock finding. Both congestion maps remain diffuse through the corridor.
- West transmit has paired side-edge rows and a small east clock annotation, with open central area in the placement plot and broadly distributed GRT pressure. Its canonical pins `31e82022b2ca` differ from HARVEST's signed predecessor `b27ec46f652a`, so its retained r9 route is a distinct physical candidate.
- North transit and turn are shallow horizontal corridors with localized top and bottom annotations respectively. GRT pressure follows the repetitive routing grid, and the annotated boundary groups remain the regions to inspect if STA reports seam failures.

Geometry reviewed for STA-only recovery of retained final routes. Original routed ODB/SPEF, successful route and LEC artifacts and failed signoff traces remain intact. No layout edits or reroute proposed.

The archived PG-aware north turn `6eca20321243` has canonical pins `bf449d377dbc`, distinct from the retained r9 north turn `40ce5a00339`. Both signed predecessor forms stay in the counted archive.


## Nominal-capacitance re-sign results

All six read-only re-signs finished R-MINIMAL using their original routed databases and LEC. Every run reported zero antenna nets and DRC, and its complete internal FF hold census has zero violations. These local results leave parent qualification open.

| Type | TT setup (ps) | Achieved period (ps) | Export identity |
| --- | ---: | ---: | --- |
| hd_ctl_n | -13.70 | 846.7 | s81_head/ot_s81hd_ctl_nstrip__ax_bc823b4a57 |
| hd_spn_eshim_rx | +12.12 | 833.0 | s81_head/ot_s81hd_spn_eshim_rx__ax_4c8aa73bc7 |
| hd_spn_eshim_tx | +104.53 | 833.0 | s81_head/hd_spn_eshim_tx__ax_cc35cdbc27 |
| hd_spn_wshim_tx | +166.43 | 833.0 | s81_head/ot_s81hd_spn_wshim_tx__ax_a607e4ae46 |
| hd_st_n3_transit | +113.82 | 833.0 | s81_head/ot_s81hd_st_n3_transit__ax_d9a572df28 |
| hd_st_n3_turn | +89.56 | 833.0 | s81_head/ot_s81hd_st_n3_turn__ax_aec95f8839 |

The archive ledger recorded metadata for five variants under their inferred RTL top names. The east TX shim's exact ODB SHA cc35cdbc276d was already indexed under its plan type. Re-sign receipts are on E10 in `/srv/opentallas-scratch2/claude/head-crossing-1119/r9_nomcap_recover_codex/<type>/signoff/signoff.json`.
