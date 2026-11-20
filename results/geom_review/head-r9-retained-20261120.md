# HEAD r9 retained route review, 2026-11-20

Viewed the exact original E10 r9 attempt's placement and GRT maps for hd_ctl_n, hd_spn_eshim_rx, hd_spn_eshim_tx, hd_spn_wshim_tx, hd_st_n3_transit and hd_st_n3_turn. The original images are in `head-crossing-1119/kw_r9/items/<type>/gen/<type>/run/layout_review`. The contact sheets are [placement](head-r9-retained-placed-20261120.png) and [GRT](head-r9-retained-grt-20261120.png).

- hd_ctl_n has boundary bands on the north and west with isolated fan-out clusters. The route-pressure map shows diffuse stripes across the core and no concentrated central choke point.
- The east shims are narrow vertical corridors with edge pin bands. Receive pressure appears at the opposing edges. Transmit has an annotated upper-edge cluster and a localized clock finding. Both congestion maps remain diffuse through the corridor.
- West transmit has paired side-edge rows and a small east clock annotation, with open central area in the placement plot and broadly distributed GRT pressure. Its canonical pins `31e82022b2ca` differ from HARVEST's signed predecessor `b27ec46f652a`, so its retained r9 route is a distinct physical candidate.
- North transit and turn are shallow horizontal corridors with localized top and bottom annotations respectively. GRT pressure follows the repetitive routing grid, and the annotated boundary groups remain the regions to inspect if STA reports seam failures.

Geometry reviewed for STA-only recovery of retained final routes. Original routed ODB/SPEF, successful route and LEC artifacts and failed signoff traces remain intact. No layout edits or reroute proposed.

The archived PG-aware north turn `6eca20321243` has canonical pins `bf449d377dbc`, distinct from the retained r9 north turn `40ce5a00339`. Both signed predecessor forms stay in the counted archive.
