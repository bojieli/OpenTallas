`timescale 1ns/1ps
// GENERATED from the original golden-order pairwise reduction; zero extra edges.
module ot_v41_bf_reduce #(
 parameter integer NIN=16,LEVELS=1,TRW=7,
 parameter [8:0] CUT=9'b1_1111_1111,
 parameter integer NOUT=NIN>>LEVELS,
 parameter integer LAT=1+CUT[0]+CUT[1]+CUT[2]+CUT[3]+CUT[4]+CUT[5]+CUT[6]+CUT[7]+CUT[8]
)(input wire fclk,rst_pin,ze_d,iv,
 input wire [32*NIN-1:0] values_in,
 input wire [NIN-1:0] errors_in,
 input wire [TRW:0] tag_in,
 output wire ov,
 output wire [32*NOUT-1:0] values_out,
 output wire [NOUT-1:0] errors_out,
 output wire [TRW:0] tag_out);
 wire clk,rst_n;
 ot_v41_tile_clk u_tc(.fclk(fclk),.rst_pin(rst_pin),.ze_d(ze_d),.gclk(clk),.rst_n(rst_n));
 wire [31:0] val[0:LEVELS][0:NIN-1];
 wire [NIN-1:0] err[0:LEVELS];
 wire [LEVELS:0] valid;
 wire [TRW:0] tag[0:LEVELS];
 assign valid[0]=iv;assign tag[0]=tag_in;
 for(genvar n=0;n<NIN;n++) begin:g_input
  assign val[0][n]=values_in[32*n +:32];assign err[0][n]=errors_in[n];
 end
 for(genvar lv=0;lv<LEVELS;lv++) begin:g_level
  localparam integer NN=NIN>>(lv+1);
  for(genvar k=0;k<NN;k++) begin:g_node
   wire [1:0] e;wire vo;
   ot_v41_fadd #(.CUT(CUT)) u_a(.clk(clk),.rst_n(rst_n),.valid_in(valid[lv]),
    .a(val[lv][2*k]),.b(val[lv][2*k+1]),.y(val[lv+1][k]),.err(e),.valid_out(vo));
   reg [LAT-1:0] ep;
   always @(posedge clk) ep<={ep[LAT-2:0],err[lv][2*k]|err[lv][2*k+1]};
   assign err[lv+1][k]=ep[LAT-1]|(e!=2'd0);
  end
  for(genvar k=NN;k<NIN;k++) begin:g_zero
   assign val[lv+1][k]=32'd0;assign err[lv+1][k]=1'b0;
  end
  reg [LAT-1:0] vp;
  always @(posedge clk or negedge rst_n) if(!rst_n)vp<='0;else vp<={vp[LAT-2:0],valid[lv]};
  assign valid[lv+1]=vp[LAT-1];
  ot_hdc_delay #(.W(TRW+1),.D(LAT)) u_tag(.clk(clk),.rst_n(rst_n),.d(tag[lv]),.q(tag[lv+1]));
 end
 for(genvar n=0;n<NOUT;n++) begin:g_output
  assign values_out[32*n +:32]=val[LEVELS][n];assign errors_out[n]=err[LEVELS][n];
 end
 assign ov=valid[LEVELS];assign tag_out=tag[LEVELS];
endmodule
