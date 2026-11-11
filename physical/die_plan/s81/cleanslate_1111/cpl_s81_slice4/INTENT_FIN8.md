# FIN8 = FIN7 + station re-site (CPL-S81-SLICE-4, DO_NOT_COUNT), base BASE_1200 b5faa1ba
Same positions, contents, bands and window taps as FIN7 (cpl_s81_slice3/). Only internal_stations regs_um change (FIN8_companion.json, same counts).
Finding: the FIN7 "4-14 hops over reach" were an explorer --delta artifact. In delta mode the explorer shifts the station end points by the
core move a second time, and the FIN7 plan had already moved them (fix.py follow). On the FIN7 plan itself (no --delta) the over-reach is 0 on all 6 types (max hop 394-404 um).
Real residual: new hops crossing the lifted u_cap (leafup_i0/i1/i2/i4 straight segments, bypass 0-3 -> 3-5).
resite.py moves only those regs to lattice sites outside every placement box, with 0 new core crossings (explorer Builder._crosses test) and every hop <= 405 Manhattan.
A crossing-free straight hop has a staircase route of the same Manhattan length, so routed hop <= 405.
