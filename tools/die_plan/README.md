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
- **Die lattice**: put origins and outlines on `die.grid_um` (default 8.64 = lcm of row 0.27, site 0.054, the M2-M9
  pitches and the PG pitches). The pin layers M4-M9 use symmetric tracks (offset = pitch / 2; the generated kits write
  them in `make_tracks.tcl`). Together these put every pin of a type on a die track in all four orients R0, MX, MY and
  R180, at any lattice origin. Mirrored and shifted copies are therefore ONE type with one hardened view.
- **Pins on the type (recommended for replicated types)**: a bus can declare `face`, `window_um`, `layers` and `order`
  in the TYPE frame, and an ft slot can declare `in_window_um`, `out_window_um`, `layers` and `order`.
  - A port with no geometry takes it from its src type, or else its dst type. The pins are computed in that type's frame
    and transformed per instance (`Plan.port_pins`), so every instance carries the identical pin table.
  - When both sides declare geometry, it must agree in the die frame (validate).
  - The other side's instances must also map those pins onto one table (G0 abutment). A mirrored neighbour usually needs
    the mirrored partner type, or windows that are symmetric with the opposite order.
  - Example: `examples/tiny_plan_typegeo.json`.
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
- leaf bindings;
- hard cores (COORD 10-23 CORE-KS): a type over 400k cells needs `hard_cores[]`; core pins on the plan tracks after
  `track_offset_um` and the orient (M2/M3 skipped in mirrored die frames). Cell estimates come from `cells.py`
  (`type.cells`, `contents[].cells`, or evidence files in the plan dir: `cells_est.json`, `plan_notes.json`
  cells_per_type, `l1_cores_v3*.json`, `inputs/cells_evidence.json`, `cells/*.stat`; or `--cells-evidence FILE`);
  `python3 tools/die_plan/cells.py PLAN.json` lists the types over 400k without cores;
- core faces (`core_faces`, PLAN-TOOL4): every hard-core port sits on a core face that faces its partner (partition
  face via `buses[].leaf` / `contents[].bind` `bus:`, or another core / placed leaf via `net:` binds or the
  `core_conns.json` sidecar `{type: {core: {port: ["bus:B" | "core:C" | "leaf:L" | "face:N"]}}}`). ERROR when the
  mean best cosine (pin face normal vs direction from the core centre to a partner) is < -0.1, WARN up to 0; the
  message names the face to re-pin to. Cores with no known connectivity are WARNed as unchecked;
- completeness (`complete`, COORD 10-23): a missing field is an ERROR, counted per field in `summary.complete`:
  cells, `track_offset_um` on every hard core, a clock method (`tap_um` / `taps` / `tap_mode`), the die
  `clock.common_latency_ps` (R4 owner rule: the one target every partition balances its face flops to; also the
  vclk latency), type `insertion_ps` equal to it, a reset sync, face-flop pin geometry, and `internal_stations[]` for
  every estimated internal reg-reg connection over `ft_station_max_um` (R3-INTERNAL).

G0C (COORD 10-23): the `hard_cores`, `core_faces` and `complete` findings are ERRORs only with
`check.py --completeness`; plain G0 reports them as WARN `[G0C] ...`. `summary.g0c` lists findings per partition type
(`g3_eligible` = types with none and no die-level gap).

Cross-die G0C rules (PLAN-TOOL5, COORD DIE-PLAN VISUAL REVIEW 10-23 (a)-(e); `die_io.py`, `reach.py`, `xdie.py`; all
ERROR only under `--completeness`, counts in `summary.xdie_counts`):
- `die_io_plan` (a): every IO-class content (SerDes, UCIe, HBM PHY; catalog `die_io.CLASSES`, module regex -> off-die
  signals + bump pitch, ASSUMED class counts) has a `die.io` window of its `iface` over it, within
  `budgets.io_edge_max_um` (200) of a die edge, with `signals <= sites`; one window carries the host link (`host: true`
  or `iface: host`). `python3 tools/die_plan/die_io.py plan PLAN --out PLANDIR/die_io.json` (or `--inplace`) proposes
  them (footprint = the PHY content's outline, host = the link PHY nearest the host logic: CONFIRM). check.py reads
  `PLANDIR/die_io.json` when the plan has no `die.io`.
- `cut_lines` (b): bits per cut at every partition face line (abutted port bits + ft routes crossing it) against the
  partition pin layers x `pin_track_max` + die layers x `cut_avail`. The 250-um sweep (`cuts`) never lands on a face,
  so it never counted abutted neighbour links (most lanes on S81 / KV / HBM).
- `reach` (c): one per-layer measured reach table for all dies (`reach.py`, source results/arch/die_reach_m89_1022.json:
  M4-M7 452.5 measured -> 405 owner local plan, M8 1001.2, M9 1012.8, calibrated min over the 6 release relays). A
  hop routes on `lane.route_layers`, else `layer_budget.ft_route_layers`, else M8/M9 when `die_use` has `ft_reserved`;
  ERROR when hop > `budgets.reach_margin` (0.9) x the min reach of those layers. `die.reach_um` only WARNs.
- `face_tracks` (d): per partition face, every 10-um window: pins / usable (PG-free) tracks of the face's allowed pin
  layers (type `face_layers` incl. an M8 / M9 third layer, else M4..`partition_signal_max` in the face direction)
  <= `pin_track_max` (0.6), all layers together and per layer.
- `ft_budget` (e): per type, over-the-top ft bits (E-W slots on M8, N-S on M9, turning slots on both) + non-ft M8 / M9
  face pins <= usable M8 / M9 tracks across the type x `type.ft_budget[L]` (default `layer_budget.cut_avail[L]`).

R4 (owner clock rule, COORD 10-23 19:55): `OT_TAP_CHECK` (tree insertion) and `OT_CLOCK_TAPS` (sinks per tap) only
WARN. The hard clock checks are face-flop spread <= 80 ps (TT+FF, RC) and seam skew <= 80 ps to the common latency.
Tap method (CP1 r8 RULING, COORD 10-23 21:26): every partition gets a GRID of clock taps at `budgets.tap_pitch_um`
(default 400 um, or type `clock.tap_pitch_um`), every sink on its nearest tap, trees balanced to the common latency.
`clock.tap_mode` `grid+sinks` (alias `sinks`) only ADDS sink-anchored taps (taps.py) for face-register clusters after
the grid taps; they never replace the grid.  Kit SDC seam-hold padding: min input delay = -`clock.insertion_tol_ps`.

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

## G2 probes (`g2.py`, redefined by COORD on 10-23)

```
python3 tools/die_plan/g2.py all  PLAN.json --out DIR [--worst 5] [--adjust 0.5] --run   # -> DIR/g2_report.json
python3 tools/die_plan/g2.py die  PLAN.json --out DIR --run
python3 tools/die_plan/g2.py part PLAN.json --out DIR (--types a,b | --worst 5) --run
```

When partitions abut, the die has no signal route of its own, so G2 has two parts.

**(a) Die probe.** This covers the die-level nets only: the clock spine (spine root to every partition's clock tap) and
the reset spine (root to every reset tap), routed on the die layers.
- The partitions block M1-M7. Areas listed in `die.channels` stay open.
- `die.pg.grid` stripes are M8/M9 obstructions.
- It reports GRT overflow per layer, wirelength, and root-to-tap reach (max and p90).

**(b) Partition FT probes.** These run once per partition TYPE, on the N worst types by G0 (worst cut-segment ratio,
then face pin density).
- The partition gets its exact outline and pins (the kit `io.tcl` and `make_tracks.tcl`).
- Each pin bit gets a flop beside its pin.
- Each ft bit gets its station flops: data plus the epoch bit, at `regs_um` or spread evenly along the in-to-out route.
- Leaf blockages come from `contents[].origin_um/outline_um`, as obstructions M1..`obs_max` (default M5) plus placement
  blockages.
- Then it runs detailed placement, GRT on M2..M7 with `--adjust` capacity left to the partition's own logic, and DRT
  pin access.
- It reports overflow, wirelength and no-access counts.

PASS means every probe finished, total overflow is 0, and no pin is without access.

Probes are read-only diagnostics, run directly in docker with `--memory` equal to `--memory-swap`. Memory is set by
`--mem`: 64 GB by default for the die probe, 32 GB for a partition probe. The S81 frame-sized fa probe peaked at 33 GB
(GRT about 4 min), so run it with `--mem 48` on a host that keeps at least 64 GB free.

## G0 census coverage (`census_cov.py`, mandatory from COORD 10-23 06:45)

Every plan declares `census`. It is either `[{rows, map, note}]` (paths relative to the plan) or `{"none": reason}`.
`none` is only for synthetic or proof plans, and it raises a WARN. Leaving `census` out is an ERROR.

**`rows`** is an FT census (`tools/die_feedthrough` census JSON `groups[]`, or the `<die>_lanes.tsv`). Each row has
`src, src_bus, dst, dst_bus, kind, bits`.

**`map`** is a JSON file with these keys:
- `parts`: instance to partition (exact names);
- `rules`: `[[regex, partition|group]]`;
- `groups`: a group to partition list, used when a census block is re-derived as several partitions;
- `collapse`: pass-through regexes, such as `^ld_` landing cells;
- `exempt`: `[{match, kind: clock|reset, replaced_by, reason}]`.

G0 checks:
1. Unmapped instance is an ERROR.
2. For each directed partition pair, planned lane bits (data width; an ft lane counts once) must be at least the
   as-built bits. Otherwise the shortfall is reported as `dropped` (ERROR).
3. Reset or clock rows count as dropped unless an explicit `exempt` entry lists them. Exempt totals appear in the
   summary.
4. A group spanning several partitions gets a WARN: the traffic inside it needs a finer census.

## TYPE-DEDUP (`dedup.py`, `gen.py dedup`; opt-in, writes a copy)

```
python3 tools/die_plan/dedup.py analyze  PLAN.json [--fix-order] [--out report.json]
python3 tools/die_plan/gen.py   dedup    PLAN.json --out-plan COPY/die_plan.json [--fix-order] [--only canon,..]
python3 tools/die_plan/dedup.py variants PLAN.json [--rtl BOUND_RTL_DIR]     # bound modules per plan type (kit count)
```

Merges near-duplicate partition types only when the merge is exact: the same netlist key (outline, bus interface with
leaf binds, ft slots, contents with params, hard-core modules) and, per instance, an orient under which every port keeps
its die pins and the instance's type-frame pin table equals the canonical type's. `--fix-order` also accepts members
that match up to the bit order of some ports (same faces and tracks) and re-solves port / type orders die-wide as
parity constraints; the provenance lists the re-ordered ports and the other types whose pin tables change (their kits
regenerate). A bound-RTL gate (default `PLANDIR/bind/bound_r8/rtl`) keeps a member whose bound netlist differs (R8
pads, narrowed ports) as its own type. Members that differ only in contents params are reported STRAP candidates, and
members that differ in ft-slot population FT-POP families; neither is merged (no tie-offs: a strap is a planned lane
from a configuration register, an unused slot is an unbound bus). Ports, lanes, latency and census are never changed;
`verify()` re-checks that, and the output must pass G0 (`check.py`) like any plan. Results: `results/type_dedup/`.

## Whole-die CI (`die_ci.py`, lane DIE-CI, owner-approved 2026-10-24)

```
python3 tools/die_plan/die_ci.py run [--mode commit|nightly] [--g2 auto|all|none] [--views-root DIR]   # -> results/die_ci/<date>_<sha12>/
python3 tools/die_plan/die_ci.py margins --derive --out tools/die_plan/die_ci_margins.json            # liberty-derived margin numbers
```

One entry point re-runs the whole-die prototype of every plan (s81, s81_head, qwen_compute, qwen_kvsys, hbm; hbm_arch B2
once on main) on one sha: G0 + G0C (one `check.py --completeness`), cross-die (PLAN-TOOL5 in-die rules + `xdie_io.py`
on the rack tables), G2 (`g2.py` die + 5 worst types; CARRIED in commit mode when the plan and G2 tools are unchanged),
census + latency consistency (the `<die>_latency.json` carrying the current plan digest equals `Plan.lane_latency()`),
and die STA through DIE-STA's `die_sta.py` (ILM) on a sub-top of the partitions registered in `die_ci_views.json`,
with stand-in budgets (kit SDC contract composition, else the R2 face-flop estimate) for every other seam.
Per die: `<die>.json` + `<die>.md` (gate status, counts, worst seam slack, deltas vs the previous run); `SUMMARY.md`.

Margins (`die_ci_margins.json`, derivations inside) are added ON TOP of the AGENTS.md policy and reported next to the
policy slack: crosstalk per seam (|MCF-1| x R_eff x Cc over 2 x pin_reg_p90; OpenSTA has no SI), IR drop (PDNSim when a
die PDN database exists, else 5 % VDD stated -> late cell derate via the alpha-power law), flat OCV
(`set_timing_derate`). `check_margins` refuses any value that would relax the policy. Until the owner rules on the margin values, the die STA gate is
the policy slack (TT setup / FF hold, 60/25 ps); the margined slack is an INFO column.

Schedule (localhost systemd user timers, `systemd/`): `die-ci-commit.timer` hourly runs `die_ci_cron.sh commit` when main
moved with changes under tools/die_plan or physical/die_plan; `die-ci-nightly.timer` 02:30 Pacific runs the full set.
The runner picks a scratch2 host with `ot-run --pick`, runs there via `ot-run`, copies the run back to
/srv/opentallas-scratch/claude/die-ci/results, commits the JSON/MD to branch `claude/die-ci-results`, and keeps the
`DIE-CI LATEST:` line of ~/coord/HANDOFF.md current.

Optional FT bit sites: a slot may declare `bit_sites_um` as internal stages j=1..stations-1, each containing width+1 cell lower-left x/y coordinates (payload bits then epoch), and `bit_site_cell_um` as the allocated width/height envelope. The physical generator emits exact sites; the hook requires real row/site alignment, row orientation, core bounds and master dimensions. Slots without this declaration keep their existing placement. Validate actual macro/cell overlap and paired-bit reach in the placed ODB before routing; coordinates alone do not establish those gates.

## Die STA (`die_sta.py`, G4 seam timing; lane DIE-STA 10-24)

```
python3 tools/die_plan/die_sta.py extract --odb KIT/run/results/asap7/*/base/5_route.odb --out PARTS/<type>   # RCX
python3 tools/die_plan/die_sta.py top  --plan PLAN.json --out DIE/die_top.v [--views VIEWS]   # = die_top_struct.v
python3 tools/die_plan/die_sta.py run  --top DIE/die_top.v --parts PARTS --out OUT [--mode ilm|flat|etm]
        [--corner TT --corner FF] [--spine-branch DIE/spine_branch.json] [--die-spef DIE/6_final.spef] [--threads N]
python3 tools/die_plan/die_sta.py compare OUT_FLAT/die_sta.json OUT_ILM/die_sta.json --tol 2
python3 tools/die_plan/die_sta.py replica --netlist P/6_final.v --spef P/6_final.spef --n N --out DIR   # capacity
```

`PARTS/<x>/6_final.v|.spef` per partition (found by the module name in the netlist; `6_final.sdc` names the clock
ports).  Seams are found from the die top (every internal net from a partition output to another partition's input)
and reported per `src->dst/bus`: worst slack, path count, violating endpoints, TNS, launch/capture clock arrival.
Constraints follow AGENTS.md (owner 2026-10-24): one clock on die `clk`, propagated through each partition's own routed
tree, 60 ps setup / 25 ps hold uncertainty; signoff = setup at TT, hold at FF (the default `--corner TT --corner FF`),
plus the R4 face-flop spread: clock arrival spread over every register launching into / capturing from a seam,
<= 80 ps per partition at TT and FF (`FFSPREAD`).  SS may be run for information and never gates.
`verdict.status` is PASS only when TT setup and FF hold ran, every seam slack is >= 0 and every spread <= 80 ps;
otherwise FAIL or NOT RUN.
Die spine: ideal by default (taps at the plan's common latency), `--spine-branch` (CP2 H-tree branch offsets as
source latency on every tap pin), or the routed die SPEF.  All current plans (s81, qwen_compute, qwen_kvsys, hbm)
have no channel ports, so every seam wire is a zero-length abutment; channel seams need the routed die SPEF.

Modes:
- **ilm** (default, continuous die check): each partition is replaced by its interface logic model, extracted from
  the routed netlist: fan-out of every non-clock input to the first register, fan-in of every output back to the
  launching registers, the clock network of those registers, and every other cell on a kept net as a side load (that
  pin only), so kept nets keep their exact RC and pin load; the SPEF is filtered to the kept nets.  Corner independent
  (one abstract per type, cached in `OUT/ilm/<module>`).  Internal reg-to-reg paths are not timed (that is the kit's
  own signoff).
- **flat** (signoff): routed netlists + per-instance `read_spef -path`, stitched under the die top.
- **etm**: OpenSTA `write_timing_model` per type and corner.  NOT a verdict: OpenSTA be771a0 writes clock->output arcs
  from the max arrival only (`MakeTimingModel::min_max_`), so ETM hold is optimistic.  KV pair e5e6: ETM vs flat
  -82 ps setup / +73 ps hold.

Validation (KV pair e5e6, routed kv3_io_cor_v1 | kv3_io_ft_v1, 4 seam groups, TT / FF / SS): ilm == flat to
0.000 ps on every seam slack and face-flop spread, ilm 2x faster than flat.  (That pair: TT setup +93.7 ps, FF hold
+231.0 ps, spread TT 24.8 / FF 20.1 ps: PASS.)

Flat capacity (OpenSTA be771a0, `replica` of routed kv3_io_cor_v1, 16 threads; results/die_sta/capacity/SUMMARY.json):
linear from N=8 to N=512 (73.4M instances, 172.8 GB, 5817 s; ~2.4 KB per instance).  Split: 2.4 KB per logic cell,
0.9 KB per tapcell (no timing: strip), 3.9 KB per net of parasitics (1.1 KB with `--reduce` = read_spef -reduce, seam
slacks unchanged to 0.000 ps on KV e5e6).  The serial SPEF reader dominates time (~7 MB/s; -reduce halves it again).
Full die (400 x 400k logic cells): ~970 GB with full parasitics = NOT feasible on a 1 TB host; ~540 GB with
`--reduce` = feasible, ~19 h per corner (one process per corner, TT and FF on two hosts).  The continuous G4 check is
`ilm` (seam-exact); flat `--reduce` is the signoff run.
