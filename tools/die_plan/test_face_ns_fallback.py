"""NS-BANK-FALLBACK 11-19 (FABLE-FIX-S81-LEAF): a face register with no comb cell (row stride > 1) inside the pin retention takes a
stride-1 cell instead of stopping the kit; stride 1 kits walk the search once, as before.
    python3 -m pytest -q tools/die_plan/test_face_ns_fallback.py"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = (Path(__file__).resolve().parent / "face_flops.tcl").read_text()


def test_fallback_is_in_the_ns_bank_search_only():
    body = TCL[TCL.index("proc ff_put_near {f x y} {"):TCL.index("# interior pin registers")]
    assert "foreach ff_try_stride [expr {$ff_ns_stride > 1 ? [list $ff_ns_stride 1] : [list $ff_ns_stride]}]" in body
    assert "%$ff_try_stride ||" in body and "%$ff_ns_stride ||" not in body
    assert body.index("foreach ff_try_stride") < body.index('error "NS face bank cannot fit')    # the stop stays, after both passes
    assert body.count("OT_FACE_FLOPS NS bank fallback") == 1


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
def test_stride_list(tmp_path):
    expr = re.search(r"foreach ff_try_stride (\[expr \{.*?\}\])", TCL).group(1)
    out = subprocess.run(["tclsh"], input=f"foreach s {{1 2 4}} {{ set ff_ns_stride $s; puts {expr} }}\n", capture_output=True, text=True).stdout.split("\n")
    assert out[:3] == ["1", "2 1", "4 1"]
