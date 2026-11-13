`timescale 1ns/1ps
module tb_qfd_collective_status;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[115:0] cmd=0;reg[1037:0] ret=0;wire[106:0] st;wire[9:0] ag;
`ifdef STATUS_LPC
wire[106:0] st_next;wire[9:0] ag_next;
// This component contains no HEAD instruction; the independent HEAD fault
// input is inactive.  The actual reset-safe core and actual status flops run.
qfd_dv_slice2_lpc #(.MU_NU(1),.SU_LT(0),.HD_W130(1)) p(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i(453'b0),.rs_s0(514'b0),.rs_s1(514'b0),.rs_n0(514'b0),.rs_n1(514'b0),.l9_i(514'b0),.st_up_i(1088'b0),.st_dn_i(1088'b0),.sc_up_i(48'b0),.sc_dn_i(48'b0),.ch_up_i(1095'b0),.ch_dn_i(ret),.ag_up_i(10'b0),.st_n(st_next),.ag_n(ag_next));
qfd_dv_slice2_lps ps(.ck(ck),.rst_n(rst_n),.st_n(st_next),.ag_n(ag_next),.hd_fault(1'b0),.st(st),.ag_dn_o(ag));
`else
`ifdef STATUS_LPF
qfd_dv_slice2_e_lpf #(.MU_NU(1),.SU_LT(0)) p(.ck(ck),.rst_n(rst_n),.cmd_ei(cmd),.hr_ei(453'b0),.st_ei(1088'b0),.st_wi(1088'b0),.sc_ei(48'b0),.sc_wi(48'b0),.arv_wi(1'b0),.art_wi(32'b0),.arm_wi(1'b0),.arl_wi(1'b0),.ard_wi(512'b0),.dd_wi(548'b0),.rv_ei(ret[1037]),.re_ei(ret[1036]),.rr_ei(ret[1035:1033]),.rl_ei(ret[1032]),.rd_ei(ret[1031:520]),.dr_ei(ret[519:0]),.ag_wi(10'b0),.l9_wi(514'b0),.rs_n0(514'b0),.rs_n1(514'b0),.rs_s0(514'b0),.rs_s1(514'b0),.ss_eo(st),.ag_eo(ag));
`else
`ifdef STATUS_LANDED
qfd_dv_slice2 #(.SU_LT(1)) p(
`else
qfd_dv_slice2 p(
`endif
.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i(453'b0),.rs_s(1028'b0),.rs_n(1028'b0),.l9_i(514'b0),.st_up_i(1088'b0),.st_dn_i(1088'b0),.sc_up_i(48'b0),.sc_dn_i(48'b0),.ch_up_i(1095'b0),.ch_dn_i(ret),.ag_up_i(10'b0),.st(st),.ag_dn_o(ag));
`endif
`endif
qfd_tt_ctlm_dv #(.HARD_HR(1),.XPF_TRANSPORT_EDGES(1)) c(.ck(ck),.rst_n(rst_n),.pw(75'b0),.dh(187'b0),.kok(1'b0),.kwd(1'b1),.fab(1'b0),.native_ret(95'b0),.ss5(st),.ag5(ag));
reg[2:0] expected=0;reg[2:0] r0=0,r1=0;reg[1:0] vpipe=0;integer cycles=0,errs=0,nexpected=0,ngot=0;reg check_on=0;
always @(posedge ck)begin if(!rst_n)begin expected<=0;vpipe<=0;r0<=0;r1<=0;end else begin expected<={expected[1:0],ret[1037]&&ret[1032]};vpipe<={vpipe[0],ret[1037]};r0<=ret[1035:1033];r1<=r0;end end
always @(negedge ck)begin
 cycles=cycles+1;
 if(check_on)begin
  if(vpipe[1] && (st[28:26]!==r1))begin errs=errs+1;$display("STATUS_RANK_MISMATCH cyc=%0d expected=%0d got=%0d",cycles,r1,st[28:26]);end
  if(expected[2])nexpected=nexpected+1;if(c.coll_done)ngot=ngot+1;
  if(c.coll_done!==expected[2])begin errs=errs+1;if(errs<10)$display("STATUS_MISMATCH cyc=%0d expected=%b got=%b stland=%b stlast=%b",cycles,expected[2],c.coll_done,st[106],st[25]);end
 end
end
task beat(input reg v,input reg last);begin @(negedge ck);ret=0;ret[1037]=v;ret[1032]=last;ret[1035:1033]=cycles%8;ret[511:0]=512'h1234;end endtask
task arm;begin
 repeat(24)@(negedge ck);
 cmd=(116'hf<<112)|116'd15;@(negedge ck);cmd=0;repeat(5)@(negedge ck);
 cmd=(116'hf<<112)|(116'd1<<52)|116'd9;@(negedge ck);cmd=0;repeat(5)@(negedge ck);check_on=1;
end endtask
task exercise;begin
 // A terminal word followed by idle.
 beat(1,1);beat(0,0);repeat(5)@(negedge ck);
 // Consecutive multiword return followed by idle.
 beat(1,0);beat(1,0);beat(1,1);beat(0,0);repeat(5)@(negedge ck);
 // Bubbles inside a return and back-to-back one-word message boundaries.
 beat(1,0);beat(0,0);beat(1,1);beat(0,0);beat(1,1);beat(1,1);beat(0,0);repeat(6)@(negedge ck);
end endtask
initial begin
 repeat(12)@(negedge ck);rst_n=1;arm;exercise;
 check_on=0;rst_n=0;ret=0;cmd=0;repeat(12)@(negedge ck);rst_n=1;arm;exercise;
 check_on=0;
 if(errs==0&&nexpected==10&&ngot==10)$display("COLLECTIVE_STATUS PASS expected=%0d got=%0d errors=%0d added_cycles=0",nexpected,ngot,errs);
 else $display("COLLECTIVE_STATUS FAIL expected=%0d got=%0d errors=%0d",nexpected,ngot,errs);
 $finish;
end
endmodule
