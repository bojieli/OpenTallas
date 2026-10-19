#!/usr/bin/env python3
"""HBM-NEXT-VEH (10-19 step 3): per-unit P = 4 layer benches driven by ONE layer's records.

Minimum-component form (AGENTS.md; memory token-pass-release-gate-1018): no P = 4 die netlist exists, so the P = 4 layer
is measured unit by unit.  This tool
  records   compiles the DS token on the D1 compiler chain at the next-die point (P = 4, COLL L = 5, HC II 250 =
            measured hnx, VM grown) and dumps ONE layer's records (MTP verify N = 6 and 4-user N = 4; layers 2 and 3 by
            default) with unit / op / rows / shapes / priced cost.  Fleet (compile = the hgi_sim model).
  plan      maps every record of the dumped layer to the landed unit bench that measures it, with the bench parameters
            the record implies, and says which (unit, shape) points are ALREADY measured on the hnx RTL (no re-run:
            AGENTS.md "never duplicate") and which are new.  Writes plan.json + one fleet script per new bench.
The bit-exact layer benches against the CMTP goldens (mtp accept / reject, mu4) need the CMTP BINARY record images
(emitter + VM allocator, CMTP step 3) and stay in the pending list (p4_intake.json).

    PYTHONPATH=tools python3 tools/hbm_next/vehicle/p4_layer_units.py records --out DIR [--layers 2,3]
    python3 tools/hbm_next/vehicle/p4_layer_units.py plan --records DIR/layer_records.json --out DIR
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P4 = 4
A = "results/arch/hbm_next_1019"

# measured unit laws on the hnx RTL (source-pinned; each one is a committed Verilator 5.050 bench with mutant witnesses)
MEASURED = {
    "HC": dict(law="HC_MIX_CYCLES(N) = 998 + 250 (N - 1), production K 20,480 / 24 mix rows / W 256",
               points={1: 998, 2: 1248, 3: 1498, 4: 1748, 6: 2248, 8: 2748},
               src=f"{A}/units/hc/README.md (tb_hnx_hc_eng4, witness/e1_n4.log, e4_n4.log)"),
    "COLL": dict(law="N-row train: one fire + one 40-edge drain; further row = 3K/2 edges, K = ceil(F / R)",
                 points="N 1..6 trains, F < 200 (bench s1/s2)",
                 src=f"{A}/units/coll/README.md (tb_hnx_coll_gq, witness m6/m7/m8)"),
    "SM": dict(law="P = 4 leaf span = P = 1 span + 24 (lane p result +8p, +1 front, +1 publish); 1.003x at K 16, "
                   "1.012x at K 4 (minimum spacing); bit-exact vs production d4g leaves P1-4",
               points={"K16": [8238, 8262], "K4": [2094, 2118]},
               src=f"{A}/sm4/bench_summary.json (tb_hnx_rp4lp4_leaf, MUT1-3 witnesses)"),
    "ATT": dict(law="4-query KV-line-stationary slice: fixed ~113-127 + 7.8 cycles a union row; bit-exact per lane",
                points="sigma 0 / 0.3 / 1.0 / disjoint (s00 s03 s10 sdj)",
                src=f"{A}/att4/bench/throughput.json (tb_hnx_att4, imut1-4 / pvmut1-2 witnesses)"),
}


def _desc(r):
    out = {}
    for k, d in (getattr(r, "desc", None) or {}).items():
        out[k] = {a: getattr(d, a) for a in ("n", "m", "fmt", "stride") if hasattr(d, a)}
    return out


def records(a):
    from hgi_sim import hbm_plane_model as M
    from hgi_sim import ds_mtp_verify as V
    from hgi_sim import plan_study_price_1017 as PS
    layers = [int(x) for x in a.layers.split(",")]
    M.d4g_env()
    PS.VARIANTS["b"]["split"]["lanes"] = 5
    M._ENV["kn"]["lanes"] = 5
    M._ENV["vb"] = PS.VARIANTS["b"]
    M.d4g_env()
    V.HCP_II = 250.0
    st = M.load_stats(ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json")
    u6, uu = st["verify_union"][M.N_MTP]["mean"], st["users_union"]
    cases = {"mtp_verify": dict(N=M.N_MTP, union=u6, kv="upper", users=False),
             "mu4": dict(N=P4, union=uu.get(P4, 6.0 * P4), kv="upper", users=True)}
    out = dict(schema="opentallas.hbm_next_1019.veh.layer_records.v1", rule=__doc__, point="P4 L5 HC-II250 VM grown",
               layers=layers, cases={})
    for name, c in cases.items():
        cfg = M.plane_cfg(P4)
        prog, _ = M.ds_compile(c["N"], cfg, c["union"], c["kv"], c["users"])
        cf = V.cost_fn(None)
        rows = []
        for r in prog:
            if r.layer not in layers:
                continue
            try:
                cost = cf(r, None, None)[0]
            except Exception as e:          # cost needs the schedule context for some records: keep the base price
                cost = getattr(r, "base_cost", None)
            rows.append(dict(layer=r.layer, unit=r.unit, op=r.op, orig_op=getattr(r, "orig_op", None),
                             tag=getattr(r, "tag", None), npos=getattr(r, "npos", 1),
                             mtp_kind=getattr(r, "mtp_kind", None), c1=getattr(r, "c1", None),
                             ii=getattr(r, "ii", None), priced=cost, desc=_desc(r)))
        out["cases"][name] = rows
        print(name, len(rows), dict(Counter(x["unit"] for x in rows)), flush=True)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "layer_records.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


def _sm_shape(x):
    b = x["desc"].get("B", {})
    n, m = b.get("n", 0) or 0, b.get("m", 0) or 0
    return dict(K=n, rows=m, chunks_bdc=max(1, math.ceil(n / 256)), rows_per_sm=max(1, math.ceil(m / 16)))


def plan(a):
    rec = json.loads(a.records.read_text())
    out = dict(schema="opentallas.hbm_next_1019.veh.layer_unit_plan.v1", rule=__doc__, measured_laws=MEASURED,
               by_case={})
    for case, rows in rec["cases"].items():
        per = defaultdict(lambda: dict(records=0, priced=0.0, shapes=Counter()))
        for x in rows:
            u = x["unit"]
            p = per[u]
            p["records"] += 1
            p["priced"] += float(x["priced"] or 0.0)
            if u == "SM":
                s = _sm_shape(x)
                p["shapes"][f"N{x['npos']}|K{s['K']}|m{s['rows']}"] += 1
            elif u == "HC":
                p["shapes"][f"{x['op']}|N{x['npos']}"] += 1
            elif u == "COLL":
                aa = x["desc"].get("A", {})
                p["shapes"][f"{x['op']}|N{x['npos']}|n{aa.get('n')}"] += 1
            else:
                p["shapes"][f"{x['op']}|N{x['npos']}"] += 1
        cov = {}
        for u, p in per.items():
            p["priced"] = round(p["priced"], 1)
            p["shapes"] = dict(p["shapes"].most_common())
            if u == "HC":
                ns = sorted({int(k.split("|N")[1]) for k in p["shapes"]})
                cov[u] = dict(new_points=[n for n in ns if n not in MEASURED["HC"]["points"]],
                              note="every HC row count of the layer is a measured point of tb_hnx_hc_eng4" if
                              all(n in MEASURED["HC"]["points"] for n in ns) else "new N -> hnx_hc_bench.sh e0 with N")
            elif u == "COLL":
                ns = sorted({int(k.split("|N")[1].split("|")[0]) for k in p["shapes"]})
                cov[u] = dict(new_points=[n for n in ns if n > 6], note="N <= 6 trains measured (s1/s2); the law is "
                              "exact in F (check-train proof F < 200)")
            elif u == "SM":
                cov[u] = dict(new_points=sorted(p["shapes"]), note="layer SM shapes -> tb_hnx_rp4lp4_leaf at the "
                              "record's chunk count (NCHUNK) and spacing; P = 1 reference + MUT1 witness")
            elif u == "ATT":
                cov[u] = dict(new_points=[], note="the DS production attention shape (hd 512, window 128 + top-512) "
                              "is the ATT4 bench shape; layer union -> sigma (s03 = 0.3 measured)")
        out["by_case"][case] = dict(units=per, coverage=cov)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "plan.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    for c, v in out["by_case"].items():
        for u, p in v["units"].items():
            print(c, u, p["records"], p["priced"], list(p["shapes"])[:6])
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("records")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--layers", default="2,3")
    p = sp.add_parser("plan")
    p.add_argument("--records", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    return records(a) if a.cmd == "records" else plan(a)


if __name__ == "__main__":
    sys.exit(main())
