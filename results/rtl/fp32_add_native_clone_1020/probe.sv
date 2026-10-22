module fan32_graph_input(input wire clk,rst_n,valid_in,input wire[31:0]a,b,output wire[31:0]y,output wire[1:0]err,output wire valid_out);
 ot_hdc_fp32_add_lat #(.LAT(7),.DRST(0)) u(.*);
endmodule
