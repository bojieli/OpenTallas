# HBM fewer-SM die options (OWNER 10-16 ~19:15: more dies, fewer SMs per die; hc_eng stick rejected)
Plan model only (compact_plan + v6_eval, measured block outlines as d4c; rp4e SM 7,755.84 x 1,807.2). Relay area scaled
from d4c (~48 mm2 at 2.75 M relay flops). Reticle check = tools/hbm_die_v15/reticle.py (>= 0.5 mm in W AND H).

| option | SM/die | stacks | W x H mm | mm2 | margins long/short mm | density incl relays | SM_X | SM_HBM | worst cut V/H |
|---|---|---|---|---|---|---|---|---|---|
| d4c (base) | 32 | 4 | 32.43 x 25.43 | 824.8 | 0.57 / 0.57 | 0.84 | 10.37 | 11.78 | 0.494 / 0.621 |
| A2P (recommended) | 16 | 2 | 18.90 x 26.25 | 496.0 | 6.75 / 7.10 | 0.72 | 10.46 | 2.75 | 0.490 / 0.499 |
| A16 (4 stacks) | 16 | 4 | 32.43 x 20.21 | 655.3 | 0.57 / 5.79 | 0.69 | 8.42 | 9.88 | 0.516 / 0.591 |
| B24a (drop row d) | 24 | 4 (or 3) | 32.43 x 24.02 | 779.0 | 0.57 / 1.98 | 0.74 | 8.80 | 9.12 | 0.515 / 0.519 |
| B24d (drop row a) | 24 | 4 (or 3) | 32.43 x 24.02 | 779.0 | 0.57 / 1.98 | 0.74 | 10.79 | 12.08 | 0.542 / 0.591 |

A2P = W half of the die (SW + NW quadrants, one PHY on the S and one on the N edge), 8 SMs per stack as R90 rp4e columns
directly over the PC row (SM_HBM face -> PC row, xw face -> band), centre column (3.1 mm: lk/ep + hc_eng 3.1 x 3.06 mm)
at the E edge. Needs H-SM: rp4e placed R90 or re-pinned with SM_HBM / xw windows on the short faces (1,807 um face >=
360 um xw window). Open in A2P: COLL_EP 17.4 / HBM_VM 38 stages (ep stacks at the column ends, hub far from the PHY) ->
move the ep stacks to mid-column beside COLL, PHY/hub alignment.
uarch_model iso-total-SM (DS AR chain, v41_hbm_n): 96 x 32 SM 505.2 us, 192 x 16 SM 502.8 us, 128 x 24 SM 504.4 us.
compact_plan args: d4c_landscape_rp4e README base + `--sm-rows bc|abc|bcd --centre-strip 2400` (A16/B24) or
`--sm-columns 200 --sm-col-real --half-die --column 3100 --channel 100` (A2P).
