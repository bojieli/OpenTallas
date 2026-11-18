"""TAP-CAP-CENSUS: per-tap sinks of the CTS log against the cap."""
import tempfile
from pathlib import Path

import tap_cap_census as T

LOG = ("OT_TAP_BALANCE it1 target 250: clk=163(152-286,639) clk_t1=303(288-366,716)\n"
       "OT_TAP_BALANCE it3 target 250: clk=163(152-286,639) clk_t1=303(288-366,1700) clk_t42=554(538-715,3500) clk_t10=247(247-247,1)\n"
       "OT_TAP_BALANCE done: 100 delay cells\n")


def test_last_iteration_is_read():
    assert T.census(LOG) == {"clk": 639, "clk_t1": 1700, "clk_t42": 3500, "clk_t10": 1}
    assert T.census("nothing") == {}


def test_over_cap_and_added_taps():
    s = T.census(LOG)
    assert T.over(s, 1700) == {"clk_t42": dict(sinks=3500, add_taps=2)}       # exactly 1700 is not over
    assert T.over(s, 5000) == {}


def test_cli_exit_codes_and_cap_from_config():
    d = Path(tempfile.mkdtemp())
    (d / "run/logs/asap7/dp_x/base").mkdir(parents=True)
    (d / "run/logs/asap7/dp_x/base/4_1_cts.log").write_text(LOG)
    (d / "config.mk").write_text("export OT_TAP_MAX_SINKS = 1700\n")
    assert T.cap_of(d) == 1700
    assert T.main(["x", str(d)]) == 1
    assert T.main(["x", str(d), "--cap", "4000"]) == 0
    (d / "run/logs/asap7/dp_x/base/4_1_cts.log").write_text("no census here\n")
    assert T.main(["x", str(d)]) == 2
