"""The bit-exact TP sensitivity must stay tied to its source and old design point."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/arch/v41_tp_exact_reprice.json"


def test_rowsplit_record_is_current_and_does_not_claim_a_measured_headline():
    rec = json.loads(RECORD.read_text())
    base = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())
    assert rec["schema"] == "v41_tp_exact_reprice_v1"
    for path, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path

    contract = rec["contract"]
    assert contract["activation_allgather_payload_B"] == 68_096
    assert contract["y_allgather_payload_B"] == 20_480
    assert contract["activation_allgather_payload_B"] // 4 == 17_024

    for context in ("1048576", "200000"):
        for mode in ("ar", "mtp"):
            row = rec["points"]["design_point"][context][mode]
            assert row["baseline"] == base["design_point"][context][mode]
            assert row["rowsplit"] > 0
            assert row["delta_fraction"] < 0

    assert "uncalibrated" in rec["calibration"]["design_point"]
    assert "pending" in rec["calibration"]["adopted_rate_claim"]
    bench = rec["calibration"]["required_collective_bench"]
    assert bench["current_die_collective_flit_bytes"] == 64
    assert bench["activation_local_flits"] == 266
    assert bench["output_local_flits"] == 80
    assert bench["previous_small_gather_word_bytes"] == 512
    assert rec["capacity"]["model_striped_key_users"] == 866
    assert rec["capacity"]["replicated_key_static_users"] == 551
    assert rec["capacity"]["replicated_key_addressable_users"] == 481
    assert rec["capacity"]["multiuser_key_address_isolation"] is False
    assert rec["capacity"]["adopted_saturation_claim_valid"] is False
    assert "parallel scan scheduler" in rec["capacity"]["gate"]
