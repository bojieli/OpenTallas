"""pytest: ADV-TIED-BITS predicts the S81 svc slang shared-ABI truncation (c8 / lk_ES0, 11-24) from the bind-tree RTL."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_tied_bits as A  # noqa: E402

KREG = "module ot_hdc_v41x_kreg #(parameter integer W = 1) (input clk, input [W-1:0] d, output [W-1:0] q);\nendmodule\n"
ENG = """module ot_s81_svc_attn_s (input clk);
  wire [575:0] a, b; wire [1039:0] c, e;
  ot_hdc_v41x_kreg #(.W(576)) u_ib (.clk(clk), .d(a), .q(b));
  ot_hdc_v41x_kreg #(.W(1040)) u_l (.clk(clk), .d(c), .q(e));
  ot_fixed u_f (.clk(clk));
endmodule
module ot_fixed (input clk); endmodule
"""


def _tree(tmp_path, listed=()):
    t = tmp_path / "tree"
    (t / "rtl/hdc").mkdir(parents=True)
    (t / "rtl/s81").mkdir(parents=True)
    (t / "rtl/hdc/ot_hdc_v41x_kreg.sv").write_text(KREG)
    (t / "rtl/s81/attn.sv").write_text(ENG)
    nb = t / "physical/die_plan/s81/plan_of_record/native_bind"
    nb.mkdir(parents=True)
    (nb / "asbuilt_run.json").write_text(json.dumps({"frontend": "slang", "slang_parameterized_blackboxes": list(listed), "dissolve": ["ot_s81_svc_attn_s"]}))
    raw = {"die": "s81", "partition_types": {"svc_hi_attn__t1": {"module": "p", "contents": [{"inst": "u", "module": "ot_s81_svc_attn_s"}]}}}
    return str(t), raw


def test_unlisted_parameterized_leaf_is_predicted(tmp_path):
    t, raw = _tree(tmp_path)
    out = A.findings(raw, "p", t)
    hit = [x for x in out if "PREDICTED ot_hdc_v41x_kreg" in x]
    assert hit and "2 instance(s) with 2 distinct" in hit[0] and "est >= 928 bit(s)" in hit[0] and "svc_hi_attn__t1" in hit[0]
    assert "ot_fixed" not in " ".join(out) and "PREDICTED 1 unlisted" in out[-1]


def test_listed_leaf_is_quiet(tmp_path):
    t, raw = _tree(tmp_path, listed=["ot_hdc_v41x_kreg"])
    out = A.findings(raw, "p", t)
    assert len(out) == 1 and "PREDICTED 0 unlisted" in out[0]


def test_native_frontend_not_applicable(tmp_path):
    t, raw = _tree(tmp_path)
    ab = os.path.join(t, "physical/die_plan/s81/plan_of_record/native_bind/asbuilt_run.json")
    d = json.load(open(ab))
    d["frontend"] = "native"
    json.dump(d, open(ab, "w"))
    out = A.findings(raw, "p", t)
    assert len(out) == 1 and "PREDICTED not applicable" in out[0] and "frontend native" in out[0]
