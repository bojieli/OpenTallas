`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_a2f_core (S-VM-RTL, 2026-10-16): the STATIC S81 layer-die VM, stream domain, with the ADOPTED A2-F write front
// and hop-1 storage (dsfd_vm_a2f_mem).  Derived from dsfd_vm_static_core (left byte-identical for the legacy parent):
// identical source map (53 sources, tags), read schedule, return lanes, read router / output registers, engine-12
// tile and static landing.  Changes, all fixed-cycle:
//   * write: dsfd_vm_static_wsched + dsfd_vm_static512_suhc write capture -> A2-F front (s81_a2f_controlled_split4m)
//     -> scatter_b8_out PIPE 1 -> b8 -> [HOP1=0: b4] -> bank128.  Measured (tb_dsfd_vm_a2f_diff, source pin P, lane
//     0..2): raw SRAM write P+11+lane (HOP1) / P+12+lane (HOP1=0), returned commit P+12+lane / P+14+lane; legacy
//     profile s81_vm_r4_c2_w1 (WSCATTER_PIPE 1): raw P+10+lane, commit P+12+lane (w0: P+9 / P+11).
//   * read:  HOP1 removes one request and one response register: raw SRAM read Q+7 -> Q+6 and every client read
//     (SU / HC / PQ / aux / MIX) returns 2 stream edges earlier (READ_PIPE 4: L16 -> L14); the release chain uses
//     dsfd_vm_a2f_rsched REL 8 (HOP1=0: REL 10, cycle-identical to dsfd_vm_static_rsched).
//   * clock roots: the legacy write roots (control 1, dispatch 16, stage 128, wcapture 128) are retired; the A2-F front
//     takes header 1 + payload 4 + control 4 + fault 4 + meta 28 + data 128; relay roots 16 (HOP1) / 48 (HOP1=0).
// WSCATTER_PIPE does not exist here: the A2-F scatter is always pin-registered (PIPE 1).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_a2f_core #(parameter integer READ_PIPE=4, parameter integer HOP1=1) (  // READ_PIPE 0 legacy L12 | 1 router L13 | 2 pin-registered router L14 | 4 + pin-registered rsched / return lanes L16
    // cks owns ONLY the legacy READ_PIPE=0 die output registers (native read production: no sink; the VM control
    // glue lives in the hardened engine-12 tile dsfd_vm_seq_tile on ck_seq). Every child root is an explicit
    // independently deliverable clock pin; tying these pins is a TESTBENCH decision only.
    input  wire          cks, rss,
    input  wire          ck_rsched, ck_seq,
    input  wire [4:0]    ck_landing,
    input  wire [3:0]    ck_mem_native_diag, rst_mem_native_diag_n,
    input  wire          ck_write_summary, rst_write_summary_n,
    input  wire [15:0]   ck_mem_fsr,
    input  wire [15:0]   ck_mem_return,
    input  wire [127:0]  ck_mem_bank,
    input  wire [15:0]   ck_mem_wscatter,
    input  wire [(HOP1?16:48)-1:0] ck_mem_relay_req, ck_mem_relay_rsp,
    // A2-F write front roots (replace the legacy write control / dispatch / stage / capture roots)
    input  wire          ck_write_header,
    input  wire [15:0]   ck_write_payload,
    input  wire [3:0]    ck_write_control, ck_write_fault,
    input  wire [27:0]   ck_write_meta,
    input  wire [127:0]  ck_write_data,
    input  wire          rst_rsched_n, rst_seq_n, rst_landing_n,
    input  wire [15:0]   rst_mem_fsr_n,
    input  wire [3:0]    rst_mem_return_n,
    input  wire [127:0]  rst_mem_bank_n,
    input  wire [15:0]   rst_mem_wscatter_n,
    input  wire [(HOP1?16:48)-1:0] rst_mem_relay_n,
    input  wire          rst_write_header_n,
    input  wire [15:0]   rst_write_payload_n,
    input  wire [3:0]    rst_write_control_n, rst_write_fault_n,
    input  wire [27:0]   rst_write_meta_n,
    input  wire [127:0]  rst_write_data_n,
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
    // external service fault sources, checked/registered in the engine-12 tile: 3:4 landing transfer alarms and
    // headers {xw_v, xw_d[1025:1024], xc_v, xc_d[513:512], xs_v, xs_d[513:512]}, edge leaf faults {xio, wfc, cap}
    input  wire [2:0]    x_al, input wire [8:0] x_hdr, input wire [2:0] edge_f, input wire edge_cap_xfault,
    output wire          vm_fault
);

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
    wire rel_v; wire [2:0] rel_g; wire [31:0] rel_m; wire pre_v; wire [2:0] pre_g; wire [31:0] pre_m; wire [17:0] exp_v; wire [89:0] rel_s; wire [11:0] aux_exp;
    wire [419:0] obs_row; wire [19:0] mx_exp; wire [99:0] mx_sl; wire r_flt;
    // HOP1: release E0 + 8 (rows reach the return store two edges earlier); HOP1=0: E0 + 10 (= dsfd_vm_static_rsched).
    // DSFD_VM_A2F_MUT_HOP1_REL: the hop-1 release edge is NOT moved (a missing hop-1 edge) -- must FAIL.
`ifdef DSFD_VM_A2F_MUT_HOP1_REL
    localparam integer RS_REL = 10;
`else
    localparam integer RS_REL = HOP1 ? 8 : 10;
`endif
    generate if (READ_PIPE >= 4) begin : rs_l16
    dsfd_vm_a2f_rsched_p #(.REL(RS_REL)) u_rs (.ck(ck_rsched), .rst_n(rst_rsched_n), .su_v(f_su_rqv), .su_row(f_su_rq), .hc_v(f_hc_rqv), .hc_row(f_hc_rq),
            .aux_v(aux_v), .aux_row(aux_row), .mx_v(f_mx_rqv), .mx_row(f_mx_rq),
            .mx_expected(mx_exp), .mx_rslot(mx_sl), .sched_fault(r_flt), .n_v(n_v), .n_row(n_row), .n_slot(n_slot), .n_group(n_group), .a_v(a_v), .a_row(a_row),
            .release_v(rel_v), .release_group(rel_g), .release_mask(rel_m), .prepare_v(pre_v), .prepare_group(pre_g), .prepare_mask(pre_m),
            .expected_v(exp_v), .release_slot(rel_s),
            .aux_expected(aux_exp), .obs_row(obs_row));
    end else begin : rs_l14
    dsfd_vm_a2f_rsched #(.REL(RS_REL)) u_rs (.ck(ck_rsched), .rst_n(rst_rsched_n), .su_v(f_su_rqv), .su_row(f_su_rq), .hc_v(f_hc_rqv), .hc_row(f_hc_rq),
            .aux_v(aux_v), .aux_row(aux_row), .mx_v(f_mx_rqv), .mx_row(f_mx_rq),
            .mx_expected(mx_exp), .mx_rslot(mx_sl), .sched_fault(r_flt), .n_v(n_v), .n_row(n_row), .n_slot(n_slot), .n_group(n_group), .a_v(a_v), .a_row(a_row),
            .release_v(rel_v), .release_group(rel_g), .release_mask(rel_m), .prepare_v(pre_v), .prepare_group(pre_g), .prepare_mask(pre_m),
            .expected_v(exp_v), .release_slot(rel_s),
            .aux_expected(aux_exp), .obs_row(obs_row));
    end endgenerate

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
    // A2-F front + hop-1 storage: the 53 sources enter the front's W0 header / payload pin registers directly (s_t = the
    // legacy tags: source index, collective tag); compact source-ID capture replaces wdispatch / wstage / write capture.
    wire w_flt; wire [15:0] wf_flt;
    dsfd_vm_native_valid_diag u_write_summary (
        .ck(ck_write_summary), .rst_n(rst_write_summary_n),
        .i_v(32'd0), .expected_v(18'd0), .release_slot(90'd0),
        .i_fault(wf_flt), .fault(w_flt));

    // ---------------------------------------------------------------- native memory
    wire [71:0] nat_v; wire [9215:0] nat_d; wire [127:0] grp_v; wire [16383:0] grp_d; wire [11:0] grp_id;
    wire [127:0] cm_v; wire [1151:0] cm_a; wire [511:0] cm_m; wire [1023:0] cm_t; wire [39:0] m_flt, memory_fault;
    // Preserve the exact hardened seq-tile interface: bit4 was freed when raw
    // scatter faults moved into each slice captured diagnostic bit9.
    assign m_flt={memory_fault[39:5],edge_cap_xfault,memory_fault[3:0]};
    dsfd_vm_a2f_mem #(.RET_PINREG(READ_PIPE >= 4), .HOP1(HOP1)) u_mem (
        .ck_native_diag(ck_mem_native_diag), .rst_native_diag_n(rst_mem_native_diag_n),
        .ck_wf_header(ck_write_header), .ck_wf_payload(ck_write_payload), .ck_wf_control(ck_write_control),
        .ck_wf_fault(ck_write_fault), .ck_wf_meta(ck_write_meta), .ck_wf_data(ck_write_data),
        .rst_wf_header_n(rst_write_header_n), .rst_wf_payload_n(rst_write_payload_n), .rst_wf_control_n(rst_write_control_n),
        .rst_wf_fault_n(rst_write_fault_n), .rst_wf_meta_n(rst_write_meta_n), .rst_wf_data_n(rst_write_data_n),
        .ck_rscatter(ck_mem_fsr), .ck_return(ck_mem_return), .ck_wscatter(ck_mem_wscatter), .ck_bank(ck_mem_bank),
        .ck_relay_req(ck_mem_relay_req), .ck_relay_rsp(ck_mem_relay_rsp),
        .rst_rscatter_n(rst_mem_fsr_n), .rst_return_n(rst_mem_return_n), .rst_wscatter_n(rst_mem_wscatter_n),
        .rst_bank_n(rst_mem_bank_n), .rst_relay_n(rst_mem_relay_n),
        .native_rq_v(n_v), .native_rq_row(n_row), .native_rq_slot(n_slot), .native_rq_group(n_group),
        .aux_rq_v(a_v), .aux_rq_row(a_row),
        .i_v(s_v), .i_row(s_row), .i_tag(s_t), .i_mask(s_m), .i_data(s_d),
        .release_v(rel_v), .release_group(rel_g), .release_mask(rel_m),
        .prepare_v(pre_v), .prepare_group(pre_g), .prepare_mask(pre_m),
        .native_expected_v(exp_v), .native_release_slot(rel_s),
        .native_v(nat_v), .native_data(nat_d), .group_v(grp_v), .group_data(grp_d), .group_id(grp_id),
        .commit_v(cm_v), .commit_addr(cm_a), .commit_mask(cm_m), .commit_tag(cm_t), .fault(memory_fault), .w_fault(wf_flt));

    // ---------------------------------------------------------------- die output registers (P+12)
    wire [7:0] out_fault;
    generate if (READ_PIPE == 0) begin : legacy_read
        wire ck = cks;     // legacy READ_PIPE=0 output stage only (native read production: cks has no sink)
        reg [1:0] rr;
        always @(posedge ck or negedge rss) if (!rss) rr <= 2'b00; else rr <= {rr[0], 1'b1};
        wire rn = rr[1];
        reg [15:0] q_t_su_rsv; assign t_su_rsv=q_t_su_rsv;
        reg [8191:0] q_t_su_rs; assign t_su_rs=q_t_su_rs;
        reg [1:0] q_t_hc_rsv; assign t_hc_rsv=q_t_hc_rsv;
        reg [1023:0] q_t_hc_rs; assign t_hc_rs=q_t_hc_rs;
        reg [2048:0] q_t_pqx; assign t_pqx=q_t_pqx;
        reg [7:0] q_x_rv; assign x_rv=q_x_rv;
        reg [4095:0] q_x_rd; assign x_rd=q_x_rd;
        reg [19:0] q_t_mx_rsv; assign t_mx_rsv=q_t_mx_rsv;
        reg [10239:0] q_t_mx_rs; assign t_mx_rs=q_t_mx_rs;
        reg [0:0] q_o_bad; assign out_fault={7'd0,q_o_bad};
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
        // READ_PIPE 1: R0/R1 leaves (L13).  READ_PIPE 2: the same leaves with every input pin-registered
        // (dsfd_vm_static_read_router_p, L14; native capture audit 2026-10-15).
        if (READ_PIPE == 1) begin : l13
        dsfd_vm_static_read_router u_read (
            .ck_data(ck_read_data), .ck_valid(ck_read_valid),
            .rst_data_n(rst_read_data_n), .rst_valid_n(rst_read_valid_n),
            .slot_data(grp_d), .slot_valid(grp_v), .n_expected(exp_v), .n_slot(rel_s),
            .aux_expected(aux_exp), .mx_expected(mx_exp), .mx_slot(mx_sl),
            .n_data({t_hc_rs,t_su_rs}), .n_valid({t_hc_rsv,t_su_rsv}),
            .pq_data(t_pqx[2048:1]), .pq_valid(t_pqx[0]), .x_data(x_rd), .x_valid(x_rv),
            .mx_data(t_mx_rs), .mx_valid(t_mx_rsv), .fault(read_fault));
        end else begin : l14
        dsfd_vm_static_read_router_p u_read (
            .ck_data(ck_read_data), .ck_valid(ck_read_valid),
            .rst_data_n(rst_read_data_n), .rst_valid_n(rst_read_valid_n),
            .slot_data(grp_d), .slot_valid(grp_v), .n_expected(exp_v), .n_slot(rel_s),
            .aux_expected(aux_exp), .mx_expected(mx_exp), .mx_slot(mx_sl),
            .n_data({t_hc_rs,t_su_rs}), .n_valid({t_hc_rsv,t_su_rsv}),
            .pq_data(t_pqx[2048:1]), .pq_valid(t_pqx[0]), .x_data(x_rd), .x_valid(x_rv),
            .mx_data(t_mx_rs), .mx_valid(t_mx_rsv), .fault(read_fault));
        end
        // read-router faults are registered (sticky) in the engine-12 tile; never gate data or extend a schedule.
        assign out_fault=read_fault;
    end endgenerate

    // ---------------------------------------------------------------- engine 12 + static native ops + control glue
    wire larm_v; wire [3:0] larm_g; wire [13:0] larm_base;
    dsfd_vm_seq_tile u_seq (.ck(ck_seq), .rst(rst_seq_n), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .o_cv(cm_v), .o_ca(cm_a), .o_cm(cm_m), .o_rv({2'b00, a_v, n_v}), .o_rr({28'd0, obs_row}),
        .t_inp_su(t_inp_su), .t_inp_hc(t_inp_hc), .nf_v(nf_v), .nf_d(nf_d),
        .larm_v(larm_v), .larm_g(larm_g), .larm_base(larm_base),
        .pqx_chk({f_pqx[19], f_pqx[6:1], f_pqx[0]}), .read_fault(out_fault), .edge_f(edge_f), .x_hdr(x_hdr), .x_al(x_al),
        .w_flt(w_flt), .m_flt(m_flt), .l_flt(l_flt), .r_flt(r_flt), .vm_fault(vm_fault));
    // Five source-identical native hard leaves: four lane pin-register/data paths and a two-edge fault join.
    // Normal data age/II remain 2/1. Diagnostic lane flags reach seq two edges later than the monolith.
`ifdef OT_VM_LANDING_PINREG0
    dsfd_vm_static_landing #(.PINREG(0)) u_land (.ck(ck_landing[0]), .rst_n(rst_landing_n), .larm_v(larm_v), .larm_g(larm_g), .larm_base(larm_base),
`else
    dsfd_vm_static_landing_joined u_land (.ck(ck_landing), .rst_n(rst_landing_n), .larm_v(larm_v), .larm_g(larm_g), .larm_base(larm_base),
`endif
        .i_v(l_v), .i_d01(l_d[1023:0]), .i_d23(l_d[2047:1024]), .o_v(lo_v), .o_row(lo_row),
        .o_d01(lo_d[1023:0]), .o_d23(lo_d[2047:1024]), .fault(l_flt));
endmodule
`default_nettype wire
