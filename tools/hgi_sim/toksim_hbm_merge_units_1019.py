#!/usr/bin/env python3
"""TOKSIM-HBM (10-19): merge the per-group measured unit files into ONE --measured input for toksim_hbm_census_1019, and
(after the composition ran) write cycles.json with the per-class grade table.

  toksim_hbm_merge_units_1019.py merge  UNITS_DIR OUT_MEASURED.json [--qwen-kv-heads 1]
  toksim_hbm_merge_units_1019.py grade  UNITS_DIR CENSUS_JOBS_DIR(measured run) PRICE_JOBS_DIR OUT_cycles.json [--row R]

Grades (owner 10-19 request): measured-on-bound (RTL bound in the current d4g die.v, golden PASS), measured-not-bound
(newest bench-passing RTL / successor controller / lower bound), model (price kept).  --qwen-kv-heads 1: Qwen TP-8 holds ONE
KV head a die (qwen_compiler Geometry(tp=8) nk=1; HBM-ATTN-MB / HBM-RATE-DROP 2b): the census's second-head records
(attention_qk.kv1 / attention_pv.kv1) do not exist and are dropped (cost 0).
"""
import json
import sys
from pathlib import Path


def grade_of(g):
    g = g or ""
    if g == "measured-current-d4g":
        return "measured-on-bound"
    if g.startswith("measured"):
        return "measured-not-bound"
    return "model"


def merge(units, out, kv_heads):
    des = {}
    src = {}
    for f in sorted(Path(units).glob("*.json")):
        d = json.loads(f.read_text())
        for dn, cl in d["designs"].items():
            for c, v in cl.items():
                if c in des.setdefault(dn, {}):
                    raise SystemExit(f"class {dn}/{c} in two unit files ({src[(dn, c)]}, {f.name})")
                des[dn][c] = v
                src[(dn, c)] = f.name
    if kv_heads == 1:
        for c in ("ATT.QK", "ATT.PV"):
            if c in des.get("qwen", {}):
                des["qwen"][c]["drop_tags"] = ["attention_qk.kv1", "attention_pv.kv1"]
    Path(out).write_text(json.dumps(dict(designs=des, sources={f"{a}/{b}": s for (a, b), s in src.items()}), indent=1) + "\n")
    print("merged", {k: len(v) for k, v in des.items()})


def grade(units, mjobs, pjobs, out, row):
    des = json.loads(Path(units).read_text())["designs"] if Path(units).is_file() else None
    if des is None:
        des = {}
        for f in sorted(Path(units).glob("*.json")):
            for dn, cl in json.loads(f.read_text())["designs"].items():
                des.setdefault(dn, {}).update(cl)
    res = {}
    for dn, tag in (("ds_ar", "AR"), ("qwen", "qwen")):
        m = json.loads((Path(mjobs) / f"{row}__{tag}.json").read_text())
        p = json.loads((Path(pjobs) / f"{row}__{tag}.json").read_text())
        rows = {}
        tot = {"measured-on-bound": 0.0, "measured-not-bound": 0.0, "model": 0.0}
        for c, a in sorted(m["classes"].items(), key=lambda kv: -kv[1]["used_sum"]):
            u = des.get(dn, {}).get(c, {})
            gr = grade_of(u.get("grade")) if u else "model"
            if gr != "model" and a.get("measured_n", 0) == 0 and a.get("ratio_n", 0) == 0:
                gr = "model"
            pc = p["classes"].get(c, {})
            rows[c] = dict(n=a["n"], used_sum=a["used_sum"], price_sum=pc.get("model_sum"), crit_cycles=a["crit_cycles"],
                           price_crit_cycles=pc.get("crit_cycles"), measured_records=a.get("measured_n", 0),
                           ratio_records=a.get("ratio_n", 0), grade=gr, unit_grade=u.get("grade"),
                           where_model_wrong=u.get("where_model_wrong"))
            tot[gr] += a["crit_cycles"]
        T = m["schedule_total"]
        res[dn] = dict(schedule_total=T, price_schedule_total=p["schedule_total"], result=m["result"],
                       price_result=p["result"], crit_by_grade=tot,
                       crit_share={k: round(v / T, 4) for k, v in tot.items()}, classes=rows)
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    for dn, r in res.items():
        print(dn, r["result"], "price", r["price_result"], r["crit_share"])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "merge":
        kv = int(a[a.index("--qwen-kv-heads") + 1]) if "--qwen-kv-heads" in a else 2
        merge(a[1], a[2], kv)
    else:
        row = a[a.index("--row") + 1] if "--row" in a else "info_banklat_all"
        grade(a[1], a[2], a[3], a[4], row)
