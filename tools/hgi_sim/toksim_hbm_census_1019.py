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
    tg = getattr(r, "tag", "") or ""
    if any(tg.startswith(t) for t in m.get("drop_tags", [])):   # record does not exist on the measured die (e.g.
        LAST["kind"] = "exact"                                   # Qwen TP-8: 1 KV head a die -> kv1 records dropped)
        return 0.0
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
    # critical path: walk back from the last retire through the term that actually BOUND each dispatch / start /
    # retire (timing.schedule "bind": wait-bit producer, unit / pipelined issue, stream producer start / tail,
    # in-order retire, CP dispatch, fetch / decode).  Every token cycle is attributed exactly once: to the record
    # that was executing on the path, or to a named gap (dispatch wire, retire wire, cp issue, fetch / decode).
    # The 10-19 walk followed region deps only and stopped at the first STREAM consumer (Qwen: ARGMAX.LOCAL rides
    # the LM-head stream, so its start precedes every dep's end) -> Qwen ALL_REDUCE / SM / norm all showed 0.
    ex = s["ex"]
    crit, gaps = crit_walk(s)
    agg = CUR["agg"]
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
        if crit.get(i, 0.0) > 1e-9:
            a["crit_n"] += 1
            a["crit_cycles"] += crit[i]
        sk = json.dumps(shape_of(r, L), sort_keys=True)
        sh = a["shapes"].setdefault(sk, dict(n=0, model_cost=round(c, 1), bytes_B=bytes_B(r, L)))
        sh["n"] += 1
        tg = (getattr(r, "tag", "") or "")[:48]
        a["tags"][tg] = a["tags"].get(tg, 0) + 1
    CUR["segments"] += 1
    CUR["total"] += s["total_cycles"]
    # time not covered by any critical record = dispatch / fetch bound gaps
    CUR["crit_rec_cycles"] += sum(crit.values())
    for k, v in gaps.items():
        CUR["crit_gaps"][k] = CUR["crit_gaps"].get(k, 0.0) + v
    return s


def crit_walk(s):
    """-> ({executed index: critical cycles}, {gap name: cycles}); sum of both == s["total_cycles"]"""
    st, en, dp, bind = s["start"], s["end"], s["disp"], s.get("bind")
    n = len(s["ex"])
    crit, gaps = defaultdict(float), defaultdict(float)
    if not n or not bind or bind[0] is None:
        return crit, gaps
    import numpy as np
    i = int(np.argmax(en))
    pt, t = "end", en[i]
    if s["total_cycles"] > t:
        gaps["tail"] += s["total_cycles"] - t
    for _ in range(20 * n + 10):
        if pt == "end":
            kind, j = bind[i][2]
            if kind in ("stream_tail", "inorder"):
                crit[i] += t - en[j]
                i, pt, t = j, "end", en[j]
            else:
                crit[i] += t - st[i]
                pt, t = "start", st[i]
        elif pt == "start":
            kind, j = bind[i][1]
            if kind == "disp":
                gaps["dispatch_wire"] += t - dp[i]
                pt, t = "disp", dp[i]
            elif kind in ("unit", "fence") and j is not None:
                gaps["unit_serial" if kind == "unit" else "fence"] += t - en[j]
                i, pt, t = j, "end", en[j]
            elif kind == "pipe":
                crit[i] += t - st[j]
                i, pt, t = j, "start", st[j]
            elif kind == "stream_start":
                i, pt, t = j, "start", st[j]
            else:
                gaps["unbound"] += t
                return crit, gaps
        else:
            kind, j = bind[i][0]
            if j is None:
                gaps["fetch_decode"] += t
                return crit, gaps
            if kind == "wait":
                gaps["retire_wire"] += t - en[j]
                i, pt, t = j, "end", en[j]
            elif kind == "queue":
                gaps["queue"] += t - st[j]
                i, pt, t = j, "start", st[j]
            else:                                         # cp issue / fetch-decode: previous dispatch
                gaps["cp_dispatch" if kind == "cp" else "fetch_decode"] += t - dp[j]
                i, pt, t = j, "disp", dp[j]
        if t < -1e-6:
            break
    gaps["unbound"] += max(0.0, t)
    return crit, gaps


T.schedule = schedule


# HBM-COLLFUSE (10-20): the census schedules the Qwen TP-4 programme (qwen_compiler.Geometry default tp=4: nq = 8 q heads,
# nk = 2 KV heads a die) while the release die is TP-8 (Geometry(tp=8): nq = 4, nk = 1).  TOKSIM-HBM already drops the
# kv1 attention records and measures SM rows at TP-8; the per-q-head SU records below still carried 8 rows.  With
# --measured they take the TP-8 programme's n / m (same tag, same occurrence), keeping the TP-4 VM base so every region
# dependence of the TP-4 schedule is kept.  --qwen-tp4-rows restores the 10-19 behaviour.
QWEN_TP8_TAGS = ("softmax.max", "softmax.exp_sum", "softmax.bf16_p", "pv_normalize", "rope", "round_q", "row_scale_qkv")
TP8_LOG = {}


def _tp8_rows_patch():
    import dataclasses
    from hgi_sim import qwen_compiler as QC
    orig = QC.program
    if getattr(orig, "_tp8_rows", False):
        return

    def program(g, params, n_layers, *a, **k):
        recs = orig(g, params, n_layers, *a, **k)
        if getattr(g, "tp", 4) != 4:
            return recs
        cfg = dict(hidden_size=g.H, num_attention_heads=g.NH, num_key_value_heads=g.KV, head_dim=g.HD,
                   intermediate_size=g.FF, vocab_size=g.V, num_hidden_layers=g.L)
        r8 = orig(QC.Geometry(cfg, g.ctx, tp=8), params, n_layers, *a, **k)
        by = defaultdict(list)
        for r in r8:
            if r.tag in QWEN_TP8_TAGS:
                by[r.tag].append(r)
        seen = defaultdict(int)
        out = []
        for r in recs:
            if r.tag in QWEN_TP8_TAGS:
                j = seen[r.tag]
                seen[r.tag] += 1
                t8 = by[r.tag][j]
                assert (t8.unit, t8.op, sorted(t8.desc)) == (r.unit, r.op, sorted(r.desc)), r.tag
                nd = {key: dataclasses.replace(d, n=t8.desc[key].n, m=t8.desc[key].m) for key, d in r.desc.items()}
                if any((nd[key].n, nd[key].m) != (d.n, d.m) for key, d in r.desc.items()):
                    TP8_LOG[r.tag] = TP8_LOG.get(r.tag, 0) + 1
                r = dataclasses.replace(r, desc=nd)
            out.append(r)
        return out
    program._tp8_rows = True
    QC.program = program


def main():
    argv = list(sys.argv[1:])
    out = Path(argv[argv.index("--out") + 1])
    if "--measured" in argv:
        MEAS.update(json.loads(Path(argv[argv.index("--measured") + 1]).read_text())["designs"])
        if "--qwen-tp4-rows" not in argv:
            _tp8_rows_patch()
    global OUTDIR
    OUTDIR = out.parent / (out.stem + "_jobs")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    from hgi_sim import d4g_reprice_1019 as R
    from hgi_sim import d4g_reprice3b_1019 as R3B
    INNER["f"] = R._job
    _job.__module__ = R.__name__
    R._job = _job
    # --bw / --bridge pass through (default 45.03 = the composed price of record; 90.67 --bridge 1 = the successor PC
    # controller with the rotated layout, LH-REPRICE3 successor scenario) for every record that keeps its model cost
    bw = argv[argv.index("--bw") + 1] if "--bw" in argv else "45.03"
    extra = ["--bridge", argv[argv.index("--bridge") + 1]] if "--bridge" in argv else []
    sys.argv = [sys.argv[0], "--bw", bw] + extra + ["--only", ONLY, "--jobs", "16", "--out", str(out)]
    return R3B.main()


ONLY = "info_banklat_all,all,rec,rec_lat,rec_att,rec_att_bigprog,all_bigprog"
INNER = {}


def _job(j):
        inner = INNER["f"]
        name = j[1]
        CUR.update(job=name, agg={}, segments=0, total=0.0, crit_rec_cycles=0.0, crit_gaps={})
        DESIGN["d"] = "qwen" if name.endswith("|qwen") else "ds_ar"
        EXTRAP.clear()
        TP8_LOG.clear()
        res = inner(j)
        agg = {k: dict(v, units=sorted(v["units"]), model_sum=round(v["model_sum"], 1), used_sum=round(v["used_sum"], 1),
                       busy=round(v["busy"], 1), crit_cycles=round(v["crit_cycles"], 1),
                       shapes=dict(sorted(v["shapes"].items(), key=lambda kv: -kv[1]["n"])[:40]))
               for k, v in CUR["agg"].items()}
        doc = dict(job=name, schedule_total=round(CUR["total"], 1), segments=CUR["segments"],
                   crit_rec_cycles=round(CUR["crit_rec_cycles"], 1),
                   crit_gaps={k: round(v, 1) for k, v in sorted(CUR["crit_gaps"].items(), key=lambda kv: -kv[1])}, result=res[1].get("cycles", res[1].get("tok_s")),
                   extrapolated_records=dict(EXTRAP), qwen_tp8_rows_remapped=dict(TP8_LOG), classes=agg)
        (OUTDIR / (name.replace("|", "__") + ".json")).write_text(json.dumps(doc, indent=1, default=str) + "\n")
        CUR["job"] = None
        return res


if __name__ == "__main__":
    raise SystemExit(main())
