`timescale 1ns/1ps
// Fixed-cycle transport storage. Both address streams and slot enables come
// from the compiler schedule; runtime validity and publication checks only
// latch faults. They never suppress, advance, retry or reschedule a transfer.
// Fixed latency: write slot at w0 writes SRAM at w1; read slot at r0 launches
// data/valid at r3. The schedule includes reset release and version-sync delay.
module qfd_static_ch546 (
 input wire wck,rck,rst_n,
 input wire w_slot,input wire [5:0] w_addr,input wire w_version,
 input wire i_valid,input wire [545:0] i_data,
 input wire r_slot,input wire [5:0] r_addr,input wire r_version,
 output reg o_valid,output reg [545:0] o_data,
 output reg w_fault,r_fault);
 wire w_rst_n,r_rst_n,r_pub_rst_n;
 // One reset capture point per domain. The compiler starts its calendar
 // after the fixed two-edge deassertion guard in both domains; reset does
 // not fan from a die pin across the whole publication checker.
 ot_reset_sync u_wreset(.clk(wck),.async_rst_n(rst_n),.sync_rst_n(w_rst_n));
 // Two kept second-stage copies retain the same two-edge release while
 // separating the 256 publication synchronizer flops from the read control.
 (* async_reg="true" *) reg r_reset_meta;
 (* async_reg="true", keep="true", dont_touch="true" *) reg [1:0] r_reset_q;
 always @(posedge rck or negedge rst_n) begin
  if(!rst_n) begin r_reset_meta<=0;r_reset_q<=0;end
  else begin r_reset_meta<=1;r_reset_q<={2{r_reset_meta}};end
 end
 assign r_rst_n=r_reset_q[0];assign r_pub_rst_n=r_reset_q[1];
 reg wp,rp;reg [5:0] wa,ra;reg wv,rv;
 reg [545:0] wd,rd_stage;
 reg [63:0] published, seen;
 (* async_reg="true" *) reg [63:0] pub_meta,pub_sync,seen_meta,seen_sync;
 reg [2:0] read_pipe;
 wire [545:0] memory_data;
 always @(posedge wck or negedge w_rst_n) begin
  if(!w_rst_n) begin wp<=0;w_fault<=0;published<=0;seen<=0;wv<=0;end
  else begin
   wp<=w_slot;wv<=w_version;
   if(wp) begin published[wa]<=wv;seen[wa]<=1;end
   w_fault<=w_fault | (w_slot && (i_valid !== 1'b1));
  end
 end
 always @(posedge wck) begin wa<=w_addr;wd<=i_data;end
 always @(posedge rck or negedge r_rst_n) begin
  if(!r_rst_n) begin rp<=0;rv<=0;read_pipe<=0;o_valid<=0;r_fault<=0;end
  else begin
   rp<=r_slot;rv<=r_version;read_pipe<={read_pipe[1:0],r_slot};
`ifdef OT_STATIC_MUT_LATENCY
   o_valid<=read_pipe[1];
`else
   o_valid<=read_pipe[2];
`endif
   r_fault<=r_fault | (rp && (seen_sync[ra] !== 1'b1 || pub_sync[ra] !== rv));
  end
 end
 always @(posedge rck or negedge r_pub_rst_n) begin
  if(!r_pub_rst_n) begin pub_meta<=0;pub_sync<=0;seen_meta<=0;seen_sync<=0;end
  else begin pub_meta<=published;pub_sync<=pub_meta;seen_meta<=seen;seen_sync<=seen_meta;end
 end
 always @(posedge rck) begin ra<=r_addr;rd_stage<=memory_data;o_data<=rd_stage;end
 // The SRAM enables are delayed compiler slots. No validity, FIFO-full,
 // FIFO-empty, credit or ready flag participates in this datapath.
 ot_sram_1r1w2c_64x546_m1 u_mem (
 .wclk(wck),.rclk(rck),.r_ce_in(rp),.r_addr_in(ra),.rd_out(memory_data),
 .w_ce_in(wp),.w_addr_in(wa),.wd_in(wd),.w_mask_in({546{1'b1}}));
endmodule
