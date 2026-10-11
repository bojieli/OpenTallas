`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_dsrom_mtp_seed_launch / dsfd_mtp_seed_launch (mtp-dsbind, 2026-10-10): the DSpark PRIMARY die's consumer of the
// seed descriptor (results/uarch/dsrom_s81_mtp_binding_20261010: P.k0..3, generator --draft P).
//
// The head-die sequencer (ot_dsrom_mtp_seq) sends one descriptor per closed step on the collective's dedicated MTP
// lane (dsfd_sp_collective OT_S81PH_COLL_MTPL: t_mrs = {seed word 77, valid}, grant f_mrs):
//     {user[USER_W], anchor[NW] (closing position), nrow[NW] (positions newly committed), y[NW] (bonus), epoch[4]}
// The committed positions are anchor - nrow + 1 .. anchor (= the sequencer's u_lc .. anchor).  seed_ctl
// (ot_dsrom_mtp_seed_ctl) takes x vectors only: one token = 240 beats of 64 BF16 (in_xa lanes 0..31, in_xb 32..63)
// of the HC mean of layers 37/38/39, after out_x_rdy, then out_done.  This block turns a descriptor into that
// program:
//   1. receive (ot_dsrom_mtp_lrx_rtt: RTT-sized grant receiver, FWD_C / RET_C = the real stations), decode;
//   2. check the descriptor against per-user state (next unseeded position lc, last epoch ep):
//        drop   first row != lc[user]            (a lost descriptor leaves a gap; a replay re-covers rows)  fault[0]
//        stale  epoch not in {ep, ep + 1}         (the sequencer advances the epoch by at most 1 a step)     fault[1]
//        range  user >= MAXU or nrow == 0                                                                  fault[2]
//      a failed descriptor launches NOTHING (state unchanged) and raises the sticky fault;
//   3. per committed position inside the drafter window (the last WIN; older rows are outside the drafter's
//      ring), fetch the position's 240-beat hidden row from the row store (row stride 256 beats: address HBASE +
//      {issue epoch, user, pos mod WIN, beat}; the issue epoch = the user's epoch before this descriptor, i.e. the
//      block epoch the committed positions were issued under: the store serves only that version of the row, never a
//      squashed one -- dsfd_mtp_hrow) and stream it into seed_ctl, then wait out_done (all seed elements, die join);
//   4. after the anchor row: a one-cycle program-start event {user, anchor, y, epoch} to the DSpark block mtp.0 issue.
// Faults (sticky): [0] drop, [1] stale, [2] range, [3] protocol (VM response outside a row / x_done outside wait).
// Mutants (negative controls, never in a build): OT_SEEDL_MUT_NOGAP (no lc check), OT_SEEDL_MUT_NOEPOCH (no epoch
// check).
// Cycle cost (bench tools/mtp_seed_launch_gate.py, measured): descriptor at the pin -> first x beat, and last
// x_done -> program start; the 240 beats + seed_ctl itself are the seed term already in the composition.
// ---------------------------------------------------------------------------------------------------------------
module ot_dsrom_mtp_seed_launch #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8,
    parameter integer WIN = 256, parameter integer BEATS = 240, parameter integer VM_AW = 24,
    parameter integer HBASE = 0
) (
    input  wire                       clk, rst_n,
    input  wire                       d_v,
    output wire                       d_r,
    input  wire [USER_W+3*NW+4-1:0]   d_d,
    input  wire                       c_v,          // host: clear a user's MTP state (new request)
    input  wire [USER_W-1:0]          c_user,
    output reg                        v_rq_v,
    input  wire                       v_rq_r,
    output reg  [VM_AW-1:0]           v_rq_a,
    input  wire                       v_rs_v,
    input  wire [1023:0]              v_rs_d,
    output reg                        x_v,
    output reg  [511:0]               x_a,
    output reg  [511:0]               x_b,
    input  wire                       x_rdy,
    input  wire                       x_done,
    output reg                        p_v,          // one-cycle program-start event (the block issue queues it)
    output reg  [USER_W+2*NW+4-1:0]   p_d,
    output reg  [3:0]                 fault,
    output reg  [15:0]                n_launch
);
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer WB = $clog2(WIN);
    localparam integer BB = 8;
    initial if ((1 << WB) != WIN || BEATS > 256 || VM_AW < UB + WB + BB + 4) $fatal(1, "seed_launch: bad dimensions");
    localparam [2:0] S_IDLE = 3'd0, S_CHK = 3'd1, S_WAIT = 3'd2, S_ROW = 3'd3, S_PROC = 3'd4;
    reg [2:0] st;
    reg [NW-1:0] lc [0:MAXU-1];
    reg [3:0]    ep [0:MAXU-1];
    reg [MAXU-1:0] seen;                      // a user's first descriptor sets its epoch
    // decoded descriptor (registered)
    reg [USER_W-1:0] r_u; reg [NW-1:0] r_anc, r_nrow, r_y, r_first; reg [3:0] r_ep, r_iep;
    reg [NW-1:0] pos; reg [8:0] nrq, nrs;
    assign d_r = (st == S_IDLE) && !c_v;
    wire [UB-1:0] ui = r_u[UB-1:0];
    wire [NW-1:0] win_lo = (r_nrow > NW'(WIN)) ? r_anc + 1'b1 - NW'(WIN) : r_first;
    wire gap_bad = r_first != lc[ui];
    wire ep_bad  = seen[ui] && r_ep != ep[ui] && r_ep != ep[ui] + 4'd1;
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            st <= S_IDLE; fault <= 4'd0; n_launch <= 16'd0; seen <= '0; p_d <= '0;
            v_rq_v <= 1'b0; x_v <= 1'b0; p_v <= 1'b0; nrq <= 0; nrs <= 0;
            for (i = 0; i < MAXU; i = i + 1) begin lc[i] <= '0; ep[i] <= 4'd0; end
        end else begin
            x_v <= 1'b0; p_v <= 1'b0;
            if (c_v && st == S_IDLE && c_user < MAXU) begin
                lc[c_user[UB-1:0]] <= '0; ep[c_user[UB-1:0]] <= 4'd0; seen[c_user[UB-1:0]] <= 1'b0;
            end
            // VM responses stream straight into seed_ctl (it takes every beat of a token; no stall inside a row)
            if (v_rs_v) begin
                if (st != S_ROW || nrs == 9'(BEATS)) fault[3] <= 1'b1;
                else begin
                    x_v <= 1'b1; x_a <= v_rs_d[511:0]; x_b <= v_rs_d[1023:512]; nrs <= nrs + 1'b1;
                end
            end
            if (x_done && st != S_PROC) fault[3] <= 1'b1;
            if (v_rq_v && v_rq_r) begin
                v_rq_v <= 1'b0;
                if (nrq != 9'(BEATS)) begin
                    v_rq_v <= 1'b1; v_rq_a <= v_rq_a + 1'b1;
                end
            end
            case (st)
                S_IDLE: if (d_v && d_r) begin
                    {r_u, r_anc, r_nrow, r_y, r_ep} <= d_d;
                    r_first <= d_d[4+2*NW +: NW] - d_d[4+NW +: NW] + 1'b1;     // anchor - nrow + 1
                    st <= S_CHK;
                end
                S_CHK: begin
                    if (r_u >= MAXU || r_nrow == 0) begin fault[2] <= 1'b1; st <= S_IDLE; end
`ifndef OT_SEEDL_MUT_NOGAP
                    else if (gap_bad) begin fault[0] <= 1'b1; st <= S_IDLE; end
`endif
`ifndef OT_SEEDL_MUT_NOEPOCH
                    else if (ep_bad) begin fault[1] <= 1'b1; st <= S_IDLE; end
`endif
                    else begin
                        lc[ui] <= r_anc + 1'b1; ep[ui] <= r_ep; seen[ui] <= 1'b1;
                        r_iep <= seen[ui] ? ep[ui] : 4'd0;     // the epoch these rows were ISSUED under
                        pos <= win_lo; st <= S_WAIT;
                    end
                end
                S_WAIT: if (x_rdy) begin
                    nrq <= 9'd1; nrs <= 0;
                    v_rq_v <= 1'b1;
                    v_rq_a <= VM_AW'(HBASE) + {{(VM_AW-UB-WB-BB-4){1'b0}}, r_iep, ui, pos[WB-1:0], {BB{1'b0}}};
                    st <= S_ROW;
                end
                S_ROW: begin
                    if (v_rq_v && v_rq_r && nrq != 9'(BEATS)) nrq <= nrq + 1'b1;
                    if (nrs == 9'(BEATS)) st <= S_PROC;
                end
                S_PROC: if (x_done) begin
                    if (pos == r_anc) begin
                        p_v <= 1'b1; p_d <= {r_u, r_anc, r_y, r_ep}; n_launch <= n_launch + 1'b1; st <= S_IDLE;
                    end else begin
                        pos <= pos + 1'b1; st <= S_WAIT;
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
endmodule

// dsfd_mtp_seed_launch: the die master (slab between collective and VM on the primary die).  Every port is behind a
// pin flop.  Both flow-controlled die links use the MTP grant protocol: the descriptor arrives through
// ot_dsrom_mtp_lrx_rtt (pin capture inside, RTT-sized to FWD_C collective -> slab and RET_C back, OUTPUT_PIPE 1); the
// VM read requests leave through ot_dsrom_mtp_ltx (one request per grant from the VM's RTT receiver).  VM responses
// (in order, only for issued requests) and the x beats have no flow control: seed_ctl takes every beat of a token.
module dsfd_mtp_seed_launch #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8,
    parameter integer WIN = 256, parameter integer VM_AW = 24, parameter integer HBASE = 0,
    parameter integer FWD_C = 9, parameter integer RET_C = 9,
    parameter integer SW = USER_W + 3 * NW + 4, parameter integer PW = USER_W + 2 * NW + 4
) (
    input  wire [0:0]        ck, rst,
    input  wire [SW:0]       f_mrs,          // {seed word, valid} = collective t_mrs
    output wire [0:0]        t_mrs,          // grant = collective f_mrs
    input  wire [USER_W:0]   f_clr,          // {user, valid}: host clear
    output wire [VM_AW:0]    t_vrq,          // {addr, valid} VM read request (grant protocol)
    input  wire [0:0]        f_vrq,          // VM grant
    input  wire [1024:0]     f_vrs,          // {data 1024, valid} VM read response (in order)
    output wire [1024:0]     t_x,            // {x_b, x_a, valid} to the seed elements (in_x_v / in_xa / in_xb)
    input  wire [1:0]        f_x,            // {all out_done, all out_x_rdy} (die join)
    output wire [PW:0]       t_ps,           // {program start word, event}
    output wire [3:0]        t_flt
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    wire dv, dr; wire [SW-1:0] dd;
    ot_dsrom_mtp_lrx_rtt #(.W(SW), .D(FWD_C + RET_C + 4), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                           .FORWARD_HOPS(FWD_C), .RETURN_HOPS(RET_C)) u_rx (
        .clk(ck[0]), .rst_n(rn), .l_valid(f_mrs[0]), .l_ready(t_mrs[0]), .l_data(f_mrs[SW:1]),
        .c_valid(dv), .c_ready(dr), .c_data(dd));
    reg [USER_W:0] i_clr; reg [1024:0] i_vrs; reg [1:0] i_x;          // input pin flops
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin i_clr[0] <= 1'b0; i_vrs[0] <= 1'b0; i_x <= 2'b0; end
        else begin i_clr[0] <= f_clr[0]; i_vrs[0] <= f_vrs[0]; i_x <= f_x; end
    always @(posedge ck[0]) begin i_clr[USER_W:1] <= f_clr[USER_W:1]; i_vrs[1024:1] <= f_vrs[1024:1]; end
    wire rqv, rqr, xv, pv; wire [VM_AW-1:0] rqa; wire [511:0] xa, xb; wire [PW-1:0] pd; wire [3:0] flt; wire [15:0] nl;
    ot_dsrom_mtp_ltx #(.W(VM_AW)) u_rq (.clk(ck[0]), .rst_n(rn), .c_valid(rqv), .c_ready(rqr), .c_data(rqa),
        .l_valid(t_vrq[0]), .l_ready(f_vrq[0]), .l_data(t_vrq[VM_AW:1]));
    ot_dsrom_mtp_seed_launch #(.NW(NW), .USER_W(USER_W), .MAXU(MAXU), .WIN(WIN), .VM_AW(VM_AW), .HBASE(HBASE)) u_c (
        .clk(ck[0]), .rst_n(rn), .d_v(dv), .d_r(dr), .d_d(dd), .c_v(i_clr[0]), .c_user(i_clr[USER_W:1]),
        .v_rq_v(rqv), .v_rq_r(rqr), .v_rq_a(rqa), .v_rs_v(i_vrs[0]), .v_rs_d(i_vrs[1024:1]),
        .x_v(xv), .x_a(xa), .x_b(xb), .x_rdy(i_x[0]), .x_done(i_x[1]),
        .p_v(pv), .p_d(pd), .fault(flt), .n_launch(nl));
    reg [1024:0] o_x; reg [PW:0] o_ps; reg [3:0] o_flt;                // output pin flops
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin o_x[0] <= 1'b0; o_ps[0] <= 1'b0; o_flt <= 4'd0; end
        else begin o_x[0] <= xv; o_ps[0] <= pv; o_flt <= flt; end
    always @(posedge ck[0]) begin o_x[1024:1] <= {xb, xa}; o_ps[PW:1] <= pd; end
    assign t_x = o_x; assign t_ps = o_ps; assign t_flt = o_flt;
endmodule
