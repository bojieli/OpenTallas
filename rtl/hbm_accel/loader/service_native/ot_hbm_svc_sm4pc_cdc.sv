`default_nettype none
// Source-native SM candidate: four actual PC owner units and eight real landing SRAM banks.
// Two block banks support variable off-die prefetch then fixed-slot local delivery.
// Physical PC group is compiled from SM0..7; it is not a tied input or a free replica.
// Old generic mapped4 source is preserved byte-identical.
// PC-parallel four-sector burst reverse boundary. Explicit local clocks must
// have the same fixed frequency/phase as their named domain control clock.
// Variable waits are entirely on the HBM side. Delivery begins only after a
// whole block is resident and then emits ceil(total/8) fixed stream cycles.
// Performance, routing, and physical CDC timing remain unqualified.
// H-DIE 2026-10-15: OVERLAP=1 (default) issues the next block once every owner has issued the current block's commands
// (ot_hbm_svc_prefetch_overlap_owner), counting returns per landing bank; OVERLAP=0 = the Codex 14:47 behaviour (the next
// descriptor only after the whole block has RETURNED), kept for the measured ablation.  Steady 64-row stream at
// OVERLAP=0: 139.3 ns/epoch = 52 B/cycle/SM vs the 99 B/cycle/SM price (tb_hbm_svc_sm_stack_steady).
module ot_hbm_svc_sm4pc_cdc #(parameter [1:0] STACK=0, parameter integer SM=0, OWNER_AW=5, parameter integer RESPONSE_DEPTH=8, parameter integer OVERLAP=1)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [1:0] stream_bank_clk,input wire [1:0] hbm_fifo_clk,input wire [3:0] hbm_pc_clk,
 input wire [14:0] reserve_row_base,
 input wire reserve_v,output wire reserve_ready,input wire [31:0] reserve_base,
 input wire [11:0] reserve_total,input wire reserve_bank,input wire [15:0] reserve_epoch,
 output wire [1:0] block_ready,output reg block_ready_v,block_ready_bank,
 output reg [15:0] block_ready_epoch,
 input wire start_v,start_bank,input wire [15:0] start_epoch,
 output reg out_v,output reg [3:0] out_mask,output wire [1023:0] out_data,
 output reg [10:0] out_ordinal,output reg out_bank,output reg [15:0] out_epoch,
 output reg out_last,output wire fault,
 output wire [3:0] k_v,input wire [3:0] k_rdy,output wire [119:0] k_addr,
 output wire [15:0] k_len,output wire [67:0] k_tag,output wire [3:0] k_we,
 output wire [1023:0] k_wdata,output wire [127:0] k_wstrb,input wire [3:0] k_wr_done,
 input wire [3:0] kr_v,output reg [3:0] kr_rdy,input wire [67:0] kr_tag,
 input wire [15:0] kr_beat,input wire [1023:0] kr_data
);
 localparam integer PC_BASE=4*SM;
 localparam [19:0] reserve_pcs={5'(PC_BASE+3),5'(PC_BASE+2),5'(PC_BASE+1),5'(PC_BASE)};
 initial if(SM<0||SM>7)$fatal(1,"SM physical PC group must be0..7");
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 function automatic [4:0] pc_of(input [29:0] s);
  pc_of=s[6:2]^s[11:7]^s[16:12];
 endfunction
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+reserve_total;
 wire pcs_unique=reserve_pcs[4:0]!=reserve_pcs[9:5]&&reserve_pcs[4:0]!=reserve_pcs[14:10]&&reserve_pcs[4:0]!=reserve_pcs[19:15]&&reserve_pcs[9:5]!=reserve_pcs[14:10]&&reserve_pcs[9:5]!=reserve_pcs[19:15]&&reserve_pcs[14:10]!=reserve_pcs[19:15];
 wire descriptor_ok=pcs_unique&&reserve_base[29:0]==0&&reserve_row_base<32768&&reserve_total!=0&&reserve_total<=512&&reserve_base[31:30]==STACK&&reserve_end<=33'h040000000;
 reg [1:0] allocated,ready_q,announced;
 reg [15:0] bank_epoch[0:1];reg [11:0] bank_total[0:1];
 reg [7:0] completed_q[0:1];reg stream_fault,hbm_fault;
 wire [7:0] bank_complete,bank_complete_bank,bank_fault;
 reg [7:0] complete_event[0:1];
 (* async_reg="true" *)reg hbf1,hbf2;
 (* async_reg="true" *)reg stf1,stf2;
 wire desc_wr_ready,desc_rd_valid,desc_rd_ready,desc_ov,desc_un;
 wire [95:0] desc_data;
 assign reserve_ready=srst&&!allocated[reserve_bank]&&desc_wr_ready&&!fault;
 wire reserve_fire=reserve_v&&reserve_ready&&descriptor_ok;
 ot_hbm_svc_async_fifo #(.WIDTH(96),.DEPTH(4)) u_descriptor(
 .wr_clk(stream_clk),.wr_rst_n(srst),.wr_valid(reserve_fire),.wr_ready(desc_wr_ready),
 .wr_data({reserve_pcs,reserve_row_base,reserve_base,reserve_total,reserve_bank,reserve_epoch}),.wr_overflow(desc_ov),
 .rd_clk(hbm_clk),.rd_rst_n(hrst),.rd_valid(desc_rd_valid),.rd_ready(desc_rd_ready),.rd_data(desc_data),.rd_underflow(desc_un));
 assign fault=stream_fault||hbf2||desc_ov||(|bank_fault);
 assign block_ready=ready_q;
 reg h_active,h_bank;reg [15:0] h_epoch;reg [29:0] h_base;
 reg [11:0] h_total,h_received;reg [19:0] h_pcs;reg [14:0] h_row_base;
 reg [11:0] rx_left[0:1];reg h_fresh;wire [3:0] issue_done;
 wire [3:0] pc_fault,response_ok,response_bank;
 wire [10:0] response_ordinal[0:3];wire [15:0] response_epoch[0:3];
 reg [3:0] response_accepted;
 wire descriptor_fire=desc_rd_valid&&desc_rd_ready;
 assign desc_rd_ready=!h_active&&!hbm_fault&&hrst&&desc_rd_valid&&(OVERLAP==0||rx_left[desc_data[16]]==0);
 assign k_we=0;assign k_wdata=0;assign k_wstrb=0;
 wire [7:0] fifo_wr_ready,fifo_ov;
 reg [7:0] fifo_wr_valid;reg [283:0] fifo_wr_data[0:7];
 genvar pc,g;
 generate for(pc=0;pc<4;pc=pc+1)begin:pc_owner
  if(OVERLAP!=0)begin:ov
  ot_hbm_svc_prefetch_overlap_owner #(.PC(PC_BASE+pc),.OWNER_AW(OWNER_AW)) u_owner(
   .clk(hbm_pc_clk[pc]),.rst_n(hrst),.descriptor_v(descriptor_fire),
   .descriptor_base(desc_data[58:29]),.descriptor_pcs(desc_data[95:76]),.descriptor_row_base(desc_data[75:61]),.descriptor_total(desc_data[28:17]),
   .descriptor_bank(desc_data[16]),.descriptor_epoch(desc_data[15:0]),
   .block_active(h_active),.block_base(h_base),.block_pcs(h_pcs),.block_row_base(h_row_base),.block_total(h_total),
   .block_bank(h_bank),.block_epoch(h_epoch),.stop(hbm_fault),
   .k_ready(k_rdy[pc]),.kr_v(kr_v[pc]),.kr_tag(kr_tag[17*pc+:17]),
   .kr_beat(kr_beat[4*pc+:4]),.response_take(response_accepted[pc]),
   .k_v(k_v[pc]),.k_addr(k_addr[30*pc+:30]),.k_len(k_len[4*pc+:4]),.k_tag(k_tag[17*pc+:17]),
   .response_ok(response_ok[pc]),.response_ordinal(response_ordinal[pc]),
   .response_epoch(response_epoch[pc]),.response_bank(response_bank[pc]),.fault(pc_fault[pc]),.issue_done(issue_done[pc]));
  end else begin:seq
  ot_hbm_svc_prefetch_mapped4_owner #(.PC(PC_BASE+pc),.OWNER_AW(OWNER_AW)) u_owner(
   .clk(hbm_pc_clk[pc]),.rst_n(hrst),.descriptor_v(descriptor_fire),
   .descriptor_base(desc_data[58:29]),.descriptor_pcs(desc_data[95:76]),.descriptor_row_base(desc_data[75:61]),.descriptor_total(desc_data[28:17]),
   .descriptor_bank(desc_data[16]),.descriptor_epoch(desc_data[15:0]),
   .block_active(h_active),.block_base(h_base),.block_pcs(h_pcs),.block_row_base(h_row_base),.block_total(h_total),
   .block_bank(h_bank),.block_epoch(h_epoch),.stop(hbm_fault),
   .k_ready(k_rdy[pc]),.kr_v(kr_v[pc]),.kr_tag(kr_tag[17*pc+:17]),
   .kr_beat(kr_beat[4*pc+:4]),.response_take(response_accepted[pc]),
   .k_v(k_v[pc]),.k_addr(k_addr[30*pc+:30]),.k_len(k_len[4*pc+:4]),.k_tag(k_tag[17*pc+:17]),
   .response_ok(response_ok[pc]),.response_ordinal(response_ordinal[pc]),
   .response_epoch(response_epoch[pc]),.response_bank(response_bank[pc]),.fault(pc_fault[pc]));
  assign issue_done[pc]=1'b1;
  end
 end endgenerate
 reg [1:0] arb_cursor[0:7];
 reg [1:0] arb_selected[0:7];
 generate for(g=0;g<8;g=g+1)begin:response_fairness
  always @(posedge hbm_fifo_clk[g/4] or negedge hrst)begin
   if(!hrst)arb_cursor[g]<=0;
   else if(fifo_wr_valid[g])arb_cursor[g]<=arb_selected[g]+1'b1;
  end
 end endgenerate
 integer h_take,h_take_b0,h_take_b1,p,l,offset;
 always @*begin
  kr_rdy=0;fifo_wr_valid=0;response_accepted=0;h_take=0;h_take_b0=0;h_take_b1=0;
  for(l=0;l<8;l=l+1)begin
   fifo_wr_data[l]=0;arb_selected[l]=0;
   for(offset=0;offset<4;offset=offset+1)begin
    p=(arb_cursor[l]+offset)&3;
    if(response_ok[p]&&response_ordinal[p][2:0]==l&&!fifo_wr_valid[l]&&fifo_wr_ready[l])begin
     kr_rdy[p]=1;fifo_wr_valid[l]=1;arb_selected[l]=p;response_accepted[p]=1;h_take=h_take+1;
     if(response_bank[p])h_take_b1=h_take_b1+1;else h_take_b0=h_take_b0+1;
     fifo_wr_data[l]={response_ordinal[p],response_bank[p],response_epoch[p],kr_data[256*p+:256]};
    end
   end
  end
 end
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin
   h_active<=0;h_bank<=0;h_epoch<=0;h_base<=0;h_total<=0;h_received<=0;h_pcs<=0;h_row_base<=0;
   rx_left[0]<=0;rx_left[1]<=0;h_fresh<=0;
   hbm_fault<=0;stf1<=0;stf2<=0;
  end else begin
   stf1<=stream_fault;stf2<=stf1;
   if(stf2||desc_un||(|fifo_ov)||(|k_wr_done)||(|pc_fault))hbm_fault<=1;
   if(descriptor_fire)begin
    if(desc_data[60:59]!=STACK||desc_data[28:17]==0||desc_data[28:17]>512||
       {3'b0,desc_data[58:29]}+desc_data[28:17]>33'h040000000)hbm_fault<=1;
    else begin h_active<=1;h_base<=desc_data[58:29];h_pcs<=desc_data[95:76];h_row_base<=desc_data[75:61];h_total<=desc_data[28:17];
     h_bank<=desc_data[16];h_epoch<=desc_data[15:0];h_received<=0;end
   end
   if(OVERLAP==0)begin
    if(h_active)begin
     h_received<=h_received+h_take;
     if(h_received+h_take==h_total)h_active<=0;
    end else if(|kr_v)hbm_fault<=1;
   end else begin
    // issue phase ends when every owner has issued the block; returns are counted per landing bank
    h_fresh<=descriptor_fire;
    if(h_active&&!descriptor_fire&&!h_fresh&&(&issue_done))h_active<=0;
    if(descriptor_fire&&rx_left[desc_data[16]]!=0)hbm_fault<=1;
    rx_left[0]<=(descriptor_fire&&!desc_data[16]?desc_data[28:17]:rx_left[0])-12'(h_take_b0);
    rx_left[1]<=(descriptor_fire&& desc_data[16]?desc_data[28:17]:rx_left[1])-12'(h_take_b1);
    if((h_take_b0!=0&&rx_left[0]==0)||(h_take_b1!=0&&rx_left[1]==0))hbm_fault<=1;
    if(|kr_v&&rx_left[0]==0&&rx_left[1]==0&&!descriptor_fire)hbm_fault<=1;
   end
  end
 end
 reg draining,drain_bank;reg [10:0] drain_ordinal;reg [10:0] read_ordinal_q;reg [2:0] drain_phase;
 wire [2:0] drain_count=drain_phase==4?3'd1:3'd4;
 wire [255:0] macro_data[0:7];
 generate for(g=0;g<8;g=g+1)begin:ordinal_bank
  wire [11:0] candidate={3'b0,drain_ordinal[8:3],3'(g)}+((g<drain_ordinal[2:0])?12'd8:12'd0);
  ot_hbm_svc_sm8_landing_bank #(.BANK(g),.RESPONSE_DEPTH(RESPONSE_DEPTH)) u_bank(
   .hbm_clk(hbm_fifo_clk[g/4]),.hbm_rst_n(hrst),.stream_clk(stream_bank_clk[g/4]),.stream_rst_n(srst),
   .in_v(fifo_wr_valid[g]),.in_ready(fifo_wr_ready[g]),.in_data(fifo_wr_data[g]),.overflow(fifo_ov[g]),
   .reserve_v(reserve_fire),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_total(reserve_total),.stop(fault),
   .complete_v(bank_complete[g]),.complete_bank(bank_complete_bank[g]),.fault(bank_fault[g]),
   .read_v(draining&&candidate<drain_ordinal+drain_count&&candidate<bank_total[drain_bank]),.read_bank(drain_bank),.read_row(candidate[8:3]),.read_data(macro_data[g]));
 end endgenerate
 integer ci;
 always @*begin
  complete_event[0]=0;complete_event[1]=0;
  for(ci=0;ci<8;ci=ci+1)if(bank_complete[ci])complete_event[bank_complete_bank[ci]][ci]=1;
 end
 generate for(g=0;g<4;g=g+1)begin:out_lane
  assign out_data[256*g+:256]=macro_data[(read_ordinal_q[2:0]+g)%8];
 end endgenerate
 integer si,sb;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin
   allocated<=0;ready_q<=0;announced<=0;stream_fault<=0;hbf1<=0;hbf2<=0;
   block_ready_v<=0;block_ready_bank<=0;block_ready_epoch<=0;
   draining<=0;drain_bank<=0;drain_ordinal<=0;read_ordinal_q<=0;drain_phase<=0;
   out_v<=0;out_mask<=0;out_ordinal<=0;out_bank<=0;out_epoch<=0;out_last<=0;
   for(sb=0;sb<2;sb=sb+1)begin bank_epoch[sb]<=0;bank_total[sb]<=0;completed_q[sb]<=0;end
  end else begin
   hbf1<=hbm_fault;hbf2<=hbf1;block_ready_v<=0;out_v<=0;out_last<=0;out_mask<=0;
   if(reserve_v)begin
    if(!reserve_ready||!descriptor_ok)stream_fault<=1;
    else begin
     allocated[reserve_bank]<=1;bank_epoch[reserve_bank]<=reserve_epoch;bank_total[reserve_bank]<=reserve_total;
     for(si=0;si<8;si=si+1)completed_q[reserve_bank][si]<=reserve_total<=si;
     ready_q[reserve_bank]<=0;announced[reserve_bank]<=0;
    end
   end
   for(sb=0;sb<2;sb=sb+1)if(|complete_event[sb])begin
    completed_q[sb]<=completed_q[sb]|complete_event[sb];
    if(&(completed_q[sb]|complete_event[sb]))ready_q[sb]<=1;
   end
   if(!announced[0]&&allocated[0]&&(&(completed_q[0]|complete_event[0])))begin
    block_ready_v<=1;block_ready_bank<=0;block_ready_epoch<=bank_epoch[0];announced[0]<=1;
   end else if(!announced[1]&&allocated[1]&&(&(completed_q[1]|complete_event[1])))begin
    block_ready_v<=1;block_ready_bank<=1;block_ready_epoch<=bank_epoch[1];announced[1]<=1;
   end
   if(start_v)begin
    if(draining||!ready_q[start_bank]||start_epoch!=bank_epoch[start_bank]||fault)stream_fault<=1;
    else begin draining<=1;drain_bank<=start_bank;drain_ordinal<=0;drain_phase<=0;ready_q[start_bank]<=0;end
   end
   if(draining&&!fault)begin
    out_v<=1;out_bank<=drain_bank;out_epoch<=bank_epoch[drain_bank];out_ordinal<=drain_ordinal;
    read_ordinal_q<=drain_ordinal;drain_phase<=drain_phase==4?0:drain_phase+1'b1;
    for(si=0;si<4;si=si+1)if(si<drain_count&&drain_ordinal+si<bank_total[drain_bank])out_mask[si]<=1;
    if(drain_ordinal+drain_count>=bank_total[drain_bank])begin
     out_last<=1;draining<=0;allocated[drain_bank]<=0;
    end else drain_ordinal<=drain_ordinal+drain_count;
   end
  end
 end
endmodule
`default_nettype wire
