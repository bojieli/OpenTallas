"""KV-101/SPLIT: a recorded wavefront core reset on a 1-bit rst_n BUS input drives the tap (owner: plan tap wins)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def test_bus_input_rst_n_takes_recorded_tap():
    cr = {(7, "rst_n"): "rst_n_t131"}
    e, ov, err = bind.core_reset_port_expr(cr, 7, "rst_n", ["x"], ["ri_ahub_rst_n_q[0]"])
    assert e == ["rst_n_t131"] and err is None
    assert ov == dict(pin="rst_n", tap="rst_n_t131", replaced="ri_ahub_rst_n_q[0]", kind="x")


def test_reset_kind_and_unrecorded_ports_unchanged():
    cr = {(7, "rst_n"): "rst_n_t131"}
    assert bind.core_reset_port_expr(cr, 7, "rst_n", ["rst"], ["rst_n_t131"]) == (["rst_n_t131"], None, None)
    assert bind.core_reset_port_expr(cr, 8, "rst_n", ["x"], ["a[0]"]) == (["a[0]"], None, None)
    assert bind.core_reset_port_expr(cr, 7, "d", ["x"], ["a[0]"]) == (["a[0]"], None, None)


def test_wide_or_active_high_port_is_an_error_not_a_rewire():
    cr = {(7, "rst_n"): "rst_n_t1", (7, "rst"): "rst_n_t1"}
    e, ov, err = bind.core_reset_port_expr(cr, 7, "rst_n", ["x", "x"], ["a[0]", "a[1]"])
    assert e == ["a[0]", "a[1]"] and ov is None and "2 bit" in err
    e, ov, err = bind.core_reset_port_expr(cr, 7, "rst", ["x"], ["a[0]"])
    assert ov is None and err


def test_emitter_uses_helper_and_records_overrides():
    src = Path(bind.__file__).read_text()
    assert "core_reset_port_expr(core_reset, ci, pn," in src and "_core_reset_bus_taps" in src
