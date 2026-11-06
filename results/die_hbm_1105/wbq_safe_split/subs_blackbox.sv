module ot_wbq_sw_split_main #(parameter integer WOPEN=0, parameter integer CRED=4, parameter [29:0] STACK_SECTORS=30'd703125000, parameter integer HREG=0, parameter integer GIN=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [1:0] stk,input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire [15:0] wb_reserve_epoch,wb_fill_epoch,
 input wire [11:0] wb_reserve_sectors,input wire [31:0] wb_reserve_base,
 input wire wb_fill_start,
 input wire [263:0] wd_c,                // per sector {valid, sector[31:0]}
 output reg wb_ready,output reg [11:0] wa,
 output reg wbw_v,output reg [29:0] wbw_base,output reg [11:0] wbw_total,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata,
 input wire [15:0] w_k_wr_done,
 output reg fault,
 // seam to the roots
 input wire [3:0] root_ready,
 input wire [7:0] g_v,input wire [2287:0] g_d,
 output wire [7:0] g_credit,
 output reg [7:0] root_id,
 output wire copy_on,copy_sel,s_stop,h_stop
);
endmodule
module ot_wbq_sw_split_out #(parameter integer MUT=0)(
 input wire hbm_clk,hbm_rst_n,
 input wire [15:0] in_v,output wire [15:0] in_ready,
 input wire [479:0] in_addr,input wire [4095:0] in_data,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,
 output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata
);
endmodule
