# HBM accelerator executable composition inputs

Owner: Kant (input compiler only). Sagan confirmed no active whole-die
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
the four missing binding groups. They create no placement output directory.
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
- `top`, full `top_parameters`, and `source_pins` (path/SHA references);
- `instances`: exact `name`, `role`, `module`, `rtl_source`, explicit
  `parameters`, `master`, `lef`, `abstract_provenance`, `ports`, `tied_ports`;
- each port's `kind` (`memory`, `signal`, `clock_power`), `physical_bits` and
  `bits_per_cycle`; memory ports also have `bytes_per_cycle`;
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
