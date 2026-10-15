`timescale 1ns/1ps
// Complete released embedding vocabulary, exactly one global table copy.
// This logical composition exposes all12HEAD shard clocks; physical link
// pipelines are separately measured and included in the static calendar.
module ot_s81_embed_full_table #(parameter integer MUTANT=0)(
 input wire clk,rst_n,start,
 input wire [95:0] rom_clocks,
 input wire [16:0] token,
 input wire [13:0] vm_base,
 input wire [511:0] header,
 output wire busy,done,fault,vm_v,
 output wire [13:0] vm_row,
 output wire [511:0] vm_d,
 output wire hop_v,hop_last,
 output wire [511:0] hop_d
);
 wire [3:0] bv,dv,fv,vv,hv,hl;
 wire [55:0] rows;
 wire [2047:0] vd,hd;
 reg invalid_command;
 for(genvar owner=0;owner<4;owner=owner+1) begin: quarters
  ot_s81_embed_full_home #(.OWNER(owner),.MUTANT(MUTANT)) home(
   .clk(clk),.rst_n(rst_n),.rom_clocks(rom_clocks[24*owner+:24]),
   .start(start && token/32320==owner),.token(token),.vm_base(vm_base),.header(header),
   .busy(bv[owner]),.done(dv[owner]),.fault(fv[owner]),.vm_v(vv[owner]),.vm_row(rows[14*owner+:14]),
   .vm_d(vd[512*owner+:512]),.hop_v(hv[owner]),.hop_last(hl[owner]),.hop_d(hd[512*owner+:512]));
 end
 always @(posedge clk) begin
  if(!rst_n) invalid_command<=0;
  else if(start && (token>=129280 || busy)) invalid_command<=1;
 end
 assign busy=|bv;assign done=|dv;assign fault=(|fv)|invalid_command;
 assign vm_v=|vv; assign hop_v=|hv;assign hop_last=|hl;
 assign vm_row=({14{vv[0]}}&rows[0+:14])|({14{vv[1]}}&rows[14+:14])|
               ({14{vv[2]}}&rows[28+:14])|({14{vv[3]}}&rows[42+:14]);
 assign vm_d=({512{vv[0]}}&vd[0+:512])|({512{vv[1]}}&vd[512+:512])|
             ({512{vv[2]}}&vd[1024+:512])|({512{vv[3]}}&vd[1536+:512]);
 assign hop_d=({512{hv[0]}}&hd[0+:512])|({512{hv[1]}}&hd[512+:512])|
              ({512{hv[2]}}&hd[1024+:512])|({512{hv[3]}}&hd[1536+:512]);
endmodule
