`timescale 1ns/1ps
module tb_qfd_collective_status;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[115:0] cmd=0;reg[1037:0] ret=0;wire[106:0] st;wire[9:0] ag;
qfd_dv_slice2 p(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i(453'b0),.rs_s(1028'b0),.rs_n(1028'b0),.l9_i(514'b0),.st_up_i(1088'b0),.st_dn_i(1088'b0),.sc_up_i(48'b0),.sc_dn_i(48'b0),.ch_up_i(1095'b0),.ch_dn_i(ret),.ag_up_i(10'b0),.st(st),.ag_dn_o(ag));
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
initial begin
 repeat(8)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
 cmd=(116'hf<<112)|116'd15;@(negedge ck);cmd=0;repeat(5)@(negedge ck);
 cmd=(116'hf<<112)|(116'd1<<52)|116'd9;@(negedge ck);cmd=0;repeat(5)@(negedge ck);check_on=1;
 // A terminal word followed by idle.
 beat(1,1);beat(0,0);repeat(5)@(negedge ck);
 // Consecutive multiword return followed by idle.
 beat(1,0);beat(1,0);beat(1,1);beat(0,0);repeat(5)@(negedge ck);
 // Bubbles inside a return and back-to-back one-word message boundaries.
 beat(1,0);beat(0,0);beat(1,1);beat(0,0);beat(1,1);beat(1,1);beat(0,0);repeat(6)@(negedge ck);
 check_on=0;
 if(errs==0&&nexpected==5&&ngot==5)$display("COLLECTIVE_STATUS PASS expected=%0d got=%0d errors=%0d added_cycles=0",nexpected,ngot,errs);
 else $display("COLLECTIVE_STATUS FAIL expected=%0d got=%0d errors=%0d",nexpected,ngot,errs);
 $finish;
end
endmodule
