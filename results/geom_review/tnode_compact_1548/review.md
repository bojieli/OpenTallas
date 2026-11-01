# Native Tnode compact envelope: PREP, no adoption

Personally LOOKED actual native_actual_placed.png and the new proposal.png.
Selected proposal125.28x95.04 (aspect1.318), macro4447.442304um2, actual standard
only1670.38686um2/free=22.39%, conservative cleaned-source1574.28/free=21.11%,
projected unoccupied outline area48.62% (NOT actual80-bin empty_area). Actual source stats6021.72 include macros; Yosys precleanup6083.38
is a different stage and is not substituted. No macro double count/filler/ties.

Two exact actual SRAMs keep R0 and move by multiples.192um, preserving old
M4/M6 signal track phase. Their four macro halos and clock island/halo are
clear: W/E signal access10.848/10.968um after4.32halo, Hcross10.872um. Existing
source body/stages/cycles are unchanged. Large W/E-only SRAM pin access plus
1341 public pins sets this compact outline; no invented cells fill free area.

All1341 public named pins retained. Explicit new face event: uaW271,uo+daE444,
ub+6pad_k+pad_b+rstN279,dn+dbS346. M4W/E,M5N/S with exact.048pitch/.024offset;
peak ten-um windows35/58/26/33, maxtrackuse.2741. The seven actual per-core pad
bits remain LIVE/free. Global60 producer port groups across30 Tnodes are not
60 physical rectangles; pad upstream producer reservation geometry remains UNSUPPLIED. All1341 child
BPin rectangles/layers/sides are provided, including every pad bit, with
actual native-kit size rules .192x.024 W/E, .024x.192 N/S and .048x.48 clock;
rotated data pins use the existing native N/S rule. candidate_io.tcl is an
explicit1341-row proposal, not a launched kit. Actual compact80-bin empty_area
is NOT RUN and cannot be inferred from source area.

New root M5(64.776,64.8) and PG(64.8,64.8) retain the old-.024 M5/PGoffset.
Generic child-orientation formulas are keyed explicitly as CHILD orientation,
not inherited parent-partition orientation. HBM cores confirmed all30 actual
childrenR0; child origin+21.6,+21.6 in parent-local coordinates preserves exact
globalclock+PG under both15R0/15MY parent parts. Cores owns the concrete30-row
proof and every data-endpoint delta; that full packet is still required.

Verdict PASS-COND as one finite geometry PREP for coordinator review. No parent
outline/pin/clock adoption, old50055 pinSHA reuse, source alias, new FIFO/stage,
CLK budget change, native view or physical/timing PASS. Parent event/G0/G0C,
actual generator track checks, native LEF/TTFF and normal PLACE/channel/clock/
signoff gates remain. No GEN/PNR/CTS/GRT/STA launched for this proposal.
