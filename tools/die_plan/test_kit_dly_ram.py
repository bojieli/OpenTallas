"""FIX-KV-PV-MESOFIFO 11-23: kit_dly_ram.py (landing-pad trunks in SRAM rings, kit RTL post-pass, opt-in plan pad_ram)."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import kit_dly_lockup as dl  # noqa: E402
import kit_dly_ram as kr  # noqa: E402

CELLS = """
module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    assign q = r[D-1];
endmodule
module ot_dp_dly_keep #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    assign q = r[D-1];
endmodule
module core #(parameter integer N = 1) (input wire clk, input wire [N-1:0] a, output reg [N-1:0] y);
    always @(posedge clk) y <= a;
endmodule
"""

NB = 300          # in-lane bits: two chunks (256 + 44)


def bound_text():
    """a bound module in the bind's statement forms: tail-split trunks (+ one chained piece), tail copies for two cores,
    one unsplit pad read by a core directly, one shallow pad (below min_d), one intra pipe (never touched)"""
    decl, body = [], []
    for j in range(NB):
        D = 40 + (j % 5)                     # 40..44: one chunk per 256 bits, residual <= 4
        t = f"pd{D}_i_x_{j}_t_{D + 2}"
        decl.append(f"    wire [0:0] {t};")
        body.append(f"    ot_dp_dly_keep #(.W(1), .D({D})) u_{t} (.clk(clk), .d(i_x_q[{j}]), .q({t}));  "
                    f"// landing pad trunk: shared stages of pad {D + 2} (tail split)")
        for c in ("ca", "cb"):
            n = f"pd2_i_x_{j}_{c}_{D + 2}"
            decl.append(f"    wire [0:0] {n};")
            body.append(f"    ot_dp_dly_keep #(.W(1), .D(2)) u_{n} (.clk(clk), .d({t}[0]), .q({n}));  "
                        f"// landing pad tail copy for core u_{c}: route 900 um")
    # chained trunk piece on bit 0 (pad + 1), read by core cb bit 0 of its second port
    decl.append("    wire [0:0] pd1_i_x_0_t_43;")
    body.append(f"    ot_dp_dly_keep #(.W(1), .D(1)) u_pd1_i_x_0_t_43 (.clk(clk), .d(pd40_i_x_0_t_42[0]), .q(pd1_i_x_0_t_43));  "
                "// landing pad trunk: shared stages of pad 43 (tail split)")
    for j in range(64):                      # unsplit pads, 30 cycles, read by core cc directly
        n = f"pd30_i_y_{j}"
        decl.append(f"    wire [0:0] {n};")
        body.append(f"    ot_dp_dly #(.W(1), .D(30)) u_{n} (.clk(clk), .d(i_y_q[{j}]), .q({n}));  // landing pad: as-built relative timing")
    for j in range(8):                       # shallow
        n = f"pd3_i_y_{j}"
        decl.append(f"    wire [0:0] {n};")
        body.append(f"    ot_dp_dly #(.W(1), .D(3)) u_{n} (.clk(clk), .d(i_y_q[{j}]), .q({n}));  // landing pad: as-built relative timing")
    decl.append("    wire [7:0] d9_s_o;")
    body.append("    ot_dp_dly #(.W(8), .D(9)) u_d9_s_o (.clk(clk), .d(i_y_q[7:0]), .q(d9_s_o));")
    ca = "{" + ", ".join(f"pd2_i_x_{j}_ca_{40 + (j % 5) + 2}" for j in reversed(range(NB))) + "}"
    cb = "{" + ", ".join(f"pd2_i_x_{j}_cb_{40 + (j % 5) + 2}" for j in reversed(range(NB))) + "}"
    cc = "{" + ", ".join([f"pd30_i_y_{j}" for j in reversed(range(64))]) + "}"
    sh = "{" + ", ".join([f"pd3_i_y_{j}" for j in reversed(range(8))]) + "}"
    body += [f"    core #(.N({NB})) u_ca (.clk(clk), .a({ca}), .y(y_a));",
             f"    core #(.N({NB})) u_cb (.clk(clk), .a({cb}), .y(y_b));",
             "    core #(.N(64)) u_cc (.clk(clk), .a(" + cc + "), .y(y_c));",
             "    core #(.N(8)) u_cd (.clk(clk), .a(" + sh + "), .y(y_d));",
             "    core #(.N(8)) u_ce (.clk(clk), .a(d9_s_o), .y(y_e));",
             "    core #(.N(1)) u_cf (.clk(clk), .a(pd1_i_x_0_t_43), .y(y_f));"]
    return (f"module top_bound (\n    input wire clk,\n    input wire [{NB - 1}:0] i_x_q,\n    input wire [63:0] i_y_q,\n"
            f"    output wire [{NB - 1}:0] y_a,\n    output wire [{NB - 1}:0] y_b,\n    output wire [63:0] y_c,\n"
            "    output wire [7:0] y_d,\n    output wire [7:0] y_e,\n    output wire [0:0] y_f\n);\n"
            + "\n".join(decl) + "\n" + "\n".join(body) + "\nendmodule\n")


TYPE = {"outline_um": [1200.0, 900.0], "pad_ram": {"min_flops": 1024, "keepout_um": [[550.0, 0.0, 650.0, 900.0]]},
        "hard_cores": [{"inst": "ca", "origin_um": [20.0, 20.0], "outline_um": [300.0, 200.0]},
                       {"inst": "cb", "origin_um": [880.0, 20.0], "outline_um": [300.0, 200.0]},
                       {"inst": "cc", "origin_um": [20.0, 680.0], "outline_um": [300.0, 200.0]},
                       {"inst": "cd", "origin_um": [880.0, 680.0], "outline_um": [300.0, 200.0]}]}
PINS = [("i_x", b, "M5", 600.0, 900.0, "N") for b in range(NB)] + [("i_y", b, "M5", 0.0, 450.0, "W") for b in range(64)]


def test_plan_chunks_sites_and_counts():
    txt = bound_text()
    chunks, st, cand = kr.plan(txt, TYPE, PINS, kr.cfg_of(TYPE))
    by = {(c["bus"], c["bits"]): c for c in chunks}
    assert set(by) == {("i_x", 256), ("i_x", 44), ("i_y", 64)}
    x0 = by[("i_x", 256)]
    assert x0["base"] == 40 and x0["cores"] == ["ca", "cb"] and x0["resid"] > 0
    assert x0["lead"] + x0["trail"] + x0["ram_d"] <= 40
    assert by[("i_y", 64)]["cores"] == ["cc"]          # unsplit pad: the core reading it directly
    W, H = TYPE["outline_um"]
    boxes = []
    for c in chunks:                                  # inside, clear of cores / keepout / each other
        x, y = c["origin_um"]
        b = (x, y, x + kr.MACRO_UM[0], y + kr.MACRO_UM[1])
        assert 0 <= b[0] and b[2] <= W and 0 <= b[1] and b[3] <= H
        assert not (b[0] < 650 + 10 and 550 - 10 < b[2])
        for o in boxes:
            assert b[2] <= o[0] or o[2] <= b[0] or b[3] <= o[1] or o[3] <= b[1]
        boxes.append(b)
    assert st["candidates"] == NB + 64 + 8 - 0       # chained piece and intra pipe are not candidates
    assert all(not n.startswith("u_pd3_") for c in chunks for n in c["names"])
    assert [m[0] for m in kr.macros_of(chunks)] == [f"u_bound.{c['inst']}.g_b[0].u_m" for c in chunks]


def test_respects_firm_seats_and_assigned_taps(tmp_path):
    f = tmp_path / "top_bound.sv"
    f.write_text(bound_text())
    base = kr.plan_kit([f], TYPE, PINS)[f.name][1]
    seats = [(r["origin_um"][0] + kr.MACRO_UM[0] / 2, r["origin_um"][1] + kr.MACRO_UM[1] / 2)
             for r in base]
    t = dict(TYPE, internal_stations=[{"bit_sites_um": [[list(seats[0])]]}],
             relay_sites={"relay": list(seats[1])})
    clock_sites = [("clk_t2", *seats[2])]
    chunks = kr.plan_kit([f], t, PINS, clock_sites=clock_sites)[f.name][1]
    assert len(chunks) == len(base)
    for row in chunks:
        x, y = row["origin_um"]
        w, h = kr.MACRO_UM
        for sx, sy in seats:
            assert not (x - 10 < sx < x + w + 10 and y - 10 < sy < y + h + 10)


def test_absent_key_is_no_change(tmp_path):
    f = tmp_path / "top_bound.sv"
    f.write_text(bound_text())
    assert kr.plan_kit([f], {k: v for k, v in TYPE.items() if k != "pad_ram"}) == {}


def test_staged_source_must_match(tmp_path):
    f = tmp_path / "src" / "top_bound.sv"
    f.parent.mkdir()
    f.write_text(bound_text())
    pl = kr.plan_kit([f], TYPE, PINS)
    st = tmp_path / "rtl"
    st.mkdir()
    (st / "top_bound.sv").write_text(bound_text() + "\n// edited\n")
    with pytest.raises(kr.LkError):
        kr.apply_kit(st, pl)


def _verilator():
    for c in (os.environ.get("OT_BIND_VERILATOR"), str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"),
              shutil.which("verilator")):
        if c and Path(c).is_file():
            return c
    return None


TB = """
module tb;
    reg clk = 0;
    reg [31:0] cyc = 0;
    reg [%(NB)d:0] x;
    reg [63:0] y;
    wire [%(NB)d:0] a0, a1, b0, b1;
    wire [63:0] c0, c1;
    wire [7:0] d0, d1, e0, e1;
    wire f0, f1;
    integer k, bad = 0;
    always #1 clk = ~clk;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        for (k = 0; k <= %(NB)d; k = k + 1) x[k] <= $urandom;
        y <= {$urandom, $urandom};
    end
    top_bound g (.clk(clk), .i_x_q(x), .i_y_q(y), .y_a(a0), .y_b(b0), .y_c(c0), .y_d(d0), .y_e(e0), .y_f(f0));
    top_bound_ram r (.clk(clk), .i_x_q(x), .i_y_q(y), .y_a(a1), .y_b(b1), .y_c(c1), .y_d(d1), .y_e(e1), .y_f(f1));
    always @(negedge clk) if (cyc > 60 && {a0, b0, c0, d0, e0, f0} !== {a1, b1, c1, d1, e1, f1}) bad = bad + 1;
    initial begin
        #2000;
        $display("KDR_SIM bad=%%0d", bad);
        $finish;
    end
endmodule
"""


@pytest.mark.skipif(_verilator() is None, reason="no verilator")
def test_rewrite_is_cycle_exact_and_lockup_composes(tmp_path):
    txt = bound_text()
    chunks, _st, cand = kr.plan(txt, TYPE, PINS, kr.cfg_of(TYPE))
    new = kr.rewrite(txt, chunks, cand)
    assert new.count("ot_dp_dly_ram #(") == 3
    # every candidate q wire keeps exactly one driver
    for n, x in cand.items():
        drivers = len(re.findall(r"\.q\(\{?[^;]*\b%s\b" % re.escape(x["q"]), new))
        assert drivers == 1, (n, drivers)
    # the lockup post-pass (runs after this pass at GEN) accepts the result and keeps every depth
    lk, _lat, stats = dl.apply(new, seg=8, core_types={"core"})
    assert stats["selected"] > 0
    for name, body in (("ram", new), ("lk", lk)):
        rtl = tmp_path / f"{name}.sv"
        rtl.write_text(CELLS + txt + body.replace("module top_bound (", "module top_bound_ram (", 1)
                       .replace("module ot_dp_lk", "module ot_dp_lk_unused"))
        tb = tmp_path / "tb.sv"
        tb.write_text(TB % dict(NB=NB - 1))
        lkcell = tmp_path / "lk.v"
        lkcell.write_text("module ot_dp_lk #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);\n"
                          "    assign q = d;  // LEC latch_to_wire view: 0 cycles\nendmodule\n")
        o = tmp_path / f"o_{name}"
        r = subprocess.run([_verilator(), "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb",
                            str(HERE / "ot_dp_dly_ram.sv"),
                            str(ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"),
                            str(lkcell), str(rtl), str(tb), "-Mdir", str(o), "-o", "tb"], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
        s = subprocess.run([str(o / "tb")], capture_output=True, text=True)
        assert "KDR_SIM bad=0" in s.stdout, (name, s.stdout[-2000:])
