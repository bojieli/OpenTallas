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
| `outline {w,h}` / `std_area_um2` + `util` / `contract {file, slot}` | outline: explicit (snapped up to the 2.16 lattice; `"exact": true` keeps the given size: a drop-in replacement inside a fixed sub-slot), sized to util (0.52 default), or the die contract slot |
| `pins {N,S,E,W: [port base names]}` | per-face port groups; base names only (`ck`, never `ck[0]`); every port exactly once |
| `macros [{view, count, at?, at_exact?, orient?, inst?}]` | SRAM/ROM views (DIR holds NAME.lef + NAME_{ss,ff,tt}.lib); `at_exact: true` takes `at` unsnapped (an abutted N-S stack: pitch = array height + 0.024 um; off-track pins FAIL) |
| `children [{view, count, at?, inst?}]` | hard children (cluster): views exported by this flow |
| `layer_cap` | leaf (2026-10-12 contract, `results/arch/hier_contract_1011/layer_usage_1012.md`): signals AND PG stop at M5 (default; PG stripes on M5 as pins, pins on M4/M5, parent straps M6, die signals M6/M7 over the tile, M8/M9 die power + global). `M6` only as a die-lead exception with `layer_cap_grant: "<lead>: <reason>"` (pin-dense edge relays / stations). Kits generated before the cut (`legacy_layer_kits.json`) keep PG M6/M7, signals <= M6; a new spec with `pg_layer` M6/M7 and no grant is refused. Contract slots carry `layer_cap` (new routes) and `view_cap` (the closed view's own cap, valid while child_lint passes at it) |
| `pg_layer` | leaf: derived from `layer_cap` (legacy kits only: M6 or M7); cluster: M7 |
| `inhold` | true: one dont_touch hold buffer per data input -> capture flop before global placement (leaf_inhold.tcl; hold-only input-capture misses on a sound tile) |
| `outhold` | true: flop-driven outputs get lead BUF -> HB4 -> BUF FIRM at the pin before global placement (leaf_iohold.tcl, runs leaf_inhold.tcl too when `inhold`; hold-only reg->output misses at the routed IO ref) |
| `io_flop_at_pins` | `{"cols": N}`: every port's single launch/capture flop FIRM at its own pin before global placement, N staggered rows per face (qwen_die_masters/io_flop_at_pins.tcl, released to DPL by out_flop_release.tcl); for RTL that already registers every port at the face but whose face registers GPL pulls into the core (qkd_d2d_ref reg->out -740 ps). Not combinable with outhold/inhold |
| `recipe` | kit recipe = the generator defaults (kit.env `RECIPE=<n>`, no line = 1). Not set: an existing kit keeps the recipe in its kit.env, a NEW kit takes 2. **1**: hold margin 10 ps, macro halo 2.16 um, no pin hook unless asked, `io_flop_at_pins` cannot be combined with `inhold` / `outhold`. **2** (owner 10-13 finishing recipe): `route.hold_margin_ns` 0.030, `route.macro_halo_um` 5.4, `inhold` + `outhold` + `io_flop_at_pins {"cols": 4}` on, combined through the kit files `pre_gpl.tcl` (hold stages, then pin flops traced through them: `OT_OFLOP_HOPS=8`) and `pre_dpl.tcl` (both releases). Each item is a default: the spec value wins, `false` switches a hook off; no default pin hooks when the spec owns a `POST_TAPCELL_TCL` / `PRE_GLOBAL_PLACE_TCL` hook, no default hold stages with `route.hold_delay`. `pin_balance` stays opt-in (needs per-port `pin_ranges`). M5 re-routes of closed tiles (reroute_batch.py) pin recipe 1. |
| `sdc_extra` | repo SDC files inlined at the end of clock.sdc and signoff.sdc (a second clock domain, e.g. a CDC adapter's controller clock; s81 hc cseq) |
| `inter`, `refglob`, `io_budget {in,out}` | die-context IO (io_ref_skew.sdc), 0.2 / 0.2 T default |
| `abut_plan {channel_um, edge_um, why}` | Diagnostic tile/cluster only with `job.hold_merge`: an explicitly described candidate with narrower than20um channels is routed to measure it; gaps >= `channel_um` and tile-edge distances >= `edge_um` are WARN `abut_plan` instead of FAIL `channel` / `macro_edge`. A block that can merge always obeys the 20-um rule |
| `forwarded_clock` | cluster with a forwarded-clock subtree (keeps the forwarding inverter, own root) |
| `clock`, `clock_ports` | `spine` builds a balanced parent tree; `cts` uses TritonCTS. A wires-only `entries` parent takes one top port per actual hard-child clock pin. Generation automatically creates related per-entry clocks and a virtual IO clock, binds every pin to routed `insertion.json` boundary min/mean/max at TT/FF/SS, and remeasures entry wires after clearing source latency. Delivery is phi minus entry-wire delay minus child reference; ETM arcs are unchanged. Coverage or missing clock data fails. Entry clocks are explicitly propagated before measuring; actual bound Liberty names select TT/FF/SS, because a WC scene may contain TT libraries. Route-boundary/signoff zero wire arrivals require physical source/pin coincidence within 0.001 um; missing parasitics cannot qualify. Same-level internal setup reserves 60+90 ps; any pair with either TT entry-wire plus child R above 300 ps reserves 60+150 ps (including two deep entries); physical FF/SS scenes conservatively use 210 ps when the TT entry-wire level is not measured in that scene; internal hold reserves H1 50+50=100 ps. Its own flops belong in hardened leaves. Obsolete TT-only `wires_only_ioref` entry hooks are replaced automatically; the spine helper remains supported. `probe_clock_entries.py` provides an actual-ETM all-entry calibration probe; zero-wire calibration proves accounting, while routed parasitics and child clock checks remain required for closure. |
| `clock_entry_domains` | Required when a child has multiple clock pins. Explicit related domains map every entry clock port and every normal IO (including resets) once: `{"core":{"ratio":[1,1],"ports":["ck"],"inputs":["rst","f_core*"],"outputs":["t_core*"]},"serial":{"ratio":[4,3],"ports":["ckv"],"inputs":["rsv","f_ser*"],"outputs":["t_ser*"]}}`. CK and CKV remain related at 833.333 and 1111.111 ps (PLL /3 and /4); both crossing directions and waveform edges are checked. Virtual IO references are separate, boundary min/mean/max is per actual child pin and domain, and nominal 0.2T IO budgets remain fixed during route overconstraint. Duplicate/missing domain coverage or unsupported exception policy fails. No asynchronous groups or reset waivers are generated. |
| `spine_through_icg` | cluster whose clock port enters ONE tile clock gate (ICG) that clocks the rest (SM tile `ot_cg_tile`): the spine is built on the ICG output net (`OT_SPINE_THROUGH_ICG=1`, log `OT_SPINE through ICG`) |
| `route {pd, period_ps, hold_margin_ns, threads, peak_ram_gb, pin_h, pin_v, pin_balance}` | route knobs (770 ps over-constraint); `pin_balance: true` places pins uniformly over each face region alternating the pin_h / pin_v layers per 32-pin chunk (OT_PIN_BALANCE_H/V) for dense faces |
| `job {owner, branch, tag, purpose, benches, benched_by, extra_paths, views_to, record_to, no_bench_reason}` | job spec fields; `benches` / `benched_by`: see "Behavioural bench at submit" |

Extra SDC files that measure a soft clock tree must honor `::ot_ref_pre_cts`: it is 1 in the initial route SDC and 0 at signoff and after CTS. Create every real and virtual domain, uncertainty, and crossing constraint in both stages; defer propagation and virtual-clock insertion measurement until the buffered tree exists. A `boundary_tcl` hook restores those domains after every boundary reset. Signoff propagates all clocks again after extra files recreate them.

## What the kit does by construction (pitfall -> mechanism)

| pitfall (2026-10-11) | mechanism |
|---|---|
| PDN stops below the child PG pins (PDN-0233) | cluster grid: M5/M6 stripes + M7 stripes as pins; each child strapped from the layer above its own PG pins (read from its LEF) |
| PDN grid for an absent macro (PDN-0217) | every macro/child grid created only if `ot_ref_present` finds the master |
| bloated abstracts (PDN-0006) | export = `write_abstract_lef` without `-bloat_occupied_layers` (tools/tt_views/view_export.py) |
| child signals on the parent strap layer / over its own PG | leaf: explicit `RLAYERS M2 <cap>` (M5; M6 granted), PG stripes on the cap layer (signals around), pins <= cap (gate FAILs a pin layer above it), strap = cap + 1; legacy kits `RLAYERS M2 M6`, PG M6 or M7; cluster: PG M7, children <= M6; child_lint (c) on the output |
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
| util outside 45-60%, slivers, macro at a pin edge | outline from util 0.52; >= 20 um macro channels and core margin (two R0 macros may instead be ABUTTED N-S, gap <= 0.1 um, when neither has a pin on the touching faces: a bank of arrays with W / E pins; `abutted_stack`), 20 um from any pin face; gate FAILs < 30% / > 70%, WARNs outside 45-60% |
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

Gate = route (2026-10-13, `tools/pin_fit.py`): the route's pin-placement settings have one source
(`ref_tile.route_pin_settings`: `OT_PIN_GROUP_MAX` 32 unless `route.pin_balance` sets it, `pin_min_tracks`, pin layers;
`ref_route.sh` applies the same group bound to the route, the floorplan smoke and `--cts`). Two local checks, also run
at submit:
- `pin_fit`: every `--pin-region` is cut into ordered groups of 32 and `place_pins` needs one 200-slot section on one
  layer per group (six groups, 8 slots stranded), so a face filled above ~96 % of its slots FAILs here instead of in the
  route at `[PPL-0093]` / `[PPL-0111]` / `[PPL-0086]` (qkd_seq_fan-kc2: 1,623 pins on 162 um, the 51st group of 23
  pins). Port widths come from the top's header with the spec `params` applied; a header the parser cannot resolve is
  not judged. Loop successors (`auto_react_parent`) are warned, not refused. Fix: disjoint `pin_ranges` +
  `route.pin_balance`, or a longer edge / a second pin layer.
- `oflop` (kit recipe 2): face density with the recipe's pin hold stages and flop columns. `io_flop_at_pins.tcl`
  now derives the flop gap / columns per face from the FIRM hold cells (from 2 um of hold-stage depth, ~6 b/um:
  10.4 b/um -> gap 4.5 um, 6 columns); `OT_OFLOP_GAP` set = exact, `OT_OFLOP_COLS` = minimum, `OT_OFLOP_AUTO=0` = no
  derivation. WARN (never a refusal: the estimate assumes a stage and a flop on every port; it flags all 7 face
  GRT-0116 routes of 10-12/13 but also 69 closed ones): a dense face on a source without the derivation and no explicit
  gap, an explicit gap that stacks the flops on the stages, or a band deeper than 45 % of the core behind the face.

Closure loop: at submit, a job with `"ref_tile": true` runs the local gate on its kit at the source commit (REFUSE on
FAIL); every other job gets the source-sync check in WARN (mode file `~/.local/state/closure_loop/ref_gate.json`
`{"mode": "warn"|"refuse"|"off", "other": "warn"|"refuse"|"off"}`).

## Behavioural bench at submit (owner 2026-10-13)

A ref_tile job is a closure candidate: its CLOSED is offered to the guarded auto-merge, which needs a behavioural
positive bench (expect `pass`, not a lint) AND a mutant (expect `fail`). The loop applies the same definition at intake
(`closure_loop.py` `bench_evidence_gap`, shared by `auto_merge_guard` and `bench_gate_at_submit`) and REFUSES a job
that lacks it (`SUBMIT_LINT BENCH_REQUIRED`) before any compute. The auto `lint` bench does not count, and
`no_bench_reason` alone no longer admits a ref_tile job. Three ways to satisfy it:

1. `job.benches`: the tile's own bit-exact bench and its mutant
   (`{"name", "cmd", "expect": "pass"|"fail", "pass_regex"/"fail_regex", "min_count_regex", "threads", "peak_ram_gb"}`).
2. `job.benched_by: "<gate>"` for a sub-tile with no golden of its own (HC column/root pieces, SU bank slices): the name
   of a composition gate in `tools/ref_tile/composition_gates.json` (`s81hc_ng64`, `s81hc_ng256`, `s81su_full`, `vm8_cp`). At
   intake the loop appends the gate's positive bench and mutant to the job as `<gate>_exact` / `<gate>_mutant`; they run
   in the job's own source snapshot, i.e. the composition built from the sub-tile's RTL at the job's source commit, and
   the merge guard requires both results. The registry is read from main (the daemon tree), never from the job's
   branch: add a new gate there first (>= 1 behavioural pass + >= 1 mutant, `extra_paths` if it needs unsynced dirs).
   A gate that must be built with branch-specific parameters goes in `job.benches` instead.
3. A physical probe that must never merge: `"hold_merge": "<reason>"` in the job spec (not a closure candidate; it
   cannot be adopted from that job).

`closure_loop.py validate JOB.json` reports the refusal locally. Mode: `ref_gate.json` `"bench"` (ref_tile jobs,
default `refuse`) / `"bench_other"` (every other job, default `warn`). Jobs ingested before the gate, and auto-react
successors of those, are not refused.

## Measured clock rule and structure-repeat limit (owner 2026-10-13)

**Clock rule.** Up to 15,000 sinks on one clock root pass. A larger root is allowed only with pre-route clock-tree
evidence measured by `pre_route_gate.py <kit> --remote <host> --cts` on that kit: TT insertion delay at most 300 ps and
leaf arrival spread at most 80 ps. The three numbers are constants in `tools/textbook_lint.py`
(`CLK_ROOT_SINKS_MAX`, `CLK_INSERTION_MAX_PS`, `CLK_SPREAD_MAX_PS`). Sinks are counted on the synthesized netlist: flops
plus one per hard-child or macro clock pin. A declared spine does not waive the rule and there is no spec waiver; the fix
is hardened leaves with their own roots. CLOSED tiles are not re-judged.

- The gate prints a `clock_rule` item for every kit, with the measured insertion and spread when `--cts` ran, and a
  `--remote` run writes `<kit>/gate_result.json` v2. Commit that file with the kit: the submit gate reads it.
  Its immutable source manifest binds the bytes actually shipped (generated kit, RTL, transitive hooks, macro views,
  and effective daemon helper overlays), the archive SHA256 verified before remote extraction, and the generated
  execution script. Start HEAD and daemon HEAD are provenance; `commit` is null when the effective contents do not
  all match one commit. A later HEAD never changes the receipt's source identity. The remote adjacent
  `<run>.source_snapshot.json` preserves the shipping manifest before execution; runtime image and environment
  provenance appear in the completed receipt. Old receipts are preserved in `source_binding_history/` when replaced.
  A parser-failed v2 run can be recovered without rerouting with `tools/ref_tile/recover_gate_result.py KIT
  --host ORIGINAL_HOST --run ORIGINAL_RUN --script ORIGINAL_SCRIPT --log ORIGINAL_LOG --route-commit EXPLICIT_COMMIT
  [--cts]`. The adapter verifies the entire original manifest, staged source, execution script and archive verification
  log, reruns local checks, and shares the live remote parser. It preserves the original identity and writes FAIL if
  the explicitly requested route source or current daemon helpers differ; it never labels the receipt with current HEAD.
  For an already executed gate, `--frozen-helper-recovery` additionally verifies the original helper plan against its
  recorded committed tree, all helper blob hashes and executable bits, and the actual staged helper bytes and full
  transported modes. It recovers that original evidence without editing the staged tree. Uncommitted helper snapshots,
  missing files, changed bytes/modes, changed producer sources or incomplete execution receipts still fail. The recovered
  receipt retains its original producer identity; ordinary new-job submission continues to check current helpers.
  Gate packing and route refreshes share the effective helper resolver: an older main helper in the daemon is
  resolved to origin/main's bytes; a daemon-only edit retains its exact content identity. New receipts carry the
  full effective route helper plan (hashes and modes). New ingested jobs freeze this plan. Once installed, later stages
  verify the committed original tree/blob identity and every actual `<run>/cl` helper byte/mode against its unchanged
  sidecar, then reuse that directory without writing it. A later main update alone does not replace the executed helpers.
  Missing/tampered original files or sidecars fail closed; recovery does not patch a live job. Initial installs still
  resolve current helpers, and `<run>/cl/helper_overlay_plan.json` records the frozen plan. This transport recovery does
  not change timing acceptance: negative setup/hold, unconstrained sentinel slacks, DRC or other failed checks remain failures.
  Older live jobs and CLOSED archives are preserved. Legacy v2 snapshots remain usable when their exact overlays
  match the effective resolver; an upgraded plan explicitly records the original narrower gate scope.
  Legacy receipts or receipts whose contents differ from the submitted commit/current daemon overlay are refused
  for unclosed tiles; regenerate their gate. CLOSED tiles continue to stand.
- At submit a `ref_tile` job is REFUSED when the kit's gate result shows more than 15,000 sinks without passing
  numbers, or when the kit has no gate result and the block's latest synthesized design in the loop's history had more
  than 15,000 sinks.
- A kit with no gate result and no history is judged by the in-flow lint right after synthesis: the job ends
  `FLOORPLAN_MARGIN` before placement. `textbook_lint: false` and `waive` do not switch this check off.
- `STATE/ref_gate.json` `"clock": "refuse" | "warn" | "off"` sets the mode (default refuse).

**Structure-repeat limit.** A block with two or more terminal failed routes since its last CLOSED (NEEDS_RTL,
EARLY_FAIL_*, or a NEEDS_HUMAN route crash) takes a new job only when the spec carries
`"structural_change": "<one sentence>"`; otherwise the job is REFUSED at submit. Hold-overlay re-runs (name suffix
`-hs`) are exempt. Mode: `STATE/ref_gate.json` `"structure_repeat"` (default refuse). Tests for both rules:
`tools/closure_loop/test_rule_enforcement.py`.

## Validation (2026-10-11)

See /home/ubuntu/claude-takeover-20261007/ref-flow-1011.log (cases, numbers, job names).

For a fleet-selected synthesis or CTS gate, use `--remote auto`. The gate asks `ot-run --pick` for a host with measured headroom, ships the inputs there, then runs through `ot-run --hosts <chosen>` with one resource reservation. An explicit host uses the same admission checks restricted to that host.

The default work/output disk reserve is 20 GiB. Set a positive finite `gate_disk_gb` in the tile spec, or override it with `--disk GB`. Host selection checks the scratch filesystem and adds the measured compressed snapshot size, its estimated unpacked allocation, and 1 GiB for metadata and rounding. Runtime admission checks again after upload, adding extraction space to the work/output reserve. Both integer GiB thresholds and snapshot sizes are recorded in `source_binding.disk_admission`. These checks do not reserve disk against concurrent jobs; a runtime refusal preserves the uploaded snapshot and does not start synthesis.

CTS gates measure every external clock from the actual CTS SDC. The measured clock exception uses the insertion and spread of the largest synthesized root's own source port. A secondary root cannot use the primary clock's measurement; an unmatched root has no measured exception.

Opt-in mixed glue and hard-child clocks use `"clock": "hybrid_entries"`.
Declare every scalar source in `clock_ports`, keep `clock_port` equal to the
first source, and list only the standard-cell tree sources in
`clock_cts_roots` (a nonempty proper subset). For example a band with native
glue and sixteen hard lanes has `clock_cts_roots: ["ck"]` and seventeen
`clock_ports`: `ck` plus `ck_l0` through `ck_l15`. Existing `entries` keeps its
wires-only contract.

Each remaining entry must still directly drive exactly one hard-child clock
pin. Each CTS root must reach only standard-cell register clock pins. CTS gets
only the declared glue nets; it cannot absorb a child entry. All clocks remain
related, including explicit `clock_entry_domains` when present. There are no
asynchronous groups or false paths. The existing pair setup/hold margins apply
between glue and child clocks too.

At each timing scene the generated constraints measure every propagated glue
clock sink for tree safety, select the same input-capture/output-launch
boundary register population as the insertion exporter, and deliver its source
at phi minus that boundary mean. Roots with no boundary registers explicitly
report an `all_internal_only` fallback to their own sink population. Hard-child delivery retains measured entry
wire plus the bound routed child insertion. A shared reference origin keeps
source latencies nonnegative; it does not replace the distinct physical tree
measurements. Missing sources/sinks/measurements fail closed. A final glue root
must have positive measured propagation; above 15,000 sinks it must also meet
the existing 300 ps insertion and 80 ps spread limits. Child insertion records
and ETM timing arcs are read without modification. `OT_HYBRID CTS_MEASURE`
records the actual glue measurements in the run log. Functional microfixtures
validate this flow mechanism, not a production parent's physical closure.
An optional tile `signal_max_layer` may tighten the existing signal ceiling, for example `M4` with `layer_cap: M5`. PG remains on M5 and the parent strap remains M6; macro M4 supply still connects through real M4-M5 vias. The field cannot raise the existing or assigned signal limit. Default M5 and legacy kits retain their existing contracts. Pin placement, GRT and DRT use the explicit lower signal limit.

This opt-in profile runs a net-type audit after DRT and again while exporting each final routed corner, including any hold ECO. It checks signal and clock wire/via geometry against the signal ceiling, PG special-wire geometry against the PG ceiling, and actual signal pins. The exact exported LEF must have no signal pin above the lower ceiling; higher OBS must remain within the PG ceiling and have actual PG metal evidence in the same final ODB. Hard-macro OBS above the requested signal limit are unsupported without separate net-type evidence. Reports and helper hashes are carried in `abstract.json`. An old route report cannot qualify a later ECO.

A held geometry probe never relaxes the 20 um requirement for a production closure candidate. Removing `job.hold_merge` restores the original FAIL; measured access, timing, DRC and eventual die acceptance remain separate requirements.

### Independent CTS roots inside a leaf tile

Opt in with `"clock":"multiple_cts_roots"`, `"kind":"tile"`,
`"clock_ports":["ck_req","ck_rsp"]`, and `"clock_port":"ck_req"`.
Every listed port owns a real standard-cell CTS tree; no hard children or
fabricated child insertion records are used. Explicit `clock_entry_domains`
are required, with one `[1,1]` clock root per domain, the primary root in
`core`, and literal base input/output names covering every IO once (including
reset). The supported relationship is related samefrequency clocks with zero
nominal phase; asynchronous groups, ratio changes, or unassigned IO are refused.
Shared asynchronous resets get one IO reference; actual data-pin paths (including
synchronous resets) must obey their declared domain like other data inputs.

Each root is measured in the actual loaded corner. Its boundary register
population determines its own R; delivery compensates each source to phi−R.
Generated CTS, route, fill, and signoff hooks replay the complete domain
boundary. Actual timing-graph ownership checks reject cross-domain datapaths,
wrong input/output assignments, and unowned registers. This mode deliberately
does not apply the legacy single-clock IO shim. The pre-route gate requires
`--cts`, exact per-source measurement coverage, and the clock rule on each
actual root separately. `ck_insertion.py --all-clocks --raw-source` and exported
multi-clock insertion records preserve the physical per-pin references.

`tests/test_multiple_cts_roots.py` exercises two actual OpenROAD CTS trees,
differing insertion references, source compensation, generated hooks, and
wrong-domain/unknown-port/crossing mutants. These are flow fixtures; production
leaf placement, routed TT/FF timing, DRC, and native boundary closure remain
required.

### Direct raw SRAM clock entries

An `entries` or `hybrid_entries` cluster may expose a raw SRAM clock on its own
face, alongside independently clocked routed children and local CTS roots.
Annotate each individual `macros` item with
`"clock_entry":{"port":"clk_mem0","pin":"clk","reference":"raw_liberty_clock_pin"}`
and an exact `inst` pattern and `count:1`. The port must be a declared hard entry,
not a local CTS root. The generator binds the actual LEF clock pin and all three
raw SRAM Liberty files, requiring memory semantics and real setup, hold and
clock-to-Q arcs. Routed-child ETM insertion records remain a separate reference.

Runtime checks prove the exact linked instance, library corner, sole source and
clock pin. Only the actual propagated source-to-SRAM wire is compensated; no
SRAM internal insertion is invented and its Liberty arcs stay unchanged. Pure
raw-macro clusters are supported as well. The direct-macro probe checks all
three corners, source/corner mutants, unchanged real clock-to-Q timing and the
complete generated entry SDC. Its nonzero-RC SPEF is a test fixture, not routed
layout qualification.

A leaf that actually transfers registered data between these roots must opt in
separately with `"clock_data_paths":"related_same_frequency"` and
`"clock_relationship":{"kind":"same_pll_fixed_phase","ratio":[1,1],"phase_ps":0}`.
The independent profile remains the default and refuses such transfers. The
related profile permits transfers only between registers owned by the declared
roots; direct input capture and output launch still obey each port's domain.
Every detected domain pair must retain finite actual max and min STA paths.
The normal clock-pair setup/hold uncertainty and measured phi−R compensation
remain in force. A false-path mutant is rejected because its required crossing
has no timed path. The declaration expresses the leaf's required clock contract;
production integration must prove that actual parent clock delivery supplies it.
It is not a CDC waiver or evidence that the PLL/clock distribution is closed.

Multi-root ownership classifies asynchronous clear/preset pins using OpenSTA's
`all_registers -async_pins` on the actual loaded Liberty. OpenSTA also includes
these controls in `-data_pins`; they are excluded only from the data-domain
ownership walk and from synchronous crossing witnesses. Recovery/removal timing
stays enabled. Names and `reset_ports` never exempt a real D path. The regression
uses actual DFFASRHQN cells with a shared reset and rejects a mutant connecting
that same reset port to the other domain's D input.

Leaf corner inference uses the actual sequential clock-sink cells. Physical-only
LEF taps and endcaps have no Liberty association and cannot identify a timing
corner. Missing or unknown Liberty associations on actual sequential cells still
fail. The physical regression includes a real LEF-only ASAP7 tap and replays the
complete generated CTS and later boundary hooks.

Multi-root route jobs and their formal CTS gates use the same physical clock
fixes (`cg_pushdown.tcl` and `clk_net_protect.tcl`). They do not install the
legacy single-boundary `link_budget_hook.tcl`: the generated domain constraints
already own every input/output max/min delay and each root's phi−R reference.
Combining the two models created extra route-period virtual clocks that survived
into 833.333 ps signoff. The strict clock inventory guard remains unchanged;
unexpected virtual clocks and aliases still fail. Other clock modes retain the
legacy hook and their existing job command bytes.
