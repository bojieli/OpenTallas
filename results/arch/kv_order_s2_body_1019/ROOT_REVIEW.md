# KV ORDER S2 body and native face proposal

Retain the prospective 302.4x267.84 um outline, six 51.408x39.96 um SRAM bodies at the existing 43.2-lattice origins, and implement a full-width north body at y190.08..265.68. Retain 5.4 um strips inside the west/east/south core faces for actual face registers. Move ck_core from the actual native NE corner (x301.260) to a free M5 track at x151.116 beside the register body. Preserve every data pin, signal interface and data edge. Candidate spec is `physical/ref_tile/qkd_hr_core_order_s2_body/spec.json`; it is intentionally not a generated runnable kit or an approved floorplan. Existing S2/S1/guard/prompt kits and jobs were not changed.

## Measured evidence

The immutable source is436d6e726 (paired-copy RTL2f4bdadb6), archived by e906f4859, mapped netlist SHA e8bc20ae54460ce71ee1cda66cb7dd3dddf2058a3a1ddd65f88ef542c3f1c13f. Actual R2 census has18229FF, max32/zero-over32 mapped register loads, six SRAMs and12199.21722um2 standard cells. Reset remains two edges, root12/first24/final30. Existing same-source enabled/default600k and independent30k exact proofs and six causal mutants remain the functional evidence; this lane adds no timing or token claim.

Fleet OpenDB replay on ep7 unit oth-ubuntu-3114184-1792429116 completed exit0 with OpenROAD26Q3-1510-g6cb3f2b704. Input `2_floorplan.odb` SHA84728cae4c655c69a2fdd7d2a870539042272184ed2151caa66d9f81acb97f15 is the exact old R2 synthesis/floorplan/PDN output. Its clone swaps six masters to the distinct calibrated p192_rc family, proving identical signal/clock/PG rectangles, orientation, location and every connected net. Native2282BTerms include2280signal/clock pins and twoPG; all data pin geometry is preserved. Clock relocation is explicit in body_plan.json.gz (gzip archive of the exact JSON). Actual E1036/267.84=3.868pins/um, N1165/302.4=3.853, S74/302.4=.245 and W5/267.84=.019. Earlier report message counts1086/1171/80/55 included flow bookkeeping; these are actual native BTerm counts.

Real row pruning in the cloned DB retains1692row segments out of1960: north280rows/22534.848um2sites, W/E696each/1014.768um2each, south20/1551.312um2. Total26115.696um2 makes raw mapped area/site density46.712%; even placing all old mapped area in the north body gives54.135%. These are actual site capacities, NOT placed occupancy. No cell assignment/face fence, retap, new PDN or placement was performed. The clone still contains old physical cells/rails outside the newly retained rows and is diagnostic only. Output clone SHA bcde938900a2703d806f7cd4997369438b010a292aeb3e50e3e396ef3d18528f is preserved remotely at ep7:/srv/opentallas-scratch/claude/codex-kv-order-s2-body-1019/body_plan.odb.

Viewed body_plan.png: three map SRAMs on the lower row, three dispatch SRAMs above, one full-width north row body, side/bottom face strips, unchanged full-face data pins and a centred proposed clock. Hatch represents reserved rows, never placed standard cells. Generated SVG is also attached. Plotting input-staging exit2 is preserved in execution.json; it did not run RTL or alter the successful DB evidence.

## Calibrated SRAM binding

Pin bb61ae67c. Geometry/behavior/BB are byte-identical to old p192 after exact master rename (macro_binding.json). All new BB, behavioral, LEF, TT/FF/SS Lib files are coherent under ot_sram_1r1w_32x128_m1_p192_rc. Old p192 files remain immutable. Source uses an opt-in OT_HOST_BOOT_FIFO_P192_RC kit define; only master name changes. Contact-lead calibration adds TT4.366807829/FF3.231477211ps CQ/setup plus actual capacitance, period, slew and energy deltas. These are analytical deltas, not measured native STA. Six raw macro areas total12325.58208um2; no change in hard area or external data edges.

Each macro still exposes199W/198E contacts, density4.980/4.955 perum. Horizontal body gaps34.992um retain24.192 after both5.4halos; vertical46.44 retains35.64; top SRAM to north body20.52 leaves15.12 after halo. Native R0 contacts are on M4 tracks. The 24x24nm M4 contacts have576nm2 area below2000nm2 minimum, so actual external patch/via/PG/DRC escape remains REQUIRED. The HBM compiler owner confirmed no escape qualification exists; do not waive it or relabel calibration as routed proof.

## SAFE checklist and next owner

1. Pins: source pin registers and exactly two reset landing stages retained; existing exact proofs PASS. Actual face-register ownership/placement still OPEN.
2. Reach: OPEN. 403.960um Euclidean outline diagonal is NOT a bound on Manhattan/routed wires. Measure every real registered path; associate SRAM caches/selects with their native bank faces. No data masks.
3. Fanout: old exact mapped source PASS18229FF/max32. New coherent source synthesis must confirm unchanged structural census and actual macro clock loads; no old-helper overlay.
4. Depth: same-edge caches/onehot control retained. Calibrated SRAM arcs increase slightly; actual native TT setup and FF hold OPEN.
5. Storage: six real32x128 1R1W macros retain logical FIFO depth8, two cached words and local RAW forwarding. No new flop delay array or data cycle.
6. Floorplan: actual lattice/channels/native densities and site capacities proven as above. Cell placement, tap/PG regeneration, actual body/face occupancy and external pin escape remain OPEN. No ROOT low-fill approval is filled in.
7. Clock: actual native clock moves near body centre; expected18235FF+SRAM sinks. No CTS, native insertion/slew, TT/FF spread or parent-neighbour compensation exists. Do not infer clock qualification from root position.
8. Schedule/model: control-only MAC0, two independent 3x128-bit stores give at most96readB and96writeB/edge total, II1, zero extra external edges. Static source behavior/quiet unchanged. New STATUS quiet/drain work belongs to retirement owner.

Next finite lane: ROOT review of this diagnostic geometry and canonical balanced-reset tools a9a97ee00/54ceeb3f0/63d26d83c; ensure daemon actually carries them. Implement true body/face fences, retap and regenerate PDN from the current coherent source, then floorplan/native structural preflight and measured placement occupancy/reach/access. ROOT must approve geometry/tooling and all structural/native preflight before CTS. Parent GEN slot regrant/repack remains unmeasured; no fit, REVIEW, submit or adoption claim. No job remains live in this lane.
