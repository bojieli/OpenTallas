// DIE-HBM-62/KPORT d44v: plan module ot_hbm_svc_wb_kport_q = thin parent glue of the split hard core (wires only; u_hub and
// u_root0..3 of ot_hbm_svc_wb_kport_q__split are the hard cores, each with its own kit face shell).
`default_nettype none
module ot_hbm_svc_wb_kport_q__fcore (
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,
 input wire[1:0]stk,
 input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output wire wb_ready,output wire[11:0]wa,
 output wire wbw_v,output wire[29:0]wbw_base,output wire[11:0]wbw_total,
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output wire fault
);
 ot_hbm_svc_wb_kport_q__split u_core (.stream_clk(stream_clk), .stream_rst_n(stream_rst_n), .hbm_clk(hbm_clk), .hbm_rst_n(hbm_rst_n), .stream_fifo_clk(stream_fifo_clk), .stk(stk), .quad(quad), .wb_reserve_v(wb_reserve_v), .wb_reserve_bank(wb_reserve_bank), .wb_fill_bank(wb_fill_bank), .wb_reserve_epoch(wb_reserve_epoch), .wb_fill_epoch(wb_fill_epoch), .wb_reserve_sectors(wb_reserve_sectors), .wb_reserve_base(wb_reserve_base), .wb_fill_start(wb_fill_start), .wd(wd), .wb_ready(wb_ready), .wa(wa), .wbw_v(wbw_v), .wbw_base(wbw_base), .wbw_total(wbw_total), .w_k_v(w_k_v), .w_k_rdy(w_k_rdy), .w_k_addr(w_k_addr), .w_k_wdata(w_k_wdata), .w_k_wr_done(w_k_wr_done), .fault(fault));
endmodule
module ot_hbm_svc_wb_kport_q (
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,
 input wire[1:0]stk,
 input wire quad,
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output wire wb_ready,output wire[11:0]wa,
 output wire wbw_v,output wire[29:0]wbw_base,output wire[11:0]wbw_total,
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output wire fault
);
 ot_hbm_svc_wb_kport_q__fcore u_fcore (.stream_clk(stream_clk), .stream_rst_n(stream_rst_n), .hbm_clk(hbm_clk), .hbm_rst_n(hbm_rst_n), .stream_fifo_clk(stream_fifo_clk), .stk(stk), .quad(quad), .wb_reserve_v(wb_reserve_v), .wb_reserve_bank(wb_reserve_bank), .wb_fill_bank(wb_fill_bank), .wb_reserve_epoch(wb_reserve_epoch), .wb_fill_epoch(wb_fill_epoch), .wb_reserve_sectors(wb_reserve_sectors), .wb_reserve_base(wb_reserve_base), .wb_fill_start(wb_fill_start), .wd(wd), .wb_ready(wb_ready), .wa(wa), .wbw_v(wbw_v), .wbw_base(wbw_base), .wbw_total(wbw_total), .w_k_v(w_k_v), .w_k_rdy(w_k_rdy), .w_k_addr(w_k_addr), .w_k_wdata(w_k_wdata), .w_k_wr_done(w_k_wr_done), .fault(fault));
endmodule
`default_nettype wire
