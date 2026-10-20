#!/usr/bin/env python3
"""OWN-QWEN/SLICE-E 10-18 (landed-regions-standard-1018): re-cut qfd_dv_slice2 (SU_LT 1, HD_W130 1) as a WIRES-ONLY flat
parent of the E master, qfd_dv_slice2_e_lpf, so tools/landed_parent/lp.py can build the landed slice parent.

Pure re-partition: every register / edge is the one of qfd_dv_slice2_e(SU_LT 1, HD_W130 1); tb_qfd_dv_slice2_e_lpf proves
the two cycle-exact on every output (lockstep, random stimulus; mutants FAIL).  Children (regions in
tools/landed_parent/specs/qfd_dv_slice2_e_lpf.json):
  u_c    qfd_dv_slice2_lpc  core: pin registers, SETID / decode, SU (8 lane tiles), VM (22 SRAM), station, scalar, stream,
                            LM-head argmax, gather, outbound chain, status NEXT values (st_n / ag_n, without the heads fault)
  u_s    qfd_dv_slice2_lps  status registers st / ag_dn_o (= st_n / ag_n | the heads fault)   [core region]
  u_hd   qfd_dv_slice2_lph  the heads (qfd_dv_heads_w130: 4 column heads + 32 x leaves)        [hd region]
  u_t*   qfd_dv_slice2_e_t* wires only: they put every face output in its face region (the landing read is the flop at the pin)
Every part keeps the core's 2-stage reset synchroniser (rs1 / rst), so the re-cut releases every register on the same edge.

    python3 tools/qwen_dv/gen_slice2_lpf.py      (writes rtl/qwen_dv/qfd_dv_slice2_lpf_parts.sv, rtl/qwen_dv/qfd_dv_slice2_e_lpf.sv)
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "rtl/qwen_dv/qfd_dv_slice2.sv"


def sub1(t, a, b):
    n = t.count(a)
    if n != 1:
        raise SystemExit(f"pattern found {n} times: {a[:80]!r}")
    return t.replace(a, b)


def core():
    t = SRC.read_text()
    body = t[t.index("module qfd_dv_slice2 #("):]
    body = sub1(body, "module qfd_dv_slice2 #(", "module qfd_dv_slice2_lpc #(")
    body = sub1(body, "    input  wire [1027:0]  rs_s,\n    input  wire [1027:0]  rs_n,\n",
                "    input  wire [513:0]   rs_s0, rs_s1,\n    input  wire [513:0]   rs_n0, rs_n1,\n")
    body = sub1(body, "    output wire [515:0]   cw_n0, cw_n1, cw_n2, cw_n3,\n    output wire [515:0]   cw_s0, cw_s1, cw_s2, cw_s3,\n",
                "    // the heads' inputs (u_hd, hd region)\n"
                "    output wire [3:0]     hd_sid,\n    output wire [71:0]    hd_xpf,\n    output wire [379:0]   hd_gi,\n"
                "    output wire           hd_sw_v,\n    output wire [23:0]    hd_sw_a,\n    output wire [64*32-1:0] hd_sw_d,\n"
                "    output wire           hd_fe,\n")
    body = sub1(body, "    output reg  [106:0]   st,           // status {ar_land, tok_val 32, sid 4, (qfd_dv_slice st)}: to tt_ctlm\n",
                "    output wire [106:0]   st_n,         // NEXT status (u_s registers it with the heads fault): to tt_ctlm\n")
    body = sub1(body, "    output reg  [9:0]     ag_dn_o\n", "    output wire [9:0]     ag_n          // NEXT ag_dn_o (u_s)\n")
    body = sub1(body, "    reg rs1, rst;\n", "    wire [1027:0] rs_s = {rs_s1, rs_s0}, rs_n = {rs_n1, rs_n0};\n    reg rs1, rst;\n")
    a = body.index("    wire hd_fault;\n")
    b = body.index("    end endgenerate\n", a) + len("    end endgenerate\n")
    body = body[:a] + (
        "    // the heads live in u_hd (hd region): their inputs leave here, their fault joins the status in u_s\n"
        "    wire hd_fault = 1'b0;\n"
        "    wire hv = hr_q[0];\n"
        "    assign hd_sid = sid_q;\n"
        "    assign hd_xpf = {hr_q[72:2], hr_q[1] & hv};\n"
        "    assign hd_gi = {hr_q[451:73], hr_q[452] & hv};\n"
        "    assign hd_sw_v = xt_v;\n    assign hd_sw_a = xt_a;\n    assign hd_sw_d = xt_f;\n    assign hd_fe = xt_bad;\n") + body[b:]
    a = body.index("    always @(posedge ck or negedge rst)\n        if (!rst) st <= 107'd0;\n")
    b = body.index("(107'(sid_q) << 70);\n", a) + len("(107'(sid_q) << 70);\n")
    blk = body[a:b]
    blk = blk.replace("    always @(posedge ck or negedge rst)\n        if (!rst) st <= 107'd0;\n        else st <= ",
                      "    assign st_n = ")
    body = body[:a] + blk + body[b:]
    a = body.index("    always @(posedge ck or negedge rst)\n        if (!rst) ag_dn_o <= 10'd0;\n")
    body = sub1(body, "    always @(posedge ck or negedge rst)\n        if (!rst) ag_dn_o <= 10'd0;\n        else ag_dn_o <= agu_q | ",
                "    assign ag_n = agu_q | ")
    body = sub1(body, "    initial if (MUT < 0 || (MUT > 12 && MUT != 14 && MUT != 15)) $fatal(1, \"qfd_dv_slice2: MUT %0d undefined\", MUT);  // 14 = redstn2 kcm1 ignored, 15 = kcm1 at [58:51]",
                "    initial if (MUT < 0 || (MUT > 12 && MUT != 14 && MUT != 15)) $fatal(1, \"qfd_dv_slice2_lpc: MUT %0d undefined\", MUT);\n"
                "    initial if (HD_W130 != 1) $fatal(1, \"qfd_dv_slice2_lpc: the landed re-cut is the HD_W130 = 1 slice\");")
    return body


PARTS_TAIL = r"""
// ---------------------------------------------------------------------------------------------------- u_s: status
module qfd_dv_slice2_lps (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [106:0]  st_n,
    input  wire [9:0]    ag_n,
    input  wire          hd_fault,
    output reg  [106:0]  st,
    output reg  [9:0]    ag_dn_o
);
    reg rs1, rst;                                // the core's regional reset synchroniser (same release edge)
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rst <= 1'b0; end
        else begin rs1 <= 1'b1; rst <= rs1; end
    // the heads fault enters any_fault: st[69] and ag_dn_o[8] (OR, as qfd_dv_slice2)
    always @(posedge ck or negedge rst)
        if (!rst) begin st <= 107'd0; ag_dn_o <= 10'd0; end
        else begin
`ifdef OT_LPF_MUT1
            st <= st_n;                          // MUT 1 (bench only): the heads fault is lost
            ag_dn_o <= ag_n;
`elsif OT_LPF_MUT3
            st <= st_n | {37'd0, hd_fault, 69'd0};
            ag_dn_o <= {ag_n[9:2], ag_n[0], ag_n[1]} | {1'b0, hd_fault, 8'd0};   // MUT 3: two ag bits swapped
`else
            st <= st_n | {37'd0, hd_fault, 69'd0};
            ag_dn_o <= ag_n | {1'b0, hd_fault, 8'd0};
`endif
        end
endmodule

// ---------------------------------------------------------------------------------------------------- u_hd: heads
module qfd_dv_slice2_lph #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    input  wire [71:0]   xpf,
    input  wire [379:0]  gi,
    input  wire          sw_v,
    input  wire [23:0]   sw_a,
    input  wire [64*32-1:0] sw_d,
    input  wire          fe_i,
    output wire [515:0]  cw_n0, cw_n1, cw_n2, cw_n3,
    output wire [515:0]  cw_s0, cw_s1, cw_s2, cw_s3,
    output wire          fault
);
    reg rs1, rst;                                // the core's regional reset synchroniser (same release edge)
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rst <= 1'b0; end
        else begin rs1 <= 1'b1; rst <= rs1; end
    wire [4*516-1:0] n_d, s_d;
`ifdef OT_LPF_MUT2
    assign {cw_n3, cw_n1, cw_n2, cw_n0} = n_d;   // MUT 2 (bench only): corridor words of column heads 1 / 2 swapped
`else
    assign {cw_n3, cw_n2, cw_n1, cw_n0} = n_d;
`endif
    assign {cw_s3, cw_s2, cw_s1, cw_s0} = s_d;
`ifdef OT_DV_SLICE_HARD
    qfd_dv_heads_w130 u_hd (.ck(ck), .rst_n(rst), .sid(sid),
`else
    qfd_dv_heads_w130 #(.HEAD_MUT((MUT == 8) ? 3 : 0)) u_hd (.ck(ck), .rst_n(rst), .sid(sid),
`endif
        .xpf(xpf), .gi(gi), .sw_v(sw_v), .sw_a(sw_a), .sw_d(sw_d), .fe_i(fe_i), .n_d(n_d), .s_d(s_d), .fault(fault));
endmodule
"""

THRU = {   # module: (comment, [(in name, width, [(out name, msb, lsb)])])
    "qfd_dv_slice2_e_te": ("E face (master E = the dn face)", [
        ("st_dn_o", 1088, [("st_eo", 1087, 0)]), ("sc_dn_o", 48, [("sc_eo", 47, 0)]),
        ("ch_dn_o", 1095, [("arv_eo", 1094, 1094), ("art_eo", 1093, 1062), ("arm_eo", 1061, 1061), ("arl_eo", 1060, 1060),
                           ("ard_eo", 1059, 548), ("dd_eo", 547, 0)]),
        ("cc_o", 50, [("ccv_eo", 49, 49), ("ccm_eo", 48, 48), ("ccw_eo", 47, 32), ("cct_eo", 31, 0)]),
        ("l9_o", 514, [("l9_eo", 513, 0)])]),
    "qfd_dv_slice2_e_tes": ("E face status outputs (own node: they follow the heads fault, the chains do not wait for it)", [
        ("ag_dn_o", 10, [("ag_eo", 9, 0)]), ("st", 107, [("ss_eo", 106, 0)])]),
    "qfd_dv_slice2_e_tw": ("W face (the up face)", [
        ("cmd_o", 116, [("cmd_wo", 115, 0)]), ("hr_o", 453, [("hr_wo", 452, 0)]), ("st_up_o", 1088, [("st_wo", 1087, 0)]),
        ("sc_up_o", 48, [("sc_wo", 47, 0)]),
        ("ch_up_o", 1038, [("rv_wo", 1037, 1037), ("re_wo", 1036, 1036), ("rr_wo", 1035, 1033), ("rl_wo", 1032, 1032),
                           ("rd_wo", 1031, 520), ("dr_wo", 519, 0)])]),
}
for f in ("n", "s"):
    THRU[f"qfd_dv_slice2_e_t{f}w"] = (f"{f.upper()} face, W pin group (cw_{f}0)", [(f"cw_{f}0_i", 516, [(f"cw_{f}0", 515, 0)])])
    THRU[f"qfd_dv_slice2_e_t{f}c"] = (f"{f.upper()} face, centre pin groups (cw_{f}1, cw_{f}2)",
                                      [(f"cw_{f}1_i", 516, [(f"cw_{f}1", 515, 0)]), (f"cw_{f}2_i", 516, [(f"cw_{f}2", 515, 0)])])
    THRU[f"qfd_dv_slice2_e_t{f}e"] = (f"{f.upper()} face, E pin group (cw_{f}3)", [(f"cw_{f}3_i", 516, [(f"cw_{f}3", 515, 0)])])


def thru_modules():
    o = []
    for m, (c, ios) in THRU.items():
        ports = ["    input  wire          ck,                       // region membership only (no state)",
                 "    input  wire          rst_n"]
        asg = []
        for i, w, outs in ios:
            ports.append(f"    input  wire [{w - 1}:0] {i}")
            for on, a, b in outs:
                ports.append(f"    output wire [{a - b}:0] {on}" if a != b else f"    output wire {on}")
                asg.append(f"    assign {on} = {i}[{a}:{b}];" if a != b else f"    assign {on} = {i}[{a}];")
        o.append(f"\n// ---------------------------------------------------------------------------------------------------- {m}: {c}\n"
                 f"module {m} (\n" + ",\n".join(ports) + "\n);\n" + "\n".join(asg) + "\nendmodule\n")
    return "".join(o)


def faces_ports():
    t = (ROOT / "rtl/qwen_dv/qfd_dv_slice2_faces.sv").read_text()
    m = t[t.index("module qfd_dv_slice2_e #("):]
    hdr = m[m.index(") (\n") + 4:m.index("\n);\n")]
    return hdr


def top():
    ports = faces_ports()
    o = ["`timescale 1ns/1ps",
         "// =====================================================================================================================",
         "// qfd_dv_slice2_e_lpf -- GENERATED by tools/qwen_dv/gen_slice2_lpf.py (OWN-QWEN/SLICE-E 10-18).  The E master",
         "// qfd_dv_slice2_e (SU_LT 1, HD_W130 1) re-cut as a WIRES-ONLY flat parent for tools/landed_parent/lp.py",
         "// (spec tools/landed_parent/specs/qfd_dv_slice2_e_lpf.json).  Same port list as qfd_dv_slice2_e; cycle-exact to it",
         "// (tb rtl/test/qwen_dv/tb_qfd_dv_slice2_e_lpf.sv).  Face outputs pass wires-only children in their face regions.",
         "// =====================================================================================================================",
         "module qfd_dv_slice2_e_lpf #(parameter integer SL_MUT = 0, parameter integer SU_TLS = 1, parameter integer SU_LT = 1,",
         "                            parameter integer MU_NU = 4) (   // MU-QWEN R4: the 4-user LM-head argmax (MU-ADOPT-SLICE)",
         ports, ");"]
    w = o.append
    w("    wire [1094:0] w_ch_up_i = {arv_wi, art_wi, arm_wi, arl_wi, ard_wi, dd_wi};")
    w("    wire [1037:0] w_ch_dn_i = {rv_ei, re_ei, rr_ei, rl_ei, rd_ei, dr_ei};")
    w("    wire [115:0]  c_cmd_o;\n    wire [452:0]  c_hr_o;\n    wire [513:0]  c_l9_o;\n"
      "    wire [1087:0] c_st_up_o, c_st_dn_o;\n    wire [47:0]   c_sc_up_o, c_sc_dn_o;\n"
      "    wire [1094:0] c_ch_dn_o;\n    wire [1037:0] c_ch_up_o;\n    wire [49:0]   c_cc_o;\n"
      "    wire [106:0]  c_st_n, s_st;\n    wire [9:0]    c_ag_n, s_ag;\n"
      "    wire [3:0]    h_sid;\n    wire [71:0]   h_xpf;\n    wire [379:0]  h_gi;\n    wire          h_sw_v, h_fe, h_fault;\n"
      "    wire [23:0]   h_sw_a;\n    wire [64*32-1:0] h_sw_d;\n"
      "    wire [515:0]  h_n0, h_n1, h_n2, h_n3, h_s0, h_s1, h_s2, h_s3;")
    w("    qfd_dv_slice2_lpc #(.MUT(SL_MUT), .SU_TLS(SU_TLS), .SU_LT(SU_LT), .HD_W130(1), .MU_NU(MU_NU), .DIR(1)) u_c (.ck(ck), .rst_n(rst_n),\n"
      "        .cmd_i(cmd_ei), .cmd_o(c_cmd_o), .hr_i(hr_ei), .hr_o(c_hr_o),\n"
      "        .rs_s0(rs_s0), .rs_s1(rs_s1), .rs_n0(rs_n0), .rs_n1(rs_n1), .l9_i(l9_wi), .l9_o(c_l9_o),\n"
      "        .st_up_i(st_ei), .st_up_o(c_st_up_o), .st_dn_i(st_wi), .st_dn_o(c_st_dn_o),\n"
      "        .sc_up_i(sc_ei), .sc_up_o(c_sc_up_o), .sc_dn_i(sc_wi), .sc_dn_o(c_sc_dn_o),\n"
      "        .ch_up_i(w_ch_up_i), .ch_dn_o(c_ch_dn_o), .ch_dn_i(w_ch_dn_i), .ch_up_o(c_ch_up_o),\n"
      "        .hd_sid(h_sid), .hd_xpf(h_xpf), .hd_gi(h_gi), .hd_sw_v(h_sw_v), .hd_sw_a(h_sw_a), .hd_sw_d(h_sw_d), .hd_fe(h_fe),\n"
      "        .st_n(c_st_n), .cc_o(c_cc_o), .ag_up_i(ag_wi), .ag_n(c_ag_n));")
    w("    qfd_dv_slice2_lps u_s (.ck(ck), .rst_n(rst_n), .st_n(c_st_n), .ag_n(c_ag_n), .hd_fault(h_fault), .st(s_st), .ag_dn_o(s_ag));")
    w("    qfd_dv_slice2_lph #(.MUT(SL_MUT)) u_hd (.ck(ck), .rst_n(rst_n), .sid(h_sid), .xpf(h_xpf), .gi(h_gi), .sw_v(h_sw_v),\n"
      "        .sw_a(h_sw_a), .sw_d(h_sw_d), .fe_i(h_fe), .cw_n0(h_n0), .cw_n1(h_n1), .cw_n2(h_n2), .cw_n3(h_n3),\n"
      "        .cw_s0(h_s0), .cw_s1(h_s1), .cw_s2(h_s2), .cw_s3(h_s3), .fault(h_fault));")
    w("    qfd_dv_slice2_e_te u_te (.ck(ck), .rst_n(rst_n), .st_dn_o(c_st_dn_o), .sc_dn_o(c_sc_dn_o), .ch_dn_o(c_ch_dn_o),\n"
      "        .cc_o(c_cc_o), .l9_o(c_l9_o), .st_eo(st_eo), .sc_eo(sc_eo), .arv_eo(arv_eo),\n"
      "        .art_eo(art_eo), .arm_eo(arm_eo), .arl_eo(arl_eo), .ard_eo(ard_eo), .dd_eo(dd_eo),\n"
      "        .ccv_eo(ccv_eo), .ccm_eo(ccm_eo), .ccw_eo(ccw_eo), .cct_eo(cct_eo), .l9_eo(l9_eo));")
    w("    qfd_dv_slice2_e_tes u_tes (.ck(ck), .rst_n(rst_n), .ag_dn_o(s_ag), .st(s_st), .ag_eo(ag_eo), .ss_eo(ss_eo));")
    w("    qfd_dv_slice2_e_tw u_tw (.ck(ck), .rst_n(rst_n), .cmd_o(c_cmd_o), .hr_o(c_hr_o), .st_up_o(c_st_up_o),\n"
      "        .sc_up_o(c_sc_up_o), .ch_up_o(c_ch_up_o), .cmd_wo(cmd_wo), .hr_wo(hr_wo), .st_wo(st_wo), .sc_wo(sc_wo),\n"
      "        .rv_wo(rv_wo), .re_wo(re_wo), .rr_wo(rr_wo), .rl_wo(rl_wo), .rd_wo(rd_wo), .dr_wo(dr_wo));")
    for f in ("n", "s"):
        w(f"    qfd_dv_slice2_e_t{f}w u_t{f}w (.ck(ck), .rst_n(rst_n), .cw_{f}0_i(h_{f}0), .cw_{f}0(cw_{f}0));")
        w(f"    qfd_dv_slice2_e_t{f}c u_t{f}c (.ck(ck), .rst_n(rst_n), .cw_{f}1_i(h_{f}1), .cw_{f}1(cw_{f}1), .cw_{f}2_i(h_{f}2), .cw_{f}2(cw_{f}2));")
        w(f"    qfd_dv_slice2_e_t{f}e u_t{f}e (.ck(ck), .rst_n(rst_n), .cw_{f}3_i(h_{f}3), .cw_{f}3(cw_{f}3));")
    w("endmodule")
    return "\n".join(o) + "\n"


def tb():
    """lockstep qfd_dv_slice2_e (SU_LT 1, HD_W130 1) vs qfd_dv_slice2_e_lpf: random inputs every edge, every output compared
    every cycle after the reset; LPF_EQ PASS / FAIL (mutants: +define+OT_LPF_MUT1/2/3 must FAIL)"""
    ports = []
    for line in faces_ports().splitlines():
        m = re.match(r"\s*(input|output)\s+wire\s*(\[(\d+):0\])?\s*(\w+)", line)
        if m:
            ports.append((m.group(1), int(m.group(3) or 0) + 1, m.group(4)))
    ins = [(w, n) for d, w, n in ports if d == "input" and n not in ("ck", "rst_n")]
    outs = [(w, n) for d, w, n in ports if d == "output"]
    o = ["`timescale 1ns/1ps",
         "// GENERATED by tools/qwen_dv/gen_slice2_lpf.py: lockstep qfd_dv_slice2_e (SU_LT 1, HD_W130 1) vs the wires-only re-cut",
         "// qfd_dv_slice2_e_lpf.  Random words on every input every edge; every output compared every cycle after reset.",
         "module tb_qfd_dv_slice2_e_lpf;",
         "    parameter integer CYC = 3000;",
         "    reg ck = 1'b0;  always #0.5 ck = ~ck;",
         "    reg rst_n = 1'b0;"]
    for w, n in ins:
        o.append(f"    reg [{w - 1}:0] {n};")
    for w, n in outs:
        o.append(f"    wire [{w - 1}:0] a_{n}, b_{n};")
    ca = ", ".join([".ck(ck)", ".rst_n(rst_n)"] + [f".{n}({n})" for _, n in ins] + [f".{n}(a_{n})" for _, n in outs])
    cb = ", ".join([".ck(ck)", ".rst_n(rst_n)"] + [f".{n}({n})" for _, n in ins] + [f".{n}(b_{n})" for _, n in outs])
    o.append(f"    qfd_dv_slice2_e #(.SU_LT(1), .HD_W130(1), .MU_NU(4)) u_ref ({ca});")
    o.append(f"    qfd_dv_slice2_e_lpf #(.SU_LT(1), .MU_NU(4)) u_lpf ({cb});")
    quiet = {"cmd_ei", "rv_ei", "re_ei", "rr_ei", "rl_ei", "rd_ei", "dr_ei", "arv_wi", "art_wi", "arm_wi", "arl_wi", "ard_wi",
             "dd_wi", "ag_wi", "l9_wi", "rs_n0", "rs_n1", "rs_s0", "rs_s1"}
    o.append("    integer pnz [0:%d];" % (len(outs) - 1))
    o += ["    integer cyc, bad, nc, nz, k, nhf, naf; reg quiet, hronly;",
          "    always @(posedge ck) if (rst_n) begin nhf = nhf + (u_ref.u_core.g_hdw.u_hd.fault ? 1 : 0); naf = naf + (u_ref.u_core.any_fault ? 1 : 0); end",
          "    initial begin", "        bad = 0; nc = 0; nz = 0; nhf = 0; naf = 0; quiet = $test$plusargs(\"quiet\"); hronly = $test$plusargs(\"hronly\");",
          f"        for (k = 0; k < {len(outs)}; k = k + 1) pnz[k] = 0;"]
    for w, n in ins:
        o.append(f"        {n} = '0;")
    o += ["        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin", "            @(negedge ck);",
          "            if (cyc == 16) rst_n = 1'b1;"]
    for w, n in ins:
        r = '{' + ','.join(['$urandom'] * ((w + 31) // 32)) + '}'
        if n == "hr_ei":
            o.append(f"            {n} = {r};")
        elif n in quiet:
            o.append(f"            {n} = (quiet || hronly) ? '0 : {r};")
        else:
            o.append(f"            {n} = hronly ? '0 : {r};")
    o.append("            if (cyc > 18) begin")
    for w, n in outs:
        o.append(f"                nc = nc + 1; if (|a_{n}) begin nz = nz + 1; pnz[{outs.index((w, n))}] = pnz[{outs.index((w, n))}] + 1; end if (a_{n} !== b_{n}) begin bad = bad + 1; "
                 f"if (bad <= 8) $display(\"LPF_MISMATCH port={n} cycle=%0d ref=%h lpf=%h\", cyc, a_{n}, b_{n}); end")
    o += ["            end", "        end"]
    o += [f"        $display(\"LPF_NZ {n} %0d\", pnz[{i}]);" for i, (w, n) in enumerate(outs)]
    o += ["        $display(\"LPF_FAULT_CYCLES heads=%0d any=%0d\", nhf, naf);"]
    o += [
          "        if (bad == 0 && nc > 0) $display(\"LPF_EQ PASS quiet=%0d hronly=%0d compared=%0d nonzero=%0d cycles=%0d\", quiet, hronly, nc, nz, CYC);",
          "        else $display(\"LPF_EQ FAIL quiet=%0d hronly=%0d mismatches=%0d of %0d\", quiet, hronly, bad, nc);", "        $finish;", "    end", "endmodule"]
    return "\n".join(o) + "\n"


def main():
    hdr = ("`timescale 1ns/1ps\n// GENERATED by tools/qwen_dv/gen_slice2_lpf.py from rtl/qwen_dv/qfd_dv_slice2.sv -- do not edit.\n"
           "// The children of the wires-only E slice parent qfd_dv_slice2_e_lpf (OWN-QWEN/SLICE-E 10-18, landed-regions-standard).\n"
           "// u_c: qfd_dv_slice2 minus the heads and the two status registers (st / ag_dn_o leave as NEXT values).\n")
    (ROOT / "rtl/qwen_dv/qfd_dv_slice2_lpf_parts.sv").write_text(hdr + core() + "\n" + PARTS_TAIL + thru_modules())
    (ROOT / "rtl/qwen_dv/qfd_dv_slice2_e_lpf.sv").write_text(top())
    (ROOT / "rtl/test/qwen_dv/tb_qfd_dv_slice2_e_lpf.sv").write_text(tb())
    print("wrote rtl/qwen_dv/qfd_dv_slice2_lpf_parts.sv rtl/qwen_dv/qfd_dv_slice2_e_lpf.sv")


if __name__ == "__main__":
    main()
