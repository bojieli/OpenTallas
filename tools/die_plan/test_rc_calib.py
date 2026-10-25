"""tests for tools/die_plan/rc_calib.py (FLOW 10-25): python3 -m pytest tools/die_plan/test_rc_calib.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rc_calib  # noqa: E402

SPEF = """*SPEF "ieee 1481-1999"
*C_UNIT 1 PF
*R_UNIT 1 OHM

*NAME_MAP
*1 n_a
*2 n\\[3\\]

*D_NET *1 0.002
*CONN
*I u1:Y O
*CAP
1 *1:1 0.001
2 *1:2 0.001
*RES
1 *1:1 *1:2 30.0
2 *1:2 u2:A 10.0
*END

*D_NET *2 0.004
*RES
1 *2:1 *2:2 100.0
*END
"""


def test_parse_spef(tmp_path):
    p = tmp_path / "x.spef"
    p.write_text(SPEF)
    d = rc_calib.parse_spef(str(p))
    assert abs(d["n_a"][0] - 2.0) < 1e-9 and abs(d["n_a"][1] - 40.0) < 1e-9   # pF -> fF; sum of R
    assert abs(d["n[3]"][0] - 4.0) < 1e-9 and abs(d["n[3]"][1] - 100.0) < 1e-9


def test_fit_recovers_layer_values():
    c = {"M2": 0.2, "M3": 0.14, "M4": 0.12, "M5": 0.10}
    r = {"M2": 29.7, "M3": 31.3, "M4": 18.0, "M5": 19.0}
    vr = {"V@M1": 17.2, "V@M2": 17.2, "V@M3": 17.2, "V@M4": 11.8}
    wire, spef = {}, {}
    import random
    rnd = random.Random(1)
    for i in range(400):
        acc = {L: rnd.uniform(0, 50) for L in c}
        acc.update({v: float(rnd.randint(0, 8)) for v in vr})
        wire["n%d" % i] = ("SIGNAL", acc)
        spef["n%d" % i] = (sum(c[L] * acc[L] for L in c), sum(r[L] * acc[L] for L in r) + sum(vr[v] * acc[v] for v in vr))
    f = rc_calib.fit_layers(wire, spef, ["M2", "M3", "M4", "M5"])
    for L in c:
        assert abs(f["C_fF_per_um"][L] - c[L]) < 1e-6
        assert abs(f["R_ohm_per_um"][L] - r[L]) < 1e-4
    assert abs(f["via_R_ohm"]["V@M4"] - 11.8) < 1e-4
    assert f["C_fit"]["n"] == 400


def test_emit_stock_roundtrip_and_override():
    t = rc_calib.emit_tcl({})
    assert "set_layer_rc -layer M2 -resistance 2.97127E-02 -capacitance 1.74942E-01" in t
    assert "set_wire_rc -clock -resistance 2.14161E-02 -capacitance 1.45426E-01" in t
    assert "set_layer_rc -via V4 -resistance 1.18000E-02" in t
    t = rc_calib.emit_tcl({"layer": {"M5": {"C": 0.094}}}, header="hdr")
    assert t.startswith("# hdr")
    assert "set_layer_rc -layer M5 -resistance 1.89935E-02 -capacitance 9.40000E-02" in t


def test_compare(tmp_path):
    ref = tmp_path / "r.tsv"; est = tmp_path / "e.tsv"
    ref.write_text("HOLD\t-1.0\t2\nSETUP\t40\t0\nCK\ta/CLK\t100\nCK\tb/CLK\t110\nNET\tn\tu/A\t10\n")
    est.write_text("HOLD\t3.0\t0\nSETUP\t30\t0\nCK\ta/CLK\t105\nCK\tb/CLK\t105\nCK\tc/CLK\t1\nNET\tn\tu/A\t12\n")
    d = rc_calib.compare(str(ref), str(est))
    assert d["clock_arrival"]["n"] == 2 and d["clock_arrival"]["mean"] == 0.0 and d["clock_arrival"]["mean_abs"] == 5.0
    assert d["net_delay"]["mean"] == 2.0 and d["net_delay_rel_mean"] == 0.2
    assert d["hold_wns_rcx"] == (-1.0, 2)
