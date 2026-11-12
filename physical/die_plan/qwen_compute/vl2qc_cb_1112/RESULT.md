# VL2QC-CB (sub-lane of VISLAYOUT2-QC), 2026-11-12: round-1 held cb rows + sl_su_l1 on QC s25 (e4820bd9d97c)

Tools: s25 tool tree (src_qc_s25_4e2764d237 copy), route_supply --grt-halving edge_outline, G0 check.py.

## Round-1 delta_cb_qc4 re-applied to s25 (apply_cb.py -> delta_cb_s25_r1.json, 29 tile edits, 15 types)
route_supply p99 is UNCHANGED on 13/15 types (cbf_q00 x2 1.339, cbf_q01 1.127, cbf_q01_s2 2.06, cbf_q11 1.741,
cbn_q00 1.656/1.36/1.656, cbn_q11 x2 1.737, cbx_q10 0.969/0.976); only cbn_q01 x3 1.084 -> 1.053.
Every worst region is a landing RING (H M2 at a face strip or V M3 beside a ring band), not the core arrangement.
G0: errors 265 -> 265, warnings 305 -> 348: +30 hard_cores [G0C] "pin ck M5 off the plan track (offset 0.024)" on
the MY tiles (the s22/s25 NK-quad orients keep the ck pin on track; the round-1 MY orients do not) + core_faces WARNs.
VERDICT: round-1 orient form SUPERSEDED by the s22 NK-quad orients in s25 (equal or better p99, ck pins on track).
Not built (an off-track ck pin is a real pin-access risk, and 13/15 show no gain).

## cbf_q01_s2 REDESIGN (round-1 "S1 ft corridor")
On s25 the worst is the S-face landing ring, not the ft corridor: ring_H 2.06 at (232,5) under the
serdes_tx_tx_flit_i band, a 10.8-um strip (y 28.08-38.88, x 108-573, 597 b); street_H/V only 0.23/0.28.
Form tried (make_cbs2.py): all 4 NK tiles N +69.12 um (S street 77.76 -> 146.88), tile-owned xy moved with tiles.
route_supply: worst 2.06 -> 2.061 (unchanged), core_H 0.81 -> 0.48, ring_V 1.44 -> 1.24, street_V 0.28 -> 0.19.
G0/schema FAIL: 2 seam-port geometry errors (c_W5_bf_01__b00__0, c_W5_bf_11__a00__1): the NK tile data pins define
the seam windows, so a tile y-shift is not type-local. VERDICT: no legal positions form; residual = ring strip
-> LAND-RING-2 strip density (the 10.8-um serdes_tx_tx_flit_i strip is exactly their class). Not built.

## cbf_q00 x2 (round-1 ARCH: one 514-b H run over the NK cores on M6)
s25: G0 has no cbf_q00 error; route_supply core_H 0.688/0.657 (< 1; the ARCH evidence was core_H 1.267 on the
old plan/tools); worst = N-face na_i00 ring H 1.339 (LAND-RING-2 class). R4 pin cycles do not remove an
over-core H run, and on s25 there is none above 1.0. Private full-flow build of the s25 stock form started
(cbf_q00__cl1b5a6458, bind out_s25fix, place epyc2/epyc7) as the measured answer.

## sl_su_l1 (VIS-TRIAGE F: NE-corner ft_cws0 + windows, old plan)
s25: sle_su_l1__clc6d66f5b worst ring_H 1.359 (S rsn band), all other regions < 1 (street_V 0.59, core_V 0.83):
the NE-corner hot spot is gone. slw_su_l1__clcc9d0155 worst ring_V 1.697 + core_V 1.15 in the 190-um E column
(x 432-622: cws0 516 b at x 475, rsf 514 b at x 570, the x_su_c/_p1 767/765-b E landing cores).
Trial: E landing cores flush to the E face (+13/+15 um): 1.697 -> 1.667, core_V 1.15 -> 1.19 (worse).
VERDICT: no positions form (the four 414.72-um lane cores are frozen in a 622-um slot and the cws0 windows are die
seam positions at x 436-525); residual = ring class (LAND-RING-2) + E-column V supply (die window plan).
