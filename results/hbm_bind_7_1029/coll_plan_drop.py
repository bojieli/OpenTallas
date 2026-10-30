#!/usr/bin/env python3
"""HBM-BIND-7 (HBM-035, COORD/OWNER precedent HBM-034 'plan follows source'): drop the duplicate PATH-HBM-R9
service-quadrant copy of every hub collective cut part (reduce / ring_ag / body_n2|body_core / vm / edge) so that each
hub carries ONE coll part set, as the source has ONE hb_coll_NE / hb_coll_NW parent.  All parts of a hub keep the SAME
copy (one collective: its internal reduce<->body<->vm<->edge stations stay local); the copy is chosen by locality
(fewest added station registers, then shortest moved length; report of both candidates).

Uses results/die_hbm_1029/hbm19/drop_dup_copies.py unchanged, then removes what that tool does not handle:
  * plan stations whose launch/capture names the dropped copy explicitly (<fam>__q1.<pin>): the PATH-HBM-R9 segment
    combine-chain link r9tree body q0 -> q1 (824 b), which has no source counterpart (one body per hub);
  * clock taps named <dropped>.<pin> (drop_dup_copies removes only taps named exactly <dropped>).
Fails closed if any other reference to a dropped instance remains in the plan.
usage: coll_plan_drop.py PLAN_DIR OUT_DIR --keep q0|q1 [--tools TOOLS_DIE_PLAN]"""
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

FAMS = ["u_hb_coll_Q_reduce", "u_hb_coll_Q_ring_ag", "u_hb_coll_Q_body_n2", "u_hb_coll_Q_body_core",
        "u_hb_coll_Q_vm", "u_hb_coll_Q_edge"]


def strings(x, key=None):
    """every string value of the plan object except free-text 'note' fields"""
    if isinstance(x, dict):
        for k, v in x.items():
            if k != "note":
                yield from strings(v, k)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)
    elif isinstance(x, str):
        yield x


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_dir"); ap.add_argument("out_dir")
    ap.add_argument("--keep", required=True, choices=("q0", "q1"))
    ap.add_argument("--repo", required=True)
    a = ap.parse_args(argv)
    repo = Path(a.repo)
    spec = importlib.util.spec_from_file_location("ddc", repo / "results/die_hbm_1029/hbm19/drop_dup_copies.py")
    D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
    rep = D.run(a.plan_dir, a.out_dir, FAMS, a.keep, ("q_hub_ne", "q_hub_nw"), repo / "tools/die_plan")
    out = Path(a.out_dir)
    P = json.loads((out / "die_plan.json").read_text())
    extra = {}
    for tn, fs in rep["hubs"].items():
        t = P["partition_types"][tn]
        dropped = [st["dropped"] for st in fs.values() if "dropped" in st]
        hit = lambda n: any(n == d or n.startswith(d + ".") for d in dropped)
        rm = [s for s in t["internal_stations"] if hit(s.get("launch", "")) or hit(s.get("capture", ""))]
        t["internal_stations"] = [s for s in t["internal_stations"] if s not in rm]
        ck = t.get("clock", {})
        taps = [x for x in ck.get("taps", []) if hit(x.get("name", ""))]
        ck["taps"] = [x for x in ck.get("taps", []) if x not in taps]
        extra[tn] = dict(dropped=dropped,
                         stations_removed=[dict(conn=s.get("conn"), launch=s["launch"], capture=s["capture"],
                                                bits=s.get("bits"), regs=len(s.get("regs_um", []))) for s in rm],
                         taps_removed=[x["name"] for x in taps])
        left = sorted({d for d in dropped for v in strings(t) if d in v})
        if left:
            raise SystemExit(f"{tn}: dropped copies still referenced: {left}")
    P["note"] = P.get("note", "") + f" | HBM-BIND-7 coll plan follows source (HBM-035): keep {a.keep}, combine-chain + dangling taps removed"
    txt = json.dumps(P, indent=1)
    (out / "die_plan.json").write_text(txt)
    rep["hbm_bind_7"] = extra
    rep["plan_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    (out / "drop_dup_report.json").write_text(json.dumps(rep, indent=1))
    tot = {}
    for tn, fs in rep["hubs"].items():
        s = [st for st in fs.values() if "kept" in st]
        tot[tn] = dict(stations_moved=sum(x["stations_moved"] for x in s), regs_added=sum(x["regs_new"] - x["regs_old"] for x in s),
                       max_latency_up=max([int(k) for x in s for k in x["latency_up_hist"]] or [0]),
                       stations_latency_up=sum(x["latency_up"] for x in s), dup_removed=sum(x["duplicates_removed"] for x in s),
                       length_new_um=round(sum(x["length_new_um"] for x in s), 1),
                       extra_stations_removed=len(extra[tn]["stations_removed"]), extra_taps_removed=len(extra[tn]["taps_removed"]))
    print(json.dumps(dict(keep=a.keep, totals=tot, plan_sha256=rep["plan_sha256"][:12])))


if __name__ == "__main__":
    main()
