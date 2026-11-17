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
