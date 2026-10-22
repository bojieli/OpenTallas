# s81hd_spo_m (S81-HEAD HD-TILE 10-21)

S81-HEAD HD-TILE 10-21 MAIN: new spine node ot_s81hd_spo (SPEC v1 section 2, 26 a die), std-cell only, 216.0 x 648.0.

SAFE checklist (owner 10-19 / safe_1021, 8 points) -- ot_s81hd_spo:
1 pins: PASS -- the three outputs are KEPT register copies that capture the input pins directly (every input bit -> 3 flops, every output its own flop), no combinational in -> out.  Reset lands in 2 registered stages at the face (kit reset_landing).
2 reach: PASS within the node (216.0 x 648.0: one register stage, its flops between the faces, <= ~324 um a side);
  the spine level-to-level gaps (~1.3 mm) get die relay stations (SPEC 4, dv_route72).
3 fanout: PASS -- each input pin drives 3 flops; 9 reset loads (go / xv / rv a copy).
4 depth: PASS -- no logic (register copies).
5 storage: PASS -- 1695 flops, no arrays.
6 floorplan: PASS -- std-cell only, slot 216.0 x 648.0 (SPEC 1: 216 x 648 a node); pin-bound (3 x 565 + 565 pins), faces
  <= 2.88/um; util well under 40% is the slot / pin price (fill_reason pin_bound).
7 clock: one region (the node belongs to its row-pair chain region, SPEC 6), one TritonCTS tree; spread <= 80 ps TT+FF
  by the gate; io_hold_margin 0.03.
8 schedule: static valid-only forward; 1 cycle a spine level.
Why hardened, not die-top glue: 26 + 26 identical nodes with 2,260 pins each sit in the spine lane between the tile
columns; one closed view replicated keeps the die top free of ~70k flat flops / ~120k pins of glue and gives the die
STA a fixed node timing model (SPEC 2 'one hardened element, then replicate').

census: pending (pre-gate native census run with the first gate).
