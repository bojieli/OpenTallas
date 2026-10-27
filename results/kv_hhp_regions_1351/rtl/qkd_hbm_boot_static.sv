`timescale 1ns/1ps
// Dedicated pin-registered arbiter for cold boot vs the production static path.
// Scratch row0 lies outside host KV rows64..99 and embedding rows24427..24575.
// Normal traffic is released only after both real readbacks pass. This leaf
// adds one registered edge each way on the normal static path (must be priced).
module qkd_hbm_boot_static #(parameter integer TIMEOUT=20000,MUT=0)(
 input wire ck,ck_test,rst_n,boot_go,
 input wire[287:0]normal_es,output reg[260:0]normal_er,
 output reg[287:0]ctrl_es,input wire[260:0]ctrl_er,
 output wire boot_done,boot_ok,output wire[3:0]boot_cause,
 output reg fault,
 // Q-KVFIX 0130 (native launch, owner 10-16 register-every-pin): duplicates of ctrl_es[0] / ctrl_es[286] (same D, same
 // edge) for in-tile observers, so the ctrl_es pin flops drive only their pins.  Zero cycles; leave open if unused.
 output reg launch_v,launch_we);
 wire[287:0]test_es;reg[260:0]test_er;wire test_busy,test_ok;
 assign boot_ok=test_ok&&!fault;
 qkd_hbm_boot_pc #(.TIMEOUT(TIMEOUT),.MUT(MUT))u_test(
 .ck(ck_test),.rst_n(rst_n),.start(boot_go),.bank(5'd3),.col(5'd2),.row(19'd0),
 .es(test_es),.er(test_er),.busy(test_busy),.done(boot_done),.ok(test_ok),.cause(boot_cause));
 wire normal=boot_done&&boot_ok;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin ctrl_es<=0;normal_er<=0;test_er<=0;fault<=0;launch_v<=0;launch_we<=0;end
  else begin
   ctrl_es<=normal?normal_es:test_es;
   launch_v<=normal?normal_es[0]:test_es[0];launch_we<=normal?normal_es[286]:test_es[286];
   normal_er<=normal?ctrl_er:261'b0;
   test_er<=normal?261'b0:ctrl_er;
   if(!normal&&normal_es[0])fault<=1;
  end
 end
endmodule
