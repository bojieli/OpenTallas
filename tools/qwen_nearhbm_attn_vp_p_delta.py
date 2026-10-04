#!/usr/bin/env python3
"""Added cycles of the verify-block timing successors (hub_p + stack_vp_p) per attention op, p = 1..6 verify positions.

Inputs are three gate records (tools/qwen_nearhbm_attn_vp_gate.py) of the SAME p = 6 jobs run on three bench builds:
  parent  the dspark step-2 builds (ot_qwen_nearhbm_attn_stack_vp + parent hub, source 7e55cac85),
  hubp    the hub successor only (stack_vp + hub_p, source 49096e8cb),
  new     both successors (stack_vp_p + hub_p, the --source commit of the 'new' record).
An attention op of p positions on L lane sets runs ceil(p / L) passes in sequence; pass j covers positions L j ..
L j + L - 1 on one K/V stream of T = the last covered position's context.  With L = 2 and odd p, the last pass is the
measured L = 2 pass at first = p - 1, whose second lane set holds position p: its stream is ONE row longer than the
op needs (conservative by <= 1 row; recorded per entry as tail_one_row_long).  L = 1 is exact for every p.

    python3 tools/qwen_nearhbm_attn_vp_p_delta.py --parent P.json --hubp H.json --new N.json --out OUT.json
"""
import argparse
import hashlib
import json
from pathlib import Path


def load(p):
    b = Path(p).read_bytes()
    return json.loads(b), hashlib.sha256(b).hexdigest()


def index(rec):
    return {(x["build"], x["case"], x["first"]): x for x in rec["rows"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parent", required=True)
    ap.add_argument("--hubp", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    recs = {k: load(getattr(a, k)) for k in ("parent", "hubp", "new")}
    idx = {k: index(v[0]) for k, v in recs.items()}
    new_rows = recs["new"][0]["rows"]
    keys = sorted({(x["build"], x["case"]) for x in new_rows})
    ops = []
    for b, case in keys:
        vp = int(b.split("_vp")[1])
        pmax = max(x["p"] for x in new_rows if x["case"] == case)
        for p in range(1, pmax + 1):
            firsts = list(range(0, p, vp))
            ent = dict(build=b, case=case, lane_sets=vp, p=p, passes=len(firsts), firsts=firsts,
                       tail_one_row_long=(firsts[-1] + vp > p))
            ok = True
            for k in ("parent", "hubp", "new"):
                xs = [idx[k].get((b, case, f)) for f in firsts]
                if any(x is None or x.get("cycles_total") is None for x in xs):
                    ok = False
                    break
                ent[k] = sum(x["cycles_total"] for x in xs)
                ent[f"{k}_exact"] = all(x["exact"] for x in xs)
            if not ok:
                continue
            ent["added_vs_parent"] = ent["new"] - ent["parent"]
            ent["added_by_row_engine"] = ent["new"] - ent["hubp"]
            ent["added_per_pass_vs_parent"] = round(ent["added_vs_parent"] / ent["passes"], 2)
            ops.append(ent)
    per_run = []
    for (b, case, f), x in sorted(idx["new"].items()):
        y, z = idx["parent"].get((b, case, f)), idx["hubp"].get((b, case, f))
        per_run.append(dict(build=b, case=case, first=f, exact=x["exact"], fault=x["fault"], new=x["cycles_total"],
                            hubp=z and z["cycles_total"], parent=y and y["cycles_total"],
                            added_vs_parent=(y and x["cycles_total"] - y["cycles_total"]),
                            added_by_row_engine=(z and x["cycles_total"] - z["cycles_total"])))
    rec = dict(schema="qwen-nearhbm-attn-vp-p-delta.v1",
               inputs={k: dict(path=str(getattr(a, k)), sha256=v[1], source_commit=v[0]["source_commit"],
                               verdict=v[0]["verdict"], runs=v[0]["runs"], exact_runs=v[0]["exact_runs"])
                       for k, v in recs.items()},
               all_exact=all(r["exact"] for r in per_run) and bool(per_run), ops=ops, runs=per_run)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for e in ops:
        if e["case"].startswith("8187"):
            print(f'{e["build"]:12s} {e["case"]:15s} p={e["p"]} passes={e["passes"]} parent={e["parent"]} '
                  f'new={e["new"]} +{e["added_vs_parent"]} (row engine +{e["added_by_row_engine"]})')


if __name__ == "__main__":
    main()
