# s81hd_spr_f (S81-HEAD HD-TILE 10-21)

S81-HEAD HD-TILE 10-21 FALLBACK: new spine node ot_s81hd_spr (SPEC v1 section 2, 26 a die), std-cell only, 259.2 x 691.2.

SAFE checklist (owner 10-19 / safe_1021, 8 points) -- ot_s81hd_spr:
1 pins: PASS -- every input lands in a flop (i x / go / xv, per port 3 kept rv copies + row / bits / flt), every output leaves a flop; iw / ie x / go / xv are unused inputs (the chain ends' stream copies).  Reset lands in 2 registered stages at the face (kit reset_landing).
2 reach: PASS within the node (259.2 x 691.2: one register stage, its flops between the faces, <= ~346 um a side);
  the spine level-to-level gaps (~1.3 mm) get die relay stations (SPEC 4, dv_route72).
3 fanout: PASS -- hold enables from 3 kept rv copies a port (<= 18 loads), selects from 3 kept copies a compare level.
4 depth: PASS -- 2 registered compare levels (pair (iw, ie), then (pair, i)): one 32-bit key + 17-bit row compare a stage.
5 storage: PASS -- 1300 flops, no arrays.
6 floorplan: PASS -- std-cell only, slot 259.2 x 691.2 (SPEC 1: 216 x 648 a node); pin-bound (3 x 565 + 565 pins), faces
  <= 2.36/um; util well under 40% is the slot / pin price (fill_reason pin_bound).
7 clock: one region (the node belongs to its row-pair chain region, SPEC 6), one TritonCTS tree; spread <= 80 ps TT+FF
  by the gate; io_hold_margin 0.03.
8 schedule: static valid-only forward; fire = 4 edges after the last best (capture, select, pair, select, output), cleared by i.go.
Why hardened, not die-top glue: 26 + 26 identical nodes with 2,260 pins each sit in the spine lane between the tile
columns; one closed view replicated keeps the die top free of ~70k flat flops / ~120k pins of glue and gives the die
STA a fixed node timing model (SPEC 2 'one hardened element, then replicate').

census: pending (pre-gate native census run with the first gate).
