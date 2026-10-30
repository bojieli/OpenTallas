"""DIE-QC-46: die-trial partition placement must carry the exact plan origin.  `{ox:g}` kept 6 significant digits,
so a 16390.08-um origin was placed at 16390.1 (QC TRIAL1: 221/377 partitions 0.02/0.04 um off plan, 438,159 port
bits not touching).  The ot_place / bump lines now use gen_phys._um (4 decimals)."""
from pathlib import Path
from types import SimpleNamespace
import re
import sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D


def _plan():
    parts = {"a": dict(origin_um=[16390.08, 18420.48], orient="MX"), "b": dict(origin_um=[2617.92, 0.0])}
    return SimpleNamespace(W=20000.0, H=24000.0, name="tiny", parts=parts, die={})


def test_psm_ot_place_exact_origin():
    t = D.psm_tcl(_plan(), [], None, [])
    assert "ot_place a 16390.08 18420.48 MX" in t
    assert "ot_place b 2617.92 0 R0" in t


def test_no_g_format_on_placement_lines():
    src = (Path(__file__).parent / "die_trial.py").read_text()
    assert not re.search(r"ot_place \{sv\(n\)\} \{ox:g\}", src)
    assert not re.search(r"ot_pad \{net\} \{k\} \{x:g\}", src)
