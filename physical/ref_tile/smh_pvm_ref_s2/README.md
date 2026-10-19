# PVM SAFE2 structural geometry successor

The earlier SAFE1 kit used a 10-pin/um macro face and two logic bands. Those waivers were rejected by the coordinator. This isolated successor keeps SAFE1 merge/fold RTL byte-equivalent after module/memory renaming. Old masters, macros, views and failure evidence remain immutable.

The new p192 SRAM has the same calibrated64x512core and repair/behavioral model, with793pins/edge on153.9um (5.153pins/um). Dedicated generator tools/mem_compiler/build_pvm_safe_pins_1019.py expands the outline and recalculates area, density, leakage and timing. It adds full-height M4 pin-access RC and calibrated driver load to max timing, adds lead capacitance/energy and retains conservative minimum hold. The datasheet states its analytical claim boundary.

The302.4um square outline reserves one full-width north logic band at y216..302.4. Lower placement rows are removed before global placement; fixed tap/endcap infrastructure may remain. All data/clock/reset pins use the full northface; clock enters at149..151um beside the register mass. Macro origin43.2,43.2 is on the43.2lattice. The W/E routing channels are43.2/87.912um. The11,400um2 synthesis anchor plus26,361.2232um2 macro gives41.294% totalfill and43.6% band logicfill before new synthesis.

No new data edge is added. Existing SAFE1 Qwen fold publication node0 at F0+23 (one edge later than old), node1 unchanged and DS zero, remains priced in REPRICE3. Tile area increases0.046656mm2, or0.746496mm2 at16copies. Die lead must re-slot the expanded tile.

See design_review.json for all eight SAFE checklist items, actual per-corner macro timing and outstanding gate qualification. Clock spread, fanout/depth and actual synthesis area are pending gate results. Critical tile: no REVIEW.json or submit without coordinator review of the gate PNGs and checklist.

Fleet Verilator5.050 evidence now committed: exact240/tight192PASS; mut1FAIL240,mut4FAIL32,mut5FAIL121 with RTLstop, pubearlyFAIL33. Full-cycle SS read-path sizing: macro515.506 + calibrated DFFsetup16.207 + uncertainty60 leaves241.620ps for local interconnect. A380um M4 external lead including SSdriver gives the conservative bound in design_review.json (no half-cycle). Actual gate placement must verify reach and timing; this is a sizing bound, not closure.
