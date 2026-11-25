"""BIND-SPEED-1124 (COORD 11-25): bind._reset_anchor_prewarm solves the anchored types' reset trees in the fork pool on a COPY of the
plan; the anchor pass then reads exactly the trees an uncached solve gives on the bind's own Plan, and a type changed in between
is solved again (its key moved)."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import reset_anchor  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402


class _B:
    def __init__(self, raw):
        self.plan, self.plan_dir = raw, HERE / "examples"

    def wavefront_plan(self):
        if not hasattr(self, "_wp"):
            self._wp = schema.Plan(self.plan, self.plan_dir / "die_plan.json")
        return self._wp


def _raw():
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw.setdefault("reset", {})["release"] = "wavefront"
    for ty in raw["partition_types"].values():
        ty.pop("contents", None)
    for tn in sorted(raw["partition_types"])[:3]:
        raw["partition_types"][tn].setdefault("clock", {})[reset_anchor.KEY] = {"marker": True}
    return raw


def _trees(P):
    out = {}
    for tn in sorted(P.types):
        try:
            out[tn] = ("ok", RT.for_type(P, tn))
        except Exception as e:  # noqa: BLE001
            out[tn] = ("err", type(e).__name__, str(e))
    return out


def test_prewarmed_anchor_trees_equal_uncached(monkeypatch):
    raw = _raw()
    monkeypatch.setenv("OT_RESET_TREE_CACHE", "0")
    ref = _trees(schema.Plan(copy.deepcopy(raw), HERE / "examples/die_plan.json"))
    monkeypatch.delenv("OT_RESET_TREE_CACHE")
    monkeypatch.setenv("OT_RESET_POOL_J", "2")
    RT.cache_clear()
    B = _B(copy.deepcopy(raw))
    bind._reset_anchor_prewarm(B, B.plan)
    anchored = sorted(tn for tn, t in raw["partition_types"].items() if reset_anchor.KEY in t.get("clock", {}))
    assert len(RT.XP_PREWARMED) == len(anchored) and RT.XP_STATS["pool"] + RT.XP_STATS["miss"] >= 1
    miss0 = RT.XP_STATS["miss"]
    got = _trees(B.wavefront_plan())                       # the bind's own Plan object reads them
    assert got == ref
    assert RT.XP_STATS["miss"] - miss0 == len(ref) - len(anchored)   # only the non-anchored types were solved on demand


def test_type_changed_after_prewarm_is_solved_again(monkeypatch):
    raw = _raw()
    monkeypatch.setenv("OT_RESET_POOL_J", "1")
    RT.cache_clear()
    B = _B(copy.deepcopy(raw))
    bind._reset_anchor_prewarm(B, B.plan)
    tn = sorted(tn for tn, t in raw["partition_types"].items() if reset_anchor.KEY in t.get("clock", {}))[0]
    B.plan["partition_types"][tn]["clock"]["bench_marker"] = 1        # the block changed before the anchor pass read it
    miss0 = RT.XP_STATS["miss"]
    try:
        RT.for_type(B.wavefront_plan(), tn)
    except Exception:  # noqa: BLE001 - a solve error is fine: it was solved again, not served
        pass
    assert RT.XP_STATS["miss"] == miss0 + 1


def test_off_switch(monkeypatch):
    monkeypatch.setenv("OT_BIND_RESET_PREWARM", "0")
    RT.cache_clear()
    B = _B(_raw())
    bind._reset_anchor_prewarm(B, B.plan)
    assert not RT.XP_PREWARMED
