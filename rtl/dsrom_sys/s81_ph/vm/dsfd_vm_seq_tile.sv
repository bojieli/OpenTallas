`timescale 1ns/1ps
`default_nettype none
// Hardened engine-12 tile: dsfd_vm_seq_static plus the VM control glue that only it consumes (top-down hierarchy
// contract: glue goes into the tile that uses it).  Previously these 18 flops sat unhardened on two extra die clock
// roots (cks: VM-top p_bad / e_flt; ck_core_t: core rr / pq_bad / fault_q / v_dv / v_dt / op_bad).  Now one root
// (ck_seq_t) and one reset; every edge is unchanged except vm_fault, which leaves the tile registered (+1 stream edge,
// a diagnostic level sampled by the WFC in the serial domain; it never gates data or stretches a schedule).
module dsfd_vm_seq_tile (
    input  wire          ck,
    input  wire [0:0]    rst,                       // async, active low (seq convention)
    input  wire [84:0]   c_cmd,
    output wire [8:0]    c_done,
    output wire [1:0]    c_st,
    input  wire [127:0]  o_cv, input wire [1151:0] o_ca, input wire [511:0] o_cm,
    input  wire [31:0]   o_rv, input wire [447:0]  o_rr,
    output wire          t_inp_su, t_inp_hc,
    // native-op forward (engine -> VM services) and landing arm
    output wire          nf_v, output wire [83:0] nf_d,
    output wire          larm_v, output wire [3:0] larm_g, output wire [13:0] larm_base,
    // fault sources (levels from their own leaves)
    input  wire [7:0]    pqx_chk,                   // {f_pqx[19], f_pqx[6:1], f_pqx[0]}
    input  wire [7:0]    read_fault,
    input  wire [2:0]    edge_f,                    // capture / WFC / xio
    input  wire [8:0]    x_hdr,                     // {xw_v, xw_d[1025:1024], xc_v, xc_d[513:512], xs_v, xs_d[513:512]}
    input  wire [2:0]    x_al,
    input  wire          w_flt, input wire [39:0] m_flt, input wire [2:0] l_flt, input wire r_flt,
    output reg           vm_fault
);
    reg [1:0] rq;
    always @(posedge ck or negedge rst[0]) if (!rst[0]) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    wire rn = rq[1];
    wire v_cv; wire [83:0] v_cd; reg v_dv; reg [7:0] v_dt; reg op_bad, pq_bad, o_bad, p_bad, e_flt;
    // r3 (S-ELEM-A 2026-10-15): every fault/check INPUT is captured in a plain pin flop first (r2 routed TT -48.77 on
    // input -> OR tree -> vm_fault / u_seq.v_flt, e.g. l_flt[2]).  Faults are diagnostic and never gate data or the
    // command calendar: vm_fault and the sequencer's fault flag move one edge later; command issue/done timing unchanged.
    reg w_flt_q, r_flt_q; reg [39:0] m_flt_q; reg [2:0] l_flt_q; reg [7:0] pqx_q;
    reg [2:0] x_al_q; reg [8:0] x_hdr_q; reg [7:0] rf_q; reg [2:0] ef_q;
    always @(posedge ck) begin
        w_flt_q <= w_flt; r_flt_q <= r_flt; m_flt_q <= m_flt; l_flt_q <= l_flt; pqx_q <= pqx_chk;
        x_al_q <= x_al; x_hdr_q <= x_hdr; rf_q <= read_fault; ef_q <= edge_f;
    end
    wire x_flt = |x_al_q | p_bad | e_flt;
    // landing header check per x34 i (sel 0, col 1, aSW 2): x_hdr[3i+2] valid, [3i+1] header top bit, [3i] header bit
    wire hdr_bad = (x_hdr_q[2] && (!x_hdr_q[0] || x_hdr_q[1])) || (x_hdr_q[5] && (!x_hdr_q[3] || x_hdr_q[4])) ||
                   (x_hdr_q[8] && (!x_hdr_q[6] || x_hdr_q[7]));
    wire svc_flt = w_flt_q | |m_flt_q | |l_flt_q | pq_bad | o_bad | op_bad | r_flt_q | x_flt;
    dsfd_vm_seq_static u_seq (.ck(ck), .rst(rst), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .o_cv(o_cv), .o_ca(o_ca), .o_cm(o_cm), .o_rv(o_rv), .o_rr(o_rr),
        .v_cv(v_cv), .v_cd(v_cd), .v_dv(v_dv), .v_dt(v_dt), .v_flt(svc_flt),
        .t_inp_su(t_inp_su), .t_inp_hc(t_inp_hc));
    wire [2:0] v_code = v_cd[30:28];
    assign larm_v = v_cv && v_code == 3'd6 && v_cd[27:24] != 4'd7;   // group 7 = collective landing (xio)
    assign larm_g = v_cd[27:24]; assign larm_base = v_cd[20:7];
    assign nf_v = v_cv; assign nf_d = v_cd;
    always @(posedge ck) begin
        if (!rn) begin v_dv <= 1'b0; op_bad <= 1'b0; pq_bad <= 1'b0; o_bad <= 1'b0; p_bad <= 1'b0; e_flt <= 1'b0; vm_fault <= 1'b0; end
        else begin
            v_dv <= v_cv;                                   // every native op retires one edge after its forward
            if (v_cv && (v_code == 3'd5 || v_code == 3'd7 || (v_code == 3'd6 && v_cd[27:24] == 4'd7))) op_bad <= 1'b1;
            if (pqx_q[0] && (pqx_q[7] || pqx_q[6:1] != 6'd0)) pq_bad <= 1'b1;
            if (|rf_q) o_bad <= 1'b1;
            if (hdr_bad) p_bad <= 1'b1;
            if (|ef_q) e_flt <= 1'b1;
            vm_fault <= svc_flt;
        end
        v_dt <= {v_cd[83], v_cd[6:0]};
    end
endmodule
`default_nettype wire
