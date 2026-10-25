# S81 decision-17 regenerated plan

Codex completed the paused DEC12R generated outputs on the source branch
285f3a70859a5ce55240d66e95afab85275b8c28. Includes methodology alignment,
RTLA/RTLC conflict resolution, split ve/vn cores, VQ write-port fix, and
reserve-pair endpoint/PHY-zone changes. Generated S81 and head plans use
signal layers <=M7, 405-um reach and neighbour-wavefront reset.

Collected original gates: S81 G0/G0C PASS 0 errors (176/176 types, 399 parts);
head G0/G0C PASS 0 errors (16/16 types, 326 parts). The full die_plan pytest
run completed at 100% with one skip; original log is retained.

This is plan adoption, not physical sign-off. The over-core feedthrough audit
is FAIL for 22 types (previous main: 32). These remain held from partition
routing pending channel corrections and a CLEAN fresh prototype. Audit
results and all individual failures are retained in overcore_ft.json.

Per-lane added-cycle pricing versus main and the prior DEC12 draft is in
lane_cycles.json. Model/token owners must use the regenerated latency table.
LEAFPLAN2 is the next pending fold into the same batch.

## LEAFPLAN2 plus frame corridor follow-up

LEAFPLAN2 is now folded into the decision-17 plan, with the zero-cycle frame
FT corridor fix. Final G0C PASS 176/176, zero errors, 1259 warnings. Six new
lane-side tests PASS. The 72 leaf types remaining after reserve-pair type
deduplication reduce internal station bits 770,228 -> 593,917 and summed
internal station cycles 1,106 -> 858. All lane-side violation counts are zero.
112 die-lane depths change versus 5c6fd2a2a: net -173 cycles, minimum -14,
maximum +1; leaf_lane_delta.json provides every lane.

The 21 frame slots retain station counts (zero added cycles), all four
frame over-core failures are removed, and maximum actual paired-bit hop is
370.44 um. The combined plan remains FAIL on 19 leaf types under the over-core
audit, including some SRAM crossings worsened by the new arrangement. These
19 types remain held from partition routing until channel correction and a
fresh CLEAN prototype. This conditional plan adoption gives no G3/G4 credit.
Original base audit and failed packaging/check logs remain retained.
