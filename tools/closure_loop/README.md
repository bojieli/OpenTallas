# Closure loop (tools/closure_loop)

A scripted block-closure loop that runs with no AI in the loop (owner-approved 2026-10-06), so usage-limit outages
no longer leave the fleet idle. The daemon `closure_loop.py daemon` runs as the systemd user unit
`closure-loop.service` on localhost. It only dispatches work over ssh and takes every job through these stages:

```
sync source (git archive of the pinned commit -> <host base>/<job>/src, read-only to everyone else)
 -> bench stages (expect pass | fail: an exact bench must PASS, a negative control must FAIL)
 -> calibrate (DEFAULT ON): CTS-only run -> measured SS/FF clock insertion at the boundary registers
    (ck_insertion.py) -> CK_* env + regenerated IO SDC (your sdc_cmd)
 -> route -> [signoff] -> VERDICT: SS >= +15 ps, FF >= +15 ps at 833.333 (60/25 corners), DRC 0, every check OK
      CLOSED : collect -> export -> commit record + view on the job's branch (explicit paths)
               -> trial-merge the branch into merge_target in a scratch worktree -> push -> ledger
      budget : (jobs with a `budget`) calibrate is a CHECK against the sheet -> NEEDS_BUDGET on deviation
      else   : path-class summary (path_summary.py: worst 10 classes per failing check, start/end, slack, levels)
               -> ledger -> NEEDS_RTL
 a stage crash -> retry ONCE (on another host if the crash is resource-related: OOM / ENOSPC / Killed / lost wrapper)
              -> NEEDS_HUMAN
```

## Add a job: one JSON file

Drop `<name>.json` into `/tmp/claude-review-20261003/closure_jobs/`, or commit it to
`tools/closure_loop/jobs/` on main. The daemon reads both locations every minute. Check the file first with
`python3 tools/closure_loop/closure_loop.py validate <file>`. The spec is frozen the first time the daemon sees it,
so a new source commit needs a new job name (`<block>-<sha9>`).
`jobs/hbm-svc-SE_s3-fb5bc706e.json` is a complete real example.

| field | meaning |
|---|---|
| `name` | unique, `[A-Za-z0-9._-]`; also the run dir name |
| `block` | master/top. The loop allows **one route per (block, source commit)**: the key is taken when the route launches, and a retry after a crash is the only re-run |
| `owner` | stream that owns the block (e.g. `Claude:hbm-views`) |
| `hosts` | optional hosts.json subset. The loop takes the LEAST-LOADED host that fits. A job with `peak_ram_gb` <= 40 may also go to any other host whose toolchain matches the reference host EPYC3 for the tools its commands use (ORFS image digest; asap7lock / iverilog / verilator / yosys only when mentioned). Every command snippet is checked with `bash -n` at drop time |
| `threads`, `peak_ram_gb` | route estimate, used for host choice and the load cap |
| `source` | `branch`, `commit` (must be on `origin/<branch>`), optional `paths` (default tools rtl physical Makefile), `extra_paths` (result dirs your tools read) |
| `stages.bench[]` | `{name, cmd, expect: pass|fail, fail_regex?, pass_regex? (MULTILINE, searched over the whole stage log), ok?, threads?, peak_ram_gb?}`. You need at least one `pass` and one `fail`, or a top-level `no_bench_reason` that names the bench record. A negative whose rc is 124/137/139/143, or whose log looks like OOM, counts as a crash, not a FAIL |
| `stages.calibrate` | `{cmd, base, clock?, sdc_cmd?}`, or `{"enabled": false, "reason": "..."}`. `cmd` is the CTS-only run. For a route_view.sh / run_abi3_physical flow it is the route command, written so that `{LABEL}${CL_LABEL_SUFFIX}` (=`<label>_cal`) is the label and `$CL_STOP_AFTER` (=`--pnr-stop-after cts`) goes on the end. `base` is a glob of its ORFS `results/asap7/*/base`. `clock` is the clock name (default `ck`; spine/svc views use `core_clk`). `sdc_cmd` regenerates the IO SDC from the measurement, e.g. `physical/hbm_accel_die_views/common/make_io_vclk_margin.sh $CK_SS_MEAN`, `make_io_vclk_ff.sh $CK_FF_MIN $CK_FF_MAX`, or the stations' `MARGIN=1 CKINS=$CK_SS_MAX CKFF="$CK_FF_MIN $CK_FF_MAX"` (stn_margin_sdc.py + io_min_delay.json from stn_io_min.py) |
| `stages.route` | `{cmd, ok?, logs?}`. The route only counts as done if the wrapper exits 0 AND `ok` exits 0 (e.g. `grep -q '^rc=0' {RUN}/routes/{NAME}/exit`). `logs` are scanned for resource-crash signatures |
| `stages.signoff`, `collect`, `export` | `{cmd, ok?}`, all optional. signoff runs before the verdict, collect/export only after CLOSED |
| `verdict` | `corner_sta` (glob of a tools/w18/corner_sta.py JSON) + `drc_metrics` (glob of ORFS `5_2_route.json`), or `metrics_cmd` printing `{"ss_ps","ff_ps","drc"}`. `checks[]`: `{name, cmd}` must exit 0 (LEF check MATCH, pin access ...). `macros`, `post_sdc`, `summary_base`: inputs for the failure summary |
| `record[]` | `{from: remote path (may use {RUN}), to: repo-relative path, exclude?}`, copied into the branch on CLOSED. The loop also writes `results/closure_loop/<name>/verdict.json` |
| `merge_target` | branch to trial-merge the job branch into after CLOSED (`main`, a coordinator branch, or null) |
| `budget` | optional `{master, clock?, domain_clock?[], on_deviation?: flag\|continue, sheets_ref?}`: close against the master's BUDGET SHEET (results/rtl/budgets_20261006/sheets/<master>.json at `sheets_ref`, default origin/main). At sync the loop generates `{CL}/budget_route.sdc`, `budget_signoff.sdc`, `budget_ff.sdc` with tools/budgets/make_block_sdc.py and exports `BUDGET_SDC`, `BUDGET_SDC_SIGNOFF`, `BUDGET_SDC_FF`, `BUDGET_SHEET`, `BUDGET_LINT_SS/FF`; use them in `sdc_cmd` / the route instead of `make_io_vclk*` at `$CK_*`. Calibrate stays a CHECK: a measured insertion off the sheet (or over the block's insertion target) by more than the sheet tolerance -> `NEEDS_BUDGET` (default) or a ledger flag (`continue`); `retry` of a NEEDS_BUDGET job continues after calibrate on the sheet SDC |
| `cycles_added` | optional, copied into the verdict record for the recompose |

Placeholders in every command: `{RUN}` (the job's run dir), `{SRC}` (`{RUN}/src`, the cwd of every stage), `{CL}`
(`{RUN}/cl`: stage scripts, logs, rc files, calib.json, path_summary.json), `{NAME}`, `{LABEL}` (the name with every non-`[A-Za-z0-9_]` character as `_`: USE IT AS THE ROUTE LABEL, since run_abi3_physical --nickname-tag rejects dashes), `{BLOCK}`, `{COMMIT}`,
`{HOST}`, `{THREADS}`. The same values are exported as env vars, plus `CL_PHASE`, `CL_LABEL_SUFFIX` and
`CL_STOP_AFTER`. Every stage after calibrate also gets `CK_SS_MEAN/MIN/MAX`, `CK_FF_MEAN/MIN/MAX` (boundary
registers, ps) and `CK_*_ALL_*` (all registers).

## Floorplan margin lint (OWNER 2026-10-08): verdict FLOORPLAN_MARGIN
Every calibrate and route runs `tools/fp_margin_lint.tcl` + `tools/fp_margin_lint.py` at ORFS PRE GLOBAL_PLACE (after the
block's own PRE_GLOBAL_PLACE hook, on 3_2_place_iop.odb), installed in the flow container by `tools/orfs_hold_mm.py` and
switched on through the docker shim (`OT_FP_LINT=1`, verdict dir `{CL}/fplint/<stage tag>` mounted at /ot_fplint). A failing
floorplan stops the flow in seconds and the job ends `FLOORPLAN_MARGIN` with the reasons (no retry, no route spent):
utilisation > 60% (> 65% with 1 BUFx2 hold buffer per flop), > 12 pins/um/layer over 100 um of a face, a full-density pin
column within 1 track of a PDN strap / via stack, an illegal pin width (WIDTHTABLE), cut-line nets over the free tracks,
a macro on a pin edge with pins behind it, an unblocked < 12 um macro gap with rows, a pin bank > 100 um from its pins.
Spec `"fp_lint": false` opts out; `"fp_lint": {"set": {"util_max": 0.62}, "warn_only": true}` overrides / reports only.
Offline: `openroad` `read_db X.odb; source tools/fp_margin_lint.tcl; ot_fp_lint_dump d.json`, then
`python3 tools/fp_margin_lint.py check d.json` (calibration and thresholds in that file's docstring).

### Lint at submit (2026-10-09): pin density / utilisation before any compute
`validate` and intake run `submit_lint.py` on route_master.sh jobs: the cfg outline, `--pin-region` plan, top-module port
widths (ANSI header, parameters resolved, no synthesis) and IO placer settings give a LOWER BOUND on the flow lint's pin
density per face/layer (a region is one ordered group packed on one layer at PIN_MIN_TRACKS x pitch; a face averages at
least T/(layers x max(L, 100 um))).  Fails as configured -> the first APPROVED automatic fix whose estimate passes
(coordinator 2026-10-09, layout only, 0 cycles), in order: 1. `pin_balance` OT_PIN_GROUP_MAX=32 + OT_PIN_BALANCE_H 'M4 M6'
/ _V 'M5 M7' (uniform over the region, layers alternating per 32-pin chunk; needs span/pins >= the layer pitch);
2. `pin_tracks2_spread` PIN_MIN_TRACKS=2 + PIN_H 'M4 M6' / PIN_V 'M5 M7' (the group must fit the face).  The settings go
inline on the `bash ...route_master.sh` invocation and are recorded in `spec.submit_lint` (submitted spec kept in
`spec_submitted`); no fix passes -> `REFUSED` "SUBMIT_LINT FLOORPLAN_MARGIN: ..." saying why each fix does not.  Utilisation
is estimated only from an earlier FLOORPLAN_MARGIN util measurement of the same synthesis input (STATE/submit_lint_util.json).
A setting counts only when the job's SOURCE COMMIT's flow reads it (drive-0212: OT_PIN_GROUP_MAX / OT_PIN_BALANCE_* exist in
run_abi3_physical.py since dde873a8e, PIN_MIN_TRACKS in route_master.sh since main; on an older source the fix is not
applied and the job is REFUSED "rebase the source").  Balanced regions add only where their ranges overlap (densest 100 um
window).  `"submit_lint": false` opts out.  `closure_loop.py submit-recheck --since ISO [--requeue] [--log F]` re-judges past
FLOORPLAN_MARGIN jobs without a live successor.

## Early-fail gates and the stuck scanner (OWNER 2026-10-08, stuckscan)
The daemon probes every RUNNING route every 15 min (`early_fail_gate`, one ssh; spec `"early_fail": false` opts out) and
stops a hopeless run at once with a terminal verdict, its diagnosis in `{CL}/early_fail.json`,
`STATE/early_fail/<job>.json` and `failtrig/stuck/<job>.json` (failtrig/scan.py lists EARLY_FAIL_* as redesign work even
with a live sibling; an old-flow hold flood is a `flow` item: re-route under the HM/stall guard):
- `EARLY_FAIL_SETUP`: TT runs only (liberty corner read from the synthesis log), before 5_3/6_*. Post-CTS
  (`4_1_cts.json`) WNS normalised to 833.333 (`ws + 833.333 - route period` for 730-833 ps routes; other clocks
  unshifted) < -400 ps with > 500 failing endpoints (or TNS < -1e6); before CTS finishes, post-placement
  (`3_5_place_dp.json`, ideal clocks) < -900 ps with > 2,000 endpoints. CALIBRATION (`stuckscan.py --calibrate`,
  289 finished TT routes, 214 closed at TT): post-CTS -> final TT recovered p50 +133 / p90 +312 ps (NOT the 60-100 ps
  assumed: route-SDC IO and repair after CTS), the worst post-CTS WNS that still closed is -358.1 (4 endpoints) /
  -329.3 (656 endpoints), post-placement -736.6; the gates would have stopped 12 (CTS) / 5 (placement) routes whose best
  final TT was -117 / -162 ps and NO eventual closure. The verdict carries the worst max path of every path group
  from the post-CTS (else placement) report: class input/reg/macro -> reg/macro/out, wire- vs logic-dominated, max fanout.
- Coordinator rules (2026-10-08): CRITICAL_PATH item 1 (S81 BF: names bfh*/bfi*/bf_*/*halfphl*, block
  ot_s81_bf_native) is NEVER auto-stopped (daemon gate skips it; stuckscan reports `critical` with what it would have
  done). A route on an untrusted clock insertion (`insertion_untrusted`: its parallel calibrate measured > 100 ps off
  the assumption, or the assumption came from another variant and is not measured yet) has its setup gate judged on
  reg->reg/macro paths only (IO slack is fake on a wrong insertion; bfh_halfphl started on the full-rate SS 1169 / FF 714
  vs its real 1546 / 875), and the real-hold-WNS gate does not apply to it.
- `EARLY_FAIL_HOLD`: during CTS / GRT hold repair, only when the repair is NOT converging (drive-2140; the endpoint
  count in margin is not a verdict -- 30k-70k endpoints at HM 10-25 with WNS -20..-40 converge): hold buffers inserted
  in the step > 100k (or > 0.30 x placed instances, floor 20k; 0.60 x / floor 60k while real WNS gains >= 5 ps over
  2,000 iterations); real WNS < 0 gaining < 1 ps AND hold TNS improving < 2 % over the last 2,000 cumulative iterations (guard chunks summed; a flat WNS with falling TNS is one stubborn endpoint, drive-2155); or
  real WNS < -150 ps after 1 h gaining < 5 ps over 2,000 iterations.  NEVER once real hold WNS >= 0 (drive-2155: the
  margin is a design target, HM 0 allowed); the flow's MET-FIRST guard (orfs_hold_mm.tcl) repairs a margin flood at
  HM 0 and stops once met (OT_HOLD_FLOOD_MET_FIRST=0 disables it).
- `EARLY_FAIL_CONGESTION`: GRT past extra iteration 20 with > 1,000 markers in the latest congestion-N.rpt and no new
  best (by 5%) over the last two reports (10 iterations).
- `EARLY_FAIL_DRC`: DRT past iteration 20 with > 100 violations and no new best over the last 8 iterations.
- A stage still without a pid file 1 h after its launch is LOST (crash path: retry once elsewhere); it used to poll
  STARTING forever (hbm_pkt_ii3ref: run dir emptied, 16 h).

`stuckscan.py` (run by the 15-min drive) diagnoses every live job from one probe per host (step logs, the current
step's hold/GRT/DRT progress, congestion reports, the job's process-tree CPU over 5 s) and recommends an action:
`cancel` (redundant: a counting closure of the block on the same or a newer commit, or a newer descendant commit of the
same variant RUNNING; a closure on an OLDER commit only flags `redundant?`), `early_fail` (the gates above), `kill_stage`
(hung: no write for 45 min and < 0.2 cores; or an old-flow hold margin chase frozen >= 3 h with hold >= 0 -> the loop
retries the stage once under the guarded flow; cancelled instead when a newer commit of the block is live), else
`let_run` with `slow` (step > 2x the p90 duration per floorplan-ODB MB learned from finished jobs,
`STATE/stuckscan_hist.json`) / `quiet_busy` notes. `--apply` executes them through `closure_loop.py cancel --why`,
`early-fail <job> --verdict V --why W --detail F` and `kill-stage <job> --why W [--orfs DIR]`, and logs to
`claude-takeover-20261007/stuckscan.log`. Report: `STATE/stuckscan_last.json`.

## Rules the daemon enforces
- Load cap (OWNER_RULE_LOAD_CAP): launch only if `load1 + own launches of the last 5 min + threads <= cap`
  (1.2 x cores: 154 / 34 / 77) and `MemAvailable >= peak + 32 GB`; per-host per-job limits and NVMe run roots in
  `hosts.json`. Otherwise the job waits, and the reason is shown in the status.
- It never kills anything it did not start. `cancel` stops only its own stage process group and containers that
  mount its own run dir. It never sweeps settings.
- It registers every run in `/home/ubuntu/opentallas-monitor/experiment.py` as `closure-loop:<name>`, owner
  `Claude:closure-loop`.
- Commits stage explicit paths only (sparse scratch worktrees under `~/.local/state/closure_loop/git`), never
  `git add -A`, and never touch the shared checkout.

## Operate
```
systemctl --user status closure-loop          # daemon; log ~/.local/state/closure_loop/daemon.log
python3 tools/closure_loop/closure_loop.py status
cat /tmp/claude-review-20261003/CLOSURE_LOOP_STATUS.md   # rewritten every tick
cat /tmp/claude-review-20261003/CLOSURE_LOOP_LEDGER.md   # one entry per verdict
python3 tools/closure_loop/closure_loop.py retry <name>  # human: re-queue a NEEDS_HUMAN job
python3 tools/closure_loop/closure_loop.py cancel <name>
```
Job state lives in `~/.local/state/closure_loop/jobs/<name>.json` (events, metrics, calibration, publish result).
The unit runs from `/home/ubuntu/wt-closure-loop`; `closure-loop.service` here is the installed copy.

## Host capabilities and stage needs (2026-10-06)
`hosts.json` gives each host its `caps` (EPYC1/2/3 and AGIdock: verilator, yosys, iverilog, orfs; PVE1: orfs only).
Any bench or stage may set `"needs": [...]`. Defaults: bench = verilator + iverilog + yosys; calibrate, route,
signoff and the failure summary = orfs; collect and export = none. All stages of a job run on one host, so the host
must cover the UNION of the job's needs and match EPYC3's ORFS image digest. The loop never places a job on a host
that lacks a need.

## Budget check (2026-10-06)
Calibrate stops a budget job (NEEDS_BUDGET) only when the measured SS insertion EXCEEDS the block's target
(`internal_insertion.target_ss`). At or below the target, the measured insertion is accepted. The loop regenerates
budget_route/signoff/ff.sdc from the measured SS/FF mean/min/max plus the sheet's per-edge budgets, and records the
acceptance in `{CL}/calib.json` (`budget_accepted`). Every calibrated block's measured insertion is collected in
`results/rtl/budgets_20261006/measured_insertion.json` on main (published at most every 10 min) for the die
clock plan.

Variant-keyed insertion (bf-insertion 2026-10-08): `measured_insertion.json` also holds `variants{variant_key: entry}`
and every entry carries its `variant`. `variant_key(spec)` = block + recipe script + the insertion-relevant options of
the route cmd (`VAR=value` assignments such as BF_VAR / OT_CGL_FRAC / OT_MULTI_VT / OT_CTS_FIX_HOOKS / corner
overrides, `--param K=V`, other `--flags`; hold margin, paths and labels excluded). A parallel calibrate starts the route
on an assumed insertion ONLY from the same variant (old block entries count when the measuring job's JSON gives the same
key); otherwise the job calibrates first (CTS-only) and routes on the measurement. bfh_halfphl_a730 had started on
bfh_recutcgl50's SS 1169 / FF 714; the half-rate tree measured 1546 / 875.
At daemon start `backfill_variants()` adds every job's calibrate measurement taken before the table existed
(newest per variant; existing variant entries are never replaced), so a re-route of an older variant (e.g.
bfh2_recut_lvt, SS 951 / FF 556) starts on its own value instead of calibrating again.

## Hold margin and automatic hold ECO (2026-10-06)
- Jobs created from 2026-10-07 04:17 get `HM=0.010` (10 ps; coordinator: 35 ps + the 50 ps FF IO hold uncertainty
  overloaded CTS/GRT hold repair, RSZ-0060 buffer-cap deaths); the post-route hold ECO carries hold to +18.
- Jobs ingested from 2026-10-06 20:40 to 2026-10-07 04:17 get `HM=0.035` (route hold margin, ns, as route_view.sh reads it) exported
  to calibrate and route. Override it with spec `route_hold_margin_ns`, or with an inline `HM=` in the command.
- HOLD-ECO: when a verdict is hold-only (SS >= +15, DRC 0, all checks and benches OK, FF < +15), the loop runs
  `hold_eco.sh` / `hold_eco.tcl` before declaring NEEDS_RTL. The ECO is the hub recipe:
  - input is the routed pre-fill `5_2_route.odb`, with the sign-off `6_final.sdc` plus `verdict.post_sdc` and the
    `verdict.macros` views
  - RCX parasitics on the SS and FF scenes, then `repair_timing -hold` to +22 ps while keeping setup >= +25 ps
  - legalise, strip and re-route every signal and clock wire (keeping clock wires broke DRT once legalisation moved sinks), max 30 % buffers, fillers, re-extract, then sign off again with
    tools/w18/corner_sta.py
  - on a PASS (SS/FF >= +15, ECO DRC 0) the loop installs the ECO database in place of the route (originals kept
    as `*.pre_eco`), points the verdict's corner_sta at the ECO sign-off, re-exports the view (`hold_eco.reexport`,
    else hbm_fmax_attn_abstract.py when `<route>/view/<block>.lef` exists), and judges again
  - only a missed ECO goes NEEDS_RTL
  - tune with `hold_eco: {hold_margin_ps, setup_margin_ps, keep_clock, max_buffer_percent, reexport, enabled}`
- Earlier hold-only NEEDS_RTL jobs are re-opened once, unless the block already has a live or closed sibling job.

### Automatic VT-swap setup ECO (2026-10-09, merge-eco)
- A route whose only miss is a THIN TT setup miss -- TT in [-45, 0), FF >= 0, DRC 0, no failed check / bench / metric
  error -- runs `vtswap_eco.sh` / `vtswap_eco.tcl` (eco-sweep e494ff8ac) as its ECO stage before NEEDS_RTL: RVT->LVT
  master swaps on the worst TT paths, band-limited, prospective <= 2 % LVT cap, FF hold guard, no re-route (ASAP7 R/L
  footprints are identical, so the route DRC stands). Same stage tag / output layout as the hold ECO: the ECO completion
  installs, re-verdicts at the routed insertion and records it unchanged.
- Targets 10 ps, then (on a miss) once more at 5 ps (fewer swaps under the cap); then NEEDS_RTL. Each run keeps its own
  output (`cl/eco-vtswap-t<target>[-r<n>]`) and stage tag. Spec `hold_eco: {vtswap: false}` turns it off;
  `vtswap_targets`, `vtswap_cap_pct` override. `vtswap_launch.py` remains the manual launcher for an already NEEDS_RTL job.

### Hold ECO rev 2 (2026-10-07): the "ECO buffers destroy setup" class
Nine hold-only misses went NEEDS_RTL because the ECO took setup below +15. Causes found, and what rev 2 does:
- constraints differed from sign-off: corner-conditional post-SDCs (`vclk_corner_true.sdc`, budget FF files) were read
  once into a two-corner session, so the ECO applied the FF IO model to SS setup (idxq_b1: ECO SS -414.69 vs sign-off
  +107.23; 14,557 buffers). Rev 2 builds each corner's EFFECTIVE sign-off SDC in its own session (`hold_eco_corner.tcl`,
  corner_sta.py's read order, `write_sdc`), merges them (`hold_eco_sdc.py`: SS max side, FF min side, FF min IO delays
  shifted by the virtual-clock latency difference). Repair now defaults to an FF-only session protected by the SS
  session's endpoint slacks and critical nets. Matching the worst margins alone cannot exclude irrelevant SS hold
  endpoints (W2 NO3/hquad diagnosis). `ECO_SESSION=ff` makes this explicit; `hold_eco.session: "ff"` selects it in
  a job. `ECO_SESSION=auto` retains the legacy two-corner mismatch detection for explicitly requested experiments.
- the RE-ROUTE, not the buffers, destroyed setup: on ctrl_pc 3f0455126 a strip + fresh GRT + DRT with NO ECO cell took
  SS +70.18 -> +5.98 (FF -4.20 -> -2.06). Rev 2 keeps the route's GRT guides (still in 5_2_route.odb): incremental
  GRT around the repair re-guides only the touched nets, every wire is stripped, DRT routes on the original guides.
  The same no-ECO control then reproduces SS +70.18 / FF -4.20 exactly; with the ECO (293 cells) SS +73.02 / FF -4.20 ->
  +6.51 in one pass (the 2nd pass closes the residue). Keeping untouched WIRES does not work with this DRT ('pin not
  visited' on untouched nets), nor does keeping clock wires (checkConnectivity). Guide preservation is the preferred
  tested strategy, not an acceptance requirement. Missing/rejected guides fail the pass by default; an explicit
  `ALLOW_FRESH_GRT=1` (job `hold_eco.allow_fresh_grt: true`) permits fresh resistance-aware GRT. The result records
  the strategy and fallback reason in `route_strategy`. All unchanged strict timing, DRC, IO and context checks
  still apply. Historical `svc_SE_s6` eco-r3 is not rejected merely because it used fresh GRT.
- post-route hold GOAL +18 (coordinator 2026-10-07: margin over the +15 line for die context; was a +22 pre-route
  target that routed to anything); the repair aims +18 + an allowance (3 ps, then adds 1.5 times the previous pass's shortfall, capped at 20 ps)
  because the new buffers' nets are unrouted during the repair; acceptance stays +15. Only endpoints with SS setup > 2.4 x deficit + 40 ps are repaired (a ps of FF hold delay costs ~2.4 ps at
  SS; `hold_eco_window.tcl` prints every class as fixable / tight / infeasible / nodata: S - 2.4 (15 - H) < 15 means the
  constraints leave no window -> IO budget or RTL, never an ECO);
  `repair_timing -setup_margin 40`; HB1-4xp67 delay cells allowed; up to 2 passes ECO -> re-route -> corner_sta, the
  each starting from the original route. A failed later pass retains the best completed earlier pass.
- SS endpoint export includes `all_registers -data_pins`, covering macro timing-check pins as well as flop D pins
  and output ports. Missing SS data is `nodata` and excluded from repair, not evidence of an infeasible window.
  `test_hold_eco_macro_pins.py` covers this export and classification and the original-guide failure behavior.
- tune with `hold_eco: {hold_margin_ps, setup_margin_ps, setup_filter_ps, passes, resistance_aware, hold_cells, ...}`;
  `WINDOW_ONLY=1 hold_eco.sh ...` reports the endpoint windows without an ECO.
- `closure_loop.py retry-eco <name> [--why ...]` re-runs the ECO on a hold-only NEEDS_RTL job whose earlier ECO missed
  (earlier ECO kept in `eco_history`, new output `cl/eco-r<n>`).
- found on the way: tools/budgets/make_block_sdc.py `--route-mode signoff` put the sheet latency on the REAL clock;
  read after set_propagated_clock that made sign-off ideal-clock (hfd_svc_SE_s6 FF -135.15 -> -36.67 once propagated).
  Fixed: vclk only + `set_propagated_clock` on the real clock.

### Cancellation and ECO reliability (2026-10-06)

Job transitions and cancellation share a per-job file lock in `CL_STATE/job_locks`.
Workers reload state under that lock before any launch. `CANCELLED` is terminal even
for a stale ingest/requeue save; a new attempt needs a new job name. Cancellation
is persisted before remote termination, so an unreachable host cannot requeue it.
Use the same deployed version of the CLI and daemon to get this serialization.

`restore-cancelled <name>` repairs a cancellation overwritten by an older daemon.
It requires an explicit human cancellation in the ledger, archives the current job
JSON in `CL_STATE/cancel_recovery`, and prevents subsequent transitions. It neither
kills nor restarts remote processes; the preserved stage identity is recorded for
parent follow-up. It refuses an already CLOSED job.

The hold ECO takes its ordered post-SDC list from the measured sign-off record
(falling back to the spec only when that metadata is absent), and records that
list in job state. Non-finite/missing timing, STA errors, and failed repair cannot
pass installation. Existing ECO output directories are preserved rather than
removed. The hbglue failure and cancellation race evidence are in
`evidence/reliability_20261006.json`. Run the local regression vehicle with:

```
python3 -m unittest discover -s tools/closure_loop -p test_reliability.py -v
```

`recover-eco-overlays hbglue_cl_8ddc70024` is a narrowly scoped, one-shot recovery
for the recorded missing-overlay failure (-340500.58/-59.43 ps, zero cells).
It refuses other jobs, changed verdicts, installed ECOs, or a repeated request.
It verifies the pinned original ODB/SPEF/SDC and measured overlay hashes, archives
the failed state and original helper scripts, and hashes the entire failed ECO.
The new output is `cl/eco-overlay-recovery-a2/candidate`; the old `cl/eco` remains
untouched. The request resumes at verdict, retaining the original source and
bench evidence. Admission, sign-off, conditional re-export, re-verdict and
collection remain normal loop stages. Inputs are checked again before ECO and
installation. Legacy automatic ECO requeues cannot repeat this explicit attempt.

`python3 tools/closure_loop/rebind_index_budget.py --out receipt.json` replays the
immutable `ea6759434` index binding audit and validates the live b1/b3/b5 jobs.
Add `--apply` to archive their historical state, calibration and copied SDCs under
`cl/budget-rebind-ea6759434`, bind each complete hash-pinned `d05ac0e8` sheet, and
resume at route through normal admission. b0/b2 are excluded. Source and bench
proofs must match the audit snapshots. Rebound jobs retain their complete sheet
on later calibration, check both SS/FF boundary maxima, and refuse a digest
mismatch. Records remain component evidence; automatic integration-branch merge
is disabled for these three rebinds pending parent review.

## Launch immediately, in parallel (OWNER 2026-10-07 05:00)
- Benches run in a PARALLEL TRACK beside calibrate -> route (same host, one bench at a time, `<bench>.a<n>b<k>` tags).
  They gate adoption, not launch: the verdict waits until every bench has its expected verdict; a bench with the wrong
  verdict stops the job's running stage (route / calibrate / ECO) and ends the job NEEDS_RTL; a bench that crashes is
  retried once. Default for every job that had not started its first stage when this deployed; `"bench_first": true`
  in the spec keeps the old order (benches, then calibrate/route).
- Up to 3 routes per (block, source commit) (small + aggressive + half-rate variants together); was 1.
- localhost is a host (hosts.json): ORFS stages only, at most 24 loop threads in total (`max_loop_threads`) and
  MemAvailable >= job peak + 40 GB (`min_free_ram_gb`), so ssh stays responsive. Stages run directly, without ssh.
- New jobs route at hold margin 10 ps (see "Hold margin" above).

## Route-time hold corners (2026-10-07)
- Calibrate and route stages export `OT_ROUTE_HOLD_CORNERS=primary` and run `hold_corners_patch.py` on the job's snapshot (older
  snapshots get the same code main's tools/run_abi3_physical.py now has): place-and-route repairs setup and hold at the
  primary corner (WC) only. The recipes' one route SDC puts the virtual IO clock at the SS insertion, so at BC every
  IO path showed a fake hold violation of about the SS-FF insertion difference (hfd_svc_SE_s6 route SDC: output hold
  WC +106 / BC -121 ps) and the flow inserted thousands of hold buffers (SE_s6 7,531, SW_s4 5,939, ctrl_pc 11,732).
  FF hold is closed by the post-route hold ECO against the exact FF sign-off constraints; sign-off is unchanged.
  Spec `"route_hold_corners": "keep"` keeps the recipe's own `--hold-corners`; any other value is passed through.
- localhost incident (2026-10-07 05:20): recipes pinning the BARE image ID `sha256:16470cea...` failed there (exit 125):
  the same image has another ID in localhost's overlay2 store. localhost stages now export
  `OPENTALLAS_ORFS_IMAGE=openroad/orfs@sha256:16470cea...` (the registry digest resolves everywhere; the image's Yosys /
  OpenROAD binaries are byte-identical to the fleet's), and a job whose recipe hard-codes a bare ID is not placed there.
  hosts.json `smoke_only` admits only spec `"smoke": true` jobs (terminal status SMOKE_OK, nothing published);
  spec `host_require` pins a job to hosts.

### Hold ECO rev 3 (2026-10-07)
- Default session `mm` (multi-mode): scene ss = the SS effective sign-off SDC with hold false-pathed (SS libs), scene ff =
  the FF effective SDC with setup false-pathed (FF libs), the route's own SPEF, port loads re-applied per mode. It must
  reproduce sign-off (worst SS setup / FF hold within 1 ps) or the pass falls back to the FF-only session. repair_timing's
  `-setup_margin` then guards against REAL SS setup: dshead-ctl-r6 FF-only stacked six HB4 cells (SS +87.9 -> -335.7);
  mm: SS +16.0 / FF +17.1 after 2 passes; router dv12: SS +24.56 kept (+22.5 routed) while FF -8.6 -> +7.3 in pass 1.
- Only HB1/HB2 delay cells; post-repair setup guard: ECO cells on any SS path under the setup margin are removed.
- Macro-output net freeze exists (`OT_FREEZE_MACRO_NETS=1`) but is OFF: it corrupted the session on hbm_cmdproc_n.

### Preserved-wire fallback recovery (2026-10-07)
`hold_eco.sh` accepts `FREEZE=1` (macro-output nets) or `KEEPWIRES=1`
(untouched nets). Both remain off by default; physical benefit and stability are
not established. If detailed routing rejects preserved wires, the Tcl process
exits instead of attempting another detailed route in the damaged session. The
shell preserves the rejected log as `eco_<session>_kept.log` and output as
`base_kept`, then repeats from the original route in a fresh process with both
options disabled. SS/FF/DRC acceptance is unchanged. The local shell/Tcl fixture
covers session arguments, retained failure evidence, and the clean retry; it is
not physical validation of either wire-preservation option.

### Adoption holds and mutation benches (2026-10-07)
An owner can write `CL_STATE/adoption_holds/<job>.json` with a nonempty `reason`
to retain running physical work while blocking verdict, collection, export and
publication. Remove the hold only after its missing evidence is committed and
bound to the job; archive the hold and release evidence. Timing and exactness
requirements remain unchanged.
Newly launched bench stages execute in `bench_src_a<attempt>`, a private copy of
the job source shared only by its sequential bench stages. CWD, `$SRC`, `{SRC}`
and legacy `{RUN}/src` point there. Route stages retain their original `src`.
This prevents a negative control's in-place source mutation from racing synthesis.
Previously launched stages require an owner audit before adoption.
