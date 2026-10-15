`default_nettype none
// Opt-in successor mechanism, not a replacement band ABI. HBM responses alone
// may arrive at variable times. After one ready check per block, start reserves
// exactly 64 consecutive read slots. No per-lane credits or output ready exist.
// begin/fill are PHY-boundary operations; start is a compiler-scheduled pulse.
module ot_hbm_svc_static_landing (
 input wire clk, rst_n,
 input wire begin_v, begin_bank, input wire [15:0] begin_epoch,
 input wire [31:0] fill_v, input wire [31:0] fill_bank,
 input wire [32*6-1:0] fill_slot, input wire [32*16-1:0] fill_epoch,
 input wire [8191:0] fill_data,
 output wire [1:0] block_ready,
 input wire start, start_bank, input wire [15:0] start_epoch,
 output reg out_v, output reg out_bank, output reg [5:0] out_slot,
 output wire [8191:0] out_data, output reg [15:0] out_epoch,
 output wire busy, output wire fault
);
 reg [1:0] owned;
 reg [15:0] epoch [0:1];
 wire [31:0] full0,full1;
 reg running, bank_q, sticky;
 reg [5:0] slot_q;
 wire start_ok = start && !running && owned[start_bank] &&
                      block_ready[start_bank] && start_epoch==epoch[start_bank] && !fault;
 wire issue = running || start_ok;
 wire rb = running ? bank_q : start_bank;
 wire [5:0] rs = running ? slot_q : 6'd0;
 wire [31:0] pc_fault;
 assign fault = sticky || |pc_fault;
 assign busy = running;
 assign block_ready = {owned[1] && (&full1),owned[0] && (&full0)};
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   owned<=0;epoch[0]<=0;epoch[1]<=0;running<=0;bank_q<=0;slot_q<=0;
   sticky<=0;out_v<=0;out_bank<=0;out_slot<=0;out_epoch<=0;
  end else begin
   out_v<=issue && !fault;out_bank<=rb;out_slot<=rs;out_epoch<=epoch[rb];
   if(begin_v) begin
    if(owned[begin_bank] || (start && start_bank==begin_bank)) sticky<=1;
    else begin owned[begin_bank]<=1;epoch[begin_bank]<=begin_epoch;end
   end
   if(start && !start_ok) sticky<=1;
   if(start_ok) begin running<=1;bank_q<=start_bank;slot_q<=1;end
   if(running) begin
    if(slot_q==63) begin running<=0;owned[bank_q]<=0;end
    else slot_q<=slot_q+1'b1;
   end
  end
 end
 genvar p;
 generate for(p=0;p<32;p=p+1)begin:pc
  reg [63:0] seen[0:1];
  reg bad;
  wire fb=fill_bank[p];wire [5:0] fs=fill_slot[p*6+:6];
  wire fill_ok=fill_v[p] && owned[fb] && fill_epoch[p*16+:16]==epoch[fb] &&
               !seen[fb][fs] && !(issue && rb==fb) && !fault;
  wire clear_bank=begin_v && !owned[begin_bank] && !(start && start_bank==begin_bank);
  assign full0[p]=&seen[0];assign full1[p]=&seen[1];assign pc_fault[p]=bad;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin seen[0]<=0;seen[1]<=0;bad<=0;end
   else begin
    if(clear_bank)seen[begin_bank]<=0;
    if(fill_v[p]&&!fill_ok)bad<=1;
    if(fill_ok)seen[fb][fs]<=1;
   end
  end
  ot_sram_1r1w_128x256_m1_r2c2 u_payload (
   .clk(clk),.r_ce_in(issue && !fault),.r_addr_in({rb,rs}),.rd_out(out_data[p*256+:256]),
   .w_ce_in(fill_ok),.w_addr_in({fb,fs}),.wd_in(fill_data[p*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
endmodule
`default_nettype wire
