`default_nettype none
// PC-parallel four-sector burst reverse boundary. Explicit local clocks must
// have the same fixed frequency/phase as their named domain control clock.
// Variable waits are entirely on the HBM side. Delivery begins only after a
// whole block is resident and then emits ceil(total/8) fixed stream cycles.
// Performance, routing, and physical CDC timing remain unqualified.
module ot_hbm_svc_prefetch_burst_cdc #(parameter [1:0] STACK=0, parameter integer OWNER_AW=5, parameter integer RESPONSE_DEPTH=8)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [3:0] stream_bank_clk,input wire [7:0] hbm_fifo_clk,input wire [31:0] hbm_pc_clk,
 input wire reserve_v,output wire reserve_ready,input wire [31:0] reserve_base,
 input wire [11:0] reserve_total,input wire reserve_bank,input wire [15:0] reserve_epoch,
 output wire [1:0] block_ready,output reg block_ready_v,block_ready_bank,
 output reg [15:0] block_ready_epoch,
 input wire start_v,start_bank,input wire [15:0] start_epoch,
 output reg out_v,output reg [7:0] out_mask,output wire [2047:0] out_data,
 output reg [10:0] out_ordinal,output reg out_bank,output reg [15:0] out_epoch,
 output reg out_last,output wire fault,
 output wire [31:0] k_v,input wire [31:0] k_rdy,output wire [959:0] k_addr,
 output wire [127:0] k_len,output wire [543:0] k_tag,output wire [31:0] k_we,
 output wire [8191:0] k_wdata,output wire [1023:0] k_wstrb,input wire [31:0] k_wr_done,
 input wire [31:0] kr_v,output reg [31:0] kr_rdy,input wire [543:0] kr_tag,
 input wire [127:0] kr_beat,input wire [8191:0] kr_data
);
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 function automatic [4:0] pc_of(input [29:0] s);
  pc_of=s[6:2]^s[11:7]^s[16:12];
 endfunction
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+reserve_total;
 wire descriptor_ok=reserve_total!=0&&reserve_total<=2048&&reserve_base[31:30]==STACK&&reserve_end<=33'h040000000;
 reg [1:0] allocated,ready_q,announced;
 reg [15:0] bank_epoch[0:1];reg [11:0] bank_total[0:1],received[0:1];
 reg [2047:0] seen[0:1];reg stream_fault,hbm_fault;
 (* async_reg="true" *)reg hbf1,hbf2;
 (* async_reg="true" *)reg stf1,stf2;
 wire desc_wr_ready,desc_rd_valid,desc_rd_ready,desc_ov,desc_un;
 wire [60:0] desc_data;
 assign reserve_ready=srst&&!allocated[reserve_bank]&&desc_wr_ready&&!fault;
 wire reserve_fire=reserve_v&&reserve_ready&&descriptor_ok;
 ot_hbm_svc_async_fifo #(.WIDTH(61),.DEPTH(4)) u_descriptor(
 .wr_clk(stream_clk),.wr_rst_n(srst),.wr_valid(reserve_fire),.wr_ready(desc_wr_ready),
 .wr_data({reserve_base,reserve_total,reserve_bank,reserve_epoch}),.wr_overflow(desc_ov),
 .rd_clk(hbm_clk),.rd_rst_n(hrst),.rd_valid(desc_rd_valid),.rd_ready(desc_rd_ready),.rd_data(desc_data),.rd_underflow(desc_un));
 assign fault=stream_fault||hbf2||desc_ov;
 assign block_ready=ready_q;
 reg h_active,h_bank;reg [15:0] h_epoch;reg [29:0] h_base;
 reg [11:0] h_total,h_received;
 wire [31:0] pc_fault,response_ok,response_bank;
 wire [10:0] response_ordinal[0:31];wire [15:0] response_epoch[0:31];
 reg [31:0] response_accepted;
 wire descriptor_fire=desc_rd_valid&&desc_rd_ready;
 assign desc_rd_ready=!h_active&&!hbm_fault&&hrst&&desc_rd_valid;
 assign k_we=0;assign k_wdata=0;assign k_wstrb=0;
 wire [31:0] fifo_wr_ready,fifo_rd_valid,fifo_rd_ready,fifo_ov,fifo_un;
 reg [31:0] fifo_wr_valid;reg [283:0] fifo_wr_data[0:31];
 wire [283:0] fifo_rd_data[0:31];
 genvar pc,g;
 generate for(pc=0;pc<32;pc=pc+1)begin:pc_owner
  ot_hbm_svc_prefetch_burst_owner #(.PC(pc),.OWNER_AW(OWNER_AW)) u_owner(
   .clk(hbm_pc_clk[pc]),.rst_n(hrst),.descriptor_v(descriptor_fire),
   .descriptor_base(desc_data[58:29]),.descriptor_total(desc_data[28:17]),
   .descriptor_bank(desc_data[16]),.descriptor_epoch(desc_data[15:0]),
   .block_active(h_active),.block_base(h_base),.block_total(h_total),
   .block_bank(h_bank),.block_epoch(h_epoch),.stop(hbm_fault),
   .k_ready(k_rdy[pc]),.kr_v(kr_v[pc]),.kr_tag(kr_tag[17*pc+:17]),
   .kr_beat(kr_beat[4*pc+:4]),.response_take(response_accepted[pc]),
   .k_v(k_v[pc]),.k_addr(k_addr[30*pc+:30]),.k_len(k_len[4*pc+:4]),.k_tag(k_tag[17*pc+:17]),
   .response_ok(response_ok[pc]),.response_ordinal(response_ordinal[pc]),
   .response_epoch(response_epoch[pc]),.response_bank(response_bank[pc]),.fault(pc_fault[pc]));
 end endgenerate
 reg [4:0] arb_cursor[0:31];
 reg [4:0] arb_selected[0:31];
 generate for(g=0;g<32;g=g+1)begin:response_fairness
  always @(posedge hbm_fifo_clk[g/4] or negedge hrst)begin
   if(!hrst)arb_cursor[g]<=0;
   else if(fifo_wr_valid[g])arb_cursor[g]<=arb_selected[g]+1'b1;
  end
 end endgenerate
 integer h_take,p,l,offset;
 always @*begin
  kr_rdy=0;fifo_wr_valid=0;response_accepted=0;h_take=0;
  for(l=0;l<32;l=l+1)begin
   fifo_wr_data[l]=0;arb_selected[l]=0;
   for(offset=0;offset<32;offset=offset+1)begin
    p=(arb_cursor[l]+offset)&31;
    if(response_ok[p]&&response_ordinal[p][4:0]==l&&!fifo_wr_valid[l]&&fifo_wr_ready[l])begin
     kr_rdy[p]=1;fifo_wr_valid[l]=1;arb_selected[l]=p;response_accepted[p]=1;h_take=h_take+1;
     fifo_wr_data[l]={response_ordinal[p],response_bank[p],response_epoch[p],kr_data[256*p+:256]};
    end
   end
  end
 end
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin
   h_active<=0;h_bank<=0;h_epoch<=0;h_base<=0;h_total<=0;h_received<=0;
   hbm_fault<=0;stf1<=0;stf2<=0;
  end else begin
   stf1<=stream_fault;stf2<=stf1;
   if(stf2||desc_un||(|fifo_ov)||(|k_wr_done)||(|pc_fault))hbm_fault<=1;
   if(descriptor_fire)begin
    if(desc_data[60:59]!=STACK||desc_data[28:17]==0||desc_data[28:17]>2048||
       {3'b0,desc_data[58:29]}+desc_data[28:17]>33'h040000000)hbm_fault<=1;
    else begin h_active<=1;h_base<=desc_data[58:29];h_total<=desc_data[28:17];
     h_bank<=desc_data[16];h_epoch<=desc_data[15:0];h_received<=0;end
   end
   if(h_active)begin
    h_received<=h_received+h_take;
    if(h_received+h_take==h_total)h_active<=0;
   end else if(|kr_v)hbm_fault<=1;
  end
 end
 generate for(g=0;g<32;g=g+1)begin:lanes
  ot_hbm_svc_async_fifo #(.WIDTH(284),.DEPTH(RESPONSE_DEPTH)) u_response(
   .wr_clk(hbm_fifo_clk[g/4]),.wr_rst_n(hrst),.wr_valid(fifo_wr_valid[g]),.wr_ready(fifo_wr_ready[g]),
   .wr_data(fifo_wr_data[g]),.wr_overflow(fifo_ov[g]),
   .rd_clk(stream_bank_clk[g/8]),.rd_rst_n(srst),.rd_valid(fifo_rd_valid[g]),.rd_ready(fifo_rd_ready[g]),
   .rd_data(fifo_rd_data[g]),.rd_underflow(fifo_un[g]));
 end endgenerate
 reg [31:0] landing_write;reg [11:0] landed[0:1];
 integer sl;reg [10:0] ordinal;reg bank;reg [15:0] epoch_in;
 always @*begin
  landing_write=0;landed[0]=0;landed[1]=0;
  for(sl=0;sl<32;sl=sl+1)begin
   ordinal=fifo_rd_data[sl][283:273];bank=fifo_rd_data[sl][272];epoch_in=fifo_rd_data[sl][271:256];
   if(fifo_rd_valid[sl]&&!fault&&allocated[bank]&&epoch_in==bank_epoch[bank]&&
      ordinal<bank_total[bank]&&ordinal[4:0]==sl&&!seen[bank][ordinal])begin
    landing_write[sl]=1;landed[bank]=landed[bank]+1'b1;
   end
  end
 end
 assign fifo_rd_ready={32{srst&&!fault}}&fifo_rd_valid;
 reg draining,drain_bank;reg [7:0] drain_row;reg [1:0] read_group_q;
 wire [255:0] macro_data[0:31];
 generate for(g=0;g<32;g=g+1)begin:payload_lane
  wire [10:0] ordinal_w=fifo_rd_data[g][283:273];
  wire bank_w=fifo_rd_data[g][272];
  ot_sram_1r1w_128x256_m1_r2c2 u_payload(
   .clk(stream_bank_clk[g/8]),.r_ce_in(draining&&!fault&&drain_row[1:0]==g/8),
   .r_addr_in({drain_bank,drain_row[7:2]}),.rd_out(macro_data[g]),
   .w_ce_in(landing_write[g]),.w_addr_in({bank_w,ordinal_w[10:5]}),
   .wd_in(fifo_rd_data[g][255:0]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 generate for(g=0;g<8;g=g+1)begin:out_lane
  assign out_data[256*g+:256]=macro_data[g+8*read_group_q];
 end endgenerate
 integer si,sb;reg [10:0] ordinal_s;reg bank_s;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin
   allocated<=0;ready_q<=0;announced<=0;stream_fault<=0;hbf1<=0;hbf2<=0;
   block_ready_v<=0;block_ready_bank<=0;block_ready_epoch<=0;
   draining<=0;drain_bank<=0;drain_row<=0;read_group_q<=0;
   out_v<=0;out_mask<=0;out_ordinal<=0;out_bank<=0;out_epoch<=0;out_last<=0;
   for(sb=0;sb<2;sb=sb+1)begin bank_epoch[sb]<=0;bank_total[sb]<=0;received[sb]<=0;seen[sb]<=0;end
  end else begin
   hbf1<=hbm_fault;hbf2<=hbf1;block_ready_v<=0;out_v<=0;out_last<=0;out_mask<=0;
   if(|fifo_un)stream_fault<=1;
   if(reserve_v)begin
    if(!reserve_ready||!descriptor_ok)stream_fault<=1;
    else begin
     allocated[reserve_bank]<=1;bank_epoch[reserve_bank]<=reserve_epoch;bank_total[reserve_bank]<=reserve_total;
     received[reserve_bank]<=0;seen[reserve_bank]<=0;ready_q[reserve_bank]<=0;announced[reserve_bank]<=0;
    end
   end
   for(si=0;si<32;si=si+1)if(fifo_rd_valid[si]&&fifo_rd_ready[si])begin
    ordinal_s=fifo_rd_data[si][283:273];bank_s=fifo_rd_data[si][272];
    if(!landing_write[si])stream_fault<=1;
    else seen[bank_s][ordinal_s]<=1;
   end
   for(sb=0;sb<2;sb=sb+1)if(landed[sb]!=0)begin
    received[sb]<=received[sb]+landed[sb];
    if(received[sb]+landed[sb]==bank_total[sb])begin ready_q[sb]<=1;end
   end
   // Whole-block availability is announced at the final verified landing edge.
   if(!announced[0]&&(ready_q[0]||(landed[0]!=0&&received[0]+landed[0]==bank_total[0])))begin
    block_ready_v<=1;block_ready_bank<=0;block_ready_epoch<=bank_epoch[0];announced[0]<=1;
   end else if(!announced[1]&&(ready_q[1]||(landed[1]!=0&&received[1]+landed[1]==bank_total[1])))begin
    block_ready_v<=1;block_ready_bank<=1;block_ready_epoch<=bank_epoch[1];announced[1]<=1;
   end
   if(start_v)begin
    if(draining||!ready_q[start_bank]||start_epoch!=bank_epoch[start_bank]||fault)stream_fault<=1;
    else begin draining<=1;drain_bank<=start_bank;drain_row<=0;ready_q[start_bank]<=0;end
   end
   if(draining&&!fault)begin
    out_v<=1;out_bank<=drain_bank;out_epoch<=bank_epoch[drain_bank];out_ordinal<={drain_row,3'b0};
    read_group_q<=drain_row[1:0];
    for(si=0;si<8;si=si+1)if({drain_row,3'b0}+si<bank_total[drain_bank])out_mask[si]<=1;
    if({drain_row,3'b0}+8>=bank_total[drain_bank])begin
     out_last<=1;draining<=0;allocated[drain_bank]<=0;
    end else drain_row<=drain_row+1'b1;
   end
  end
 end
endmodule
`default_nettype wire
