import os, sys

import pytest
sys.path.insert(0, os.path.dirname(__file__))
import kit_wave as KW
from test_kit_wave import cfg, _legacy_signoff_profile  # noqa: F401

OWN = """# OWNERS -- test
die\titem\tkind\tstate\towner\tlive_job\tlast_activity\tnext_step\tevidence\tdefault_owner\treplicas\tmembers
qwen_kvsys\tslw_stm_v1\ttype\tSIGNED-UNVERSIONED\tKV-PLAN\tnone\t3606m\tx\t\tKV-PLAN\t4\t
qwen_kvsys\tdone_one\ttype\tSIGNED-UNVERSIONED\tKV-PLAN\tnone\t3606m\tx\t\tKV-PLAN\t1\t
"""


@pytest.mark.parametrize("parent_state", ["SIGNED", "SIGNED-UNVERSIONED"])
def test_signed_parent_takes_class_items_and_drops_are_logged(parent_state):
    rows = KW.parse_owners(OWN.replace("SIGNED-UNVERSIONED", parent_state))
    plan = {"slw_stm_v1__cl1", "slw_stm_v1__cl2", "done_one"}
    c = cfg(take_states=["NEEDS-KIT"], only_items=["slw_stm_v1__cl1", "slw_stm_v1__cl2", "done_one"])
    picks, skip = KW.select(rows, c, "qwen_kvsys", {"items": {}}, plan)
    assert {p["item"] for p in picks} >= {"slw_stm_v1__cl1", "slw_stm_v1__cl2"}
    assert any("done_one" in v and f"SKIP state {parent_state}" in k for k, v in skip.items())


def test_signed_parent_preserves_a_current_signed_class_without_hiding_its_sibling():
    die = "qwen_kvsys"
    done, pending = "slw_stm_v1__cl1", "slw_stm_v1__cl2"
    c = cfg(take_states=["NEEDS-KIT"], only_items=[done, pending])
    event = c["dies"][die]["event"]
    key = KW.item_key(die, event, done, "done-hash")
    state = {"items": {key: {"die": die, "event": event, "item": done, "attempt": 1,
                            "status": "ENQUEUED", "q_status": "SIGNED"}}}
    picks, _ = KW.select(KW.parse_owners(OWN.replace("SIGNED-UNVERSIONED", "SIGNED")),
                         c, die, state, {done: "done-hash", pending: "pending-hash"})
    assert [p["item"] for p in picks] == [pending]
