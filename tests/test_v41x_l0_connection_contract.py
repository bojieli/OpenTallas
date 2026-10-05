"""results/rtl/v41x_l0_connection_contract.json: current, or carrying an explicit stale marker."""
import json
from pathlib import Path

from record_currency_support import assert_current_or_marked_stale

ROOT = Path(__file__).resolve().parents[1]


def test_record_is_current_or_marked_stale():
    rec = json.loads((ROOT / "results/rtl/v41x_l0_connection_contract.json").read_text())
    assert rec["status"] == "blocked_pending_integration"          # the historical verdict is kept
    assert_current_or_marked_stale(rec, rec["source_sha256"], "v41x_l0_connection_contract")
