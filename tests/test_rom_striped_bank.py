import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_rom_striped_bank_campaign as campaign  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (shutil.which("iverilog") and shutil.which("verilator")),
    reason="needs iverilog and verilator",
)


def test_striped_banks_read_selected_experts_at_the_full_rate():
    result = campaign.run()
    assert result["status"] == "pass"
    # Striped: six experts cost the same whatever they are.
    assert result["striped_cycles_six_experts"] == [6 * campaign.EXPERT_WORDS // campaign.BANKS + campaign.OVERHEAD]
    # Dedicated: concentrated routes serialise up to six full experts.
    assert max(result["dedicated_cycles_six_experts"]) == 6 * campaign.EXPERT_WORDS + campaign.OVERHEAD
    assert all(c["scoreboard_errors"] == 0 for c in result["cases"])


def test_committed_record_is_current():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
