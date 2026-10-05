`timescale 1ns/1ps
// Finite aligned RF provider. 512 vectors of 128 FP32 lanes, two physical
// 1R1W operand copies. No read-during-write semantics are assumed. Response
// registers lease all banks until consumption; mirrored ACK is registered
// after both copies' write edge. Persistent competing read/write alternate.
module ot_gpu_rf_service (
 input wire clk, rst_n,
 input wire rd_valid, output wire rd_ready,
 input wire [8:0] rd_a, rd_b,
 output reg rsp_valid, input wire rsp_ready,
 output reg [4095:0] rsp_a, rsp_b,
 input wire wr_valid, output wire wr_ready,
 input wire [8:0] wr_addr, input wire [4095:0] wr_data,
 output reg ack_valid, input wire ack_ready
);
 reg read_pending, prefer_write;
 reg [1:0] page_a, page_b;
 wire idle = rst_n && !read_pending && !rsp_valid && !ack_valid;
 assign rd_ready = idle && (!wr_valid || !prefer_write);
 assign wr_ready = idle && (!rd_valid || prefer_write);
 wire read_go = rd_valid && rd_ready;
 wire write_go = wr_valid && wr_ready;
 wire [4095:0] words_a [0:3];
 wire [4095:0] words_b [0:3];
 genvar p,b;
 generate for(p=0;p<4;p=p+1) begin:g_page
  for(b=0;b<16;b=b+1) begin:g_bank
   ot_sram_1r1w_128x256_m1_r2c2 u_operand_a (
    .clk(clk),.r_ce_in(read_go && rd_a[8:7]==p),.r_addr_in(rd_a[6:0]),.rd_out(words_a[p][b*256+:256]),
    .w_ce_in(write_go && wr_addr[8:7]==p),.w_addr_in(wr_addr[6:0]),.wd_in(wr_data[b*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(16'd0));
   ot_sram_1r1w_128x256_m1_r2c2 u_operand_b (
    .clk(clk),.r_ce_in(read_go && rd_b[8:7]==p),.r_addr_in(rd_b[6:0]),.rd_out(words_b[p][b*256+:256]),
    .w_ce_in(write_go && wr_addr[8:7]==p),.w_addr_in(wr_addr[6:0]),.wd_in(wr_data[b*256+:256]),
    .w_mask_in({256{1'b1}}),.rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(16'd0));
  end
 end endgenerate
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   read_pending<=0; rsp_valid<=0; ack_valid<=0; prefer_write<=0; page_a<=0;page_b<=0;
  end else begin
   read_pending<=read_go;
   if(read_go) begin page_a<=rd_a[8:7];page_b<=rd_b[8:7];prefer_write<=1;end
   if(read_pending) begin rsp_a<=words_a[page_a];rsp_b<=words_b[page_b];rsp_valid<=1;end
   else if(rsp_valid && rsp_ready) rsp_valid<=0;
   if(write_go) begin ack_valid<=1;prefer_write<=0;end
   else if(ack_valid && ack_ready) ack_valid<=0;
  end
 end
endmodule
