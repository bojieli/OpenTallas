`timescale 1ns/1ps
// Native fixed edge delay, with real kept hold-delay cells before existing FFs.
// No register or reset semantic change. HB delay is combinational identity.
module ot_qfd_su_delay_hold #(parameter integer W=32,D=1,RESET=0)(
 input wire clk,rst_n,input wire[W-1:0]d,output wire[W-1:0]q
);
 generate if(D==0)begin:g_wire
 assign q=d;
 end else begin:g_line
 reg[W*D-1:0]line;
 wire[W*D-1:0]next_data;
 wire[W*D-1:0]padded;
 if(D==1)begin:g_next_one
 assign next_data=d;
 end else begin:g_next_many
 assign next_data={line[W*(D-1)-1:0],d};
 end
 for(genvar k=0;k<W*D;k=k+1)begin:g_bit
`ifdef SYNTHESIS
 (* keep *) HB4xp67_ASAP7_75t_R u_hdly_native (.A(next_data[k]),.Y(padded[k]));
`else
 assign padded[k]=next_data[k];
`endif
 end
 if(RESET!=0)begin:g_reset
 always @(posedge clk or negedge rst_n)if(!rst_n)line<=0;else line<=padded;
 end else begin:g_data
 always @(posedge clk)line<=padded;
 end
 assign q=line[W*D-1-:W];
 end endgenerate
endmodule
