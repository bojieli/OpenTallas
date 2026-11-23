#!/usr/bin/env python3
"""plan_advisory.py -- PRECHECK-R2 (COORD 11-22): static ADVISORY checks of a composed die plan + its bind inputs.

Owner rule 11-19: the precheck is an ESTIMATOR, never a gate.  Every line this module returns starts with "WARN ADV-<CHECK>";
plan_gate_pre.check() appends them (class ADVISORY, --skip ADVISORY or OT_PLAN_ADVISORY=off to leave out) and they never
change its verdict or exit code.  Each check found, on 11-22, a problem one build (about a day) late that the plan showed:

  CORE-PARAM       hard-core parameters the bind derives (e.g. KV ectl QK_ISSUE_AGE / RESPONSE_LAT from landed station depths)
                   differ from the parameters the signed core view was built with (KV D27d3+ ectl 42/31 vs signed qkd_ectlk 37/26)
  GHOST-MACRO      a placed macro / hard-core row of the plan with no instance in the bound RTL (S81 svc pvq_capture rows)
  SITE-COLLIDE     station / relay / START / reset sites crowding each other or a macro keep-out (HEAD w10 reader START ~(487,1370))
  PORT-WINDOW-PAIR the two ends of a die-level port pair no longer carry matching windows after a split / nudge (S81 J8 svc
                   rt_W0_out_1__6, rt_E0_out_0__5)
  DEPTH-VS-RTL     plan stage counts beyond what the RTL parameters allow (S81 istation_respace vs LF_CS_DEPTH: 102 bind errors)
  DENSITY          std-cell utilisation of a piece from the synth cell count > ~0.6 (S81 strip_S 0.91)
  TAP-BUDGET       estimated clock insertion of a pin-register cluster from its tap distance > 450 ps (S81 t5 / col 478-538 ps)
  TAP-LOAD         planned max tap load > 1.3x below the netlist flop estimate; placed tap load > 1,500 (S81 t5 1,099 vs 8,000)
  PORT-PIN         a wrapper port of the strict bind output with no planned pin (KV pv_v3e ri_pv_u_g1_j_rst_n: split piece without
                   its reset pin, died at place)
  MERGE-RESET-DEPTH core reset pins merged into one port whose delay rows carry different depths (OPUS-FIX-KV-HUB-R6)
  PATH-SEAT        a short pin-to-seat span whose path detours behind a macro (S81 leaf t15: 5 um span, 1,885 um path), and
                   planned paths over ~20 logic stages at 833 ps (lepw_mus_C 28)
  PHANTOM-STATION  a plan station row priced +N cycles on a lane with no stage register in the bound RTL (HEAD hd_lep0N e1/e2)

    python3 -I tools/die_plan/plan_advisory.py --plan PLAN.json [--tree TREE] [--checks A,B] [--json OUT]   (exit 0 always, 2 = bad input)
"""
import argparse
import importlib
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# (check name, module in this directory); a module absent from an older tree is skipped quietly
CHECKS = (("CORE-PARAM", "adv_core_param"), ("GHOST-MACRO", "adv_ghost_macro"), ("SITE-COLLIDE", "adv_site_collide"),
          ("PORT-WINDOW-PAIR", "adv_port_window_pair"), ("DEPTH-VS-RTL", "adv_depth_vs_rtl"), ("DENSITY", "adv_density"),
          ("TAP-BUDGET", "adv_tap_budget"), ("TAP-LOAD", "adv_tap_load"),
          ("PORT-PIN", "adv_port_pin"), ("MERGE-RESET-DEPTH", "adv_merge_reset_depth"), ("PATH-SEAT", "adv_path_seat"),
          ("PHANTOM-STATION", "adv_phantom_station"))
CHECK_TIMEOUT_S = int(os.environ.get("OT_PLAN_ADVISORY_TIMEOUT_S", "120"))
MAX_LINES = 25          # per check, plus its own summary line


class _Timeout(Exception):
    pass


def _alarm(_sig, _frm):
    raise _Timeout()


def _norm(name, lines):
    out = []
    for x in lines or []:
        x = str(x)
        if not x.strip() or x.startswith("#"):          # module debug / coverage lines
            continue
        if not x.startswith("WARN "):
            x = f"WARN ADV-{name} {x}"
        out.append(x)
    if len(out) > MAX_LINES + 1:
        out = out[:MAX_LINES] + [f"WARN ADV-{name} ... {len(out) - MAX_LINES} more line(s) (plan_advisory.py --checks {name} for all)"]
    return out


def run(raw, plan_path, tree=None, checks=None, skip=(), timing=None, cap=True, **kw):
    """WARN ADV-* lines of every check (never raises)."""
    if os.environ.get("OT_PLAN_ADVISORY", "").lower() == "off":
        return []
    skip = {s.upper() for s in skip or ()}
    want = {c.upper() for c in checks} if checks else None
    out = []
    sys.path.insert(0, str(HERE))
    try:
        for name, mod in CHECKS:
            if name in skip or (want is not None and name not in want):
                continue
            t0 = time.time()
            try:
                m = importlib.import_module(mod)
            except ImportError:
                continue
            main_thread = threading.current_thread() is threading.main_thread()
            old = None
            try:
                if main_thread and CHECK_TIMEOUT_S > 0:
                    old = signal.signal(signal.SIGALRM, _alarm)
                    signal.alarm(CHECK_TIMEOUT_S)
                lines = m.findings(raw, plan_path, tree=tree, **{k: v for k, v in kw.items() if v})
            except _Timeout:
                lines = [f"WARN ADV-{name} not checked: over {CHECK_TIMEOUT_S} s"]
            except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
                lines = [f"WARN ADV-{name} not checked: {type(e).__name__}: {str(e)[:200]}"]
            finally:
                if old is not None:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old)
            out += _norm(name, lines) if cap else [str(x) for x in lines or []]
            if timing is not None:
                timing[name] = round(time.time() - t0, 2)
    finally:
        try:
            sys.path.remove(str(HERE))
        except ValueError:
            pass
    return out


def summary(lines):
    """'ADV-X n, ADV-Y m' over finding lines (not-checked / summary lines excluded)"""
    n = {}
    for x in lines:
        f = x.split()
        if len(f) > 2 and f[1].startswith("ADV-") and f[2] not in ("not", "...") and not f[2].startswith("summary"):
            n[f[1]] = n.get(f[1], 0) + 1
    return ", ".join(f"{k} {v}" for k, v in n.items())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="plan_advisory", description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--tree")
    ap.add_argument("--checks", default="")
    ap.add_argument("--asbuilt")
    ap.add_argument("--bind-out")
    ap.add_argument("--baseline", help="base plan (changed-lane scope, e.g. PHANTOM-STATION)")
    ap.add_argument("--json")
    ap.add_argument("--all", action="store_true", help="no per-check line cap")
    a = ap.parse_args(argv)
    try:
        raw = json.loads(Path(a.plan).read_text())
    except (OSError, ValueError) as e:
        print(f"plan_advisory: cannot read {a.plan}: {e}", file=sys.stderr)
        return 2
    tm = {}
    lines = run(raw, a.plan, a.tree, [c for c in a.checks.split(",") if c] or None, timing=tm, cap=not a.all,
                asbuilt=a.asbuilt, bind_out=a.bind_out, baseline=a.baseline)
    for x in lines:
        print(x)
    print(f"PLAN-ADVISORY plan={a.plan} lines={len(lines)} ({summary(lines) or 'no findings'}) seconds={tm}")
    if a.json:
        Path(a.json).write_text(json.dumps({"plan": a.plan, "tree": a.tree, "advisories": lines, "seconds": tm}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
