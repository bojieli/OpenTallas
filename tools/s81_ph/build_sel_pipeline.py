#!/usr/bin/env python3
"""Generate private pipelined search/control copies; leave native golden bytes intact."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[2]
lib=ROOT/'rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv'
ctl=ROOT/'rtl/hdc/v41x/ot_hdc_v41x_sel.sv'
s=lib.read_text().split('module ot_hdc_v41x_sel_su #(',1)[1]
s='module ot_s81ph_sel_su_pipe #('+s
start=s.index('    reg [16*SW-1:0]   sa_d;')
end=s.index('    // compares registered',start)
s=s[:start]+'''    wire [16*SW-1:0] sa_d;
    wire [16*XW-1:0] s2_d, s3_d;
    reg [16*SW-1:0] ap0, ap1;
    reg [16*XW-1:0] aq0, aq1, at;
    reg [QW-1:0] qp, qq, qt;
    genvar n;
    generate for (n=0; n<16; n=n+1) begin : g_a
        wire [SW-1:0] p0, p1;
        wire [XW-1:0] z0, z1, zt;
        ot_hdc_ksadd_k #(.W(SW)) p_0 (.a({2'b0,gs_r[GW*n+:GW]}), .b({2'b0,gs_r[GW*(16+n)+:GW]}), .cin(1'b0), .s(p0), .cout());
        ot_hdc_ksadd_k #(.W(SW)) p_1 (.a({2'b0,gs_r[GW*(32+n)+:GW]}), .b({2'b0,gs_r[GW*(48+n)+:GW]}), .cin(1'b0), .s(p1), .cout());
        ot_hdc_ksadd_k #(.W(SW)) p_sum (.a(ap0[SW*n+:SW]), .b(ap1[SW*n+:SW]), .cin(1'b0), .s(sa_d[SW*n+:SW]), .cout());
        wire [XW-1:0] a0={{(XW-SW){1'b0}},sa_r[SW*n+:SW]};
        wire [XW-1:0] a1=(n+1<16) ? {{(XW-SW){1'b0}},sa_r[SW*((n+1)%16)+:SW]} : 0;
        wire [XW-1:0] a2=(n+2<16) ? {{(XW-SW){1'b0}},sa_r[SW*((n+2)%16)+:SW]} : 0;
        wire [XW-1:0] a3=(n+3<16) ? {{(XW-SW){1'b0}},sa_r[SW*((n+3)%16)+:SW]} : 0;
        ot_hdc_ksadd_k #(.W(XW)) q_0 (.a(a0), .b(a1), .cin(1'b0), .s(z0), .cout());
        ot_hdc_ksadd_k #(.W(XW)) q_1 (.a(a2), .b(a3), .cin(1'b0), .s(z1), .cout());
        ot_hdc_ksadd_k #(.W(XW)) q_sum (.a(aq0[XW*n+:XW]), .b(aq1[XW*n+:XW]), .cin(1'b0), .s(s2_d[XW*n+:XW]), .cout());
        ot_hdc_ksadd_k #(.W(XW)) t_sum (.a(s2_r[XW*n+:XW]), .b((n+4<16) ? s2_r[XW*((n+4)%16)+:XW] : {XW{1'b0}}), .cin(1'b0), .s(zt), .cout());
        ot_hdc_ksadd_k #(.W(XW)) s_sum (.a(at[XW*n+:XW]), .b((n+8<16) ? at[XW*((n+8)%16)+:XW] : {XW{1'b0}}), .cin(1'b0), .s(s3_d[XW*n+:XW]), .cout());
        always @(posedge clk) begin ap0[SW*n+:SW]<=p0; ap1[SW*n+:SW]<=p1; aq0[XW*n+:XW]<=z0; aq1[XW*n+:XW]<=z1; at[XW*n+:XW]<=zt; end
    end endgenerate
    always @(posedge clk) begin
        gs_r <= gs; q0 <= q;
        qp <= q0; sa_r <= sa_d; q1 <= qp;
        qq <= q1; s2_r <= s2_d; q2 <= qq;
        qt <= q2; s3_r <= s3_d; q3 <= qt;
    end
''' + s[end:]
start=s.index('    reg [16*SW-1:0]   sb_d;')
end=s.index('    reg [15:0]      geb;',start)
s=s[:start]+'''    wire [16*SW-1:0] sb_d;
    wire [16*XW-1:0] u2_d, u3_d;
    reg [16*SW-1:0] bp0, bp1;
    reg [16*XW-1:0] bq0, bq1, bt, bu;
    reg [XW+QW+4-1:0] bm0, bm1, bm2, bm3;
    generate for (n=0; n<16; n=n+1) begin : g_b
        wire [SW-1:0] p0, p1;
        wire [XW-1:0] z0, z1, zt, zu;
        ot_hdc_ksadd_k #(.W(SW)) p_0 (.a({{(SW-CB){1'b0}},bs_r[CB*n+:CB]}), .b({{(SW-CB){1'b0}},bs_r[CB*(16+n)+:CB]}), .cin(1'b0), .s(p0), .cout());
        ot_hdc_ksadd_k #(.W(SW)) p_1 (.a({{(SW-CB){1'b0}},bs_r[CB*(32+n)+:CB]}), .b({{(SW-CB){1'b0}},bs_r[CB*(48+n)+:CB]}), .cin(1'b0), .s(p1), .cout());
        ot_hdc_ksadd_k #(.W(SW)) p_sum (.a(bp0[SW*n+:SW]), .b(bp1[SW*n+:SW]), .cin(1'b0), .s(sb_d[SW*n+:SW]), .cout());
        wire [XW-1:0] a0={{(XW-SW){1'b0}},sb_r[SW*n+:SW]};
        wire [XW-1:0] a1=(n+1<16) ? {{(XW-SW){1'b0}},sb_r[SW*((n+1)%16)+:SW]} : 0;
        wire [XW-1:0] a2=(n+2<16) ? {{(XW-SW){1'b0}},sb_r[SW*((n+2)%16)+:SW]} : 0;
        wire [XW-1:0] a3=(n+3<16) ? {{(XW-SW){1'b0}},sb_r[SW*((n+3)%16)+:SW]} : 0;
        ot_hdc_ksadd_k #(.W(XW)) q_0 (.a(a0), .b(a1), .cin(1'b0), .s(z0), .cout());
        ot_hdc_ksadd_k #(.W(XW)) q_1 (.a(a2), .b(a3), .cin(1'b0), .s(z1), .cout());
        ot_hdc_ksadd_k #(.W(XW)) q_sum (.a(bq0[XW*n+:XW]), .b(bq1[XW*n+:XW]), .cin(1'b0), .s(u2_d[XW*n+:XW]), .cout());
        ot_hdc_ksadd_k #(.W(XW)) t_sum (.a(u2_r[XW*n+:XW]), .b((n+4<16) ? u2_r[XW*((n+4)%16)+:XW] : {XW{1'b0}}), .cin(1'b0), .s(zt), .cout());
        ot_hdc_ksadd_k #(.W(XW)) u_sum (.a(bt[XW*n+:XW]), .b((n+8<16) ? bt[XW*((n+8)%16)+:XW] : {XW{1'b0}}), .cin(1'b0), .s(zu), .cout());
        wire [XW-1:0] aligned_acc=bm3[XW+QW+4-1:QW+4];
        ot_hdc_ksadd_k #(.W(XW)) final_sum (.a(bu[XW*n+:XW]), .b(aligned_acc), .cin(1'b0), .s(u3_d[XW*n+:XW]), .cout());
        always @(posedge clk) begin bp0[SW*n+:SW]<=p0; bp1[SW*n+:SW]<=p1; bq0[XW*n+:XW]<=z0; bq1[XW*n+:XW]<=z1; bt[XW*n+:XW]<=zt; bu[XW*n+:XW]<=zu; end
    end endgenerate
    always @(posedge clk) begin
        acc_d1 <= acc_a; acc_d2 <= acc_d1; acc_d3 <= acc_d2;
        q_d1 <= qa; q_d2 <= q_d1; q_d3 <= q_d2;
        g_d1 <= g_out; g_d2 <= g_d1; g_d3 <= g_d2;
        bs_r <= bs;
        bm0 <= {acc_e,q_e,g_e};
        sb_r <= sb_d; {acc_b1,q_b1,g_b1} <= bm0;
        bm1 <= {acc_b1,q_b1,g_b1};
        u2_r <= u2_d; {acc_b2,q_b2,g_b2} <= bm1;
        bm2 <= {acc_b2,q_b2,g_b2}; bm3 <= bm2;
        u3_r <= u3_d; {acc_b3,q_b3,g_b3} <= bm3;
    end
''' + s[end:]
s=s.replace('endmodule','    initial if (Q != 4) $fatal(1, "S81 search pipeline requires Q=4");\nendmodule')
c='module ot_s81ph_sel_ctl_pipe #('+ctl.read_text().split('module ot_hdc_v41x_sel_ctl #(',1)[1]
c=c.replace('ot_hdc_v41x_sel_su #','ot_s81ph_sel_su_pipe #')
c=c.replace('WAIT = 13 + XR','WAIT = 20 + XR').replace('HOLD = 26 + 2 * XR','HOLD = 40 + 2 * XR')
c=c.replace('HC0  = 20 + 2 * XR, HF0 = 36 + 2 * XR, CLRW = 20 + 2 * XR','HC0  = 27 + 2 * XR, HF0 = 50 + 2 * XR, CLRW = 27 + 2 * XR')
# Mechanism negatives: deliberately unsafe threshold / replay behavior, only opt-in benches.
c=c.replace('c_T <= (tc > c_T)', "c_T <= (tc > c_T)")
c=c.replace('    wire [15:0]   tc = {cres_b, 8\'h00};', '''`ifdef S81PH_MUT_THRESHOLD
    wire [15:0] tc = 16'hffff;
`else
    wire [15:0] tc = {cres_b, 8'h00};
`endif''')
c=c.replace('rep_req <= |st_ovf;', '''rep_req <= |st_ovf;
`ifdef S81PH_MUT_REPLAY
                        rep_req <= 1'b0;
`endif''')
header='`timescale 1ns/1ps\n// Generated by tools/s81_ph/build_sel_pipeline.py. Native golden sources remain unchanged.\n'
header+='// sel_lib SHA256 '+hashlib.sha256(lib.read_bytes()).hexdigest()+'\n'
header+='// sel_ctl SHA256 '+hashlib.sha256(ctl.read_bytes()).hexdigest()+'\n'
header+='// A: +3 edges; B: +4 edges; II=1. Every added arithmetic cut carries quota/group/offset.\n'
(ROOT/'rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv').write_text(header+s+'\n'+c)
