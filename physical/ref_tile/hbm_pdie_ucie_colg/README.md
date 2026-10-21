
## SAFE review
09:44 UCIE5 SAFE before generation/gates
Cold routed NEEDS_RTL TT-74.66/FF+5.36 DRC0: only failing class rx output; final wire364.63ps from u_lpo_rx.q66, all register D TT>=47.11ps, PMA_TX+182.79ps. Structural colf MAIN / colg FALLBACK keep RTL/ports/data cycles unchanged, expand N strip86.4/129.6um and fence512 rx output flops in dedicated43.2um N-face region through DPL/CTS.
1 pins PASS existing registered interfaces; 2 reach FIX face output drift with dedicated band; 3 fanout PASS unchanged mapped max32 existing census; 4 depth PASS unchanged270ps; 5 storage PASS dualclock SRAM; 6 floorplan FIX enlarged continuous N band, PMA offlattice/aspect inherited slot waiver, no squeeze; 7 clock existing regional roots and macro bindings retained, measured cold55.4/55.7; new CTS must pass; 8 static PASS no cycle change (existing RX+1 applies). Fresh WT codex-hbm-ucie5-1021, exact new names, no live WT touched.


PDN: inherited validated macro_m5 grid retained for M5-PG PMA abstracts; main generator still treats all macros as M4-PG SRAM. Same macro inventory/PG layers as cold.

Placement-stage correction: r3 failed before optimization because the exclusive RX group contained only FIRM anchors (GPL movable area/target density 0 -> NaN). Create the same face region after generic pin-anchor release in PRE_DPL; normal GPL anchors remain. Native32 PASS; no timing/route verdict from r3.
