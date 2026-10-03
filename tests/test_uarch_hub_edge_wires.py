import sys
import hashlib
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import uarch_model as u
import uarch_model_par2_boundary as x


def test_package_replaces_proxy_with_both_routed_endpoints():
    hop = dict(link="UCIe", latency_s=10e-9)
    full = hop["latency_s"] + u.hub_edge_hop_wire_s(hop, 1.2e9, u.DIE_SHRUNK_INTERIM)
    assert full == pytest.approx(65.16666666666667e-9)
    assert full == pytest.approx(x.one_way_s(x.default_cfg("owner"), 1.2e9))


def test_board_and_older_die_have_positive_wire_costs():
    assert u.hub_edge_hop_wire_s(dict(link="board"), 1.2e9, u.DIE_SHRUNK_INTERIM) == 90 / 1.2e9
    assert u.hub_edge_hop_wire_s(dict(link="UCIe"), 1.2e9) == 74 / 1.2e9 - 1.5e-9
    with pytest.raises(ValueError):
        u.hub_edge_hop_wire_s(dict(link="UCIe"), 0)


@pytest.mark.parametrize("kind,stage", [("stage", 1), ("substage", 1), ("head", 1),
                                         ("engram", None), ("return", None)])
@pytest.mark.parametrize("ss_wire", [False, True])
def test_every_hop_is_charged_even_without_optional_ss_retiming(kind, stage, ss_wire):
    g = u.A.D.Graph()
    g.add("token.return", [], layer=None, kind="hop", hop_kind=kind,
          stage=stage, payload=32, depth=100e-9)
    out = u._cons_adjust(g, 1, 1.2e9, "columns", 1, {}, ss_wire=ss_wire,
                         die=u.DIE_SHRUNK_INTERIM)
    node = g.nodes["token.return"]
    assert node["_hub_edge_s"] > 50e-9
    assert out == pytest.approx(100e-9 + node["_hub_edge_s"])


def test_layer_split_replaces_full_base_path_once():
    cfg = x.default_cfg("layer_split", board="fc4")
    base, _ = x._fabrics(cfg)
    hop = base.hop("stage", 32, 1)
    g = u.A.D.Graph()
    g.add("token.return", [], layer=None, kind="hop", hop_kind="stage",
          stage=1, payload=32, depth=hop["latency_s"], issue=hop["bytes_s"])
    u._cons_adjust(g, 1, 1.2e9, "columns", 1, {}, die=u.DIE_SHRUNK_INTERIM)
    x.apply(g, 1, 1.2e9, cfg, set(), 116)
    assert g.nodes["token.return"]["depth"] == pytest.approx(x.one_way_s(cfg, 1.2e9))


def test_local_operations_receive_no_remote_wire_charge():
    g = u.A.D.Graph()
    g.add("token.return", [], layer=None, kind="op", depth=3e-9)
    assert u._cons_adjust(g, 1, 1.2e9, "columns", 1, {}, die=u.DIE_SHRUNK_INTERIM) == 3e-9
    assert "_hub_edge_s" not in g.nodes["token.return"]


@pytest.mark.parametrize("mode", x.MODES)
def test_no_mapping_or_proposed_edge_root_erases_routed_endpoint_floor(mode):
    cfg = x.default_cfg(mode, edge_root_extra_stages=0)
    assert x.one_way_s(cfg, 1.2e9) >= 2 * 34 / 1.2e9 + 8.5e-9
    with pytest.raises(ValueError):
        x.default_cfg(mode, vm_ucie_stages=0)


def test_mirrored_forward_pays_wire_latency_even_for_tiny_payload():
    cfg = x.default_cfg("mirror_hub", board="fc4")
    base, new = x._fabrics(cfg)
    hop = base.hop("stage", 1, 1)
    g = u.A.D.Graph()
    g.add("token.return", [], layer=None, kind="hop", hop_kind="stage",
          stage=1, payload=1, depth=hop["latency_s"], issue=hop["bytes_s"])
    u._cons_adjust(g, 1, 1.2e9, "columns", 1, {}, die=u.DIE_SHRUNK_INTERIM)
    x.apply(g, 1, 1.2e9, cfg, set(), 58)
    other = new.hop("stage", 1, 1)
    expected = other["latency_s"] + u.hub_edge_hop_wire_s(other, 1.2e9, u.DIE_SHRUNK_INTERIM)
    assert g.nodes["token.return"]["depth"] == pytest.approx(expected + x.one_way_s(cfg, 1.2e9))


def test_composed_model_binds_current_sources_and_preserves_historical_record():
    root = Path(__file__).resolve().parents[1]
    record = json.loads((root / "results/uarch/dsrom_hub_edge_wires_20261003/model.json").read_text())
    for source, digest in record["source_sha256"].items():
        actual = hashlib.sha256((root / source).read_bytes()).hexdigest()
        if source == "tools/uarch_model.py" and actual != digest:
            # A separately priced GPU-source correction follows this frozen
            # wire record; it must bind current code and the unchanged record.
            successor = json.loads((root / "results/uarch/dsrom_gpu_index_scan_correction_20261003/model.json").read_text())
            assert successor["source_sha256"][source] == actual
            assert successor["unchanged_wire_result_sha256"] == hashlib.sha256(
                (root / "results/uarch/dsrom_hub_edge_wires_20261003/model.json").read_bytes()).hexdigest()
        else:
            assert actual == digest
    assert len(record["results"]) == 6
    assert record["endpoint_wires_in_all_mappings"]
    assert min(record["link"]["one_way_ns"].values()) >= 65.16
    historical = json.loads((root / "results/uarch/dsrom_par2_boundary_20261003/model.json").read_text())
    assert historical["baseline_reproduced"]
