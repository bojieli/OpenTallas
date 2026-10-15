`timescale 1ps/1fs
`default_nettype none
// Production successor: actual PHY CDC landing SRAMs feed the HC aperture
// directly. No second landing copy or zero padding is necessary: HC consumes
// exactly80 rows per bank (320 sectors), never uninitialized rows80..127.
// Four banks are written/cycle for320 cycles per half,640 cycles per row.
// Eight resident regions per stack retain four rows; epoch low two bits select
// SRAM region, while full epoch remains the mandatory ownership identity.
// Reserve and drain descriptors are separate so next-row prefetch can overlap
// the prior row's fixed on-chip drain, in each bank's two-region lifetime.
module ot_hgi_hc_prefetch_resident_static #(parameter integer MUT=0, parameter integer MAX_OUTSTANDING=8)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire reserve_v,reserve_half,input wire [34:0] reserve_row_local_byte,
 input wire [15:0] reserve_epoch,output wire [3:0] reserve_ready,output wire [7:0] fetched_ready,output wire [31:0] resident_ready,
 input wire drain_v,drain_half,drain_slot,input wire [15:0] drain_epoch,
 output reg half_done,output reg done_half,output wire [2223:0] ap,output wire fault,
 output wire [127:0] k_v,input wire [127:0] k_rdy,output wire [3839:0] k_addr,
 output wire [511:0] k_len,output wire [2175:0] k_tag,output wire [127:0] k_we,
 output wire [32767:0] k_wdata,output wire [4095:0] k_wstrb,input wire [127:0] k_wr_done,
 input wire [127:0] kr_v,output wire [127:0] kr_rdy,input wire [2175:0] kr_tag,
 input wire [511:0] kr_beat,input wire [32767:0] kr_data
);
 wire [3:0] ov,ol,pfault;wire [11:0] ob;wire [8191:0] od;wire [43:0] oo;wire [63:0] oe;
 reg [2047:0] capture[0:3];reg [8:0] position;reg [2:0] sub;
 reg serializing,half_q,slot_q;reg [2:0] region_q;reg [15:0] epoch_q;
 reg bad;reg [2223:0] ap_q;
 assign ap=ap_q;assign fault=bad||(|pfault);
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
   position<=0;sub<=0;serializing<=0;half_q<=0;region_q<=0;slot_q<=0;epoch_q<=0;
   bad<=0;ap_q<=0;half_done<=0;done_half<=0;
  end else begin
   ap_q<=0;half_done<=0;
   if(reserve_v&&(reserve_ready!=4'hf||reserve_row_local_byte[4:0]!=0||
      reserve_row_local_byte<35'd21474836480||reserve_row_local_byte+35'd81920>35'd21743271936))bad<=1;
   if(drain_v)begin
    if(serializing || |ov)bad<=1;
    half_q<=drain_half;region_q<={drain_epoch[1:0],drain_half};slot_q<=drain_slot;epoch_q<=drain_epoch;
   end
   if(|ov)begin
    if(ov!=4'hf || (serializing&&sub!=7))bad<=1;
    for(integer s=0;s<4;s=s+1)begin
     capture[s]<=od[s*2048+:2048];
     if(oo[s*11+:11]!=oo[0+:11]||ob[s*3+:3]!=region_q||oe[s*16+:16]!=epoch_q)bad<=1;
    end
    position<=oo[0+:11];sub<=0;serializing<=1;
   end
   if(serializing)begin
    for(integer s=0;s<4;s=s+1)begin:lane
     integer bank,pos;
     bank=s+(half_q?4:0);pos=position+sub;
     ap_q[bank*278+:278]<={1'b1,slot_q,3'(bank),9'(pos),
       capture[s][sub*256+:256]^(MUT==1&&bank==5&&pos==319?256'd1:256'd0),8'hff};
     if(pos>=320)bad<=1;
    end
    if(sub==7)begin
     if(!(|ov))serializing<=0;
     if(position==312)begin half_done<=1;done_half<=half_q;end
    end else if(!(|ov))sub<=sub+1'b1;
   end
  end
 end
 for(genvar s=0;s<4;s=s+1)begin:stack
  assign fetched_ready[s*2+:2]=(resident_ready[s*8+:8] >> {drain_epoch[1:0],1'b0});
  wire [36:0] byte_address={2'(s),reserve_row_local_byte+35'((s+(reserve_half?4:0))*10240)};
  wire [1:0] mapped_stack;wire [4:0] pc;wire [29:0] sector;wire valid;
  ot_hbm_loader_kport_address #(.ENABLE(1)) u_address(.byte_address(byte_address),.stack_bytes(36'd25769803776),
   .stack(mapped_stack),.pc(pc),.sector_address(sector),.valid(valid));
  always @(posedge stream_clk)if(stream_rst_n&&reserve_v&&(!valid||mapped_stack!=2'(s)))$fatal(1,"HC address facade rejected descriptor");
  ot_hbm_svc_prefetch_region_cdc #(.STACK(2'(s)),.DELIVERY_II(8),.ISSUE_INTERLEAVE(1),.MAX_OUTSTANDING(MAX_OUTSTANDING),.ISSUE_WIDTH(4)) u_prefetch(
   .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
   .reserve_v(reserve_v),.reserve_ready(reserve_ready[s]),.reserve_base({mapped_stack,sector}),.reserve_total(12'd320),
   .reserve_bank({reserve_epoch[1:0],reserve_half}),.reserve_epoch(reserve_epoch),.block_ready(resident_ready[s*8+:8]),
   .block_ready_v(),.block_ready_bank(),.block_ready_epoch(),.start_v(drain_v),.start_bank({drain_epoch[1:0],drain_half}),.start_epoch(drain_epoch),
   .out_v(ov[s]),.out_mask(),.out_data(od[s*2048+:2048]),.out_ordinal(oo[s*11+:11]),.out_bank(ob[s*3+:3]),.out_epoch(oe[s*16+:16]),.out_last(ol[s]),.fault(pfault[s]),
   .k_v(k_v[s*32+:32]),.k_rdy(k_rdy[s*32+:32]),.k_addr(k_addr[s*960+:960]),.k_len(k_len[s*128+:128]),
   .k_tag(k_tag[s*544+:544]),.k_we(k_we[s*32+:32]),.k_wdata(k_wdata[s*8192+:8192]),.k_wstrb(k_wstrb[s*1024+:1024]),.k_wr_done(k_wr_done[s*32+:32]),
   .kr_v(kr_v[s*32+:32]),.kr_rdy(kr_rdy[s*32+:32]),.kr_tag(kr_tag[s*544+:544]),.kr_beat(kr_beat[s*128+:128]),.kr_data(kr_data[s*8192+:8192]));
 end
endmodule
`default_nettype wire
