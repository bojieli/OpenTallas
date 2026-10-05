# HBM accelerator executable composition inputs

Owner: Kant (joined physical model and placement inputs); Sagan owns current
measured-target source/port/width/hierarchy selection. Sagan confirmed no active whole-die
assembler at 03:47:26; component owners and shared inventories stay unchanged.
Claude owns the full-target source selection and any structural design change.

`bindings.json` pins the current source authorities and existing macro views.
It has separate **deepseek** and **qwen** selections. Both are **BLOCKED**:
there is no committed selected full-die instance census joined to a priced
unified-model physical record. The compiler emits no placeholder floorplan.

```sh
python3 tools/hbm_accel_fulldie_inputs.py --target deepseek --out /path/to/new/inputs
python3 tools/hbm_accel_fulldie_inputs.py --target qwen --out /path/to/new/inputs
```

Current inputs return exit 2 and a machine-readable BLOCKED result listing
the missing binding groups including service.loader. They create no placement output directory.
After the authority supplies explicit records, replace only the target's
`selected_instances` and `unified_model` references with repository-relative
`{path, sha256, pointer}` references (pointer is optional JSON Pointer).
Use `--bindings` for a separately pinned future selection. No model replay,
elaboration, synthesis, inference, route, or physical tool is launched.

## Exact missing bindings

1. **Current physical source/top and full instance census.** DS authority is
   `dshbm_1m_allmeasured.py`/its measured composition: TP96, 32 SMs per die,
   N1024 SU and the actual dedicated/service/collective resources. Qwen authority
   is the HA8 W12 driver and its selected f12 successors: emitted die, tiles,
   vector storage, collective and four-stack wstream. Its chosen TP, SMIN,
   CODE_BANKS, arithmetic and service parameters must come from the actual
   selected build/source record. A shared 32-SIMT census is incorrect.
   `ot_hbm_accel_hbm_system` is the reduced HA3 adapter, not either full target.
   Its fixed loader/position widths cannot implement DS96/32/1M by overrides.
   On its memory path `NPC` means PCs **per stack**; four stacks of 32 PCs are
   128 PCs total, not `NPC=128`. No reduced default is selected here.
2. **Unified-model physical selection.** Pin the same census and parameters to
   every replica, slot/halo, memory and boundary port, mux/fanout area, routing
   layer/channel capacity, wire/CDC/credit cost and composed token latency.
   Historical ablation geometry and clocks are not a substitute. No topology,
   slot, clock or rate is invented by this compiler.
3. **Current compute/storage views.** Popper's existing SM_r2 source is
   `3b4bd73f…716d23`, NC8/SUB4/XD128/MAX_OUT512, with 202 macros and an existing
   2202.768 × 2072.79 um element context. Its component TC/BD views and placement
   are captured under `providers/sm_r2/` with exact remote origins and hashes.
   Whole-SM hardened LEF is still absent; the physical route is owned by Popper.
   Either that real abstract or a complete owner-priced expanded leaf/logic
   mapping is needed. RF residence/views must be explicit. Qwen needs its own
   W12 tile/vector storage bindings. An absent generic RF/L2 role requires a
   pinned owner source exclusion, not importation of DS or ablation storage.
4. **Actual L2/service/controller/PHY/collective bindings.** Supply selected
   module/parameters/counts, residence, footprints, pins, LEF and SS/FF library
   lineage. SRAM primitive LEFs alone do not size their enclosing controller.
   The existing 32-PC PHY LEF is a known, assumed licensed-IP outline; it does
   not prove silicon/package signoff or current controller-side installation.

These requests were sent directly to Sagan/Claude and Popper; no new run was
requested. No user topology decision is implied by the current missing records.

## Executable record schema

The selected-instance record requires:

- `design_kind: "hbm_accelerator"`, `target: "deepseek"|"qwen"`, `adopted: true`
  (selected component design, **not** full-die signoff), `census_complete: true`;
- `top`, `top_source`, full `top_parameters`, and `source_pins` (path/SHA references);
  every public parameter in the exact top and instance module headers must be
  supplied explicitly; the compiler does not fill values from RTL defaults;
- `instances`: exact `name`, `role`, `module`, `rtl_source`, explicit
  `parameters`, `master`, `lef`, `abstract_provenance`, `ports`, `tied_ports`;
- each port's `kind` (`memory`, `signal`, `clock_power`), `physical_bits` and
  `bits_per_cycle`; memory ports also have `bytes_per_cycle`. A bundled port
  supplies `lef_pins` mapping its logical name to every actual LEF bit pin;
  physical width must equal this pin count. A scalar defaults to its own name;
- optional `contained_in` for storage physically contained by a hardened block;
  no extra placement/area charge is emitted for such a child;
- `absent_roles` source references if RF or L2 is absent in that target.

Every abstract-provenance record requires `actual_macro_abstract: true`, matching
RTL/parameter/LEF references, `master`, actual `size_um`, `liberty.ss/ff` references,
and no `pending_outline`. A containing block must additionally bind each child
under `contained_instances[name]` to its exact abstract-provenance reference.

The unified-model record requires:

- matching `design_kind`, `target`, `top_parameters`, `selection_sha256`,
  `uarch_source`, pinned `technology_source`, `slot_latency_route_ready: true`;
- `die_um`, `core_um` as **x/y/width/height**, `reticle_mm2`, `macro_grid_um`,
  `routing_layers`, `clock_domains_ns`, and setup-SS60/hold-FF25 `uncertainty_ps`;
- `required_roles`, exact `replica_counts`, matching `absent_roles`, and a
  keyed `instances` table covering the complete selected census;
- each instance's identical parameters/ports, `reservation_um`, `location_um`,
  orientation (R0/MX/MY/R180), `macs_per_cycle`, `communication_intensity`,
  `mux_demux_fanout_area_um2`, `latency_cycles`;
- `boundaries`: actual `[instance, port]` endpoints, reserved layers,
  `tracks_per_bit`, `required_tracks`, `capacity_tracks`, wire/CDC/credit cycles
  and composed boundary latency. Track demand uses physical bus width, never
  the lower average port duty cycle;
- `layer_reservations`: layers, `box_um` and purpose signal/power/clock/keepout;
  `composed_token_cycles` includes the complete per-user path.

All counts, footprints, ports and route/latency terms must be explicit.
Missing values, source drift, incomplete census, wrong target/parameters,
pending abstracts, undersized/overlapping reservations, off-grid placements,
unaccounted pins or over-capacity routes refuse emission.

On complete inputs, the compiler writes `floorplan.tcl`, `macro_place.tcl`,
`lef_files.txt`, SS/FF library lists and `composition.json`. Load the selected
netlist and views before sourcing Tcl. Placement checks the loaded macro census,
instance names and master identity before placing anything. The composition JSON
carries exact ports, boundaries, layer reservations and prices for the physical
owner's existing flow. It always says `signoff: false`; emitting inputs is not
RTL exactness, SS/FF closure, routability, power or performance evidence.

## Current measured-target physical join

`python3 tools/hbm_accel_physical_join.py --target deepseek` (or `qwen`)
emits integration demands from pinned Sagan component authority, the actual DS
composition, Qwen **TP4 measured** record, captured SM context, PHY metadata and
Turing's existing unified-model loader geometry price. This reads existing
results; it performs no RTL measurement or model replay.

The DS candidate 32-SM footprint/macro sum is explicitly conditional: captured
SM source 3b4 differs from current measured component source 88e6. It cannot be
charged as adopted until Sagan resolves source compatibility. Qwen TP4 measured
NWS5/TWS38/ORD7 supersedes the reconciliation common NWS4/TWS30/ORD4 tuple for
that measurement; final fmax successors still require Sagan selection. No DS
SM geometry is transferred to Qwen's 421.5 MiB storage residence.

`physical_join.allocation` can point to a pinned JSON record keyed by target.
Each target supplies existing `service_box_um`, `loader_box_um` (both x/y/w/h),
`parent_budget_name: "service"`, `parent_includes_loader_area: true`,
`blocked_area_um2`, `repair_clock_buffer_area_um2`, `unallocated_service_area_um2`,
and `fold_regions` for crc_got_load, crc_got_store, vcrc_load, mcrc_store.
The named allocation is **service.loader**, contained in the existing service
budget: loader slot area is charged once, while new exclusive corridor area is
charged against remaining service capacity. The isolated 68379.6 um2 vehicle
is never used as the parent rectangle.

`corridors` names MREQ, RSP, DMA64 and CRC with `box_um`, layers containing
actual `direction`, `pitch_um`, `reserved_tracks`, `port_coordinates_um`,
`additional_exclusive_area_um2`, `clock_period_ns`, `wire_cycles`, `cdc_cycles`,
`credit_cycles` and `exposed_token_traversals`. This joins physical width/cut
capacity and incremental exposed latency, without average-throughput discounts
or zero-cost clock repair. The CRC demand remains the conservative 35520-track
all-cut bound until Turing supplies a source-bound locality reduction. Actual
clock/reset/IRQ routing and full service/compute/collective bounds must also be
joined before full-die admission; loader geometric admission alone cannot
select a CRC repair or authorize a build. Allocation is currently null because
no source-selected service rectangle exists. Total die area, physical token
latency and physical fit remain unknown until the full component join is supplied.

Exact budget contradiction: HA9's DS 340.5 mm2 right-size inherits
`uarch_model.right_size_hbm_die` and HBM_SHORE 8.5 mm/PHY (19 mm long edge
including two 1 mm corners). The actual existing PHY LEF is 12.000096 mm wide;
four stacks placed two per edge need 26.000192 mm with those same corners.
The actual old full rectangles are 815 mm2 GPU comparator layouts with pending
SM abstracts, not current sm_v/TU96 or W12 instances. DS service r11 explicitly
sets DS_provider_area_fit=false. Thus no current source-selected die/core/service
rectangle can be obtained from these authorities without a geometry selection;
`budget_join` emits the exact pinned conflict and never imports those slots.
Kant has sent this specific conflict to Sagan/Claude/Turing. The missing work
is current rectangle selection plus actual component costs/ports, not approval
of the already implemented record compiler.

The owner decision now supersedes 340.5 mm2 with actual 12 mm PHY sizing.
`deepseek_physical_model.json` and `qwen_physical_model.json` are the current
joined integration models, consuming Sagan's committed per-target portmap.
Their `current_frame` uses 33 x 26 mm / 858 mm2 limits and actual four-PHY
constraints, with no change to rank, SM, tile or stack counts. The DS captured
four-by-two eight-SM group envelope is 8811.072 x 4145.58 um before external
channels/halos; source compatibility and remaining dedicated/service/clock/PG
bounds are explicit. These partial envelopes are not minimum feasible dies.
No loader coordinates can be emitted safely until actual service geometry,
port locality and repair capacity fill those bounds. The named service.loader
allocation and corridor pricing are executable when those real fields arrive.

Turing's actual width-successor price is captured byte-identically under
providers/loader_width. Full-stack access requires byte ADDR37 encoded as
stack2/local35, translated by bit slices to sector34+stack2. The current model
therefore requires MREQ341 at the service boundary (internal byte packet342),
RSP273 and DMA64. +62 address/validity FFs cost at least18.0792 um2, with guard,
mux, CDC and repair cost still unknown. The previous loader CRC context cost is
retained without removal credit; its closure cannot qualify this successor.
Allocation must include address_guard_mux_CDC_cell_area_um2 and an explicit
wide_source_price_complete bound before loader geometric admission. The copied
owner price is default-off/unselected; it does not adopt or implement new RTL.
