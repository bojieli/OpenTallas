# smh_xs_p192d_bay: gate review packet (HBM-SMATT7 10-20)

The checklist lives here because gate_layout/ is outside the kit source binding. A new kit file would unbind the committed gate.
Gate: `--cts`, commit 5ad27c356, ot-epyc9, WARN with 0 FAIL and 6 WARN (gate_result.json). The PNGs were inspected: floorplan.png and density.png.

Geometry: the outline is 475.2x388.8 um (1.22:1). All 11 SRAMs are R0 on 43.2 um origins: 7 ring 32x128 at an 86.4 um row pitch, plus a 2x2 x-store of 128x256.
Std-cell rows run across the full width, with no islands. Density stays below about 0.6 everywhere, and the hottest spot is the x-store W/S channel.
The clock enters at the N face centre, beside the register mass. Pins sit on the full N, S and W faces (81-86% span); E has 19 pins.

SAFE-DESIGN checklist:
1. Pins: PASS. The RTL in/out registers are retained. rst_a lands in 2 posedge stages (OT_SMH_XSRST).
2. Reach: FIXED. The two EXCLUSIVE bays (strap 519 / control 19 flops) put all 61679 source/capture pairs at <=399.9 um in the e3bdacfca model. Before the bays, gate D measured 652 um. Per-net placed reach is measured on the route.
3. Fanout: PASS. The mapped native census gives max 32 dynamic loads, resets included.
4. Depth: PASS. 288.4 ps mapped. GRT-stage TT setup WNS is +28 ps (reg->macro) and hold WNS is +37 ps.
5. Storage: PASS. The ring has 7 SRAMs and the x-store 4; there are no runtime-indexed flop arrays.
6. Floorplan: PASS with a pin-bound fill waiver. The lattice holds, there is a full-width band, aspect is 1.22, and SRAM faces carry <=5.1 pins/um. Fill is 30%: pins set the width, not area.
7. Clock: PASS. One root has 26146 sinks (guidance only). TT/FF insertion is 598.5/472.1 ps and pin-flop spread is 65.3/53.1 ps (<=80). io_hold_margin is 0.03.
8. Schedule: PASS. There is no RTL, cycle or pin change against p192d_lattice.

Trial GRT overflow is 0, and the worst layer is M2 at 26.7%. The sources WARN lists 2 behavioural SRAM .v models that the xs_ring benches read. Both files are in git, outside the old sparse checkout, so they do not affect the view (synthesis uses the _bb.v files).
