"""KIT-OPS-6 11-15: protect_sync protects every die's kit_rtl/bind dirs (cleanup pruned live bind worktrees) -- lane_root + kr_paths."""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parent / "protect_sync.py").read_text()


def _ns():
    ns = {"re": re, "os": __import__("os"), "paths": set()}
    ns["add"] = lambda p: ns["paths"].add(p)
    for name in ("lane_root", "kr_paths"):
        m = re.search(r"^def %s\(.*?(?=^\S)" % name, SRC, re.S | re.M)
        exec(m.group(0), ns)
    return ns


def test_lane_root_keeps_the_tree_that_holds_the_hdl():
    ns = _ns()
    assert ns["lane_root"]("/srv/opentallas-scratch2/claude/kv-102/cg3/kv_tree15/rtl/qwen_sys/a.sv") == "/srv/opentallas-scratch2/claude/kv-102/cg3/kv_tree15"
    assert ns["lane_root"]("/home/ubuntu/x/rtl/a.sv") is None


def test_kr_paths_adds_bind_out_asbuilt_script_and_dirs():
    ns = _ns()
    bo = ns["kr_paths"]({"bind_out": "/srv/opentallas-scratch2/claude/q/bind/out", "asbuilt": "/srv/opentallas-scratch2/claude/q/ab.json", "script": "/srv/x"})
    assert bo == "/srv/opentallas-scratch2/claude/q/bind/out"
    assert {"/srv/opentallas-scratch2/claude/q/bind", "/srv/opentallas-scratch2/claude/q", "/srv/opentallas-scratch2/claude/q/bind/out"} <= ns["paths"]


def test_item_inputs_and_hub_are_covered():
    assert 'd.get("item_inputs")' in SRC and "the hub itself" in SRC and "bind_named_sources" in SRC
