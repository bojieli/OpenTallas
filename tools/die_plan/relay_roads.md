# Explicit relay road placement

This opt-in helper preserves the existing cell/net topology. It controls named
relay flops and the **actual** BUF/INV/HB chains on reviewed source-pin to sink-pin
roads. It adds no stages, clones, clock changes, or timing exceptions.

`relay_roads.py --graph endpoint_net_graph.json --roads road_pin_paths.json
--out traces.json` resolves each branch using exact non-PG net and pin identities.
Direct zero-buffer nets must be present in the graph. Clock nets, ambiguous
multiple drivers, loops, missing endpoints and non-unary intermediate cells fail.

For a pre-GPL proposal, `allocate_buffer_sites` takes that graph and trace list,
the existing `core_plan_to_infra.read_sites()` row snapshot, explicit FF targets,
and an owner-reviewed finite branch corridor. It normalizes cut-row fragments by
physical y and shares occupancy across fragments. Macro body halos and actual
fixed taps must be included in the snapshot's fixed rectangles. It reuses SiteMap
body occupancy and site search; upper-metal clock-stack M5 avoidance is not a data
flop/buffer placement rule. Optional FF motion requires an explicit displacement
budget. Shared prefix buffers are reserved alongside their source FF before the
remaining FFs or exclusive branches consume the local fork bay. A shared cell
must fit all its branch corridors. No independent placements or averaging of
incompatible branches is permitted.

`price_buffer_paths` preserves actual buffer order, includes every input/output
pin and any backtracking, and follows projections onto the updated road. Its
result is a conservative wire-length proposal, not routed timing. The owner must
review the full image, opaque macro crossings, clock/reset/tie placement and all
existing reach/timing gates before a physical continuation. Allocation failure
includes partial sites for diagnosis; those partial sites are not an adoption.

After the complete candidate passes its review, compile explicit sites with
`--graph ... --roads ... --sites sites.json --out relay_road_sites.tsv`. Site rows
have `origin_um` and actual row `orient`. All existing buffers on every declared
road need sites. The file freezes every controlled cell's complete non-PG pin/net
inventory, including clocks and resets. No connectivity is modified.

Set `OT_RELAY_ROAD_FILE=/work/relay_road_sites.tsv` in the owned candidate kit.
Modern macro kit generation copies `relay_roads.tcl`; face_flops invokes it before
automatic midpoint clustering. The Tcl helper validates the entire transaction
before moving a cell: exact names/masters, complete pin/net identity, integer DBU,
actual row fragment/orientation, cell footprint, all hard-core halos (at least
8.64 um), fixed-cell occupancy and mutual body overlap. It preserves the placed
road cells FIRM through DPL. Ordinary soft cells still require fresh GPL/DPL.
The default flow remains unchanged when the environment variable is absent.

After repair changes any branch or inserts buffers, regenerate the graph and
complete site contract. Reusing old buffer identities or silently leaving a new
buffer at its straight-line position is unsupported. The current helper handles
existing data FF and BUF/INV/HB placement; reset/tie/control additions need their
own explicit complete candidate rather than an inference from instance suffixes.
