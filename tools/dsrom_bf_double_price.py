#!/usr/bin/env python3
"""bf-double field phase merges, MEASURED (Claude bf-double, 2026-10-07).

Two allocations at the f198.72 frame (results/uarch/dsrom_bf_double_binding_20261007): base_f198 (today's allocator,
2,050 pairs / 440 BF) and shared4_f198 (tools/dsrom_bf_double_alloc.py --shared: 4 BF pairs in every region, BF16
x-group pair avoidance).  Every BF16 field phase of both was run in the field vehicle (tools/dsrom_1m_field.py run,
--qelem 10, bit-exact against the golden per region; OT_DSROM_FIELD_BINDING).  This tool composes each BF16 node
(wo_a; a_proj with its FP8 phase taken from the as-built qelem10 regions; router; cmp.wk) with the reprice r8 rule
(tools/dsrom_field_reprice_r8.seq_cycles: per-region wire of the composition's frame geometry) and writes the per
node delta (merged - base) the DS closure-cost ledger prices.

    python3 tools/dsrom_bf_double_price.py --base W_base --merged W_merged [--geom f183.60]
      (W = field work dirs holding plan.json and runs/<phase>/rNNN/result.json)
"""
import argparse, gzip, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_field_reprice_r8 as RP
import dsrom_1m_measure as M

OUT = ROOT / "results/rtl/dsrom_bf_double_20261007"
BFNODES = ("attn.wo_a", "attn.a_proj", "ffn.router", "attn.cmp.wk")


def regions(work):
    plan = json.loads((work / "plan.json").read_text())
    ph = {}
    for p in plan["phases"]:
        rows = {}
        for reg in p["regions"]:
            r = json.loads((work / "runs" / p["phase"] / f"r{reg:03d}" / "result.json").read_text())
            rows[str(reg)] = [r["rows"], r["go_to_last_w"], r["go_to_idle"], int(r["pass_"])]
        ph[p["phase"]] = dict(layer=p["layer"], node=p["node"], stage=p["stage"], regions=rows)
    return ph


def nodes(ph, fp8):
    """(layer, node) -> [phases in plan order]; a_proj gets its FP8 phase (as-built qelem10) first"""
    out = {}
    for name, p in ph.items():
        out.setdefault((p["layer"], p["node"]), []).append(p)
    for (L, n), v in out.items():
        if n == "attn.a_proj":
            v.insert(0, fp8[f"L{L}.a_proj.fp8"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--merged", type=Path, required=True)
    ap.add_argument("--geom", default="f183.60")
    ap.add_argument("--out", type=Path, default=OUT / "merge_price.json")
    a = ap.parse_args()
    geo = RP.load_geo(a.geom)
    W = RP.wire_fn(geo, RP.hub_terms(geo))
    asb = RP.load_regions(RP.OUT / "regions/asbuilt_qelem10.json.gz")["phases"]
    tab = {}
    for tag, w in (("base", a.base), ("merged", a.merged)):
        for (L, n), phs in nodes(regions(w.resolve()), asb).items():
            tot, ok = RP.seq_cycles(phs, lambda r: W[r])
            tab.setdefault(f"L{L}.{n}", {})[tag] = dict(total=tot, meas=RP.seq_cycles_noloc(phs), phases=len(phs),
                                                       exact=ok)
    tab = {k: v for k, v in tab.items() if "merged" in v}     # nodes the merged run measured
    for k, v in tab.items():
        v["delta_cycles"] = v["merged"]["total"] - v["base"]["total"]
    # representative layer -> every layer of its type (tools/dsrom_1m_measure.TYPES)
    per_layer = {}
    for t in M.TYPES.values():
        for L in t["layers"]:
            for n in BFNODES:
                k = f"L{t['rep']}.{n}"
                if k in tab and tab[k]["delta_cycles"]:
                    per_layer[f"L{L}.{n}"] = tab[k]["delta_cycles"]
    rec = dict(schema="opentallas.dsrom.bf-double.merge-price.v1", tool="tools/dsrom_bf_double_price.py",
               geometry=a.geom, wire="tools/dsrom_field_reprice_r8 wire_fn (per region, composition frame)",
               base=str(a.base), merged=str(a.merged),
               bindings=dict(base="results/uarch/dsrom_bf_double_binding_20261007/base_f198",
                             merged="results/uarch/dsrom_bf_double_binding_20261007/shared4_f198"),
               all_exact=all(v[t]["exact"] for v in tab.values() for t in ("base", "merged")),
               nodes=tab, per_layer_delta_cycles=per_layer,
               measured="field vehicle RTL (Verilator, 2-state), bit-exact per region; FP8 a_proj phase from the "
                        "as-built qelem10 regions (unchanged by the merge)")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for k, v in sorted(tab.items(), key=lambda kv: (int(kv[0].split(".")[0][1:]), kv[0])):
        print(f"{k:22s} base {v['base']['total']:5d} ({v['base']['phases']} ph)  merged {v['merged']['total']:5d} "
              f"({v['merged']['phases']} ph)  delta {v['delta_cycles']:+5d}  exact {v['base']['exact'] and v['merged']['exact']}")


if __name__ == "__main__":
    main()
