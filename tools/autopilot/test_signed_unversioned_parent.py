import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import kit_wave as KW
from test_kit_wave import cfg, _legacy_signoff_profile  # noqa: F401

OWN = """# OWNERS -- test
die\titem\tkind\tstate\towner\tlive_job\tlast_activity\tnext_step\tevidence\tdefault_owner\treplicas\tmembers
qwen_kvsys\tslw_stm_v1\ttype\tSIGNED-UNVERSIONED\tKV-PLAN\tnone\t3606m\tx\t\tKV-PLAN\t4\t
qwen_kvsys\tdone_one\ttype\tSIGNED-UNVERSIONED\tKV-PLAN\tnone\t3606m\tx\t\tKV-PLAN\t1\t
"""


def test_signed_unversioned_parent_takes_class_items_and_drops_are_logged():
    rows = KW.parse_owners(OWN)
    plan = {"slw_stm_v1__cl1", "slw_stm_v1__cl2", "done_one"}
    c = cfg(take_states=["NEEDS-KIT"], only_items=["slw_stm_v1__cl1", "slw_stm_v1__cl2", "done_one"])
    picks, skip = KW.select(rows, c, "qwen_kvsys", {"items": {}}, plan)
    assert {p["item"] for p in picks} >= {"slw_stm_v1__cl1", "slw_stm_v1__cl2"}
    assert any("done_one" in v and "SKIP state SIGNED-UNVERSIONED" in k for k, v in skip.items())
