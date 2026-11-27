"""C-LEG405-FIRM (KV-INT-R3 11-27): pin["export_relay_status"] = "FIRM" seats the forwarded-export relays FIRM on the site/row grid.
Default (key absent or PLACED) stays byte-identical to the LEG405 form; the key is validated."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_contract as LC  # noqa: E402
import test_cts0114_fwd as T  # noqa: E402


def _pins(**extra):
    p = {"name": "fclk_out_o", "kind": "clock", "dir": "out", "source_clock_port": "clk", "export_relay_xy_um": [[1622.295, 20.655]]}
    p.update(extra)
    return [p]


def _tcl(**extra):
    return LC.export_tcl(T._P({"landing_contract": {"pins": _pins(**extra)}}), "T")


def test_firm_emitted_only_when_the_key_is_set():
    base = _tcl()
    assert "cland_rly_fclk_out_o_0" in base and "setPlacementStatus FIRM" not in base and "cland_sw" not in base
    assert _tcl(export_relay_status="PLACED") == base
    firm = _tcl(export_relay_status="FIRM")
    assert firm != base and "setPlacementStatus FIRM" in firm and "cland_sw" in firm
    # only the relay instance is affected: the export buffer stays PLACED
    assert firm.count("setPlacementStatus FIRM") == 1 and firm.count("setPlacementStatus PLACED") == 1


def test_status_key_is_validated():
    q = T._Q(_pins(export_relay_status="LOCKED"))
    assert any("export_relay_status" in e for e in LC.check_export_relays(q)["errors"])
    ok = LC.check_export_relays(T._Q(_pins(export_relay_status="FIRM")))
    assert not any("export_relay_status" in e for e in ok["errors"])


_ROWS = r'''
mkobj site {switch $m {getWidth {return 54} getHeight {return 270}}}
mkobj row0 {switch $m {getSite {return site} getOrient {return MX} getBBox {return rb0}}}
mkobj rb0 {switch $m {yMin {return 20520}}}
mkobj row1 {switch $m {getSite {return site} getOrient {return R0} getBBox {return rb1}}}
mkobj rb1 {switch $m {yMin {return 20790}}}
'''


def test_firm_relay_executes_on_the_site_grid_with_row_orientation():
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    mock = (T._RELAY_MOCK + _ROWS).replace("getDbUnitsPerMicron {return 1000}}}",
                                           "getDbUnitsPerMicron {return 1000} getRows {return {row0 row1}}}}")
    mock = mock.replace("setPlacementStatus {}", r'setPlacementStatus {L \"$name status \$args\"} setOrient {L \"$name orient \$args\"}')
    r = subprocess.run(["tclsh"], input=mock + _tcl(export_relay_status="FIRM") + "\nforeach l $::log {puts $l}\n",
                       text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout.splitlines()
    # centre 1622.295 um minus half the 1000 dbu master = 1621795 -> snapped to the 54 dbu site grid; y on the 270 dbu row
    assert "cland_rly_fclk_out_o_0 loc 1621782 20520" in out
    assert "cland_rly_fclk_out_o_0 status FIRM" in out
    assert "cland_rly_fclk_out_o_0 orient MX" in out
