`default_nettype none
module ot_wbq_sw #(parameter integer WOPEN=0, parameter integer CRED=4, parameter [29:0] STACK_SECTORS=30'd703125000, parameter integer HREG=2, parameter integer GIN=1)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [1:0] stk,input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire [15:0] wb_reserve_epoch,wb_fill_epoch,
 input wire [11:0] wb_reserve_sectors,input wire [31:0] wb_reserve_base,
 input wire wb_fill_start,
 input wire [263:0] wd_c,                // per sector {valid, sector[31:0]}
 output wire wb_ready,output wire [11:0] wa,
 output wire wbw_v,output wire [29:0] wbw_base,output wire [11:0] wbw_total,
 output wire [15:0] w_k_v,input wire [15:0] w_k_rdy,output wire [479:0] w_k_addr,output wire [4095:0] w_k_wdata,
 input wire [15:0] w_k_wr_done,
 output wire fault,
 // seam to the roots
 input wire [3:0] root_ready,
 input wire [7:0] g_v,input wire [2287:0] g_d,
 output wire [7:0] g_credit,
 output wire [7:0] root_id,
 output wire copy_on,copy_sel,s_stop,h_stop
);
 wire [15:0] send_v,send_ready;wire [479:0] send_addr;wire [4095:0] send_data;
 ot_wbq_sw_split_main #(.WOPEN(WOPEN),.CRED(CRED),.STACK_SECTORS(STACK_SECTORS),.HREG(HREG),.GIN(GIN)) u_main (
 .stream_clk(stream_clk),
 .stream_rst_n(stream_rst_n),
 .hbm_clk(hbm_clk),
 .hbm_rst_n(hbm_rst_n),
 .stk(stk),
 .quad(quad),
 .wb_reserve_v(wb_reserve_v),
 .wb_reserve_bank(wb_reserve_bank),
 .wb_fill_bank(wb_fill_bank),
 .wb_reserve_epoch(wb_reserve_epoch),
 .wb_fill_epoch(wb_fill_epoch),
 .wb_reserve_sectors(wb_reserve_sectors),
 .wb_reserve_base(wb_reserve_base),
 .wb_fill_start(wb_fill_start),
 .wd_c(wd_c),
 .wb_ready(wb_ready),
 .wa(wa),
 .wbw_v(wbw_v),
 .wbw_base(wbw_base),
 .wbw_total(wbw_total),
 .w_k_v(send_v),
 .w_k_rdy(send_ready),
 .w_k_addr(send_addr),
 .w_k_wdata(send_data),
 .w_k_wr_done(w_k_wr_done),
 .fault(fault),
 .root_ready(root_ready),
 .g_v(g_v),
 .g_d(g_d),
 .g_credit(g_credit),
 .root_id(root_id),
 .copy_on(copy_on),
 .copy_sel(copy_sel),
 .s_stop(s_stop),
 .h_stop(h_stop));
 ot_wbq_sw_split_out u_out(.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.in_v(send_v),.in_ready(send_ready),.in_addr(send_addr),.in_data(send_data),
 .w_k_v(w_k_v),.w_k_rdy(w_k_rdy),.w_k_addr(w_k_addr),.w_k_wdata(w_k_wdata));
endmodule
`default_nettype wire
