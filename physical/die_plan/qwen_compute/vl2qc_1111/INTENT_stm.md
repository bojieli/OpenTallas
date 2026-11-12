# INTENT sle_stm / slw_stm (VISLAYOUT2-QC, 2026-11-11), round 2 of the round-1 ADOPT

Round 1: VIS-TRIAGE-QC INTENT_stm.md (epyc4 /srv/opentallas-scratch3/claude/vis-triage-qc/cs/intent/). The dataflow and the timing-critical pair are unchanged from there.
- Path: treq → loader → 4 ROMs (4096x266) → rd_out 4x266 b → VM join → tw (1051 b) out at the N window, x 4-366.
- Critical: ROM clk → rd_out → join → tw reg.
  - At s15/s22 positions: TT -560..-1046.
  - About 450 ps of that is wire from the mid-type ROMs (y 595-690) to the N-window endpoint.
  - The rest is logic depth (ROM 595 ps + 5 levels): Form A, owned by DIE-QC-97.

## Why round 1 was reverted
The 12:00 compose (plan_qc99_1111) reverted it because the ROM origins were off the 8.64 die lattice (G0C), and one block position collided with type-specific straps.

## Round-2 form (delta_stm_d.json, on plan_vl2_qc_d)
- The 4 ROMs form a 2x2 block in the N band, all orient MX. MX keeps the M4 pins on track and puts them at the ROM top, facing N.
- m0/m2 share the left column and m1/m3 the right (address pairs).
- Each origin is on the 8.64 lattice (asserted).
- Each type's block is legalised by stm_free.py against that type's hard points: count straps, ft regs and bit sites, internal stations, clock and edge taps, landing pins. There is no single position valid for all 11 types.

| types | x_left | x_right | y_top | y_bottom |
|---|---|---|---|---|
| sle_stm_v1 x2 | 17.28 | 233.28 | 1218.24 | 1140.48 |
| slw_stm_v1__cl05fc43f7 x2 | 17.28 | 233.28 | 1235.52 | 1157.76 |
| the other 7 | 34.56 | 216.0 | 1244.16 | 1166.4 |

- 5 count-strap sites sit exactly on the 4.32 halo edge, not inside a ROM.
- Collector, reset relays and start stages inside the ROM boxes are moved at kit time by landing_place._collector_window and _clear_of_hard_cores.
- The ROM-free S and middle of the type stays a straight macro-free channel for the stream glue and the ft pass-throughs (AMENDMENT 3).

## Scores (route_supply --grt-halving edge_outline)
| | p99 |
|---|---|
| s22 | 1.136-1.334 (mstreet H M2) |
| d | 0.617-0.842 (landing ring H) |

The G0 diff is in the CLEANSLATE2-QC row.

## Residual
Logic depth (Form A ROM output stage, DIE-QC-97) is not addressed by positions. Expect the setup residual to shrink by the wire share only.
