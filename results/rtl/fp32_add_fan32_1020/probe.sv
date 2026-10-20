module fan32_probe(input wire clk,rst_n,valid_in,input wire[31:0]a,b,output wire[31:0]y,output wire[1:0]err,output wire valid_out);
 ot_hdc_fp32_add_lat_fan32 #(.LAT(7),.DRST(0),.SAFE_DIST(1),.SLICE_W(4)) u(.*);
endmodule
