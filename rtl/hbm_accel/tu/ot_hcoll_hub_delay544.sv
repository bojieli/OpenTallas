`timescale 1ns/1ps
// Extract the existing SRAM-backed HUBW35 flight without changing an epoch.
// The544-bit input capture, three real128x256 SRAMs, read capture and35-stage
// valid pipeline all belong to this root. This is not a sampled clock path.
module ot_hcoll_hub_delay544 #(parameter integer MUT=0)(
 input wire clk,rst_n,valid,input wire[543:0]data,output wire reply_v,output wire[543:0]reply
);
 wire[0:0]rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 ot_hcoll_sdelay #(.W(544),.D(MUT==1?34:35))u_delay(.clk(clk),.rst_n(rr[0]),.v_in(valid),.d_in(data),.v_out(reply_v),.d_out(reply));
endmodule
