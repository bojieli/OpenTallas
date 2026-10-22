# sram_escape128x64_1019 (QW-SRAM3 10-19): CTL128x64 dual-clock family escape coupon

Same method as CLOSED sram_escape64_1019 (route DRC0, spread 17.2/16.1): ot_sram_1r1w2c_128x64_m1 (33.72 x 27.576,
W/E 105 pins = 3.81/um, already <=6/um so no pitch successor is needed), 108 sq, macro at (43.2, 43.2), generated
pin regs + reset landing, one synchronous clock on rclk/wclk (no CDC/collision claim; that stays client-owned).
Checklist: 1 pin regs+reset landing ON; 2 <=108 um wires; 3 fanout <=64 data/1 per bit; 4 one stage; 5 SRAM;
6 43.2 lattice, 32 um edge clearance, 3.81/um; 7 single TritonCTS root, spread measured; 8 coupon only.
