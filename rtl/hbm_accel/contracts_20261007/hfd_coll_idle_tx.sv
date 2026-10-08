`timescale 1ns/1ps
// Physical wrapper: the TX idle-insertion pacer (M = 1024, 200 ppm).
module hfd_coll_idle_tx(input wire clk,rst_n,in_v,output wire slot,send);
 (* ASYNC_REG="TRUE" *) reg [1:0] rst_s;
 always @(posedge clk or negedge rst_n)if(!rst_n)rst_s<=2'b00;else rst_s<={rst_s[0],1'b1};
 ot_hbm_coll_idle_insert #(.M(1024),.PPM(200)) u_i(.clk(clk),.rst_n(rst_s[1]),.in_v(in_v),.slot(slot),.send(send));
endmodule
