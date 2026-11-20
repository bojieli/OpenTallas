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
