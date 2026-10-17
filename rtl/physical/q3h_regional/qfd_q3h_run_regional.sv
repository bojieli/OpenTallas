`timescale 1ns/1ps
module qfd_q3h_run_regional #(parameter integer W=514,parameter integer D=1)(
 input wire [((D>0)?D:1)-1:0] ck_stage,
 input wire [W-1:0] d, output wire [W-1:0] q);
 generate if(D==0)begin:g_wire assign q=d;end
 else begin:g_run
   wire [W-1:0] s[0:D];assign s[0]=d;
   for(genvar i=0;i<D;i=i+1)begin:g_s
     qfd_q3h_stn #(.W(W),.N(1)) u_s(.ck(ck_stage[i]),.d(s[i]),.q(s[i+1]));
   end
   assign q=s[D];
 end endgenerate
endmodule
