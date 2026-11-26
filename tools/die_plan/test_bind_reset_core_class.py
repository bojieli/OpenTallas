import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_reset_core_class as C  # noqa: E402

TXT = """module kv3_t (input wire clk, input wire [0:0] ri_pv_u_g0_j_rst_n);
    (* keep = 1 *) wire rst_n_t7;
    (* keep = 1 *) wire rst_n_t8;
    wire [0:0] rs_ri_pv_u_g0_j_rst_n_r0;
    ot_dp_rtail #(.D(4)) u_rs_ri_pv_u_g0_j_rst_n_r0 (.clk(clk), .a(1'b1), .d(q[0]), .q(rs_ri_pv_u_g0_j_rst_n_r0[0]));  // landing pad tail copy for core u_pv_u_g0_j: reset spine relay (1 load(s)); 6 stage(s) total; synchronous copy
    ot_qwen_tp8_pv_join_t #(.J_LAT(7), .MUT(0)) u_pv_u_g0_j (
        .clk(clk),
        .rst_n(rs_ri_pv_u_g0_j_rst_n_r0[0]),
        .sf(x[7:0])
    );
    ot_core_w u_w (
        .clk(clk),
        .rst_n(rst_n_t8)
    );
    qkd_fin #(.A(1)) u_fin (
        .clk(clk),
        .rst_n(some_local_net)
    );
endmodule
"""


def _w(*cores):
    return {"types": {"kv3_t": {"core_resets": list(cores)}}}


def test_spine_driven_core_is_a_mismatch():
    R = C.check(_w(dict(inst="pv__u_g0_j", pin="rst_n", tap=7, physical_inst="u_bound.u_pv_u_g0_j")), {"kv3_t": TXT})
    r = R["types"]["kv3_t"][0]
    assert (r["rtl_class"], r["agrees"], R["mismatches"]) == ("spine", False, 1)
    assert r["rtl_net"] == "rs_ri_pv_u_g0_j_rst_n_r0[0]"


def test_wavefront_tap_agrees():
    R = C.check(_w(dict(inst="w", pin="rst_n", tap=8, physical_inst="u_bound.u_w")), {"kv3_t": TXT})
    assert R["types"]["kv3_t"][0]["rtl_class"] == "wavefront" and R["mismatches"] == 0


def test_wrong_tap_is_other():
    R = C.check(_w(dict(inst="w", pin="rst_n", tap=7, physical_inst="u_bound.u_w")), {"kv3_t": TXT})
    assert R["types"]["kv3_t"][0]["rtl_class"] == "other"


def test_internal_leaf_resolves_to_ancestor_instance():
    R = C.check(_w(dict(inst="fin_lo", pin="rst_n", tap=9, physical_inst="u_bound.u_fin.g_sl[0].u_sl")), {"kv3_t": TXT})
    r = R["types"]["kv3_t"][0]
    assert (r["rtl_inst"], r["rtl_class"]) == ("u_fin", "other")


def test_missing_type_rtl_is_reported_not_dropped():
    R = C.check(_w(dict(inst="w", pin="rst_n", tap=8, physical_inst="u_bound.u_w")), {})
    assert R["types"]["kv3_t"][0]["rtl_class"] == "missing" and R["mismatches"] == 1


def test_main_report_only_leaves_bind_reset_unchanged(tmp_path):
    W = _w(dict(inst="pv__u_g0_j", pin="rst_n", tap=7, physical_inst="u_bound.u_pv_u_g0_j"))
    (tmp_path / "bind_reset.json").write_text(json.dumps(W))
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "kv3_t_part.sv").write_text(TXT.replace("module kv3_t ", "module kv3_t_part "))
    before = (tmp_path / "bind_reset.json").read_bytes()
    assert C.main(["x", str(tmp_path)]) == 0
    assert (tmp_path / "bind_reset.json").read_bytes() == before
    R = json.loads((tmp_path / "bind_reset_core_class.json").read_text())
    assert R["mode"] == "report-only" and R["by_class"] == {"spine": 1}


def _w2():
    return {"types": {"kv3_t": {"core_resets": [
                dict(inst="pv__u_g0_j", pin="rst_n", tap=7, physical_inst="u_bound.u_pv_u_g0_j"),
                dict(inst="w", pin="rst_n", tap=8, physical_inst="u_bound.u_w")]}},
            "parts": {"p0": {"type": "kv3_t", "release": 20, "core_release": {"pv__u_g0_j.rst_n": 21, "w.rst_n": 21}},
                      "p1": {"type": "kv3_x", "release": 30, "core_release": {"pv__u_g0_j.rst_n": 31}}}}


def test_apply_spine_publishes_spine_consumers_only():
    W = _w2()
    R = C.check(W, {"kv3_t": TXT})
    assert C.apply_spine(W, R, {"kv3_t": TXT}) == 1
    c0, c1 = W["types"]["kv3_t"]["core_resets"]
    assert (c0["reset_class"], c0["tap_used"], c0["spine_stages"]) == ("spine", False, 6)
    assert "reset_class" not in c1                                   # wavefront core unchanged
    p0 = W["parts"]["p0"]
    assert p0["core_release"] == {"w.rst_n": 21}                     # the untrue wavefront number is gone
    assert p0["spine_release"]["pv__u_g0_j.rst_n"]["spine_stages"] == 6
    assert W["parts"]["p1"]["core_release"] == {"pv__u_g0_j.rst_n": 31}   # other type untouched
    assert W["core_reset_classes"]["spine"] == 1


def test_apply_spine_noop_when_all_wavefront():
    W = {"types": {"kv3_t": {"core_resets": [dict(inst="w", pin="rst_n", tap=8, physical_inst="u_bound.u_w")]}},
         "parts": {"p0": {"type": "kv3_t", "core_release": {"w.rst_n": 21}}}}
    before = json.dumps(W, sort_keys=True)
    assert C.apply_spine(W, C.check(W, {"kv3_t": TXT}), {"kv3_t": TXT}) == 0
    assert json.dumps(W, sort_keys=True) == before


def test_stages_from_bare_synchroniser():
    t = "    ot_dp_rsync #(.W(1), .S(2)) u_rs_ri_a_rst_n (.clk(clk), .a(ri_a_rst_n), .q(ri_a_rst_n_q));\n"
    assert C._stages(t, "ri_a_rst_n_q[0]") == 2


def test_bound_leaf_identity_takes_precedence_over_matching_tail():
    instance = "u_r0.u_e0.u_w"
    W = _w(dict(inst=instance, pin="rst_n", tap=8))
    text = TXT.replace("endmodule", "ot_core_w u_u_r0_u_e0_u_w (.rst_n(rst_n_t7));\nendmodule")
    mapped = {"kv3_t": [dict(inst=instance, pin="rst_n", leaf="u_u_r0_u_e0_u_w", reset="rst_n_t8")]}
    row = C.check(W, {"kv3_t": text}, mapped)["types"]["kv3_t"][0]
    assert (row["rtl_inst"], row["rtl_net"], row["rtl_class"]) == ("u_u_r0_u_e0_u_w", "rst_n_t7", "other")


def test_disagreeing_bound_leaf_drivers_do_not_publish_a_spine():
    W = _w(dict(inst="split_core", pin="rst_n", tap=8))
    mapped = {"kv3_t": [dict(inst="split_core", pin="rst_n", leaf=leaf) for leaf in ("u_w", "u_pv_u_g0_j")]}
    report = C.check(W, {"kv3_t": TXT}, mapped)
    assert report["by_class"] == {"ambiguous": 1}
    assert C.apply_spine(W, report, {"kv3_t": TXT}) == 0
