#!/usr/bin/env python3
"""hgi-1010/h (2026-10-10): report of a tb_hgi_e2e MTP run (the DS DSpark job through the die).

Launch spans: the translator's KERNEL completions (run.log 'E2E KCPL i cyc c') in the order of the simulator's launch
list (ds_mtp_kernels sim launches.json); launch i's RTL span = c_i - c_{i-1} (job start for i = 0) against the
simulator's S2 cycles of that body.  Per L0 column: the span and every unit.op's RTL busy (dispatch -> retire) against
the simulator's unit price; exactness = the harness's per-record checks (real units) + its final VM / HBM compare.

    python3 -m hgi_e2e.mtp_report RUN_DIR LAUNCHES_JSON [--out REPORT.json]      (from tools/)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from hgi_e2e import run as RUN  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("launches", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    base = RUN.report(a.run, None)
    log = (a.run / "run.log").read_text(errors="replace")
    kc = [int(m.group(1)) for m in re.finditer(r"E2E KCPL \d+ cyc (\d+)", log)]
    emits = [int(m.group(1)) for m in re.finditer(r"E2E MTP emit \d+ token (\d+)", log)]
    done = re.search(r"E2E MTP host done: (.*)", log)
    L = json.loads(a.launches.read_text())
    spans = []
    prev = 0
    for i, e in enumerate(L):
        if i >= len(kc):
            break
        spans.append(dict(i=i, kind=e["kind"], Lp=e["Lp"], pos=e["pos"], token=e["token"], rtl=kc[i] - prev,
                          sim=e["s2_cycles"]))
        prev = kc[i]
    # records of each launch in dispatch order (non-CTL records per launch from the simulator)
    recs = base["records"]
    j = 0
    l0 = []
    for i, e in enumerate(L):
        n = e["records"]
        mine = recs[j:j + n]
        j += n
        if e["kind"] == "layer" and e["Lp"] == 0 and mine:
            per = defaultdict(lambda: dict(n=0, rtl_busy=0, sim=0.0, real=0, exact=0))
            for r in mine:
                p = per[r["unit"]]
                p["n"] += 1
                p["rtl_busy"] += max(0, r["ret"] - r["disp"]) if r["ret"] >= 0 and r["disp"] >= 0 else 0
                p["sim"] += r["cost"]
                p["real"] += r["real"]
                p["exact"] += int(r["real"] and r["mismatch"] == 0 and r["stray"] == 0)
            sp = next((s for s in spans if s["i"] == i), None)
            l0.append(dict(pos=e["pos"], token=e["token"], records=len(mine),
                           first_dispatch=min(r["disp"] for r in mine), last_retire=max(r["ret"] for r in mine),
                           launch_rtl=sp and sp["rtl"], launch_sim=e["s2_cycles"],
                           per_unit={k: dict(v, sim=round(v["sim"], 1)) for k, v in per.items()}))
    by = defaultdict(lambda: dict(n=0, rtl=0, sim=0.0))
    for s in spans:
        k = s["kind"] + ("0" if s["kind"] == "layer" and s["Lp"] == 0 else "")
        by[k]["n"] += 1
        by[k]["rtl"] += s["rtl"]
        by[k]["sim"] += s["sim"]
    out = dict(schema="opentallas.hgi_e2e.mtp_report.v1", pass_=base["pass_"], summary=base["summary"],
               emitted=emits, host_done=done.group(1) if done else None, launches_completed=len(kc),
               launches_expected=len(L), job_rtl_cycles=kc[-1] if kc else None,
               job_sim_cycles=round(sum(e["s2_cycles"] for e in L), 1),
               by_kind={k: dict(v, sim=round(v["sim"], 1), ratio=round(v["rtl"] / v["sim"], 3) if v["sim"] else None)
                        for k, v in by.items()},
               l0_columns=l0, per_unit_all=base["per_unit"], rtl_lines=base["rtl_lines"][-40:])
    txt = json.dumps(out, indent=1, default=int) + "\n"
    if a.out:
        a.out.write_text(txt)
    print(json.dumps({k: v for k, v in out.items() if k not in ("l0_columns", "per_unit_all", "rtl_lines")},
                     indent=1, default=int))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
