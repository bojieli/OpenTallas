"""Consume the source-bound SM head schedule repair as an exposed DS token price.

The 53100-edge inherited stage budget FAILED. 59460 edges is the measured
four-kind service sequence; only its head adds6360 edges. This price composition
never qualifies a full token or retroactively passes the old performance budget.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

RECEIPT = Path(__file__).resolve().parents[2] / "results/token_pass/hbm_functional_1021/smb_param1/receipt.json"


def head_schedule_price():
    data = json.loads(RECEIPT.read_text())
    assert data["functional_verdict"] == "PASS"
    assert data["actual_params"]["SMH_ENABLE_INT8"] == data["actual_params"]["SVG_ID_COHORT"] == 1
    assert data["results"]["go_slots_exact"] and data["results"]["fault"] is None
    return dict(delta_stream_edges=data["price"]["delta_stream_edges"],
                head_rc_edges=data["price"]["head_actual"],
                prior_head_rc_edges=data["price"]["head_old_compiled"],
                measured_stage_edges=data["price"]["measured_current_component_sequence"],
                failed_stage_budget=data["price"]["retained_failed_compiled_budget"],
                receipt=str(RECEIPT.relative_to(RECEIPT.parents[4])),
                receipt_sha256=hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
                old_budget_qualification="FAIL (+11.98%, exceeds inherited10%)",
                price_scope="one fixed DS head schedule increment per user token; model composition only")


def reprice_existing(data):
    out = copy.deepcopy(data)
    price = head_schedule_price()
    delta = price["delta_stream_edges"] - data.get("sm_head_reprice", {}).get("delta_stream_edges", 0)
    if "sm_head_reprice" not in data:
        out["historical_before_smb_head_repair"] = dict(release=copy.deepcopy(data.get("release")), scenarios=copy.deepcopy(data.get("scenarios")))
    for row in out.get("scenarios", {}).values():
        if row.get("ds_ar_cycles") is not None:
            row["ds_ar_cycles"] = round(row["ds_ar_cycles"] + delta, 1)
            row["ds_ar_tok_s"] = round(1.2e9 / row["ds_ar_cycles"], 1)
            row["rate_grade"] = "model composition; inherited other stages not requalified"
            if "fixed head schedule" not in row.get("what", ""):
                row["what"] = row.get("what", "") + "; +6360 fixed head schedule, composed rate only; old stage budget FAIL"
    release = out.get("release", {})
    basis = out.get("scenarios", {}).get("rel98_int8") or out.get("scenarios", {}).get("rel98")
    if basis:
        release["ds_ar_cycles"] = basis["ds_ar_cycles"]
        release["ds_ar_tok_s"] = basis["ds_ar_tok_s"]
        release["rate_grade"] = "model composition; no full-token or production-throughput PASS"
    out["sm_head_reprice"] = price
    out["qualification"] = "SM service component functional PASS; old budget FAIL; token rates are composed estimates"
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path); parser.add_argument("output", type=Path)
    args=parser.parse_args()
    data=reprice_existing(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(data, indent=1)+"\n")
    print(json.dumps(dict(release=data.get("release"), delta_stream_edges=head_schedule_price()["delta_stream_edges"])))


if __name__=="__main__": main()
