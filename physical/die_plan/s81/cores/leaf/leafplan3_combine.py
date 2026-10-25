#!/usr/bin/env python3
"""S81/LEAFPLAN3 10-25: fold the per-type ft_sites.py results (exact FT station sites recomputed against the template
placement; one ot-run job per leaf type) into the template plan.  Only the 72 leaf types' ft_slots derived fields
(stations, regs_um, bit_sites_um, bit_site_cell_um) may change; every other field of every type must be identical.
usage: combine.py TEMPLATE_PLAN JOBS_DIR OUT_PLAN [--summary JSON]"""
import argparse
import json
from pathlib import Path

DERIVED = {"stations", "regs_um", "bit_sites_um", "bit_site_cell_um"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("jobs")
    ap.add_argument("out")
    ap.add_argument("--summary")
    a = ap.parse_args()
    P = json.loads(Path(a.plan).read_text())
    rows = []
    for tn, T in P["partition_types"].items():
        if not tn.startswith("ot_s81sl_leaf__t"):
            continue
        J = json.loads((Path(a.jobs) / tn / "plan.json").read_text())["partition_types"][tn]
        assert {k: v for k, v in J.items() if k != "ft_slots"} == {k: v for k, v in T.items() if k != "ft_slots"}, tn
        assert len(J["ft_slots"]) == len(T["ft_slots"]), tn
        add = 0
        for s, n in zip(T["ft_slots"], J["ft_slots"]):
            assert {k: v for k, v in s.items() if k not in DERIVED} == {k: v for k, v in n.items() if k not in DERIVED}, \
                (tn, s["name"])
            add += n["stations"] - s["stations"]
        led = json.loads((Path(a.jobs) / tn / "ledger.json").read_text())
        rows.append(dict(type=tn, added_slot_stations=add,
                         max_paired_bit_hop_um=max((x["worst_paired_bit_um"] for x in led), default=0.0)))
        T["ft_slots"] = J["ft_slots"]
    Path(a.out).write_text(json.dumps(P, indent=0) + "\n")
    s = dict(types=len(rows), added_slot_stations=sum(r["added_slot_stations"] for r in rows),
             types_with_added=[r["type"] for r in rows if r["added_slot_stations"]],
             max_paired_bit_hop_um=max(r["max_paired_bit_hop_um"] for r in rows), rows=rows)
    if a.summary:
        Path(a.summary).write_text(json.dumps(s, indent=1) + "\n")
    print({k: v for k, v in s.items() if k != "rows"})


if __name__ == "__main__":
    main()
