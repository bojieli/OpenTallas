#!/usr/bin/env python3
"""native_pin_audit.py on the synthetic ETM of test_pinreg_audit.py (run: python3 test_native_pin_audit.py)."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_pin_audit as N  # noqa: E402
import test_pinreg_audit as T  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        v = root / "physical" / "ref_tile" / "k" / "views" / "t"
        v.mkdir(parents=True)
        (v / "t_tt.lib").write_text(T.lib())
        (v / "t.lef").write_text("MACRO t\nEND t\n")
        # macro abstracts are not tiles
        m = root / "physical" / "asap7_memory_macros" / "m"
        m.mkdir(parents=True)
        (m / "m_tt.lib").write_text(T.lib())
        (m / "m.lef").write_text("MACRO m\nEND m\n")
        assert N.find_views(root) == [("t", "physical/ref_tile/k/views/t")]
        # lib midrange R = 100: launch q[1] 400 - 100 = 300 > 220, capture far_i 150 + 100 = 250 > 190, thru combinational
        r = N.audit_one((str(root), "t", "physical/ref_tile/k/views/t"))
        assert (r["launch_ps"], r["launch_pin"], r["launch_over"]) == (300.0, "q[1]", 1), r
        assert (r["capture_ps"], r["capture_pin"], r["capture_over"]) == (250.0, "far_i", 1), r
        assert r["comb_pins"] == 1 and not r["pass"] and not r["insertion"], r
        # the measured boundary reference replaces the lib estimate: R = 160 -> launch 240, capture 310
        (v / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"mean": 160.0, "min": 150.0, "max": 170.0, "n": 4}}}))
        r = N.audit_one((str(root), "t", "physical/ref_tile/k/views/t"))
        assert (r["launch_ps"], r["capture_ps"], r["R_ps"], r["spread_ps"]) == (240.0, 310.0, 160.0, 20.0), r
        assert r["insertion"] and "insertion.json boundary mean" in r["ref_src"]
    assert N.family("qfd_cst_n", "") == "qwen" and N.family("dsfd_coll_ct", "") == "s81" and N.family("ot_hgi_seq_fe", "") == "hbm"
    print("PASS test_native_pin_audit")


if __name__ == "__main__":
    main()
