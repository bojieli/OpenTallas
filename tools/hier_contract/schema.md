# Hierarchy contract (TOP-DOWN HIERARCHY CONTRACT, owner 2026-10-11)

One JSON per die: `results/arch/hier_contract_1011/<die>.json`, JSON Schema `tools/hier_contract/contract.schema.json`
(`schema: "opentallas.hier_contract.v1"`). The die lead owns it. Elements are built to their slot; a change goes
through the lead, bumps the slot `version` and the file `version`, and gets a `changelog` line.

## Slot fields

| field | meaning |
|---|---|
| `name`, `cell`, `kind`, `parent` | slot instance name, the LEF MACRO / module built for it, die/parent/element/tile, enclosing slot (`null` for the die top) |
| `outline.w`, `outline.h` | um, fixed by the parent floorplan (50-60% utilisation, >= 20 um channels) before the child routes |
| `origin.x`, `origin.y`, `origin.orient` | um, lower-left in the parent frame. Macro origins must keep the pins on the routing tracks (asap7 M4 y = 0.012 + 0.048k) |
| `pins[]` | `name` (or bus `name[msb:lsb]`), `face` N/S/E/W, `layer`, `offset` (um along the face, pin centre), `width` (um; also the offset tolerance) |
| `io_budget` | `in_delay_frac` / `out_delay_frac` = fraction of `clock_period_ps` (833.333) used outside the slot; default 0.2 T each side with registered boundaries |
| `clock_entry` | `pin`, `face`, `offset`, `layer` where the parent clock spine enters the slot |
| `target_insertion_ps` | clock-pin insertion delay the parent CTS balances against (CLOCK LATENCY ACROSS THE HIERARCHY) |
| `pg_layer` | the child's top layer: full-length VDD/VSS stripes only (leaf: M6 or M7 per die; a parent that is itself a child: M7) |
| `strap_layer` | the parent's strap layer = `pg_layer` + 1; the child puts no signal or OBS there |
| `signal_max_layer` | highest layer for child signals (normally `pg_layer`, with signals routing around the stripes, or `pg_layer` - 1) |
| `layer_cap` | (2026-10-12) top layer for a NEW route of the slot's tile, signals AND PG: M5 (default from `layer_defaults`); M6 only with `layer_cap_grant` "<die lead>: <reason>". `pg_layer` / `strap_layer` / `signal_max_layer` follow it (cap / cap+1 / cap) |
| `view_cap`, `view_layers`, `view_status` | (2026-10-12) the existing closed view's own cap and pre-bump layers; the view stays valid only while child_lint passes at `view_cap` (strap = cap + 1); `view_status` records the measured top signal layer from layer_usage_1012.json |
| `layer_rule` | which rule the slot follows: `tile_m5` (bumped), `cluster` (cluster PG M7 over <= M6 children, unchanged), `hard_ip` / `die_layer` (PHY / die-layer pins, unchanged; die lead re-plans) |
| `version` | slot version; the element records the version it was built to |

M8/M9 belong to the die top only.

## Example

```json
{"schema": "opentallas.hier_contract.v1", "die": "hbm_accel", "version": 1, "clock_period_ps": 833.333,
 "slots": [
  {"name": "u_slice5", "cell": "ot_hbm_w2_stn_slice5", "kind": "tile", "parent": "u_station",
   "outline": {"w": 90.0, "h": 58.0}, "origin": {"x": 20.0, "y": 20.016, "orient": "R0"},
   "pins": [{"name": "clk", "face": "S", "layer": "M5", "offset": 1.98, "width": 0.024},
            {"name": "din[127:0]", "face": "S", "layer": "M5"}],
   "io_budget": {"in_delay_frac": 0.2, "out_delay_frac": 0.2},
   "clock_entry": {"pin": "clk", "face": "S", "offset": 1.98, "layer": "M5"}, "target_insertion_ps": 150,
   "pg_layer": "M7", "strap_layer": "M8", "signal_max_layer": "M7", "version": 1}]}
```

## Tools

* `child_lint.py CHILD.lef [--libs DIR] [--contract DIE.json --slot NAME] [--json]` - checks (a) no bloated OBS at or
  above the PG layer, (b) full-length VDD/VSS stripes on one top layer, (c) nothing on the strap layer or above,
  (d) TT/FF/SS libs, (e) contract outline / PG layer / pin face+layer(+offset), (f) face-pin access (no OBS on the
  layer above a face pin; fix = `physical/redesign_ds/coll_split/pin_access_pregrt.tcl`), (g, warn) clock insertion
  from the TT lib vs `target_insertion_ps`. Exit 1 on any FAIL.
* `macro_grid_lint.py SPEC.json [--repo DIR]` - evaluates a job's macro placement Tcl against a mock OpenDB and
  refuses macros whose origin puts their signal pins off the routing tracks (DRT-0255 / DRT-0419).
* `hier_submit.py` - the closure loop's submit hook: finds the hard-child views a parent spec names and runs
  `child_lint` on each (mode from `~/.local/state/closure_loop/hier_lint.json` `{"mode": "warn"|"refuse"}`, spec
  `"hier_lint": false` opts out), and runs `macro_grid_lint` (always refuse; spec `"macro_grid_lint": false` opts out).
* `slot_fit.py KIT_DIR` - (owner 2026-10-13: a tile must be known to fit its die slot BEFORE it routes) compares a ref_tile
  kit with the slot the live contract gives its top cell (the spec's `contract`, else every slot / `sub_layouts` row of
  that cell): outline, pin faces, pin layers, layer cap, estimated clock insertion vs `target_insertion_ps` (+-100 ps;
  estimate = spec `est_insertion_ps`, else the cell's previous view). `tools/ref_tile/pre_route_gate.py submit_check`
  REFUSES a mismatch unless the spec carries `"slot_change_request": "<die lead log line or contract version>"`; then
  it is a WARN and the request is appended to the die lead's log. A contract named in another's `derived_from` is
  superseded and not checked.
* `die_real_census.py` - per master, the die instances bound to a real closed view (exact LEF + exact ETM of a view
  found by the master's name) against placeholders / generated views; JSON + a README row in
  `results/physical/die_real_census/`. Die leads run it on every die case and every contract version (`--contract`).
