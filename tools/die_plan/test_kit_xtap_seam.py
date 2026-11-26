"""C-XTAP-HOLD 11-26: kit_xtap_seam.py -- the planned hard-seam hold element (hb4 / lockup), plan clock.xtap_seam_element."""
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_xtap_seam as X  # noqa: E402

WRAP = """module wrap3 #(parameter integer NSEG = 8) (
    input  wire clk,
    input  wire rst_n_pin,
    input  wire [7:0] i,
    output wire pv
);
    localparam integer HTG = 3 + $clog2(NSEG);
    wire          r_v_a, r_err_a;
    wire [31:0]   r_val_a, r_val_b;
    wire [HTG:0]  r_t_a;
    core_c #(.NSEG(NSEG)) u_c (
        .clk(clk), .rst_n_pin(rst_n_pin), .i(i), .pv(pv),
        .r_v_a(r_v_a), .r_val_a(r_val_a), .r_val_b(r_val_b), .r_err_a(r_err_a), .r_t_a(r_t_a));
    half #(.TRW(HTG)) u_ha (.clk(clk), .ov(r_v_a), .oval(r_val_a), .oerr(r_err_a), .otag(r_t_a));
    half #(.TRW(HTG)) u_hb (.clk(clk), .ov(), .oval(r_val_b), .oerr(), .otag());
endmodule
"""
PORTS = ["r_v_a", "r_val_a", "r_err_a", "r_t_a", "r_val_b"]


def _spec(form, **kw):
    return dict(pairs=[dict(inst="u_c", types=["core_c"], ports=PORTS, form=form, **kw)])


def test_sizing_and_setup():
    assert X.size_hb4(16.59) == 2            # (16.59 + 25) / 37 -> 2
    assert X.size_hb4(104.37) == 4           # (104.37 + 25) / 37 = 3.5 -> 4
    assert X.size_hb4(49.0, margin_ps=25) == 2 and X.size_hb4(49.01, margin_ps=25) == 3
    assert X.hb4_setup_ps(4, 131.4) == pytest.approx(833 + 131.4 - 240 - 200)
    assert X.lockup_setup_ps(131.4) == pytest.approx(416.5 + 131.4 - 100)
    assert X.lockup_hold_ps(131.4) == pytest.approx(416.5 - 131.4)
    assert X.lockup_setup_ps(-400.0) < 0


def test_hb4_form_on_capture_pins():
    txt, els, sk = X.apply(WRAP, _spec("hb4", deficit_ps=104.37))
    assert [e["port"] for e in els] == PORTS and all(e["n"] == 4 and e["form"] == "hb4" for e in els)
    assert "ot_dp_hd #(.W(32), .N(4)) u_xshd_c_r_val_a (.a(r_val_a), .y(xs_c_r_val_a));" in txt
    assert "ot_dp_hd #(.W(1), .N(4)) u_xshd_c_r_v_a (.a(r_v_a), .y(xs_c_r_v_a));" in txt
    # parameter-width tag bus keeps its expression width
    assert re.search(r"ot_dp_hd #\(\.W\(\(\(HTG\)-\(0\)\+1\)\), \.N\(4\)\) u_xshd_c_r_t_a \(\.a\(r_t_a\), \.y\(xs_c_r_t_a\)\);", txt)
    # only the capture core's pins moved; the launch cores still drive the original nets
    assert ".r_val_a(xs_c_r_val_a)" in txt and ".oval(r_val_a)" in txt and ".oval(r_val_b)" in txt
    assert ".clk(clk), .rst_n_pin(rst_n_pin), .i(i)" in txt
    assert "ot_dp_lk" not in txt


def test_lockup_form_uses_wrapper_clock_and_fabric_name():
    txt, els, sk = X.apply(WRAP, _spec("lockup"))
    assert len(els) == 5
    assert "ot_dp_lk #(.W(32)) u_xslk_c_r_val_b (.clk(clk), .d(r_val_b), .q(xs_c_r_val_b));" in txt
    assert "u_fl_" not in txt and "u_lk_nk_" not in txt     # never the follow-D launch-tap classes
    assert "ot_dp_hd" not in txt


def test_type_filter_and_no_match_is_identity():
    txt, els, _ = X.apply(WRAP, dict(pairs=[dict(inst="u_c", types=["other"], ports=PORTS, form="hb4", n=2)]))
    assert txt == WRAP and not els
    with pytest.raises(X.XsError):
        X.apply(WRAP, dict(pairs=[dict(inst="u_c", ports=["nope"], form="hb4", n=2)]))
    with pytest.raises(X.XsError):
        X.apply(WRAP, dict(pairs=[dict(inst="u_c", ports=PORTS, form="hb4")]))     # neither n nor deficit
    with pytest.raises(X.XsError):
        X.apply(WRAP, dict(pairs=[dict(inst="u_c", ports=PORTS, form="hb4", deficit_ps=900)]))


def test_reset_and_const_connections_left_alone():
    txt, els, sk = X.apply(WRAP, dict(pairs=[dict(inst="u_c", ports=["rst_n_pin", "r_v_a"], form="lockup")]))
    src = WRAP.replace(".rst_n_pin(rst_n_pin)", ".rst_n_pin(rst_n)")
    txt, els, sk = X.apply(src, dict(pairs=[dict(inst="u_c", ports=["rst_n_pin", "r_v_a"], form="lockup")]))
    assert sk["reset"] == 1 and [e["port"] for e in els] == ["r_v_a"]


def test_apply_kit_both_forms_cells_and_fail_closed(tmp_path):
    for form in X.FORMS:
        rd = tmp_path / form
        rd.mkdir()
        (rd / "wrap3.sv").write_text(WRAP)
        (rd / "other.sv").write_text("module other (input wire a, output wire y);\n    assign y = a;\nendmodule\n")
        rec = X.apply_kit(rd, _spec(form, n=3))
        assert rec["_pairs"] == [5] and rec["wrap3.sv"]["elements"] == 5 and rec["wrap3.sv"]["forms"] == [form]
        out = (rd / "wrap3.sv").read_text()
        assert ("module ot_dp_hd" in out) == (form == "hb4") and ("module ot_dp_lk" in out) == (form == "lockup")
        assert (rd / "other.sv").read_text().startswith("module other")
        if form == "hb4":
            assert rec["wrap3.sv"]["hb4_cells"] == 3 * (1 + 32 + 1 + 32)       # the parameter-width tag bus is not counted
        again = X.apply_kit(rd, dict(pairs=[dict(_spec(form, n=3)["pairs"][0], allow_missing=True)]))   # second GEN: no double element
        assert again == {"_pairs": [0]} and (rd / "wrap3.sv").read_text() == out
    rd = tmp_path / "none"
    rd.mkdir()
    (rd / "wrap3.sv").write_text(WRAP)
    with pytest.raises(X.XsError):
        X.apply_kit(rd, dict(pairs=[dict(inst="u_zz", ports=["a"], form="hb4", n=1)]))
    assert X.apply_kit(rd, dict(pairs=[dict(inst="u_zz", ports=["a"], form="hb4", n=1, allow_missing=True)])) == {"_pairs": [0]}
    assert (rd / "wrap3.sv").read_text() == WRAP


def test_spec_of_and_keep_tcl():
    raw = {"clock": {"xtap_seam_element": {"col_h9_r2*": _spec("hb4", n=4), "x": _spec("lockup")}}}
    assert X.spec_of(raw, "col_h9_r2__t1__clce45cab5__pv9e92407b")["pairs"][0]["form"] == "hb4"
    assert X.spec_of(raw, "x")["pairs"][0]["form"] == "lockup" and X.spec_of(raw, "y") is None
    assert X.spec_of({}, "x") is None and X.spec_of({"clock": {}}, "x") is None
    assert X.keep_tcl(None) == "" and X.keep_tcl(_spec("lockup")) == ""
    t = X.keep_tcl(_spec("hb4", n=4))
    assert "*u_xshd_*" in t and "setDoNotTouch 1" in t and "error" in t


def test_schema_accepts_key_and_rejects_bad_form():
    import schema
    props = schema.SCHEMA["properties"]["clock"]["properties"]["xtap_seam_element"]
    pair = props["additionalProperties"]["properties"]["pairs"]["items"]
    assert pair["properties"]["form"]["enum"] == ["hb4", "lockup"] and pair["additionalProperties"] is False
    assert set(pair["required"]) == {"inst", "ports", "form"}


def test_findings_report_only():
    raw = {"die": {"period_ps": 833.0}, "partition_types": {"col_h9_r2__t1": {}},
           "clock": {"xtap_seam_element": {
               "col_h9_r2*": dict(pairs=[dict(inst="u_c", ports=PORTS, form="hb4", deficit_ps=104.37, delta_ps=131.4),
                                         dict(inst="u_c", ports=PORTS, form="lockup", delta_ps=131.4)]),
               "ghost": dict(pairs=[dict(inst="u_c", ports=PORTS, form="hb4", n=12, delta_ps=-200.0),
                                    dict(inst="u_c", ports=PORTS, form="lockup", delta_ps=500.0),
                                    dict(inst="u_c", ports=PORTS, form="hb4")])}}}
    f = X.findings(raw)
    assert all(x.startswith("WARN ADV-XTAP-SEAM ") for x in f)
    assert not [x for x in f if " col_h9_r2*" in x]
    assert any("matches no partition type" in x for x in f) and any("TT setup estimate" in x for x in f)
    assert any(">= T/2" in x for x in f) and any("needs n or deficit_ps" in x for x in f)
    assert X.findings({}) == [] and X.findings({"clock": {}}) == []


def test_gen_phys_and_advisory_are_wired():
    g = (HERE / "gen_phys.py").read_text()
    assert "_XS.spec_of(getattr(P, \"raw\", None), tn)" in g and "_XS.keep_tcl(xs_spec)" in g
    assert '("XTAP-SEAM", "kit_xtap_seam")' in (HERE / "plan_advisory.py").read_text()


def test_real_wrapper_shapes_comments_and_nested_parameters():
    """S81 kit rtl (ot_v41_bf_col3.sv): commented parameter list with parentheses, $clog2 in port ranges, a header-less
    neighbour module in the same directory -- found on the col_h9_r2 pv9e92407b kit copy."""
    src = """// module in a comment (never a header)
module w #(
    parameter integer NSEG = 8,   // segments (2 tree banks (by parity))
    parameter integer NCH = 16    /* chains ( */
) (
    input  wire clk,
    input  wire [$clog2(NCH)+3+$clog2(NSEG)-1:0] i1_t,
    output wire pv
);
    wire [31:0] r_val_a;   // .r_val_a(bogus) in a comment
    core_c #(.A(NSEG >= 3 ? 2 : (NCH + 1))) u_c (
        .clk(clk), .i1_t(i1_t), .pv(pv),  // u_c ( .r_val_a(x) )
        .r_val_a(r_val_a));
    half u_ha (.clk(clk), .oval(r_val_a));
endmodule
"""
    txt, els, _ = X.apply(src, dict(pairs=[dict(inst="u_c", ports=["r_val_a"], form="hb4", n=2)]))
    assert len(els) == 1 and ".r_val_a(xs_c_r_val_a));" in txt and ".r_val_a(bogus) in a comment" in txt
    assert "u_c ( .r_val_a(x) )" in txt and txt.count("u_xshd_c_r_val_a") == 1
    assert txt.rstrip().endswith("endmodule") and txt.index("u_xshd_c_r_val_a") < txt.rindex("endmodule")
    with pytest.raises(X.XsError):
        X.apply("module broken #(parameter A = (1;\nendmodule\n", dict(pairs=[dict(inst="u_c", ports=["a"], form="hb4", n=1)]))
    assert X.apply("module nop;\nendmodule\n", dict(pairs=[dict(inst="u_c", ports=["a"], form="hb4", n=1)]))[1] == []


def test_abutted_capture_core_is_reported():
    """S81 live plan 1f8fcdd9c4d7 col_h9_r2: u_view.u_ha (17.28, 959.04, 241.92 x 95.04) ends exactly where u_view.u_c begins."""
    t = {"hard_cores": [
        {"inst": "u_r2.u_e13w.u_view.u_c", "module": "ot_v41_bf_col3_c", "orient": "R0", "origin_um": [259.2, 959.04], "outline_um": [208.248, 198.72]},
        {"inst": "u_r2.u_e13w.u_view.u_ha", "module": "ot_v41_bf16_half", "orient": "R0", "origin_um": [17.28, 959.04], "outline_um": [241.92, 95.04]},
        {"inst": "u_r2.u_e13w.u_view.u_hb", "module": "ot_v41_bf16_half", "orient": "R0", "origin_um": [17.28, 1062.72], "outline_um": [241.92, 95.04]},
        {"inst": "u_r2.u_far", "module": "x", "orient": "R0", "origin_um": [600.0, 959.04], "outline_um": [10.0, 10.0]}]}
    pair = dict(inst="u_c", types=["ot_v41_bf_col3_c"], ports=["r_v_a"], form="hb4", n=2)
    ab = X.abutted(t, pair)
    assert sorted(a[1] for a in ab) == ["u_r2.u_e13w.u_view.u_ha", "u_r2.u_e13w.u_view.u_hb"] and all(a[2] == 0 for a in ab)
    raw = {"partition_types": {"col_h9_r2__t1": t}, "clock": {"xtap_seam_element": {"col_h9_r2*": dict(pairs=[pair])}}}
    f = X.findings(raw)
    assert len(f) == 1 and "ABUT" in f[0] and "gap 0 um" in f[0]
    t["hard_cores"][0]["origin_um"] = [265.2, 959.04]          # a 6 um aisle: soft sites exist
    assert X.abutted(t, pair) == [] and X.findings(raw) == []
    assert X.abutted({}, pair) == [] and X.abutted({"hard_cores": [{"inst": "u_c"}]}, pair) == []
