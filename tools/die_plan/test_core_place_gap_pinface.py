"""--gap-pinface HI:LO:PINS (R3 face rule) in core_place: facing faces keep HI when either face carries more than
PINS pins, else LO; the diagonal gap is LO; the pin-count floor need(pa + pb) still applies; off = uniform --gap."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_place as CP  # noqa: E402


def stub(pf=None):
    s = SimpleNamespace(cfg={"gap": 21.6, "gap_pinface": pf})
    s.need = lambda pins: pins * CP.PIN_UM
    return s


def test_off_is_uniform_gap():
    s = stub()
    assert CP.TypeModel.req_gap(s, 21.6, 160, 2) == max(21.6, CP.PIN_UM * 162)
    assert CP.TypeModel.req_gap(s, 21.6, 2, 2) == 21.6
    assert CP.TypeModel.diag_gap(s, 21.6) == 21.6


def test_pin_face_hi_lo():
    s = stub((43.2, 21.6, 24.0))
    # lane N face (160 pins) toward a lane N face: street HI
    assert CP.TypeModel.req_gap(s, 21.6, 160, 160) == max(43.2, CP.PIN_UM * 320)
    # S faces (clk + rst_n) facing: LO
    assert CP.TypeModel.req_gap(s, 21.6, 2, 2) == 21.6
    # one busy face is enough for HI
    assert CP.TypeModel.req_gap(s, 21.6, 2, 97) >= 43.2
    # threshold is strict (> PINS)
    assert CP.TypeModel.req_gap(s, 21.6, 24, 0) == max(21.6, CP.PIN_UM * 24)
    assert CP.TypeModel.diag_gap(s, 21.6) == 21.6


def test_cli_parses_gap_pinface():
    src = (Path(__file__).resolve().parent / "core_place.py").read_text()
    assert "--gap-pinface" in src and "gap_pinface" in src


if __name__ == "__main__":
    test_off_is_uniform_gap(); test_pin_face_hi_lo(); test_cli_parses_gap_pinface(); print("ok")
