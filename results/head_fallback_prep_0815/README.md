# HEAD fallback plan preparation, 2026-10-27

`compose/landed_portable.json` is a plan-only landed fallback on the approved R17
HEAD infrastructure geometry, with current real providers, source closure, BQ=2,
physical clock-tap names, and the qualified Native32 source profile. It is a
prepared alternative for the owner 10-29 trigger; no fallback build was launched.

The current composition has 326 partition regions, 427 crossed ports carrying
211,813 bits, and 1,061,200 live ring flops. All 16 types remain shared: zero type
splits, zero storage-band placement failures, and zero landing-contract errors.
The monitor has 1,281 edges and a 327-cycle boot budget. The head pass pays 171
extra cycles. The 0.987 mm2 ring-area estimate is logical and unmapped.

The original compose outputs are preserved. `landed_portable.json` additionally
rebases plan-relative pin assets and records the type source profiles; these
changes add no data cycles or geometry changes. The underlying G0 of the first
source candidate failed only because its copied plan-relative pin paths pointed
at an absent `results/.../cores` folder; the portable export fixes those paths.

The R18 physical owner is correcting hard-core outlines and producing a real
clock build on HEAD5 PG. Apply this same fallback recipe to that final plan before
adoption. Historical sl300 overflow/timing results do not qualify the new plan.
Its tree sites must be reserved and rechecked against the final hard-core shapes.

Hardware readiness remains open: native binder ring emission needs the actual
generated HEAD top and its reset nodes, and the observer is deliberately OPEN.
The current controller has real `start_i` and `lep_fault_i` inputs that can serve
the ready/fault gates, but that exact binding must pass `clock_landings` on the
native body. The eight new physical FT ports on each A/B hard core also need the
physical parent's adapter; the existing logical `.clk` provider alone does not
prove that physical interface.
