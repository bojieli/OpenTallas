module pvj_probe(input wire clk,rst_n,input wire[1023:0]ts0,ts1,ts2,ts3,input wire join_go,input wire[7:0]sf,output wire[511:0]y,output wire y_valid,fault);
 ot_qwen_tp8_pv_join_t #(.RESET_PIN(1),.OUTPUT_LOAD_LOCAL(1)) u(.clk(clk),.rst_n(rst_n),.ts0(ts0),.ts1(ts1),.ts2(ts2),.ts3(ts3),.join_go(join_go),.sf(sf),.y(y),.y_valid(y_valid),.fault(fault));
endmodule
