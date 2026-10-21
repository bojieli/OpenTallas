# s81hd_spr_m2 (S81-HEAD HD-TILE 10-21)

S81-HEAD HD-TILE 10-21 MAIN: new spine node ot_s81hd_spr (SPEC v1 section 2, 26 a die), std-cell only, 216.0 x 648.0.

SAFE checklist (owner 10-19 / safe_1021, 8 points) -- ot_s81hd_spr:
1 pins: PASS -- every input lands in a flop (i x / go / xv, per port 3 kept rv copies + row / bits / flt), every output leaves a flop; iw / ie x / go / xv are unused inputs (the chain ends' stream copies).  Reset lands in 2 registered stages at the face (kit reset_landing).
2 reach: PASS within the node (216.0 x 648.0: one register stage, its flops between the faces, <= ~324 um a side);
  the spine level-to-level gaps (~1.3 mm) get die relay stations (SPEC 4, dv_route72).
3 fanout: PASS -- hold enables from 5 kept rv copies a port (<= 22 load pins), selects 11 / 7 kept copies (<= 8 bits each), keys from ot_s81hd_key (kept sign / -0 copies a byte).  Round 1 (s81hd_spr_m route EARLY_FAIL_SETUP reg -> out -467 ps: the N-face stream flop drove the S-face pin in one cycle; gate census max 88): 2-stage stream forward, key unit, copies.
4 depth: PASS -- keys 2 registered stages, then 2 registered compare levels (pair (iw, ie), then (pair, i)) on registered keys.
5 storage: PASS -- 2600 flops, no arrays.
6 floorplan: PASS -- std-cell only, slot 216.0 x 648.0 (SPEC 1: 216 x 648 a node); pin-bound (3 x 565 + 565 pins), faces
  <= 2.88/um; util well under 40% is the slot / pin price (fill_reason pin_bound).
7 clock: one region (the node belongs to its row-pair chain region, SPEC 6), one TritonCTS tree; spread <= 80 ps TT+FF
  by the gate; io_hold_margin 0.03.
8 schedule: static valid-only forward; fire = 6 edges after the last best (2 key stages, select, pair, select, output), cleared by i.go; the stream on the return spine is 2 cycles a node.
Why hardened, not die-top glue: 26 + 26 identical nodes with 2,260 pins each sit in the spine lane between the tile
columns; one closed view replicated keeps the die top free of ~70k flat flops / ~120k pins of glue and gives the die
STA a fixed node timing model (SPEC 2 'one hardened element, then replicate').

census: pending (pre-gate native census run with the first gate).

CODEX takeover reset successor: original mapped census s81hd_spr_m2 (20261021-092156) failed solely rst_n__ot_rl1 QN=33 dynamic loads. Four equal-depth landing copies and max_loads24 reserve relay overhead; data RTL, schedule and reset release stages stay unchanged. PRE-GATE census required before CTS. Original failure retained remotely. This is a pre-floorplan refusal, no failed route.
