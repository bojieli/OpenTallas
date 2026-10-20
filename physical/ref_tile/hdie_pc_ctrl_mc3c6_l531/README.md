# hdie_pc_ctrl_mc3c6_l531 (HBM-MC3F, 10-20) -- LITERAL 43.2-lattice MC3c v6 kit (NOT GATED: approval owed)

Same RTL/params/benches/pin set as hdie_pc_ctrl_mc3c6_t242 (source 272b37645; mapped native32 census PASS max 32,
netlist sha b3a34e22... at the t242/s350 gates; the gate re-runs it). Generator: tools/hbm_layer_vehicle/mc3f_lattice_kit.py l531.
Geometry: 531.36 x 354.24 (aspect 1.50; 6 cols x 4 rows, 24 slots, slot (5,2) empty; band y 175.23-198.18 between rows 1/2); data groups over cols 0,1,4,5; worst planned macro<->face hop ~372 um (queue (216,216) -> S face col 0).
All 23 p192 SRAMs R0 with origins on 43.2 multiples (86.4 pitch: channels 52.70 E-W / 58.86 N-S), offtrack 0.
Why 86.4: macro 33.696 x 27.54 with signal pins on BOTH W and E faces -> 43.2 pitch leaves 9.50 / 15.66 um (<20) and
neither abutted_stack (needs 27.552 pitch) nor abutted_row (needs bare faces) is on the literal lattice. 86.4^2 per
macro is the floor -> fill 14.4 % (macros 21,344 + std 5,872 um2 / 188.2k) -> only legal as
fill_reason.lattice_channel_bound. ref_tile gen: every geometry check PASS, the ONLY finding is
"missing coordinator approval" (approved_by must be ROOT / codex coordinator), so pre_route_gate skips the remote run.
Before a gate can pass even after approval: (1) the flow has no band-confinement mechanism (placement blockages outside
the band except pin strips); (2) placed_exceptions must list every pin-register / input-output buffer / clock instance
outside the band by exact name (from a placed dump). Neither exists today.

## Safe-design checklist
1 Pins PASS (every port a flop in RTL, 2-stage reset landing) | 2 Reach: model only (see geometry) | 3 Fanout PASS (census
max 32) | 4 Depth PASS at source | 5 Storage PASS (23 SRAM) | 6 Floorplan: lattice PASS, channels PASS, aspect PASS,
one full-width band (48.5 % at synth area), fill 14 % = exception | 7 Clock W-face at band centre, spread owed |
8 Schedule static, unchanged.
