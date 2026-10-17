`timescale 1ns/1ps
// Source-constrained reader controller only. HOST/write service and native
// operand/consumer joins remain unsupported; no die production binding yet.
module qkd_kv_compact_reader #(parameter integer FRAME=1782,STAGES=36,MUT=0)(
 input wire pll_hbm,ck,rst_n,
 input wire h_we,h_seal,input wire[9:0]h_row,input wire[255:0]h_data,
 input wire[14:0]h_bytes,input wire[31:0]h_stop,input wire h_start,
 input wire c_we,c_seal,input wire[9:0]c_row,input wire[255:0]c_data,
 input wire[14:0]c_bytes,input wire[31:0]c_stop,input wire c_start,
 input wire[15:0]epoch,
 output wire configured_h,configured_c,active_h,active_c,done_h,done_c,fault_h,fault_c,
 output wire[31:0]cycle_h,cycle_c,
 output reg[42:0]static_cmd,output wire static_cmd_owner,reserved_rd,
 output wire reserved_static_col,reserved_write_col,blk_go,
 output reg[15:0]static_epoch,
 output reg expected_put,output reg[9:0]expected_sector,
 output reg[15:0]expected_epoch,output reg[5:0]expected_layer
);
 wire hs,cs;wire[14:0]hn,cn;
 qkd_kv_delta_calendar #(.MUT(MUT)) hprog(.ck(pll_hbm),.rst_n(rst_n),.cfg_we(h_we),.cfg_seal(h_seal),
  .cfg_row(h_row),.cfg_data(h_data),.cfg_bytes(h_bytes),.cfg_stop(h_stop),.start(h_start),
  .slot(hs),.ordinal(hn),.configured(configured_h),.active(active_h),.done(done_h),.fault(fault_h),.cycle(cycle_h));
 qkd_kv_delta_calendar cprog(.ck(ck),.rst_n(rst_n),.cfg_we(c_we),.cfg_seal(c_seal),
  .cfg_row(c_row),.cfg_data(c_data),.cfg_bytes(c_bytes),.cfg_stop(c_stop),.start(c_start),
  .slot(cs),.ordinal(cn),.configured(configured_c),.active(active_c),.done(done_c),.fault(fault_c),.cycle(cycle_c));
 assign static_cmd_owner=active_h;
 assign reserved_rd=hs;
 assign reserved_static_col=1'b0;assign reserved_write_col=1'b0;
 reg[47:0]release_slots;
 reg[12:0]frame_cycle;reg[5:0]stage;
 reg[5:0]v_go_delay;
 // This delay is driven by compiler slots, never by actual returned data.
 assign blk_go=release_slots[47];
 always @(posedge pll_hbm or negedge rst_n)begin
  if(!rst_n)begin release_slots<=0;static_cmd<=0;static_epoch<=0;frame_cycle<=0;stage<=0;v_go_delay<=0;end
  else begin
   static_cmd<=0;
   release_slots<={release_slots[46:0],hs&&hn[2:0]==0};
   if(!active_h)begin frame_cycle<=0;stage<=0;static_epoch<=epoch;v_go_delay<=0;end
   else begin
    if(frame_cycle==FRAME-1)begin frame_cycle<=0;stage<=stage+1'b1;end
    else frame_cycle<=frame_cycle+1'b1;
    if(frame_cycle==9)static_cmd<={10'd0,2'd0,11'd256,19'd64+{13'd0,stage},1'b1};
    if(frame_cycle==39)static_cmd<={10'd0,2'd1,30'd0,1'b1};
    if(hs&&hn[8:0]==9'd256)begin
     static_cmd<={10'd512,2'd0,11'd768,19'd64+{13'd0,stage},1'b1};v_go_delay<=30;
    end else if(v_go_delay!=0)begin
     v_go_delay<=v_go_delay-1'b1;
     if(v_go_delay==1)static_cmd<={10'd0,2'd1,30'd0,1'b1};
    end
   end
  end
 end
 wire[14:0]ci=cn-15'd1;wire[7:0]vi=ci[7:0];
 wire[9:0]sector_next=(ci[8]?{2'b10,vi[3],vi[7:4],vi[2:0]}:{2'b00,ci[7:0]}) ^ ((MUT==3)?10'd1:10'd0);
 // Metadata and its valid occupy real output pin flops. Compiler bytecode
 // predecodes this extra edge; receiver-facing slot cycles stay unchanged.
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin expected_put<=0;expected_sector<=0;expected_layer<=0;expected_epoch<=0;end
  else begin expected_put<=cs;expected_sector<=sector_next;expected_layer<=ci[14:9];expected_epoch<=epoch;end
endmodule
