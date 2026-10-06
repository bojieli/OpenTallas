`timescale 1ns/1ps
// CORE-side after EXISTING ot_hbm_accel_owned_crossing. No new FIFO, clock,
// SRAM, image/oracle data or grant dictionary. Actual installed span/issuer
// must remain immutable through delivery and future-reader leases.
module ot_hbm_qwen_code_leaf_map #(parameter integer ENABLE=0,RANK_LIMIT=4,ROWS=4496)(
 input wire clk,por_n,input wire owned_v,output wire owned_r,
 input ot_hbm_r14_pkg::owned_t owned,
 input wire owned_we,owned_credit,
 input wire installed_span_valid,input wire[1:0] span_stack,
 input wire[33:0] span_first_sector,input wire[13:0] span_rows,
 input wire[12:0] span_first_row,input wire[11:0] span_first_column,
 input wire[63:0] operation,input wire[31:0] phase,input wire[6:0] global_rank,
 input wire hardware_owner_valid,input ot_hbm_r14_pkg::identity_t expected_identity,
 output wire leaf_v,output wire[592:0] leaf_packet,
 input wire private_visible,input wire[336:0] private_visible_key,
 output wire fault
);
 wire[34:0] end_sector={1'b0,span_first_sector}+({21'b0,span_rows}<<1);
 wire[34:0] delta={1'b0,owned.id.sector}-{1'b0,span_first_sector};
 wire[34:0] destrow={22'b0,span_first_row}+(delta>>1);
 wire[12:0] row=destrow[12:0];wire[11:0] col={11'b0,delta[0]};
 wire span_ok=installed_span_valid&&span_rows!=0&&span_rows<=ROWS&&span_first_column==0&&
   ({1'b0,span_first_row}+span_rows)<=ROWS&&end_sector<=35'd703125000&&
   owned.id.stack==span_stack&&owned.id.sector>=span_first_sector&&{1'b0,owned.id.sector}<end_sector&&destrow<ROWS;
 wire identity_ok=hardware_owner_valid&&owned.id==expected_identity;
 wire legal=span_ok&&identity_ok&&!owned_we&&!owned_credit&&global_rank<7'(RANK_LIMIT);
 wire[336:0] key={operation,phase,global_rank,row,col,owned.id,owned.physical_tag,owned.beat};
 reg sticky;
 assign leaf_v=ENABLE&&owned_v&&legal&&!sticky;
 assign leaf_packet=ENABLE?{operation,phase,global_rank,row,col,owned}:593'b0;
 assign owned_r=leaf_v&&private_visible&&private_visible_key==key;
 assign fault=ENABLE&&sticky;
 always @(posedge clk or negedge por_n)if(!por_n)sticky<=0;else if(ENABLE)begin
 if(owned_v&&installed_span_valid&&hardware_owner_valid&&!legal)sticky<=1;
 if(private_visible&&(!leaf_v||private_visible_key!=key))sticky<=1;
 end
endmodule
