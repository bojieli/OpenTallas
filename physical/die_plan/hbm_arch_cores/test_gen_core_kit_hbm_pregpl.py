"""HBM-CORES-B 11-11: gen_core_kit_hbm.py --pre-gpl-extra (opt-in extra PRE_GLOBAL_PLACE hook after face_flops.tcl)."""
import hashlib
import importlib.util
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('coregen_pgx', HERE / 'gen_core_kit_hbm.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_absent_is_unchanged(tmp_path):
    assert m.pre_gpl_extra_stage(tmp_path, None) == ("/work/face_flops.tcl", None)
    assert list(tmp_path.iterdir()) == []


def test_present_copies_and_chains(tmp_path):
    src = tmp_path / "src"; src.mkdir(); hook = src / "flc_wd_split.tcl"; hook.write_text("puts hi\n")
    kd = tmp_path / "kit"; kd.mkdir()
    tcl, rec = m.pre_gpl_extra_stage(kd, str(hook))
    assert tcl == "/work/pre_gpl_chain.tcl"
    assert (kd / "pre_gpl_extra.tcl").read_text() == "puts hi\n"
    chain = (kd / "pre_gpl_chain.tcl").read_text().splitlines()
    assert chain[1:] == ["source /work/face_flops.tcl", "source /work/pre_gpl_extra.tcl"]
    assert rec["sha256"] == hashlib.sha256(b"puts hi\n").hexdigest() and rec["source"] == str(hook.resolve())


def test_missing_file_refused(tmp_path):
    with pytest.raises(SystemExit):
        m.pre_gpl_extra_stage(tmp_path, str(tmp_path / "nope.tcl"))
