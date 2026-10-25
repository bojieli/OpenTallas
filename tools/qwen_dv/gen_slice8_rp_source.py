#!/usr/bin/env python3
"""Recover existing c0f8097f3 RP1/ARF1 into opt-in split-parent source.
No old CRH hard-view alias: qfd_dv_s8_crh_rp1 is a new, unclosed leaf.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
D=R/'rtl/qwen_dv/s5/s8';D.mkdir(parents=True,exist_ok=True)
def extract(path,module):
    s=(R/path).read_text();a=s.index('module '+module+' ');b=s.index('endmodule',a)+len('endmodule');return s[a:b]+'\n'

def retain_selected(name):
    p=D/name
    if not p.is_file():
        raise SystemExit(f"selected qualified SRAM parent/leaf absent: {p}; restore it from source control")

def main():
    cr=extract('rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv','qfd_dv_s8x_crh').replace('module qfd_dv_s8x_crh ','module qfd_dv_s8_crh_rp1 ',1)
    cr=cr.replace('wire [511:0] cr_rd;', '''// Same capture age as twc_a/crw; bank mask is part of actual leaf logic.
    wire [1:0] twc_half;
    qfd_dv_s8x_kff #(.W(2), .ID(7303)) u_twch (.ck(ck), .d(ptw_addr[11:10]), .q(twc_half));
    wire [511:0] cr_rd;''')
    cr=cr.replace('.w_ce_in(twc_crw)', '.w_ce_in(twc_crw && (!twc_half[1] || twc_half[0] == bk[0]))')
    cr=cr.replace('ptw_addr[23:10] != 0','(ptw_addr[23:12] != 0 || (!ptw_addr[11] && ptw_addr[10]))')
    retain_selected('qfd_dv_s8_crh_rp1.sv')
    q=(R/'rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv').read_text().replace('qfd_dv_s5_vm8q','qfd_dv_s8_vm8q_rp1').replace('qfd_dv_s8x_crh u_c','qfd_dv_s8_crh_rp1 u_c')
    assert q.count('qfd_dv_s8_crh_rp1 u_c')==2
    retain_selected('qfd_dv_s8_vm8q_rp1.sv')
    q=(R/'rtl/qwen_dv/s5/p3/qfd_dv_s5_suvm_su8p3.sv').read_text().replace('module qfd_dv_s5_suvm_su8p3 #','module qfd_dv_s8_suvm_rp1 #',1).replace('qfd_dv_s5_vm8q u_vm8q','qfd_dv_s8_vm8q_rp1 u_vm8q')
    retain_selected('qfd_dv_s8_suvm_rp1.sv')
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
    // QE3-SLICE2B 10-21 (census c_xcc 80/34, !arf_fr 68 loads): kept same-edge decode / AND copies, <=12 b each.
    // c_xcc_k: [0] arm/bad, [1..4] tag bytes, [5..6] wm1 bytes, [7..8] cnt bytes. arf_fr_k: [0..2] stamp mux, [3..4] cnt bytes.
    wire [8:0] c_xcc_k;
    generate for(genvar k=0;k<9;k=k+1) begin:g_xdec
      (* keep_hierarchy = "yes" *) qfd_s8k_arf_dec u_d(.c0(cmd_q[0]),.op(cmd_q[3:1]),.sub(cmd_q[5:4]),.dst(cmd_q[115:112]),.sid(arf_sid),.sid_ok(arf_sid_ok),.c_xcc(c_xcc_k[k]));
    end endgenerate
    wire c_xcc=c_xcc_k[0];
    wire arf_fr=arf_arm && ch_raw[1094];wire arf_last=arf_cnt==arf_wm1;
    wire [4:0] arf_fr_k;
    generate for(genvar k=0;k<5;k=k+1) begin:g_frk
      (* keep_hierarchy = "yes" *) qfd_s8k_and2 u_a(.a(arf_arm),.b(ch_raw[1094]),.y(arf_fr_k[k]));
    end endgenerate
    wire arf_bad=(c_xcc && arf_arm && !(arf_fr && arf_last)) || (ch_raw[1094] && !arf_arm && arf_sid==0);
    // Payload/tag/counter are meaningful only while arf_arm. Control reset uses
    // the existing independent kept copy1, preserving original copy0's20loads.
    always @(posedge ck or negedge rst[1])
      if(!rst[1])arf_arm<=0;
      else if(c_xcc)arf_arm<=1;
      else if(arf_fr && arf_last)arf_arm<=0;
    wire [15:0] arf_wm1_d=cmd_q[22:7]-16'd1;
    wire [15:0] arf_cnt_inc=arf_cnt+16'd1;
    always @(posedge ck) begin
      for(integer j=0;j<4;j=j+1) if(c_xcc_k[1+j]) arf_tag[j*8+:8]<=cmd_q[23+j*8+:8];
      for(integer j=0;j<2;j=j+1) if(c_xcc_k[5+j]) arf_wm1[j*8+:8]<=arf_wm1_d[j*8+:8];
      for(integer j=0;j<2;j=j+1)
        if(c_xcc_k[7+j]) arf_cnt[j*8+:8]<=8'd0;
        else if(arf_fr_k[3+j]) arf_cnt[j*8+:8]<=arf_cnt_inc[j*8+:8];
    end
    wire [31:0] arf_tag_sel;
    generate for(genvar t=0;t<32;t=t+1) begin:g_tag_sel
      assign arf_tag_sel[t]=arf_fr_k[t/12] ? arf_tag[t] : ch_raw[1062+t];
    end endgenerate
    wire arf_last_sel=arf_fr_k[2] ? arf_last : ch_raw[1060];
    // == arf_fr ? {1'b1,arf_tag,ch_raw[1061],arf_last,ch_raw[1059:548]} : ch_raw[1094:548]
    wire[546:0]ar_out={arf_fr ? 1'b1 : ch_raw[1094],arf_tag_sel,ch_raw[1061],arf_last_sel,ch_raw[1059:548]};
    wire[1094:0]ch_m={ar_out,ch_raw[547:0]};
'''
    assert anchor in f;f=f.replace(anchor,logic+anchor).replace('pq <= pc;','pq <= pc | arf_bad;')
    # QE3-SLICE2B 10-21 (w13cb census l9_i[513:512] 64 loads = 8 per-station rings x D=8): the shared 2 control bits
    # leave once as l9_c (one ring, read by every station region); per-station nets carry only their 64 data bits.
    import re as _re
    f=_re.sub(r'output wire \[65:0\](\s+)l9_r0, l9_r1, l9_r2, l9_r3, l9_r4, l9_r5, l9_r6, l9_r7,',
              r'output wire [63:0]\1l9_r0, l9_r1, l9_r2, l9_r3, l9_r4, l9_r5, l9_r6, l9_r7,\n    output wire [1:0]     l9_c,',f)
    assert 'l9_c,' in f
    n0=f.count('{l9_i[513:512], l9_i[');f=f.replace('{l9_i[513:512], l9_i[','{l9_i[');assert n0==8,n0
    f=f.replace('    assign l9_r0 =','    assign l9_c = l9_i[513:512];\n    assign l9_r0 =',1)
    (D/'qfd_dv_s8_fdn_arf1.sv').write_text('`timescale 1ns/1ps\n// Existing ARF1 stamps before original fdn output register; split regional timing must be measured.\n'+f)
if __name__=='__main__':main()
