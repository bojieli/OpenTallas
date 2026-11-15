# ROM-VIAMAP-ASSY handoff (11-15)
Branch claude/rom-viamap-assy @8dfe82f36fb (origin), clone /srv/opentallas-scratch2/claude/rom-viamap-assy.
Files: tools/mem_compiler/rom_viamap_gds.py, tests/test_rom_viamap_gds.py (12 pass, KLayout pip reader included).
Gap: rom_gen.py writes LEF/Liberty/model + <INSTANCE>.viamap.hex only; no layout. Only content-dependent mask is the programming VIA1 (GDS 21/0, 18 nm square; tools/asap7_bitcell_density.py build_rom).
Tool: overlay (viamap -> GDS of V1 only), merge (die GDS stream + placed DEF + personalisation manifest: one overlay structure per UNIQUE image, one SREF per placed instance, N/S/FN/FS/W/E), verify (reads vias back from the merged GDS through the SREFs and compares to each hex), readback. Pure Python streaming GDSII, no KLayout needed; manifest SHA-256 of each hex is checked; unmapped placed instance = error.
Proof: 64x16 mux8 ROM, 2 instances (FS and N) sharing one image: 1 unique overlay, verify PASS, KLayout flat V1 count 1020 = 2x510 hex bits, positions equal.
Sibling types differing only in ROM image: same placed layout, run merge with each type manifest; base layout identical, overlay differs.
CLAIM BOUNDARY / OPEN:
1. No base macro GDS exists (array/decoder/sense). The overlay is the content mask only, placed on the compiler cell grid with array origin assumed (decoder_width, 0); via x/y offset inside a cell is the cell centre, not the drawn drain. When a base GDS generator exists, set --array-origin-um and via offset from it; the overlay must then be layer-exact in that macro frame (and V1 over base V1 pads must be DRC-checked).
2. Orientation FW/FE rejected in DEF-by-design only for FW/FE (N W S E FN FS accepted).
3. Run at die stream-out after final DEF: rom_viamap_gds.py merge ... then verify; wire into the die kit when a base ROM GDS exists.
4. tests/test_mem_compiler.py::test_committed_library_matches_generator fails on main for ot_rom_1024x72_m8_bb.v (not touched by this branch).
