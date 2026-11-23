"""S81-COL-HOLD-MARGIN 11-17 (COORD, FABLE-PD-S81-0720 B2): per-item hold-margin knobs, default-preserving."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pregrt_ff_hold as P  # noqa: E402

T = {"clock": {"pregrt_ff_hold": True}}


def test_pregrt_port_margin_defaults_to_today(monkeypatch):
    monkeypatch.delenv("OT_PREGRT_HOLD_PORT_MARGIN_PS", raising=False)
    lines = P.config_lines(T)
    assert not any("OT_PREGRT_HOLD_PORT_MARGIN" in ln for ln in lines) and lines
    monkeypatch.setenv("OT_PREGRT_HOLD_PORT_MARGIN_PS", "  ")
    assert lines == P.config_lines(T)


def test_pregrt_port_margin_per_item_env(monkeypatch):
    monkeypatch.setenv("OT_PREGRT_HOLD_PORT_MARGIN_PS", "15")
    lines = P.config_lines(T)
    assert "export OT_PREGRT_HOLD_PORT_MARGIN = 15" in lines
    assert P.config_lines({}) == []          # opted-out types stay untouched


def test_gen_phys_reads_the_grt_margin_knob():
    src = (HERE / "gen_phys.py").read_text()
    assert 'os.environ.get("OT_HOLD_FF_MARGIN_PS"' in src and "hold_ff_margin = float(_hm)" in src
    # the knob sits at the top of write_type_kit, before the kit config is built from hold_ff_margin
    assert src.index("OT_HOLD_FF_MARGIN_PS") < src.index("export OT_HOLD_FF_MARGIN = {hold_ff_margin:g}")


def test_pregrt_hold_ports_scope_vclk(monkeypatch):
    """KV-CTLPORT 11-23: gen env OT_PREGRT_HOLD_PORTS_SCOPE=vclk writes the config line run_kit.sh passes to the build; the tcl then excepts
    only forwarded ring / native pad inputs.  Unset = no line (byte-identical kit)."""
    from pathlib import Path
    import pytest
    import pregrt_ff_hold as PG
    t = {"clock": {"pregrt_ff_hold": True}}
    monkeypatch.delenv("OT_PREGRT_HOLD_PORTS_SCOPE", raising=False)
    assert not any("OT_PREGRT_HOLD_PORTS " in ln for ln in PG.config_lines(t))
    monkeypatch.setenv("OT_PREGRT_HOLD_PORTS_SCOPE", "vclk")
    assert "export OT_PREGRT_HOLD_PORTS = vclk" in PG.config_lines(t)
    monkeypatch.setenv("OT_PREGRT_HOLD_PORTS_SCOPE", "ctl")
    assert "export OT_PREGRT_HOLD_PORTS = ctl" in PG.config_lines(t)
    monkeypatch.setenv("OT_PREGRT_HOLD_PORTS_SCOPE", "all")
    with pytest.raises(ValueError):
        PG.config_lines(t)
    src = Path(PG.__file__).read_text()
    assert "in {vclk ctl}" in src and "set pg_np_in $pg_in" in src
    assert "set pg_ctl_globs {arst_n start_i cland_tstart_in* cland_rstart_in* ri_*}" in src
    assert "set_false_path -hold -from $::pg_np_in" in src and "unset_path_exceptions -hold -from $::pg_np_in" in src
    assert src.index("set pg_np_in $pg_in") < src.index("proc pg_np_apply") < src.index("foreach pg_tag {all rr xt}")
    gp = Path(PG.__file__).with_name("gen_phys.py").read_text()
    assert "OT_PREGRT_HOLD_PORTS=\\$(sed -n 's/^export OT_PREGRT_HOLD_PORTS = //p' /work/config.mk)" in gp
