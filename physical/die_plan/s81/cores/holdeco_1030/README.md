# DIE-S81-36/HOLDECO: S81 FF hold ECO / re-sign (COORD 16:43 ruling, owner 12.19), 2026-10-30 17:24 PDT

## dsfd_rstg: SIGNED at flow-20261030-d-s81 (b2bbfe7186c)
- Source DB (plan of record, untouched): intel2 counted/s81/dsfd_rstg/kit_e1027 (S81-ECO-1 10-27 e1, FF vclk bound 202.5).
- ECO kit: intel2 /srv/opentallas-scratch2/claude/counted/s81/dsfd_rstg/kit_holdeco_1030
- Re-sign: intel2 /srv/opentallas-scratch2/claude/counted/s81/dsfd_rstg/resign_holdeco_d-s81 (PROVENANCE kind resign, copy here).
- Before: FF hold -7.36 ps (6 violators, ff_min_endpoints_pre.txt). After: TT setup +252.39, FF hold +10.1, DRC 0, antenna 0,
  PG pass, pair skew TT/FF 7.1/5.8, sdc_lint/face_guard PASS; LEC EQUIVALENT 198/198; pincmp MATCH 134/134 vs main core_pins.
- Method: eco.tcl = FF sign-off session.tcl of signoff.py at the tag, lines 1-339 (libs, read_db, read_spef, golden SDC,
  propagated clock, vclk rebind, -40/0 overlay), then holdeco_eco_tail.tcl: one HB1xp67 per FF min endpoint with
  measured slack < 10 ps (70 + 2 second pass), existing insts FIRM (0 moved), wires of the 141 touched nets stripped,
  all other signal nets dont_touch, GRT + DRT, ORFS asap7 FILL_CELLS, write_verilog without physical-only cells, RCX SPEF;
  gc.tcl applies the DB global_connect rules after fill. DEF compare (defcmp.py): 715/786 nets byte-identical.
- Caveats: ck[0] and clknet_0_ck[0] got DRT pin-access edits (re-timed in sign-off); 6_final.gds dropped (stale) and
  needs a stream-out before tape-out views; 5_2_route.json DRC/antenna keys = ECO run values (orig kept in kit holdeco/).

## dsfd_node_NNfu: no same DB -> retire / rebuild
See dsfd_node_NNfu/EVIDENCE.txt.
