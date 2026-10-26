#!/usr/bin/env python3
"""TOK-HBM 2026-10-26: file the accepted-cost r25gq row for the D-HBM-B1 FT-overlay lane latencies
(PATH-HBM-R2 06:04 request; COORD 11:33 accepted under the accepted-cost rule, NUMBER-CHECK confirmed 11:48).

Re-runs the exact accepted_cost.hbm_schedule S2 schedule with the per-op fixed cycles of price_request.json
(schedule.<wl>.lower.terms, from tools/hbm_b2/b1_lane_traversal.py price) in ONE schedule per workload, checks the
added cycles against price_request.json, then proposes + accepts one ledger row (ledger = repo default).

    python3 results/token_pass/hbm_b1_lane_map_1026/file_ft_overlay_row.py [--dry-run]
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/throughput"))
import accepted_cost as A  # noqa: E402

HERE = Path(__file__).resolve().parent
REQ = HERE / "price_request.json"
UNIT = "HBM.D4G_B1_FT_OVERLAY"
NOTE = ("D-HBM-B1 FT-overlay lane stations (native_cut_bands_r3 0552ecf2 -> b1n6 60d58330; b1e 43fb3b14 keeps the "
        "same 230 live-lane latencies): fixed cycles per record SU.VOP/ARGMAX.LOCAL/COLL.*/FUSED.ROW_NORM +2 "
        "(L36 hub->su, L101/L126 ctl), HC.HC_MIX_POST/FUSED.HC_* +1 (L15 bank chain); L93/L119/L146(+m) dead "
        "(removed in b1e). Price = plan lane latency (Plan.lane_latency), not a bench; MTP not priced (no r25gq MTP basis).")
ACCEPT_NOTE = ("COORD 2026-10-26 11:33 PDT accepted under the accepted-cost rule pending NUMBER-CHECK; "
               "NUMBER-CHECK confirmed 11:48 PDT (COORD-REVIEW-QUEUE); filed by TOK-HBM")


def main(dry=False):
    req = json.loads(REQ.read_text())
    per = {}
    for wl, name in A.DESIGNS["r25gq"]["workloads"].items():
        s = req["schedule"][wl]
        terms = tuple((o, None, float(d)) for o, d in s["lower"]["terms"])
        run, count = A.hbm_schedule(name)
        base = run()
        new = run(extra=terms)
        added = round(new - base, 1)
        assert abs(added - s["lower"]["added_cycles"]) < 0.2, (wl, added, s["lower"]["added_cycles"])
        assert abs(round(base, 1) - s["base_cycles"]) < 0.2, (wl, base, s["base_cycles"])
        per[wl] = dict(model="S2 schedule, fixed cycles added to every record of each op (one schedule)",
                       base_cycles=round(base, 1), cycles=round(new, 1), added_cycles=added,
                       terms=[[o, d] for o, _, d in terms],
                       program_records={o: count.get(o, 0) for o, _, _ in terms},
                       e2e_loss_pct=round(A.loss_pct(base, new), 3))
        print(wl, per[wl])
    row = A.make_row("r25gq", UNIT, 0.0, 2.0, per, "results/token_pass/hbm_b1_lane_map_1026/price_request.json",
                     "committed_bench", NOTE, unit_of_measure="cycles a record (max over ops)")
    if dry:
        print(json.dumps(row, indent=1))
        return
    led = A.load_ledger()
    A.propose(led, row)
    A.accept(led, "r25gq", UNIT, note=ACCEPT_NOTE)
    A.save_ledger(led)
    print("FILED+ACCEPTED", UNIT, "loss", row["e2e_loss_pct"], "totals", led["totals"]["r25gq"])


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
