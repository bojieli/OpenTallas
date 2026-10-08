`timescale 1ns/1ps
// Physical wrapper: the TX idle-insertion pacer (M = 1024, 200 ppm).
module hfd_coll_idle_tx(input wire clk,rst_n,in_v,output wire slot,send);
 ot_hbm_coll_idle_insert #(.M(1024),.PPM(200)) u_i(.*);
endmodule
