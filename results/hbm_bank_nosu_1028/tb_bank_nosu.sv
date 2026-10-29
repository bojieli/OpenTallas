`timescale 1ps/1ps
module tb_bank_nosu;
reg clk=0; always begin #416 clk=1; #417 clk=0; end
reg [16:0] rq0=0;
wire [256:0] ref_rr0, dut_rr0;
reg [16:0] rq1=0;
wire [256:0] ref_rr1, dut_rr1;
reg [16:0] rq2=0;
wire [256:0] ref_rr2, dut_rr2;
reg [16:0] rq3=0;
wire [256:0] ref_rr3, dut_rr3;
reg [16:0] rq4=0;
wire [256:0] ref_rr4, dut_rr4;
reg [280:0] wq0=0;
wire ref_wq_done0, dut_wq_done0;
reg [280:0] wq1=0;
wire ref_wq_done1, dut_wq_done1;
reg [2:0] bid=0;
reg [1:0] sid=0;
reg rst_n=0;
reg rslot_v=0;
reg [2:0] rslot=0;
reg wslot_v=0;
reg [2:0] wslot=0;
reg [280:0] dq=0;
wire ref_dq_done, dut_dq_done;
reg [280:0] kq=0;
wire ref_kq_done, dut_kq_done;
reg [275:0] xq=0;
wire ref_xq_done, dut_xq_done;
reg [275:0] xq2=0;
wire ref_xq2_done, dut_xq2_done;
wire [275:0] ref_eg, dut_eg;
reg [284:0] pq=0;
wire [265:0] ref_pr, dut_pr;
wire [17:0] ref_status, dut_status;
hfd_vms_bank_native_q0_faces u_reference (.clk(clk), .clk_n(clk), .clk_s(clk), .clk_e(clk), .clk_w(clk), .clk_macro0(clk), .clk_macro1(clk), .clk_macro2(clk), .rq0(rq0), .rr0(ref_rr0), .rq1(rq1), .rr1(ref_rr1), .rq2(rq2), .rr2(ref_rr2), .rq3(rq3), .rr3(ref_rr3), .rq4(rq4), .rr4(ref_rr4), .wq0(wq0), .wq_done0(ref_wq_done0), .wq1(wq1), .wq_done1(ref_wq_done1), .bid(bid), .sid(sid), .rst_n(rst_n), .rslot_v(rslot_v), .rslot(rslot), .wslot_v(wslot_v), .wslot(wslot), .dq(dq), .dq_done(ref_dq_done), .kq(kq), .kq_done(ref_kq_done), .xq(xq), .xq_done(ref_xq_done), .xq2(xq2), .xq2_done(ref_xq2_done), .eg(ref_eg), .pq(pq), .pr(ref_pr), .status(ref_status));
hfd_vms_bank_native_q0_faces_nosu dut (.clk(clk), .clk_n(clk), .clk_s(clk), .clk_e(clk), .clk_w(clk), .clk_macro0(clk), .clk_macro1(clk), .clk_macro2(clk), .rr0(dut_rr0), .rq1(rq1), .rr1(dut_rr1), .rq2(rq2), .rr2(dut_rr2), .rq3(rq3), .rr3(dut_rr3), .rq4(rq4), .rr4(dut_rr4), .wq_done0(dut_wq_done0), .wq1(wq1), .wq_done1(dut_wq_done1), .bid(bid), .sid(sid), .rst_n(rst_n), .rslot_v(rslot_v), .rslot(rslot), .wslot_v(wslot_v), .wslot(wslot), .dq(dq), .dq_done(dut_dq_done), .kq(kq), .kq_done(dut_kq_done), .xq(xq), .xq_done(dut_xq_done), .xq2(xq2), .xq2_done(dut_xq2_done), .eg(dut_eg), .pq(pq), .pr(dut_pr), .status(dut_status));
integer checks=0, reads=0, writes=0, cycle=0;
reg mutate=0, illegal=0;
reg [256:0] observed;
function automatic [255:0] payload(input integer r);
 for(integer w=0;w<8;w=w+1)payload[w*32+:32]=32'h3481beaf ^ (r<<9) ^ w;
endfunction
task automatic clear;
 begin rq1=0;rq2=0;rq3=0;rq4=0;wq1=0;dq=0;kq=0;xq=0;xq2=0;pq=0;rslot_v=0;wslot_v=0; end
endtask
task automatic tick;
 begin
 @(posedge clk); #20; cycle=cycle+1;
 if(rst_n)begin
   if(!illegal && ref_status !== dut_status)$fatal(1,"status mismatch");
   if(!illegal && ref_status !== 0)$fatal(1,"unexpected bank fault");
   if(ref_wq_done1 !== dut_wq_done1 || ref_dq_done !== dut_dq_done || ref_kq_done !== dut_kq_done ||
      ref_xq_done !== dut_xq_done || ref_xq2_done !== dut_xq2_done || ref_wq_done0 !== dut_wq_done0)
     $fatal(1,"completion mismatch");
   if(dut_wq_done1)writes=writes+1;

   observed=dut_rr0;
   if(mutate && 0==1 && observed[256])observed[31:0]=observed[31:0]^1;
   if(ref_rr0[256] !== observed[256])$fatal(1,"group0 valid mismatch");
   if(ref_rr0[256])begin
     if(ref_rr0 !== observed)$fatal(1,"group0 payload mismatch");
     reads=reads+1;
   end
   checks=checks+1;

   observed=dut_rr1;
   if(mutate && 1==1)observed=dut_rr2;
   if(ref_rr1[256] !== observed[256])$fatal(1,"group1 valid mismatch");
   if(ref_rr1[256])begin
     if(ref_rr1 !== observed)$fatal(1,"group1 payload mismatch");
     reads=reads+1;
   end
   checks=checks+1;

   observed=dut_rr2;
   if(mutate && 2==1 && observed[256])observed[31:0]=observed[31:0]^1;
   if(ref_rr2[256] !== observed[256])$fatal(1,"group2 valid mismatch");
   if(ref_rr2[256])begin
     if(ref_rr2 !== observed)$fatal(1,"group2 payload mismatch");
     reads=reads+1;
   end
   checks=checks+1;

   observed=dut_rr3;
   if(mutate && 3==1 && observed[256])observed[31:0]=observed[31:0]^1;
   if(ref_rr3[256] !== observed[256])$fatal(1,"group3 valid mismatch");
   if(ref_rr3[256])begin
     if(ref_rr3 !== observed)$fatal(1,"group3 payload mismatch");
     reads=reads+1;
   end
   checks=checks+1;

   observed=dut_rr4;
   if(mutate && 4==1 && observed[256])observed[31:0]=observed[31:0]^1;
   if(ref_rr4[256] !== observed[256])$fatal(1,"group4 valid mismatch");
   if(ref_rr4[256])begin
     if(ref_rr4 !== observed)$fatal(1,"group4 payload mismatch");
     reads=reads+1;
   end
   checks=checks+1;

   if(ref_pr[265] !== dut_pr[265] || (ref_pr[265] && ref_pr !== dut_pr))$fatal(1,"packet mismatch");
   if(ref_eg[275] !== dut_eg[275] || (ref_eg[275] && ref_eg !== dut_eg))$fatal(1,"egress mismatch");
 end
 @(negedge clk); #1;
 end
endtask
integer row,g;
initial begin
 mutate=$test$plusargs("MUT_RESPONSE");
 repeat(5)tick;rst_n=1;repeat(8)tick;
 // One physical bank, original and specialized, real three-SRAM body each.
 // Exercise32 native rows and32 mirror rows through live client1 writes.
 for(integer mirror=0;mirror<2;mirror=mirror+1)begin
  for(row=0;row<32;row=row+1)begin
   clear;wslot_v=1;wslot=1;
   wq1={1'b1,1'(mirror),2'd0,10'(row),3'd0,payload(row+1024*mirror),8'hff};tick;
  end
  clear;repeat(10)tick;
  for(row=0;row<32;row=row+1)for(g=1;g<=4;g=g+1)begin
   clear;rslot_v=1;rslot=3'(g);
   case(g)
    1:rq1={1'b1,1'(mirror),2'd0,10'(row),3'd0};
    2:rq2={1'b1,1'(mirror),2'd0,10'(row),3'd0};
    3:rq3={1'b1,1'(mirror),2'd0,10'(row),3'd0};
    4:rq4={1'b1,1'(mirror),2'd0,10'(row),3'd0};
   endcase
   tick;
  end
  clear;repeat(10)tick;
 end
 if(reads!=256 || writes!=64)$fatal(1,"unobserved SRAM path reads%0d writes%0d",reads,writes);
 if($test$plusargs("FORBID_READ") || $test$plusargs("FORBID_WRITE"))begin
  illegal=1;clear;
  if($test$plusargs("FORBID_READ"))begin rslot_v=1;rslot=0;end
  else begin wslot_v=1;wslot=0;end
  tick;clear;repeat(4)tick;
  if(!dut_status[17])$fatal(1,"absent client calendar grant accepted");
  $display("NOSU_FORBIDDEN_GRANT CAUGHT");
 end
 $display("NOSU_LOCKSTEP PASS checks%0d reads%0d writes%0d cycles%0d",checks,reads,writes,cycle);
 $finish;
end
endmodule
