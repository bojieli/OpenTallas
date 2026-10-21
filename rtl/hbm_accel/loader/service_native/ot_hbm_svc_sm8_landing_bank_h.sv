`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED ot_hbm_svc_sm8_landing_bank (LBANKS 4: one 256x256 SRAM = four 64-row landing
// blocks; that module stays byte-identical).  Same identity checks (epoch, ordinal%8 bank, row < count, duplicate),
// same faults.  Changes:
//   * response FIFO = ot_hbm_svc_async_fifo_oh (registered one-hot slot selects, no 570-load decode / mux nets);
//   * SRAM write port from STREAM flops (as the fg2 WREG=1 master): the accepted word lands one stream edge later and
//     complete_v is registered with it (landing -> resident +1 stream edge, before the elastic block_ready); a macro pin
//     then reads only stream-family flops (reviewed_gray_fifos);
//   * the reserve arrives REGISTERED (the producer's per-bank copy) and is registered once more here into KEPT per-slot
//     enable copies (each <= 32 flops): a block's bank state is set 2 stream edges after its reserve (the first response
//     of a block needs the descriptor crossing + DRAM, >> 2 edges; a bank is only re-reserved after its drain);
//   * reset only on control (valid, sticky, write strobe, completion, reserve enables) from ot_rst_fanout leaves.
module ot_hbm_svc_sm8_landing_bank_h #(
 parameter [2:0] BANK=0,parameter integer RESPONSE_DEPTH=8,parameter integer LBANKS=4,
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
 initial if(LBANKS!=4)$fatal(1,"landing_bank_h: LBANKS 4 (one 256x256 macro)");
 wire[3:0]hr;wire[4:0]sr;
 ot_rst_fanout #(.N(4)) u_hr(.clk(hbm_clk),.rst_n_in(hbm_rst_n),.rst_n(hr));
 ot_rst_fanout #(.N(5)) u_sr(.clk(stream_clk),.rst_n_in(stream_rst_n),.rst_n(sr));
 wire packet_v,packet_take,underflow;wire [IW-1:0] packet;
 ot_hbm_svc_async_fifo_oh #(.WIDTH(IW),.DEPTH(RESPONSE_DEPTH),.NRW(4),.NRR(4)) u_response(
  .wr_clk(hbm_clk),.wr_rst_n(hr),.wr_valid(in_v),.wr_ready(in_ready),.wr_data(in_data),.wr_overflow(overflow),
  .rd_clk(stream_clk),.rd_rst_n(sr[3:0]),.rd_valid(packet_v),.rd_ready(packet_take),.rd_data(packet),.rd_underflow(underflow));
 // reserve stage 2: KEPT per-slot enables [slot*4+c] (c0: valid/epoch/count 24, c1/c2: seen halves 32, c3: received 7)
 (* keep="true",dont_touch="true" *) reg[LBANKS*4-1:0]ren_k;
 reg[15:0]r_epoch;reg[6:0]r_count;
 reg [LBANKS-1:0] valid_q;reg [15:0] epoch_q[0:LBANKS-1];reg [6:0] count_q[0:LBANKS-1],received_q[0:LBANKS-1];
 reg [63:0] seen_q[0:LBANKS-1];reg sticky;
 wire [10:0] ordinal=packet[IW-1:IW-11];wire [LB-1:0] bank=packet[271+LB:272];wire [15:0] epoch=packet[271:256];
 wire [5:0] row=ordinal[8:3];
 wire identity_ok=valid_q[bank]&&epoch_q[bank]==epoch&&ordinal[2:0]==BANK&&
                 {1'b0,row}<count_q[bank]&&!seen_q[bank][row];
 wire landing_write=packet_v&&!stop&&!sticky&&identity_ok;
 assign packet_take=packet_v&&!stop&&!sticky;
 wire complete_now=landing_write&&received_q[bank]+1'b1==count_q[bank];
 reg w_ce_q,cmp_q;reg [LB-1:0] w_bank_q;reg [5:0] w_row_q;reg [255:0] w_data_q;
 assign complete_v=cmp_q;assign complete_bank=w_bank_q;assign fault=sticky||underflow;
 integer b,c;
 always @(posedge stream_clk or negedge sr[4])begin
  if(!sr[4])begin valid_q<=0;sticky<=0;w_ce_q<=0;cmp_q<=0;ren_k<=0;end
  else begin
   w_ce_q<=landing_write;cmp_q<=complete_now;
   for(b=0;b<LBANKS;b=b+1)for(c=0;c<4;c=c+1)ren_k[b*4+c]<=reserve_v&&reserve_bank==b;
   for(b=0;b<LBANKS;b=b+1)if(ren_k[b*4])valid_q[b]<=1;
   if(packet_take&&!identity_ok)sticky<=1;
  end
 end
 always @(posedge stream_clk)begin
  r_epoch<=reserve_epoch;r_count<=reserve_total>BANK?7'((reserve_total+7-BANK)/8):7'd0;
  w_bank_q<=bank;w_row_q<=row;w_data_q<=packet[255:0];
  for(b=0;b<LBANKS;b=b+1)begin
   if(ren_k[b*4])begin epoch_q[b]<=r_epoch;count_q[b]<=r_count;end
   if(ren_k[b*4+1])seen_q[b][31:0]<=0;
   if(ren_k[b*4+2])seen_q[b][63:32]<=0;
   if(ren_k[b*4+3])received_q[b]<=0;
  end
  if(packet_take&&identity_ok)begin seen_q[bank][row]<=1;received_q[bank]<=received_q[bank]+1'b1;end
 end
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(
  .clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank,read_row}),.rd_out(read_data),
  .w_ce_in(w_ce_q),.w_addr_in({w_bank_q,w_row_q}),.wd_in(w_data_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
endmodule
`default_nettype wire
