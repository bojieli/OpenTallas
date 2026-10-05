import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_rom_layer_pipeline_campaign as campaign  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (shutil.which("iverilog") and shutil.which("verilator")),
    reason="needs iverilog and verilator",
)


def test_pipeline_latency_is_stage_services_plus_hops_and_users_overlap():
    result = campaign.run()
    assert result["status"] == "pass"
    assert abs(result["first_token_latency_cycles"] - result["expected_first_token_latency_cycles"]) <= 1
    assert result["steady_arrival_interval_cycles"] == [campaign.STAGE_SERVICE]
    # Several users are in flight at once without slowing each other.
    assert result["users_in_flight"] > campaign.STAGES


def test_committed_record_is_current():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
