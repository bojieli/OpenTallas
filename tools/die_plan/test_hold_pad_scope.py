"""KV-HOLD-STRUCT 11-25: OT_HOLD_PAD_SCOPE=zlxt, the opt-in scope of the family-margin hold pad (default off)."""
import shutil
import subprocess
from pathlib import Path
import pytest
import pregrt_ff_hold as PG
import test_hold_pad as TH

HERE = Path(__file__).resolve().parent


def test_gen_knob_off_by_default_and_baked_when_on(monkeypatch):
    monkeypatch.delenv("OT_HOLD_PAD_SCOPE", raising=False)
    assert PG.pad_scope() == ""
    assert 'set ::env(OT_HOLD_PAD_SCOPE) "zlxt"' not in PG.tail_text()
    monkeypatch.setenv("OT_HOLD_PAD_SCOPE", "zlxt")
    assert PG.pad_scope() == "zlxt"
    assert 'set ::env(OT_HOLD_PAD_SCOPE) "zlxt"' in PG.tail_text()
    monkeypatch.setenv("OT_HOLD_PAD_SCOPE", "bogus")
    with pytest.raises(ValueError):
        PG.pad_scope()


def run_scope(tmp_path, ends, verdicts, on):
    """ends rows as in test_hold_pad; verdicts = {endpoint: keep|drop|unk|boom} stub of ot_hp_scope_keep"""
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    e = " ".join("{%s}" % " ".join(str(x) for x in row) for row in ends)
    v = " ".join("%s %s" % (k, x) for k, x in verdicts.items())
    env = 'set ::env(OT_HOLD_PAD_SCOPE) zlxt\n' if on else ''
    body = ("namespace eval ord {}\nnamespace eval sta {}\n" + TH.STUB + env + f"\nset ::E {{{e}}}\n"
            + (HERE / "hold_pad.tcl").read_text()
            + f"\nset ::V {{{v}}}\n"
            + "proc ot_hp_scope_keep {it pe pin} { set r [dict get $::V $pin]; if {$r eq \"boom\"} { error x }; return $r }\n"
            + f"\nputs \"N [ot_hold_pad t 40 0 {tmp_path}]\"\n")
    (tmp_path / "t.tcl").write_text(body)
    r = subprocess.run(["tclsh", str(tmp_path / "t.tcl")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


ENDS = [("a", 10, 500, "reg"), ("b", 12, 500, "reg"), ("c", 20, 500, "reg"), ("d", 25, 500, "reg")]
VERD = {"a": "keep", "b": "drop", "c": "unk", "d": "boom"}


def test_scope_off_pads_everything(tmp_path):
    out = run_scope(tmp_path, ENDS, VERD, on=False)
    assert "N 8" not in out and "scope zlxt" not in out
    assert "ends 4 padded 4" in out


def test_scope_on_drops_same_tap_logic_keeps_unknown(tmp_path):
    out = run_scope(tmp_path, ENDS, VERD, on=True)
    assert "ends 3 padded 3" in out                  # b dropped; a keep, c unk kept, d error -> unk kept
    assert "scope zlxt: scope_dropped 1 scope_unk 2 kept 3" in out


def test_config_line_and_refresh_keep_scope(tmp_path, monkeypatch):
    on = {"clock": {"pregrt_ff_hold": True}}
    monkeypatch.delenv("OT_HOLD_PAD_SCOPE", raising=False)
    assert not any("OT_HOLD_PAD_SCOPE" in x for x in PG.config_lines(on))
    monkeypatch.setenv("OT_HOLD_PAD_SCOPE", "zlxt")
    assert "export OT_HOLD_PAD_SCOPE = zlxt" in PG.config_lines(on)
    (tmp_path / "hold_gate.tcl").write_text((HERE / "hold_gate.tcl").read_text())
    assert PG.install(on, tmp_path)
    monkeypatch.delenv("OT_HOLD_PAD_SCOPE")          # the refresh runs without the gen env
    f = tmp_path / "pregrt_ff_hold.tcl"
    f.write_text(f.read_text().replace('set ::env(OT_HOLD_PAD_SCOPE) "zlxt"', "#"))   # a kit baked before the knob
    (tmp_path / "config.mk").write_text("export OT_HOLD_PAD_SCOPE = zlxt\n")
    assert PG.refresh(tmp_path).startswith("refreshed")
    assert 'set ::env(OT_HOLD_PAD_SCOPE) "zlxt"' in f.read_text()
    assert "OT_HOLD_PAD_SCOPE" not in __import__("os").environ
