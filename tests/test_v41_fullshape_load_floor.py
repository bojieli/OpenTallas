"""The full-shape activation-load sensitivity must stay tied to its evidence."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_fullshape_load_floor as F  # noqa: E402
import arch_lanes_v41 as AL  # noqa: E402
import collective_exposure as CX  # noqa: E402
import decode_critical_path as DC  # noqa: E402
from v41_tp_exact_reprice import v41_moe_rowsplit  # noqa: E402
from v41_tp_rowsplit_measured_reprice import measured_gather_mutation  # noqa: E402


def test_current_record_and_source_pins():
    saved = json.loads(F.OUT.read_text())
    assert F.build() == saved
    for path, digest in saved["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_floor_changes_batch_one_token_path():
    rec = F.build()
    assert rec["contract"]["proposed_wo_a_load_cycles_per_layer"] == 2048
    assert rec["contract"]["current_wo_a_descriptor"].startswith("invalid")
    for rows in rec["points"].values():
        row = rows["gw1_depth128_exact_stage"]
        assert row["proposed_wo_load_ar_tok_s"] < row["before_wo_load_ar_tok_s"]
        assert row["status"].startswith("conditional")
    assert "MTP has no corrected" in " ".join(rec["limits"])
    for rows in rec["me_read_width_sensitivity"].values():
        assert rows["4"]["conditional_ar_tok_s"] < rows["8"]["conditional_ar_tok_s"]
        assert rows["8"]["conditional_ar_tok_s"] < rows["16"]["conditional_ar_tok_s"]
        assert rows["4"]["activation_load_cycles_per_layer"] == 2048
        assert rows["8"]["activation_load_cycles_per_layer"] == 1024


def test_all_40_wo_a_nodes_are_on_batch_one_critical_path():
    point = AL.design_point()
    lanes = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())
    lev = lanes["collective_exposure"]["levers"]
    common = point["muts"] + [point["ml"], CX.mutation(lev["terms"]),
                              CX.consumer_mutation(tuple(lev["consumers"]))]
    old = DC.v41_moe
    DC.v41_moe = v41_moe_rowsplit
    try:
        with AL.LX.clock(point["hz"][0]), AL.U.params(**point["hz"][1]):
            result = AL.U.solve(point["sp"], 1_048_576, levers=AL.U.CHAIN_L3,
                                muts=common + [measured_gather_mutation({"act": 1220, "y": 476})])
        built = result["_built"]
        path = built.g.path(built.sink)
        assert sum(name.endswith(".attn.wo_a") for name in path) == 40
        assert result["binding"] == "critical_path"
    finally:
        DC.v41_moe = old
