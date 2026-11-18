import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW


def cfg(**d):
    die = {"gen_host": "epyc9", "gen_hosts": ["epyc9", "epyc7"], "hosts": ["intel1", "epyc2", "epyc7", "intel2"], "place_prefer": ["intel1", "epyc7"]}
    die.update(d)
    return {"dies": {"kv": die}, "hosts": ["intel1"]}


def test_effective_hosts_are_the_tree_holders_only():
    c = cfg()
    assert KW.tree_hosts(c, "kv", None, c["dies"]["kv"]["hosts"]) == ["epyc7", "epyc9"]
    assert KW.tree_hosts(c, "kv", None, c["dies"]["kv"]["place_prefer"], keep_order=True) == ["epyc7"]
    assert KW.tree_hosts(cfg(hosts_static=True), "kv", None, ["intel1"]) == ["intel1"]
    c2 = cfg()
    del c2["dies"]["kv"]["gen_hosts"]
    assert KW.tree_hosts(c2, "kv", None, ["a", "b"]) == ["a", "b"]


def test_rt_tools_fail_is_an_infra_retry_not_a_design_fail():
    cls, _ = KW.classify("place", "KW_RT_TOOLS FAIL: die tree /x_d22 missing on epyc1\n")
    assert cls == "INFRA"
