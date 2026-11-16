"""DRT0255 C3b (OT_PGCAP): per-gcell GRT capacity cut hook in grt_pre.tcl, default off, config lines from the gen environment."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402


def test_default_off_writes_nothing(monkeypatch):
    for k in ("OT_PGCAP", "OT_PGCAP_LAYERS", "OT_PGCAP_ADJ", "OT_PGCAP_GCELL_UM", "OT_PGCAP_EPS_DBU", "OT_PGCAP_MARGIN_DBU"):
        monkeypatch.delenv(k, raising=False)
    assert gen_phys.pgcap_cfg() == []
    monkeypatch.setenv("OT_PGCAP_ADJ", "1.0")          # a knob without the switch stays off
    assert gen_phys.pgcap_cfg() == []


def test_on_writes_switch_and_valid_knobs(monkeypatch):
    monkeypatch.setenv("OT_PGCAP", "1")
    monkeypatch.setenv("OT_PGCAP_LAYERS", "M5 M6 M7")
    monkeypatch.setenv("OT_PGCAP_ADJ", "1.0")
    monkeypatch.setenv("OT_PGCAP_GCELL_UM", "0.57")
    monkeypatch.setenv("OT_PGCAP_EPS_DBU", "10")
    out = "\n".join(gen_phys.pgcap_cfg())
    assert "export OT_PGCAP = 1" in out
    assert 'export OT_PGCAP_LAYERS = "M5 M6 M7"' in out
    assert "export OT_PGCAP_ADJ = 1.0" in out and "export OT_PGCAP_GCELL_UM = 0.57" in out and "export OT_PGCAP_EPS_DBU = 10" in out


@pytest.mark.parametrize("k,v", [("OT_PGCAP_LAYERS", "M5;rm"), ("OT_PGCAP_ADJ", "2"), ("OT_PGCAP_GCELL_UM", "x"),
                                 ("OT_PGCAP_EPS_DBU", "-1")])
def test_invalid_knob_fails_closed(monkeypatch, k, v):
    monkeypatch.setenv("OT_PGCAP", "1")
    monkeypatch.setenv(k, v)
    with pytest.raises(SystemExit):
        gen_phys.pgcap_cfg()


def test_install_appends_hook_last_only_when_on(monkeypatch, tmp_path):
    (tmp_path / "grt_pre.tcl").write_text("# kit grt_pre\nsource pg_track_truth.tcl; ot_pgtt_add\n")
    monkeypatch.delenv("OT_PGCAP", raising=False)
    assert gen_phys.pgcap_install(tmp_path) is False
    assert (tmp_path / "grt_pre.tcl").read_text() == "# kit grt_pre\nsource pg_track_truth.tcl; ot_pgtt_add\n"
    assert not (tmp_path / "pg_pair_cap.tcl").exists()                      # default kit: byte-equal, no new file
    monkeypatch.setenv("OT_PGCAP", "1")
    assert gen_phys.pgcap_install(tmp_path) is True
    assert gen_phys.pgcap_install(tmp_path) is True                         # idempotent
    t = (tmp_path / "grt_pre.tcl").read_text()
    assert t.count("ot_pgcap_add") == 1 and t.index("ot_pgtt_add") < t.index("ot_pgcap_add")
    assert 'eq "1"' in t and "proc ot_pgcap_add" in (tmp_path / "pg_pair_cap.tcl").read_text()


def test_generator_calls_install_after_file_copy():
    g = (HERE / "gen_phys.py").read_text()
    assert g.count("\n    pgcap_install(kd) ") == 1 and "cfg += pgcap_cfg()" in g
