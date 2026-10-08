#!/usr/bin/env python3
"""bf_merge_ksplit on the mixed-slot S81 die (Claude bf-double, 2026-10-07): MEASURED full-field per-node deltas.

Unadopted candidate results/uarch/dsrom_bf_candidates_20261007/mixed2304 (tools/dsrom_bf_double_alloc.py --shared --pbf 2304
--ksplit gate: 2,304 pairs = 18 a region, 512 BF on the flat RTL is_bf map, 77 allocator stages; column = 4 BF slots
at f198.72 (BF outline 190.08) + 7 q slots at f183.60, slot order [BF,q,q,BF,q,q,BF,q,BF,q,q]).  Every field phase of
the seven representative layers ran in the qelem10 field vehicle (tools/dsrom_1m_field.py, OT_DSROM_FIELD_BINDING;
18,288 region runs, every one bit-exact).  Each node is composed with the reprice r8 rule at the composition frame
(f183.60 per-region wire: the mixed column is 37.8 um a tier taller, ESTIMATED as the f183.60 wire) and compared with
the as-built qelem10 regions (2,417-pair binding); the delta of a representative layer applies to every layer of its
type (tools/dsrom_1m_measure.TYPES).  Writes results/rtl/dsrom_bf_double_20261007/candidate_full_field_price.json, whose
contains model sensitivity only. Physical geometry, native BF/PQ timing, and final wire pricing remain pending.

    python3 tools/dsrom_bf_merge_mixed_price.py --regions results/rtl/dsrom_bf_double_20261007/B_mixed_2304_regions.json.gz --out /tmp/mixed-price.json
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_field_reprice_r8 as RP

import dsrom_1m_measure as M

OUT = ROOT / "results/rtl/dsrom_bf_double_20261007/candidate_full_field_price.json"
GEOM = "f183.60"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", type=Path, required=True, help="Committed compact field regions")
    ap.add_argument("--out", type=Path, default=OUT); a = ap.parse_args()
    geo = RP.load_geo(GEOM); W = RP.wire_fn(geo, RP.hub_terms(geo))
    old = RP.summarise(RP.node_table(RP.load_regions(RP.OUT / "regions/asbuilt_qelem10.json.gz"), lambda r: W[r]))
    ph = RP.load_regions(a.regions)["phases"]
    new = RP.summarise(RP.node_table(dict(config="asbuilt", phases=ph), lambda r: W[r]))
    rep = {L: t["rep"] for t in M.TYPES.values() for L in t["layers"]}
    nodes, adds = {}, []
    for n in sorted(old):
        d = new[n]["total_cycles"] - old[n]["total_cycles"]
        nodes[n] = dict(old=old[n]["total_cycles"], new=new[n]["total_cycles"], old_phases=old[n]["phases"],
                        new_phases=new[n]["phases"], delta=d, exact=new[n]["exact"])
        if not d:
            continue
        if n.startswith("E1."):
            adds.append([n, d]); continue
        Lr, node = n.split(".", 1)
        adds += [[f"L{L}.{node}", d] for L, r in rep.items() if r == int(Lr[1:])]
    rec = dict(schema="opentallas.dsrom.bf-double.mixed-price.v1", tool="tools/dsrom_bf_merge_mixed_price.py",
               release="results/uarch/dsrom_bf_candidates_20261007/mixed2304", geometry=GEOM,
               region_runs=sum(len(p["regions"]) for p in ph.values()),
               all_exact=all(v["exact"] for v in new.values()) and all(int(x[3]) for p in ph.values() for x in p["regions"].values()),
               nodes=nodes, adds=adds,
               estimated="wire: f183.60 per-region round trip (the mixed column is 37.8 um a tier taller)")
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["region_runs"], rec["all_exact"], len(adds), sum(v["delta"] for v in nodes.values()))


if __name__ == "__main__":
    main()
