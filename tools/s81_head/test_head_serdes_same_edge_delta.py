"""DIE-HEAD-75 11-06: head_serdes_same_edge_delta.add_row (l48ui): pma_rx same-edge row on the hd_serdes pma_rck pad clock."""
import copy, os, sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import head_serdes_same_edge_delta as D


def plan():
    pins = [{"name": "pma_rck", "dir": "in", "period_ps": 833.0},
            {"name": "pma_tck", "dir": "out", "period_ps": 833.0, "source_clock_port": "clk"}]
    return {"partition_types": {"hd_serdes": {"clock": {"pad_clock": {"pins": pins}}},
                                "hd_tile": {"clock": {}}}}


def test_adds_one_same_edge_row_only_on_rck():
    P = plan(); before = copy.deepcopy(P)
    rck = D.add_row(P)
    assert rck["data_inputs"] == [D.ROW]
    row = rck["data_inputs"][0]
    assert row["port"] == "pma_rx" and row["capture"] == "same_edge"
    assert (row["max_ps"], row["min_ps"], row["eye_hold_extra_ps"]) == (166.6, -90.0, 175.0)
    del rck["data_inputs"]
    assert P == before                                  # nothing else changed


def test_refuses_second_application():
    P = plan(); D.add_row(P)
    with pytest.raises(AssertionError):
        D.add_row(P)


def test_refuses_missing_or_output_rck():
    P = plan(); P["partition_types"]["hd_serdes"]["clock"]["pad_clock"]["pins"][0]["dir"] = "out"
    with pytest.raises(AssertionError):
        D.add_row(P)
