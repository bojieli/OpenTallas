import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile  # noqa: E402


def test_extra_only_keeps_tool_clustering():
    env = ref_tile.cts_sink_env({"cts_sink": {"extra": "-no_obstruction_aware"}})
    assert len(env) == 1 and "-no_obstruction_aware" in env[0]
    assert "-sink_clustering_size" not in env[0] and "-sink_clustering_max_diameter" not in env[0]


def test_size_and_diameter_unchanged():
    env = ref_tile.cts_sink_env({"cts_sink": {"size": 16, "diameter_um": 20}})
    assert "-sink_clustering_size 16 -sink_clustering_max_diameter 20" in env[0]


def test_half_given_or_empty_refused():
    with pytest.raises(ref_tile.SpecError):
        ref_tile.cts_sink_env({"cts_sink": {"size": 16}})
    with pytest.raises(ref_tile.SpecError):
        ref_tile.cts_sink_env({"cts_sink": {"extra": ""}})
    assert ref_tile.cts_sink_env({}) == []


def test_sink_clustering_false_drops_enable():
    env = ref_tile.cts_sink_env({"cts_sink": {"sink_clustering": False, "extra": "-no_obstruction_aware"}})
    assert "-sink_clustering_enable" not in env[0] and "-no_obstruction_aware" in env[0]
    assert "-repair_clock_nets" in env[0]
    env = ref_tile.cts_sink_env({"cts_sink": {"sink_clustering": False}})
    assert "-sink_clustering_enable" not in env[0]
    assert "-sink_clustering_enable" in ref_tile.cts_sink_env({"cts_sink": {"extra": "-no_obstruction_aware"}})[0]


def test_sink_clustering_false_with_size_or_non_bool_refused():
    with pytest.raises(ref_tile.SpecError):
        ref_tile.cts_sink_env({"cts_sink": {"sink_clustering": False, "size": 16, "diameter_um": 20}})
    with pytest.raises(ref_tile.SpecError):
        ref_tile.cts_sink_env({"cts_sink": {"sink_clustering": "no"}})
