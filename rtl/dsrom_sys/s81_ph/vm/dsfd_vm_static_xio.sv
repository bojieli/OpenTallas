`timescale 1ns/1ps
`default_nettype none
// Source-real XIO partition: request +2core; collective total +4core; Q/G +4core/+3serial.
// All delays fixed, II unchanged, no credit/backpressure. Physical qualification pending.







module dsfd_vm_static_xio #(parameter integer RLAT = 13) (
    input wire ck_control_t, ck_control_s,
    input wire ck_return_t, rss_return_t, ck_fault_t, ck_fault_s, rss_fault_t, rst_fault_s,
    input wire ck_fault_join_t,rss_fault_join_t,
    input wire [1:0] ck_x43_t, ck_x43_s, // [0]query, [1]gather
    input wire rss_control_t, rst_control_s,
    input wire [1:0] rss_x43_t, rst_x43_s, // per-root active-low epoch resets
    // engine 12 native forward
    input  wire          n_v, input wire [83:0] n_d,
    // aux ports 4..7 to / from dsfd_vm_static_core
    output wire [3:0]    a_v, output wire [55:0] a_row,
    input  wire [3:0]    e_v, input wire [2047:0] e_d,
    // collective
    input  wire [2203:0] f_collective,
    input  wire [14:0]   f_crq,
    output wire [512:0]  t_crs,
    output reg  [3:0]    w_v, output reg [55:0] w_row, output reg [2047:0] w_d, output reg [63:0] w_m, output reg [31:0] w_t,
    // gather
    output wire [511:0]  t_gather,             // serial
    input  wire [10:0]   f_xgo,                // stream
    // scan query
    output wire [512:0]  qSW,                  // serial
    input  wire [2:0]    qSWs,                 // serial
    output wire          fault
);

 // Wires-only parent. Each hardened leaf receives its own measured phi-minus-R root.
 wire[2:0]return_valid;wire[5:0]return_lane;wire req_fault,ret_fault,serial_fault;
 wire q_v,g_v;wire[511:0]q_d;wire[510:0]g_d;
 dsfd_vm_xio_request #(.RLAT(RLAT))u_req(.ck(ck_control_t),.rst_n(rss_control_t),.n_v(n_v),.n_d(n_d),.f_crq(f_crq),.a_v(a_v),.a_row(a_row),.return_valid(return_valid),.return_lane(return_lane),.fault(req_fault));
 dsfd_vm_xio_return u_ret(.ck(ck_return_t),.rst_n(rss_return_t),.return_valid(return_valid),.return_lane(return_lane),.e_v(e_v),.e_d(e_d),.f_xgo(f_xgo),.t_crs(t_crs),.q_v(q_v),.q_d(q_d),.g_v(g_v),.g_d(g_d),.fault(ret_fault));
    // Compiler rows and masks are passed to the core without a landing pointer
    // or extra pin stage. Each lane's 8-bit tag remains part of f_collective ABI;
    // the wrapper/core associates these writes with fixed sources 44..47.
    always @* begin : p_land integer k;
        w_v = 4'd0; w_row = 56'd0; w_d = 2048'd0; w_m = 64'd0; w_t = 32'd0;
        for (k = 0; k < 4; k = k + 1) begin
            w_v[k] = f_collective[551*k];
            w_row[14*k +: 14] = f_collective[551*k+1 +: 14];
            w_m[16*k +: 16] = f_collective[551*k+15 +: 16];
            w_d[512*k +: 512] = f_collective[551*k+31 +: 512];
            `ifdef OT_VM_XIO_MUT_TAG
            w_t[8*k +: 8] = f_collective[551*k+543 +: 8] ^ 8'd1;
`else
            w_t[8*k +: 8] = f_collective[551*k+543 +: 8];
`endif
        end
    end
    // ---------------------------------------------------------------- serial-bound streams
    wire qo_v, go_v; wire [511:0] qo_d; wire [510:0] go_d; wire qf, gf;
    ot_s81_vm_x43 #(.W(512)) u_xq (.t_ck(ck_x43_t[0]), .t_rst_n(rss_x43_t[0]), .s_v(q_v), .s_d(q_d), .s_ck(ck_x43_s[0]), .s_rst_n(rst_x43_s[0]),
        .o_v(qo_v), .o_d(qo_d), .fault(qf));
    ot_s81_vm_x43 #(.W(511)) u_xg (.t_ck(ck_x43_t[1]), .t_rst_n(rss_x43_t[1]), .s_v(g_v), .s_d(g_d), .s_ck(ck_x43_s[1]), .s_rst_n(rst_x43_s[1]),
        .o_v(go_v), .o_d(go_d), .fault(gf));
    assign qSW = {qo_d, qo_v};
    assign t_gather = {go_d, go_v};

 dsfd_vm_xio_serial u_serial(.ck(ck_control_s),.rst_n(rst_control_s),.qo_v(qo_v),.qf(qf),.gf(gf),.qSWs(qSWs),.fault(serial_fault));
 wire[1:0]fb0,fb1,fb2;wire[2:0]fpar;wire fmark,fvalid,flevel,fxfault;
 ot_s81_vm_fault_x34_s_w1 u_fault_s(.s_ck(ck_fault_s),.s_rst_n(rst_fault_s),.s_v(1'b1),.s_d(serial_fault),.b0(fb0),.b1(fb1),.b2(fb2),.bpar(fpar),.s_mark(fmark));
 ot_s81_vm_fault_x34_t_w1 u_fault_t(.t_ck(ck_fault_t),.t_rst_n(rss_fault_t),.b0(fb0),.b1(fb1),.b2(fb2),.bpar(fpar),.s_mark(fmark),.o_v(fvalid),.o_d(flevel),.fault(fxfault));
 dsfd_vm_xio_fault_join u_fault(.ck(ck_fault_join_t),.rst_n(rss_fault_join_t),.request_fault(req_fault),.return_fault(ret_fault),.serial_valid(fvalid),.serial_level(flevel),.transport_fault(fxfault),.fault(fault));
endmodule
`default_nettype wire
