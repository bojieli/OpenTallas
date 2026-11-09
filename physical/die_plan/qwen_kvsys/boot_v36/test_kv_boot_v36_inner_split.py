"""DIE-KV-97 11-09: kv_boot_v36 prices changed INNER rows of the KV PC core split (PCC keeps the leaf path and names the split
bus <port>_c, PCF is <path>_f with <port>_f) on the as-built kvpc<->slg relay bus; an unpriced changed INNER edge still stops prep."""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("kv_boot_v36", HERE / "kv_boot_v36.py")
KB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(KB)

SPLITS = [{"from": "qkd_kvs_pc", "pcc": "qkd_kvs_pcc", "pcf": "qkd_kvs_pcf",
           "split": {"i_grp": {"pcc": [0], "pcf": [1], "pcc_port": "i_grp_c", "pcf_port": "i_grp_f"},
                     "o_grp": {"pcc": [0], "pcf": [1], "pcc_port": "o_grp_c", "pcf_port": "o_grp_f"}}}]


def inner(sink, port, source, asb, bnd):
    part = "pc_EN_1"
    return dict(id=f"INNER:{part}:{sink}.{port}<-{source}@{asb}", kind="intra", sink=sink, sink_part=part, src_part=part,
                sink_port=port, source=source, asbuilt_stages=asb, landed_stages=bnd, lane=f"INNER:{part}")


def groups(tmp_path, rows):
    f = tmp_path / "bus_groups.json"
    f.write_text(json.dumps(dict(landing=[], internal=rows)))
    return f


def bus(src, sp, dst, dp, stages):
    return {"id": f"{src}.{sp} -> {dst}.{dp}", "src": {"inst": src, "port": sp}, "dst": {"inst": dst, "port": dp},
            "stages": stages}


ROWS = [inner("kvpc_EN_5", "i_grp_c", "slg_EN_5.o_pc1", 1, 3),          # PCC half of slg_EN_5.o_pc1 -> kvpc_EN_5.i_grp
        inner("kvpc_EN_5_f", "i_grp_f", "slg_EN_5.o_pc1", 1, 3),        # PCF half of the same bus
        inner("slg_EN_5", "i_pc1", "kvpc_EN_5.o_grp_c", 3, 6),          # return bus, PCC half
        inner("slg_EN_5", "i_pc1", "kvpc_EN_5_f.o_grp_f", 3, 6)]        # return bus, PCF half
RS = {"buses": [bus("slg_EN_5", "o_pc1", "kvpc_EN_5", "i_grp", 1), bus("kvpc_EN_5", "o_grp", "slg_EN_5", "i_pc1", 3),
                bus("slg_EN_4", "o_pc0", "kvpc_EN_0", "i_grp", 2)]}


def test_split_halves_priced_on_asbuilt_bus(tmp_path):
    G = KB.Groups(groups(tmp_path, ROWS), SPLITS)
    out, rows = KB.overlay_relay_stages(RS, G)
    G.require_inner_priced()                                            # all four halves consumed
    st = {b["id"]: b["stages"] for b in out["buses"]}
    assert st["slg_EN_5.o_pc1 -> kvpc_EN_5.i_grp"] == 3                 # bound = landed depth of the bus (LANDED)
    assert st["kvpc_EN_5.o_grp -> slg_EN_5.i_pc1"] == 6
    assert st["slg_EN_4.o_pc0 -> kvpc_EN_0.i_grp"] == 2                 # no changed member: unchanged as-built value
    assert {r["key"]: r["members"] for r in rows} == {"slg_EN_5.o_pc1 -> kvpc_EN_5.i_grp": 2, "kvpc_EN_5.o_grp -> slg_EN_5.i_pc1": 2}


def test_without_split_map_the_guard_still_stops(tmp_path):
    """control: the same rows with no core_splits map are not matched by any bus and prep refuses (the 11-08/11-09 failure)"""
    G = KB.Groups(groups(tmp_path, ROWS), None)
    KB.overlay_relay_stages(RS, G)
    with pytest.raises(ValueError, match="Unpriced changed INNER edges"):
        G.require_inner_priced()


def test_unpriced_inner_edge_still_raises(tmp_path):
    """failing control: a changed INNER edge with no relay bus (here a split half of a bus the table lacks) stays unpriced"""
    rows = ROWS + [inner("kvpc_EN_9_f", "i_grp_f", "slg_EN_7.o_pc2", 1, 2)]
    G = KB.Groups(groups(tmp_path, rows), SPLITS)
    KB.overlay_relay_stages(RS, G)
    with pytest.raises(ValueError, match=r"kvpc_EN_9_f\.i_grp_f<-slg_EN_7\.o_pc2"):
        G.require_inner_priced()


def test_pcf_port_on_unsuffixed_leaf_is_refused(tmp_path):
    with pytest.raises(ValueError, match="without the _f suffix"):
        KB.Groups(groups(tmp_path, [inner("kvpc_EN_5", "i_grp_f", "slg_EN_5.o_pc1", 1, 3)]), SPLITS)


def test_repo_core_splits_file_names_the_kv_split():
    root = HERE.parents[3]
    f = root / "physical/die_plan/qwen_kvsys/plan_of_record/kv67_1104/core_splits.json"
    al = KB.split_aliases(KB.load_splits(f))
    assert al["i_grp_c"] == ("i_grp", "pcc", "_f") and al["o_grp_f"] == ("o_grp", "pcf", "_f")
