# Selector quadrant s3s_b pre-gate safety record

Supersedes s3s_a whose native census passed31 but placement never ran because its region enum FENCE is not valid OpenDB. EXCLUSIVE is the actual dbRegion enum (tested on original floorplan DB). Source and static calendar edges are unchanged. Actual measured standard area is6324um2; predecessor27600 was macro-inclusive and is rejected as a cell-sizing input.

- Pins/reset PASS at source: every functional boundary captured/launched by source registers, two synchronization stages plus regional reset tree,15reset leaves. Same source as native31 and scheduled positive/mutant receipts. No tied functional port or reset waiver.
- Native PASS at source: original s3r and s3s_a exact mapped all-driver census max31/0violations including reset, kept pfx/pri leaf modules survive. Repeat in current gate before floorplan.
- Storage PASS source inventory:196608-bit records use3realSRAMs; remaining histogram counters/single words and pipeline fields retain constant-index accesses; no new delay line or indexed flop memory.
- Depth OPEN: current helper estimates737ps/21levels to selected[13], above600ps plan. Must restructure recurrence before adoption if actual physical paths fail; this gate determines actual paths without relaxing clock or constraints.
- Reach OPEN: source unchanged; actual placed nets <=405um required. Large outline alone proves nothing; no reach waiver.
- Lattice/floorplan FIXED:345.6square, R0 (LEF X Y symmetry), origins x86.4/y86.4,172.8,259.2;45.336um intermacro channels; real37.8um fullwidthEXCLUSIVE soft-cell region,6324/12900.384=49.02%beforeCTS. Pin density3.66/um for wide S buses. Actual placed-cell region/row coverage required.
- Clock FIXED at plan: centered S source clock beside lower mass; TT/FF pin-flopspread<=80ps required; insertion and sink counts alone are guidance. Parent landing/compensation remains required.30ps IOholdmargin retained.
- Schedule PASS source: static registered_s3, no credits/backpressure,+0cycles. Parent area must grow:119439.36um2/quadrant(+113.33%);600x450parentcannotfitfour; integration/repricing owed.

Native/reset/functional evidence does not establish physical closure. This packet is not a waiver of the depth/reach/clock/placed-band obligations.
