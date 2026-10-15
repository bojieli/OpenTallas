# Die-assigned native COLL leaf pins

Consume the exact `pins/*_io.tcl` files with `io_tcl` in the corresponding ref_tile spec. `pins/assignments.json` records the source header hashes, evaluated widths, measured outlines, every scalar pin coordinate, and capacity checks. M4 serves W/E; M5 serves N/S; every adjacent pin has at least two tracks and every coordinate is on the ASAP7 0.012+0.048n track lattice. No M6/M7 tile routing grant is introduced.

These leaf reservations use the existing v14 COLL quarter/core-band and SW VM-parent budgets. `child_slots.json` reserves eight state and eight adder leaves per COLL quarter above the closed port band; the four RGX and one TOPK receive leaves belong inside the real SW VM composition. The new child rectangles pass outline/overlap checks against one another and clear the existing closed port band. Full parent control/broadcast/reset/clock placement, native binding, GRT and timing remain required. The native SW VM composition uses NC9/WG3 and cannot alias old NC4/WG2 hard views.

The TOPK native hierarchy requires **39 explicit clock entries**: 32 tile, 4 ingress, selector, buffer and packer. Every child clock pin receives phi minus that child insertion. Leaf assignment does not establish parent or die qualification.
