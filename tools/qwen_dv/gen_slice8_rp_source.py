#!/usr/bin/env python3
"""Recover existing c0f8097f3 RP1/ARF1 into opt-in split-parent source.
No old CRH hard-view alias: qfd_dv_s8_crh_rp1 is a new, unclosed leaf.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
D=R/'rtl/qwen_dv/s5/s8';D.mkdir(parents=True,exist_ok=True)
def extract(path,module):
    s=(R/path).read_text();a=s.index('module '+module+' ');b=s.index('endmodule',a)+len('endmodule');return s[a:b]+'\n'

def main():
    cr=extract('rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv','qfd_dv_s8x_crh').replace('module qfd_dv_s8x_crh ','module qfd_dv_s8_crh_rp1 ',1)
    cr=cr.replace('wire [511:0] cr_rd;', '''// Same capture age as twc_a/crw; bank mask is part of actual leaf logic.
    wire [1:0] twc_half;
    qfd_dv_s8x_kff #(.W(2), .ID(7303)) u_twch (.ck(ck), .d(ptw_addr[11:10]), .q(twc_half));
    wire [511:0] cr_rd;''')
    cr=cr.replace('.w_ce_in(twc_crw)', '.w_ce_in(twc_crw && (!twc_half[1] || twc_half[0] == bk[0]))')
    cr=cr.replace('ptw_addr[23:10] != 0','(ptw_addr[23:12] != 0 || (!ptw_addr[11] && ptw_addr[10]))')
    (D/'qfd_dv_s8_crh_rp1.sv').write_text('`timescale 1ns/1ps\n// Existing CRH1 half-write semantics recovered from c0f8097f3 qfd_dv_vm. UNCLOSED successor.\n'+cr)
    q=(R/'rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv').read_text().replace('qfd_dv_s5_vm8q','qfd_dv_s8_vm8q_rp1').replace('qfd_dv_s8x_crh u_c','qfd_dv_s8_crh_rp1 u_c')
    assert q.count('qfd_dv_s8_crh_rp1 u_c')==2
    (D/'qfd_dv_s8_vm8q_rp1.sv').write_text(q)
    q=(R/'rtl/qwen_dv/s5/p3/qfd_dv_s5_suvm_su8p3.sv').read_text().replace('module qfd_dv_s5_suvm_su8p3 #','module qfd_dv_s8_suvm_rp1 #',1).replace('qfd_dv_s5_vm8q u_vm8q','qfd_dv_s8_vm8q_rp1 u_vm8q')
    (D/'qfd_dv_s8_suvm_rp1.sv').write_text(q)
    fdn()

def fdn():
    # ARF stamps the existing outgoing publication: no extra sequential edge.
    f=extract('rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv','qfd_dv_s6_fdn').replace('module qfd_dv_s6_fdn ','module qfd_dv_s8_fdn_arf1 ',1)
    f=f.replace('module qfd_dv_s8_fdn_arf1 (', 'module qfd_dv_s8_fdn_arf1 #(parameter integer USE_SEL_COPIES=0) (', 1)
    f=f.replace('    input  wire [1094:0]  chu_q,', '    input wire [45:0] chu_ar_sel, chu_dd_sel,\n    input  wire [1094:0]  chu_q,', 1)
    old_mux="wire [1094:0] ch_m = {p_ar ? chu_q[1094:548] : own_ch[1094:548], p_dd ? chu_q[547:0] : own_ch[547:0]};"
    new_mux="""wire [1094:0] ch_raw;
    generate for(genvar c=0;c<46;c=c+1) begin:g_ch_select
      localparam integer ARW=(547-c*12<12)?547-c*12:12;
      localparam integer DDW=(548-c*12<12)?548-c*12:12;
      wire sa=USE_SEL_COPIES?chu_ar_sel[c]:p_ar;
      wire sd=USE_SEL_COPIES?chu_dd_sel[c]:p_dd;
      assign ch_raw[548+c*12+:ARW]=sa?chu_q[548+c*12+:ARW]:own_ch[548+c*12+:ARW];
      assign ch_raw[c*12+:DDW]=sd?chu_q[c*12+:DDW]:own_ch[c*12+:DDW];
    end endgenerate"""
    assert old_mux in f
    f=f.replace(old_mux,new_mux)
    anchor='    always @(posedge ck or negedge rst[0])\n        if (!rst[0]) begin ch_dn_o'
    logic='''    reg [3:0] arf_sid; reg arf_sid_ok;
    wire setid=cmd_q[0] && cmd_q[3:1]==3'd7;
    always @(posedge ck or negedge rst[1])
      if(!rst[1]) begin arf_sid<=0;arf_sid_ok<=0;end
      else if(setid) begin arf_sid<=cmd_q[7:4];arf_sid_ok<=1;end
    wire go=cmd_q[0] && arf_sid_ok && (cmd_q[115:112]==arf_sid || cmd_q[115:112]==4'hf) && cmd_q[3:1]!=3'd7;
    reg arf_arm;reg[31:0]arf_tag;reg[15:0]arf_wm1,arf_cnt;
    // One header predicate, then independent real kept guard cells per field.
    wire xcc_header=(cmd_q[3:1]==0) && (cmd_q[5:4]==0);
    wire [7:0] xcc_guard;
    generate for(genvar g=0;g<8;g=g+1)begin:g_xcc_guard
      qfd_dv_s8_fdn_and2 #(.ID(g)) u_g(.a(go),.b(xcc_header),.y(xcc_guard[g]));
    end endgenerate
    wire c_xcc=xcc_guard[0];
    wire [6:0] fr_guard;
    generate for(genvar g=0;g<7;g=g+1)begin:g_fr_guard
      qfd_dv_s8_fdn_and2 #(.ID(20+g)) u_g(.a(arf_arm),.b(ch_raw[1094]),.y(fr_guard[g]));
    end endgenerate
    wire arf_fr=fr_guard[0];wire arf_last=arf_cnt==arf_wm1;
    wire arf_bad=(c_xcc && arf_arm && !(arf_fr && arf_last)) || (ch_raw[1094] && !arf_arm && arf_sid==0);
    // Payload/tag/counter are meaningful only while arf_arm. Control reset uses
    // the existing independent kept copy1, preserving original copy0's20loads.
    always @(posedge ck or negedge rst[1])
      if(!rst[1])arf_arm<=0;
      else if(c_xcc)arf_arm<=1;
      else if(arf_fr && arf_last)arf_arm<=0;
    wire[15:0] arf_wm1_load=cmd_q[22:7]-16'd1;
    wire[15:0] arf_cnt_inc=arf_cnt+16'd1;
    generate for(genvar g=0;g<3;g=g+1)begin:g_tag
      localparam integer LO=g*12,GW=(32-LO<12)?32-LO:12;
      always @(posedge ck) if(xcc_guard[1+g]) arf_tag[LO+:GW]<=cmd_q[23+LO+:GW];
    end
    for(genvar g=0;g<2;g=g+1)begin:g_counter
      localparam integer LO=g*12,GW=(16-LO<12)?16-LO:12;
      always @(posedge ck) if(xcc_guard[4+g]) arf_wm1[LO+:GW]<=arf_wm1_load[LO+:GW];
      always @(posedge ck)
        if(xcc_guard[6+g]) arf_cnt[LO+:GW]<=0;
        else if(fr_guard[5+g]) arf_cnt[LO+:GW]<=arf_cnt_inc[LO+:GW];
    end endgenerate
    wire[546:0]ar_out;
    // These branches were identical in the original ternary, including X/Z.
    assign ar_out[511:0]=ch_raw[1059:548];
    assign ar_out[513]=ch_raw[1061];
    generate for(genvar g=0;g<3;g=g+1)begin:g_tag_mux
      localparam integer LO=g*12,GW=(32-LO<12)?32-LO:12;
      qfd_dv_s8_fdn_mux #(.W(GW),.ID(g)) u_m(.s(fr_guard[1+g]),
        .a(arf_tag[LO+:GW]),.b(ch_raw[1062+LO+:GW]),.y(ar_out[514+LO+:GW]));
    end endgenerate
    qfd_dv_s8_fdn_mux #(.W(2),.ID(4)) u_meta(.s(fr_guard[4]),
      .a({1'b1,arf_last}),.b({ch_raw[1094],ch_raw[1060]}),.y({ar_out[546],ar_out[512]}));
    wire[1094:0]ch_m={ar_out,ch_raw[547:0]};
'''
    assert anchor in f;f=f.replace(anchor,logic+anchor).replace('pq <= pc;','pq <= pc | arf_bad;')
    helpers='''

(* keep_hierarchy="yes" *) module qfd_dv_s8_fdn_and2 #(parameter integer ID=0)(input wire a,b,output wire y);
 assign y=a & b;
endmodule
(* keep_hierarchy="yes" *) module qfd_dv_s8_fdn_mux #(parameter integer W=12,ID=0)(input wire s,input wire[W-1:0]a,b,output wire[W-1:0]y);
 assign y=s ? a : b;
endmodule
'''
    (D/'qfd_dv_s8_fdn_arf1.sv').write_text('`timescale 1ns/1ps\n// Existing ARF1 stamps before original fdn output register; split regional timing must be measured.\n'+f+helpers)
if __name__=='__main__':main()
