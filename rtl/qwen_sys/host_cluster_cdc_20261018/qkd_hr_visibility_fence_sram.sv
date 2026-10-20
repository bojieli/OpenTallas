// HOST SAFE opt-in: effective8-entry SRAM queue, same-edge head prefetch/bypass; valid-qualified output capture.
// Original CDC fence unchanged. Reset banks preserve existing two-host-edge release; independent sticky causes OR exactly.
`timescale 1ns/1ps
// True controller host-write completions (ack_n) are counted in ck. A held
// snapshot crosses into clk_h using a toggle/ack MCP handshake, so multi-event
// increments cannot tear a Gray word. Done count is the engine cumulative
// sector count. Flop completion storage and control need no ECC or mirrors.
module qkd_hr_visibility_fence_sram #(parameter integer ENABLE=1,MUT=0)(
 input wire rst_n,ck,clk_h,input wire[7:0] ack_n,
 input wire in_v,input wire[63:0] in_d,output reg in_cr,
 output reg out_v,output reg[63:0] out_d,input wire out_cr,
 output wire fault,output wire[31:0] landed_debug
);
 generate if(!ENABLE)begin:g_off
  assign fault=0;assign landed_debug=0;
  always @(*)begin in_cr=0;out_v=0;out_d=0;end
 end else begin:g_on
  reg[31:0] commits,snapshot;reg req;
  reg ack_host,ac1,ac2;reg fc;
  reg rc1,rc2,fc1,fc2;reg[31:0] landed;reg fh_queue,fh_snapshot;wire fh=fh_queue|fh_snapshot;

 reg[7:0]ack_q;reg iv_q,ocr_q,fault_q;reg[63:0]id_q;
 always @(posedge ck or negedge rst_n)if(!rst_n)ack_q<=0;else ack_q<=ack_n;
 always @(posedge clk_h)id_q<=in_d;
 // host-family registers: rst_n (core family) asserts asynchronously and releases synchronised to clk_h
 wire [2:0] rn_bank;wire rn_h=rn_bank[0];
 ot_host_reset_bank #(.N(3)) u_rsh(.clk(clk_h),.async_rst_n(rst_n),.sync_rst_n(rn_bank));
 always @(posedge clk_h or negedge rn_h)if(!rn_h)begin iv_q<=0;ocr_q<=0;fault_q<=0;end
 else begin iv_q<=in_v;ocr_q<=out_cr;fault_q<=fc2|fh;end
  wire[32:0] add={1'b0,commits}+ack_q;
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin commits<=0;snapshot<=0;req<=0;ac1<=0;ac2<=0;fc<=0;end
   else begin
    ac1<=ack_host;ac2<=ac1;
    if(add[32])fc<=1;
    if(!fc)begin
     commits<=add[31:0];
     if(req==ac2&&commits!=snapshot)begin snapshot<=commits;req<=~req;end
    end
   end
  end
  reg[2:0] wp,rp;reg[3:0] count;
  reg[2:0] host_credits;
  wire[63:0] head,mq;wire pop;
  wire write_q=!fh&&!fc2&&iv_q&&!(count==8&&!pop);
  wire[2:0] next_head=rp+3'(pop);
  (* keep *) reg[3:0] same_row;
  reg[63:0] bypass_d;
  always @(posedge clk_h) bypass_d<=id_q;
  for(genvar b=0;b<4;b=b+1)begin:g_bypass
   always @(posedge clk_h or negedge rn_bank[2])
    if(!rn_bank[2])same_row[b]<=0;else same_row[b]<=write_q&&(wp==next_head);
   `ifdef FENCE_MUT_BYPASS
   assign head[16*b+:16]=mq[16*b+:16];
`else
   assign head[16*b+:16]=same_row[b]?bypass_d[16*b+:16]:mq[16*b+:16];
`endif
  end
`ifdef FENCE_MUT_ADDR
  wire[4:0] fence_read_addr={2'b0,next_head^3'b001};
`else
  wire[4:0] fence_read_addr={2'b0,next_head};
`endif
  ot_sram_1r1w_32x64_m1_p192_mir u_queue(.clk(clk_h),.r_ce_in(1'b1),.r_addr_in(fence_read_addr),.rd_out(mq),
   .w_ce_in(write_q),.w_addr_in({2'b0,wp}),.wd_in(id_q),.w_mask_in(64'hffffffffffffffff));
  wire is_done=head[63:56]==8'h01;
  assign pop=count!=0&&host_credits!=0&&!fh&&!fc2&&(!is_done||MUT!=0||landed>=head[31:0]);
  assign fault=fault_q;assign landed_debug=landed;
  // Payload carries meaning only on out_v; enable-free capture avoids broad enables/reset.
  always @(posedge clk_h)out_d<=head;
  always @(posedge clk_h or negedge rn_bank[1])
   if(!rn_bank[1])landed<=0;
   else if(rc2!=ack_host && snapshot>=landed)landed<=snapshot;
  always @(posedge clk_h or negedge rn_bank[2])
   if(!rn_bank[2])fh_snapshot<=0;
   else if(rc2!=ack_host && snapshot<landed)fh_snapshot<=1;
  reg[2:0] nw,nr,nh;reg[3:0] nc;
  always @(posedge clk_h or negedge rn_h)begin
   if(!rn_h)begin rc1<=0;rc2<=0;ack_host<=0;fc1<=0;fc2<=0;fh_queue<=0;
    wp<=0;rp<=0;count<=0;host_credits<=4;in_cr<=0;out_v<=0;
   end else begin
    rc1<=req;rc2<=rc1;fc1<=fc;fc2<=fc1;in_cr<=0;out_v<=0;
    if(rc2!=ack_host)begin
     ack_host<=rc2;
    end
    nw=wp;nr=rp;nc=count;nh=host_credits;
    if(!fh&&!fc2)begin
     if(iv_q)begin
      if(count==8&&!pop)fh_queue<=1;
      else begin nw=wp+1'b1;nc=nc+1'b1;end
     end
     if(ocr_q)begin if(host_credits==4&&!pop)fh_queue<=1;else nh=host_credits+1'b1;end
     if(pop)begin
      out_v<=1;in_cr<=1;nr=rp+1'b1;nc=nc-1'b1;nh=nh-1'b1;
     end
    end
    wp<=nw;rp<=nr;count<=nc;host_credits<=nh;
    if(fh||fc2)begin out_v<=0;in_cr<=0;end
   end
  end
 end endgenerate
endmodule
