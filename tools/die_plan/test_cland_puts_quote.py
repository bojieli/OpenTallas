"""CLAND-PUTS-QUOTE + PLACE-FANOUT log line: generated Tcl must not evaluate note text."""
import shutil, subprocess, sys
from pathlib import Path
import pytest
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import landing_place  # noqa: E402

NOTE = "u_cland_fstart_cws1_o moved 10.53 um along/off face S: [72.38399999999999, 0.0, 81.024, 8.64] -> [72.384, 10.53] $x \"q\" (ft)"


def test_quote_escapes():
    q = landing_place._tcl_quote(NOTE)
    assert "\\[72.38399999999999," in q and "\\]" in q and "\\$x" in q and '\\"q\\"' in q


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_tcl_prints_note_verbatim():
    out = subprocess.run(["tclsh"], input=f'puts "OT_CLAND face-window {landing_place._tcl_quote(NOTE)}"\n',
                         capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "OT_CLAND face-window " + NOTE


def test_fanout_log_line_has_no_get_full_name():
    assert "get_full_name [current_design]" not in (D / "gp_noconverge_gate.tcl").read_text()
