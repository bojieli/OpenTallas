"""KIT-OPS-5 11-15: 'No module named ot_store' is INFRA (retryable), not FLOW."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

TEXT = "tool / Tcl error @place: ModuleNotFoundError: No module named 'ot_store'"


def test_ot_store_rule_is_infra_and_first_for_that_text():
    hits = [(r[0], r[-1]) for r in KW.RULES if isinstance(r[2], str) and (r[1] is None or re.search(r[1], "place")) and re.search(r[2], TEXT)]
    assert hits and hits[0][0] == "INFRA", hits
