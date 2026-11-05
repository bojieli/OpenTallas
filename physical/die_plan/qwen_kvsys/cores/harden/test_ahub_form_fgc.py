#!/usr/bin/env python3
"""AHUB form fgc on the canonical source reproduces the signed kit RTL byte for byte; refuses a changed source. Run from any directory."""
import hashlib, json, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ahub_clock7
import ahub_form_fgc

REPO = HERE.parents[4]
# sha256 of dkv70ahub/fgc/rtl/qkd_ahub_static_dw.sv, byte-equal to dkv71/ahub/h1, the signed h1c view; refreshed only by a new sign-off.
KIT_DW = "a5369c1df6a31d3d32527c4b2e780c7d6c2e00c5fbdba64af530deb174edc403"


def test_kit_bytes():
    with tempfile.TemporaryDirectory() as t:
        core = {"files": [str(REPO / "results/kv_host_regen_1/rtl/qkd_ahub/qkd_ahub.sv"), str(REPO / "rtl/hdc/nearhbm/qkd_ahub_static_dw.sv")],
                "pin_class": {}, "classes": {}, "report": {}}
        ahub_clock7.prepare(core, t)
        assert hashlib.sha256((Path(t) / "qkd_ahub_static_dw.sv").read_bytes()).hexdigest() == KIT_DW
        wrap = (Path(t) / "qkd_ahub.sv").read_text()
        assert "qkd_ahub_static_dw_ck7 #(" in wrap and ".ck_ent(ck[6:3])," in wrap  # am-g-drop on this wrapper is applied later, by the kit generator


def test_refuses_changed_source():
    try:
        ahub_form_fgc.apply_fgc("module x; endmodule")
    except ValueError:
        return
    raise AssertionError("a source without the form's lines must refuse")


if __name__ == "__main__":
    test_kit_bytes()
    test_refuses_changed_source()
    print("AHUB_FORM_FGC PASS")
