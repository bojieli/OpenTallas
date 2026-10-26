`timescale 1ps/1fs
module kv_native_mission_gate #(parameter integer MUT=0)(input wire clk,rst_n,request,static_setup_ready,program_ready,mission_start,output wire boot_begin);
 localparam integer REQUIRE_MISSION_START=1;
 wire installed = static_setup_ready && program_ready && (!REQUIRE_MISSION_START || mission_start);
 qkd_d2d_boot_event_bridge #(.ENABLE(1)) u_bridge(clk,rst_n,request,MUT==1?(static_setup_ready&&program_ready):MUT==2?1'b0:installed,boot_begin);
endmodule
