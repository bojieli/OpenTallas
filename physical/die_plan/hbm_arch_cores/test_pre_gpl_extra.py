"""KW-FIX-45 11-11: opt-in --pre-gpl-extra hook chain (default off = unchanged)."""
import hashlib
import importlib.util
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coregen_pg", HERE / "gen_core_kit_hbm.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_chain_sources_face_flops_then_extras_in_order(tmp_path):
    kd = tmp_path / "kit"; kd.mkdir()
    a = tmp_path / "flc_wd_split.tcl"; a.write_text("puts A\n")
    b = tmp_path / "second.tcl"; b.write_text("puts B\n")
    lines, rec = m.pre_gpl_extra_setup(kd, [str(a), str(b)])
    assert lines == ["export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl_chain.tcl"]
    chain = (kd / "pre_gpl_chain.tcl").read_text().splitlines()
    assert chain[1:] == ["source /work/face_flops.tcl", "source /work/pre_gpl_extra_0_flc_wd_split.tcl",
                         "source /work/pre_gpl_extra_1_second.tcl"]
    assert (kd / "pre_gpl_extra_0_flc_wd_split.tcl").read_text() == "puts A\n"
    assert rec[0]["sha256"] == hashlib.sha256(b"puts A\n").hexdigest() and rec[1]["name"] == "pre_gpl_extra_1_second.tcl"


def test_missing_file_refuses(tmp_path):
    with pytest.raises(SystemExit):
        m.pre_gpl_extra_setup(tmp_path, [str(tmp_path / "nope.tcl")])


def test_flag_is_declared_and_default_empty():
    src = (HERE / "gen_core_kit_hbm.py").read_text()
    assert '"--pre-gpl-extra", action="append", default=[]' in src
    assert 'export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl' in src          # the default line is untouched
    assert 'if a.pre_gpl_extra:' in src
