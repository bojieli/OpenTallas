module ot_hdc_fp32_add_lat_fan32 #(parameter integer LAT=3,CUTS=-1,DRST=1,SAFE_DIST=0,SLICE_W=4)(input wire clk,rst_n,valid_in,input wire[31:0]a,b,output wire[31:0]y,output wire[1:0]err,output wire valid_out);
 generate if(SAFE_DIST!=0 && LAT==7 && DRST==0 && (CUTS==-1 || CUTS==15))begin:g_native
 ot_hdc_fp32_add_lat7_fan32_native u(.*);
 end else begin:g_legacy
 ot_hdc_fp32_add_lat #(.LAT(LAT),.CUTS(CUTS),.DRST(DRST)) u(.*);
 end endgenerate
endmodule
