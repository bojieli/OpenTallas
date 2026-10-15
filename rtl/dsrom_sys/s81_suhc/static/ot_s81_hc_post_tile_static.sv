`timescale 1ns/1ps
`default_nettype none
// Actual four-group HCPOST storage+arithmetic tile. Compiler pulses reserve
// independent H/Y writes, computation reads and inspection reads. No readiness
// controls the memory calendar. WB_LAT is a measured implementation contract.
module ot_s81_hc_post_tile_static #(
 parameter integer ROWS=20,WB_LAT=24
)(
 input wire clk,rst_n,
 input wire coef_v,input wire [511:0] comb,input wire [127:0] post,
 input wire h_v,h_slot,input wire [4:0] h_row,input wire [255:0] h_data,
 input wire y_v,y_slot,input wire [4:0] y_row,input wire [127:0] y_data,
 input wire compute_v,compute_slot,input wire [4:0] compute_row,
 input wire inspect_v,inspect_slot,input wire [4:0] inspect_row,
 output reg inspect_out_v,output reg [255:0] inspect_data,
 output reg writeback_v,output reg [4:0] writeback_row,
 output reg writeback_slot,output reg fault
);
 reg cv,hv,hs,yv,ys,rv,rs,iv,ins;
 reg [4:0]hr,yr,rr,ir;
 reg [255:0]hd;reg[127:0]yd;
 reg [511:0]c;reg[127:0]p;
 always @(posedge clk)begin
  hs<=h_slot;hr<=h_row;hd<=h_data;ys<=y_slot;yr<=y_row;yd<=y_data;
  rs<=compute_slot;rr<=compute_row;ins<=inspect_slot;ir<=inspect_row;c<=comb;p<=post;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin cv<=0;hv<=0;yv<=0;rv<=0;iv<=0;end
  else begin cv<=coef_v;hv<=h_v;yv<=y_v;rv<=compute_v;iv<=inspect_v;end
 wire [255:0]hq,yq;
 wire [6:0]h_read_addr=rv?7'(rs*ROWS+rr):7'(ins*ROWS+ir);
 wire [6:0]h_write_addr;
 wire [255:0]h_write_data;
 wire [6:0]y_write_addr=7'(ys*ROWS+yr),y_read_addr=7'(rs*ROWS+rr);
 wire [6:0]wb;
 ot_hdc_delay #(.W(7),.D(WB_LAT),.RESET(1)) wb_calendar(
  .clk(clk),.rst_n(rst_n),.d({rv,rs,rr}),.q(wb));
 wire wb_v=wb[6];
 wire [511:0]arith_out;
 wire [255:0]result;
 for(genvar k=0;k<16;k=k+1)assign result[k*16+:16]=arith_out[k*32+16+:16];
 assign h_write_addr=wb_v?7'(wb[5]*ROWS+wb[4:0]):7'(hs*ROWS+hr);
 assign h_write_data=wb_v?result:hd;
 ot_sram_1r1w_128x256_m1_r2c2 hmem(.clk(clk),.r_ce_in(rv|iv),.r_addr_in(h_read_addr),.rd_out(hq),
  .w_ce_in(wb_v|hv),.w_addr_in(h_write_addr),.wd_in(h_write_data),.w_mask_in({256{1'b1}}),
  .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 ot_sram_1r1w_128x256_m1_r2c2 ymem(.clk(clk),.r_ce_in(rv),.r_addr_in(y_read_addr),.rd_out(yq),
  .w_ce_in(yv),.w_addr_in(y_write_addr),.wd_in({128'd0,yd}),.w_mask_in({256{1'b1}}),
  .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 wire [511:0]r_fp32;
 for(genvar k=0;k<16;k=k+1)assign r_fp32[k*32+:32]={hq[k*16+:16],16'd0};
 reg mem_v,inspect_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin mem_v<=0;inspect_q<=0;inspect_out_v<=0;writeback_v<=0;end
  else begin mem_v<=rv;inspect_q<=iv;inspect_out_v<=inspect_q;writeback_v<=wb_v;end
 always @(posedge clk)begin
  inspect_data<=hq;writeback_row<=wb[4:0];writeback_slot<=wb[5];
 end
 wire arith_v,arith_fault;
 ot_dsrom_su_hcpost #(.NG(4),.WIN(0),.WOUT(0),.ML(5),.AL(4)) arithmetic(
  .clk(clk),.rst_n(rst_n),.go(cv),.comb(c),.post(p),.in_v(mem_v),.in_r(r_fp32),.in_y(yq[127:0]),
  .out_v(arith_v),.out_d(arith_out),.fault(arith_fault));
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else begin
   if((rv&&iv)||(wb_v&&hv)||arith_v!=wb_v||arith_fault)fault<=1;
   if((hv&&hr>=ROWS)||(yv&&yr>=ROWS)||(rv&&rr>=ROWS)||(iv&&ir>=ROWS))fault<=1;
  end
endmodule
`default_nettype wire
