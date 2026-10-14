`timescale 1ns/1ps
module tb_dsfd_vm_bank_reset_ack;
 reg ck=0, cq=0, ct=0, req=0;
 reg enb=1,enq=1,ent=1;
 always #5 if(enb) ck=~ck;
 always #5 if(enq) cq=~cq;
 always #5 if(ent) ct=~ct;
 wire [2:0] ack; wire flat_ack;
 dsfd_vm_bgl #(.NP(28),.NPR(10),.NB(32),.NBL(8),.QD(4),.RQ(8),.MACRO(0),.DW(128),.CLOCK_SPLIT(1),.PREHIT(1),.FAST4(1),.FORWARD_HOP(2)) u_mc
 (.ck(ck),.ck_req(cq),.ck_ret(ct),.rs(req),.grp(2'd0),.bi(3'd0),.i_v(28'd0),.i_we(28'd0),.i_row(392'd0),.i_mask(112'd0),.i_d(3584'd0),.r_v(10'd0),.r_d(1280'd0),.r_f(4'd0),.r_o(3'd0),.reset_ack(ack));
 dsfd_vm_bgr #(.NP(28),.NPR(10),.NB(32),.NBL(8),.QD(4),.RQ(8),.MACRO(0),.DW(128),.NSTG(4),.EP(2)) u_flat
 (.ck(ck),.rs(req),.grp(2'd0),.i_v(28'd0),.i_we(28'd0),.i_row(392'd0),.i_mask(112'd0),.i_d(3584'd0),.r_v(10'd0),.r_d(1280'd0),.r_f(4'd0),.r_o(3'd0),.reset_ack(flat_ack));
 // Fault injection only on an independent helper: a missed final conditioner
 // must remain unacknowledged even if the epoch request has released.
 reg missed_req=0, missed_local=1; wire missed_ack;
 dsfd_vm_reset_ack u_missed (.clk(ck),.request_n(missed_req),.local_release(missed_local),.consumer_live(1'b1),.ack(missed_ack));
 initial begin
  #2; req=1; missed_req=1;
  #40; if(ack!==3'b111 || flat_ack!==1'b1) $fatal(1,"running consumers did not acknowledge");
  if(missed_ack!==1'b0) $fatal(1,"missed conditioner was acknowledged");
  for(int k=0;k<3;k++) begin
   @(negedge ck); #1;
   case(k) 0:enb=0; 1:enq=0; 2:ent=0; endcase
   req=0; #1; if(ack!==0 || flat_ack!==0) $fatal(1,"epoch request failed to clear ACK asynchronously");
   req=1; #40;
   if(ack[k]!==0) $fatal(1,"stopped domain acknowledged");
   for(int j=0;j<3;j++) if(j!=k && ack[j]!==1) $fatal(1,"running peer failed to acknowledge");
   if(k==0 && flat_ack!==0) $fatal(1,"stopped production flat root acknowledged");
   case(k) 0:enb=1; 1:enq=1; 2:ent=1; endcase
   #40; if(ack!==3'b111 || flat_ack!==1) $fatal(1,"resumed domain failed to acknowledge");
  end
  $display("BANK_RESET_ACK PASS NP28 flatEP2 and native3roots; stopped domain reset pulse + missed conditioner"); $finish;
 end
endmodule
