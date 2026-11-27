"""P-COMPOSE-DROP: row_compose.compose_drops writes <plan>.drop_list and reports unnamed drops."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import row_compose as RC  # noqa: E402


def _tree(root, plan):
    (root / "p.json").parent.mkdir(parents=True, exist_ok=True)
    (root / "p.json").write_text(json.dumps(plan))
    return root


def test_unnamed_and_intended_drops(tmp_path):
    old = {"partition_types": {"a": {"relays": 1, "tap_offset": 5}}}
    new = {"partition_types": {"a": {"relays": 1}}}
    prev = dict(tree=str(_tree(tmp_path / "old", old)), plan="p.json")
    t = _tree(tmp_path / "new", new)
    d = RC.compose_drops(prev, t, "p.json", [{}])
    assert d["unnamed"] == ["partition_types.a.tap_offset"] and not d["intended"]
    assert "#UNNAMED DROP partition_types.a.tap_offset" in (t / "p.json.drop_list").read_text()
    d = RC.compose_drops(prev, t, "p.json", [{"intended_drops": ["DROP partition_types.a.tap_offset # 222->217 taps"]}])
    assert d["intended"] == ["partition_types.a.tap_offset"] and not d["unnamed"]
    assert (t / "p.json.drop_list").read_text().startswith("DROP partition_types.a.tap_offset")
