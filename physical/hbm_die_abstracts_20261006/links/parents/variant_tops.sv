// Fixed elaboration aliases of ONE parameterized implementation.
// Default-off, not hardened views; source-owner parent packing still OPEN.
module ot_hbm_station_mcast3 #(parameter integer ENABLE=0, parameter [191:0] COHORT_MASK={192{1'b1}})(
 input wire fclk_i,input wire [3:0] rst_n,output wire fclk_o,input wire quiesce,
 input wire [0:0] in_v,output wire [0:0] in_r,
 input wire [2062:0] in_data,input wire [191:0] in_owner,
 output wire [2:0] out_v,input wire [2:0] out_r,
 output wire [6188:0] out_data,output wire [575:0] out_owner,
 input wire [2:0] ACK_v,input wire [575:0] ACK_owner,
 output wire source_release,drained,paused,fault
);
 ot_hbm_native_station #(.MODE(1),.ENABLE(ENABLE),.W(2063),.NI(1),.NO(3),.IW(2063),.COHORT_MASK(COHORT_MASK)) u_station(
 .i_v(1'b0),.i_d(2063'b0),.o_v(),.o_d(),.*);
endmodule
module ot_hbm_station_mcast4 #(parameter integer ENABLE=0, parameter [191:0] COHORT_MASK={192{1'b1}})(
 input wire fclk_i,input wire [3:0] rst_n,output wire fclk_o,input wire quiesce,
 input wire [0:0] in_v,output wire [0:0] in_r,
 input wire [2062:0] in_data,input wire [191:0] in_owner,
 output wire [3:0] out_v,input wire [3:0] out_r,
 output wire [8251:0] out_data,output wire [767:0] out_owner,
 input wire [3:0] ACK_v,input wire [767:0] ACK_owner,
 output wire source_release,drained,paused,fault
);
 ot_hbm_native_station #(.MODE(1),.ENABLE(ENABLE),.W(2063),.NI(1),.NO(4),.IW(2063),.COHORT_MASK(COHORT_MASK)) u_station(
 .i_v(1'b0),.i_d(2063'b0),.o_v(),.o_d(),.*);
endmodule
module ot_hbm_station_gather2 #(parameter integer ENABLE=0, parameter [191:0] COHORT_MASK={192{1'b1}})(
 input wire fclk_i,input wire [3:0] rst_n,output wire fclk_o,input wire quiesce,
 input wire [1:0] in_v,output wire [1:0] in_r,
 input wire [539:0] in_data,input wire [383:0] in_owner,
 output wire [0:0] out_v,input wire [0:0] out_r,
 output wire [539:0] out_data,output wire [191:0] out_owner,
 input wire [0:0] ACK_v,input wire [191:0] ACK_owner,
 output wire source_release,drained,paused,fault
);
 ot_hbm_native_station #(.MODE(2),.ENABLE(ENABLE),.W(540),.NI(2),.NO(1),.IW(270),.COHORT_MASK(COHORT_MASK)) u_station(
 .i_v(1'b0),.i_d(540'b0),.o_v(),.o_d(),.*);
endmodule
module ot_hbm_station_gather4 #(parameter integer ENABLE=0, parameter [191:0] COHORT_MASK={192{1'b1}})(
 input wire fclk_i,input wire [3:0] rst_n,output wire fclk_o,input wire quiesce,
 input wire [3:0] in_v,output wire [3:0] in_r,
 input wire [1079:0] in_data,input wire [767:0] in_owner,
 output wire [0:0] out_v,input wire [0:0] out_r,
 output wire [1079:0] out_data,output wire [191:0] out_owner,
 input wire [0:0] ACK_v,input wire [191:0] ACK_owner,
 output wire source_release,drained,paused,fault
);
 ot_hbm_native_station #(.MODE(2),.ENABLE(ENABLE),.W(1080),.NI(4),.NO(1),.IW(270),.COHORT_MASK(COHORT_MASK)) u_station(
 .i_v(1'b0),.i_d(1080'b0),.o_v(),.o_d(),.*);
endmodule
module ot_hbm_station_gather8 #(parameter integer ENABLE=0, parameter [191:0] COHORT_MASK={192{1'b1}})(
 input wire fclk_i,input wire [3:0] rst_n,output wire fclk_o,input wire quiesce,
 input wire [7:0] in_v,output wire [7:0] in_r,
 input wire [2159:0] in_data,input wire [1535:0] in_owner,
 output wire [0:0] out_v,input wire [0:0] out_r,
 output wire [2159:0] out_data,output wire [191:0] out_owner,
 input wire [0:0] ACK_v,input wire [191:0] ACK_owner,
 output wire source_release,drained,paused,fault
);
 ot_hbm_native_station #(.MODE(2),.ENABLE(ENABLE),.W(2160),.NI(8),.NO(1),.IW(270),.COHORT_MASK(COHORT_MASK)) u_station(
 .i_v(1'b0),.i_d(2160'b0),.o_v(),.o_d(),.*);
endmodule
