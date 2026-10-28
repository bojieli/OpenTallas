# DIE-QC-14 (2026-10-28 10:55-11:15 PDT): QC die owner, A0 parent local trunk on the a0k5 romleaf pin

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc14-1028/a0trunk (parent nk = QC-A0-KITS-3 placed db + DIE-QC-12 57 glue cluster trees).
Numbers are OWN / UNCHECKED-independent unless marked CHECKED. All arrivals are placement RC (estimate_parasitics -placement, setRC_rcx), NLDM RVT, propagated: the same method as DIE-QC-12 nkg110, NOT routed.

## Task 1 (re-plan CA/STA with clock_cell=inv2 declared): BLOCKED
Main has FLOW-ONEMODEL-1 (RM157 48e2076a2), but not CLK-INV-CAL-1 (RM165 HELD for the onemodel rework + fail-closed clock_cell) and not region_stub (QC-13 9c4415e27c approved, not merged). Template stays results/die_qc13_1028 ca/runCA11i.sh.

## Task 2: A0 parent trunk (nk)
Inputs:
- Child views. Romleaf clk pin moved to the a0k5 entry (21.612,15.12) M5 (QC-A0-KITS-5 plan fix, 1662a1bff39e). The parent db was rebuilt as cl_nkr.odb through a DEF round trip with the patched abstract ot_qwen_tile_romleaf_a0k5pin.lef (relef.tcl, wdef.tcl).
  - Pin check (CHECKED): MY col[0] pins sit at x 173.652, R0 col[1] pins at x 284.268, y = macro y0 + 15.12. Both face the centre channel.
  - Rawleaf and node a0k3 kits place clk at the macro centre, (57.66,70.2) and (23.772,216). That is the fixture position, so those pins were left unchanged (CHECKED io.tcl).
- Child budget: every child pin is balanced to the 12.3 contract 250 TT / 202.5 FF. The fixture ETM numbers (158-222) are no longer used.
  - Real views for reference: romleaf a0k5 routed all-sink mean 284.2 / 224.8 (signoff.json, NOT SIGNED on DRV slew); node a0k3 274.8 / 223.1 (NOT SIGNED).
Planner trunk2.py (lane-local):
- Same greedy DME of CKINVDCx16 and the same ICG site as trunk.py. Parity is even to every flop by construction: 0 odd sinks.
- No padding-stage stacks. Each merge is balanced by WIRE LENGTH: the faster leg is lengthened along a bridge polyline whose corners are repeater sites, and stages are added only in parity pairs, spread along the longer wire.
- Leg delays are computed on the legalised geometry (refine step).
- corr mode is a measured re-balance on the same topology. Bottom-up, it shortens an elongated slow leg or lengthens the fast leg by the measured mid-range difference of the two subtrees. The model is used only for the delta. This is a plan iteration, not an ECO.

| build | INV | wire mm | elongation um / legs | TT min-max (spread) | FF min-max (spread) | regs mean TT/FF |
|---|---|---|---|---|---|---|
| q0 plan | 197 | 10.99 | 1164 / 30 | 693.5-782.9 (89.4) | 594.8-691.5 (96.7) | 743.5 / 646.6 |
| q1 corr | 205 | 11.28 | 1457 / 41 | 702.0-782.0 (80.0) | 606.4-692.0 (85.6) | 732.6 / 635.2 |
| q2 corr | 205 | 11.33 | 1510 / 39 | 726.1-768.2 (42.1) | 625.7-674.3 (48.6) | 749.8 / 651.0 |
| q3 corr | 205 | 11.34 | 1511 / 41 | 723.4-755.6 (32.2) | 621.6-668.4 (46.8) | 739.7 / 641.4 |
| **q4 corr** | 205 | 11.38 | 1553 / 41 | **735.3-763.3 (28.0)** | **628.6-670.7 (42.2)** | 748.2 / 649.6 |

- q4 meets the contract spread of <=60 ps at TT and FF (placement RC). DIE-QC-12 nkg110 was 90 / 84.
  - All 15,013 glue registers plus the 19 child pins (pin arrival + 250/202.5) are included. Child totals: TT 739.4-747.6, FF 628.6-650.6.
  - Max legalisation displacement 3.7 um. 0 repeaters inside macros (checked on the plan).
  - 5 leg segments are shorter than 8 um. These are bridge corners pulled together by legalisation, not stacks.
- INSERTION is now ~750 TT / ~650 FF, not ~535 / 457. This is structural: the glue registers must arrive with the child flops, and the child flops sit 250 / 202.5 below their pins by contract, where the fixture ETMs had 158-222.
  - The die region tree therefore taps the A0 centre early by the measured trunk insertion. c_* planning should use the q4 regs mean 748 TT / 650 FF, not 535 / 457.
- Sensitivity to the real views (UNCHECKED): if children land at a0k5/node routed values (+25..+34 TT, +20..+22 FF), the child totals rise to ~765-782 TT. The spread is then ~47 TT / ~42 FF, still <=60. Children are held to 250 +-40 by their own sign-off.
- Render a0trunk_q4.png VIEWED:
  - romleaf legs are short stubs from the centre channel to the inner-edge pins;
  - elongated legs (red) run in the channels and along the E column;
  - rawleaf/node legs cross their own macros to the centre pins (real a0k3 pin positions, upper-layer wire, the same PASS-COND as nkg110);
  - no repeater sits on a macro.
- ICG: the site is at the tile root, and the trial build ties ENA=1/SE=0. The enable RTL step (existing signal, 1-cycle lead) plus the gated-clock bench and LEC are NOT done. They are required before adoption.

## Not done
- nl variant, the c_* centre-entry die delta (now unblocked: A0 tap early = q4 748 / 650), routed (GRT/SPEF) recheck of q4, ICG enable RTL + bench + LEC.
- FF hold region balance (task 3) and the FF duty spice check (task 4).
