"""KV-101/SPLIT: clock.spine.feed reference carries the root read from the committed feed doc."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_split_regions as KSR  # noqa: E402


def _feed(tmp_path, root="hub_C", parent=None, **extra):
    doc = dict(root=root, parent=parent if parent is not None else {"hub_C": None, "hub_Ei": "hub_C"},
               form="fwd", frame="wall_aligned", **extra)
    p = tmp_path / "feed.json"
    p.write_text(json.dumps(doc))
    return p


def test_feed_ref_root_from_doc(tmp_path):
    ref = KSR.feed_ref(_feed(tmp_path), parts={"hub_C", "hub_Ei"})
    assert ref["root"] == "hub_C" and ref["form"] == "fwd" and ref["frame"] == "wall_aligned"
    assert ref["path"] == "feed.json" and len(ref["sha256"]) == 64


def test_feed_ref_root_follows_doc_not_name(tmp_path):
    ref = KSR.feed_ref(_feed(tmp_path, root="hub_Ei", parent={"hub_Ei": None, "hub_C": "hub_Ei"}))
    assert ref["root"] == "hub_Ei"


@pytest.mark.parametrize("root,parent,parts", [
    (None, {"hub_C": None}, None),                              # no root in doc
    ("hub_C", {"hub_C": "hub_Ei", "hub_Ei": None}, None),       # root has a parent
    ("hub_C", {"hub_C": None, "hub_Ei": None}, None),           # two parentless nodes
    ("hub_C", {"hub_C": None}, {"hub_Ei"}),                     # root not a partition
])
def test_feed_ref_fails_closed(tmp_path, root, parent, parts):
    doc = dict(parent=parent)
    if root:
        doc["root"] = root
    p = tmp_path / "feed.json"
    p.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        KSR.feed_ref(p, parts=parts)


def test_restamp_feed_keeps_path_and_checks_sha(tmp_path):
    f = _feed(tmp_path)
    ref = KSR.feed_ref(f)
    plan = {"partitions": [{"name": "hub_C", "type": "t"}, {"name": "hub_Ei", "type": "t"}],
            "clock": {"spine": {"feed": {"path": "x/feed.json", "sha256": ref["sha256"], "frame": "wall_aligned"}}}}
    KSR.restamp_feed(plan, f)
    assert plan["clock"]["spine"]["feed"]["root"] == "hub_C"
    assert plan["clock"]["spine"]["feed"]["path"] == "x/feed.json"
    plan["clock"]["spine"]["feed"]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        KSR.restamp_feed(plan, f)


def test_feed_ref_matches_schema_feed_object(tmp_path):
    # schema.py clock.spine.feed: required path/sha256/root, additionalProperties false (form/frame allowed)
    ref = KSR.feed_ref(_feed(tmp_path, v_ps_mm=290.0, note="x"))
    assert set(ref) == {"path", "sha256", "root", "form", "frame"}


def test_restamp_feed_rejects_root_outside_plan(tmp_path):
    f = _feed(tmp_path)
    plan = {"partitions": [{"name": "hub_Ei", "type": "t"}], "clock": {"spine": {}}}
    with pytest.raises(ValueError):
        KSR.restamp_feed(plan, f)
