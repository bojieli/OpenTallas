#!/usr/bin/env python3
"""KVG3-CORES: collect one finished KV core kit run into the record + the view layout cores.find_views() expects.

    python3 collect_core.py KITDIR [--host HOST:DIR] [--repo ~/wt/kv-g3] [--no-views]

KITDIR = a local copy of the kit (rsync the run back first: run/logs, run/reports, run/results/*.lef|*.odb not needed,
views/, pin_audit.json, sdc_lint.log, face_guard.json, freeze.json).  Writes
  physical/ref_tile/<module>/views/<module>/{<module>.lef, <module>_tt.lib, <module>_ff.lib, <module>_ss.lib}
  physical/die_plan/qwen_kvsys/cores/harden/results/<module>.json
Verdict (coordinator 10-24): the kit's tools/die_plan/signoff.py record KIT/signoff/signoff.json decides -- closed only
when it says SIGNED (TT setup / FF hold, DRV, spread, sdc_lint, face_guard, DRC, antenna); the pin audit must also PASS.
No signoff.json = NOT SIGNED (signoff NOT RUN).  A FAIL still publishes the views, marked
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


def contract_reeval(kd, so):
    """A signoff.json written before the kit carried the hard-core latency contract (signoff.py befed6a747) judged the
    core's internal insertion against the partition-tap target 250 +- 40.  When the kit now carries the typed contract
    (core.json clock_contract kind hard_core_latency), re-evaluate the SAME measured record with signoff.evaluate()
    without the insertion target (spread / unique arrival still gate) and publish core_latency, as signoff.py run
    does.  The original record is kept as signoff.pre_contract.json (failed verdicts are never overwritten)."""
    if not so or so.get("core_latency"):
        return so
    import sys
    sys.path.insert(0, str(HERE.parents[4] / "tools" / "die_plan"))
    import signoff
    cc = signoff.hard_core_latency_contract(dict(kit=str(kd)))
    if not cc:
        return so
    pre = kd / "signoff" / "signoff.pre_contract.json"
    if not pre.exists():
        shutil.copyfile(kd / "signoff" / "signoff.json", pre)
    rec = json.loads(json.dumps(so))
    signoff.evaluate(rec, None)
    rec["core_latency"] = dict(contract=cc, measured={c: v.get("insertion_pinflops") for c, v in rec["corners"].items()
                                                      if v.get("done")})
    rec["checks"]["clock"]["core_latency_contract"] = cc.get("kind")
    rec["contract_reevaluated"] = dict(by="collect_core.py (KV-CORES 10-24)", pre_contract_verdict=so.get("verdict"),
                                       pre_contract_reasons=so.get("reasons"), original="signoff.pre_contract.json")
    (kd / "signoff" / "signoff.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


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
               grt_overflow=pick(m, r"globalroute__route__overflow", r"globalroute__route__overflow__total"),   # never *_iterations_s (a runtime)
               drc=pick(m, r"detailedroute__route__drc_errors", r"finish__route__drc_errors"),
               antenna=pick(m, r"detailedroute__antenna__violating__nets", r"finish__antenna.*"),
               pin_audit=f"{pa.get('verdict', 'NOT RUN')} {pa.get('ok', 0)}/{pa.get('pins', 0)}",
               sta=sta)
    if len(fz.get("clocks") or []) > 1:
        rec["clock_assumption"] = ("LABELLED ASSUMPTION: clocks " + " ".join(fz["clocks"]) + " co-timed as one 833 ps clock "
                                   "(plan has no HBM clock period; pending KV-G3)")
    views = kd / "views"
    lef = next(iter(sorted(views.glob(f"{mod}.lef"))), None)
    libs = {c: views / f"{mod}_{c}.lib" for c in ("tt", "ff", "ss")}   # SS: information only
    ok_route = rec["drc"] == 0 and rec["grt_overflow"] in (0, None) and pa.get("verdict") == "PASS"
    ss, ff, tt = sta.get("ss") or {}, sta.get("ff") or {}, sta.get("tt") or {}
    setup_ss = ss.get("setup_ws_ps")
    hold_ff = ff.get("hold_ws_ps")
    so = jload(kd / "signoff" / "signoff.json") or {}
    so = contract_reeval(kd, so)
    rec["signoff"] = dict(verdict=so.get("verdict", "NOT RUN"), reasons=so.get("reasons"),
                          checks={k: v.get("verdict") if isinstance(v, dict) else v for k, v in (so.get("checks") or {}).items()})
    if not lef or not all(libs[c].is_file() for c in ("tt", "ff")) or not sta["tt"]:
        verdict = "INCOMPLETE (views / corner STA missing)"
    elif so.get("verdict") == "SIGNED" and ok_route:
        verdict = "SIGNED (signoff.py; pin audit PASS)"
    else:
        verdict = (f"NOT SIGNED (signoff {so.get('verdict', 'NOT RUN')}; DRC {rec['drc']}, GRT ovf {rec['grt_overflow']}, "
                   f"pins {rec['pin_audit']}, TT setup WS {tt.get('setup_ws_ps')}, FF hold WS {hold_ff})")
    rec["verdict"] = verdict
    rec["views_status"] = "signoff" if verdict.startswith("SIGNED") else "abstract_only (not SIGNED)"
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
        cj = jload(kd / "core.json")
        if cj is not None:          # the hard-core contract the parent consumes, with the measured insertion
            cj["clock_latency_measured"] = (so.get("core_latency") or {}).get("measured") or {
                c: (sta.get(c) or {}).get("insertion") for c in ("tt", "ff")}
            (vd / f"{mod}.core.json").write_text(json.dumps(cj, indent=1) + "\n")
        (vd / "provenance.json").write_text(json.dumps(dict(kit=fz, verdict=verdict, views_status=rec["views_status"]),
                                                       indent=1) + "\n")
        rec["views"] = str(vd.relative_to(repo))
    rd = HERE / "results"
    rd.mkdir(exist_ok=True)
    out = rd / f"{mod}.json"
    old = jload(out)
    if old and not str(old.get("verdict", "")).startswith(("SIGNED", "INCOMPLETE")) and old.get("kit_hash") != rec["kit_hash"]:
        out = rd / f"{mod}.{rec['kit_hash']}.json"     # failed verdicts are never overwritten
    elif old and old.get("run") != rec["run"] and not str(old.get("verdict", "")).startswith("SIGNED"):
        # same kit, a later run of it (e.g. a post-route ECO): the earlier record is kept under a new name, never lost
        n = 1
        while (rd / f"{mod}.prev{n}.json").exists():
            n += 1
        (rd / f"{mod}.prev{n}.json").write_text(json.dumps(old, indent=1) + "\n")
        so_old = rd / f"{mod}.signoff.json"
        if so_old.exists():
            (rd / f"{mod}.prev{n}.signoff.json").write_text(so_old.read_text())
        rec["previous_record"] = f"{mod}.prev{n}.json"
    out.write_text(json.dumps(rec, indent=1) + "\n")
    if so and out.name == f"{mod}.json":
        (rd / f"{mod}.signoff.json").write_text(json.dumps(so, indent=1) + "\n")
    print(json.dumps(dict(module=mod, verdict=verdict, synth_cells=synth_cells, drc=rec["drc"],
                          grt_overflow=rec["grt_overflow"], pin_audit=rec["pin_audit"],
                          tt=(tt.get("setup_ws_ps"), tt.get("hold_ws_ps")), ff=(ff.get("setup_ws_ps"), hold_ff),
                          ss=(setup_ss, ss.get("hold_ws_ps")), record=str(out))))


if __name__ == "__main__":
    main()
