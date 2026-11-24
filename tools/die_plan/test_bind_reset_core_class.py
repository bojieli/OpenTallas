import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_reset_core_class as C  # noqa: E402

TXT = """module kv3_t (input wire clk, input wire [0:0] ri_pv_u_g0_j_rst_n);
    (* keep = 1 *) wire rst_n_t7;
    (* keep = 1 *) wire rst_n_t8;
    wire [0:0] rs_ri_pv_u_g0_j_rst_n_r0;
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
