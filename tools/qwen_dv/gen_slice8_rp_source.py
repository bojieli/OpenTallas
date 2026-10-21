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
    # ARF stamps the existing outgoing publication: no extra sequential edge.
    f=extract('rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv','qfd_dv_s6_fdn').replace('module qfd_dv_s6_fdn ','module qfd_dv_s8_fdn_arf1 ',1)
    f=f.replace('wire [1094:0] ch_m =','wire [1094:0] ch_raw =')
    anchor='    always @(posedge ck or negedge rst[0])\n        if (!rst[0]) begin ch_dn_o'
    logic='''    reg [3:0] arf_sid; reg arf_sid_ok;
    wire setid=cmd_q[0] && cmd_q[3:1]==3'd7;
    always @(posedge ck or negedge rst[0])
      if(!rst[0]) begin arf_sid<=0;arf_sid_ok<=0;end
      else if(setid) begin arf_sid<=cmd_q[7:4];arf_sid_ok<=1;end
    wire go=cmd_q[0] && arf_sid_ok && (cmd_q[115:112]==arf_sid || cmd_q[115:112]==4'hf) && cmd_q[3:1]!=3'd7;
    reg arf_arm;reg[31:0]arf_tag;reg[15:0]arf_wm1,arf_cnt;
    wire c_xcc=go && cmd_q[3:1]==0 && cmd_q[5:4]==0;
    wire arf_fr=arf_arm && ch_raw[1094];wire arf_last=arf_cnt==arf_wm1;
    wire arf_bad=(c_xcc && arf_arm && !(arf_fr && arf_last)) || (ch_raw[1094] && !arf_arm && arf_sid==0);
    always @(posedge ck or negedge rst[0])
      if(!rst[0])begin arf_arm<=0;arf_tag<=0;arf_wm1<=0;arf_cnt<=0;end
      else if(c_xcc)begin arf_arm<=1;arf_tag<=cmd_q[54:23];arf_wm1<=cmd_q[22:7]-16'd1;arf_cnt<=0;end
      else if(arf_fr)begin arf_cnt<=arf_cnt+16'd1;if(arf_last)arf_arm<=0;end
    wire[546:0]ar_out=arf_fr ? {1'b1,arf_tag,ch_raw[1061],arf_last,ch_raw[1059:548]} : ch_raw[1094:548];
    wire[1094:0]ch_m={ar_out,ch_raw[547:0]};
'''
    assert anchor in f;f=f.replace(anchor,logic+anchor).replace('pq <= pc;','pq <= pc | arf_bad;')
    (D/'qfd_dv_s8_fdn_arf1.sv').write_text('`timescale 1ns/1ps\n// Existing ARF1 stamps before original fdn output register; split regional timing must be measured.\n'+f)
if __name__=='__main__':main()
