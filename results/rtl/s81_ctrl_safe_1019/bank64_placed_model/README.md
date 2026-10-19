CTRL bank64 actual placement: diagnostic only

The exact22 native32x64 banks and FIFO de58d09a7 completed canonical ORFS placement/DPL in the existing531.25x250 candidate reservation. Original090615 gate/source and bank64 synthesized checkpoint were read-only; all new files belong to the separate placed_model directory. No CTS, native or gate was launched.

Detailed placement has zero violations. Actual ODB has34540 instances:22 macros/12178.970496um2;2953.63098um2 other area includes393.86412um2 tap/endcaps, leaving2559.76686um2 functional standard cells. Bare synthesis1132.71um2 understated the pin/hold/repair footprint. Exact TSV, scripts/config and full driver log are preserved.

Viewed actual_placement.png shows forced I/O mass at faces and remaining logic distributed around real banks. Earlier central16-row band was arithmetic only. It contains7.05672um2 actual total mass (0.31percent bandarea), NOT a measured40-60percent band. No fill exception asserted. A valid model must price actual face and memory-control regions.

Source reset fanout and protected-net CloneMove CTS failure remain unresolved. CDC sampled age/collision/phase, native per-root TT/FF, clock/PG/pin escape, stage reach and parent composition are separate obligations. Placement alone qualifies none of these or the unchanged old PHY reservation.

First read-only inspection used unsupported dbBox dx/dy and stopped before collecting. Corrected xMax-xMin/yMax-yMin inspection exit0 generated instances.tsv; neither changed design artifacts.

Actual stage geometry replay:13170 conservative source/register/memory boundary pairs,0 missing physical pins;57 bbox-Manhattan spans exceed405um. Five end at async-reset pins (worst495.946),52 other endpoints reach423.149, including response metadata capture and far request read controls. This is not an acceptable stage-reach result. The separate four-bank rearrangement is placement-only and source-identical; no source reset/CDC/CTS qualification follows.

Sequential roles are explicit actual DFF master/pin roles and actual SRAM rclk/wclk/data directions; source clocks clk/ckh excluded. All174 dead starts match exactly the paid raw SRAM read tails: perPC request bank5 bits20..63 and response bank4 bits21..63, checked in unused_tail_contract.json. These exact padding bits are not permission for unrelated unused outputs. Decompress driver_reach.tsv.gz before running stage_reach.py.
