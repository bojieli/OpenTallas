# CTRL native32 pre-gate SAFE checklist

Candidate 531.25x324,16 replicated controllers; each2PC/4SRAM. No closure claim. Evidence results/rtl/s81_ctrl_rg2_s3_1019/pickup_0037 and native32_witness.

1. Pins PASS(source/native graph): every data input captured/output launched by native FF; reset_landing2. No constant top output pins. Postplacement native pin/PG audit owed.
2. Reach PASS(planning): all2468 native SRAM LEF data-pin/IO-flop-anchor payload legs max302.739um/0>405 after RESPONSE SRAM R180 (requestsR0). >100um allowance for inward columns/buffers. Native PHY19904seam bits max149.134um. Actual control/reset/data reach must be audited from placed netlist; no waiver.
3. Fanout PASS(mapped):2956FF/4realSRAM,max31 nonclock terminal loads through BUF/INV,0>32 including reset;4explicitSRAMdirections. Same ORFS canonicalize hook kept97 registers.
4. Depth PASS(planning): controller baseline375ps; changed G12 copies reduce perenable loads to24, added reset one leaf-stage. Full32PC production exactPASS and RD/KRDY/PACK FAIL witnesses. Gate remeasures candidate timing.
5. Storage PASS:4x16x340 dualclock native SRAM; FIFOdepth8 unchanged, no>2kb indexedflop arrays. +216FF are bounded control/reset copies, not new queue/delay storage.
6. Floorplan PASS(planning): same pin-bound slot,4macros on43.2lattice/legalSYMMETRY, widepitch contacts5.12/um, twoPCcolumns/clearfullwidthstandard region; N/S fullface buses, prior measuredfaceusage98%, no powerislands. Actual PNG/density review owed.
7. Clock FIXED(candidate): separateK8 regional core+PHY trees; original timing/CDC boundary constraints retained, io_hold_margin0.03. Bothdomains require measured TT/FF spread<=80; no assumedPASS.
8. Schedule PASS:0 added steady data edges/throughput change; reset release+1PCR/+1FIFO local edge, +216FF/tile/+3456die. Outline/SRAMcapacity unchanged. Native32 production/warmreset exactPASS; initialization increase recorded in model.

No REVIEW.json or submit before S81 lead's physical packet review. Latest main helpers source-synced in7be2c6292 with Gate-Rule:neutral.
