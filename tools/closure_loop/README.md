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

## Hold margin and automatic hold ECO (2026-10-06)
- Jobs ingested from 2026-10-06 20:40 get `HM=0.035` (route hold margin, ns, as route_view.sh reads it) exported
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
