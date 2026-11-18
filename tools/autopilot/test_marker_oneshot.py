import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR

TREE = "/k/src_s81_d7w"
PLAN = "p" * 64


def cfg(**d):
    die = {"src": TREE, "src_manifest_hash": "h1", "gen_host": "epyc2", "tools_sha": "new", "plan_sha256": PLAN,
           "hold_records": [{"id": "r", "plan_sha": PLAN, "release": ["tree_ready:s81:" + TREE], "items": ["a"], "reason": "x"}]}
    die.update(d)
    return {"dies": {"s81": die}}


MARKER = {"manifest_hash": "h1", "config": {"gen_host": "epyc8", "tools_sha": "old"}, "die_gen_env": {"OT_X": "1"}}
CTX = HR.Ctx(tree_fn=lambda die, p: True, marker_fn=lambda die: MARKER)


def test_marker_never_reapplies_to_a_die_already_on_its_tree():
    c = cfg()
    assert HR.apply_tree_switches(c, CTX) == []
    d = c["dies"]["s81"]
    assert d["gen_host"] == "epyc2" and d["tools_sha"] == "new" and "die_gen_env" not in d       # derive_gen_hosts / a newer tools_sha win


def test_marker_does_not_pull_a_refreshed_die_back_to_the_marker_tree():
    c = cfg(src=TREE + "_t5144e08", superseded_trees=[TREE], src_manifest_hash="h2")
    assert HR.apply_tree_switches(c, CTX) == []
    assert c["dies"]["s81"]["src"] == TREE + "_t5144e08"
    c = cfg(src="/k/other", rollback_tree=TREE)
    assert HR.apply_tree_switches(c, CTX) == [] and c["dies"]["s81"]["src"] == "/k/other"


def test_an_unadopted_marker_tree_still_switches_once_in_memory():
    c = cfg(src="/k/old", src_manifest_hash="h0")
    out = HR.apply_tree_switches(c, CTX)
    assert out and c["dies"]["s81"]["src"] == TREE and c["dies"]["s81"]["gen_host"] == "epyc8"
