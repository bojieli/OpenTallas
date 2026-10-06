// Shared primitive view preparation only; NOT the dsfd_cfifo parent.
// No W512 view/capacitance/area inheritance. Matches S81 r8 W564 entry.
module ot_meso_w564_preview #(parameter ENABLE=0)(
 input wire wclk,wrst_n,w_v,output wire w_rdy,input wire [563:0] w_d,
 input wire rclk,rrst_n,output wire r_v,input wire r_rdy,output wire [563:0] r_d,
 output wire w_live,r_live,w_fault,r_fault
);
 ot_meso_fifo #(.W(564),.ENABLE(ENABLE)) u_fifo(.*);
endmodule
