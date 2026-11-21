"""RESET-COHORT-1119: collectors fed only by the chain predecessor / a root-reset register (t1 a32 collectors 149 150 159-163 167 170,
t15 a11 collector264) are their own cohort members instead of 'ambiguous/missing actual driver []'.  Undriven collectors still fail closed."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import reset_cohort_model as M
import serdes_cohorts_env as E


def _graph(tmp_path, collectors):
    rows = ["TAP\tclk_t1\t100\t100", "TAP\tclk_t2\t300\t100",
            "NODE\tRRL\t0\tu_rrl_0/q\t90\t90\tFIRM\tclk", "NODE\tRRL\t1\tu_rrl_1/q\t310\t110\tFIRM\tclk",
            "FANIN\tRRL\t1\tu_rrl_1/q\tD\t0"]
    for cid, xy, fan in collectors:
        rows.append(f"NODE\tCOLLECTOR\t{cid}\tu_cland_collect_rst_rl_{cid}/q\t{xy[0]}\t{xy[1]}\tFIRM\tclk")
        rows.append(f"FANIN\tCOLLECTOR\t{cid}\tu_cland_collect_rst_rl_{cid}/q\tD\t{fan}")
    p = tmp_path / "g.tsv"
    p.write_text("\n".join(rows) + "\n")
    return p


def test_root_fed_collectors_are_own_members_t1_t15_shape(tmp_path):
    g = _graph(tmp_path, [(148, (95, 95), "0"), (149, (105, 100), "root"), (150, (295, 100), "root"), (264, (110, 95), "root")])
    r = M.model(g, hop_um=405.0, auto_encoder=False)
    assert [x["key"] for x in r["root_collector_groups"]] == ["c149", "c150", "c264"]
    assert all(x["light_root_fit"] and x["root_candidates"] for x in r["root_collector_groups"])
    assert r["collector_actual_owners"] == {"148": 0}
    assert all(149 not in x["rrl_ids"] for x in r["groups"])            # not mixed into RRL cohorts
    assert r["unfit_light_root_groups"] == []
    v = E.env_values(r)
    assert "serdes_rst_c149:" in v["OT_TAP_GROUP_FIXED"] and "c149" not in v["OT_SERDES_RELAY_COHORTS"]


def test_rrl_owner_wins_over_root_marker(tmp_path):
    g = _graph(tmp_path, [(10, (95, 95), "0,root")])
    r = M.model(g, auto_encoder=False)
    assert r["collector_actual_owners"] == {"10": 0} and r["root_collector_groups"] == []


def test_truly_undriven_collector_still_fails_closed(tmp_path):
    g = _graph(tmp_path, [(149, (105, 100), "")])
    with pytest.raises(ValueError, match="collector149 ambiguous/missing"):
        M.model(g, auto_encoder=False)


def test_two_rrl_owners_still_ambiguous(tmp_path):
    g = _graph(tmp_path, [(5, (105, 100), "0,1,root")])
    with pytest.raises(ValueError, match="ambiguous"):
        M.model(g, auto_encoder=False)


def test_root_collector_out_of_reach_is_unfit(tmp_path):
    g = _graph(tmp_path, [(7, (5000, 5000), "root")])
    r = M.model(g, auto_encoder=False)
    assert r["unfit_light_root_groups"] == ["c7"]
    with pytest.raises(SystemExit):
        E.env_values(r)


def test_tcl_trace_marks_root_registers():
    d = Path(__file__).parent
    for f in ("serdes_reset_graph.tcl", "clock_taps.tcl"):
        assert "u_cland_(?:reset_rst_rl|collect_rst_rl)" in (d / f).read_text()


def test_union_never_loses_the_light_root_t4_edge_shape(tmp_path):
    """FAM-S81-SERDES-R4 11-21 (serdes__t4 J6 rep, CTS fail-closed 'unfit light-root groups [222]'): RRL 222 / 223 sit 278 um
    apart on the die edge, 148 um below the tap row.  Each alone fits its own tap; their union fit the 405 um bbox but no tap
    reached both.  The union is refused, both parts keep a root, and the old union is recorded as rejected."""
    rows = ["TAP\tclk_t2\t901.792\t152.864", "TAP\tclk_t3\t1262.496\t152.864",
            "NODE\tRRL\t222\tu_rrl_222/q\t1239.84\t4.32\tPLACED\tclk",
            "NODE\tRRL\t223\tu_rrl_223/q\t966.168\t4.59\tPLACED\tclk",
            "FANIN\tRRL\t223\tu_rrl_223/q\tD\t222"]
    for cid, x in ((222, 1239.678), (222, 1242.378), (223, 964.71), (223, 967.41)):
        rows.append(f"NODE\tCOLLECTOR\t{cid}\tu_cland_collect_rst_rl_{cid}/q{x}\t{x}\t4.59\tFIRM\tclk")
        rows.append(f"FANIN\tCOLLECTOR\t{cid}\tu_cland_collect_rst_rl_{cid}/q{x}\tD\t{cid}")
    g = tmp_path / "t4.tsv"
    g.write_text("\n".join(rows) + "\n")
    r = M.model(g, hop_um=405.0, auto_encoder=False)
    assert r["unfit_light_root_groups"] == []
    assert sorted(x["key"] for x in r["groups"]) == [222, 223]
    assert {x["key"]: x["root_candidates"][0]["name"] for x in r["groups"]} == {222: "clk_t3", 223: "clk_t2"}
    assert any(x.get("rejected_union_no_light_root") for x in r["rejected_unions"])
    E.env_values(r)                                                     # no fail-closed raise
