#!/usr/bin/env python3
"""Emit the 1.2 GHz successor of the Qwen stream unit (HBM accelerator fmax closure, 2026-10-04; default off).

The vehicle's stream unit is ot_hdc_vstream_rt (tools/qwen_rom_rt_core_emit_w12.py emit_vstream of
rtl/hdc/ot_hdc_vstream.sv).  Its binary32 adder and multiplier are the LATENCY-3 fast units
(ot_hdc_qadd / ot_hdc_qmul, rtl/hdc/ot_hdc_fastfp.sv), which miss 0.833 ns at SS.  This emitter writes the same
unit with EVERY fast unit replaced by the qualified pipelined units (ot_hdc_fp32_add_lat #(LA),
ot_hdc_fp32_mul_lat #(LM): the same arithmetic bit for bit, more register stages) and every companion delay line,
tap and Newton/Horner schedule re-derived from LA / LM (the pinned sources already express them in LA / LM; only
their localparams are frozen at 3):

  ot_hdc_qadd_f12 / ot_hdc_qmul_f12 #(LAT)        the fault-reporting wrappers (as ot_hdc_qadd / ot_hdc_qmul)
  ot_hdc_exp_q_f12 / recip_q_f12 / rsqrt_q_f12   rtl/hdc/ot_hdc_sfu_q.sv with parameters LA, LM
  ot_hdc_vred_op_f12 / ot_hdc_vreduce_f12        rtl/hdc/ot_hdc_vreduce.sv with parameters LA, LM
  ot_hdc_vstream_lane_f12                        rtl/hdc/ot_hdc_vstream_lane.sv with parameters LA, LM
                                                 (SFU depths derived: D_EXP, D_RECIP, D_RSQRT)
  ot_hdc_vstream_rt_f12 (or --top-name)          emit_vstream(rtl/hdc/ot_hdc_vstream.sv) on the successors

LA = 3, LM = 3 with the fast units reproduces the pinned unit exactly (the generator is checked against that).
Outputs: rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_f12.sv (units, SFUs, reducer, lane) and
rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_rt_f12.sv (the unit).  The vehicle substitutes the unit by writing
emit_rt(top_name="ot_hdc_vstream_rt") into its gen/ot_hdc_vstream_rt.sv and adding the units file plus
rtl/hdc/ot_hdc_fp32_add_lat.sv, rtl/hdc/ot_hdc_fp32_mul_lat.sv, rtl/hdc/ot_hdc_prefix.sv.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "rtl/hdc/ot_hdc_vstream_lane.sv"
SFUQ = ROOT / "rtl/hdc/ot_hdc_sfu_q.sv"
VRED = ROOT / "rtl/hdc/ot_hdc_vreduce.sv"
VSTREAM = ROOT / "rtl/hdc/ot_hdc_vstream.sv"
OUT = ROOT / "rtl/hbm_accel/qwen/fmax"
DEF_LA, DEF_LM = 5, 6

UNITS = f"""
// Fault-reporting binary32 units at a parameter latency: ot_hdc_qadd / ot_hdc_qmul (LAT 3, the fast units) or the
// qualified pipelined units ot_hdc_fp32_add_lat #(LAT) / ot_hdc_fp32_mul_lat #(LAT) (bit-identical, keep-prefix).
module ot_hdc_qadd_f12 #(parameter integer LAT = {DEF_LA}) (
    input  wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
    output wire [31:0] y, output wire fault
);
    wire [1:0] err;
    wire vo;
    generate if (LAT == 3) begin : g_fast
        ot_hdc_fp32_add_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_lat
        ot_hdc_fp32_add_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_qmul_f12 #(parameter integer LAT = {DEF_LM}) (
    input  wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
    output wire [31:0] y, output wire fault
);
    wire [1:0] err;
    wire vo;
    generate if (LAT == 3) begin : g_fast
        ot_hdc_fp32_mul_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_lat
        ot_hdc_fp32_mul_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule
"""


HIER_TOP = """
// Hierarchical route top: the Qwen SU shape (SW 64, LV 7, WR 16, AW 24, NW 18, KV_FP8 1, LA 5, LM 6), fixed
// parameters (yosys 0.68 asserts when a parameterised reducer parent is the top of a hierarchy pass).
module ot_hdc_vstream_rt_f12_hw (
    output wire rt_active, output wire [7:0] rt_inflight,
    input wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input wire [17:0] i_nout, i_nin,
    input wire i_asrc, input wire [23:0] i_abase, i_aso, i_asi,
    input wire i_bsrc, input wire [23:0] i_bbase, i_bso, i_bsi,
    input wire i_csrc, input wire [23:0] i_cbase, i_cso, i_csi,
    input wire [1:0] i_ma, i_mb, input wire [2:0] i_ad, i_sfu, input wire i_mc, i_md,
    input wire [1:0] i_dst, input wire [23:0] i_dbase, i_dso, i_dsi,
    input wire [1:0] i_red, input wire i_redsq, input wire [23:0] i_rbase, i_rso, input wire [31:0] i_imm1, i_imm2,
    output wire [63:0] va_re, output wire [64*24-1:0] va_addr, input wire [64*32-1:0] va_q,
    output wire [63:0] vb_re, output wire [64*24-1:0] vb_addr, input wire [64*32-1:0] vb_q,
    output wire [63:0] vc_re, output wire [64*24-1:0] vc_addr, input wire [64*32-1:0] vc_q,
    output wire wrom_re, output wire [23:0] wrom_addr, input wire [255:0] wrom_q,
    output wire [63:0] crom_re, output wire [64*24-1:0] crom_addr, input wire [64*64-1:0] crom_q,
    output wire [63:0] vm_we, output wire [64*24-1:0] vm_waddr, output wire [64*32-1:0] vm_wdata,
    output wire [63:0] kv_we, output wire [64*24-1:0] kv_waddr, output wire [64*32-1:0] kv_wdata,
    output wire red_we, output wire [23:0] red_addr, output wire [31:0] red_data,
    output wire [15:0] progress, progress_rows, output wire fault
);
    ot_hdc_vstream_rt_f12_h #(.SW(64), .LV(7), .WR(16), .AW(24), .NW(18), .KV_FP8(1)) u (.*);
endmodule
"""


def sub1(pattern: str, repl: str, s: str, flags=0, count=1) -> str:
    out, n = re.subn(pattern, repl, s, flags=flags)
    if n != count:
        raise SystemExit(f"anchor {pattern!r}: {n} matches, expected {count}")
    return out


def units_calls(t: str) -> str:
    """ot_hdc_qadd x (...) -> ot_hdc_qadd_f12 #(.LAT(LA)) x (...), same for qmul."""
    t = re.sub(r"\bot_hdc_qadd (\w+)(\s+)\(", r"ot_hdc_qadd_f12 #(.LAT(LA)) \1\2(", t)
    t = re.sub(r"\bot_hdc_qmul (\w+)(\s+)\(", r"ot_hdc_qmul_f12 #(.LAT(LM)) \1\2(", t)
    if re.search(r"\bot_hdc_q(add|mul)\s+\w+\s*\(", t):
        raise SystemExit("a fast unit instance survived")
    return t


def lat_params(t: str, module: str, la: int, lm: int) -> str:
    """the module's frozen `localparam integer LA = 3, LM = 3;` -> parameters LA, LM"""
    i = t.index(f"module {module}")
    j = t.index("endmodule", i)
    body = t[i:j]
    body = sub1(r"\n\s*localparam integer LA = 3, LM = 3;[^\n]*", "", body)
    if f"module {module} #(" in body:
        body = body.replace(f"module {module} #(", f"module {module}_f12 #(\n    parameter integer LA = {la},\n"
                            f"    parameter integer LM = {lm},", 1)
    else:
        body = sub1(rf"module {module} \(", f"module {module}_f12 #(\n    parameter integer LA = {la},\n"
                    f"    parameter integer LM = {lm}\n) (", body)
    return t[:i] + body + t[j:]


def emit_units(la: int = DEF_LA, lm: int = DEF_LM) -> str:
    # SFUs
    s = SFUQ.read_text()
    for m in ("ot_hdc_exp_q", "ot_hdc_recip_q", "ot_hdc_rsqrt_q"):
        s = lat_params(s, m, la, lm)
    s = sub1(r"localparam integer DEPTH = T_P \+ 1;\s*// 49", "localparam integer DEPTH = T_P + 1;         // 49 at LA = LM = 3", s)
    s = units_calls(s)
    # reducer
    r = VRED.read_text()
    r = sub1(r"module ot_hdc_vred_op #\(\n    parameter integer LA = 3\n\)", "module ot_hdc_vred_op_f12 #(\n    parameter integer LA = 3\n)", r)
    r = lat_params(r, "ot_hdc_vreduce", la, lm)
    r = r.replace("ot_hdc_vred_op #(.LA(LA))", "ot_hdc_vred_op_f12 #(.LA(LA))")
    r = units_calls(r)
    # the vred op's add takes the reducer's LA (its own parameter LA is passed down)
    # lane
    ln = LANE.read_text()
    ln = lat_params(ln, "ot_hdc_vstream_lane", la, lm)
    # The FP8 KV rounding (fp8r) shifted the subnormal significand by a VARIABLE 14 - e; e < -6 and 14 - e < 26 leave
    # only e in [-11, -7], so the successor branches on the exponent field with five CONSTANT shifts (fp8r_sub):
    # the same value for every input (rtl/test/hbm_accel_qwen/fmax/tb_fp8r_equiv.sv, every subnormal-branch input).
    ln = sub1(r"""                sig = \{2'b01, mt\};
                if \(14 - e >= 26\) y = 32'd0;
                else begin
                    sh = 14 - e;
                    n = sig >> sh; rem = sig & \(\(25'd1 << sh\) - 1\); half = 25'd1 << \(sh - 1\);
                    if \(rem > half \|\| \(rem == half && n\[0\]\)\) n = n \+ 1;""",
              """                sig = {2'b01, mt};
                if (ex < 8'd116) y = 32'd0;
                else begin
                    case (ex)
                        8'd116:  n = fp8r_sub(sig, 25);
                        8'd117:  n = fp8r_sub(sig, 24);
                        8'd118:  n = fp8r_sub(sig, 23);
                        8'd119:  n = fp8r_sub(sig, 22);
                        default: n = fp8r_sub(sig, 21);
                    endcase""", ln)
    ln = sub1(r"    function automatic \[31:0\] fp8r\(input \[31:0\] v\);",
              """    function automatic [24:0] fp8r_sub(input [24:0] sig, input integer sh);   // round(sig / 2^sh), half to even
        reg [24:0] n, rem, half;
        begin
            n = sig >> sh; rem = sig & ((25'd1 << sh) - 1); half = 25'd1 << (sh - 1);
            if (rem > half || (rem == half && n[0])) n = n + 1;
            fp8r_sub = n;
        end
    endfunction
    function automatic [31:0] fp8r(input [31:0] v);""", ln)
    # The embedding element select wrom_q[16 * t_lane +: 16] decoded the binary lane index after s1 (a 16:1 select
    # behind a 16-way decode fanout).  The successor carries the index ONE-HOT from the address cycle (s1_loh, the
    # same cycle as s1_tag) and selects by AND-OR: the same element, no added cycle.
    ln = sub1(r"(    reg \[LW-1:0\] e_lane;)", r"\1\n    reg [WR-1:0] e_loh, s1_loh;      // e_lane / t_lane one-hot", ln)
    ln = sub1(r"(e_lane <= cura\[LW-1:0\];)", r"\1 e_loh <= {{(WR-1){1'b0}}, 1'b1} << cura[LW-1:0];", ln)
    ln = sub1(r"(    always @\(posedge clk\) s1_tag <= e_tag;)", r"\1\n    always @(posedge clk) s1_loh <= e_loh;\n"
              r"    reg [15:0] s1_wsel;\n    integer wk;\n"
              r"    always @(*) begin s1_wsel = 16'd0; for (wk = 0; wk < WR; wk = wk + 1) s1_wsel = s1_wsel | (wrom_q[16*wk +: 16] & {16{s1_loh[wk]}}); end", ln)
    ln = sub1(r"s2_a <= t_asrc \? \{wrom_q\[16\*t_lane \+: 16\], 16'h0000\} : va_q;", "s2_a <= t_asrc ? {s1_wsel, 16'h0000} : va_q;", ln)
    # The final select bit o_md fanned out to the vector-memory, KV and reducer outputs (96 loads, the lane output
    # ports -150 ps): the reducer output gets its own (* keep *) copy of the bit's delay line.  No added cycle.
    ln = sub1(r"(    wire \[31:0\] out = o_md \? md_out : dbyp5;)",
              r"\1\n    (* keep *) reg [LM-1:0] md2_line;            // o_md replica for the reducer output\n"
              r"    always @(posedge clk) md2_line <= {md2_line[LM-2:0], md_tail[TT-2]};\n"
              r"    wire [31:0] out_red = md2_line[LM-1] ? md_out : dbyp5;", ln)
    ln = sub1(r"    assign l_out = out;", "    assign l_out = out_red;", ln)
    ln = sub1(r"localparam integer D_EXP = 49, D_RECIP = 28, D_RSQRT = 37;[^\n]*",
              "//: SFU depths of ot_hdc_exp_q_f12 / recip_q_f12 / rsqrt_q_f12 (49 / 28 / 37 at LA = LM = 3)\n"
              "    localparam integer D_EXP = (LM + 3 + 2 * LA + 6 * (LM + LA)) + 1, D_RECIP = 1 + 3 * (2 * LM + LA),\n"
              "                       D_RSQRT = 1 + 3 * (3 * LM + LA);", ln)
    for m in ("exp_q", "recip_q", "rsqrt_q"):
        ln = sub1(rf"\bot_hdc_{m} u_", f"ot_hdc_{m}_f12 #(.LA(LA), .LM(LM)) u_", ln)
    ln = units_calls(ln)
    head = ("// GENERATED by tools/qwen_hbmacc_vstream_f12_emit.py (LA = %d, LM = %d defaults) from "
            "rtl/hdc/ot_hdc_sfu_q.sv (sha256 %s), rtl/hdc/ot_hdc_vreduce.sv (sha256 %s) and "
            "rtl/hdc/ot_hdc_vstream_lane.sv (sha256 %s).\n// Needs rtl/hdc/ot_hdc_fastfp.sv, ot_hdc_fp32_add_lat.sv, "
            "ot_hdc_fp32_mul_lat.sv, ot_hdc_prefix.sv, ot_hdc_delay.sv, ot_hdc_sfu.sv (ot_hdc_vline).\n"
            % (la, lm, *(hashlib.sha256(p.read_bytes()).hexdigest() for p in (SFUQ, VRED, LANE))))
    return head + UNITS + "\n" + s + "\n" + r + "\n" + ln


def emit_rt(top_name: str = "ot_hdc_vstream_rt_f12", la: int = DEF_LA, lm: int = DEF_LM, macro_lane: bool = False) -> str:
    """macro_lane: every lane is the parameter-free hardened macro ot_hdc_vstream_lane_f12_m (LA 5, LM 6, WR 16,
    AW 24, NW 18, KV_FP8 1; rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_lane_f12_m.sv) -- the hierarchical route top"""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import qwen_rom_rt_core_emit_w12 as E
    t = E.emit_vstream(VSTREAM.read_text())
    t = sub1(r"module ot_hdc_vstream_rt #\(", f"module {top_name} #(\n    parameter integer LA = {la},\n"
             f"    parameter integer LM = {lm},", t)
    if macro_lane:
        t = sub1(r"ot_hdc_vstream_lane #\(\.WR\(WR\), \.AW\(AW\), \.NW\(NW\), \.LANE\(0\), \.KV_FP8\(KV_FP8\)\) u_lane",
                 "ot_hdc_vstream_lane_f12_m u_lane", t)
    else:
        t = sub1(r"ot_hdc_vstream_lane #\(\.WR\(WR\),", "ot_hdc_vstream_lane_f12 #(.LA(LA), .LM(LM), .WR(WR),", t)
    t = sub1(r"ot_hdc_vreduce #\(\.SW\(SW\),", "ot_hdc_vreduce_f12 #(.LA(LA), .LM(LM), .SW(SW),", t)
    return "// GENERATED by tools/qwen_hbmacc_vstream_f12_emit.py: the emit_vstream unit on the f12 successors.\n" + t


def vehicle(la: int = DEF_LA, lm: int = DEF_LM):
    """HA8 vehicle substitution (tools/qwen_hbmacc_rt_token_w12_f12.py --vs-f12): (rt_text, unit_paths, hier_names).
    rt_text replaces the vehicle's gen/ot_hdc_vstream_rt.sv (module ot_hdc_vstream_rt, the emit_vstream ports incl.
    rt_active / rt_inflight; LA / LM fixed as its parameter defaults); unit_paths are the extra sources (the units
    file written for (la, lm) under rtl/hbm_accel/qwen/fmax/ and the pipelined FP units); hier_names are the
    parameter-identical Verilator hier blocks (the lane and its FP units)."""
    units = OUT / ("ot_hdc_vstream_f12.sv" if (la, lm) == (DEF_LA, DEF_LM) else f"ot_hdc_vstream_f12_la{la}lm{lm}.sv")
    text = emit_units(la, lm)
    if not units.exists() or units.read_text() != text:
        units.write_text(text)
    paths = [units] + [ROOT / f"rtl/hdc/{n}.sv" for n in
                       ("ot_hdc_fp32_add_lat", "ot_hdc_fp32_mul_lat", "ot_hdc_prefix", "ot_hdc_fastfp", "ot_hdc_delay")]
    return emit_rt("ot_hdc_vstream_rt", la, lm), paths, ("ot_hdc_vstream_lane_f12", "ot_hdc_qadd_f12", "ot_hdc_qmul_f12")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "ot_hdc_vstream_f12.sv").write_text(emit_units())
    (a.out / "ot_hdc_vstream_rt_f12.sv").write_text(emit_rt())
    (a.out / "ot_hdc_vstream_rt_f12_h.sv").write_text(emit_rt("ot_hdc_vstream_rt_f12_h", macro_lane=True) + HIER_TOP)
    print(a.out)


if __name__ == "__main__":
    main()
