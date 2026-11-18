import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW


class AP:
    DRY = True
    HUB_NAME = "hub"
    logs = []
    log = staticmethod(lambda m: AP.logs.append(m))
    sh = staticmethod(lambda *a, **k: (0, "", ""))


def mk(blocks):
    cfg = {"dies": {"s": {"enabled": True, "event": "e2", "plan": "/p.json", "gen_host": "h"}}}
    st = {"plans": ({"h:/p.json|e2": {"blocks": blocks}} if blocks is not None else {}),
          "adopt_seen": {"s": {"switched": True}},
          "items": {"a": {"die": "s", "item": "a", "event": "e1", "status": "RUNNING", "unit": "u", "block_sha": "b1", "dir": "/nonexistent"},
                    "b": {"die": "s", "item": "b", "event": "e1", "status": "RUNNING", "unit": "u", "block_sha": "b2", "dir": "/nonexistent"}}}
    return cfg, st


def test_only_the_item_whose_block_changed_is_cancelled():
    cfg, st = mk({"a": "b1", "b": "bX"})
    KW.supersede_on_switch(AP, cfg, st, {})
    assert st["items"]["a"]["status"] == "RUNNING" and st["items"]["b"]["status"] == "CANCELLED"


def test_nothing_is_cancelled_before_the_new_plan_is_probed():
    cfg, st = mk(None)
    KW.supersede_on_switch(AP, cfg, st, {})
    assert [r["status"] for r in st["items"].values()] == ["RUNNING", "RUNNING"]
    st["plans"]["h:/p.json|e2"] = {"blocks": {"a": "b1", "b": "bX"}}            # probe arrives: the window is still open
    KW.supersede_on_switch(AP, cfg, st, {})
    assert st["items"]["b"]["status"] == "CANCELLED" and st["items"]["a"]["status"] == "RUNNING"
