`timescale 1ns/1ps
// Actual native bank and three real SRAM macros. This coupon observes macro
// commit pins and reads back through rq0/rr0; it never peeks SRAM contents.
module native_vm_warm_coupon #(parameter integer MUT_RESET=0)(input wire clk, cold_rst_n, enable, queued_valid,
 input wire [280:0] kq, output reg warm_reset=0, output reg done=0);
 wire rst_n=cold_rst_n&&!warm_reset;
 reg [16:0] rq0=0; wire [256:0] rr0; wire [17:0] status; wire kq_done;
 hfd_vms_bank_native_q0_faces bank(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
 .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(MUT_RESET ? cold_rst_n : rst_n),.bid(3'd0),.sid(2'd3),
 .rslot_v(1'b1),.rslot(3'd0),.wslot_v(1'b1),.wslot(3'd2),
 .rq0(rq0),.rr0(rr0),.rq1(17'd0),.rr1(),.rq2(17'd0),.rr2(),.rq3(17'd0),.rr3(),.rq4(17'd0),.rr4(),
 .wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.dq(281'd0),.dq_done(),
 .kq(kq),.kq_done(kq_done),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status));
 reg [15:0] sectors[0:3];
 wire wa=bank.u_ot_pr_core.bank.u_a.w_ce_in;
 wire wb=bank.u_ot_pr_core.bank.u_b.w_ce_in;
 wire wc=bank.u_ot_pr_core.bank.u_c.w_ce_in;
 wire [9:0] addr=bank.u_ot_pr_core.bank.u_a.w_addr_in;
 wire [255:0] data=bank.u_ot_pr_core.bank.u_a.wd_in;
 wire [255:0] mask=bank.u_ot_pr_core.bank.u_a.w_mask_in;
 reg [255:0] gold[0:1023]; reg [15:0] sector[0:1023]; bit touched[0:1023];
 integer commits=0,readbacks=0; reg forbid=0;
 always @(posedge clk)begin
  sectors[0]<=kq[279:264];for(integer j=1;j<4;j++)sectors[j]<=sectors[j-1];
  if(enable&&forbid&&(wa||wb||wc))$fatal(1,"WARM_QUEUED_STALE_MACRO_COMMIT wa%0b wb%0b wc%0b",wa,wb,wc);
  if(wa)begin
   if(mask!=={256{1'b1}})$fatal(1,"WARM_COUPON_NONFULL_MASK");
   gold[addr]=data;sector[addr]=sectors[3];touched[addr]=1;commits++;
  end
 end
 initial begin
  for(integer j=0;j<1024;j++)touched[j]=0;
  wait(enable);wait(cold_rst_n);
  // At least two actual macro commits precede a queued outer RING publish.
  do @(negedge clk);while(!(queued_valid&&commits>=2&&bank.kq__ot_q[280]));
  forbid=1;warm_reset=1;
  repeat(66)@(negedge clk);
  warm_reset=0;
  // Inputs/outputs of the face remain unreset; real downstream reset is used.
  repeat(66)@(negedge clk);
  if(status!==18'd0)$fatal(1,"WARM_NATIVE_BANK_STATUS %h",status);
  for(integer a=0;a<1024;a++)if(touched[a])begin
   rq0={1'b1,sector[a]};@(negedge clk);rq0=0;
   repeat(7)@(negedge clk);
   if(rr0[256]!==1'b1||rr0[255:0]!==gold[a])$fatal(1,"WARM_RETAINED_READBACK a%0d sec%h valid%0b got%h want%h",a,sector[a],rr0[256],rr0[255:0],gold[a]);
   readbacks++;repeat(2)@(negedge clk);
  end
  $display("WARM_QUEUED_NATIVE_VM_PASS commits%0d retained_readbacks%0d no_postreset_macro_writes1",commits,readbacks);done=1;
 end
endmodule
