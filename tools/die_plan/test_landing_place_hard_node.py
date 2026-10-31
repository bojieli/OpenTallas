"""DIE-KV-50: a hard-tree collector source (tap None, relay named in 'node', the KV modeled-PHY wrapper form) resolves
to its relay; tapped sources keep rst_n_t<tap>."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_place as LP  # noqa: E402


class _P:
    def __init__(self, src):
        tree = {"hard": True, "root": [842.4, 760.32],
                "relays": [{"q": "cland_h0", "d": "rst_root_n", "xy": [452.147, 760.32]},
                           {"q": "cland_h1", "d": "cland_h0", "xy": [431.96, 1130.387]},
                           {"q": "rst_n_t3", "d": "rst_root_n", "xy": [100.0, 200.0]}]}
        self.types = {"t": {"clock": {"landing_contract": {
            "bands": {}, "pins": [], "collector_root_node": "rst_root_n", "collector_tree": tree,
            "collector_local_sources": [dict({"name": "i_rst", "xy_um": [431.96, 1520.64]}, **src)],
            "collector_children": []}}}}


def test_source_node_forms():
    assert LP._source_node({"tap": 3}) == "rst_n_t3"
    assert LP._source_node({"tap": None, "node": "cland_h1"}) == "cland_h1"


def test_hard_tree_source_walks_its_relay_chain():
    tcl = LP.tcl(_P({"tap": None, "node": "cland_h1"}), "t")
    assert "u_cland_collect_cland_h1" in tcl and "u_cland_collect_cland_h0" in tcl
    assert "u_cland_collect_rst_n_t3" not in tcl


def test_tapped_source_unchanged():
    tcl = LP.tcl(_P({"tap": 3}), "t")
    assert "u_cland_collect_rst_n_t3" in tcl and "u_cland_collect_cland_h1" not in tcl


def test_tap_none_without_node_still_fails_closed():
    with pytest.raises((StopIteration, KeyError, RuntimeError)):
        LP.tcl(_P({"tap": None}), "t")
