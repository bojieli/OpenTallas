"""KW-FIX-24 (COORD 11-06 21:2x (5)): GRAY-MSB TWIN LEC hints are a generator default for every kit whose RTL holds a
gray-pointer FIFO (rx_bm3_rest / serdes RX / HEAD rxq / UCIe rate match); other kits stay byte-identical."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

TOOL = Path(__file__).resolve().parent
REPO = TOOL.parents[1]
sys.path.insert(0, str(TOOL))
import lec_gray_twin as G  # noqa: E402

RATE_MATCH = REPO / "rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv"          # defines ot_s81_rate_match
PROVED = ["gold", "ff:u_dut.u_fcore.u_rm.wp[3]", ["eq", "gate", "ff:u_dut.u_fcore.u_rm.wp_g[3]", 0]]  # HBM vA/vB2 EQ

SHELL = """
module rx_rest (input wire clk, rck, rst_n, input wire [511:0] d, output wire [511:0] q, output wire f);
    rx_rest__fcore #(.SEAM(7)) u_fcore (.clk(clk), .rck(rck), .rst_n(rst_n), .d(d), .q(q), .f(f));
endmodule
module rx_rest__fcore #(parameter integer SEAM = 2) (input wire clk, rck, rst_n, input wire [511:0] d,
        output wire [511:0] q, output wire f);
    // ot_s81_rate_match u_fake (...) in a comment is not an instance
    ot_s81_rate_match u_rm (.wclk(rck), .wrst_n(rst_n), .w_v(1'b1), .w_d(d), .rclk(clk), .rrst_n(rst_n), .r_d(q),
                            .fault(f));
endmodule
"""


def kit(tmp_path, *texts, files=(RATE_MATCH,)):
    kd = tmp_path / "kit"
    (kd / "rtl").mkdir(parents=True)
    for f in files:
        (kd / "rtl" / Path(f).name).write_text(Path(f).read_text())
    for i, t in enumerate(texts):
        (kd / "rtl" / f"t{i}.sv").write_text(t)
    return kd


def test_rate_match_rx_kit_gets_the_proved_hint_and_both_orientations(tmp_path):
    kd = kit(tmp_path, SHELL)
    h = G.gray_twin_hints(kd / "rtl", "rx_rest")
    assert PROVED in h                                           # exactly the COORD 21:2x / DIE-HBM-82-RF hint
    assert ["gold", "ff:u_dut.u_fcore.u_rm.wp_g[3]", ["eq", "gate", "ff:u_dut.u_fcore.u_rm.wp[3]", 0]] in h
    assert ["gold", "ff:u_dut.u_fcore.u_rm.rp[3]", ["eq", "gate", "ff:u_dut.u_fcore.u_rm.rp_g[3]", 0]] in h
    assert ["gold", "ff:u_dut.u_fcore.u_rm.rp_g[3]", ["eq", "gate", "ff:u_dut.u_fcore.u_rm.rp[3]", 0]] in h
    assert len(h) == 4 and not any("u_fake" in x[1] for x in h)
    st = G.stage(kd, "rx_rest")
    assert st["count"] == 4 and json.loads((kd / "lec_hints.json").read_text()) == h
    assert st["sha256"] == hashlib.sha256((kd / "lec_hints.json").read_bytes()).hexdigest()
    assert G.stage(kd, "rx_rest") is None                        # idempotent: nothing new, file untouched


def test_every_repo_gray_fifo_form_is_detected():
    """S81/HBM ot_s81_rate_match, HEAD ot_s81hd_rate_match_q, UCIe ot_ucie_rate_match_pf (split wp / rp blocks)."""
    for f, mod in (("rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv", "ot_s81_rate_match"),
                   ("rtl/dsrom_sys/s81_head/ot_s81hd_serdes_rxq.sv", "ot_s81hd_rate_match_q"),
                   ("rtl/dsrom_sys/s81_link/ucie/ot_ucie_rate_match_pf.sv", "ot_ucie_rate_match_pf")):
        mods = G.parse_modules([(REPO / f).read_text()])
        assert sorted(G.gray_pointers(mods[mod])) == [("rp", 3), ("wp", 3)], mod


def test_kit_without_gray_pointer_is_unchanged(tmp_path):
    kd = kit(tmp_path, "module plain (input wire clk, output reg [3:0] q, output reg [3:0] q_g);\n"
             "  always @(posedge clk) begin q <= q + 1'b1; q_g <= q; end\nendmodule\n", files=())
    assert G.gray_twin_hints(kd / "rtl", "plain") == []
    assert G.stage(kd, "plain") is None and not (kd / "lec_hints.json").exists()
    assert G.stage(tmp_path / "no_rtl_kit", "plain") is None


def test_rate_match_not_under_the_top_gives_no_hint(tmp_path):
    kd = kit(tmp_path, "module other (input wire a, output wire b); assign b = a; endmodule\n")
    assert G.gray_twin_hints(kd / "rtl", "other") == []
    assert G.gray_twin_hints(kd / "rtl", "missing_top") == []


def test_width_mismatch_is_not_a_twin():
    body = G.parse_modules(["module m (input wire c); reg [3:0] p; reg [4:0] p_g;\n"
                            "always @(posedge c) begin p <= p + 1'b1; p_g <= (p + 1'b1) ^ ((p + 1'b1) >> 1); end\n"
                            "endmodule\n"])["m"]
    assert G.gray_pointers(body) == []


def test_existing_kit_hints_are_kept_and_never_overridden(tmp_path):
    kd = kit(tmp_path, SHELL)
    own = [["gold", "ff:u_dut.u_fcore.u_rm.wp[3]", ["const", 0]],          # kit-specific: wins over the class hint
           ["gold", "ff:u_dut.x.q", ["eq", "gold", "ff:u_dut.y.q", 0]]]
    (kd / "lec_hints.json").write_text(json.dumps(own))
    st = G.stage(kd, "rx_rest")
    out = json.loads((kd / "lec_hints.json").read_text())
    assert out[:2] == own and len(out) == 5 and st["count"] == 5
    assert PROVED not in out
    assert sum(1 for x in out if x[1] == "ff:u_dut.u_fcore.u_rm.wp[3]") == 1


def test_hint_plan_object_gets_class_hints_in_post(tmp_path):
    kd = kit(tmp_path, SHELL)
    plan = {"schema": "opentallas.lec_hint_plan.v1", "preseed": [PROVED], "post": [], "discovery_rounds": 0}
    (kd / "lec_hints.json").write_text(json.dumps(plan))
    G.stage(kd, "rx_rest")
    out = json.loads((kd / "lec_hints.json").read_text())
    assert out["preseed"] == [PROVED] and out["discovery_rounds"] == 0 and len(out["post"]) == 3
    import lec
    pre, post, rounds = lec.decode_hint_plan(out)                 # still a valid plan for the LEC consumer
    assert pre == [PROVED] and len(post) == 3 and rounds == 0


def test_type_kit_freeze_records_gray_hints(tmp_path):
    import gen_phys
    kd = kit(tmp_path, SHELL)
    (kd / "io.tcl").write_text("")
    own = [["gold", "ff:u_dut.a.q", ["eq", "gold", "ff:u_dut.b.q", 0]]]
    p = SimpleNamespace(name="no_contract", types={"t": dict(outline_um=[10, 10], module="rx_rest", lec_hints=own)})
    fz = gen_phys.write_partition_freeze(p, "t", kd, [])
    out = json.loads((kd / "lec_hints.json").read_text())
    assert out[0] == own[0] and PROVED in out and len(out) == 5
    assert fz["lec_hints"]["count"] == 5 and "ff:u_dut.u_fcore.u_rm.wp[3]" in fz["lec_hints"]["gray_msb_twin"]
    assert fz["lec_hints"]["sha256"] == hashlib.sha256((kd / "lec_hints.json").read_bytes()).hexdigest()


def test_core_generators_stage_gray_hints_before_kit_hash():
    gens = {"physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py": "lec_gray_twin.stage(kd, module)",
            "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py": "lec_gray_twin.stage(kd, mod)",
            "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py": "lec_gray_twin.stage(kd, mod)",
            "physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py": "lec_gray_twin.stage(kd, mod)"}
    for rel, call in gens.items():
        txt = (REPO / rel).read_text()
        assert txt.count(call) == 1, rel
        assert txt.index('lec_hints.json"') < txt.index(call) < txt.rindex("kit_hash(kd)"), rel
