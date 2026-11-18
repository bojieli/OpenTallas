"""FLOW-2000: the sign-off container start checks every lib / LEF / macro path the config names (headseg44 SRAM-libs failure)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff  # noqa: E402

STD = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz"


def kit(tmp_path, cfg, files=()):
    k = tmp_path / "kit"
    k.mkdir()
    for f in files:
        (k / f).parent.mkdir(parents=True, exist_ok=True)
        (k / f).write_text("x")
    (k / "config.mk").write_text(cfg)
    return k


def test_complete_kit_passes(tmp_path):
    k = kit(tmp_path, f"export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) {STD} /work/macros/m/m_tt.lib\n"
                      "export ADDITIONAL_LEFS = /work/macros/m/m.lef\nexport ADDITIONAL_LIBS = /work/macros/m/m_tt.lib\n",
            ["macros/m/m_tt.lib", "macros/m/m.lef"])
    assert signoff.container_path_preflight(k / "config.mk", k, "tt") == []


def test_missing_work_file_is_named(tmp_path):
    k = kit(tmp_path, "export TC_LIB_FILES = /work/macros/m/m_tt.lib\nexport ADDITIONAL_LEFS = /work/macros/m/m.lef\n", ["macros/m/m.lef"])
    p = signoff.container_path_preflight(k / "config.mk", k, "tt")
    assert len(p) == 1 and "TC_LIB_FILES" in p[0] and "/work/macros/m/m_tt.lib" in p[0] and "missing" in p[0]


def test_host_path_is_not_mounted(tmp_path):
    host = "/srv/opentallas-scratch2/claude/x/src/physical/asap7_memory_macros_v2/m/m_tt.lib"
    k = kit(tmp_path, f"export TC_LIB_FILES = {host}\nexport ADDITIONAL_LIBS = {host}\n")
    p = signoff.container_path_preflight(k / "config.mk", k, "tt")
    assert p and all("not mounted" in x and host in x for x in p)


def test_other_corner_field_is_not_checked(tmp_path):
    k = kit(tmp_path, "export TC_LIB_FILES = /work/a_tt.lib\nexport BC_LIB_FILES = /work/a_ff.lib\n", ["a_tt.lib"])
    assert signoff.container_path_preflight(k / "config.mk", k, "tt") == []
    assert signoff.container_path_preflight(k / "config.mk", k, "ff")


def test_kit_variable_and_line_continuation(tmp_path):
    k = kit(tmp_path, "export ADDITIONAL_LEFS = $(KIT)/a.lef \\\n  $(KIT)/b.lef\n", ["a.lef"])
    p = signoff.container_path_preflight(k / "config.mk", k, "tt")
    assert len(p) == 1 and "/work/b.lef" in p[0]


def test_run_corner_fails_before_docker(tmp_path, monkeypatch):
    k = kit(tmp_path, "export TC_LIB_FILES = /srv/host/m_tt.lib\n")
    base = tmp_path / "base"; base.mkdir()
    (tmp_path / "c.sdc").write_text("# sdc\n")
    called = []
    monkeypatch.setattr(signoff.subprocess, "call", lambda *a, **k: called.append(a) or 0)
    disc = dict(kit=str(k), base=str(base), sdc=str(tmp_path / "c.sdc"), spef=None, odb="6_final.odb")
    with pytest.raises(ValueError, match="container preflight FAILED"):
        signoff.run_corner("tt", disc, tmp_path / "out", docker="docker", dry=False)
    assert not called
