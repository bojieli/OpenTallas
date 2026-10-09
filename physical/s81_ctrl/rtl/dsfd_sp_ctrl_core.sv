`timescale 1ns/1ps
// dsfd_sp_ctrl_core (stream ds-control, 2026-10-08): the S81 die-master shell of ot_s81_ctrl (the die control plane)
// at the S81 geometry: XW 640 HIDDEN flits, 21-bit positions, 12-bit fabric ids, MAXU 64 users, a 128-entry stage
// program (the largest S81 stage program has 75 jobs), 12 engine ports at QD 8.  Every die input is captured in a
// flop at the pin or a 2-entry skid buffer (registered ready); every die output leaves a flop.  Added cycles (priced in
// review_queue/ds-control.md): +1 inbound message (skid), +1 outbound message (skid), +1 hop_go pin flop, +1 VM write.
// Wrappers: dsfd_sp_ctrl (layer die, ROLE 0), dsfd_sp_ctrl_src (stage-0 die: host queue + boot gate, ROLE 1),
// dsfd_sp_ctrl_h (head-root die: sampler stop, ROLE 2).
module dsfd_sp_ctrl_core #(parameter integer ROLE = 0, parameter integer MY_ID = 0,
                           parameter integer SRC_LO = 0, SRC_HI = 0, parameter [15:0] TYPE_MASK = 16'h000A) (
    input  wire          ck,
    input  wire          rs,
    input  wire          pw_v, input wire [6:0] pw_a, input wire [27:0] pw_d, input wire [7:0] prog_len,
    input  wire [11:0]   cfg_users,
    input  wire          i_v, output wire i_r, input wire [511:0] i_d, input wire i_l,
    output wire          o_v, input wire o_r, output wire [511:0] o_d, output wire o_l,
    output wire [11:0]   cv, output wire [12*84-1:0] cd, input wire [11:0] dv, input wire [12*8-1:0] dt,
    input  wire          hop_go,
    output reg           vwe, output reg [13:0] vwa, output reg [511:0] vwd,
    output wire          vre, output wire [13:0] vra, input wire [511:0] vrq,
    input  wire          am_v, input wire [20:0] am_pos, input wire [20:0] am_tok, input wire [31:0] am_val,
    input  wire          boot_ok,
    input  wire          hc_v, output wire hc_r, input wire [1:0] hc_op, input wire [7:0] hc_tag, input wire [7:0] hc_user,
    input  wire [20:0]   hc_pos, input wire [20:0] hc_tok,
    output wire          cpl_v, input wire cpl_r, output wire [113:0] cpl_d,
    output reg           flt, output reg [15:0] fvec, output reg stk, output reg [15:0] snap
);
    // pin capture
    reg [11:0] cu_q; reg hg_q, am_v_q, bo_q; reg [20:0] amp_q, amt_q; reg [31:0] amv_q;
    always @(posedge ck) begin cu_q <= cfg_users; amp_q <= am_pos; amt_q <= am_tok; amv_q <= am_val; end
    always @(posedge ck or negedge rs) if (!rs) begin hg_q <= 0; am_v_q <= 0; bo_q <= 0; end
        else begin hg_q <= hop_go; am_v_q <= am_v; bo_q <= boot_ok; end
    // message streams through skid buffers
    wire si_v, si_r, so_v, so_r; wire [512:0] si_d, so_d; wire x0, x1, x2, x3;
    ot_skid_buffer #(.WIDTH(513), .DEPTH(2)) u_si (.clk(ck), .rst_n(rs), .in_valid(i_v), .in_ready(i_r), .in_data({i_l, i_d}),
        .out_valid(si_v), .out_ready(si_r), .out_data(si_d), .overflow(x0), .underflow(x1));
    wire c_ov; wire [511:0] c_od; wire c_ol;
    ot_skid_buffer #(.WIDTH(513), .DEPTH(2)) u_so (.clk(ck), .rst_n(rs), .in_valid(c_ov), .in_ready(so_r), .in_data({c_ol, c_od}),
        .out_valid(o_v), .out_ready(o_r), .out_data(so_d), .overflow(x2), .underflow(x3));
    assign o_d = so_d[511:0]; assign o_l = so_d[512];
    // host command port through a skid
    wire sh_v, sh_r; wire [59:0] sh_d; wire x4, x5;
    ot_skid_buffer #(.WIDTH(60), .DEPTH(2)) u_sh (.clk(ck), .rst_n(rs), .in_valid(hc_v), .in_ready(hc_r),
        .in_data({hc_op, hc_tag, hc_user, hc_pos, hc_tok}), .out_valid(sh_v), .out_ready(sh_r), .out_data(sh_d), .overflow(x4), .underflow(x5));
    wire c_vwe; wire [13:0] c_vwa; wire [511:0] c_vwd;
    wire f; wire [15:0] fv; wire s; wire [15:0] sn; wire [31:0] j0, t0;
    ot_s81_ctrl #(.ROLE(ROLE), .MY_ID(MY_ID), .NW(21), .MAXU(64), .VWA(14), .XW(640), .RXB(0), .TXB(2048), .SIDE_TXB(4096),
        .SIDE_BASE(8192), .SIDE_USH(6), .NOPS(128), .NENG(12), .QD(8), .SRC_LO(SRC_LO), .SRC_HI(SRC_HI),
        .TYPE_MASK(TYPE_MASK), .LEN_SIDE_MAX(64)) u (
        .clk(ck), .rst_n(rs), .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d), .prog_len(prog_len), .cfg_users_static(cu_q),
        .in_valid(si_v), .in_ready(si_r), .in_data(si_d[511:0]), .in_last(si_d[512]),
        .out_valid(c_ov), .out_ready(so_r), .out_data(c_od), .out_last(c_ol),
        .cmd_v(cv), .cmd_d(cd), .dn_v(dv), .dn_tag(dt), .hop_go(hg_q),
        .vm_we(c_vwe), .vm_waddr(c_vwa), .vm_wdata(c_vwd), .vm_re(vre), .vm_raddr(vra), .vm_rq(vrq),
        .am_v(am_v_q), .am_pos(amp_q), .am_tok(amt_q), .am_val(amv_q), .boot_ok(bo_q),
        .hc_valid(sh_v), .hc_ready(sh_r), .hc_op(sh_d[59:58]), .hc_tag(sh_d[57:50]), .hc_user(sh_d[49:42]),
        .hc_pos(sh_d[41:21]), .hc_token(sh_d[20:0]), .cpl_valid(cpl_v), .cpl_ready(cpl_r), .cpl_data(cpl_d),
        .fault(f), .fault_vec(fv), .stuck(s), .stuck_snap(sn), .st_jobs(j0), .st_tokens(t0));
    always @(posedge ck or negedge rs)
        if (!rs) begin vwe <= 0; flt <= 0; fvec <= 0; stk <= 0; snap <= 0; end
        else begin vwe <= c_vwe; flt <= f; fvec <= fv; stk <= s; snap <= sn; end
    always @(posedge ck) begin vwa <= c_vwa; vwd <= c_vwd; end
endmodule
