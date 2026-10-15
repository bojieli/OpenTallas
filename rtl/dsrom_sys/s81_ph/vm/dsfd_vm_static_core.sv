`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_core (claude S81 VM owner r8, 2026-10-14): the STATIC S81 layer-die VM, stream domain (1.2 GHz).
// Composition of real RTL only (no stubs, no behavioural memory): the full-capacity native memory
// dsfd_vm_static512_suhc (4 slices x 32 real ot_sram_1r1w_512x128 banks = 16384 x 512 b, two duplex relay levels,
// return store, native SU/HC return map), the fixed-rule read schedule dsfd_vm_static_rsched, the fixed-rule write
// service dsfd_vm_static_wsched (53 sources -> wdispatch -> compiler-indexed storage -> fixed drain), the sequencer
// engine 12 dsfd_vm_seq_static and the static landing dsfd_vm_static_landing (static LARM).
// Owner rule 2026-10-14T18:59: nothing here waits, stalls, queues by demand, arbitrates or returns a credit.  Every
// client sees a FIXED latency (stream edges, die pin sample -> die output register sample):
//   SU / HC row read  f_*_rqv/rq  -> t_*_rsv/rs        L = 12  (P pin, P+1 FSR, P+11 release, P+12 output register)
//   PQ x read         f_pqx       -> t_pqx (4 rows)    L = 12  (aux ports 0..3 = rows x_addr[17:6]*4 + 0..3)
//   edge aux reads    x_av / x_ar -> x_rv / x_rd       L = 12  (aux 4..7 xio row streams, 8..11 WFC; port = row[1:0])
//   row write         f_*_wq*     -> SRAM commit       lane c: scatter sample P+4+c (+ relay and macro stages of the
//                                                      static512 timeline); the engine CHECK observes the commits
//   engine 12         c_cmd       -> c_done            6 (dsfd_vm_seq_static DLAT)
//   Engram MIX4 read  f_mx_rq*    -> t_mx_rs* (20)     L = 12  (lane i: slot {G(i), row[1:0]} on logical port = slot)
// Write sources: 0..15 SU slots, 16..23 HC slots, 24..27 landing lanes (scan a0/a1, selector, collector), 28..31 MIX4,
// 32..43 + 48..51 the static capture lanes 0..15 (dsfd_vm_static_cap), 44..47 the collective landing words
// (dsfd_vm_static_xio, LARM group 7), 52 the WFC kit writes (dsfd_vm_static_wfc).  All fixed rules, no queue.
// Native engine codes (forwarded to the edge services on nf_v / nf_d): 4 STREAM (dsfd_vm_static_xio),
// 6 LARM (groups 0 / 5 / 6 here); legacy collective ops 5/7/group7 fault. Done = the seq's fixed DLAT.
// Every service fault is ORed onto the engine's legacy-fault input (seq flt[10] -> c_st[0]).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_static_core #(parameter integer READ_PIPE=0) (
    // cks owns this core's bounded local control registers. Every child root is an explicit
    // independently deliverable clock pin; tying these pins is a TESTBENCH decision only.
    input  wire          cks, rss,
    input  wire          ck_rsched, ck_seq, ck_landing,
    input  wire [15:0]   ck_mem_fsr,
    input  wire [3:0]    ck_mem_return,
    input  wire [127:0]  ck_mem_bank, ck_mem_wcapture,
    input  wire [15:0]   ck_mem_wscatter,
    input  wire [47:0]   ck_mem_relay_req, ck_mem_relay_rsp,
    input  wire          ck_write_control, ck_write_header,
    input  wire [3:0]    ck_write_payload,
    input  wire [15:0]   ck_write_dispatch,
    input  wire [127:0]  ck_write_stage,
    input  wire          rst_rsched_n, rst_seq_n, rst_landing_n,
    input  wire [15:0]   rst_mem_fsr_n,
    input  wire [3:0]    rst_mem_return_n,
    input  wire [127:0]  rst_mem_bank_n, rst_mem_wcapture_n,
    input  wire [15:0]   rst_mem_wscatter_n,
    input  wire [47:0]   rst_mem_relay_n,
    input  wire          rst_write_control_n, rst_write_header_n,
    input  wire [3:0]    rst_write_payload_n,
    input  wire [15:0]   rst_write_dispatch_n,
    input  wire [127:0]  rst_write_stage_n,
    input  wire [63:0]   ck_read_data, rst_read_data_n,
    input  wire [7:0]    ck_read_valid, rst_read_valid_n,
    // sequencer engine 12
    input  wire [84:0]   c_cmd, output wire [8:0] c_done, output wire [1:0] c_st,
    output wire          t_inp_su, t_inp_hc,
    // SU v2 row slots (16 rd + 16 wr)
    input  wire [15:0]   f_su_rqv, input wire [223:0] f_su_rq,
    output wire [15:0]   t_su_rsv, output reg [8191:0] t_su_rs,
    input  wire [15:0]   f_su_wqv, input wire [223:0] f_su_wq, input wire [255:0] f_su_wqm, input wire [8191:0] f_su_wqd,
    // HC v2 row slots (2 rd + 8 wr)
    input  wire [1:0]    f_hc_rqv, input wire [27:0] f_hc_rq,
    output wire [1:0]    t_hc_rsv, output reg [1023:0] t_hc_rs,
    input  wire [7:0]    f_hc_wqv, input wire [111:0] f_hc_wq, input wire [127:0] f_hc_wqm, input wire [4095:0] f_hc_wqd,
    // PQ native x read {x_addr 19, x_re} -> {x_q 2048, x_rv}
    input  wire [19:0]   f_pqx, output reg [2048:0] t_pqx,
    // edge services (dsfd_vm_static_xio / dsfd_vm_static_wfc): aux read ports 4..11 (aux p carries rows with
    // row[1:0] == p mod 4, the FSR lane rule), returns registered at the request pin + 12 like every client
    input  wire [7:0]    x_av, input wire [111:0] x_ar,
    output wire [7:0]    x_rv, output reg [4095:0] x_rd,
    // engine 12 native forward (codes 4..7) to the edge services
    output wire          nf_v, output wire [83:0] nf_d,
    // Engram MIX4 endpoint (dsfd_engram_mix4_c rq/rs/wq): 20 reads an edge (fixed return slots), 4 row writes (sources 28..31)
    input  wire [19:0]   f_mx_rqv, input wire [279:0] f_mx_rq,
    output wire [19:0]   t_mx_rsv, output reg [10239:0] t_mx_rs,
    input  wire [3:0]    f_mx_wqv, input wire [55:0] f_mx_wq, input wire [63:0] f_mx_wqm, input wire [2047:0] f_mx_wqd,
    // landing rows (stream domain, after the fixed 3:4 transfer): lanes 0/1 scan a0/a1, 2 selector, 3 collector
    input  wire [3:0]    l_v, input wire [2047:0] l_d,
    // edge write sources: capture 16 (sources 32..43, 48..51), collective landing 4 (44..47), WFC 1 (52)
    input  wire [15:0]   cp_v, input wire [223:0] cp_row, input wire [255:0] cp_m, input wire [8191:0] cp_d,
    input  wire [3:0]    cl_v, input wire [55:0] cl_row, input wire [63:0] cl_m, input wire [2047:0] cl_d, input wire [31:0] cl_t,
    input  wire          wf_v, input wire [13:0] wf_row, input wire [511:0] wf_d,
    // external service faults ORed in (e.g. the 3:4 transfers)
    input  wire          x_flt,
    output wire          vm_fault
);
    wire ck = cks;
    reg [1:0] rr;
    always @(posedge ck or negedge rss) if (!rss) rr <= 2'b00; else rr <= {rr[0], 1'b1};
    wire rn = rr[1];

    // ---------------------------------------------------------------- read schedule
    // aux 0..3: PQ x rows (4 an edge); aux 4..7: outbound row streams (xio); aux 8..11: WFC kit reads
    wire [11:0] aux_v = {x_av, {4{f_pqx[0]}}};
    wire [167:0] aux_row;
    genvar a;
    generate for (a = 0; a < 12; a = a + 1) begin : g_aux
        if (a < 4) begin : pq
            assign aux_row[14*a +: 14] = {f_pqx[18:7], a[1:0]};     // x_addr[17:6] * 4 + a
        end else begin : g_edge
            assign aux_row[14*a +: 14] = x_ar[14*(a-4) +: 14];
        end
    end endgenerate
    wire [17:0] n_v; wire [251:0] n_row; wire [89:0] n_slot; wire [2:0] n_group; wire [11:0] a_v; wire [167:0] a_row;
    wire rel_v; wire [2:0] rel_g; wire [31:0] rel_m; wire [17:0] exp_v; wire [89:0] rel_s; wire [11:0] aux_exp;
    wire [419:0] obs_row; wire [19:0] mx_exp; wire [99:0] mx_sl; wire r_flt;
    dsfd_vm_static_rsched u_rs (.ck(ck_rsched), .rst_n(rst_rsched_n), .su_v(f_su_rqv), .su_row(f_su_rq), .hc_v(f_hc_rqv), .hc_row(f_hc_rq),
        .aux_v(aux_v), .aux_row(aux_row), .mx_v(f_mx_rqv), .mx_row(f_mx_rq),
        .mx_expected(mx_exp), .mx_rslot(mx_sl), .sched_fault(r_flt), .n_v(n_v), .n_row(n_row), .n_slot(n_slot), .n_group(n_group), .a_v(a_v), .a_row(a_row),
        .release_v(rel_v), .release_group(rel_g), .release_mask(rel_m), .expected_v(exp_v), .release_slot(rel_s),
        .aux_expected(aux_exp), .obs_row(obs_row));
    reg pq_bad;
    always @(posedge ck) if (!rn) pq_bad <= 1'b0; else if (f_pqx[0] && (f_pqx[19] || f_pqx[6:1] != 6'd0)) pq_bad <= 1'b1;

    // ---------------------------------------------------------------- write sources
    localparam integer NSRC = 53;
    wire [3:0] lo_v; wire [55:0] lo_row; wire [2047:0] lo_d; wire [2:0] l_flt;
    reg [NSRC-1:0] s_v; reg [14*NSRC-1:0] s_row; reg [16*NSRC-1:0] s_m; reg [512*NSRC-1:0] s_d; reg [8*NSRC-1:0] s_t;
    always @* begin : p_src integer c;
        s_v = {NSRC{1'b0}}; s_row = {14*NSRC{1'b0}}; s_m = {16*NSRC{1'b0}}; s_d = {512*NSRC{1'b0}}; s_t = {8*NSRC{1'b0}};
        for (c = 0; c < 16; c = c + 1) begin
            s_v[c] = f_su_wqv[c]; s_row[14*c +: 14] = f_su_wq[14*c +: 14]; s_m[16*c +: 16] = f_su_wqm[16*c +: 16];
            s_d[512*c +: 512] = f_su_wqd[512*c +: 512]; s_t[8*c +: 8] = c[7:0];
        end
        for (c = 0; c < 8; c = c + 1) begin
            s_v[16+c] = f_hc_wqv[c]; s_row[14*(16+c) +: 14] = f_hc_wq[14*c +: 14]; s_m[16*(16+c) +: 16] = f_hc_wqm[16*c +: 16];
            s_d[512*(16+c) +: 512] = f_hc_wqd[512*c +: 512]; s_t[8*(16+c) +: 8] = 8'(16 + c);
        end
        for (c = 0; c < 4; c = c + 1) begin
            s_v[24+c] = lo_v[c]; s_row[14*(24+c) +: 14] = lo_row[14*c +: 14]; s_m[16*(24+c) +: 16] = 16'hffff;
            s_d[512*(24+c) +: 512] = lo_d[512*c +: 512]; s_t[8*(24+c) +: 8] = 8'(24 + c);
        end
        for (c = 0; c < 4; c = c + 1) begin
            s_v[28+c] = f_mx_wqv[c]; s_row[14*(28+c) +: 14] = f_mx_wq[14*c +: 14]; s_m[16*(28+c) +: 16] = f_mx_wqm[16*c +: 16];
            s_d[512*(28+c) +: 512] = f_mx_wqd[512*c +: 512]; s_t[8*(28+c) +: 8] = 8'(28 + c);
        end
        for (c = 0; c < 16; c = c + 1) begin : cap
            integer sc; sc = (c < 12) ? 32 + c : 36 + c;          // lanes 0..11 -> 32..43, 12..15 -> 48..51
            s_v[sc] = cp_v[c]; s_row[14*sc +: 14] = cp_row[14*c +: 14]; s_m[16*sc +: 16] = cp_m[16*c +: 16];
            s_d[512*sc +: 512] = cp_d[512*c +: 512]; s_t[8*sc +: 8] = 8'(sc);
        end
        for (c = 0; c < 4; c = c + 1) begin
            s_v[44+c] = cl_v[c]; s_row[14*(44+c) +: 14] = cl_row[14*c +: 14]; s_m[16*(44+c) +: 16] = cl_m[16*c +: 16];
            s_d[512*(44+c) +: 512] = cl_d[512*c +: 512]; s_t[8*(44+c) +: 8] = cl_t[8*c +: 8];
        end
        s_v[52] = wf_v; s_row[14*52 +: 14] = wf_row; s_m[16*52 +: 16] = 16'hffff; s_d[512*52 +: 512] = wf_d; s_t[8*52 +: 8] = 8'd52;
    end
    wire [31:0] wq_v; wire [447:0] wq_row; wire [511:0] wq_mask; wire [16383:0] wq_data; wire [255:0] wq_tag; wire w_flt;
    dsfd_vm_static_wsched #(.NSRC(NSRC)) u_ws (.ck_control(ck_write_control), .ck_header(ck_write_header), .ck_payload(ck_write_payload),
        .ck_dispatch(ck_write_dispatch), .ck_stage(ck_write_stage),
        .rst_control_n(rst_write_control_n), .rst_header_n(rst_write_header_n), .rst_payload_n(rst_write_payload_n),
        .rst_dispatch_n(rst_write_dispatch_n), .rst_stage_n(rst_write_stage_n), .i_v(s_v), .i_row(s_row), .i_mask(s_m), .i_data(s_d),
        .i_tag(s_t), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_data(wq_data), .wq_tag(wq_tag), .fault(w_flt));

    // ---------------------------------------------------------------- native memory
    wire [71:0] nat_v; wire [9215:0] nat_d; wire [127:0] grp_v; wire [16383:0] grp_d; wire [11:0] grp_id;
    wire [127:0] cm_v; wire [1151:0] cm_a; wire [511:0] cm_m; wire [1023:0] cm_t; wire [27:0] m_flt;
    dsfd_vm_static512_suhc u_mem (.ck_rscatter(ck_mem_fsr), .ck_wcapture(ck_mem_wcapture),.ck_wscatter(ck_mem_wscatter), .ck_return(ck_mem_return), .ck_bank(ck_mem_bank),
        .ck_relay_req(ck_mem_relay_req), .ck_relay_rsp(ck_mem_relay_rsp),
        .rst_rscatter_n(rst_mem_fsr_n), .rst_return_n(rst_mem_return_n), .rst_bank_n(rst_mem_bank_n),
        .rst_wcapture_n(rst_mem_wcapture_n), .rst_wscatter_n(rst_mem_wscatter_n), .rst_relay_n(rst_mem_relay_n),
        .native_rq_v(n_v), .native_rq_row(n_row), .native_rq_slot(n_slot), .native_rq_group(n_group),
        .aux_rq_v(a_v), .aux_rq_row(a_row),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_data(wq_data), .wq_tag(wq_tag),
        .release_v(rel_v), .release_group(rel_g), .release_mask(rel_m),
        .native_expected_v(exp_v), .native_release_slot(rel_s),
        .native_v(nat_v), .native_data(nat_d), .group_v(grp_v), .group_data(grp_d), .group_id(grp_id),
        .commit_v(cm_v), .commit_addr(cm_a), .commit_mask(cm_m), .commit_tag(cm_t), .fault(m_flt));

    // ---------------------------------------------------------------- die output registers (P+12)
    wire o_bad;
    generate if (READ_PIPE == 0) begin : legacy_read
        reg [15:0] q_t_su_rsv; assign t_su_rsv=q_t_su_rsv;
        reg [8191:0] q_t_su_rs; assign t_su_rs=q_t_su_rs;
        reg [1:0] q_t_hc_rsv; assign t_hc_rsv=q_t_hc_rsv;
        reg [1023:0] q_t_hc_rs; assign t_hc_rs=q_t_hc_rs;
        reg [2048:0] q_t_pqx; assign t_pqx=q_t_pqx;
        reg [7:0] q_x_rv; assign x_rv=q_x_rv;
        reg [4095:0] q_x_rd; assign x_rd=q_x_rd;
        reg [19:0] q_t_mx_rsv; assign t_mx_rsv=q_t_mx_rsv;
        reg [10239:0] q_t_mx_rs; assign t_mx_rs=q_t_mx_rs;
        reg [0:0] q_o_bad; assign o_bad=q_o_bad;
    always @(posedge ck) begin : p_out integer p, s; reg bad;
        bad = 1'b0;
        for (p = 0; p < 18; p = p + 1)
            for (s = 1; s < 4; s = s + 1) if (nat_v[18*s + p] != nat_v[p]) bad = 1'b1;
        for (p = 20; p < 28; p = p + 1)
            for (s = 0; s < 4; s = s + 1) if (aux_exp[p-20] && !grp_v[32*s + p]) bad = 1'b1;
        for (p = 0; p < 20; p = p + 1)
            for (s = 0; s < 4; s = s + 1) if (mx_exp[p] && !grp_v[32*s + mx_sl[5*p +: 5]]) bad = 1'b1;
        if (!rn) begin q_t_su_rsv <= 16'd0; q_t_hc_rsv <= 2'd0; q_t_pqx[0] <= 1'b0; q_x_rv <= 8'd0; q_t_mx_rsv <= 20'd0; q_o_bad <= 1'b0; end
        else begin
            q_t_su_rsv <= nat_v[15:0]; q_t_hc_rsv <= nat_v[17:16];
            q_t_pqx[0] <= aux_exp[0] && grp_v[20] && grp_v[52] && grp_v[84] && grp_v[116];
            for (p = 0; p < 8; p = p + 1) q_x_rv[p] <= aux_exp[4+p] && grp_v[24+p] && grp_v[56+p] && grp_v[88+p] && grp_v[120+p];
            q_t_mx_rsv <= mx_exp;
            if (bad) q_o_bad <= 1'b1;
        end
        q_t_su_rs <= nat_d[8191:0]; q_t_hc_rs <= nat_d[9215:8192];
        q_t_pqx[2048:1] <= grp_d[512*20 +: 2048];
        for (p = 0; p < 20; p = p + 1) q_t_mx_rs[512*p +: 512] <= grp_d[512*mx_sl[5*p +: 5] +: 512];
        q_x_rd <= grp_d[512*24 +: 4096];
    end

    end else begin : bounded_read
        wire [7:0] read_fault;
        dsfd_vm_static_read_router u_read (
            .ck_data(ck_read_data), .ck_valid(ck_read_valid),
            .rst_data_n(rst_read_data_n), .rst_valid_n(rst_read_valid_n),
            .slot_data(grp_d), .slot_valid(grp_v), .n_expected(exp_v), .n_slot(rel_s),
            .aux_expected(aux_exp), .mx_expected(mx_exp), .mx_slot(mx_sl),
            .n_data({t_hc_rs,t_su_rs}), .n_valid({t_hc_rsv,t_su_rsv}),
            .pq_data(t_pqx[2048:1]), .pq_valid(t_pqx[0]), .x_data(x_rd), .x_valid(x_rv),
            .mx_data(t_mx_rs), .mx_valid(t_mx_rsv), .fault(read_fault));
        // This diagnostic reduction belongs to the existing explicit core-control root.
        // One additional observation edge; it never gates data or extends a schedule.
        reg fault_q;
        always @(posedge ck) if (!rn) fault_q <= 1'b0; else if (|read_fault) fault_q <= 1'b1;
        assign o_bad=fault_q;
    end endgenerate

    // ---------------------------------------------------------------- engine 12 + static native ops
    wire v_cv; wire [83:0] v_cd; reg v_dv; reg [7:0] v_dt; reg op_bad;
    wire svc_flt = w_flt | |m_flt | |l_flt | pq_bad | o_bad | op_bad | r_flt | x_flt;
    dsfd_vm_seq_static u_seq (.ck(ck_seq), .rst(rst_seq_n), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .o_cv(cm_v), .o_ca(cm_a), .o_cm(cm_m), .o_rv({2'b00, a_v, n_v}), .o_rr({28'd0, obs_row}),
        .v_cv(v_cv), .v_cd(v_cd), .v_dv(v_dv), .v_dt(v_dt), .v_flt(svc_flt),
        .t_inp_su(t_inp_su), .t_inp_hc(t_inp_hc));
    wire [2:0] v_code = v_cd[30:28];
    wire larm_v = v_cv && v_code == 3'd6 && v_cd[27:24] != 4'd7;      // group 7 = collective landing (xio)
    assign nf_v = v_cv; assign nf_d = v_cd;
    always @(posedge ck) begin
        if (!rn) begin v_dv <= 1'b0; op_bad <= 1'b0; end
        else begin
            v_dv <= v_cv;                                  // fixed: every native op retires one edge after its forward
            if (v_cv && (v_code == 3'd5 || v_code == 3'd7 ||
                (v_code == 3'd6 && v_cd[27:24] == 4'd7))) op_bad <= 1'b1; // legacy collective ops removed
        end
        v_dt <= {v_cd[83], v_cd[6:0]};
    end
    dsfd_vm_static_landing u_land (.ck(ck_landing), .rst_n(rst_landing_n), .larm_v(larm_v), .larm_g(v_cd[27:24]), .larm_base(v_cd[20:7]),
        .i_v(l_v), .i_d(l_d), .o_v(lo_v), .o_row(lo_row), .o_d(lo_d), .fault(l_flt));
    assign vm_fault = svc_flt;
endmodule
`default_nettype wire
