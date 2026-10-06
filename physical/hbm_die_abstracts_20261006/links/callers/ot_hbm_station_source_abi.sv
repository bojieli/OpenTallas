`timescale 1ns/1ps
// One parameterized ABI adapter, not a hardened station or new controller.
// Default off. Zero storage/cycles/debt. Source endpoint logic/clock/reset is
// retained by its owner. No clock forwarding, ACK, ready or protection invented.
// FUNCTION3: actual hierarchical SM named command/status directions.
// FUNCTION4: actual TU PHY RX/TX and CORE credit directions, separate domains.
module ot_hbm_station_source_abi #(
 parameter integer ENABLE=0,FUNCTION=3,NSM=8,NPT=8,FW=512,PWT=FW+33
)(
 input wire clk_sm,rst_sm_n,pclk,prst_n,
 output wire sm_clk,sm_rst_n,endpoint_clk,endpoint_rst_n,endpoint_pclk,endpoint_prst_n,
 input wire [NSM-1:0] start,release_in,d_valid,
 input wire [NSM*13-1:0] op_rows,input wire [NSM*16-1:0] op_c,
 input wire [NSM*8-1:0] op_g,input wire [NSM-1:0] op_gs,
 input wire [NSM*2-1:0] op_fmt,input wire [NSM*7-1:0] op_xb,
 input wire [NSM*32-1:0] d_base,input wire [NSM*24-1:0] d_lines,
 output wire [NSM-1:0] sm_start,sm_release_in,sm_d_valid,
 output wire [NSM*13-1:0] sm_op_rows,output wire [NSM*16-1:0] sm_op_c,
 output wire [NSM*8-1:0] sm_op_g,output wire [NSM-1:0] sm_op_gs,
 output wire [NSM*2-1:0] sm_op_fmt,output wire [NSM*7-1:0] sm_op_xb,
 output wire [NSM*32-1:0] sm_d_base,output wire [NSM*24-1:0] sm_d_lines,
 input wire [NSM-1:0] sm_start_ready,sm_busy,sm_arrive,sm_released,sm_d_ready,
 output wire [NSM-1:0] start_ready,busy,arrive,released,d_ready,
 input wire [NPT-1:0] endpoint_tx_v,input wire [NPT*PWT-1:0] endpoint_tx_flit,
 output wire [NPT-1:0] ph_tx_v,output wire [NPT*PWT-1:0] ph_tx_flit,
 input wire [NPT-1:0] ph_rx_v,input wire [NPT*PWT-1:0] ph_rx_flit,
 output wire [NPT-1:0] endpoint_rx_v,output wire [NPT*PWT-1:0] endpoint_rx_flit,
 input wire [NPT-1:0] sw_cr_ret,output wire [NPT-1:0] endpoint_cr_ret,
 input wire [NPT-1:0] endpoint_rx_credit,output wire [NPT-1:0] rx_credit
);
 initial begin
  if(FUNCTION!=3&&FUNCTION!=4)$fatal(1,"unknown actual source ABI");
  if(FUNCTION==4&&PWT!=FW+33)$fatal(1,"actual TU tuple requires FW+kind1+dst8+src8+index16");
 end
 // These clock/reset ports identify the real enclosing domains, not generated
 // roots. No reset-based debt removal or warm acknowledge exists in this adapter.
 wire control_on=ENABLE&&(FUNCTION==3);
 wire duplex_on=ENABLE&&(FUNCTION==4);
 assign sm_clk=control_on?clk_sm:0;assign sm_rst_n=control_on?rst_sm_n:0;
 assign endpoint_clk=duplex_on?clk_sm:0;assign endpoint_rst_n=duplex_on?rst_sm_n:0;
 assign endpoint_pclk=duplex_on?pclk:0;assign endpoint_prst_n=duplex_on?prst_n:0;
 assign sm_start=control_on?start:0;assign sm_release_in=control_on?release_in:0;
 assign sm_d_valid=control_on?d_valid:0;assign sm_op_rows=control_on?op_rows:0;
 assign sm_op_c=control_on?op_c:0;assign sm_op_g=control_on?op_g:0;
 assign sm_op_gs=control_on?op_gs:0;assign sm_op_fmt=control_on?op_fmt:0;
 assign sm_op_xb=control_on?op_xb:0;assign sm_d_base=control_on?d_base:0;
 assign sm_d_lines=control_on?d_lines:0;
 assign start_ready=control_on?sm_start_ready:0;assign busy=control_on?sm_busy:0;
 assign arrive=control_on?sm_arrive:0;assign released=control_on?sm_released:0;
 assign d_ready=control_on?sm_d_ready:0;
 // TX/RX flits and valid are PHY-clock signals. Credits are CORE-clock signals
 // in ot_hbm_accel_tu_endpoint and ot_hbm_tu_shared8. Never put all in a pclk slice.
 assign ph_tx_v=duplex_on?endpoint_tx_v:0;assign ph_tx_flit=duplex_on?endpoint_tx_flit:0;
 assign endpoint_rx_v=duplex_on?ph_rx_v:0;assign endpoint_rx_flit=duplex_on?ph_rx_flit:0;
 assign endpoint_cr_ret=duplex_on?sw_cr_ret:0;assign rx_credit=duplex_on?endpoint_rx_credit:0;
endmodule

// Exact source wire codec, no owner issuer inferred from source data/status.
module ot_hbm_sm_result_codec #(parameter integer NSM=8)(
 input wire [NSM-1:0] rv,fault,input wire [NSM*12-1:0] rrow,
 input wire [NSM*256-1:0] rdata,
 output wire [NSM*270-1:0] die_wire,gather_internal
);
 for(genvar k=0;k<NSM;k=k+1)begin:slot
  assign die_wire[k*270+:270]={fault[k],rdata[k*256+:256],rrow[k*12+:12],rv[k]};
  assign gather_internal[k*270+:270]={fault[k],rv[k],rrow[k*12+:12],rdata[k*256+:256]};
 end
endmodule
