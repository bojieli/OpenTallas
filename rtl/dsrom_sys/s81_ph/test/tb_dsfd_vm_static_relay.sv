`timescale 1ns/1ps
`ifndef RELAY_NB
`define RELAY_NB 4
`endif
module tb_dsfd_vm_static_relay;
 localparam integer N=`RELAY_NB;
 reg ck=0,rst_n=0; always #0.417 ck=~ck;
 reg [168*N-1:0] request=0;wire [168*N-1:0] qrequest;
 reg [159*N-1:0] response=0;wire [159*N-1:0] qresponse;
 // One common PLL edge, two distinct real clock pins; data never crosses roots.
`define VM_RELAY_PORTS .ck_req(ck),.ck_rsp(ck),.rst_n(rst_n),\
 .i_rv(request[0+:N]),.i_wv(request[N+:N]),.i_ra(request[2*N+:9*N]),.i_wa(request[11*N+:9*N]),\
 .i_rt(request[20*N+:8*N]),.i_wt(request[28*N+:8*N]),.i_wm(request[36*N+:4*N]),.i_wd(request[40*N+:128*N]),\
 .o_rv(qrequest[0+:N]),.o_wv(qrequest[N+:N]),.o_ra(qrequest[2*N+:9*N]),.o_wa(qrequest[11*N+:9*N]),\
 .o_rt(qrequest[20*N+:8*N]),.o_wt(qrequest[28*N+:8*N]),.o_wm(qrequest[36*N+:4*N]),.o_wd(qrequest[40*N+:128*N]),\
 .i_sv(response[0+:N]),.i_cv(response[N+:N]),.i_sd(response[2*N+:128*N]),.i_st(response[130*N+:8*N]),\
 .i_ct(response[138*N+:8*N]),.i_ca(response[146*N+:9*N]),.i_cm(response[155*N+:4*N]),\
 .o_sv(qresponse[0+:N]),.o_cv(qresponse[N+:N]),.o_sd(qresponse[2*N+:128*N]),.o_st(qresponse[130*N+:8*N]),\
 .o_ct(qresponse[138*N+:8*N]),.o_ca(qresponse[146*N+:9*N]),.o_cm(qresponse[155*N+:4*N])
 generate if(N==4)begin dsfd_vm_static_relay128_b4 dut(`VM_RELAY_PORTS);end
 else begin dsfd_vm_static_relay128_b8 dut(`VM_RELAY_PORTS);end endgenerate
 integer cyc,k,bad=0;reg [168*N-1:0] previous_request;reg [159*N-1:0] previous_response;
 initial begin
  repeat(4) @(negedge ck);rst_n=1;
  repeat(5) @(negedge ck);
  for(cyc=0;cyc<1000;cyc=cyc+1)begin
   previous_request=qrequest;previous_response=qresponse;
   for(k=0;k<168*N;k=k+32)request[k+:32]=$random;
   for(k=0;k<159*N;k=k+32)response[k+:32]=$random;
   #0.05;
   if(qrequest!==previous_request||qresponse!==previous_response)bad=bad+1; // actual registered pins
   @(posedge ck);#0.05;
   if(qrequest!==request||qresponse!==response)begin bad=bad+1;if(bad<4)$display("relay mismatch cycle %0d",cyc);end
   @(negedge ck);
  end
  if(bad)begin $display("TB_VM_RELAY FAIL banks %0d cycles %0d bad %0d",N,cyc,bad);$fatal(1);end
  $display("TB_VM_RELAY PASS banks %0d cycles %0d bitchecks %0d",N,cyc,cyc*327*N);$finish;
 end
endmodule
