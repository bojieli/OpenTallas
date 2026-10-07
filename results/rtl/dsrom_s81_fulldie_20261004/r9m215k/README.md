# S81 r9m215k = r9m215 + --vch-interleave + --link-fix (CLAUDE S81-RERUN, 2026-10-06)

`python3 tools/dsrom_s81_fulldie.py plan --gen r8 --rev r9 --elem-h 198.72 --cc-reach-um 215 --vch-interleave --pairs 2050 --link-fix --die layer`
(scan die; `floorplan.json` + glue RTL `dsfd_glue.sv`; DEF/SVG regenerate with the same command).

Link fix (default off, `--link-fix`): the board SerDes LEF (`ot_pdie_serdes`, real pdie_v2) has `clk` on the face
opposite tx/rx (the die-edge face at R0 / MY); the r9 die drove it from the tx chain's last station 267-632 um behind
that face, and the tx/rx chains ended at the macro centre, 650-960 um from the ends of the 1,122 um pin spans.
- the macro's clock source stands on its ck face: a forwarded-clock relay `dsfd_lkck_<fi><fo>` (8.64 x 8.64 um,
  `assign fo = fi`, a CTS-sized clock buffer) outside the ck pin (SerDes: the die-edge side of the link column, the
  macro moved to the core side of the column; UCIe: the edge corridor at its ck pin); the relay drives the macro ck
  and the rx chain's first station (one common clock point for the macro's launch and the rx capture);
- the tx chain ends with a station forced at the centre of the tx pin span (last hop 13-18 um), the rx chain starts
  with a station forced at the centre of the rx pin span.

Die lint (`tools/die_top_lint.py lint --die s81r8_layer --s81-opts "<options>"`, `lint_link_fix.json`):
link-macro face-away 6 endpoints (r9m215, 267-581 um behind) -> 0; relays 0; missing pins 0; legality 0 outside /
0 overlaps; generated pin clashes 0; field round trip unchanged at 152.  Cost: +1 station on each tx chain at most
(link chains only, not the field round trip).
