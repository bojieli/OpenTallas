"""ADV-DRT-M2M3: inventory only; a dense type is listed, a light one is quiet, nothing ever FAILs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_drt_m2m3 as D  # noqa: E402
import plan_advisory as PA  # noqa: E402


def _t(cells, W=1000.0, H=1000.0):
    return {"outline_um": [W, H], "cells": cells}


def test_dense_type_listed_and_labelled():
    out = D.findings({"partition_types": {"sle_fe_v2": _t(300000), "other": _t(100000)}})
    assert len(out) == 1 and out[0].startswith("WARN ADV-DRT-M2M3 INVENTORY sle_fe_v2:")
    assert "known DRT-heavy" in out[0] and "not a verdict" in out[0]


def test_light_type_quiet():
    assert D.findings({"partition_types": {"x": _t(100000), "y": {"outline_um": [10, 10]}}}) == []


def test_bus_load_alone_lists():
    # 8 bit-lanes of 1024 wires through a 8.64 um channel between two cores: hot gcells >= floor with low cell density
    a = {"inst": "a", "origin_um": [100.0, 100.0], "outline_um": [114.48, 114.48], "obs_max": "M5"}
    b = {"inst": "b", "origin_um": [223.12, 100.0], "outline_um": [114.48, 114.48], "obs_max": "M5"}
    st = [{"bits": 1024, "from_um": [218.8, 20.0], "regs_um": [[218.8, 160.0]], "to_um": [218.8, 300.0]}] * 4
    t = {"outline_um": [500.0, 400.0], "cells": 10, "hard_cores": [a, b], "internal_stations": st}
    rho, hot, peak = D.metrics(t, 10)
    assert rho < D.RHO_FLOOR and hot > 0 and peak > 1.0
    assert D.metrics(dict(t, internal_stations=[]), 10)[1] == 0


def test_never_a_fail_and_bad_rows_ok():
    out = D.findings({"partition_types": {"bad": {"outline_um": [1, 1], "cells": 5, "hard_cores": [{"inst": "z"}], "internal_stations": [{"bits": "q"}]}}})
    assert all(x.startswith("WARN ADV-DRT-M2M3") for x in out)


def test_registered():
    assert ("DRT-M2M3", "adv_drt_m2m3") in PA.CHECKS
