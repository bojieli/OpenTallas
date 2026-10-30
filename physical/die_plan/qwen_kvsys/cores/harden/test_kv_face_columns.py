"""KV core kits keep the shared face_flops.tcl margin clamp (cf2b913d2) and still patch an older unclamped text."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
FF = REPO / "tools/die_plan/face_flops.tcl"


def gen():
    spec = importlib.util.spec_from_file_location("gen_core_kit_kv_cols", HERE / "gen_core_kit_kv.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(HERE))
    return mod


def test_shared_clamped_face_flops_is_kept_unchanged():
    g = gen()
    text = FF.read_text()
    assert g.FF_COL_SHARED_CLAMP in text
    assert g.clamp_face_columns(text) == text


def test_older_unclamped_face_flops_gets_lower_margin_clamp():
    g = gen()
    old = "x\n      set col [expr {($px - $ff_x0) / $ff_cpitch}]\ny\n"
    assert g.clamp_face_columns(old) == "x\n      set col [expr {max(0, ($px - $ff_x0) / $ff_cpitch)}]\ny\n"


def test_unknown_column_search_fails_closed():
    g = gen()
    with pytest.raises(AssertionError, match="column search changed"):
        g.clamp_face_columns("set col [expr {something_else}]\n")
    both = FF.read_text() + "\nset col [expr {($px - $ff_x0) / $ff_cpitch}]\n"
    with pytest.raises(AssertionError):
        g.clamp_face_columns(both)
