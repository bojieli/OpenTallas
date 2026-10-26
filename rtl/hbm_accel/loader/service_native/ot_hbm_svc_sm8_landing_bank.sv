`default_nettype none
// One ordinal%8 landing bank: actual response FIFO, local epoch/duplicate
// validation, and one actual two-block 128x256 SRAM. complete_v is the
// combinational last accepted landing event, captured at this stream edge.
// H-DIE 2026-10-15: LBANKS=4 = four 64-row landing blocks in one actual 256x256 SRAM (the steady-state fill latency
// ~150 ns + copy ~68 ns per block needs >=3 blocks in flight for the 99 B/cycle/SM price); LBANKS=2 = the two-block
// 128x256 original.  The response word carries a LB-bit landing index.
module ot_hbm_svc_sm8_landing_bank #(
 parameter [2:0] BANK=0,parameter integer RESPONSE_DEPTH=8,parameter integer LBANKS=2,
 parameter integer LB=(LBANKS>2)?2:1,parameter integer IW=283+LB
)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire in_v,output wire in_ready,input wire [IW-1:0] in_data,
 output wire overflow,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 output wire complete_v,output wire [LB-1:0] complete_bank,output wire fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,
 output wire [255:0] read_data
);
 wire packet_v,packet_take,underflow;wire [IW-1:0] packet;
 ot_hbm_svc_async_fifo #(.WIDTH(IW),.DEPTH(RESPONSE_DEPTH)) u_response(
  .wr_clk(hbm_clk),.wr_rst_n(hbm_rst_n),.wr_valid(in_v),.wr_ready(in_ready),.wr_data(in_data),.wr_overflow(overflow),
  .rd_clk(stream_clk),.rd_rst_n(stream_rst_n),.rd_valid(packet_v),.rd_ready(packet_take),.rd_data(packet),.rd_underflow(underflow));
 reg [LBANKS-1:0] valid_q;reg [15:0] epoch_q[0:LBANKS-1];reg [6:0] count_q[0:LBANKS-1],received_q[0:LBANKS-1];
 reg [63:0] seen_q[0:LBANKS-1];reg sticky;
 wire [10:0] ordinal=packet[IW-1:IW-11];wire [LB-1:0] bank=packet[271+LB:272];wire [15:0] epoch=packet[271:256];
 wire [5:0] row=ordinal[8:3];
 wire identity_ok=valid_q[bank]&&epoch_q[bank]==epoch&&ordinal[2:0]==BANK&&
                 {1'b0,row}<count_q[bank]&&!seen_q[bank][row];
 wire landing_write=packet_v&&!stop&&!sticky&&identity_ok;
 assign packet_take=packet_v&&!stop&&!sticky;
 assign complete_v=landing_write&&received_q[bank]+1'b1==count_q[bank];
 assign complete_bank=bank;assign fault=sticky||underflow;
 integer b;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
   valid_q<=0;sticky<=0;
   for(b=0;b<LBANKS;b=b+1)begin epoch_q[b]<=0;count_q[b]<=0;received_q[b]<=0;seen_q[b]<=0;end
  end else begin
   if(reserve_v)begin
    valid_q[reserve_bank]<=1;epoch_q[reserve_bank]<=reserve_epoch;
    count_q[reserve_bank]<=reserve_total>BANK?(reserve_total+7-BANK)/8:0;
    received_q[reserve_bank]<=0;seen_q[reserve_bank]<=0;
   end
   if(packet_take)begin
    if(!identity_ok)sticky<=1;
    else begin seen_q[bank][row]<=1;received_q[bank]<=received_q[bank]+1'b1;end
   end
  end
 end
 generate if(LBANKS<=2)begin:g_two
 ot_sram_1r1w_128x256_m1_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank[0],read_row}),.rd_out(read_data),
  .w_ce_in(landing_write),.w_addr_in({bank[0],row}),.wd_in(packet[255:0]),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end else begin:g_four
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank,read_row}),.rd_out(read_data),
  .w_ce_in(landing_write),.w_addr_in({bank,row}),.wd_in(packet[255:0]),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
endmodule
`default_nettype wire
