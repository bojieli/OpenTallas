"""DIE-HBM-90 11-07 (HBM q_spu0/1__physical_v1 GEN_LINT rtl_check "Module hbm_arch_ft_<T> ... is not part of the
design"): a transit-only type's contents[] placeholder (status new, cells 0, no bind, no params) is not instanced;
every other contents row is emitted exactly as before."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_rtl  # noqa: E402

ROOT = HERE.parent.parent
PH = {"inst": "u_ft", "module": "tiny_ft_mid", "status": "new", "cells": 0,
      "note": "transit only: ft stations + pin registers"}


def plan(row):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["partition_types"]["mid"]["contents"].append(copy.deepcopy(row))
    return raw


def mid_text(files):
    return next(f for f in files if "mid" in f.name and not f.name.endswith("_top.sv")).read_text()


@pytest.mark.parametrize("root", [None, ROOT])
def test_placeholder_not_instanced(tmp_path, root):
    txt = mid_text(gen_rtl.write_rtl(plan(PH), tmp_path, rtl_root=root))
    assert "tiny_ft_mid u_ft" not in txt
    assert "transit-only contents placeholder" in txt
    assert "tiny_mid_core u_m" in txt          # the real leaf stays


@pytest.mark.parametrize("change", [{"cells": None}, {"bind": {"clk": "clk"}}, {"params": {"W": 4}},
                                    {"status": "reuse"}])
def test_other_rows_unchanged(tmp_path, change):
    row = dict(PH, **change)
    if row.get("cells") is None:
        row.pop("cells")
    txt = mid_text(gen_rtl.write_rtl(plan(row), tmp_path))   # no rtl_root: no leaf header check
    assert "tiny_ft_mid" in txt and " u_ft (" in txt
    assert "transit-only contents placeholder" not in txt


def test_predicate():
    assert gen_rtl.transit_placeholder(PH, {})
    assert not gen_rtl.transit_placeholder(PH, {"clk": "clk"})
    assert not gen_rtl.transit_placeholder(dict(PH, cells=5), {})
    assert not gen_rtl.transit_placeholder(dict(PH, lef="x.lef"), {})
