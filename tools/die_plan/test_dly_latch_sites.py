import json
from pathlib import Path

import pytest

from tools.die_plan import dly_latch_sites, schema


def example():
    return {
        "outline_um": [100, 100],
        "dly_latch_sites": [{
            "latch": "u_bound.u_fl_pd_7_i/q$_DLATCH_N_",
            "master": "DLLx1_ASAP7_75t_R",
            "launch": "u_bound.u_pd1.q$_DFF_P_",
            "capture": "u_bound.u_pd2.q$_DFF_P_",
            "launch_tap": "clk_t4",
            "capture_tap": "clk_t5",
            "origin_um": [23.166, 9.72],
        }],
    }


def test_exact_seating_and_phase_hooks(tmp_path):
    release = tmp_path / "face_flops_release.tcl"
    phase = tmp_path / "pre_cts.tcl"
    release.write_text("source /work/dly_spread.tcl\n")
    phase.write_text("source /work/clock_taps.tcl\nsource /work/clock_edge_split.tcl\n")
    row = example()
    dly_latch_sites.install(tmp_path, row, "pv", "warn", {"segment": 1})
    assert release.read_text().splitlines()[-1] == "ot_dly_site::run place /work/dly_latch_sites.tsv"
    assert phase.read_text().splitlines() == [
        "source /work/clock_taps.tcl",
        "source /work/dly_latch_sites.tcl",
        "ot_dly_site::run phase /work/dly_latch_sites.tsv",
        "source /work/clock_edge_split.tcl",
    ]
    table = (tmp_path / "dly_latch_sites.tsv").read_text().strip().split("\t")
    assert table[0] == row["dly_latch_sites"][0]["latch"]
    assert table[-4:] == ["clk_t4", "clk_t5", "23.166", "9.720"]
    wire = json.loads(Path(schema.__file__).with_name("die_plan.schema.json").read_text())
    key = lambda s: s["properties"]["partition_types"]["additionalProperties"]["properties"]["dly_latch_sites"]
    assert key(wire) == key(schema.SCHEMA)


def test_inconsistent_rows_fail_before_emitting(tmp_path):
    row = example()
    with pytest.raises(ValueError, match="spread and lockup"):
        dly_latch_sites.install(tmp_path, row, "pv", None, {})
    row["dly_latch_sites"].append(dict(row["dly_latch_sites"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        dly_latch_sites.install(tmp_path, row, "pv", "warn", {"segment": 1})
    row["dly_latch_sites"].pop()
    row["dly_latch_sites"][0]["origin_um"][0] += 0.0005
    with pytest.raises(ValueError, match="database grid"):
        dly_latch_sites.install(tmp_path, row, "pv", "warn", {"segment": 1})
    assert not list(tmp_path.iterdir())
