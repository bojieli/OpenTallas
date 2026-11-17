"""KIT-COMMON-1117: gen_phys type kits and core_flow (legacy-profile) kits stage the same shared helpers."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_common_files as K  # noqa: E402


def test_sources_exist():
    for name in K.FILES:
        assert K.source(name).is_file(), name


def test_stage_copies_all(tmp_path):
    got = K.stage(tmp_path)
    assert got == sorted(K.FILES)
    for name in K.FILES:
        assert (tmp_path / name).read_bytes() == K.source(name).read_bytes()


def test_guard_in_list_and_sourced_by_shared_tools():
    # the 11-17 failure: core_final_repair.tcl (core_flow kits) sources hold_sdc_guard.tcl
    assert "hold_sdc_guard.tcl" in K.FILES
    assert "hold_sdc_guard.tcl" in (HERE / "core_final_repair.tcl").read_text()


def test_both_paths_read_the_shared_list():
    gp = (HERE / "gen_phys.py").read_text()
    cf = (HERE / "core_flow.py").read_text()
    assert "kit_common_files.stage(kd)" in gp
    assert "kit_common_files.stage(kd)" in cf
    # no private copy of a shared helper left in either path (they would drift again)
    for src, text in (("gen_phys.py", gp), ("core_flow.py", cf)):
        for name in K.FILES:
            assert not re.search(r'shutil\.copyfile\([^\n]*kd / "%s"\)' % re.escape(name), text), (src, name)


def test_core_flow_apply_stages_guard(tmp_path, monkeypatch):
    import core_flow
    monkeypatch.setattr(core_flow, "stage_grt183", lambda kd: None)
    try:
        core_flow.apply(tmp_path, {}, "kl_t")
    except Exception:
        pass   # later config work may need a real kit; the helpers are staged first
    for name in K.FILES:
        assert (tmp_path / name).is_file(), name
