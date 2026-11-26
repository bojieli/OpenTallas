import json, tempfile
from pathlib import Path
import render_type_heat as R


def test_blank_type_is_not_modelled():
    t = {"outline_um": [200, 100], "clock": {"tap_um": [100, 50]}}
    with tempfile.TemporaryDirectory() as d:
        r = R.render_type("x", t, str(Path(d) / "x.png"))
    assert r["modelled"] is False and r["peak_util"] is None and r["legs_over_405"] is None
