`timescale 1ns/1ps
// Exceptional initialization transport only. Actual authenticated HOST replay
// never stalls: a full FIFO faults/aborts setup. Ready/valid drains ONLY boot
// traffic; this module is absent from all normal token/control issue paths.
// Independent domain resets share an asynchronous source via ot_async_fifo's
// explicit EXT_RST0 conditioners. Applied is HBM-domain, and requires real
// synchronization before the core dispatcher sees it. Child faults must also
// be observed; applied certifies transport age, not successful child semantics.
module qkd_static_kv_boot_cdc #(parameter integer HAS_SEAL=0,MUT=0)(
 input wire ck,rst_n,hck,hrst_n,
 input wire cfg_we,input wire[7:0]cfg_addr,input wire[63:0]cfg_data,input wire cfg_last,
 output reg sink_we,output reg[7:0]sink_addr,output reg[63:0]sink_data,output reg sink_seal,
 output reg applied_hbm,output reg fault_core,output reg fault_hbm
);
 initial if(HAS_SEAL!=0&&HAS_SEAL!=1)$fatal(1,"explicit boot seal law required");
 wire ready,valid,overflow,underflow;wire[72:0]word;
 reg sealed_source;reg seal_pending,finish1,finish2;
 ot_async_fifo #(.WIDTH(73),.DEPTH(16),.EXT_RST(0))u_fifo(
 .wr_clk(ck),.wr_rst_n(rst_n),.wr_valid(cfg_we&&!sealed_source&&!fault_core),.wr_ready(ready),
 .wr_data({cfg_last,cfg_addr,cfg_data}),.wr_overflow(overflow),
 .rd_clk(hck),.rd_rst_n(hrst_n),.rd_valid(valid),.rd_ready(!seal_pending&&!applied_hbm),
 .rd_data(word),.rd_underflow(underflow));
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin sealed_source<=0;fault_core<=0;end
  else begin
   if(overflow||(cfg_we&&(!ready||sealed_source)))fault_core<=1;
   if(cfg_we&&cfg_last)sealed_source<=1;
  end
 end
 always @(posedge hck or negedge hrst_n)begin
  if(!hrst_n)begin sink_we<=0;sink_addr<=0;sink_data<=0;sink_seal<=0;applied_hbm<=0;fault_hbm<=0;seal_pending<=0;finish1<=0;finish2<=0;end
  else begin
   sink_we<=0;sink_seal<=0;finish1<=seal_pending;finish2<=finish1;
   if(underflow)fault_hbm<=1;
   if(seal_pending)begin sink_seal<=1'(HAS_SEAL);seal_pending<=0;end
   if(finish2)applied_hbm<=1;
   if(valid&&!seal_pending&&!applied_hbm)begin
    sink_we<=1;sink_addr<=word[71:64]^((MUT==1)?8'd1:8'd0);sink_data<=word[63:0];
    if(word[72])seal_pending<=1;
   end
   if(MUT==2&&valid)applied_hbm<=1;
  end
 end
endmodule

// Real terminal boot observations; each HBM status passes2 FF into the core
// owner. The final status register adds1 core edge. Error flags stay sticky at
// their producer; no pulse crossing is inferred here.
module qkd_static_kv_boot_observe(
 input wire ck,rst_n,input wire[159:0]applied_hbm,fault_hbm,fault_leaf_core,
 output reg[159:0]applied_core,output reg fault_core
);
 (* async_reg="true" *)reg[159:0]a1,a2,f1,f2,c1,c2;
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin a1<=0;a2<=0;f1<=0;f2<=0;c1<=0;c2<=0;applied_core<=0;fault_core<=0;end
 else begin a1<=applied_hbm;a2<=a1;f1<=fault_hbm;f2<=f1;c1<=fault_leaf_core;c2<=c1;
  applied_core<=a2;fault_core<=fault_core||(|f2)||(|c2);end
 end
endmodule
