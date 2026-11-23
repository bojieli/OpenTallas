"""ADV-GHOST-MACRO: fixture modeled on the real positive (S81 J7 plan a6771d121e95, svc_lo_dsdv_svc_rs__t3, FAM-S81-SVC-OWN
11-22): the plan places u_bound.g_u_rsv_06_u_u_att_{pvq,land,pmem}_capture.* SRAM rows that only the kit memory closure creates,
the bound carries the narrow pvq helper ot_bind_native_133b963e... instead of 9c28130c..., so the closure is NOT_APPLICABLE."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_ghost_macro as G  # noqa: E402

TN = "svc_lo_dsdv_svc_rs__t3"
MOD = "s81p_svc_lo_dsdv_svc_rs__t3"
CLOSURE = """NATIVE = ('ot_bind_native_193c9bdc13b0c4251a5bbbc4', 'ot_bind_native_9c28130c03bbd6a26f6fd9a5',
          'ot_bind_native_4c805a5536bda0930879099e', 'ot_hdc_v41x_attn_staging')
"""
SRAM = "physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.lef"


def bound(pvq_helper="ot_bind_native_133b963e2a98e3a3fc42b281"):
    return f"""`timescale 1ns/1ps
module {MOD} #(
    parameter integer X = 1
) (
    input wire clk
);
    wire [1063:0] w_u_rsv_06_u_u_att_pvq_RD_DATA;
    assign w_u_rsv_06_u_u_att_710_Y = w_u_rsv_06_u_u_att_pvq_RD_DATA[1063:0];
    ot_bind_native_193c9bdc13b0c4251a5bbbc4 g_u_rsv_06_u_u_att_pmem (.RD_ADDR(a), .RD_DATA(b));
    {pvq_helper} g_u_rsv_06_u_u_att_pvq (.RD_ADDR(a), .RD_DATA(w_u_rsv_06_u_u_att_pvq_RD_DATA));
    ot_bind_native_4c805a5536bda0930879099e g_u_rsv_06_u_u_att_land (.RD_ADDR(a));
    ot_hdc_v41x_attn_staging #(.SRAM_MACRO(1'b1)) u_u_rsv_06_u_u_att_u_eng_g_stage2_u_stage0 (.clk(clk));
    // as-built u_rsv_06.u.u_att.u_eng.g_t[0].g_ts.u_t.u_hc.g_h[0].u_c
    ot_s81c_attn_hcore #(.BZ0(1), .WPRE(2), .WSEG(0)) u_u_rsv_06_u_u_att_u_eng_g_t_0_g_ts_u_t_u_hc_g_h_0_u_c (
        .clk(clk)
    );
endmodule
"""


def plan(with_tr=True):
    hc = [{"inst": "u_rsv.u_att.u_eng.g_t[0].g_ts.u_t.u_hc.g_h[0].u_c", "module": "ot_s81c_attn_hcore",
           "lef": "physical/die_plan/s81/cores/svc/ot_s81c_attn_hcore.lef", "origin_um": [34.56, 34.56],
           "outline_um": [157.68, 259.2],
           "physical_inst": "u_bound.u_u_rsv_06_u_u_att_u_eng_g_t_0_g_ts_u_t_u_hc_g_h_0_u_c",
           "physical_master": "ot_s81c_attn_hcore"}]
    if with_tr:
        hc.append({"inst": "u_rsv.u_att.u_eng.g_tr[0].g_x.u_tr", "module": "ot_hdc_v41x_attn_tr_x",
                   "origin_um": [1252.8, 311.04], "outline_um": [60.48, 259.2],
                   "physical_inst": "u_rsv.u_att.u_eng.g_tr[0].g_x.u_tr", "physical_master": "ot_hdc_v41x_attn_tr_x_xoff0"})
    contents = [{"inst": "u_rsv", "module": "dsdv_svc_rs", "status": "rework"}]
    contents += [{"inst": "u_bound.g_u_rsv_06_u_u_att_pvq_capture.b[%d].s" % b, "lef": SRAM,
                  "module": "ot_sram_1r1w_32x128_m1_r0c0", "outline_um": [20.0, 30.0], "origin_um": [0, 0]}
                 for b in range(2)]
    contents.append({"inst": "u_bound.g_u_rsv_06_u_u_att_land_capture.g_w[0].g_b[0].ram", "lef": SRAM.replace("32x128", "160x256"),
                     "module": "ot_sram_1r1w_160x256_m1_r0c0", "outline_um": [40.0, 30.0], "origin_um": [0, 0]})
    return {"die": {"name": "s81"}, "partition_types": {TN: {"module": MOD, "hard": False, "hard_cores": hc,
                                                             "contents": contents}}}


def make_tree(tmp, pvq_helper="ot_bind_native_133b963e2a98e3a3fc42b281"):
    tree = tmp / "tree"
    rtl = tree / "physical/die_plan/s81/plan_of_record/native_bind/out/rtl"
    rtl.mkdir(parents=True)
    (rtl / (MOD + ".sv")).write_text(bound(pvq_helper))
    td = tree / "tools/die_plan"
    td.mkdir(parents=True)
    (td / "s81_svc_memory_closure.py").write_text(CLOSURE)
    return tree


def run(tmp, raw, tree):
    p = tmp / "plan.json"
    p.write_text(json.dumps(raw))
    return G.findings(raw, str(p), str(tree))


def test_positive_pvq_capture_ghosts(tmp_path):
    out = run(tmp_path, plan(), make_tree(tmp_path))
    line = next(x for x in out if x.startswith("WARN ADV-GHOST-MACRO " + TN + ":"))
    assert "4/5 placed rows" in line       # 2 pvq + 1 land capture rows + the tr plan-path row; the hcore is bound
    assert "pvq_capture" in line and "NOT_APPLICABLE" in line and "ot_bind_native_9c28130c" in line
    assert "u_rsv.u_att.u_eng.g_tr[*].g_x.u_tr x1" in line
    assert "summary: 4 ghost rows in 1 types" in out[-1]


def test_negative_closure_applies_and_tr_fixed(tmp_path):
    out = run(tmp_path, plan(with_tr=False), make_tree(tmp_path, "ot_bind_native_9c28130c03bbd6a26f6fd9a5"))
    assert len(out) == 1 and "summary: 0 ghost rows in 0 types" in out[0]


def test_fixed_by_dropping_capture_rows(tmp_path):
    raw = plan(with_tr=False)
    t = raw["partition_types"][TN]
    t["contents"] = [c for c in t["contents"] if "_capture" not in c["inst"]]
    out = run(tmp_path, raw, make_tree(tmp_path))
    assert "summary: 0 ghost rows" in out[-1] and len(out) == 1


def test_missing_bind_not_checked(tmp_path):
    (tmp_path / "empty").mkdir()
    out = run(tmp_path, plan(), tmp_path / "empty")
    assert out == ["WARN ADV-GHOST-MACRO not checked: no bound RTL (no BIND_OUT/rtl/<module>.sv for any type; pass bind_out=)"]


def test_never_raises():
    out = G.findings(None, None, None)
    assert len(out) == 1 and out[0].startswith("WARN ADV-GHOST-MACRO not checked")
