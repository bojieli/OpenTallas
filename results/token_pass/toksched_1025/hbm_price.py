#!/usr/bin/env python3
"""TOK-SCHED 2026-10-25: r25gq (HBM die; ds_ar + qwen_ar) S2-schedule cost of the three COORD-approved cycle changes
(COORD 12:07 10-25), each alone, bracketed, and all together in ONE schedule, on the exact accepted_cost.py basis
(tools/throughput/accepted_cost.py hbm_schedule: fixed cycles added to every matching record, S2 re-scheduled).
tok/s = CLK / S2 token cycles, CLK = 1.2e9 (tools/throughput_budget/build.py S2_tok_s).

    python3 results/token_pass/toksched_1025/hbm_price.py results/token_pass/toksched_1025/hbm_price.json
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/throughput"))
import accepted_cost as A  # noqa: E402

CLK = 1.2e9
TC = [("SM.MATVEC", "B", {"BF16", "INT8"})]          # SM matvecs on the BF16 tc columns (BF16 weights; INT8 = fmt3 via op_bf)
BF = [("SM.MATVEC", "B", {"BF16"})]
TKX = 52.0                                           # measured q_hub_nw W-end round trip 26 out + 26 return (hbm_tkx_measure.json)
# name -> [(op pattern, fmt filter or None, cycles a record)]
CHANGES = {
    "a_q3_arg_publish_+1": [("COLL.ARGMAX_MERGE", None, 1.0)],
    "b_sm_bf16_path_xs3n_tc_+1": [("SM.MATVEC", TC, 1.0), ("ATT.QK|ATT.PV", None, 1.0)],
    "c_tkx_q_hub_nw_W_+52": [("COLL.TOPK_MERGE", None, TKX)],
}
SENS = {
    "b_lower_bf16_weights_only": [("SM.MATVEC", BF, 1.0)],
    "b_upper_every_SM_and_ATT_record": [("SM.MATVEC|ATT.*", None, 1.0)],
    "c_+40": [("COLL.TOPK_MERGE", None, 40.0)],
    "c_+50_COORD": [("COLL.TOPK_MERGE", None, 50.0)],
    "c_+60": [("COLL.TOPK_MERGE", None, 60.0)],
    "c_+39_delta_vs_E_end": [("COLL.TOPK_MERGE", None, 39.0)],
    "c_upper_+60_also_every_IDX.TOPK": [("COLL.TOPK_MERGE|IDX.TOPK", None, 60.0)],
}


def main(out):
    res = dict(schema="toksched.hbm.1025.v2", design="r25gq", clk_hz=CLK,
               model="S2 schedule of the exact per-die program (accepted_cost.hbm_schedule), fixed cycles added to "
                     "every matching record; combined = all three in one schedule", workloads={})
    for wl, name in A.DESIGNS["r25gq"]["workloads"].items():
        run, count = A.hbm_schedule(name)
        base = run()
        w = dict(base_cycles=round(base, 1), base_tok_s=round(CLK / base, 2), program_records={})
        for terms in list(CHANGES.values()) + list(SENS.values()):
            for o, f, _ in terms:
                _, c = A.hbm_schedule(name, [(None, k, v) for _, k, v in f] if f else None)
                w["program_records"][o + (f"[{f[0][1]}={'/'.join(sorted(f[0][2]))}]" if f else "")] = \
                    sum(n for k, n in c.items() if A.op_match(k, o))

        def ev(terms):
            ex = tuple((o, [(None, k, v) for _, k, v in f] if f else None, d) for o, f, d in terms)
            new = run(extra=ex)
            return dict(terms=[[o, (f"{f[0][1]}={'/'.join(sorted(f[0][2]))}" if f else None), d] for o, f, d in terms],
                        cycles=round(new, 1), added_cycles=round(new - base, 1), tok_s=round(CLK / new, 2),
                        d_tok_s=round(CLK / new - CLK / base, 2), e2e_loss_pct=round(A.loss_pct(base, new), 4))
        w["changes"] = {k: ev(v) for k, v in CHANGES.items()}
        w["combined"] = ev([t for v in CHANGES.values() for t in v])
        w["sensitivity"] = {k: ev(v) for k, v in SENS.items()}
        res["workloads"][wl] = w
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    for wl, w in res["workloads"].items():
        print(wl, "base", w["base_cycles"], w["base_tok_s"], w["program_records"])
        for k, v in list(w["changes"].items()) + [("combined", w["combined"])] + list(w["sensitivity"].items()):
            print(f"  {k:36s} +{v['added_cycles']:8.1f} cyc  {v['tok_s']:9.2f} tok/s ({v['d_tok_s']:+.2f})  loss {v['e2e_loss_pct']:.4f} %")


if __name__ == "__main__":
    main(sys.argv[1])
