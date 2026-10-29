#!/usr/bin/env python3
"""TOK-HBM-9: price DIE-HBM-11/13 C25c cycle items on the S2 token schedule (tools/throughput/accepted_cost.py).
Fixed cycles added to EVERY record of the op class (upper bound: every COLL record assumed on the affected lane).
Run from repo root: PYTHONPATH=src python3 results/tok_hbm_9_1029/price_die_hbm_13.py OUT.json"""
import json, sys
sys.path.insert(0, "tools/throughput")
import accepted_cost as A  # noqa: E402

FLOOR = 1905.97  # planU3f ds tok/s (OWNER: 1906 floor OK)
CASES = [
    # name, op glob, delta cycles per record
    ("NE_L4_i_+1 (upper: all COLL)", "COLL.*", 1),
    ("NE_L4_i_+1 (ALL_GATHER only)", "COLL.ALL_GATHER", 1),
    ("fallback_P_N3 (all COLL)", "COLL.*", 3),
    ("RX vsN0->root L118 +19 (rx_block_ready rides with rx flit; all COLL)", "COLL.*", 19),
    ("TX hub->spb0 +24 (epcal 19b rides with tx flit; all COLL)", "COLL.*", 24),
    ("TX+RX +43 (all COLL, upper bound)", "COLL.*", 43),
    ("TX+RX +43 on cross-die classes excl ALL_GATHER", "COLL.[GRTA][ROA][OPW]*", 43),
]


def main(out):
    res = {}
    for m in ("ds", "qwen"):
        run, count = A.hbm_schedule(m)
        base = run()
        rows = {}
        for name, op, d in CASES:
            r = A.hbm_loss(run, count, op, None, base=base, delta=d)
            if r is None:
                rows[name] = None
                continue
            r["op"] = op
            if m == "ds":
                r["tok_s_at_1906"] = round(FLOOR * (1 - r["e2e_loss_pct"] / 100), 1)
            rows[name] = r
        res[m] = dict(base_cycles=round(base, 1), counts={k: v for k, v in sorted(count.items()) if k.startswith("COLL")},
                      cases=rows)
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
