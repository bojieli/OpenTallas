#!/usr/bin/env python3
"""KVG3-CORES: collect one finished KV core kit run into the record + the view layout cores.find_views() expects.

    python3 collect_core.py KITDIR [--host HOST:DIR] [--repo ~/wt/kv-g3] [--no-views]

KITDIR = a local copy of the kit (rsync the run back first: run/logs, run/reports, run/results/*.lef|*.odb not needed,
views/, pin_audit.json, sdc_lint.log, face_guard.json, freeze.json).  Writes
  physical/ref_tile/<module>/views/<module>/{<module>.lef, <module>_tt.lib, <module>_ff.lib, <module>_ss.lib}
  physical/die_plan/qwen_kvsys/cores/harden/results/<module>.json
Verdict: PASS only if route DRC 0, GRT overflow 0, pin audit PASS, setup WNS >= 0 at SS (sign-off corner, AGENTS.md),
hold WNS >= 0 at FF; TT-only closure is recorded as TT pathfinding.  A FAIL still publishes the views, marked
abstract_only (usable as placement abstracts, not as timing sign-off).  An existing FAIL record is never overwritten
by a later run: the later run gets <module>.<kit_hash>.json.
"""
import argparse
import glob
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def metrics(kd):
    m = {}
    for f in sorted(glob.glob(f"{kd}/run/logs/asap7/*/base/*.json")):
        d = jload(f)
        if isinstance(d, dict):
            m.update(d)
    return m


def pick(m, *pats):
    for p in pats:
        for k, v in m.items():
            if re.fullmatch(p, k):
                return v
    return None


def grep_last(path, rx):
    v = None
    try:
        for ln in open(path, errors="replace"):
            mm = re.search(rx, ln)
            if mm:
                v = mm.group(1)
    except OSError:
        pass
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kitdir")
    ap.add_argument("--host", default="")
    ap.add_argument("--repo", default=str(HERE.parents[4]))
    ap.add_argument("--no-views", action="store_true")
    a = ap.parse_args()
    kd = Path(a.kitdir)
    fz = json.load(open(kd / "freeze.json"))
    mod = fz["module"]
    m = metrics(kd)
    sta = {c: jload(kd / "views" / f"sta_{c}.json") for c in ("tt", "ff", "ss")}
    pa = jload(kd / "pin_audit.json") or {}
    synth_cells = None
    st = kd / "run" / "reports" / "asap7"
    for f in glob.glob(f"{st}/*/base/synth_stat.txt"):
        v = grep_last(f, r"^\s*([0-9]+)\s+[0-9.]+\s+cells$") or grep_last(f, r"Number of cells:\s+([0-9]+)")
        synth_cells = int(v) if v else None
    rec = dict(schema="opentallas.kv.core_harden.v1", module=mod, kit=fz["type"], kit_hash=fz["kit_hash"],
               run=a.host or str(kd), outline_um=fz["outline_um"], pins=fz["pins"], plan_pins=fz["plan_pins"],
               added_pins=fz["added_pins"], clocks=fz["clocks"], macros=fz["macros"],
               period_ps=fz["period_ps"], insertion_budget_ps=fz["insertion_budget_ps"],
               sdc_lint=(open(kd / "sdc_lint.log").read().strip().splitlines() or ["?"])[-1] if (kd / "sdc_lint.log").exists() else "NOT RUN",
               face_guard_report_only=(jload(kd / "face_guard.json") or {}).get("verdict"),
               synth_cells=synth_cells,
               instances=pick(m, r"finish__design__instance__count", r"detailedplace__design__instance__count"),
               std_util=pick(m, r"finish__design__instance__utilization", r"detailedplace__design__instance__utilization"),
               grt_overflow=pick(m, r"globalroute__route__overflow.*", r"globalroute__.*overflow.*"),
               drc=pick(m, r"detailedroute__route__drc_errors", r"finish__route__drc_errors"),
               antenna=pick(m, r"detailedroute__antenna__violating__nets", r"finish__antenna.*"),
               pin_audit=f"{pa.get('verdict', 'NOT RUN')} {pa.get('ok', 0)}/{pa.get('pins', 0)}",
               sta=sta)
    views = kd / "views"
    lef = next(iter(sorted(views.glob(f"{mod}.lef"))), None)
    libs = {c: views / f"{mod}_{c}.lib" for c in ("tt", "ff", "ss")}
    ok_route = rec["drc"] == 0 and rec["grt_overflow"] in (0, None) and pa.get("verdict") == "PASS"
    ss, ff, tt = sta.get("ss") or {}, sta.get("ff") or {}, sta.get("tt") or {}
    setup_ss = ss.get("setup_ws_ps")
    hold_ff = ff.get("hold_ws_ps")
    if not lef or not all(p.is_file() for p in libs.values()) or not sta["tt"]:
        verdict = "INCOMPLETE (views / corner STA missing)"
    elif ok_route and setup_ss is not None and setup_ss >= 0 and hold_ff is not None and hold_ff >= 0:
        verdict = "PASS (setup SS, hold FF, DRC 0, pin audit PASS)"
    elif ok_route and tt.get("setup_ws_ps", -1) >= 0 and tt.get("hold_ws_ps", -1) >= 0:
        verdict = f"FAIL sign-off (TT closes = pathfinding only; SS setup WS {setup_ss} ps, FF hold WS {hold_ff} ps)"
    else:
        verdict = (f"FAIL (DRC {rec['drc']}, GRT ovf {rec['grt_overflow']}, pins {rec['pin_audit']}, "
                   f"TT setup WS {tt.get('setup_ws_ps')} / SS {setup_ss}, FF hold WS {hold_ff})")
    rec["verdict"] = verdict
    rec["views_status"] = "signoff" if verdict.startswith("PASS") else "abstract_only (timing not closed)"
    repo = Path(a.repo)
    if lef and not a.no_views:
        vd = repo / "physical" / "ref_tile" / mod / "views" / mod
        vd.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(lef, vd / f"{mod}.lef")
        for c, p in libs.items():
            if p.is_file():
                shutil.copyfile(p, vd / f"{mod}_{c}.lib")
        for c in ("tt", "ff", "ss"):
            for f in (f"sta_{c}.json", f"sta_{c}_max.rpt", f"sta_{c}_min.rpt"):
                if (views / f).is_file():
                    shutil.copyfile(views / f, vd / f)
        (vd / "provenance.json").write_text(json.dumps(dict(kit=fz, verdict=verdict, views_status=rec["views_status"]),
                                                       indent=1) + "\n")
        rec["views"] = str(vd.relative_to(repo))
    rd = HERE / "results"
    rd.mkdir(exist_ok=True)
    out = rd / f"{mod}.json"
    old = jload(out)
    if old and str(old.get("verdict", "")).startswith("FAIL") and old.get("kit_hash") != rec["kit_hash"]:
        out = rd / f"{mod}.{rec['kit_hash']}.json"     # failed verdicts are never overwritten
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(module=mod, verdict=verdict, synth_cells=synth_cells, drc=rec["drc"],
                          grt_overflow=rec["grt_overflow"], pin_audit=rec["pin_audit"],
                          tt=(tt.get("setup_ws_ps"), tt.get("hold_ws_ps")), ff=(ff.get("setup_ws_ps"), hold_ff),
                          ss=(setup_ss, ss.get("hold_ws_ps")), record=str(out))))


if __name__ == "__main__":
    main()
