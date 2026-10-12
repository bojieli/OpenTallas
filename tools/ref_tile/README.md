# Reference tile / cluster flow (tools/ref_tile, owner 2026-10-11)

The one mandatory way to build a NEW hard tile (leaf) or hardened cluster (tile + hard children): a small spec in, a
closed, die-placeable block out (exact abstract, TT/FF/SS libs with clock insertion, child_lint clean), with every
flow-mechanics pitfall of 2026-10-11 prevented by construction or rejected by a minutes-long pre-route gate.

## Five commands

```bash
WT=/home/ubuntu/wt/<your-tag>; cd $WT
# 1. write the tile spec (copy tools/ref_tile/examples/nhb_pbst_ref.json; cluster: examples/qkv_hub_t.json)
python3 tools/ref_tile/ref_tile.py gen my_tile.json                     # 2. kit physical/ref_tile/<name>/ + job.json
python3 tools/ref_tile/pre_route_gate.py physical/ref_tile/<name> --remote ot-epyc2 [--cts]   # 3. gate (local s + remote min)
git add physical/ref_tile/<name> my_tile.json && git commit -m ... && \
  python3 tools/ref_tile/ref_tile.py job my_tile.json --commit $(git rev-parse --short=9 HEAD) && \
  git add physical/ref_tile/<name>/job.json && git commit -m ... && git push origin HEAD:<branch>       # 4. commit
cp physical/ref_tile/<name>/job.json /tmp/claude-review-20261003/closure_jobs/<job name>.json        # 5. submit
```

No `outline` yet? Run step 3 once with `"std_area_um2"` absent and an outline guess: the remote gate prints the
synthesized area and the exact `"std_area_um2"` to put in the spec; `gen` then sizes the outline to util 0.52.

## Spec

| key | meaning |
|---|---|
| `name`, `top`, `kind` | kit name ([a-z0-9_]), top module, `tile` (leaf) or `cluster` (has hard children) |
| `sources`, `params`, `clock_port`, `reset_ports` | RTL, top parameters, clock port, reset ports |
| `outline {w,h}` / `std_area_um2` + `util` / `contract {file, slot}` | outline: explicit, sized to util (0.52 default), or the die contract slot |
| `pins {N,S,E,W: [port base names]}` | per-face port groups; base names only (`ck`, never `ck[0]`); every port exactly once |
| `macros [{view, count, at?, orient?, inst?}]` | SRAM/ROM views (DIR holds NAME.lef + NAME_{ss,ff,tt}.lib) |
| `children [{view, count, at?, inst?}]` | hard children (cluster): views exported by this flow |
| `pg_layer` | leaf: M6 (default) or M7; cluster: M7 |
| `inhold` | true: one dont_touch hold buffer per data input -> capture flop before global placement (leaf_inhold.tcl; hold-only input-capture misses on a sound tile) |
| `sdc_extra` | repo SDC files inlined at the end of clock.sdc and signoff.sdc (a second clock domain, e.g. a CDC adapter's controller clock; s81 hc cseq) |
| `inter`, `refglob`, `io_budget {in,out}` | die-context IO (io_ref_skew.sdc), 0.2 / 0.2 T default |
| `forwarded_clock` | cluster with a forwarded-clock subtree (keeps the forwarding inverter, own root) |
| `route {pd, period_ps, hold_margin_ns, threads, peak_ram_gb, pin_h, pin_v, pin_balance}` | route knobs (770 ps over-constraint); `pin_balance: true` places pins uniformly over each face region alternating the pin_h / pin_v layers per 32-pin chunk (OT_PIN_BALANCE_H/V) for dense faces |
| `job {owner, branch, tag, purpose, benches, extra_paths, views_to, record_to, no_bench_reason}` | job spec fields |

## What the kit does by construction (pitfall -> mechanism)

| pitfall (2026-10-11) | mechanism |
|---|---|
| PDN stops below the child PG pins (PDN-0233) | cluster grid: M5/M6 stripes + M7 stripes as pins; each child strapped from the layer above its own PG pins (read from its LEF) |
| PDN grid for an absent macro (PDN-0217) | every macro/child grid created only if `ot_ref_present` finds the master |
| bloated abstracts (PDN-0006) | export = `write_abstract_lef` without `-bloat_occupied_layers` (tools/tt_views/view_export.py) |
| child signals on the parent strap layer / over its own PG | leaf: explicit `RLAYERS M2 M6`, PG on M6 (signals around) or M7 (PG only); cluster: PG M7, children <= M6; child_lint (c) on the output |
| child edge pins covered on pin layer +-1 (DRT-0073) | pin-access keepout on the layer ABOVE the outer half of the face-pin column (OT_PK_ABOVE_ONLY=1; the layer below stays free for the tile's own access, hfd_hc c95527ec0) at PRE_GLOBAL_ROUTE, removed at POST_DETAIL_ROUTE (stn_pin_keepout.tcl, OT_PK_FRAC 0.5); child_lint (f) |
| macros / tiles off the track grid (DRT-0255/0418/0419/0421) | macros: (0.432, 2.16) um lattice + the best origin shift over EVERY layer's tracks (check_macro_track_alignment); hard children: 43.2 um lattice = lcm(site, row, M1-M7 track pitches, PG strap pitch); all-layer pin check in gen + gate |
| escaped vs unescaped instance names | place.tcl matches with backslashes stripped on both sides |
| 1-bit vector ports named `ck[0]` (PPL-0061) | pin plan takes base names only (spec error otherwise); gate checks names against the RTL ports and the synthesized netlist |
| parameters on hard children | gate `rtl` check: `#()` on a hard child outside `ifndef <hard_define>` FAILs |
| missing TT/FF/SS libs | export writes ss/ff/tt; gate + child_lint (d) |
| child clock insertion not in its view | export: write_timing_model clock-tree arcs + `insertion.json` (ck_insertion.py, routed); child_lint (g) |
| cluster skew between parent flops and hard tiles (ds-vm be hold -532 ps; attention halves 1,634 ps leaf spread) | clusters: the pre-placed balanced clock spine (physical/common_flow/clock_spine.tcl, c11a6e02a) replaces TritonCTS by default (`"clock": "cts"` opts out); each leaf's target adds the hard child's own TT-lib clock insertion, so flops inside the children balance against the cluster's flops; `--cts` reports the final leaf spread. Leaf tiles keep local TritonCTS |
| forwarded-clock subtree hook missing | `forwarded_clock: true` composes forwarded_subtree.tcl into PRE_CTS |
| route script default overriding the kit's layers | ref_route.sh passes the kit's explicit `RLAYERS`; nothing else sets routing layers |
| macro clock pins on unbuffered wires | loop default macro_cts_cluster.tcl (shipped; the remote gate ships it too) |
| ORFS PLACE_DENSITY_LB_ADDON silently overrides the spec PD (pbst 0.50 -> 0.1075 target, GPL-0305) | every kit clears the addon (`route.lb_addon` re-enables it explicitly); gate FAILs a kit that leaves it, `--cts` WARNs when the placer's effective target differs from PD by > 0.05 |
| util outside 45-60%, slivers, macro at a pin edge | outline from util 0.52; >= 20 um macro channels and core margin, 20 um from any pin face; gate FAILs < 30% / > 70%, WARNs outside 45-60% |
| one clock root over > 15k sinks / 600 um, high fanout, reset on datapath, logic behind pins, ICG enable from a port, > 500 um per stage | remote gate: textbook_lint on the synthesized netlist + placed-IO floorplan; clock_domain / high_fanout / wire_reach REFUSE-tier FAIL, boundary / logic_depth WARN (calibration below) |
| runtime-indexed wide part-selects (yosys SHARE stall) | gate `rtl` WARN with the fix; the remote synthesis smoke runs under a time cap (2,700 s) and FAILs a stall |
| spec does not list a directory the flow sources | gate `sources`: every file the job's commands, scripts, hooks and views reference (followed recursively, generators one level) must exist and lie in source.paths + extra_paths |
| benches never finish / PASS without counts | benches run in the loop under Verilator 5.050; add `min_count_regex` to a bench whose pass log lacks a count |

## Pre-route gate

`pre_route_gate.py KIT [--remote HOST] [--cts]` prints one `GATE <PASS|INFO|WARN|FAIL> <check>: <message> -> FIX: ...`
line per finding and `PRE_ROUTE_GATE: PASS|WARN|FAIL`. Local checks take seconds; `--remote` runs the kit's real ORFS
synthesis (time cap) + floorplan + PDN + IO placement on the host (ot-heavy, small slot), then the netlist textbook lint
and the pin plan against the synthesized ports; `--cts` adds CTS, clock insertion spread (ck_insertion) and the worst
setup path classes (in/reg/macro -> reg/out/macro). `--job SPEC` checks any loop spec's source-sync closure.

Closure loop: at submit, a job with `"ref_tile": true` runs the local gate on its kit at the source commit (REFUSE on
FAIL); every other job gets the source-sync check in WARN (mode file `~/.local/state/closure_loop/ref_gate.json`
`{"mode": "warn"|"refuse"|"off", "other": "warn"|"refuse"|"off"}`).

## Validation (2026-10-11)

See /home/ubuntu/claude-takeover-20261007/ref-flow-1011.log (cases, numbers, job names).
