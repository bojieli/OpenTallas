#!/usr/bin/env python3
"""native_pin_audit.py on the synthetic ETM of test_pinreg_audit.py (run: python3 test_native_pin_audit.py)."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_pin_audit as N  # noqa: E402
import test_pinreg_audit as T  # noqa: E402


def test_reroute_reason_for():
    """ROOT-INF1 10-18 (INF.1): a routed view failing only the TT / FF pin-flop spread yields a native_spread
    reroute_reason that closed_stands admits; any capture / launch miss yields native_capture."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "closure_loop"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import closed_stands as CS  # noqa: E402
    rec = {"cell": "dsdv_sh_lk", "lib_cell": "dsdv_sh_lk", "spread_ps": 70.0, "ff_spread_ps": 88.3,
           "launch_ps": 150.0, "capture_ps": 120.0, "launch_over": 0, "capture_over": 0, "comb_pins": 0, "pass": False}
    rr = N.reroute_reason_for(rec, "results/closure/x/native_audit.json", [])
    assert rr["kind"] == "native_spread" and rr["cell"] == "dsdv_sh_lk" and rr["fix"], rr
    show = lambda ref, path: json.dumps(rec) if path == rr["source"] else None  # noqa: E731
    assert CS.committed_native_fail(rr, show, "abc") == ["ff_spread_ps 88.3 ps > 80"]
    rr2 = N.reroute_reason_for(dict(rec, capture_over=1, capture_ps=201.0), rr["source"], ["x"])
    assert rr2["kind"] == "native_capture" and rr2["fix"] == "x", rr2
    with tempfile.TemporaryDirectory() as td:
        assert N.receipt_path(Path(td) / "r" / "s81.json", td) == "r/s81.json"
        assert N.receipt_path("/elsewhere/s81.json", td) == "/elsewhere/s81.json"


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
        # owner 10-17 0dq: FF pin-flop spread reported; > 80 at FF fails even when TT is tight
        (v / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"mean": 160.0, "min": 150.0, "max": 170.0, "n": 4}},
                                                      "ff": {"boundary": {"mean": 120.0, "min": 70.0, "max": 160.0, "n": 4}}}))
        r = N.audit_one((str(root), "t", "physical/ref_tile/k/views/t"))
        assert r["ff_spread_ps"] == 90.0 and "FF pin-flop spread 90.0 > 80" in r["fail_why"], r
        (v / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"mean": 160.0, "min": 150.0, "max": 170.0, "n": 4}}}))
        # RELATIVE MODE: the parent compensates C = 100 (not R = 160): launch O - C = 300, capture S + C = 250, and
        # the pin flops arrive 50..70 ps after C (mismatch 70 <= 80: matched)
        comp = N.PA.compensation("100")
        r = N.audit_one((str(root), "t", "physical/ref_tile/k/views/t", comp))
        assert (r["launch_ps"], r["capture_ps"]) == (300.0, 250.0), r
        m = r["relative"]["tt"]
        assert (m["rel_min_ps"], m["rel_max_ps"], m["mismatch_ps"], m["offset_ps"]) == (50.0, 70.0, 70.0, 60.0), m
        assert "boundary vs neighbour" not in r["fail_why"], r
        # a neighbour whose boundary mean is 60: pin flops 90..110 ps late -> boundary FAIL
        nb = root / "nb"
        nb.mkdir()
        (nb / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"mean": 60.0}}}))
        comp = N.PA.compensation(str(nb))
        assert comp["tt"] == 60.0 and "ff" not in comp, comp
        r = N.audit_one((str(root), "t", "physical/ref_tile/k/views/t", comp))
        assert "TT boundary vs neighbour 110.0 > 80" in r["fail_why"], r
        assert N.PA.compensation("tt=160,ff=120") == {"tt": 160.0, "ff": 120.0, "src": "given tt=160,ff=120"}
        # CASE PINS (QK-FWD / NS-CASE 10-18): a die-SDC case-analysed strap leaves the capture metric and is listed;
        # --static-pins is the same option; a pattern matching no input pin is an error, never a silent pass
        r = N.audit_one((str(root), "t", "physical/ref_tile/k/views/t", None, ["far_*"]))
        assert r["case_pins"] == ["far_i"] and r["capture_pin"] == "ok_i" and r["capture_ps"] == 120.0, r
        assert r["case_pins_raw_capture_ps"]["far_i"] == 310.0, r
        assert "error" in N.audit_one((str(root), "t", "physical/ref_tile/k/views/t", None, ["nope"]))
        assert N.main(["--root", str(root), "--view", "physical/ref_tile/k/views/t", "--static-pins", "nope"]) == 1
        # the CLI single-view form
        assert N.main(["--root", str(root), "--view", "physical/ref_tile/k/views/t", "--relative-to", "160"]) == 1
    assert N.family("qfd_cst_n", "") == "qwen" and N.family("dsfd_coll_ct", "") == "s81" and N.family("ot_hgi_seq_fe", "") == "hbm"
    print("PASS test_native_pin_audit")


if __name__ == "__main__":
    test_reroute_reason_for()
    main()
