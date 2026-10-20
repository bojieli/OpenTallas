#!/usr/bin/env python3
"""TOKSIM-HBM (10-19): per-record census of the LH-REPRICE3 composed d4g price, and the MEASURED re-composition.

Mode `census` (default): runs tools/hgi_sim/d4g_reprice3b_1019 (--bw 45.03, banklat projected = the composed 1206.3 /
407.0 price) with T.schedule wrapped, and writes for DS AR and Qwen3-8B AR, per record class (orig_op | tag head):
count per token, the model unit cost (sum / min / max), busy cycles and the cycles the class holds on the critical path
of each scheduled segment (DS: per layer segment, summed as the price does; Qwen: whole token).  This is the
`price` column of the measured-vs-price table and the `count` of the measured composition.

Mode `--measured M.json`: the same schedule with every record whose class has a measured law replaced by the measured
start->retire cycles of that law (M.json classes: {"<class>": {"law": "const"|"affine_bytes"|"ratio", ...}});
records of unmeasured classes keep the model cost and are reported as such (% measured = cycles of measured records
on the critical path / token cycles).

    PYTHONPATH=tools python3 -m hgi_sim.toksim_hbm_census_1019 --out census.json [--measured M.json]
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from hgi_sim import timing as T

_ORIG_SCHED = T.schedule
CUR = {"job": None}
MEAS = {}            # {"ds_ar"|"qwen"|"any": {class: law}}
DESIGN = {"d": None}
EXTRAP = {}
LAST = {"kind": None}
OUTDIR = None


def cls_of(r):
    op = getattr(r, "orig_op", None) or f"{r.unit}.{r.op}"
    return op


def shape_of(r, L):
    out = {}
    for k, d in (getattr(r, "desc", None) or {}).items():
        try:
            _, n, m, _, _ = T.eff(d, T.Dyn(8191), L if isinstance(L, int) else 0)
            out[k] = [getattr(d, "space", None), int(n), int(m), getattr(d, "fmt", None)]
        except Exception:
            out[k] = [getattr(d, "space", None)]
    return out


def bytes_B(r, L):
    """per-SM streamed operand bytes of an SM/ATT record (as the hbm_bw term computes them)"""
    b = (getattr(r, "desc", None) or {}).get("B")
    if b is None or getattr(b, "space", None) != "HBM":
        return 0.0
    _, n, m, _, _ = T.eff(b, T.Dyn(8191), L if isinstance(L, int) else 0)
    if r.unit == "SM":
        return float(n * (-(-m // 16)) * T.ESZ[b.fmt])
    return float(n * 128 * T.ESZ[b.fmt] / 16)


def measured_cost(r, L, c_model):
    m = MEAS.get(DESIGN["d"], {}).get(cls_of(r)) or MEAS.get("any", {}).get(cls_of(r))
    if not m:
        return None
    law = m["law"]
    LAST["kind"] = "ratio" if law == "ratio" else "exact"
    if law == "shape_table":                             # exact measured production shapes; others by measured ratio
        sk = json.dumps(shape_of(r, L), sort_keys=True)
        e = (m.get("shapes") or {}).get(sk)
        if e is not None and e.get("cycles") is not None:
            return float(e["cycles"])
        if m.get("ratio") is not None:
            EXTRAP[cls_of(r)] = EXTRAP.get(cls_of(r), 0) + 1
            LAST["kind"] = "ratio"
            return c_model * float(m["ratio"])
        return None
    if law == "const":
        return float(m["cycles"])
    if law == "ratio":                                   # measured / model on the measured production shapes
        return c_model * float(m["ratio"])
    if law == "affine_bytes":                            # fixed + streamed bytes / measured rate
        return float(m["fixed"]) + bytes_B(r, L) / float(m["bytes_per_cycle"])
    raise ValueError(law)


def schedule(recs, pos, mode="S2", token=0, cost_fn=T.cost, wires=True):
    log = []

    def cf(r, dyn, L):
        c, g, how = cost_fn(r, dyn, L)
        LAST["kind"] = None
        mc = measured_cost(r, L, c) if MEAS else None
        log.append((r, L, c, mc, LAST["kind"]))
        return (mc if mc is not None else c), g, how
    s = _ORIG_SCHED(recs, pos, mode, token, cf, wires)
    if CUR["job"] is None or mode != "S2":
        return s
    # map executed index -> logged cost (schedule calls cost_fn once per executed record, in ex order)
    ex = s["ex"]
    crit = set()
    try:
        n = len(ex)
        if n:
            import numpy as np
            i = int(np.argmax(s["end"]))
            seen = set()
            while i is not None and i not in seen:
                seen.add(i)
                crit.add(i)
                k = ex[i][0]
                u = recs[k].unit
                cands = [(s["end"][j], j) for j in s["deps"][i]]
                for j in range(i - 1, -1, -1):
                    if recs[ex[j][0]].unit == u:
                        cands.append((s["end"][j], j))
                        break
                cands = [c for c in cands if c[0] <= s["start"][i] + 1e-6]
                if not cands:
                    break
                i = max(cands)[1]
    except Exception as e:                                 # pragma: no cover
        print("critical path failed", e, file=sys.stderr)
    agg = CUR["agg"]
    for i, (k, L, *_) in enumerate(ex):
        r, L2, c, mc, kind = log[i]
        key = cls_of(r)
        a = agg.setdefault(key, dict(n=0, model_sum=0.0, model_min=None, model_max=0.0, used_sum=0.0, busy=0.0,
                                     crit_n=0, crit_cycles=0.0, measured_n=0, measured_used=0.0, measured_model=0.0, shapes={}, tags={}, units=set()))
        a["n"] += 1
        a["units"].add(r.unit)
        a["model_sum"] += c
        a["model_min"] = c if a["model_min"] is None else min(a["model_min"], c)
        a["model_max"] = max(a["model_max"], c)
        used = mc if mc is not None else c
        a["used_sum"] += used
        a["measured_n"] += 1 if (mc is not None and kind == "exact") else 0
        if mc is not None and kind == "exact":
            a["measured_used"] += mc
            a["measured_model"] += c
        elif mc is not None:
            a["ratio_n"] = a.get("ratio_n", 0) + 1
            a["ratio_used"] = a.get("ratio_used", 0.0) + mc
            a["ratio_model"] = a.get("ratio_model", 0.0) + c
        a["busy"] += s["end"][i] - s["start"][i]
        if i in crit:
            a["crit_n"] += 1
            a["crit_cycles"] += s["end"][i] - s["start"][i]
        sk = json.dumps(shape_of(r, L), sort_keys=True)
        sh = a["shapes"].setdefault(sk, dict(n=0, model_cost=round(c, 1), bytes_B=bytes_B(r, L)))
        sh["n"] += 1
        tg = (getattr(r, "tag", "") or "")[:48]
        a["tags"][tg] = a["tags"].get(tg, 0) + 1
    CUR["segments"] += 1
    CUR["total"] += s["total_cycles"]
    # time not covered by any critical record = dispatch / fetch bound gaps
    CUR["crit_rec_cycles"] += sum(s["end"][i] - s["start"][i] for i in crit)
    return s


T.schedule = schedule


def main():
    argv = list(sys.argv[1:])
    out = Path(argv[argv.index("--out") + 1])
    if "--measured" in argv:
        MEAS.update(json.loads(Path(argv[argv.index("--measured") + 1]).read_text())["designs"])
    global OUTDIR
    OUTDIR = out.parent / (out.stem + "_jobs")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    from hgi_sim import d4g_reprice_1019 as R
    from hgi_sim import d4g_reprice3b_1019 as R3B
    INNER["f"] = R._job
    _job.__module__ = R.__name__
    R._job = _job
    sys.argv = [sys.argv[0], "--bw", "45.03", "--only", ONLY, "--jobs", "16", "--out", str(out)]
    return R3B.main()


ONLY = "info_banklat_all,all,rec,rec_lat,rec_att,rec_att_bigprog,all_bigprog"
INNER = {}


def _job(j):
        inner = INNER["f"]
        name = j[1]
        CUR.update(job=name, agg={}, segments=0, total=0.0, crit_rec_cycles=0.0)
        DESIGN["d"] = "qwen" if name.endswith("|qwen") else "ds_ar"
        EXTRAP.clear()
        res = inner(j)
        agg = {k: dict(v, units=sorted(v["units"]), model_sum=round(v["model_sum"], 1), used_sum=round(v["used_sum"], 1),
                       busy=round(v["busy"], 1), crit_cycles=round(v["crit_cycles"], 1),
                       shapes=dict(sorted(v["shapes"].items(), key=lambda kv: -kv[1]["n"])[:40]))
               for k, v in CUR["agg"].items()}
        doc = dict(job=name, schedule_total=round(CUR["total"], 1), segments=CUR["segments"],
                   crit_rec_cycles=round(CUR["crit_rec_cycles"], 1), result=res[1].get("cycles", res[1].get("tok_s")),
                   extrapolated_records=dict(EXTRAP), classes=agg)
        (OUTDIR / (name.replace("|", "__") + ".json")).write_text(json.dumps(doc, indent=1, default=str) + "\n")
        CUR["job"] = None
        return res


if __name__ == "__main__":
    raise SystemExit(main())
