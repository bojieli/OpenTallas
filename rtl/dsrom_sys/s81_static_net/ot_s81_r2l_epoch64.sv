`timescale 1ns/1ps
`default_nettype none
// Source /3, epoch /12, serial /4 from the same VCO. Three useful words and one compiled bubble per source frame.
// Rising-edge ingress repairs the old falling-edge pin seam. No direct source->serial data or control path exists.
module ot_s81_r2l_epoch_slice64 #(parameter integer MUT=0)(
 input wire clk_source,clk_epoch,clk_serial,
 input wire rst_source_n,rst_epoch_n,rst_serial_n,input wire [65:0] di,
 output reg [63:0] data,output reg raw_valid,raw_live,raw_fault);
 reg [65:0] capture_q;
 always @(posedge clk_source or negedge rst_source_n)
  if(!rst_source_n)capture_q<=0;else capture_q<=di;
 reg [64:0] source_bank[0:2];reg [23:0] source_tag[0:2];
 reg [1:0] source_phase;reg [23:0] source_frame;reg [2:0] written;reg source_fault;
 always @(posedge clk_source or negedge rst_source_n)
  if(!rst_source_n)begin source_phase<=0;source_frame<=0;written<=0;source_fault<=0;end
  else if(!capture_q[0])begin source_phase<=0;source_frame<=0;written<=0;source_fault<=0;end
  else begin
   if(source_phase<3)begin
    source_bank[source_phase]<=capture_q[65:1] ^ ((MUT==1 && source_phase==1)?65'd2:65'd0);
    source_tag[source_phase]<=source_frame;written[source_phase]<=1'b1;
   end else if(capture_q[1])source_fault<=1'b1;
   source_phase<=source_phase+1'b1;
   if(source_phase==3)source_frame<=source_frame+1'b1;
  end
 // Three independent direct registered seams into the common epoch domain: no 3:4 mux crossing.
 reg [64:0] epoch_bank[0:2];
 always @(posedge clk_epoch)begin
  epoch_bank[0]<=source_bank[0];epoch_bank[1]<=source_bank[1];epoch_bank[2]<=source_bank[2];
 end
 reg start_seen,run_epoch,epoch_fault;reg [23:0] expected_frame;
 always @(posedge clk_epoch or negedge rst_epoch_n)
  if(!rst_epoch_n)begin start_seen<=0;run_epoch<=0;epoch_fault<=0;expected_frame<=0;end
  else begin
   start_seen<=capture_q[0];
   // Fixed initialization: start_seen is sampled once; the next epoch is frame0. Invalid/missing data faults;
   // it never postpones this timeline or inserts a production wait.
   if(start_seen||run_epoch)begin
    run_epoch<=1'b1;expected_frame<=expected_frame+1'b1;
    if(!capture_q[0] || written!=3'b111 || source_fault ||
       source_tag[0]!=expected_frame || source_tag[1]!=expected_frame || source_tag[2]!=expected_frame || MUT==2)
     epoch_fault<=1'b1;
   end
  end
 reg [1:0] read_phase;reg [63:0] word_q;
 wire [64:0] selected=(read_phase==0)?epoch_bank[0]:(read_phase==1)?epoch_bank[1]:epoch_bank[2];
 always @(posedge clk_serial)word_q<=selected[64:1];
 always @(posedge clk_serial or negedge rst_serial_n)
  if(!rst_serial_n)begin read_phase<=0;raw_valid<=0;raw_live<=0;raw_fault<=0;end
  else begin
   if(run_epoch)begin
    read_phase<=(read_phase==2)?0:read_phase+1'b1;
    raw_valid<=selected[0];raw_live<=1'b1;
   end else begin read_phase<=0;raw_valid<=0;raw_live<=0;end
   if(epoch_fault)raw_fault<=1'b1;
  end
 always @(posedge clk_serial)data<=word_q;
endmodule

// Wires-only parent: 8 real three-root data leaves plus one real serial status leaf.
module dsfd_r2l_epoch64 #(parameter integer MUT=0)(
 input wire [7:0] clk_source,clk_epoch,input wire [8:0] clk_serial,
 input wire [7:0] rst_source_n,rst_epoch_n,rst_serial_n,
 input wire [513:0] di0,output wire [514:0] o);
 wire [7:0] v,l,f;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:group
  ot_s81_r2l_epoch_slice64 #(.MUT(g==7?MUT:0)) u(
   .clk_source(clk_source[g]),.clk_epoch(clk_epoch[g]),.clk_serial(clk_serial[g]),
   .rst_source_n(rst_source_n[g]),.rst_epoch_n(rst_epoch_n[g]),.rst_serial_n(rst_serial_n[g]),
   .di({di0[2+64*g+:64],di0[1:0]}),.data(o[1+64*g+:64]),
   .raw_valid(v[g]),.raw_live(l[g]),.raw_fault(f[g]));
 end endgenerate
 ot_s81_r2l_join8 status(.ck(clk_serial[8]),.valid_i(v),.live_i(l),.fault_i(f),
  .valid_o(o[0]),.live_o(o[513]),.fault_o(o[514]));
endmodule
`default_nettype wire
