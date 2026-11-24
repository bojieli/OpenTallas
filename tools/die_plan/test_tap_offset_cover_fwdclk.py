import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tap_offset_cover as C  # noqa: E402


def test_fwdclk_repick_off_by_env(monkeypatch):
    monkeypatch.setenv("OT_FWDCLK_REPICK", "0")
    assert C.fwdclk_repick({"partition_types": {}}, "x.json") == []


def test_fwdclk_repick_never_fails_the_fill(monkeypatch, capsys):
    monkeypatch.delenv("OT_FWDCLK_REPICK", raising=False)
    import fwdclk_repoint as FR
    monkeypatch.setattr(FR, "repick_report", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(C.S, "Plan", lambda raw, p: None)
    out = C.fwdclk_repick({"partition_types": {}}, "x.json")
    assert out and out[0].startswith("WARN FWDCLK-REPICK not checked (RuntimeError")


def test_fwdclk_repick_prints_report(monkeypatch, capsys):
    monkeypatch.delenv("OT_FWDCLK_REPICK", raising=False)
    import fwdclk_repoint as FR
    monkeypatch.setattr(C.S, "Plan", lambda raw, p: None)
    monkeypatch.setattr(FR, "repick_report", lambda raw, P, types, W: [dict(type="T", pin="fclk_out_x", old="a", old_um=400,
                                                                       new="b", new_um=20, basis="UNMEASURED")])
    out = C.fwdclk_repick({"partition_types": {"T": {}, "U": {}}}, "x.json", types="^T$")
    assert "WARN FWDCLK-REPICK T: fclk_out_x <- a 400 um -> b 20 um (UNMEASURED" in capsys.readouterr().out
    assert out[-1].startswith("FWDCLK-REPICK report-only: 1")
