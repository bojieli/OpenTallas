#!/usr/bin/env python3
"""Derive source-pinned, cycle-identical regional ownership for the static collective.

This is a structural source candidate, not a physical view. The legacy source is
unchanged. Every regional clock must have the same compensated edge as clk.
The geometry/cut audit must still absorb residual data muxes into physical leaves.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "f1a941b846a439ab95832aaa7d96426505a6b1b1767487faac0265c4e1365336"


def derive(root=ROOT):
    original = (root / "rtl/rom/ot_coll_tp8_static.sv").read_text()
    assert hashlib.sha256(original.encode()).hexdigest()==SOURCE_SHA256,"review source changes before re-deriving"
    text = original

    def change(old, new):
        nonlocal text
        assert text.count(old) == 1, (old[:100], text.count(old))
        text = text.replace(old, new)

    change("module ot_coll_tp8_static #(", "module ot_coll_tp8_local_roots #(")
    change("    input  wire              clk,", "    input  wire              clk,\n    input wire [33:0] clk_region, // same compiled edge; independent physical roots")
    # Keep all helper names disjoint so the legacy and candidate elaborate together.
    text = text.replace("ot_coll_static_ring", "ot_coll_local_ring")
    text = text.replace("ot_coll_static_sx_reg", "ot_coll_local_sx_reg")
    text = text.replace("ot_coll_rep_reg", "ot_coll_local_rep_reg")

    def record(decl, qv, qd, width, data, valid, reset, index, remove):
        change(decl, decl.replace("reg ", "wire "))
        for old in remove:
            change(old, "")
        anchor = decl.replace("reg ", "wire ")
        change(anchor, anchor + f"\n    ot_coll_local_record #(.W({width}),.ID({index})) u_region_{index} "
               f"(.clk(clk_region[{index}]),.rst_n({reset}),.dv({valid}),.d({data}),.qv({qv}),.q({qd}));")

    record("    reg iv_q; reg [PW-1:0] ir_q;", "iv_q", "ir_q", "PW", "{in_tag, in_mode, in_last, in_data}", "in_valid", "rs_p", 0,
           ["    always @(posedge clk) ir_q <= {in_tag, in_mode, in_last, in_data};"])
    change("iv_q <= 1'b0; ta_v", "ta_v")
    change("            iv_q <= in_valid;\n", "")
    record("    reg upv_q; reg [PW-1:0] uprec_q;", "upv_q", "uprec_q", "PW", "ir_q", "ta_v && iv_q", "rs_p", 1,
           ["    always @(posedge clk) uprec_q <= ir_q;",
            "    always @(posedge clk or negedge rs_p) if (!rs_p) upv_q <= 1'b0; else upv_q <= ta_v && iv_q;"])
    record("    reg dpv_q; reg [PW-1:0] dpr_q;", "dpv_q", "dpr_q", "PW", "dp_rec", "dp_valid", "rs_p", 2,
           ["    always @(posedge clk) dpr_q <= dp_rec;",
            "    always @(posedge clk or negedge rs_p) if (!rs_p) dpv_q <= 1'b0; else dpv_q <= dp_valid;"])
    record("    reg urv_q; reg [RW-1:0] urr_q;", "urv_q", "urr_q", "RW", "{xe_q, te_l, xr_q}", "e_own", "rs_r", 10,
           ["    always @(posedge clk) urr_q <= {xe_q, te_l, xr_q};",
            "    always @(posedge clk or negedge rs_r) if (!rs_r) urv_q <= 1'b0; else urv_q <= e_own;"])
    record("    reg drv_q; reg [RW-1:0] drr_q;", "drv_q", "drr_q", "RW", "dr_rec", "dr_valid", "rs_r", 11,
           ["    always @(posedge clk) drr_q <= dr_rec;",
            "    always @(posedge clk or negedge rs_r) if (!rs_r) drv_q <= 1'b0; else drv_q <= dr_valid;"])
    change("    reg [2:0] srv_q; reg [PW-1:0] srr_q [0:2];", "    wire [2:0] srv_q; wire [PW-1:0] srr_q [0:2];")
    change("        always @(posedge clk) srr_q[gj] <= sr_rec[gj*PW +: PW];",
           "        ot_coll_local_record #(.W(PW),.ID(6+gj)) u_region (.clk(clk_region[6+gj]),.rst_n(rs_s),.dv(sr_valid[gj]),.d(sr_rec[gj*PW +: PW]),.qv(srv_q[gj]),.q(srr_q[gj]));")
    change("    always @(posedge clk or negedge rs_s) if (!rs_s) srv_q <= 3'b0; else srv_q <= sr_valid;", "")
    change(".clk(clk),.rst_n(rs_s),.dv(w_send)", ".clk(clk_region[3+gj]),.rst_n(rs_s),.dv(w_send)")

    change("    reg [FW-1:0] lo_q, hi_q; reg red_q;", "    wire [FW-1:0] lo_q, hi_q; reg red_q;")
    change("        always @(posedge clk) if (tbv_r[gr]) begin lo_q[gr*128 +: 128] <= lo[gr*128 +: 128]; hi_q[gr*128 +: 128] <= hi[gr*128 +: 128]; end",
           "        ot_coll_local_capture #(.W(256),.ID(13+gr)) u_region (.clk(clk_region[13+gr]),.en(tbv_r[gr]),.d({hi[gr*128 +: 128],lo[gr*128 +: 128]}),.q({hi_q[gr*128 +: 128],lo_q[gr*128 +: 128]}));")
    change("    reg [FW-1:0] pf_q; reg pe_q;", "    wire [FW-1:0] pf_q; reg pe_q;")
    change("        always @(posedge clk) pf_q[gs*128 +: 128] <= ps_e[gs] ? {4{32'h7fc00000}} : ps_sum[gs*128 +: 128];",
           "        ot_coll_local_capture #(.W(128),.ID(17+gs)) u_region (.clk(clk_region[17+gs]),.en(1'b1),.d(ps_e[gs] ? {4{32'h7fc00000}} : ps_sum[gs*128 +: 128]),.q(pf_q[gs*128 +: 128]));")
    change("    reg [FW-1:0] xr_q; reg xe_q;", "    wire [FW-1:0] xr_q; reg xe_q;")
    change("    always @(posedge clk) xr_q <= xs_sum;",
           "    ot_coll_local_capture #(.W(FW),.ID(9)) u_region_9 (.clk(clk_region[9]),.en(1'b1),.d(xs_sum),.q(xr_q));")

    # Existing output mux and metadata are one explicitly owned root. A physical
    # output leaf must include their logic; merely making a register abstract is invalid.
    change("    always @(posedge clk) begin\n        for (kq", "    always @(posedge clk_region[12]) begin\n        for (kq")
    change("    always @(posedge clk or negedge rs_r) if (!rs_r) ov_q", "    always @(posedge clk_region[12] or negedge rs_r) if (!rs_r) ov_q")

    def delay(decl, old, width, expr, reset, index):
        change(decl, decl.replace("reg ", "wire "))
        change(old, f"    ot_coll_local_delay #(.W({width}),.ID({index})) u_region_{index} (.clk(clk_region[{index}]),.rst_n({reset}),.d({expr}),.q({decl.split()[-1].rstrip(';')}));")

    delay("    reg [4*DAB-1:0] tab;", "    always @(posedge clk or negedge rs_p) if (!rs_p) tab <= 0;\n        else tab <= {tab[4*(DAB-1)-1:0], ta_v, ta_m, ta_l, ta_p};", "4*DAB", "{tab[4*(DAB-1)-1:0], ta_v, ta_m, ta_l, ta_p}", "rs_p", 25)
    delay("    reg [3*DDE-1:0] tde;", "    always @(posedge clk or negedge rs_r) if (!rs_r) tde <= 0;\n        else tde <= {tde[3*(DDE-1)-1:0], td_v && !td_m, td_od, td_l};", "3*DDE", "{tde[3*(DDE-1)-1:0], td_v && !td_m, td_od, td_l}", "rs_r", 26)
    delay("    reg [3*DEF-1:0] tef;", "    always @(posedge clk or negedge rs_r) if (!rs_r) tef <= 0;\n        else tef <= {tef[3*(DEF-1)-1:0], te_v, te_o, te_l};", "3*DEF", "{tef[3*(DEF-1)-1:0], te_v, te_o, te_l}", "rs_r", 27)
    change("    reg [TBW*DBC-1:0] tbc;", "    wire [TBW*DBC-1:0] tbc;")
    change("    always @(posedge clk or negedge rs_p) if (!rs_p) tbc <= 0;\n        else tbc <= {tbc[TBW*(DBC-1)-1:0], tb_v && !tb_m, own_b, tb_l, pr_rd[FW+2 +: TAGW]};",
           """    wire [TBW*DBC-1:0] tbc_d = {tbc[TBW*(DBC-1)-1:0], tb_v && !tb_m, own_b, tb_l, pr_rd[FW+2 +: TAGW]};
    genvar gc;
    generate for(gc=0;gc<4;gc=gc+1) begin:g_calendar
        localparam integer LO=(TBW*DBC*gc)/4, HI=(TBW*DBC*(gc+1))/4;
        ot_coll_local_delay #(.W(HI-LO),.ID(21+gc)) u_region (.clk(clk_region[21+gc]),.rst_n(rs_p),.d(tbc_d[LO +: HI-LO]),.q(tbc[LO +: HI-LO]));
    end endgenerate""")
    # Replicas belong beside their consumers, not on a geographically global root.
    text = text.replace(".ID(16 + gr), .RST(0)) u_di (.clk(clk)", ".ID(16 + gr), .RST(0)) u_di (.clk(clk_region[13+gr])")
    text = text.replace(".ID(20 + gr), .RST(1)) u_tbv (.clk(clk)", ".ID(20 + gr), .RST(1)) u_tbv (.clk(clk_region[13+gr])")
    text = text.replace(".ID(24 + gr), .RST(1)) u_tcv (.clk(clk)", ".ID(24 + gr), .RST(1)) u_tcv (.clk(clk_region[17+gr])")
    text = text.replace(".ID(28 + gr), .RST(1)) u_gd (.clk(clk)", ".ID(28 + gr), .RST(1)) u_gd (.clk(clk_region[17+gr])")
    text = text.replace(".ID(32 + gq*NS + gr), .RST(0)) u_sel (.clk(clk)", ".ID(32 + gq*NS + gr), .RST(0)) u_sel (.clk(clk_region[28+gr])")
    text = text.replace(".ID(48 + gr), .RST(1)) u_tfv (.clk(clk)", ".ID(48 + gr), .RST(1)) u_tfv (.clk(clk_region[12])")
    text = text.replace(".ID(52 + gr), .RST(1)) u_tfo (.clk(clk)", ".ID(52 + gr), .RST(1)) u_tfo (.clk(clk_region[12])")
    change("u_pring (.clk(clk),", "u_pring (.clk(clk_region[32]),")
    change("u_rring (.clk(clk),", "u_rring (.clk(clk_region[33]),")
    text += """
// These leaves keep the original edge/reset/enable semantics. Data are never
// reset where the original datapath did not reset them.
(* keep_hierarchy = 1 *) module ot_coll_local_record #(parameter integer W=546,ID=0)(
 input wire clk,rst_n,dv,input wire[W-1:0]d,output reg qv,output reg[W-1:0]q);
 always @(posedge clk) q<=d;
 always @(posedge clk or negedge rst_n) if(!rst_n)qv<=0;else qv<=dv;
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_capture #(parameter integer W=128,ID=0)(
 input wire clk,en,input wire[W-1:0]d,output reg[W-1:0]q);
 always @(posedge clk) if(en)q<=d;
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_delay #(parameter integer W=128,ID=0)(
 input wire clk,rst_n,input wire[W-1:0]d,output reg[W-1:0]q);
 always @(posedge clk or negedge rst_n) if(!rst_n)q<=0;else q<=d;
endmodule
"""
    return text, hashlib.sha256(original.encode()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument("--check",action="store_true");a=p.parse_args()
    text,sha=derive();out=ROOT/"rtl/rom/ot_coll_tp8_local_roots.sv"
    if a.check:
        assert out.read_text()==text,"derived regional source differs"
    else:
        out.write_text(text)
    wrapper=(ROOT/"rtl/physical/ot_qfd_io_collective_static.sv").read_text()
    wrapper=wrapper.replace("module qfd_io_collective_static (","module qfd_io_collective_local_roots (")
    wrapper=wrapper.replace("input  wire          clk,                   // parent root","input  wire          clk,                   // controller root\n    input wire [33:0] clk_region,")
    wrapper=wrapper.replace("ot_coll_tp8_static #(","ot_coll_tp8_local_roots #(")
    wrapper=wrapper.replace(".clk(clk), .clk_pfold(",".clk_region(clk_region),.clk(clk), .clk_pfold(")
    wp=ROOT/"rtl/physical/ot_qfd_io_collective_local_roots.sv"
    if a.check:assert wp.read_text()==wrapper,"derived regional wrapper differs"
    else:wp.write_text(wrapper)
    print(json.dumps({"original_sha256":sha,"derived_sha256":hashlib.sha256(text.encode()).hexdigest(),"region_roots":34,"cycle_delta":0,"physical_qualification":False}))


if __name__=="__main__":main()
