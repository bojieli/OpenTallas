`timescale 1ns/1ps
// Default-off bounded native implementation. Released original RTL remains unchanged.
// SAFE_DIST1 is qualified ONLY for LAT7/DRST0/CUTS=-1; unsupported opt-ins fail elaboration.
module ot_hdc_fp32_add_lat_fan32 #(
 parameter integer LAT=3,
 parameter integer CUTS=-1,
 parameter integer DRST=`ifdef OT_FP_DATA_NORST 0 `else 1 `endif,
 parameter integer SAFE_DIST=0
)(input wire clk,rst_n,valid_in,input wire [31:0] a,b,
  output wire [31:0] y,output wire [1:0] err,output wire valid_out);
 generate
  if(SAFE_DIST==0) begin:g_released
   ot_hdc_fp32_add_lat #(.LAT(LAT),.CUTS(CUTS),.DRST(DRST)) u_original(.*);
  end else if(SAFE_DIST==1 && LAT==7 && DRST==0 && CUTS==-1) begin:g_native7
   ot_hdc_fp32_add_lat7_fan32_native u_native(.*);
  end else begin:g_unsupported_profile
   // Deliberately undefined: synthesis and simulation must reject unsupported opt-ins.
   OT_HDC_FAN32_UNSUPPORTED_PROFILE_REQUIRES_SAFE1_LAT7_DRST0_CUTS_MINUS1 u_refuse();
  end
 endgenerate
endmodule
