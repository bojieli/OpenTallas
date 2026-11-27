"""HEAD-EAST-R3 11-26: top-level gpl_td / street_sizing are schema keys (PRE SCHEMA-UNKNOWN-KEY refused both)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402


def test_keys_declared():
    props = S.SCHEMA["properties"]
    assert set(props["gpl_td"]["properties"]) == {"top_overflow_trigger", "firm_small_clusters", "cell_growth_gate"}
    assert set(props["street_sizing"]["properties"]) == {"pg", "pg_track_loss"}
    assert props["gpl_td"]["additionalProperties"] is False


def test_gpl_td_keys_match_tool():
    import gpl_td
    assert set(gpl_td.KEYS) == set(S.SCHEMA["properties"]["gpl_td"]["properties"])
