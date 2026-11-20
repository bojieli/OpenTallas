"""OPUS-FIX-S81-SLICEC 11-20: relay_mid.tcl HALF exports (gen_phys._relay_mid_half) and the plan schema keys."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402
import schema  # noqa: E402


def _clean_env(monkeypatch):
    for k in ("OT_RELAY_MID_HALF_SRC_RE", "OT_RELAY_MID_HALF_SINK_RE"):
        monkeypatch.delenv(k, raising=False)


def test_half_absent_is_no_export(monkeypatch):
    _clean_env(monkeypatch)
    assert gen_phys._relay_mid_half_exports({}, "dsdv_slice_c1x_C__t9") == []


def test_half_per_type_and_base_name(monkeypatch):
    _clean_env(monkeypatch)
    b = {"relay_mid_half": {"src": "_u_zz$"},
         "relay_mid_half_types": {"dsdv_slice_c1x_C": {"src": "_u_xr$|_u_eg_u_[a-z]+$", "sink": "_u_xr$"}}}
    assert gen_phys._relay_mid_half_exports(b, "dsdv_slice_c1x_C__t9") == [
        "export OT_RELAY_MID_HALF_SRC_RE = _u_xr$$|_u_eg_u_[a-z]+$$", "export OT_RELAY_MID_HALF_SINK_RE = _u_xr$$"]
    assert gen_phys._relay_mid_half_exports(b, "dsdv_slice_iq_C__t1") == ["export OT_RELAY_MID_HALF_SRC_RE = _u_zz$$"]


def test_half_env_wins_and_rejects_space(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("OT_RELAY_MID_HALF_SINK_RE", "_u_q$")
    assert gen_phys._relay_mid_half({}, "x") == (None, "_u_q$")
    monkeypatch.setenv("OT_RELAY_MID_HALF_SINK_RE", "a b")
    try:
        gen_phys._relay_mid_half({}, "x")
    except ValueError:
        return
    raise AssertionError("white space accepted")


def test_schema_keys():
    b = schema.SCHEMA["properties"]["budgets"]["properties"]
    assert b["relay_mid_half_types"]["additionalProperties"]["properties"].keys() == {"src", "sink"}
    tdir = Path(gen_phys.__file__).resolve().parent
    assert "tap_density" in (tdir / "schema.py").read_text()
    tcl = (tdir / "relay_mid.tcl").read_text()
    assert "OT_RELAY_MID_HALF_SRC_RE" in tcl and "($rm_w0 + $j - 1) / $rm_W" in tcl and "proc rm_half_list" in tcl


def test_half_weights(monkeypatch):
    _clean_env(monkeypatch)
    b = {"relay_mid_half": {"src": "_u_xr$=0.1;_u_eg_u_(gg|nh|nk)$=0.5", "sink": "_u_xr$=0.5"}}
    assert gen_phys._relay_mid_half(b, "t") == ("_u_xr$=0.1;_u_eg_u_(gg|nh|nk)$=0.5", "_u_xr$=0.5")
    try:
        gen_phys._relay_mid_half({"relay_mid_half": {"src": "_u_xr$=1.5"}}, "t")
    except ValueError:
        return
    raise AssertionError("weight 1.5 accepted")
