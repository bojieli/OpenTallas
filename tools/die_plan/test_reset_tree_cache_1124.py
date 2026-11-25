"""RESET-TREE-CACHE-1124: the process-wide reset-tree cache and the prewarm pool give exactly the trees (and errors) an uncached solve
gives, on fresh Plan objects, for pipelined and wavefront plans."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402


def _raw(release):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw.setdefault("reset", {})["release"] = release
    for ty in raw["partition_types"].values():
        ty.pop("contents", None)
    return raw


def _uncached(raw, monkeypatch):
    monkeypatch.setenv("OT_RESET_TREE_CACHE", "0")
    P = schema.Plan(copy.deepcopy(raw))
    out = {}
    for tn in sorted(P.types):
        try:
            out[tn] = ("ok", RT.for_type(P, tn))
        except Exception as e:  # noqa: BLE001
            out[tn] = ("err", type(e).__name__, str(e))
    monkeypatch.delenv("OT_RESET_TREE_CACHE")
    return out


def _cached(P):
    out = {}
    for tn in sorted(P.types):
        try:
            out[tn] = ("ok", RT.for_type(P, tn))
        except Exception as e:  # noqa: BLE001
            out[tn] = ("err", type(e).__name__, str(e))
    return out


@pytest.mark.parametrize("release", ["pipelined", "wavefront"])
def test_cached_equals_uncached_across_plan_objects(release, monkeypatch):
    raw = _raw(release)
    ref = _uncached(raw, monkeypatch)
    RT.cache_clear()
    first = _cached(schema.Plan(copy.deepcopy(raw)))
    n_miss = RT.XP_STATS["miss"]
    second = _cached(schema.Plan(copy.deepcopy(raw)))          # another Plan object of the same plan: all hits, no solve
    assert first == ref and second == ref
    assert RT.XP_STATS["miss"] == n_miss and RT.XP_STATS["hit"] >= len(ref)


@pytest.mark.parametrize("release", ["pipelined", "wavefront"])
def test_pool_prewarm_equals_uncached(release, monkeypatch):
    raw = _raw(release)
    ref = _uncached(raw, monkeypatch)
    RT.cache_clear()
    P = schema.Plan(copy.deepcopy(raw))
    info = RT.prewarm(P, sorted(P.types), jobs=2)
    assert info["todo"] == len(ref) and info["jobs"] == 2
    n_miss = RT.XP_STATS["miss"]
    assert _cached(schema.Plan(copy.deepcopy(raw))) == ref
    assert RT.XP_STATS["miss"] == n_miss                          # every type came from the pool


def test_returned_tree_is_a_copy_and_key_follows_the_type_block(monkeypatch):
    raw = _raw("pipelined")
    RT.cache_clear()
    P = schema.Plan(copy.deepcopy(raw))
    tn = sorted(P.types)[0]
    a = RT.for_type(P, tn)
    a["relays"] = "mutated"
    assert RT.for_type(P, tn)["relays"] != "mutated"
    raw2 = copy.deepcopy(raw)
    raw2["partition_types"][tn].setdefault("reset", {})["relay_um"] = 120.0
    assert RT._xp_key(schema.Plan(raw2), tn, None) != RT._xp_key(P, tn, None)
    monkeypatch.setenv("OT_RESET_TREE_CACHE", "0")
    assert RT._xp_key(P, tn, None) is None


def test_pool_size_caps(monkeypatch):
    assert RT.pool_size(3, env={"OT_RESET_POOL_J": "8"}) == 3
    assert RT.pool_size(100, env={"OT_RUN_THREADS": "2"}) <= 2
    assert RT.pool_size(100, env={"OT_RESET_POOL_GB": "100000000"}) == 1
