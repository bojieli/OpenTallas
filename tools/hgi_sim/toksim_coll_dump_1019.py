#!/usr/bin/env python3
"""TOKSIM-HBM-coll (10-19): per-record dump of every COLL record of the LH-REPRICE3 census schedule (the census tool's
jobs, unchanged): job, tag, layer, op, shape key, model cost, S2 start/end, and the record's compiled base_cost.
    PYTHONPATH=<census src>/tools python3 toksim_coll_dump_1019.py OUT.json [ONLY]"""
import json, sys
from hgi_sim import timing as T
from hgi_sim import toksim_hbm_census_1019 as C

ROWS = {}
_prev = T.schedule          # = C.schedule (installed by the census module)


def sched(recs, pos, mode="S2", token=0, cost_fn=T.cost, wires=True):
    log = []

    def cf(r, dyn, L):
        c, g, how = cost_fn(r, dyn, L)
        log.append((r, L, c, how))
        return c, g, how
    s = _prev(recs, pos, mode, token, cf, wires)
    if mode != "S2" or C.CUR["job"] is None:
        return s
    out = ROWS.setdefault(C.CUR["job"], [])
    seg = len({x["seg"] for x in out}) if out else 0
    for i, (r, L, c, how) in enumerate(log[:len(s["ex"])]):
        if r.unit != "COLL":
            continue
        out.append(dict(seg=seg, i=i, tag=r.tag, op=r.op, layer=getattr(r, "layer", None), L=L if isinstance(L, int) else None,
                        shape=json.dumps(C.shape_of(r, L), sort_keys=True), cost=round(c, 2), how=str(how)[:80],
                        base_cost=getattr(r, "base_cost", None), start=round(float(s["start"][i]), 1),
                        end=round(float(s["end"][i]), 1)))
    return s


T.schedule = sched
_CJOB = C._job
OUTP = {"p": None}


def _job(j):
    res = _CJOB(j)
    name = j[1]
    json.dump(ROWS.get(name, []), open(OUTP["p"] + "." + name.replace("|", "__") + ".json", "w"), indent=0, default=str)
    return res


C._job = _job
if __name__ == "__main__":
    out = sys.argv[1]
    OUTP["p"] = out
    C.ONLY = sys.argv[2] if len(sys.argv) > 2 else "info_banklat_all,rec"
    sys.argv = [sys.argv[0], "--out", out + ".census.json"]
    C.main()
