#!/usr/bin/env python3
"""TOKSIM-HBM-su fork A: dump every SU.VOP record (sut, descriptors, param, model cost + how) of the census job
info_banklat_all (the composed d4g price) per census SHAPE_KEY.  Read-only wrapper of hgi_sim.toksim_hbm_census_1019."""
import json, sys
from pathlib import Path
from hgi_sim import timing as T
from hgi_sim import toksim_hbm_census_1019 as C
OUT = Path(sys.argv[1]); DUMP = {}
_inner = C.schedule
def sched(recs, pos, mode="S2", token=0, cost_fn=T.cost, wires=True):
    def cf(r, dyn, L):
        c, g, how = cost_fn(r, dyn, L)
        if C.cls_of(r) in ("SU.VOP",) and C.CUR["job"] is not None and mode == "S2":
            d = DUMP.setdefault(C.DESIGN["d"], {})
            sk = json.dumps(C.shape_of(r, L), sort_keys=True)
            e = d.setdefault(sk, dict(n=0, examples=[]))
            e["n"] += 1
            if len(e["examples"]) < 3 or (getattr(r, "tag", "") not in [x["tag"] for x in e["examples"]] and len(e["examples"]) < 8):
                desc = {}
                for k, v in (r.desc or {}).items():
                    try:
                        _, n, m, st, ist = T.eff(v, T.Dyn(8191), L if isinstance(L, int) else 0)
                    except Exception:
                        n = m = st = ist = None
                    desc[k] = dict(space=v.space, fmt=v.fmt, n=n, m=m, stride=st, istride=ist,
                                   raw={a: (b if isinstance(b, (int, float, str, bool, type(None))) else str(b))
                                        for a, b in vars(v).items()})
                e["examples"].append(dict(tag=getattr(r, "tag", ""), param=getattr(r, "param", None), L=L, cost=c, how=how,
                                          sut=dict(r.sut) if isinstance(r.sut, dict) else str(r.sut), desc=desc,
                                          mtp_kind=getattr(r, "mtp_kind", "")))
        return c, g, how
    return _inner(recs, pos, mode, token, cf, wires)
T.schedule = sched
_oj = C._job
def _job(j):
    DUMP.clear()
    res = _oj(j)
    (OUT.parent / ("dump_" + j[1].replace("|", "__") + ".json")).write_text(json.dumps(DUMP, indent=1, default=str) + "\n")
    return res
_job.__module__ = C._job.__module__
C._job = _job
C.ONLY = "info_banklat_all"
sys.argv = [sys.argv[0], "--out", str(OUT.parent / "census_dump.json")]
C.main()
