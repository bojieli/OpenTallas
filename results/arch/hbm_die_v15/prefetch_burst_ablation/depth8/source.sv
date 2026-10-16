`default_nettype none
// PC-parallel four-sector burst reverse boundary. Explicit local clocks must
// have the same fixed frequency/phase as their named domain control clock.
// Variable waits are entirely on the HBM side. Delivery begins only after a
// whole block is resident and then emits ceil(total/8) fixed stream cycles.
// Performance, routing, and physical CDC timing remain unqualified.
module ot_hbm_svc_prefetch_burst_cdc #(parameter [1:0] STACK=0, parameter integer OWNER_AW=5, parameter integer RESPONSE_DEPTH=8)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [3:0] stream_bank_clk,hbm_fifo_clk,input wire [31:0] hbm_pc_clk,
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
 ot_async_fifo #(.WIDTH(61),.DEPTH(4)) u_descriptor(
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
 genvar pc;
 generate for(pc=0;pc<32;pc=pc+1)begin:pc_owner
  localparam integer ENTRIES=1<<OWNER_AW;
  localparam [4:0] PC=pc;
  localparam integer GW=17-OWNER_AW;
  reg [16:0] next_ticket;
  reg [22:0] group_q;
  reg [ENTRIES-1:0] valid_q;
  reg [GW-1:0] generation_q[0:ENTRIES-1];
  reg [15:0] epoch_q[0:ENTRIES-1];reg bank_q[0:ENTRIES-1];
  reg [10:0] ordinal_q[0:ENTRIES-1];
  reg [2:0] length_q[0:ENTRIES-1];reg [3:0] seen_q[0:ENTRIES-1];
  reg sticky;
  wire [OWNER_AW-1:0] alloc_index=next_ticket[OWNER_AW-1:0];
  wire [OWNER_AW-1:0] return_index=kr_tag[17*pc+:OWNER_AW];
  wire [GW-1:0] return_generation=kr_tag[17*pc+OWNER_AW+:GW];
  wire [3:0] beat=kr_beat[4*pc+:4];
  wire [4:0] chunk_pc=PC^group_q[4:0]^group_q[9:5];
  wire [29:0] chunk_sector={group_q,chunk_pc,2'b0};
  wire [30:0] block_end={1'b0,h_base}+h_total;
  wire [30:0] chunk_end={1'b0,chunk_sector}+4;
  wire [29:0] lo=chunk_sector<h_base?h_base:chunk_sector;
  wire [30:0] hi=chunk_end>block_end?block_end:chunk_end;
  wire [3:0] burst_length=hi-{1'b0,lo};
  wire [22:0] initial_group=desc_data[58:36];
  wire [4:0] initial_chunk_pc=PC^initial_group[4:0]^initial_group[9:5];
  wire [29:0] initial_sector={initial_group,initial_chunk_pc,2'b0};
  function automatic [3:0] mask_for(input [2:0] n);
   case(n)1:mask_for=1;2:mask_for=3;3:mask_for=7;4:mask_for=15;default:mask_for=0;endcase
  endfunction
  assign k_v[pc]=h_active&&hi>{1'b0,lo}&&{1'b0,chunk_sector}<block_end&&
                      !valid_q[alloc_index]&&!sticky&&!hbm_fault;
  assign k_addr[30*pc+:30]=lo;
  assign k_len[4*pc+:4]=burst_length;
  assign k_tag[17*pc+:17]=next_ticket;
  assign response_ok[pc]=kr_v[pc]&&valid_q[return_index]&&
       generation_q[return_index]==return_generation&&beat<length_q[return_index]&&
       !seen_q[return_index][beat]&&!sticky&&!hbm_fault;
  assign response_ordinal[pc]=ordinal_q[return_index]+beat;
  assign response_epoch[pc]=epoch_q[return_index];
  assign response_bank[pc]=bank_q[return_index];
  assign pc_fault[pc]=sticky;
  integer e;
  always @(posedge hbm_pc_clk[pc] or negedge hrst)begin
   if(!hrst)begin
    next_ticket<=0;group_q<=0;valid_q<=0;sticky<=0;
    for(e=0;e<ENTRIES;e=e+1)begin
     generation_q[e]<=0;epoch_q[e]<=0;bank_q[e]<=0;ordinal_q[e]<=0;length_q[e]<=0;seen_q[e]<=0;
    end
   end else begin
    if(descriptor_fire)begin
     if(|valid_q)sticky<=1;
     group_q<=initial_group+(({1'b0,initial_sector}+4<={1'b0,desc_data[58:29]})?1'b1:1'b0);
    end
    if(k_v[pc]&&k_rdy[pc])begin
     if(burst_length==0||burst_length>4)sticky<=1;
     valid_q[alloc_index]<=1;generation_q[alloc_index]<=next_ticket[16:OWNER_AW];
     epoch_q[alloc_index]<=h_epoch;bank_q[alloc_index]<=h_bank;
     ordinal_q[alloc_index]<=lo-h_base;length_q[alloc_index]<=burst_length[2:0];seen_q[alloc_index]<=0;
     next_ticket<=next_ticket+1'b1;group_q<=group_q+1'b1;
    end
    if(kr_v[pc]&&!response_ok[pc])sticky<=1;
    if(response_accepted[pc])begin
     seen_q[return_index]<=seen_q[return_index]|(4'b1<<beat);
     if((seen_q[return_index]|(4'b1<<beat))==mask_for(length_q[return_index]))valid_q[return_index]<=0;
    end
   end
  end
 end endgenerate
 integer h_take,p,l;
 always @*begin
  kr_rdy=0;fifo_wr_valid=0;response_accepted=0;h_take=0;
  for(l=0;l<32;l=l+1)begin
   fifo_wr_data[l]=0;
   for(p=0;p<32;p=p+1)begin
    if(response_ok[p]&&response_ordinal[p][4:0]==l&&!fifo_wr_valid[l]&&fifo_wr_ready[l])begin
     kr_rdy[p]=1;fifo_wr_valid[l]=1;response_accepted[p]=1;h_take=h_take+1;
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
 genvar g;
 generate for(g=0;g<32;g=g+1)begin:lanes
  ot_async_fifo #(.WIDTH(284),.DEPTH(RESPONSE_DEPTH)) u_response(
   .wr_clk(hbm_fifo_clk[g/8]),.wr_rst_n(hrst),.wr_valid(fifo_wr_valid[g]),.wr_ready(fifo_wr_ready[g]),
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
