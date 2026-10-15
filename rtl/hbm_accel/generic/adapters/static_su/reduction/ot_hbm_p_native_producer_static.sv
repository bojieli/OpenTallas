`timescale 1ns/1ps
`default_nettype none
// Real SFU programme/operand SRAM + real source/scratch reduction SRAM join.
// The compiler assigns all arithmetic, fetch, scalar-publication and drain slots.
// External VM ports must bind the actual LG14/11 tap and mapped bank, not an
// ideal response generator. The boundary can start at raw SC for component proof.
module ot_hbm_p_native_producer_static #(
 parameter integer PAGE_AW=2,AW=10+PAGE_AW
)(
 input wire clk,rst_n,
 input wire[15:0]clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire cfg_we,input wire[2:0]cfg_stripe,input wire[AW-1:0]cfg_addr,input wire[255:0]cfg_data,
 input wire[AW-1:0]start_base,input wire[AW:0]start_limit,input wire[15:0]start_loops,
 input wire io_cfg_we,input wire[1:0]io_cfg_stripe,input wire[AW-1:0]io_cfg_addr,input wire[255:0]io_cfg_data,
 input wire io_start_v,input wire[AW-1:0]io_start_base,input wire[AW:0]io_start_limit,input wire[15:0]io_start_loops,
 input wire aux_cfg_we,input wire[AW-1:0]aux_cfg_addr,input wire[255:0]aux_cfg_data,
 output wire[135:0]local_rq,input wire[2055:0]local_rr,
 output wire[2247:0]local_wq,input wire[7:0]local_w_done,
 output wire scalar_valid,output wire[31:0]scalar_tag,scalar_fp32,
 output wire programme_done,io_done,output wire fault,
 output wire calendar_v,output wire[31:0]calendar_ordinal
);
 wire[135:0]sfu_rq;wire[2247:0]sfu_wq,scalar_wq;
 wire[2055:0]sfu_rr,reduce_rr;
 wire[7:0]sfu_done;
 wire sfu_fault,reduce_fault;
 wire aux_fault,aux_valid,aux_active,aux_done;
 wire[31:0]aux_ordinal,sfu_io_ordinal;
 wire[181:0]aux_word;
 wire reduce_fetch_v,command_v,source_operand,publish_slot;
 wire[15:0]reduce_fetch_sector,publish_sector;
 wire[3:0]reduce_fill_burst;
 wire[9:0]source_word,command_a,command_b,command_dst;
 wire[2:0]command_op,publish_word;
 wire[31:0]constant_operand,command_tag,expected_tag;
 wire[181:0]aux=aux_valid?aux_word:182'd0;
 assign calendar_v=aux_valid;
 assign calendar_ordinal=aux_ordinal;
 assign {reduce_fill_burst,reduce_fetch_sector,reduce_fetch_v,publish_word,publish_sector,expected_tag,publish_slot,
         command_tag,constant_operand,command_dst,command_b,command_a,command_op,source_word,source_operand,command_v}=aux;
 ot_hgi_sfu_program_stripe_static #(.PAGE_AW(PAGE_AW),.W(182)) u_aux(
  .clk(clk),.rst_n(rst_n),.cfg_we(aux_cfg_we),.cfg_addr(aux_cfg_addr),.cfg_data(aux_cfg_data),
  .start_v(io_start_v),.start_base(io_start_base),.start_limit(io_start_limit),.start_loops(io_start_loops),
  .calendar(aux_word),.calendar_v(aux_valid),.ordinal(aux_ordinal),.active(aux_active),.done(aux_done),.fault(aux_fault));
 reg schedule_fault;
 reg[14:0]read_owner;
 reg[3:0]burst[0:14];
 reg[7:0]write_owner[0:11];
 wire[7:0]scalar_write_v;
 generate for(genvar b=0;b<8;b=b+1)begin:g_port
  assign local_rq[17*b+:17]=reduce_fetch_v?
   {1'b1,16'(reduce_fetch_sector+b)}:sfu_rq[17*b+:17];
  assign sfu_rr[257*b+:257]=read_owner[14]?257'd0:local_rr[257*b+:257];
  assign reduce_rr[257*b+:257]=read_owner[14]?local_rr[257*b+:257]:257'd0;
  assign local_wq[281*b+:281]=sfu_wq[281*b+:281]|scalar_wq[281*b+:281];
  assign scalar_write_v[b]=scalar_wq[281*b+280];
  assign sfu_done[b]=local_w_done[b]&~write_owner[11][b];
 end endgenerate
 always @(posedge clk)begin
  if(!rst_n)begin
   read_owner<=0;schedule_fault<=0;
   for(integer j=0;j<12;j=j+1)write_owner[j]<=0;
  end else begin
   read_owner<={read_owner[13:0],reduce_fetch_v};
   write_owner[0]<=scalar_write_v;
   for(integer j=1;j<12;j=j+1)write_owner[j]<=write_owner[j-1];
   if(reduce_fetch_v&&(reduce_fetch_sector[2:0]!=0||
      sfu_rq[16]||sfu_rq[33]||sfu_rq[50]||sfu_rq[67]||sfu_rq[84]||sfu_rq[101]||sfu_rq[118]||sfu_rq[135]))schedule_fault<=1;
   for(integer b=0;b<8;b=b+1)
    if(sfu_wq[281*b+280]&&scalar_wq[281*b+280])schedule_fault<=1;
   if(aux_valid&&aux_ordinal!=sfu_io_ordinal)schedule_fault<=1;
  end
  burst[0]<=reduce_fill_burst;
  for(integer j=1;j<15;j=j+1)burst[j]<=burst[j-1];
 end
 ot_hgi_sfu_scheduled_engine #(.PAGE_AW(PAGE_AW)) u_sfu(
 .clk(clk),.rst_n(rst_n),.clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
 .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.programme_done(programme_done),
 .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),
 .io_start_v(io_start_v),.io_start_base(io_start_base),.io_start_limit(io_start_limit),.io_start_loops(io_start_loops),.io_done(io_done),.io_ordinal(sfu_io_ordinal),
 .local_rq(sfu_rq),.local_rr(sfu_rr),.local_wq(sfu_wq),.local_w_done(sfu_done),
 .vi_q(512'd0),.side_y(512'd0),.fault(sfu_fault));
 ot_hbm_p_native_reduce_static u_reduce(
 .clk(clk),.rst_n(rst_n),.fill_slot(read_owner[14]),.fill_burst(burst[14]),.vm_rr(reduce_rr),
 .command_v(command_v),.source_operand(source_operand),.source_word(source_word),
 .command_op(command_op),.command_a(command_a),.command_b(command_b),.command_dst(command_dst),
 .constant_operand(constant_operand),.command_tag(command_tag),
 .publish_slot(publish_slot),.expected_tag(expected_tag),.publish_sector(publish_sector),.publish_word(publish_word),
 .vm_wq(scalar_wq),.scalar_valid(scalar_valid),.scalar_tag(scalar_tag),.scalar_fp32(scalar_fp32),.scalar_bf16(),.fault(reduce_fault));
 assign fault=schedule_fault|sfu_fault|reduce_fault|aux_fault;
endmodule
`default_nettype wire
