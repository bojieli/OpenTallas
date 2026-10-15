`timescale 1ps/1fs
`default_nettype none
// Actual STRIPE4 HC row: eight 320-sector contiguous bank segments; stack=b%4.
// One descriptor row has 81920 local bytes (holes on each stack are preserved).
// Four native HBM prefetch engines retain bank b and b+4 independently. Their
// eight-sector fixed bursts are spaced by eight stream cycles; registers
// serialize each into one HC-bank write per cycle, without any backpressure.
// The landing reshapes into two 2048-sector deliveries. Unused positions
// 320..511 are explicit zeros, never reads beyond the source descriptor.
// Compiler controls reserve/drain/pad/deliver pulses. Only reserve and whole
// block readiness are checked at the unpredictable PHY boundary. Every
// subsequent transfer follows the fixed schedule; violations latch fault.
module ot_hgi_hc_prefetch_static #(parameter integer MUT=0, parameter integer INTERNAL_APERTURE=1)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire row_v,input wire [34:0] row_local_byte,input wire row_slot,
 input wire [15:0] row_epoch,
 input wire reserve_v,reserve_half,output wire [3:0] reserve_ready,
 output wire [7:0] fetched_ready,
 input wire drain_v,drain_half,input wire pad_v,
 output wire [1:0] delivery_ready,
 input wire deliver_v,deliver_half,
 input wire [7:0] read_v,read_slot,input wire [55:0] read_row,
 output wire [7:0] read_valid,write_done,output wire [8191:0] raw_weight,
 output wire fault,output wire [2223:0] ap,
 output wire [127:0] k_v,input wire [127:0] k_rdy,output wire [3839:0] k_addr,
 output wire [511:0] k_len,output wire [2175:0] k_tag,output wire [127:0] k_we,
 output wire [32767:0] k_wdata,output wire [4095:0] k_wstrb,input wire [127:0] k_wr_done,
 input wire [127:0] kr_v,output wire [127:0] kr_rdy,input wire [2175:0] kr_tag,
 input wire [511:0] kr_beat,input wire [32767:0] kr_data
);
 reg configured,slot_q;reg [34:0] base_q;reg [15:0] epoch_q;
 reg bad;wire [3:0] pfault;
 wire [3:0] ov;wire [8191:0] od;wire [43:0] oo;wire [3:0] ob;
 reg [2047:0] capture[0:3];reg [8:0] position;reg [2:0] sub;
 reg serializing,half_q;reg [8:0] padding;reg padding_active;
 reg [31:0] fill_v,fill_bank;reg [191:0] fill_slot;
 reg [511:0] fill_epoch;reg [8191:0] fill_data;
 reg begin_v,begin_bank;reg [1:0] begin_stage;
 wire [2247:0] dq;wire landing_fault,bridge_fault,ap_fault,busy;
 wire [15:0] synthetic_base=deliver_half?16'h0800:16'h0000;
 assign fault=bad||(|pfault)||landing_fault||bridge_fault||ap_fault;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
   configured<=0;slot_q<=0;base_q<=0;epoch_q<=0;bad<=0;serializing<=0;
   position<=0;sub<=0;half_q<=0;padding<=0;padding_active<=0;begin_stage<=0;begin_v<=0;begin_bank<=0;
  end else begin
   begin_v<=0;
   if(row_v)begin
    if(serializing||padding_active||begin_stage!=0||row_local_byte[4:0]!=0||
       row_local_byte<35'd21474836480||row_local_byte+35'd81920>35'd21743271936)bad<=1;
    configured<=1;slot_q<=row_slot;base_q<=row_local_byte;epoch_q<=row_epoch;begin_stage<=1;
   end
   if(begin_stage==1)begin begin_v<=1;begin_bank<=0;begin_stage<=2;end
   if(begin_stage==2)begin begin_v<=1;begin_bank<=1;begin_stage<=0;end
   if(reserve_v&&(!configured||reserve_ready!=4'hf))bad<=1;
   if(drain_v)begin
    if(serializing||padding_active)bad<=1;
    half_q<=drain_half;
   end
   if(|ov)begin
    if(ov!=4'hf || (serializing&&sub!=7))bad<=1;
    for(integer s=0;s<4;s=s+1)begin
     capture[s]<=od[s*2048+:2048];
     if(oo[s*11+:11]!=oo[0+:11]||ob[s]!=half_q)bad<=1;
    end
    position<=oo[0+:11];sub<=0;serializing<=1;
   end
   if(serializing)begin
    if(sub==7)begin if(!(|ov))serializing<=0;end
    else if(!(|ov))sub<=sub+1'b1;
   end
   if(pad_v)begin
    if(serializing||padding_active)bad<=1;
    padding_active<=1;padding<=320;
   end
   if(padding_active)begin
    if(padding==511)padding_active<=0;
    else padding<=padding+1'b1;
   end
  end
 end
 always @*begin
  fill_v=0;fill_bank=0;fill_slot=0;fill_epoch={32{epoch_q}};fill_data=0;
  if(serializing)begin
   for(integer s=0;s<4;s=s+1)begin:reshape
    integer hc_bank,pos,pc;
    hc_bank=s+(half_q?4:0);pos=position+sub;pc=(pos%4)*8+hc_bank;
    fill_v[pc]=1;fill_bank[pc]=pos>=256;fill_slot[pc*6+:6]=(pos%256)/4;
    fill_data[pc*256+:256]=capture[s][sub*256+:256] ^ (MUT==1 && hc_bank==5 && pos==319?256'd1:256'd0);
   end
  end
  if(padding_active)begin
   for(integer b=0;b<8;b=b+1)begin
    fill_v[(padding%4)*8+b]=1;fill_bank[(padding%4)*8+b]=1;
    fill_slot[((padding%4)*8+b)*6+:6]=(padding%256)/4;
   end
  end
 end
 for(genvar s=0;s<4;s=s+1)begin:stack
  wire [36:0] byte_address={2'(s),base_q+35'((s+(reserve_half?4:0))*10240)};
  wire [1:0] mapped_stack;wire [4:0] pc;wire [29:0] sector;wire valid;
  ot_hbm_loader_kport_address #(.ENABLE(1)) u_address(.byte_address(byte_address),.stack_bytes(36'd25769803776),
   .stack(mapped_stack),.pc(pc),.sector_address(sector),.valid(valid));
  always @(posedge stream_clk)if(stream_rst_n&&reserve_v&&(!valid||mapped_stack!=2'(s)))$fatal(1,"HC address facade rejected descriptor");
  ot_hbm_svc_prefetch_block_cdc #(.STACK(2'(s)),.DELIVERY_II(8)) u_prefetch(
   .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
   .reserve_v(reserve_v),.reserve_ready(reserve_ready[s]),.reserve_base({mapped_stack,sector}),.reserve_total(12'd320),
   .reserve_bank(reserve_half),.reserve_epoch(epoch_q),.block_ready(fetched_ready[s*2+:2]),
   .block_ready_v(),.block_ready_bank(),.block_ready_epoch(),.start_v(drain_v),.start_bank(drain_half),.start_epoch(epoch_q),
   .out_v(ov[s]),.out_mask(),.out_data(od[s*2048+:2048]),.out_ordinal(oo[s*11+:11]),.out_bank(ob[s]),.out_epoch(),.out_last(),.fault(pfault[s]),
   .k_v(k_v[s*32+:32]),.k_rdy(k_rdy[s*32+:32]),.k_addr(k_addr[s*960+:960]),.k_len(k_len[s*128+:128]),
   .k_tag(k_tag[s*544+:544]),.k_we(k_we[s*32+:32]),.k_wdata(k_wdata[s*8192+:8192]),.k_wstrb(k_wstrb[s*1024+:1024]),.k_wr_done(k_wr_done[s*32+:32]),
   .kr_v(kr_v[s*32+:32]),.kr_rdy(kr_rdy[s*32+:32]),.kr_tag(kr_tag[s*544+:544]),.kr_beat(kr_beat[s*128+:128]),.kr_data(kr_data[s*8192+:8192]));
 end
 ot_hbm_svc_static_vm_delivery u_delivery(.clk(stream_clk),.rst_n(stream_rst_n),
  .begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(epoch_q),.fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),
  .block_ready(delivery_ready),.start(deliver_v),.start_bank(deliver_half),.start_epoch(epoch_q),.start_base_sector(synthetic_base),.dq(dq),.busy(busy),.fault(landing_fault));
 // Descriptor arrives one edge before start; bridge sees no data until later.
 ot_hgi_hc_aperture_bridge_static u_bridge(.clk(stream_clk),.rst_n(stream_rst_n),.desc_v(deliver_v),.desc_source_base(synthetic_base),
  .desc_slot(slot_q),.desc_position_base(deliver_half?9'd256:9'd0),.dq(dq),.ap(ap),.fault(bridge_fault));
 if(INTERNAL_APERTURE)begin:g_aperture
 ot_hgi_hc_aperture_static u_aperture(.clk(stream_clk),.rst_n(stream_rst_n),.ap(ap),.write_done(write_done),
  .read_v(read_v),.read_slot(read_slot),.read_row(read_row),.read_valid(read_valid),.raw_weight(raw_weight),.fault(ap_fault));
 end else begin:g_external
  assign ap_fault=0;assign write_done=0;assign read_valid=0;assign raw_weight=0;
 end
endmodule
`default_nettype wire
