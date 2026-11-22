"""QC-COLL-FAULT 11-21 (FABLE-FIX-QC-COLL): internal_stations[].or_groups on a 1-bit OUT bus.

The coll_core collective fault is an OR of 29 sources up to 1,453 um from the N-face register; serial stations after the
OR leave the source legs long.  or_groups builds the same depth as parallel chains, one per source region, ORed at the
face register (Codex's private fault pipe as a generator form).  Absent key = unchanged output.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_istations as KI  # noqa: E402
import schema  # noqa: E402

BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire [7:0] s, input wire [1:0] f, input wire m, output wire [1:0] o_f);
    wire rst_n_t5;
    wire [0:0] w_or_18_Y;
    wire [0:0] w_or_20_Y;
    wire [0:0] w_red_19_Y;
    wire [0:0] w_mid_Y;
    wire [1:0] w_face_cdc;
    assign rst_n_t5 = rst_n;
    assign w_face_cdc = f;
    ot_dp_st #(.W(1)) u_bout_o_f (.clk(clk), .rst_n(rst_n_t5), .d(w_or_20_Y[0]), .ea(rst_n), .q(o_f[0:0]), .eq(o_f[1]));
    assign w_or_18_Y = w_mid_Y[0] | s[7];  // x.sv:66.15-66.44
    assign w_or_20_Y = w_or_18_Y[0] | w_red_19_Y[0];  // x.sv:66.15-66.67
    assign w_red_19_Y = |{s[6:3], s[0], w_face_cdc[1:0]};  // x.sv:66.46-66.66
    assign w_mid_Y = m | s[1];
endmodule
"""
ST = """module ot_dp_st #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d, input wire ea,
    output reg [W-1:0] q, output reg eq);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n) if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
"""
GROUPS = [dict(name="south", match=[r"^w_face_cdc\[", r"^s\[0\]$"], regs_um=[[1, 1], [1, 2], [1, 3]]),
          dict(name="middle", match=[r"^m$", r"^s\[1\]$"], regs_um=[[5, 1], [5, 2], [5, 3]]),
          dict(name="north", match=["*"], regs_um=[[9, 1], [9, 2], [9, 3]])]


def kit(tmp_path, groups=GROUPS, bound=BOUND, regs=None, **row):
    e = dict(conn="bus:o_f", from_um=[0, 0], to_um=[1, 9], regs_um=regs or [[1, 1], [1, 2], [1, 3]], bits=1, **row)
    if groups is not None:
        e["or_groups"] = groups
    plan = dict(partition_types=dict(t=dict(buses=[dict(name="o_f", dir="out", width=1, kind="ctl")], internal_stations=[e])))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    kd = tmp_path / "kit"
    kd.mkdir(exist_ok=True)
    b = kd / "t_part_bound.sv"
    b.write_text(bound)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(b)])))
    return pf, kd, b


def run(pf, kd):
    return subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)], capture_output=True, text=True)


def test_atoms_expand_through_pure_or_assigns_only():
    atoms = KI.or_atoms("t", "o_f", BOUND, "w_or_20_Y[0]")
    assert atoms == sorted(["m", "s[1]", "s[7]", "s[3]", "s[4]", "s[5]", "s[6]", "s[0]", "w_face_cdc[0]", "w_face_cdc[1]"])
    with pytest.raises(SystemExit, match="not a pure OR"):
        KI.or_atoms("t", "o_f", BOUND.replace("m | s[1]", "m | (s[1] & s[2])"), "w_or_20_Y[0]")
    with pytest.raises(SystemExit, match="not a 1-bit OR wire"):
        KI.or_atoms("t", "o_f", BOUND.replace("wire [0:0] w_mid_Y", "wire [1:0] w_mid_Y"), "w_or_20_Y[0]")


def test_groups_are_parallel_chains_with_sites_and_receipts(tmp_path):
    pf, kd, b = kit(tmp_path)
    r = run(pf, kd)
    assert r.returncode == 0, r.stderr
    txt = b.read_text()
    inst = re.findall(r"ot_dp_st #\(\.W\(1\)\) (u_ist_\w+) \(\.clk\(clk\), \.rst_n\((\w+)\), \.d\((\w+)\), \.ea\((\w+)\)", txt)
    assert [i[0] for i in inst] == ["u_ist_o_f_0", "u_ist_o_f_1", "u_ist_o_f_2", "u_ist_o_f__ogmiddle_0", "u_ist_o_f__ogmiddle_1",
                                    "u_ist_o_f__ogmiddle_2", "u_ist_o_f__ognorth_0", "u_ist_o_f__ognorth_1", "u_ist_o_f__ognorth_2"]
    assert {i[1] for i in inst} == {"rst_n_t5"}                       # the face register's reset net
    assert [i[3] for i in inst if i[0].endswith("_0")] == ["rst_n"] * 3   # every chain starts at the face epoch source
    assert "assign o_f_ogd0 = |{s[0], w_face_cdc[0], w_face_cdc[1]};" in txt
    assert "assign o_f_ogd1 = |{m, s[1]};" in txt
    assert "assign o_f_ogd2 = |{s[3], s[4], s[5], s[6], s[7]};" in txt
    assert "assign o_f_ogy = |{o_f_is2_q, o_f_ogmiddle_is2_q, o_f_ognorth_is2_q};" in txt
    assert ".d(o_f_ogy), .ea(o_f_is2_eq), .q(o_f[0:0])" in txt
    tcl = (kd / "istations.tcl").read_text()
    for nm, x, y in [("u_ist_o_f_1", 1, 2), ("u_ist_o_f__ogmiddle_0", 5, 1), ("u_ist_o_f__ognorth_2", 9, 3)]:
        assert f"is_place {{*{nm}[./]*}} {x} {y} ist:o_f" in tcl
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    main = [x for x in rep if x.get("conn") == "bus:o_f"]
    assert len(main) == 1 and main[0]["planned"] == 3 and main[0]["inserted"] == 3 and main[0]["stations"] == ["u_ist_o_f_0", "u_ist_o_f_1", "u_ist_o_f_2"]
    extra = [x for x in rep if x.get("or_group")]
    assert [x["or_group"] for x in extra] == ["bus:o_f:middle", "bus:o_f:north"] and all(len(x["stations"]) == 3 and "conn" not in x for x in extra)
    # the bind's native receipt check (bind.py kit_native_stations): every u_ist_ instance declared once
    declared = [n for x in rep if "stations" in x for n in x["stations"]]
    assert sorted(declared) == sorted(i[0] for i in inst)
    # second application on the produced kit: no new stations, same sites and receipts
    r2 = run(pf, kd)
    assert r2.returncode == 0, r2.stderr
    assert b.read_text() == txt and (kd / "istations.tcl").read_text() == tcl
    rep2 = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    assert [x["stations"] for x in rep2] == [x["stations"] for x in rep] and all(x["inserted"] == 0 for x in rep2)


def test_absent_key_is_the_plain_serial_chain(tmp_path):
    pf, kd, b = kit(tmp_path, groups=None)
    assert run(pf, kd).returncode == 0
    txt = b.read_text()
    assert "_og" not in txt and txt.count("u_ist_o_f_") == 3 and ".d(w_or_20_Y[0]), .ea(rst_n)" in txt


@pytest.mark.parametrize("case", ["two_groups", "no_group", "depth", "first_sites", "empty_group", "join"])
def test_fail_closed(tmp_path, case):
    g = json.loads(json.dumps(GROUPS))
    row = {}
    if case == "two_groups":
        g[1]["match"].append(r"^s\[0\]$")
    if case == "no_group":
        g[2]["match"] = [r"^s\[7\]$"]
    if case == "depth":
        g[1]["regs_um"] = g[1]["regs_um"][:2]
    if case == "first_sites":
        g[0]["regs_um"][0] = [2, 2]
    if case == "empty_group":
        g[1]["match"] = ["^nothing$"]
    if case == "join":
        row["join"] = [dict(bits=[0, 0], stage=1)]
    pf, kd, b = kit(tmp_path, groups=g, **row)
    r = run(pf, kd)
    assert r.returncode != 0 and "or_groups" in r.stderr and b.read_text() == BOUND


def test_schema_accepts_the_row_key():
    it = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["internal_stations"]["items"]
    assert it["additionalProperties"] is False and "or_groups" in it["properties"]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_miter_equals_serial_stations_before_the_face_register(tmp_path):
    """bit + epoch, under reset pulses, against 3 plain serial stations in front of the same face register"""
    pf, kd, b = kit(tmp_path)
    assert run(pf, kd).returncode == 0
    ref = tmp_path / "ref"
    ref.mkdir()
    pr, kr, br = kit(ref, groups=None)
    assert run(pr, kr).returncode == 0
    (tmp_path / "st.sv").write_text(ST)
    (tmp_path / "dut.sv").write_text(b.read_text())
    (tmp_path / "ref.sv").write_text(br.read_text().replace("module t_part_bound", "module t_part_ref"))
    (tmp_path / "tb.sv").write_text("""module tb;
reg clk = 0, rst_n = 0; reg [7:0] s = 0; reg [1:0] f = 0; reg m = 0;
wire [1:0] a, b; integer i, one = 0, zero = 0;
always #5 clk = ~clk;
t_part_bound dut(.clk(clk), .rst_n(rst_n), .s(s), .f(f), .m(m), .o_f(a));
t_part_ref   rf (.clk(clk), .rst_n(rst_n), .s(s), .f(f), .m(m), .o_f(b));
initial begin
  for (i = 0; i < 4000; i = i + 1) begin
    @(negedge clk);
    rst_n = (i % 97 != 0) && (i % 97 != 1);
    {s, f, m} = 0;
    if (i % 3 != 0) begin : one_hot
      reg [10:0] v; v = 11'b1 << $urandom_range(0, 10); {s, f, m} = v;
    end
    @(posedge clk); #1;
    if (i >= 6) begin
      if (a !== b) begin $display("MISMATCH i=%0d %b %b", i, a, b); $fatal(1); end
      if (a[1] && a[0]) one = one + 1;
      if (a[1] && !a[0]) zero = zero + 1;
    end
  end
  if (one == 0 || zero == 0) begin $display("COVERAGE"); $fatal(1); end
  $display("OR_GROUPS_MITER_PASS one=%0d zero=%0d", one, zero);
  $finish;
end
endmodule
""")
    c = subprocess.run(["iverilog", "-g2012", "-o", "m", "st.sv", "dut.sv", "ref.sv", "tb.sv"], cwd=tmp_path, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr
    v = subprocess.run(["vvp", "m"], cwd=tmp_path, capture_output=True, text=True)
    assert "OR_GROUPS_MITER_PASS" in v.stdout, v.stdout + v.stderr
