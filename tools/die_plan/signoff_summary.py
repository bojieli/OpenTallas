#!/usr/bin/env python3
"""Lane SIGNOFF summary: inventory (signoff_inventory.py) + signoff.py records -> per-die SIGNED / NOT SIGNED /
NEEDS RE-RUN lists.

    python3 tools/die_plan/signoff_summary.py --inventory results/signoff_1024/inventory.json \
        --runs results/signoff_1024/runs --out results/signoff_1024/summary.json [--lanes-md DIR]

A closed module whose routed DB is gone is NEEDS RE-RUN.  Its last record is still screened on paper against the
uniform standard (recorded pin-flop spread at TT / FF <= 80 ps, recorded SS setup / FF hold >= 0, DRC 0): a paper
FAIL means the block cannot be re-signed by re-running its STA alone, it needs a re-close.  Runs signed here that are
not closed blocks of a plan (partition / in-flight runs) are listed under `other_runs`.
"""
import argparse
import json
from pathlib import Path

SPREAD_MAX = 80.0


def _n(x):
    return len(x) if isinstance(x, (list, dict)) else x


def paper_screen(rec):
    if not rec:
        return dict(verdict="NO RECORD", problems=["no closed record in the repo"])
    p = []
    for c in ("tt", "ff"):
        v = rec.get(f"spread_{c}_ps")
        if v is not None and v > SPREAD_MAX:
            p.append(f"recorded {c.upper()} pin-flop spread {v:.1f} ps > 80")
    if rec.get("cl_ss_ps") is not None and rec["cl_ss_ps"] < 0:
        p.append(f"recorded SS setup {rec['cl_ss_ps']:+.2f} ps")
    if rec.get("cl_ff_ps") is not None and rec["cl_ff_ps"] < 0:
        p.append(f"recorded FF hold {rec['cl_ff_ps']:+.2f} ps")
    if rec.get("cl_drc"):
        p.append(f"recorded DRC {rec['cl_drc']}")
    if rec.get("spread_tt_ps") is None and rec.get("spread_ff_ps") is None:
        p.append("no recorded pin-flop spread (insertion.json missing)")
    return dict(verdict="FAIL" if any("spread" in x and ">" in x or "setup" in x or "hold" in x or "DRC" in x
                                      for x in p) else ("INCOMPLETE" if p else "PASS"), problems=p)


def run_row(sj):
    r = json.loads(Path(sj).read_text())
    C = r["checks"]
    pf = {c: ((((C.get("clock") or {}).get("by_corner") or {}).get(c) or {}).get("pinflops") or {}).get("spread")
          for c in ("ss", "tt", "ff")}
    return dict(name=r["name"], verdict=r["verdict"], reasons=r["reasons"], host=r.get("host"),
                base=r["inputs"]["base"], sdc_source=r["inputs"]["sdc_source"],
                ss_setup_wns_ps=C["setup_ss"].get("wns_ps"), ss_setup_violators=C["setup_ss"].get("violators"),
                ff_hold_wns_ps=C["hold_ff"].get("wns_ps"), ff_hold_sdc_wns_ps=C["hold_ff"].get("sdc_wns_ps"),
                tt_setup_wns_ps=C["tt"].get("setup_wns_ps"), tt_hold_wns_ps=C["tt"].get("hold_wns_ps"),
                pinflop_spread_ps=pf, drv=(C.get("drv") or {}).get("by_corner"),
                unconstrained=(C.get("unconstrained") or {}).get("counts"),
                sdc_lint=C["sdc_lint"].get("verdict"), sdc_lint_errors=C["sdc_lint"].get("n_errors"),
                face_guard=C["face_guard"].get("verdict"), face_guard_fails=C["face_guard"].get("fail_counts"),
                drc=C["drc"].get("count"), antenna=C["antenna"].get("count"),
                record=str(sj))


def build(inv, runs_dir):
    runs = {}
    for sj in sorted(Path(runs_dir).glob("*/signoff.json")):
        row = run_row(sj)
        runs[row["name"]] = row
    mods = inv["modules"]
    dies = {}
    used = set()
    for die, dv in inv["dies"].items():
        rows = []
        for m in sorted(mods):
            v = mods[m]
            if die not in (v.get("dies") or {}):
                continue
            rec = v.get("record") or {}
            row = dict(module=m, instances=v["dies"][die].get("instances"), types=v["dies"][die].get("types"),
                       kit=v.get("kit"), kit_in_repo=v.get("kit_in_repo"), recorded_db=v.get("recorded_db"),
                       db_status=v.get("db_status"),
                       recorded=dict(ss_setup_ps=rec.get("cl_ss_ps"), ff_hold_ps=rec.get("cl_ff_ps"),
                                     drc=rec.get("cl_drc"), spread_tt_ps=rec.get("spread_tt_ps"),
                                     spread_ff_ps=rec.get("spread_ff_ps"), ins_tt_ps=rec.get("ins_tt_ps"),
                                     closed_at=rec.get("cl_closed_at"), gate_verdict=rec.get("gate_verdict")),
                       paper=paper_screen(rec), notes=(v.get("notes") or [])[:4])
            if m in runs:
                used.add(m)
                row.update(status=runs[m]["verdict"], signoff=runs[m])
            elif v.get("status") == "DATA":
                row.update(status="DATA, NOT RUN")
            else:
                row.update(status="NEEDS RE-RUN")
            rows.append(row)
        cnt = {}
        for r in rows:
            cnt[r["status"]] = cnt.get(r["status"], 0) + 1
        pf = sum(1 for r in rows if r["status"] == "NEEDS RE-RUN" and r["paper"]["verdict"] == "FAIL")
        dies[die] = dict(plan=dv.get("plan"), extra=dv.get("extra", False), counts=cnt,
                         needs_rerun_paper_fail=pf, not_closed=_n(dv.get("not_closed")), macros=_n(dv.get("macros")),
                         modules=rows)
    other = [r for n, r in runs.items() if n not in used]
    return dict(schema="opentallas.signoff.summary.v1", inventory_generated=inv.get("generated"),
                main_commit=inv.get("main_commit"), dies=dies, other_runs=other,
                totals=dict(closed_modules=len(mods),
                            signed=sum(1 for d in dies.values() for r in d["modules"] if r["status"] == "SIGNED"),
                            not_signed=sum(1 for d in dies.values() for r in d["modules"]
                                           if r["status"] == "NOT SIGNED"),
                            needs_rerun=len({r["module"] for d in dies.values() for r in d["modules"]
                                             if r["status"] == "NEEDS RE-RUN"}),
                            other_runs=len(other), other_runs_signed=sum(1 for r in other if r["verdict"] == "SIGNED")))


def die_md(die, d):
    L = [f"### {die} ({d['plan']})", "",
         f"counts {d['counts']}; NEEDS RE-RUN whose last record already fails the standard on paper: "
         f"{d['needs_rerun_paper_fail']}; not-closed plan cores (not counted): {d['not_closed']}", "",
         "| module | inst | status | rec SS setup | rec FF hold | rec spread TT/FF | kit in repo | paper |",
         "|---|---|---|---|---|---|---|---|"]
    for r in d["modules"]:
        rc = r["recorded"]

        def f(x):
            return "-" if x is None else f"{x:g}"
        L.append(f"| {r['module']} | {r['instances']} | {r['status']} | {f(rc['ss_setup_ps'])} | "
                 f"{f(rc['ff_hold_ps'])} | {f(rc['spread_tt_ps'])}/{f(rc['spread_ff_ps'])} | "
                 f"{'yes' if r['kit_in_repo'] else 'NO'} | {r['paper']['verdict']}"
                 f"{(': ' + '; '.join(r['paper']['problems'])) if r['paper']['problems'] else ''} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--md")
    a = ap.parse_args(argv)
    s = build(json.loads(Path(a.inventory).read_text()), a.runs)
    Path(a.out).write_text(json.dumps(s, indent=1) + "\n")
    if a.md:
        Path(a.md).write_text("\n".join(die_md(k, v) for k, v in s["dies"].items()))
    print(json.dumps(s["totals"]))
    for k, v in s["dies"].items():
        print(f"{k:14s} {v['counts']} paper-fail {v['needs_rerun_paper_fail']}")
    for r in s["other_runs"]:
        print(f"other {r['name']}: {r['verdict']} SS {r['ss_setup_wns_ps']} FF {r['ff_hold_wns_ps']} "
              f"TT {r['tt_setup_wns_ps']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
