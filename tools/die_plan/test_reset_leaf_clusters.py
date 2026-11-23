#!/usr/bin/env python3
"""LEAF-CLUSTERS (FAM-KV-HROOT-R1 11-23): reset_tree.pick_cluster_taps / opt-in type.reset.leaf_clusters."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest
import reset_tree as RT

TAPS = [("clk", 10.0, 10.0), ("clk_t1", 1000.0, 20.0), ("clk_t2", 1500.0, 300.0), ("reset_local_0", 100.0, 700.0)]


def test_nearest_tap_per_cluster():
    got = RT.pick_cluster_taps(TAPS, [{"leaf_um": [1010, 30], "buses": ["a", "b"]}, {"leaf_um": [90, 690], "buses": ["c"]}])
    assert got == {"a": 1, "b": 1, "c": 3}


def test_tie_takes_lowest_index():
    taps = [("t0", 0.0, 0.0), ("t1", 20.0, 0.0)]
    assert RT.pick_cluster_taps(taps, [{"leaf_um": [10, 0], "buses": ["x"]}]) == {"x": 0}


def test_empty_is_identity():
    assert RT.pick_cluster_taps(TAPS, []) == {}


def test_bus_in_two_clusters_refused():
    with pytest.raises(RT.ResetError):
        RT.pick_cluster_taps(TAPS, [{"leaf_um": [0, 0], "buses": ["a"]}, {"leaf_um": [1500, 300], "buses": ["a"]}])


@pytest.mark.parametrize("bad", [{"buses": ["a"]}, {"leaf_um": [1, 2]}, {"leaf_um": [1, 2], "buses": []}, {"leaf_um": [1], "buses": ["a"]}])
def test_malformed_refused(bad):
    with pytest.raises(RT.ResetError):
        RT.pick_cluster_taps(TAPS, [bad])


def test_inst_taps_nearest_and_dup():
    cl = [{"leaf_um": [1010, 30], "insts": ["u_efault"]}, {"leaf_um": [90, 690], "buses": ["c"], "insts": ["u_x"]}]
    assert RT.pick_cluster_inst_taps(TAPS, cl) == {"u_efault": 1, "u_x": 3}
    assert RT.pick_cluster_taps(TAPS, cl) == {"c": 3}
    with pytest.raises(RT.ResetError):
        RT.pick_cluster_inst_taps(TAPS, cl + [{"leaf_um": [0, 0], "insts": ["u_efault"]}])


def test_insts_only_cluster_is_valid():
    assert RT.pick_cluster_taps(TAPS, [{"leaf_um": [0, 0], "insts": ["u_efault"]}]) == {}
