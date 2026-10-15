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
    change("LU > 126 || LS < 1", "LU > 62 || LS < 1")
    change("1 <= LU <= 126, 1 <= LS <= 509, GC 8\");", "1 <= LU <= 62, 1 <= LS <= 509, GC 8\");")
    change("    input  wire              clk,", "    input  wire              clk,\n    input wire [67:0] clk_region, // same compiled edge; independent physical roots")
    change("    input wire [8:0] clk_mem, // CCLK1: P0/P1,S0..S4,R0/R1 direct macro entries",
           "    input wire [24:0] clk_mem, // P five quarters x two banks; S five; R five quarters x two banks")
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
    change("        always @(posedge clk) srr_q[gj] <= sr_rec[gj*PW +: PW];", """        for(gsi=0;gsi<4;gsi=gsi+1)begin:g_quarter
            localparam integer RID=(gsi==0)?6+gj:50+gj*3+gsi;
            if(gsi==0)begin:g_meta
                ot_coll_local_record #(.W(128+TAGW+2),.ID(RID)) u_region(.clk(clk_region[RID]),.rst_n(rs_s),.dv(sr_valid[gj]),
                    .d({sr_rec[gj*PW+FW +:TAGW+2],sr_rec[gj*PW +:128]}),.qv(srv_q[gj]),.q({srr_q[gj][FW +:TAGW+2],srr_q[gj][0 +:128]}));
            end else begin:g_data
                ot_coll_local_capture #(.W(128),.ID(RID)) u_region(.clk(clk_region[RID]),.en(1'b1),
                    .d(sr_rec[gj*PW+128*gsi +:128]),.q(srr_q[gj][128*gsi +:128]));
            end
        end""")
    change("    generate for (gj = 0; gj < 3; gj = gj + 1) begin : g_sri", "    genvar gsi;\n    generate for (gj = 0; gj < 3; gj = gj + 1) begin : g_sri")
    change("    always @(posedge clk or negedge rs_s) if (!rs_s) srv_q <= 3'b0; else srv_q <= sr_valid;", "")
    # Each SerDes record is quarter-banked at the four real fold rows. Its
    # data selection is inside the consuming registered leaf, not parent glue.
    start=text.index("    wire [NS-1:0] tcv_r, gd_r;")
    end=text.index("    // peer send slots",start)
    text=text[:start]+"""    genvar gj,gso;
    generate for(gj=0;gj<3;gj=gj+1)begin:g_sxo
      for(gso=0;gso<4;gso=gso+1)begin:g_quarter
        localparam integer RID=(gso==0)?3+gj:41+gj*3+gso;
        wire[TAGW+1:0]qm;wire qv;
        ot_coll_local_sx_quarter #(.ID(RID),.META(gso==0)) u_region(
          .clk(clk_region[RID]),.rst_data_n(rs_p),.rst_meta_n(rs_s),
          .tc_d(tbc[TBW*(DBC-1)-1]),.gd_d(gk_next[2]),
          .pf(pf_q[gso*128 +:128]),.lo(lo_q[gso*128 +:128]),.hi(hi_q[gso*128 +:128]),
          .pkg_d(pkg_s),.tc_v(tc_v),.tc_o(tc_o),.tc_l(tc_l),.tc_t(tc_t),
          .g_run(g_run),.g_r(g_r),.g_l(g_l),.g_t(g_t),
          .q(sx_rec[gj*PW+gso*128 +:128]),.qm(qm),.qv(qv));
        if(gso==0)begin:g_meta
          assign sx_rec[gj*PW+FW +:TAGW+2]=qm;assign sx_valid[gj]=qv;
        end
      end
    end endgenerate
"""+text[end:]
    start=text.index("    reg [8:0] cc;")
    end=text.index("    // ---------------- Q:",start)
    text=text[:start]+text[end:]
    start=text.index("    generate for (gm = 0; gm < SEW / 128; gm = gm + 1) begin : g_sring")
    end=text.index("    // ---------------- D:",start)
    text=text[:start]+"""    generate for(gm=0;gm<5;gm=gm+1)begin:g_sring
      if(gm<4)begin:g_data
        ot_coll_local_sring_data #(.LS(LS),.ID(37+gm)) u_region(
          .ctl_ck(clk_region[37+gm]),.mem_ck(CCLK?clk_mem[2+gm]:clk),.rst_counter_n(rs_s),.rst_select_n(rs_p),
          .tc_d(tbc[TBW*(DBC-1)-1]),.gd_d(gk_next[2]),
          .pf(pf_q[gm*128 +:128]),.lo(lo_q[gm*128 +:128]),.hi(hi_q[gm*128 +:128]),.rd(s_rd[gm*128 +:128]));
      end else begin:g_meta
        ot_coll_local_sring_meta #(.LS(LS),.ID(41)) u_region(
          .ctl_ck(clk_region[41]),.mem_ck(CCLK?clk_mem[6]:clk),.rst_counter_n(rs_s),
          .tc_v(tc_v),.tc_o(tc_o),.tc_l(tc_l),.tc_t(tc_t),
          .g_run(g_run),.g_r(g_r),.g_od(g_d),.g_l(g_l),.g_t(g_t),.rd(s_rd[512 +:128]));
      end
    end endgenerate

"""+text[end:]

    change("    reg [FW-1:0] lo_q, hi_q; reg red_q;", "    wire [FW-1:0] lo_q, hi_q; reg red_q;")
    change("        always @(posedge clk) if (tbv_r[gr]) begin lo_q[gr*128 +: 128] <= lo[gr*128 +: 128]; hi_q[gr*128 +: 128] <= hi[gr*128 +: 128]; end",
           "        ot_coll_local_pair_capture #(.W(128),.ID(13+gr)) u_region (.clk(clk_region[13+gr]),.rst_n(rs_p),.die_d(die_ps),.token_d(tab[4*(DAB-1)-1]),.local_data(pr_rd[gr*128 +: 128]),.peer_data(dpr_q[gr*128 +: 128]),.lo(lo_q[gr*128 +: 128]),.hi(hi_q[gr*128 +: 128]));")
    # The pair leaf owns its actual control FFs and both data muxes. Merely
    # extracting the 256 DFFs would leave a combinational bus in the parent.
    start=text.index("    wire [NS-1:0] di_r, tbv_r;")
    end=text.index("`ifdef OT_TP8S_MUT_OWNER",start)
    text=text[:start]+"    genvar gr;\n"+text[end:]
    change("    reg [FW-1:0] pf_q; reg pe_q;", "    wire [FW-1:0] pf_q; reg pe_q;")
    change("        always @(posedge clk) pf_q[gs*128 +: 128] <= ps_e[gs] ? {4{32'h7fc00000}} : ps_sum[gs*128 +: 128];",
           "        ot_coll_local_fold_capture #(.W(128),.ID(17+gs)) u_region (.clk(clk_region[17+gs]),.error(ps_e[gs]),.d(ps_sum[gs*128 +: 128]),.q(pf_q[gs*128 +: 128]));")
    change("    reg [FW-1:0] xr_q; reg xe_q;", "    wire [FW-1:0] xr_q; reg xe_q;")
    change("    always @(posedge clk) xr_q <= xs_sum;",
           "    ot_coll_local_capture #(.W(FW),.ID(9)) u_region_9 (.clk(clk_region[9]),.en(1'b1),.d(xs_sum),.q(xr_q));")

    # The output leaves own the complete registered gather/reduce merge. Each
    # 128-bit quarter has its own root; metadata travels with quarter zero.
    start=text.index("    wire [NS-1:0] tfv_r, tfo_r;")
    end=text.index("    // ---------------- sticky faults",start)
    text=text[:start]+"""    wire rf_e = tf_o ? rr_rd[FW+1] : drr_q[FW+1];
    wire o_conf=tf_v&&gd_v;
    wire[FW-1:0]od_q;wire ov_q,ol_q,oe_q;wire[2:0]or_q;
    generate for(gr=0;gr<NS;gr=gr+1) begin:g_output_region
        localparam integer RID=(gr==0)?12:33+gr;
        wire qv,ql,qe;wire[2:0]qr;
        ot_coll_local_output #(.W(128),.ID(RID)) u_region(
          .clk(clk_region[RID]),.rst_n(rs_r),.pkg_d(pkg_s),
          .tf_v_d(tef[3*(DEF-1)-1]),.tf_o_d(tef[3*(DEF-1)-2]),
          .tf_v(tf_v),.tf_l(tf_l),.rf_e(rf_e),.gd_v(gd_v),
          .td_r(td_r),.td_od(td_od),.td_l(td_l),
          .rr(rr_rd[gr*128 +:128]),.dr(drr_q[gr*128 +:128]),
          .td(td_d[gr*128 +:128]),.sr0(srr_q[0][gr*128 +:128]),
          .sr1(srr_q[1][gr*128 +:128]),.sr2(srr_q[2][gr*128 +:128]),
          .q(od_q[gr*128 +:128]),.qv(qv),.ql(ql),.qe(qe),.qr(qr));
        if(gr==0)begin:g_meta
          assign ov_q=qv;assign ol_q=ql;assign oe_q=qe;assign or_q=qr;
        end
    end endgenerate
    assign out_valid=ov_q;assign out_data=od_q;assign out_last=ol_q;assign out_rank=or_q;assign out_err=oe_q;

"""+text[end:]
    start=text.index("    wire [FW-1:0] g_out =")
    end=text.index("    wire gd_v",start)
    text=text[:start]+text[end:]
    start=text.index("    wire [4*FW-1:0] xsrc;")
    end=text.index("    // gather output",start)
    text=text[:start]+"""    wire[NS-1:0]xs_v,xs_e;wire[FW-1:0]xs_sum;
`ifdef OT_TP8S_MUT_RANK
    localparam integer LOCAL_XF_MUT=1;
`else
    localparam integer LOCAL_XF_MUT=0;
`endif
    generate for(gs=0;gs<NS;gs=gs+1)begin:g_xf
      ot_coll_local_xfold #(.MUT_RANK(LOCAL_XF_MUT)) u_region(
        .ctl_ck(clk_region[28+gs]),.fold_ck(CCLK?clk_xfold[gs]:clk),.rst_n(rst_n),
        .pkg_s(pkg_s),.red_in(red2),.td(td_d[gs*128 +:128]),
        .sr0(srr_q[0][gs*128 +:128]),.sr1(srr_q[1][gs*128 +:128]),.sr2(srr_q[2][gs*128 +:128]),
        .sum(xs_sum[gs*128 +:128]),.v_out(xs_v[gs]),.e_out(xs_e[gs]));
    end endgenerate
"""+text[end:]

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
    # Real existing narrow SRAM macros let every payload quarter stay local.
    # Metadata uses the fifth quarter; padding is declared physical capacity,
    # not an unbounded array or a reference-code memory substitution.
    change("    ot_coll_local_ring #(.OFF(LU + 2)) u_pring (.clk(clk), .mem_ck(CCLK ? {clk_mem[1:0],clk_mem[1:0]} : {4{clk}}), .rs_n(rs_p), .wd(ir_q), .rd(pr_rd));", """    genvar gpq;
    generate for(gpq=0;gpq<5;gpq=gpq+1)begin:g_pring_quarter
      localparam integer RID=(gpq==0)?32:59+gpq;
      if(gpq==4)begin:g_meta
        ot_coll_local_ring_quarter #(.OFF(LU+2),.W(34),.ID(RID)) u_region(.ctl_ck(clk_region[RID]),.mem_ck(CCLK?clk_mem[2*gpq +:2]:{2{clk}}),.rs_n(rs_p),.wd(ir_q[512 +:34]),.rd(pr_rd[512 +:34]));
      end else begin:g_data
        ot_coll_local_ring_quarter #(.OFF(LU+2),.W(128),.ID(RID)) u_region(.ctl_ck(clk_region[RID]),.mem_ck(CCLK?clk_mem[2*gpq +:2]:{2{clk}}),.rs_n(rs_p),.wd(ir_q[128*gpq +:128]),.rd(pr_rd[128*gpq +:128]));
      end
    end endgenerate""")
    change("    ot_coll_local_ring #(.OFF(ROFF)) u_rring (.clk(clk), .mem_ck(CCLK ? {clk_mem[8:7],clk_mem[8:7]} : {4{clk}}), .rs_n(rs_r), .wd({{(PW-RW){1'b0}}, xe_q, te_l, xr_q}), .rd(rr_rd));", """    wire[545:0]rr_wd={{(PW-RW){1'b0}},xe_q,te_l,xr_q};
    generate for(gpq=0;gpq<5;gpq=gpq+1)begin:g_rring_quarter
      localparam integer RID=(gpq==0)?33:63+gpq;
      if(gpq==4)begin:g_meta
        ot_coll_local_ring_quarter #(.OFF(ROFF),.W(34),.ID(RID)) u_region(.ctl_ck(clk_region[RID]),.mem_ck(CCLK?clk_mem[15+2*gpq +:2]:{2{clk}}),.rs_n(rs_r),.wd(rr_wd[512 +:34]),.rd(rr_rd[512 +:34]));
      end else begin:g_data
        ot_coll_local_ring_quarter #(.OFF(ROFF),.W(128),.ID(RID)) u_region(.ctl_ck(clk_region[RID]),.mem_ck(CCLK?clk_mem[15+2*gpq +:2]:{2{clk}}),.rs_n(rs_r),.wd(rr_wd[128*gpq +:128]),.rd(rr_rd[128*gpq +:128]));
      end
    end endgenerate""")
    text=text.replace("clk_mem[2+gm]","clk_mem[10+gm]").replace("clk_mem[6]:clk","clk_mem[14]:clk")
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
(* keep_hierarchy = 1 *) module ot_coll_local_pair_capture #(parameter integer W=128,ID=0)(
 input wire clk,rst_n,die_d,token_d,input wire[W-1:0]local_data,peer_data,
 output reg[W-1:0]lo,hi);
 reg die_q,token_q;
 always @(posedge clk)die_q<=die_d;
 always @(posedge clk or negedge rst_n)if(!rst_n)token_q<=0;else token_q<=token_d;
 always @(posedge clk)if(token_q)begin
  lo<=die_q?peer_data:local_data;hi<=die_q?local_data:peer_data;
 end
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_fold_capture #(parameter integer W=128,ID=0)(
 input wire clk,error,input wire[W-1:0]d,output reg[W-1:0]q);
 always @(posedge clk)q<=error?{(W/32){32'h7fc00000}}:d;
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_output #(parameter integer W=128,ID=0)(
 input wire clk,rst_n,input wire[1:0]pkg_d,input wire tf_v_d,tf_o_d,tf_v,tf_l,rf_e,gd_v,
 input wire[1:0]td_r,input wire td_od,td_l,input wire[W-1:0]rr,dr,td,sr0,sr1,sr2,
 output reg[W-1:0]q,output reg qv,ql,qe,output reg[2:0]qr);
 reg[1:0]pkg_q;reg tfv_q,tfo_q;
 always @(posedge clk)pkg_q<=pkg_d;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin tfv_q<=0;tfo_q<=0;end else begin tfv_q<=tf_v_d;tfo_q<=tf_o_d;end
 wire[1:0]jr=td_r-pkg_q+2'd3;
 wire[W-1:0]gather=(td_r==pkg_q)?td:(jr==0)?sr0:(jr==1)?sr1:sr2;
 always @(posedge clk)begin
  q<=tfv_q?(tfo_q?rr:dr):gather;
  ql<=tf_v?tf_l:(td_l&&td_od&&td_r==2'd3);
  qr<=tf_v?3'd0:{td_od,td_r};qe<=tf_v?rf_e:1'b0;
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)qv<=0;else qv<=tf_v||gd_v;
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_sx_quarter #(parameter integer ID=0,META=0)(
 input wire clk,rst_data_n,rst_meta_n,tc_d,gd_d,input wire[127:0]pf,lo,hi,
 input wire[1:0]pkg_d,input wire tc_v,tc_o,tc_l,input wire[31:0]tc_t,
 input wire g_run,input wire[1:0]g_r,input wire g_l,input wire[31:0]g_t,
 output reg[127:0]q,output wire[33:0]qm,output wire qv);
 reg tc_q,gd_q;
 always @(posedge clk or negedge rst_data_n)
  if(!rst_data_n)begin tc_q<=0;gd_q<=0;end else begin tc_q<=tc_d;gd_q<=gd_d;end
`ifdef OT_TP8S_MUT_GATHER
 always @(posedge clk)q<=tc_q?pf:(!gd_q?hi:lo);
`else
 always @(posedge clk)q<=tc_q?pf:(gd_q?hi:lo);
`endif
 generate if(META)begin:g_meta
  reg[1:0]pkg_q;reg[33:0]meta_q;reg v_q;
  always @(posedge clk)begin pkg_q<=pkg_d;meta_q<={tc_v?tc_t:g_t,!tc_v,tc_v?tc_l:g_l};end
  always @(posedge clk or negedge rst_meta_n)
   if(!rst_meta_n)v_q<=0;else v_q<=tc_v?(tc_v&&tc_o):(g_run&&g_r==pkg_q);
  assign qm=meta_q;assign qv=v_q;
 end else begin:g_data assign qm=0;assign qv=0;end endgenerate
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_sring_data #(parameter integer LS=376,ID=0)(
 input wire ctl_ck,mem_ck,rst_counter_n,rst_select_n,tc_d,gd_d,input wire[127:0]pf,lo,hi,output wire[127:0]rd);
 reg[8:0]cc;reg tc_q,gd_q;
 always @(posedge ctl_ck or negedge rst_counter_n)if(!rst_counter_n)cc<=0;else cc<=cc+9'd1;
 always @(posedge ctl_ck or negedge rst_select_n)
  if(!rst_select_n)begin tc_q<=0;gd_q<=0;end else begin tc_q<=tc_d;gd_q<=gd_d;end
`ifdef OT_TP8S_MUT_GATHER
 wire[127:0]wd=tc_q?pf:(!gd_q?hi:lo);
`else
 wire[127:0]wd=tc_q?pf:(gd_q?hi:lo);
`endif
 ot_sram_1r1w_512x128_m4_r2c2 u_m(.clk(mem_ck),.r_ce_in(1'b1),.r_addr_in(cc-9'(LS+1)),.rd_out(rd),
  .w_ce_in(1'b1),.w_addr_in(cc),.wd_in(wd),.w_mask_in({128{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_sring_meta #(parameter integer LS=376,ID=0)(
 input wire ctl_ck,mem_ck,rst_counter_n,tc_v,tc_o,tc_l,input wire[31:0]tc_t,
 input wire g_run,input wire[1:0]g_r,input wire g_od,g_l,input wire[31:0]g_t,output wire[127:0]rd);
 reg[8:0]cc;
 always @(posedge ctl_ck or negedge rst_counter_n)if(!rst_counter_n)cc<=0;else cc<=cc+9'd1;
 wire[127:0]wd={90'd0,tc_v||g_run,tc_v?2'd0:g_r,tc_v?tc_o:g_od,!tc_v,tc_v?tc_l:g_l,tc_v?tc_t:g_t};
 ot_sram_1r1w_512x128_m4_r2c2 u_m(.clk(mem_ck),.r_ce_in(1'b1),.r_addr_in(cc-9'(LS+1)),.rd_out(rd),
  .w_ce_in(1'b1),.w_addr_in(cc),.wd_in(wd),.w_mask_in({128{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_ring_quarter #(parameter integer OFF=55,W=128,ID=0)(
 input wire ctl_ck,input wire[1:0]mem_ck,input wire rs_n,input wire[W-1:0]wd,output wire[W-1:0]rd);
 localparam integer B=(OFF<=32)?1:2,AW=5+$clog2(B);
 initial if(OFF<2||OFF>64||W<1||W>128)$error("local quarter ring: OFF2..64,W1..128");
 reg[AW-1:0]wa;
 always @(posedge ctl_ck or negedge rs_n)if(!rs_n)wa<=0;else wa<=wa+1'b1;
 wire[AW-1:0]ra=wa-AW'(OFF-1);
 wire[127:0]wdata={{(128-W){1'b0}},wd};wire[128*B-1:0]rdata;
 genvar b;
 generate for(b=0;b<B;b=b+1)begin:g_bank
  wire we;
  if(B==1)begin:g_one assign we=1'b1;end else begin:g_two assign we=wa[5]==b;end
  ot_sram_1r1w_32x128_m1 u_m(.clk(mem_ck[b]),.r_ce_in(1'b1),.r_addr_in(ra[4:0]),.rd_out(rdata[128*b +:128]),
   .w_ce_in(we),.w_addr_in(wa[4:0]),.wd_in(wdata),.w_mask_in({128{1'b1}}));
 end
 if(B==1)begin:g_one assign rd=rdata[0 +:W];end else begin:g_two
  // Two private one-hot copies bound fanout to64bits per bank. They have the
  // same unreset registered read-bank timing as the legacy546-bit ring.
  wire[1:0]sel0,sel1;
  ot_coll_local_rep_reg #(.W(2),.ID(128+ID*2),.RST(0)) u_sel0(.clk(ctl_ck),.rst_n(1'b1),.d(ra[5]?2'b10:2'b01),.q(sel0));
  ot_coll_local_rep_reg #(.W(2),.ID(129+ID*2),.RST(0)) u_sel1(.clk(ctl_ck),.rst_n(1'b1),.d(ra[5]?2'b10:2'b01),.q(sel1));
  for(genvar k=0;k<W;k=k+1)begin:g_bit
   wire[1:0]sel=(k<64)?sel0:sel1;
   assign rd[k]=(rdata[k]&sel[0])|(rdata[128+k]&sel[1]);
  end
 end endgenerate
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
    wrapper=wrapper.replace("input  wire          clk,                   // parent root","input  wire          clk,                   // controller root\n    input wire [67:0] clk_region,")
    marker="    input wire clk_pring0,clk_pring1,clk_sring0,clk_sring1,clk_sring2,clk_sring3,clk_sring4,clk_rring0,clk_rring1,"
    extra=[f"clk_{family}q{q}_b{b}" for family in ('p','r') for q in range(1,5) for b in range(2)]
    assert marker in wrapper
    wrapper=wrapper.replace(marker,marker+"\n    input wire "+",".join(extra)+",")
    pclk=["clk_pring0","clk_pring1"]+[f"clk_pq{q}_b{b}" for q in range(1,5) for b in range(2)]
    rclk=["clk_rring0","clk_rring1"]+[f"clk_rq{q}_b{b}" for q in range(1,5) for b in range(2)]
    old="{clk_rring1,clk_rring0,clk_sring4,clk_sring3,clk_sring2,clk_sring1,clk_sring0,clk_pring1,clk_pring0}"
    new="{"+",".join(reversed(pclk+[f"clk_sring{k}" for k in range(5)]+rclk))+"}"
    assert old in wrapper;wrapper=wrapper.replace(old,new)
    wrapper=wrapper.replace("ot_coll_tp8_static #(","ot_coll_tp8_local_roots #(")
    wrapper=wrapper.replace(".clk(clk), .clk_pfold(",".clk_region(clk_region),.clk(clk), .clk_pfold(")
    wp=ROOT/"rtl/physical/ot_qfd_io_collective_local_roots.sv"
    if a.check:assert wp.read_text()==wrapper,"derived regional wrapper differs"
    else:wp.write_text(wrapper)
    print(json.dumps({"original_sha256":sha,"derived_sha256":hashlib.sha256(text.encode()).hexdigest(),"region_roots":68,"cycle_delta":0,"physical_qualification":False}))


if __name__=="__main__":main()
