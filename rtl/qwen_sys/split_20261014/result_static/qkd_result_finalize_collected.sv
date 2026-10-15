`timescale 1ns/1ps
// Actual arithmetic-to-record source join. No aggregate-valid aliases enter
// collection. Production stays closed until a compiler/physical owner supplies
// and qualifies a complete age/clock/geometry configuration.
module qkd_result_finalize_collected #(
 parameter integer CONFIGURED=0,
 parameter integer P0_AGE=8,P1_AGE=20,R_AGE=48,ADD_LAT=7,MUL_LAT=6,
 parameter [1023:0] CAPTURE_AGES=0,
 parameter [127:0] STACK_FIRST=0
)(input wire[31:0]clk_join,input wire[2:0]clk_merge,input wire clk_control,rst_n,start,
 input wire[15:0]epoch,input wire[5:0]layer,input wire[127:0]reciprocal,
 input wire reciprocal_valid,input wire[15:0]reciprocal_epoch,
 input wire p0_valid,p1_valid,input wire[15:0]p0_epoch,p1_epoch,
 input wire[16383:0]p0_partial,p1_partial,
 output wire result_v,output wire[547:0]result_record,output wire fault);
 localparam integer LAST_CAPTURE=(P0_AGE>P1_AGE)?((P0_AGE>R_AGE)?P0_AGE:R_AGE):((P1_AGE>R_AGE)?P1_AGE:R_AGE);
 // Actual producer exposes valid when age+1=LAST_CAPTURE+ADD_LAT+MUL_LAT+3.
 // Collector age=0 on the first edge after the shared start/CMD event.
 localparam integer SOURCE_CAPTURE_AGE=LAST_CAPTURE+ADD_LAT+MUL_LAT+2;
 wire[31:0]nv;wire[511:0]ne;wire[191:0]nl;wire[16383:0]nd;
 wire arithmetic_fault,transport_fault,collected_v;
 wire [547:0]collected_record;
 assign result_v=(CONFIGURED==1)&&collected_v;
 assign result_record=(CONFIGURED==1)?collected_record:548'd0;
 initial if(CONFIGURED!=1)$fatal(1,"unconfigured native result production calendar");
 genvar b;
 generate for(b=0;b<32;b=b+1)begin:source_age
  initial if(CAPTURE_AGES[b*32+:32]!=SOURCE_CAPTURE_AGE)
   $fatal(1,"collector capture age differs from actual finalizer source");
 end endgenerate
 ot_qwen_tp8_pv256_finalize_static #(.P0_AGE(P0_AGE),.P1_AGE(P1_AGE),.R_AGE(R_AGE),.ADD_LAT(ADD_LAT),.MUL_LAT(MUL_LAT))arithmetic(
 .clk_join(clk_join),.clk_control(clk_control),.rst_n(rst_n),.start(start),.epoch(epoch),.layer(layer),
 .reciprocal(reciprocal),.reciprocal_valid(reciprocal_valid),.reciprocal_ready(),.reciprocal_epoch(reciprocal_epoch),
 .p0_valid(p0_valid),.p1_valid(p1_valid),.p0_ready(),.p1_ready(),.p0_epoch(p0_epoch),.p1_epoch(p1_epoch),
 .p0_partial(p0_partial),.p1_partial(p1_partial),.out_valid(),.out_ready(1'b1),.out_data(nd),.out_epoch(),
 .node_valid(nv),.node_epoch(ne),.node_layer(nl),.fault(arithmetic_fault));
 qkd_result_static #(.CAPTURE_AGES(CAPTURE_AGES),.STACK_FIRST(STACK_FIRST))collection(
 .clk_node(clk_join),.clk_merge(clk_merge),.rst_n(rst_n),.cmd_v({32{start}}),.cmd_epoch({32{epoch}}),.cmd_layer({32{layer}}),
 .merge_cmd_v(start),.producer_v(nv),.producer_epoch(ne),.producer_layer(nl),.producer_data(nd),
 .result_v(collected_v),.result_record(collected_record),.fault(transport_fault));
 assign fault=(CONFIGURED!=1)||arithmetic_fault||transport_fault;
endmodule
