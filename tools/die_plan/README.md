# tools/die_plan — plan-first die tooling (TOPDOWN-PLAN, owner-approved 2026-10-23)

One `die_plan.json` per die, at `physical/die_plan/<die>/die_plan.json`, is the single source of truth. The G0 checker
and every generator (partition wrapper RTL, partition physical spec, latency table, die assembly) read only this file.

- `schema.py`: the schema (`SCHEMA`), the `Plan` loader and helpers, and `validate()` (structure + references).
- `die_plan.schema.json`: the JSON schema (draft 2020-12), written from `schema.SCHEMA` (`schema.py dump-schema`).
- `examples/tiny_plan.json`: a 4-partition example (forward lane through 2 ft slots, return lane, neighbour chain, die IO).

```
python3 tools/die_plan/schema.py validate physical/die_plan/<die>/die_plan.json     # exit 1 on error
python3 -m pytest -q tools/die_plan/
```

## Conventions (binding for every tool)

- Units are um and ps. The die frame has its origin at the die's lower-left corner.
- A partition instance has `origin_um`, the lower-left corner of its placed bbox, and `orient` (R0, MX, MY or R180).
  Every coordinate inside `partition_types` is in the type frame (R0, origin at the lower-left corner).
- Put origins and outlines on `die.grid_um` (default 8.64 = lcm of row 0.27, site 0.054 and the M4-M9 pitches). Then
  rows, sites and tracks are the same in the die frame and in the partition frame.
- **Port**: one signal bundle between two partitions, on one shared face.
  - `face` is the source partition's face in the die frame. When the source is `@die`, it is the destination's face on
    the die edge.
  - `window_um` = [lo, hi] along the face in die coordinates: y for E/W faces, x for N/S faces.
  - `layers` holds 1 or 2 layers, which must run in the right direction: H (M4/M6) for E/W faces, V (M5/M7) for N/S.
    Partition pins stay at or below `layer_budget.partition_signal_max`; the G0 checker enforces that limit.
  - `pin_positions(port)` computes the exact pins. Bit i goes on `layers[i % n]`, and the bits are spread evenly over
    the window on whole tracks. Both partitions use the same function, so their pins coincide by construction.
  - Every port is registered on both sides: a boundary flop at the source pin and one at the destination pin.
- **Bus**: a declared partition interface (`partition_types.*.buses`, dir in/out, width, and the `leaf` inst.port it
  binds to). Each bus of every instance is bound by exactly one port. An unbound bus is an error, because tie-offs are
  not allowed. A fan-out is several explicit out buses.
- **ft slot**: `ft_slots[]` of a type. Slot `S` defines bus `S_i` (in, on `in_face`) and bus `S_o` (out, on
  `out_face`), with `stations` registers between them (default 1). Each register holds reset-less data plus one reset
  epoch bit. `regs_um` optionally pins the station sites, in the type frame. A partition larger than one hop carries
  more stations. An instance with an unused slot fails as unbound, so a different slot population is a different type.
- **Lane**: an ordered list of ports. Consecutive ports meet inside one partition, at `S_i` -> `S_o` of one slot. The
  lane starts at a functional out bus and ends at a functional in bus. Every port belongs to exactly one lane, and a
  neighbour link is a 1-port lane.
- **Latency** of a lane is the register stages it adds between the source leaf and the destination leaf:
  `out boundary flop + sum(stations of the crossed slots) + in boundary flop + fixed_cycles` (a die-IO end has no partition flop). `Plan.lane_latency()` is the only formula. The table in
  `latency.lanes` is generated, and G0 checks that it is complete and equal to the formula. `param` names the SV/compiler
  parameter.
- **Clock**: there is one root per partition, at the type's `clock.tap_um` on a die layer (M8/M9). Insertion at the
  boundary flops is `clock.insertion_ps` +/- `insertion_tol_ps` (250 +/- 40), and neighbour skew is <= 80 ps.
  `face_xing` = `budgeted` means abutted faces are timed as ordinary synchronous hops under that budget.
  `forwarded_landing` means a forwarded clock plus a landing at every abutted face.
- **Reset**: there is one async-assert / sync-deassert synchronizer per partition (`sync_stages`). Data and ft flops have
  no reset (`data_reset` is const false), and each station carries one epoch bit (`epoch_bit` is const true). Release age
  is counted, never padded.
- **Budgets**, with these defaults:
  - `face_pins_per_um` 6 on `face_pin_layers` 2, also measured over any `face_window_um` 10 um window;
  - `pin_track_max` 0.6;
  - `cut_ratio_max` 0.6, swept every `cut_step_um` 250 um;
  - `pin_reg_p90_um` 30 (the G3 gate).

## die_plan.json fields

| key | content |
|---|---|
| `schema` | `"opentallas.die_plan.v1"` |
| `die` | `name`, `label`, `tech`, `outline_um` [W,H], `channels[]` {rect_um, reason} (die-level gaps; anything else uncovered is a G0 warning), `period_ps`, `reach_um` (S81 1500, KV 1200, QC 1000, HBM 1000), `rep_um` (450), `grid_um`, `rows`, `layers[]` (name, dir H/V, pitch_um, offset_um; ASAP7 default), `layer_budget` (`partition_signal_max` M7, `die_layers` [M8,M9], `die_use`, `cut_avail` {layer: fraction of tracks the die/ft traffic may use}), `pg` (`partition_pg_max`, `grid[]` layer/width/pitch/offset/nets, continuous across abutment) |
| `partition_types` | `{type: {module, outline_um, hard, kit, buses[], ft_slots[], clock{tap_um, layer, insertion_ps, insertion_tol_ps}, reset{tap_um, sync_stages}, contents[]{inst, module, status reuse/rework/new, kit, geom_pass, origin_um, outline_um}, channels[]{rect_um, reason}, ft_track_frac}}`. A replicated type is listed once. |
| `partitions` | `[{name, type, origin_um, orient}]` |
| `ports` | `[{id, src{part,bus}, dst{part,bus}, width, kind data/ctl/clock/reset, face, layers, window_um, order lsb_low/lsb_high}]` |
| `lanes` | `[{id, ports[], fixed_cycles, reach_um (override, e.g. half-cycle), param}]` |
| `clock` | `source`, `insertion_ps`, `insertion_tol_ps`, `neighbour_skew_ps`, `face_xing`, `spine{layers, root_um, topology}` |
| `reset` | `source`, `sync_stages`, `data_reset` (false), `epoch_bit` (true), `release` ("counted") |
| `latency` | `{lanes: {lane: {cycles, stations, faces, fixed, param}}}` (generated) |
| `budgets` | see above |

`validate()` checks the structure and the references:
- unique names;
- known types, partitions and buses;
- bus direction and width on both port ends;
- layer direction matches the face;
- every bus bound exactly once;
- lane continuity through ft slots;
- each port in exactly one lane;
- latency keys are known lanes.

The geometric and budget checks are G0 (`check.py`).

## G0 check and G1 render (`check.py`, `render.py`)

```
python3 tools/die_plan/check.py PLAN.json [--out DIR] [--png] [--strict]   # exit 1 on any ERROR; writes DIR/g0_report.json, DIR/die_plan.png
```

The checks are listed in the `check.py` docstring:
- schema;
- geometry and grid;
- abutment (faces coincide, pins on track in both frames, no shared tracks, identical pin tables across a replicated
  type);
- layers <= M7;
- face density (<= 6 pins/um over any 10-um window, <= 2 layers, pin/track <= 0.6);
- cut sweep every 250 um, as full line and as per-partition segment. Capacity counts the partition ft layers M4-M7
  times `ft_track_frac` (default 0.25), plus the die layers times `cut_avail`. The M8/M9-only ratio is also reported, in
  the research-sweep form;
- hops <= reach;
- latency table complete and equal;
- a clock tap and a reset synchronizer per partition type;
- leaf bindings.

A synthetic 24x24-partition plan (22k ports, 960 lanes) checks in about 5 s, including the render.

The render (G1, for GEOM-REVIEW) shows:
- partitions coloured by type, with names and orients;
- port windows;
- lanes, with width as line weight;
- stations (dots), clock taps (stars) and the spine root;
- channels (hatched);
- G0 errors in red.

## Generators (`gen.py`)

```
python3 tools/die_plan/gen.py latency PLAN.json [--inplace] [--out DIR]
```

This writes `latency.lanes` back into the plan (with `--inplace`), `<die>_lat_pkg.sv` (one `localparam int` per lane,
named by `lane.param` or `LAT_<ID>`) and `<die>_latency.json` (the compiler's input, which carries the plan digest).
A die-IO lane counts 1 cycle: the boundary flop of its partition end.
