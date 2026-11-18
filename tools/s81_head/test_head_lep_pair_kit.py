"""HEAD-TYPES-R4: head_lep_pair_kit.py driver smoke tests (io_tcl wrapper vs gen_core_kit_hbm clock_entry kwarg; --kcred params)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_lep_pair_kit as K  # noqa: E402


def test_io_tcl_wrapper_accepts_clock_entry():
    seen = []

    def orig(pins, w, h, tag, clock_entry=None):
        seen.append(clock_entry)
        return "", []

    wrapped = K.io_tcl_interior(orig)
    pins = [dict(name="a", layer="M5", x=0.1, y=5.0)]
    wrapped(pins, 388.8, 432.0, "t")
    wrapped(pins, 388.8, 432.0, "t", clock_entry={"names": ["clk"], "m5": (0.024, 0.048)})
    assert seen == [None, {"names": ["clk"], "m5": (0.024, 0.048)}]


def test_kcred_params():
    plan = K.ROOT / "physical/die_plan/s81_head/die_plan.json"
    for kc, want in ((12, {}), (28, {"KCRED": 28})):
        with tempfile.TemporaryDirectory() as d:
            _vf, _mf, rec, _clk, nm = K.build_inputs(plan, Path(d), kc)
        assert rec[K.MODULE]["params"] == want and nm == 55
