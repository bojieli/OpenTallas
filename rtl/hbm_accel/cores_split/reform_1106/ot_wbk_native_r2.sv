`timescale 1ns/1ps
`default_nettype none
// DEFAULT-OFF FULL-CLOCK native R2 family: selected only by an explicit source/profile map.
// Original ot_hbm_svc_wb_kport_q is unchanged. Wire-only hierarchy below adds
// no cycles. Actual child faces/reset stages are retained and must be priced.
// Native K buses have zero added face FFs; parent R2/STA qualification is required.
// Only the verified common-clock, WOPEN0/MUT0/STACK703125000 profile qualifies.
module ot_hbm_svc_wb_kport_q__native_r2_split #(parameter integer WOPEN=0, parameter integer MUT=0,
                               parameter [29:0] STACK_SECTORS=30'd703125000, parameter integer ADAPTER_MUT=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,                 // four stream-frequency clock-tree roots of the WB payload groups
 input wire[1:0]stk,                             // stack identity strap (declared die constant)
 input wire quad,                                // quadrant identity strap: 0 = W half (PCs 0..15), 1 = E half (16..31)
 // DMA write-back side (stream_clk)
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output wire wb_ready,output wire[11:0]wa,
 // WB window command to the quadrant's four kshare leaves (stream_clk; real stack-local sector base / span)
 output wire wbw_v,output wire[29:0]wbw_base,output wire[11:0]wbw_total,
 // K write ports of the quadrant's PCs 16q+0..16q+15 (hbm_clk): single-beat full-strobe writes, real sector address
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output wire fault
);
 ot_hbm_svc_wb_kport_q__native_r2_split_fcore #(.WOPEN(WOPEN),.MUT(MUT),.STACK_SECTORS(STACK_SECTORS),.ADAPTER_MUT(ADAPTER_MUT)) u_fcore (
  .stream_clk(stream_clk),
  .stream_rst_n(stream_rst_n),
  .hbm_clk(hbm_clk),
  .hbm_rst_n(hbm_rst_n),
  .stream_fifo_clk(stream_fifo_clk),
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
  .wd(wd),
  .wb_ready(wb_ready),
  .wa(wa),
  .wbw_v(wbw_v),
  .wbw_base(wbw_base),
  .wbw_total(wbw_total),
  .w_k_v(w_k_v),
  .w_k_rdy(w_k_rdy),
  .w_k_addr(w_k_addr),
  .w_k_wdata(w_k_wdata),
  .w_k_wr_done(w_k_wr_done),
  .fault(fault));
endmodule

module ot_hbm_svc_wb_kport_q__native_r2_split_fcore #(parameter integer WOPEN=0, parameter integer MUT=0,
                               parameter [29:0] STACK_SECTORS=30'd703125000, parameter integer ADAPTER_MUT=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,                 // four stream-frequency clock-tree roots of the WB payload groups
 input wire[1:0]stk,                             // stack identity strap (declared die constant)
 input wire quad,                                // quadrant identity strap: 0 = W half (PCs 0..15), 1 = E half (16..31)
 // DMA write-back side (stream_clk)
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output wire wb_ready,output wire[11:0]wa,
 // WB window command to the quadrant's four kshare leaves (stream_clk; real stack-local sector base / span)
 output wire wbw_v,output wire[29:0]wbw_base,output wire[11:0]wbw_total,
 // K write ports of the quadrant's PCs 16q+0..16q+15 (hbm_clk): single-beat full-strobe writes, real sector address
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output wire fault
);
 ot_hbm_svc_wb_kport_q__native_r2_split_core #(.WOPEN(WOPEN),.MUT(MUT),.STACK_SECTORS(STACK_SECTORS),.ADAPTER_MUT(ADAPTER_MUT)) u_core (
  .stream_clk(stream_clk),
  .stream_rst_n(stream_rst_n),
  .hbm_clk(hbm_clk),
  .hbm_rst_n(hbm_rst_n),
  .stream_fifo_clk(stream_fifo_clk),
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
  .wd(wd),
  .wb_ready(wb_ready),
  .wa(wa),
  .wbw_v(wbw_v),
  .wbw_base(wbw_base),
  .wbw_total(wbw_total),
  .w_k_v(w_k_v),
  .w_k_rdy(w_k_rdy),
  .w_k_addr(w_k_addr),
  .w_k_wdata(w_k_wdata),
  .w_k_wr_done(w_k_wr_done),
  .fault(fault));
endmodule

module ot_hbm_svc_wb_kport_q__native_r2_split_core #(parameter integer WOPEN=0, parameter integer MUT=0,
                               parameter [29:0] STACK_SECTORS=30'd703125000, parameter integer ADAPTER_MUT=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[3:0]stream_fifo_clk,                 // four stream-frequency clock-tree roots of the WB payload groups
 input wire[1:0]stk,                             // stack identity strap (declared die constant)
 input wire quad,                                // quadrant identity strap: 0 = W half (PCs 0..15), 1 = E half (16..31)
 // DMA write-back side (stream_clk)
 input wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 input wire[15:0]wb_reserve_epoch,wb_fill_epoch,
 input wire[11:0]wb_reserve_sectors,input wire[31:0]wb_reserve_base,
 input wire wb_fill_start,
 input wire[2311:0]wd,
 output wire wb_ready,output wire[11:0]wa,
 // WB window command to the quadrant's four kshare leaves (stream_clk; real stack-local sector base / span)
 output wire wbw_v,output wire[29:0]wbw_base,output wire[11:0]wbw_total,
 // K write ports of the quadrant's PCs 16q+0..16q+15 (hbm_clk): single-beat full-strobe writes, real sector address
 output wire[15:0]w_k_v,input wire[15:0]w_k_rdy,output wire[479:0]w_k_addr,output wire[4095:0]w_k_wdata,
 input wire[15:0]w_k_wr_done,
 output wire fault
);
 generate if(WOPEN!=0||MUT!=0||STACK_SECTORS!=30'd703125000)begin:g_unqualified
  initial $fatal(1,"WBK safe native profile requires WOPEN0/MUT0/STACK703125000");
 end endgenerate
 wire[3:0]root_ready;wire[7:0]g_v,g_credit,root_id;wire[2287:0]g_d;
 wire copy_on,copy_sel,s_stop,h_stop;wire[263:0]wd_c;
 wire[7:0]id_m=(ADAPTER_MUT==1)?{root_id[7:4],root_id[1:0],root_id[1:0]}:root_id;
 wire[255:0]wd3_m=(ADAPTER_MUT==2)?{wd[1122:868],wd[867]^1'b1}:wd[867+:256];
 assign wd_c[0+:33]={wd[288],wd[256+:32]};
 assign wd_c[33+:33]={wd[577],wd[545+:32]};
 assign wd_c[66+:33]={wd[866],wd[834+:32]};
 assign wd_c[99+:33]={wd[1155],wd[1123+:32]};
 assign wd_c[132+:33]={wd[1444],wd[1412+:32]};
 assign wd_c[165+:33]={wd[1733],wd[1701+:32]};
 assign wd_c[198+:33]={wd[2022],wd[1990+:32]};
 assign wd_c[231+:33]={wd[2311],wd[2279+:32]};
 ot_wbq_root u_r0(.hbm_clk(hbm_clk),.fifo_clk(stream_fifo_clk[0]),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
 .root_id(id_m[0+:2]),.reserve_v(wb_reserve_v),.reserve_bank(wb_reserve_bank),.reserve_total(wb_reserve_sectors),.reserve_base(wb_reserve_base[29:0]),
 .fill_start(wb_fill_start),.fill_start_bank(wb_fill_bank),
 .wd0(wd[0+:256]),
 .wd1(wd[289+:256]),
 .wd2(wd[578+:256]),
 .wd3(wd3_m),
 .wd4(wd[1156+:256]),
 .wd5(wd[1445+:256]),
 .wd6(wd[1734+:256]),
 .wd7(wd[2023+:256]),
 .wd_v({wd[2311],wd[2022],wd[1733],wd[1444],wd[1155],wd[866],wd[577],wd[288]}),
 .copy_on(copy_on),.copy_bank(copy_sel),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit[0+:2]),
 .root_ready(root_ready[0]),.g_v(g_v[0+:2]),.g_d(g_d[0+:572]));
 ot_wbq_root u_r1(.hbm_clk(hbm_clk),.fifo_clk(stream_fifo_clk[1]),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
 .root_id(id_m[2+:2]),.reserve_v(wb_reserve_v),.reserve_bank(wb_reserve_bank),.reserve_total(wb_reserve_sectors),.reserve_base(wb_reserve_base[29:0]),
 .fill_start(wb_fill_start),.fill_start_bank(wb_fill_bank),
 .wd0(wd[0+:256]),
 .wd1(wd[289+:256]),
 .wd2(wd[578+:256]),
 .wd3(wd3_m),
 .wd4(wd[1156+:256]),
 .wd5(wd[1445+:256]),
 .wd6(wd[1734+:256]),
 .wd7(wd[2023+:256]),
 .wd_v({wd[2311],wd[2022],wd[1733],wd[1444],wd[1155],wd[866],wd[577],wd[288]}),
 .copy_on(copy_on),.copy_bank(copy_sel),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit[2+:2]),
 .root_ready(root_ready[1]),.g_v(g_v[2+:2]),.g_d(g_d[572+:572]));
 ot_wbq_root u_r2(.hbm_clk(hbm_clk),.fifo_clk(stream_fifo_clk[2]),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
 .root_id(id_m[4+:2]),.reserve_v(wb_reserve_v),.reserve_bank(wb_reserve_bank),.reserve_total(wb_reserve_sectors),.reserve_base(wb_reserve_base[29:0]),
 .fill_start(wb_fill_start),.fill_start_bank(wb_fill_bank),
 .wd0(wd[0+:256]),
 .wd1(wd[289+:256]),
 .wd2(wd[578+:256]),
 .wd3(wd3_m),
 .wd4(wd[1156+:256]),
 .wd5(wd[1445+:256]),
 .wd6(wd[1734+:256]),
 .wd7(wd[2023+:256]),
 .wd_v({wd[2311],wd[2022],wd[1733],wd[1444],wd[1155],wd[866],wd[577],wd[288]}),
 .copy_on(copy_on),.copy_bank(copy_sel),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit[4+:2]),
 .root_ready(root_ready[2]),.g_v(g_v[4+:2]),.g_d(g_d[1144+:572]));
 ot_wbq_root u_r3(.hbm_clk(hbm_clk),.fifo_clk(stream_fifo_clk[3]),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
 .root_id(id_m[6+:2]),.reserve_v(wb_reserve_v),.reserve_bank(wb_reserve_bank),.reserve_total(wb_reserve_sectors),.reserve_base(wb_reserve_base[29:0]),
 .fill_start(wb_fill_start),.fill_start_bank(wb_fill_bank),
 .wd0(wd[0+:256]),
 .wd1(wd[289+:256]),
 .wd2(wd[578+:256]),
 .wd3(wd3_m),
 .wd4(wd[1156+:256]),
 .wd5(wd[1445+:256]),
 .wd6(wd[1734+:256]),
 .wd7(wd[2023+:256]),
 .wd_v({wd[2311],wd[2022],wd[1733],wd[1444],wd[1155],wd[866],wd[577],wd[288]}),
 .copy_on(copy_on),.copy_bank(copy_sel),.s_stop(s_stop),.h_stop(h_stop),.g_credit(g_credit[6+:2]),
 .root_ready(root_ready[3]),.g_v(g_v[6+:2]),.g_d(g_d[1716+:572]));
 ot_wbk_native_r2_switch u_sw(
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
 .wb_ready(wb_ready),
 .wa(wa),
 .wbw_v(wbw_v),
 .wbw_base(wbw_base),
 .wbw_total(wbw_total),
 .w_k_v(w_k_v),
 .w_k_rdy(w_k_rdy),
 .w_k_addr(w_k_addr),
 .w_k_wdata(w_k_wdata),
 .w_k_wr_done(w_k_wr_done),
 .fault(fault),
 .wd_c(wd_c),
 .root_ready(root_ready),
 .g_v(g_v),
 .g_d(g_d),
 .g_credit(g_credit),
 .root_id(root_id),
 .copy_on(copy_on),
 .copy_sel(copy_sel),
 .s_stop(s_stop),
 .h_stop(h_stop));
endmodule

module ot_wbk_native_r2_switch (
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
 ot_wbq_sw_split_main u_main (
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
