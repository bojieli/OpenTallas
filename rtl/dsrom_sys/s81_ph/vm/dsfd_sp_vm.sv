`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_sp_vm -- the S81 layer-die VM master (s81-vm-1011 under ds-1010, 2026-10-11).  Serial (0.9 GHz) domain.
//
// The banked memory is the CLOSED systolic tile dsfd_vm_bgq (rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv, NSTG 2,
// DW 128; s81b-vm_bgq-sys2s-30327ff97-tc-rd TT +57.87 / FF +10.16 / DRC 0): NS = 4 bit-sliced columns of 4 tiles,
// 8 row ports x 32 banks x 512 rows x 512 b, stall-free fixed latency L = 4*NSTG + QD + 8 = 20 from the tile-0 pins,
// ops take effect in global (issue cycle, port) order.  This file adds the two hard blocks that make it a master:
//
//   dsfd_vm_fe (N of the columns, abutting the tile-0 N faces): every client's REQUEST side, one order register
//     (stage B) shared by all ports, per-slice output copies (stage C) at the tile pins.
//   dsfd_vm_be (S of the columns, abutting the tile-3 S faces): every client's RESPONSE side.
//
// The systolic memory moves requests and read data N -> S only, so a read issued at the top returns at the bottom
// 2,000 um away.  Nothing is sent back up through the columns: response-side endpoints live in the BE, whose pins are
// die buses; per-read metadata the BE needs (P2 lane identity / word) rides DOWN in the unused write-data field of the
// read request (tile-3 f_d, 12 cycles after issue; the read data follows L - 12 = 8 cycles later); FE status rides
// down in the write-only port 3's read-return lane (tile-0 r_d / r_f -> tile-3 o_d / o_f, pass-through).  The only
// upward signal is the 1-bit P2 credit return t_p2c (BE -> FE die net, any latency: it is a credit).
//
// Port map (NP = 8, fixed; every port issues <= 1 op a cycle and never stalls):
//   p0  WFC kit write + even read   (dsfd_vm_wfc_ep RD2 m_*, the closed ep RTL instantiated in the FE)
//   p1  WFC kit odd read            (dsfd_vm_wfc_ep RD2 m1_*)
//   p2  capture W: posted row writes (grant link, ot_dsrom_mtp_lrx_rtt RTT-sized, c_ready = 1)
//   p3  dsfd_sp_ctrl VM write port  (vwe / vwa / vwd)
//   p4  dsfd_sp_ctrl VM read port   (vre / vra -> BE vrq / vrv; the ctrl runs USE_VM_RVALID 1)
//   p5  P2 lane-0 stream reader      (engine command P2RD; flits to dsfd_vm_p2_ep from the BE, credit-paced)
//   p6  generic row port X0          (fixed latency; for the SU / HC / gather masters, s81-suhc-1011)
//   p7  generic row port X1
//
// Row-completion counter (NSLOT slots, armed by engine command ARM): counts the write ops that land in
// [base, base + nrows) at the order register; when nops writes have landed the slot completes -> engine done (dv / dt
// = tag) and, if armed with notify, rows-ready {user} to dsfd_vm_mtp_ep (c_wv / c_wd).  EARLY-READ ASSERTION: a read on
// any port into an armed, incomplete slot range at the order register sets sticky fault bit 0 (fail closed) and
// $error()s in simulation.
//
// Engine command channel (one dsfd_sp_ctrl cv / cd[84] / dv / dt[8] channel; published contract
// physical/s81_ph_views/vm_master/contract_1011.json):
//   cd[83:80] op   1 ARM   [79:78] slot [77] notify [76:67] user [66:53] base [52:38] nrows [37:23] nops [7:0] tag
//                  2 P2ID  [79:6] identity (74 b) for the following P2RD commands (no done)
//                  3 P2RD  [79:66] base [65:59] nwords-1 [58:50] expert [49] shared [7:0] tag   (done at the last read)
//                  0 nop; any other op -> fault bit 7
//
// Mutants (negative controls, bench tools/s81_vm/s81_vm_gate.py):
//   OT_SPVM_MUT_STALE  capture writes reach the memory one cycle after the order register's position (an extra
//                      register on port 2 only): a read ordered after the write sees the old row -> stale read
//   OT_SPVM_MUT_DROPW  the posted-write path drops every 61st capture write (accepted by the link, never issued)
//   OT_SPVM_MUT_EARLY  the completion counter completes one write early: consumers driven by done read early
// ---------------------------------------------------------------------------------------------------------------

// ================================================================================================ front end
module dsfd_vm_fe #(
    parameter integer NS = 4,           // bit-sliced memory columns (128 b each)
    parameter integer CF = 8,           // capture link: relay stations capture -> VM (data) / VM -> capture (grant)
    parameter integer CR = 8,
    parameter integer VF = 13,          // WFC kit link stations (dsfd_vm_wfc_ep VF / VR)
    parameter integer VR = 13,
    parameter integer NSLOT = 4,        // completion-counter slots
    parameter integer P2D = 40,         // BE P2 flit FIFO depth = the reader's credits
    parameter integer CQD = 4           // P2RD command queue depth
) (
    input  wire [0:0]    ck,
    input  wire [0:0]    rst,
    // WFC kit VM channels (dsfd_vm_wfc_ep RD2 die side; its response t_srq is produced in the BE)
    input  wire [0:0]    f_swv, input wire [526:0] f_swd, output wire [0:0] t_swg,
    input  wire [0:0]    f_srv, input wire [30:0]  f_srd, output wire [0:0] t_srg,
    output wire [52:0]   t_ks,
    // capture W posted row writes {row 14, mask 16, data 512}
    input  wire [0:0]    f_cwv, input wire [541:0] f_cwd, output wire [0:0] t_cwg,
    // dsfd_sp_ctrl VM port (request side)
    input  wire [0:0]    vwe, input wire [13:0] vwa, input wire [511:0] vwd,
    input  wire [0:0]    vre, input wire [13:0] vra,
    // dsfd_sp_ctrl engine channel
    input  wire [0:0]    cv, input wire [83:0] cd, output reg [0:0] dv, output reg [7:0] dt,
    // generic row ports X0 / X1 (ports 6 / 7)
    input  wire [1:0]    x_v, input wire [1:0] x_we, input wire [27:0] x_row, input wire [31:0] x_mask,
    input  wire [1023:0] x_d,
    // rows-ready to dsfd_vm_mtp_ep (core side c_w*)
    output reg  [0:0]    c_wv, output reg [9:0] c_wd, input wire [0:0] c_wr,
    // P2 credit return from the BE
    input  wire [0:0]    f_p2c,
    // memory request ports, slice-major (to the tile-0 N faces): slice s = [s*8*W +: 8*W]
    output reg  [NS*8-1:0]     m_v,
    output reg  [NS*8-1:0]     m_we,
    output reg  [NS*8*14-1:0]  m_row,
    output reg  [NS*8*4-1:0]   m_mask,
    output reg  [NS*8*128-1:0] m_d,
    // tile-0 read-return inputs: zero except the FE status (port 3 lane of slice 0, fault bit of every slice)
    output reg  [NS*8-1:0]     m_rv,
    output reg  [NS*8*128-1:0] m_rd,
    output reg  [NS*4-1:0]     m_rf,
    output reg  [NS*3-1:0]     m_ro,
    output reg  [7:0]          fe_flt     // FE sticky fault vector (also sent down to the BE)
);
    localparam integer NP = 8, RA = 14;
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));

    // ---------------------------------------------------------------- p0 / p1: WFC kit endpoint (request half)
    wire e_v, e_we, e1_v, e_err; wire [14:0] e_row, e1_row; wire [511:0] e_d;
    dsfd_vm_wfc_ep #(.FLIT(512), .NW(21), .USER_W(10), .VWA(15), .VF(VF), .VR(VR), .PIPE(2), .RD2(1)) u_wfc (
        .ck(ck), .rst(rst),
        .f_swv(f_swv), .f_swd(f_swd), .t_swg(t_swg), .f_srv(f_srv), .f_srd(f_srd), .t_srg(t_srg),
        .t_srq(), .t_err(e_err), .t_ks(t_ks),
        .m_v(e_v), .m_we(e_we), .m_row(e_row), .m_d(e_d), .m_ov(1'b0), .m_od(512'd0), .m_fault(1'b0),
        .m1_v(e1_v), .m1_row(e1_row), .m1_ov(1'b0), .m1_od(512'd0));

    // ---------------------------------------------------------------- p2: capture posted writes
    wire c_v; wire [541:0] c_d;
    ot_dsrom_mtp_lrx_rtt #(.W(542), .D(CF + CR + 4), .SEL(1), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                           .FORWARD_HOPS(CF), .RETURN_HOPS(CR)) u_cw (
        .clk(clk), .rst_n(rn), .l_valid(f_cwv[0]), .l_ready(t_cwg[0]), .l_data(f_cwd),
        .c_valid(c_v), .c_ready(1'b1), .c_data(c_d));
`ifdef OT_SPVM_MUT_DROPW
    reg [5:0] dw_n;
    always @(posedge clk) if (!rn) dw_n <= 6'd0; else if (c_v) dw_n <= (dw_n == 6'd60) ? 6'd0 : dw_n + 6'd1;
    wire c_take = c_v && dw_n != 6'd60;                         // MUTANT: every 61st posted write vanishes
`else
    wire c_take = c_v;
`endif

    // ---------------------------------------------------------------- p3 / p4 / p6 / p7: pin flops
    reg a_we, a_re; reg [13:0] a_wa, a_ra; reg [511:0] a_wd;
    reg [1:0] a_xv, a_xwe; reg [27:0] a_xrow; reg [31:0] a_xm; reg [1023:0] a_xd;
    reg a_cv; reg [83:0] a_cd; reg a_p2c;
    always @(posedge clk) begin
        if (!rn) begin a_we <= 1'b0; a_re <= 1'b0; a_xv <= 2'b00; a_cv <= 1'b0; a_p2c <= 1'b0; end
        else begin a_we <= vwe[0]; a_re <= vre[0]; a_xv <= x_v; a_cv <= cv[0]; a_p2c <= f_p2c[0]; end
        a_wa <= vwa; a_wd <= vwd; a_ra <= vra; a_xwe <= x_we; a_xrow <= x_row; a_xm <= x_mask; a_xd <= x_d; a_cd <= cd;
    end

    // ---------------------------------------------------------------- engine commands
    wire [3:0] op = a_cd[83:80];
    wire is_arm = a_cv && op == 4'd1, is_pid = a_cv && op == 4'd2, is_prd = a_cv && op == 4'd3;
    wire is_bad = a_cv && op != 4'd0 && op != 4'd1 && op != 4'd2 && op != 4'd3;
    reg [73:0] id_r;
    always @(posedge clk) if (!rn) id_r <= 74'd0; else if (is_pid) id_r <= a_cd[79:6];
    // P2RD queue {identity 74, base 14, nw 7, expert 9, shared 1, tag 8} = 113
    localparam integer QW = 113, QB = (CQD > 1) ? $clog2(CQD) : 1;
    reg [QW-1:0] cq [0:CQD-1];
    reg [QB-1:0] cq_h, cq_t; reg [QB:0] cq_n;
    wire [QW-1:0] cq_in = {id_r, a_cd[79:66], a_cd[65:59], a_cd[58:50], a_cd[49], a_cd[7:0]};
    // P2 reader state
    reg r_act; reg [13:0] r_base; reg [6:0] r_w, r_nw; reg [73:0] r_id; reg [8:0] r_ex; reg r_sh; reg [7:0] r_tag;
    reg [$clog2(P2D+1):0] cr;
    wire r_iss = r_act && cr != 0;
    wire r_last = r_iss && r_w == r_nw;
    wire cq_pop = (!r_act || r_last) && cq_n != 0;
    wire cq_push = is_prd && cq_n != CQD;
    integer qi;
    always @(posedge clk) begin
        if (!rn) begin cq_h <= 0; cq_t <= 0; cq_n <= 0; r_act <= 1'b0; cr <= P2D; end
        else begin
            if (cq_push) begin cq[cq_t] <= cq_in; cq_t <= (cq_t == CQD - 1) ? 0 : cq_t + 1'b1; end
            if (cq_pop) cq_h <= (cq_h == CQD - 1) ? 0 : cq_h + 1'b1;
            cq_n <= cq_n + cq_push - cq_pop;
            if (cq_pop) begin
                r_act <= 1'b1; {r_id, r_base, r_nw, r_ex, r_sh, r_tag} <= cq[cq_h]; r_w <= 7'd0;
            end else if (r_last) r_act <= 1'b0;
            if (r_iss && !r_last) r_w <= r_w + 7'd1;
            cr <= cr - r_iss + a_p2c;
        end
    end

    // ---------------------------------------------------------------- stage B: the order register (all ports)
    reg [NP-1:0] b_v, b_we; reg [NP*RA-1:0] b_row; reg [NP*16-1:0] b_m; reg [NP*512-1:0] b_d;
    reg [7:0] b_bad;     // row range faults of this cycle (ep row[14])
    always @(posedge clk) begin
        if (!rn) b_v <= {NP{1'b0}};
        else begin
            b_v[0] <= e_v && !e_row[14]; b_v[1] <= e1_v && !e1_row[14]; b_v[2] <= c_take; b_v[3] <= a_we;
            b_v[4] <= a_re; b_v[5] <= r_iss; b_v[6] <= a_xv[0]; b_v[7] <= a_xv[1];
        end
        b_we <= {a_xwe[1], a_xwe[0], 1'b0, 1'b0, 1'b1, 1'b1, 1'b0, e_we};
        b_row <= {a_xrow[27:14], a_xrow[13:0], r_base + {7'd0, r_w}, a_ra, a_wa, c_d[541:528], e1_row[13:0], e_row[13:0]};
        b_m <= {a_xm[31:16], a_xm[15:0], 16'hffff, 16'hffff, 16'hffff, c_d[527:512], 16'hffff, 16'hffff};
        b_d <= {a_xd[1023:512], a_xd[511:0], {420'd0, r_id, r_ex, r_sh, r_last, r_w}, 512'd0, a_wd, c_d[511:0], 512'd0, e_d};
    end

    // ---------------------------------------------------------------- stage C: per-slice copies at the tile pins
    // (the MUT_STALE register sits between B and C on port 2 only)
`ifdef OT_SPVM_MUT_STALE
    reg s_v2, s_we2; reg [RA-1:0] s_row2; reg [15:0] s_m2; reg [511:0] s_d2;
    always @(posedge clk) begin
        if (!rn) s_v2 <= 1'b0; else s_v2 <= b_v[2];
        s_we2 <= b_we[2]; s_row2 <= b_row[2*RA +: RA]; s_m2 <= b_m[2*16 +: 16]; s_d2 <= b_d[2*512 +: 512];
    end
    wire [NP-1:0] c_vv = {b_v[7:3], s_v2, b_v[1:0]};
    wire [NP-1:0] c_we = {b_we[7:3], s_we2, b_we[1:0]};
    wire [NP*RA-1:0] c_row = {b_row[NP*RA-1:3*RA], s_row2, b_row[2*RA-1:0]};
    wire [NP*16-1:0] c_m = {b_m[NP*16-1:3*16], s_m2, b_m[2*16-1:0]};
    wire [NP*512-1:0] c_dd = {b_d[NP*512-1:3*512], s_d2, b_d[2*512-1:0]};
`else
    wire [NP-1:0] c_vv = b_v, c_we = b_we;
    wire [NP*RA-1:0] c_row = b_row;
    wire [NP*16-1:0] c_m = b_m;
    wire [NP*512-1:0] c_dd = b_d;
`endif
    integer s, p;
    always @(posedge clk) begin
        for (s = 0; s < NS; s = s + 1) begin
            if (!rn) m_v[s*NP +: NP] <= {NP{1'b0}}; else m_v[s*NP +: NP] <= c_vv;
            m_we[s*NP +: NP] <= c_we;
            m_row[s*NP*RA +: NP*RA] <= c_row;
            for (p = 0; p < NP; p = p + 1) begin
                m_mask[(s*NP + p)*4 +: 4] <= c_m[p*16 + 4*s +: 4];
                m_d[(s*NP + p)*128 +: 128] <= c_dd[p*512 + 128*s +: 128];
            end
        end
    end

    // ---------------------------------------------------------------- row-completion counter + early-read check
    // write-capable ports: 0, 2, 3, 6, 7; read-capable: 0, 1, 4, 5, 6, 7 (by b_we per op)
    reg [NSLOT-1:0] sl_arm, sl_dp, sl_rp;           // armed / engine done pending / rows-ready pending
    reg [13:0] sl_base [0:NSLOT-1]; reg [15:0] sl_end [0:NSLOT-1];
    reg [14:0] sl_need [0:NSLOT-1], sl_cnt [0:NSLOT-1];
    reg [9:0] sl_user [0:NSLOT-1]; reg [7:0] sl_tag [0:NSLOT-1]; reg [NSLOT-1:0] sl_ntf;
    reg [3:0] inc [0:NSLOT-1];
    reg [NSLOT-1:0] hit_r, cmpl;
    integer k, q;
    always @* begin
        for (k = 0; k < NSLOT; k = k + 1) begin
            inc[k] = 4'd0; hit_r[k] = 1'b0;
            for (q = 0; q < NP; q = q + 1)
                if (b_v[q] && b_row[q*RA +: RA] >= sl_base[k] && {2'b00, b_row[q*RA +: RA]} < sl_end[k]) begin
                    if (b_we[q]) inc[k] = inc[k] + 4'd1;
                    else hit_r[k] = 1'b1;
                end
`ifdef OT_SPVM_MUT_EARLY
            cmpl[k] = sl_arm[k] && sl_cnt[k] + inc[k] + 15'd1 >= sl_need[k];   // MUTANT: one write early
`else
            cmpl[k] = sl_arm[k] && sl_cnt[k] + inc[k] >= sl_need[k];
`endif
        end
    end
    wire [1:0] arm_s = a_cd[79:78];
    // P2 done pending: tags of finished P2RD commands, in order (<= CQD + 1 outstanding)
    reg [7:0] pd_q [0:CQD]; reg [$clog2(CQD+2)-1:0] pd_h, pd_t, pd_n;
    reg early, ovf_c, ovf_cr, rearm, ovf_pd;
    reg [NSLOT-1:0] dsel, rsel;          // one-hot picks of the output arbiters
    always @* begin
        dsel = {NSLOT{1'b0}}; rsel = {NSLOT{1'b0}};
        for (k = NSLOT - 1; k >= 0; k = k - 1) begin
            if (sl_dp[k]) dsel = {{(NSLOT-1){1'b0}}, 1'b1} << k;
            if (sl_rp[k]) rsel = {{(NSLOT-1){1'b0}}, 1'b1} << k;
        end
    end
    wire d_slot = |sl_dp;                      // slot dones take priority over P2 dones
    wire c_w_go = !c_wv[0] || c_wr[0];         // rows-ready output register free (or being taken)
    reg [7:0] dsel_tag; reg [9:0] rsel_user;
    always @* begin
        dsel_tag = 8'd0; rsel_user = 10'd0;
        for (k = 0; k < NSLOT; k = k + 1) begin
            if (dsel[k]) dsel_tag = dsel_tag | sl_tag[k];
            if (rsel[k]) rsel_user = rsel_user | sl_user[k];
        end
    end
    always @(posedge clk) begin
        if (!rn) begin
            sl_arm <= 0; sl_dp <= 0; sl_rp <= 0; sl_ntf <= 0; dv <= 1'b0; c_wv <= 1'b0;
            pd_h <= 0; pd_t <= 0; pd_n <= 0;
            early <= 1'b0; ovf_c <= 1'b0; ovf_cr <= 1'b0; rearm <= 1'b0; ovf_pd <= 1'b0;
        end else begin
            for (k = 0; k < NSLOT; k = k + 1) begin
                if (sl_arm[k]) sl_cnt[k] <= sl_cnt[k] + inc[k];
                if (hit_r[k] && sl_arm[k] && !cmpl[k]) early <= 1'b1;
                if (cmpl[k]) begin sl_arm[k] <= 1'b0; sl_dp[k] <= 1'b1; if (sl_ntf[k]) sl_rp[k] <= 1'b1; end
            end
            if (is_arm) begin
                if (sl_arm[arm_s] || sl_dp[arm_s] || sl_rp[arm_s]) rearm <= 1'b1;
                sl_arm[arm_s] <= 1'b1; sl_ntf[arm_s] <= a_cd[77]; sl_user[arm_s] <= a_cd[76:67];
                sl_base[arm_s] <= a_cd[66:53]; sl_end[arm_s] <= {2'b00, a_cd[66:53]} + {1'b0, a_cd[52:38]};
                sl_need[arm_s] <= a_cd[37:23]; sl_cnt[arm_s] <= 15'd0; sl_tag[arm_s] <= a_cd[7:0];
            end
            // engine done output (one a cycle)
            dv <= d_slot || pd_n != 0;
            dt <= d_slot ? dsel_tag : pd_q[pd_h];
            if (d_slot) sl_dp <= (sl_dp & ~dsel) | (cmpl & {NSLOT{1'b1}});
            // P2 done queue
            if (r_last) begin pd_q[pd_t] <= r_tag; pd_t <= (pd_t == CQD) ? 0 : pd_t + 1'b1; end
            if (!d_slot && pd_n != 0) pd_h <= (pd_h == CQD) ? 0 : pd_h + 1'b1;
            pd_n <= pd_n + r_last - (!d_slot && pd_n != 0);
            if (r_last && pd_n == CQD + 1) ovf_pd <= 1'b1;
            // rows-ready output (held until the ep takes it)
            if (c_w_go) begin
                c_wv <= |sl_rp; c_wd <= rsel_user;
                sl_rp <= (sl_rp & ~rsel) | (cmpl & sl_ntf);
            end
            if (is_prd && cq_n == CQD && !cq_pop) ovf_c <= 1'b1;
            if (cr > P2D) ovf_cr <= 1'b1;
        end
    end
    // early-read assertion (simulation); the RTL fault above is the fail-closed copy
`ifndef SYNTHESIS
    always @(posedge clk) if (rn) for (k = 0; k < NSLOT; k = k + 1)
        if (hit_r[k] && sl_arm[k] && !cmpl[k])
            $error("SPVM EARLY_READ: read into slot %0d range [%0d, %0d) at %0d of %0d writes", k, sl_base[k], sl_end[k],
                   sl_cnt[k], sl_need[k]);
`endif

    // ---------------------------------------------------------------- FE status, sent down the port-3 return lane
    reg rbad;
    always @(posedge clk) if (!rn) rbad <= 1'b0; else if ((e_v && e_row[14]) || (e1_v && e1_row[14])) rbad <= 1'b1;
    always @(posedge clk) begin
        if (!rn) fe_flt <= 8'd0;
        else fe_flt <= fe_flt | {is_bad, ovf_pd, rearm, 1'b0, ovf_cr, ovf_c, e_err | rbad, early};
    end
    always @(posedge clk) begin
        m_rv <= {NS*8{1'b0}}; m_ro <= {NS*3{1'b0}};
        m_rd <= {NS*8*128{1'b0}};
        m_rd[3*128 +: 8] <= fe_flt;                 // slice 0, port 3 lane (write-only port: pure pass-through)
        for (s = 0; s < NS; s = s + 1) m_rf[s*4 +: 4] <= {|fe_flt, 3'b000};
    end
endmodule

// ================================================================================================ back end
module dsfd_vm_be #(
    parameter integer NS = 4,
    parameter integer P2D = 40,         // P2 flit FIFO depth (the FE reader's credits)
    parameter integer MD = 9            // tile-3 f_* (request exit) -> o_* (read data) skew (NSTG 2, QD 4)
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,
    // tile-3 S faces, slice-major
    input  wire [NS*8-1:0]     o_v,
    input  wire [NS*8*128-1:0] o_d,
    input  wire [NS*4-1:0]     o_f,
    input  wire [NS*3-1:0]     o_o,
    input  wire [0:0]          f_v5,     // slice 0 tile-3 f_v[5]
    input  wire [0:0]          f_we5,    // slice 0 tile-3 f_we[5]
    input  wire [91:0]         f_m5,     // slice 0 tile-3 f_d[5*128 +: 92]: P2 metadata
    // WFC kit response (dsfd_vm_wfc_ep RD2 t_srq) and sticky status
    output reg  [1025:0]       t_srq,
    output reg  [0:0]          t_err,
    // dsfd_sp_ctrl VM read return
    output reg  [0:0]          vrv,
    output reg  [511:0]        vrq,
    // generic ports X0 / X1 read return
    output reg  [1:0]          x_ov,
    output reg  [1023:0]       x_od,
    // P2 lane 0 to dsfd_vm_p2_ep (core side c_l0*) + credit to the FE
    output wire [0:0]          c_l0v,
    output wire [603:0]        c_l0d,
    input  wire [0:0]          c_l0r,
    output reg  [0:0]          t_p2c,
    // status
    output reg  [0:0]          flt,
    output reg  [15:0]         fvec,
    output reg  [2:0]          max_occ
);
    localparam integer NP = 8;
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    // pin flops
    reg [NS*8-1:0] q_v; reg [NS*8*128-1:0] q_d; reg [NS*4-1:0] q_f; reg [NS*3-1:0] q_o;
    reg q_fv; reg [91:0] q_fm;
    always @(posedge clk) begin
        if (!rn) begin q_v <= 0; q_f <= 0; q_fv <= 1'b0; end
        else begin q_v <= o_v; q_f <= o_f; q_fv <= f_v5[0] && !f_we5[0]; end
        q_d <= o_d; q_o <= o_o; q_fm <= f_m5;
    end
    // row data of port p = the four 128-b slices
    function automatic [511:0] row_of(input [NS*8*128-1:0] d, input integer p);
        integer ss; begin
            row_of = 512'd0;
            for (ss = 0; ss < NS; ss = ss + 1) row_of[128*ss +: 128] = d[(ss*NP + p)*128 +: 128];
        end
    endfunction
    wire [NP-1:0] v0 = q_v[NP-1:0];
    // ---------------------------------------------------------------- responses (one output register)
    always @(posedge clk) begin
        if (!rn) begin t_srq <= 0; vrv <= 1'b0; x_ov <= 2'b00; end
        else begin
            t_srq <= {v0[1], row_of(q_d, 1), v0[0], row_of(q_d, 0)};
            vrv <= v0[4]; x_ov <= v0[7:6];
        end
        vrq <= row_of(q_d, 4);
        x_od <= {row_of(q_d, 7), row_of(q_d, 6)};
    end
    // ---------------------------------------------------------------- P2: metadata delay line + flit FIFO
    reg [MD-1:0] md_v; reg [91:0] md_m [0:MD-1];
    integer i;
    always @(posedge clk) begin
        if (!rn) md_v <= 0; else md_v <= {md_v[MD-2:0], q_fv};
        md_m[0] <= q_fm;
        for (i = 1; i < MD; i = i + 1) md_m[i] <= md_m[i-1];
    end
    wire mv = md_v[MD-1]; wire [91:0] mm = md_m[MD-1];
    // metadata {identity 74, expert 9, shared 1, last 1, word 7}; flit {identity74, expert9, shared1, last1, word7, data512}
    wire [603:0] flit = {mm, row_of(q_d, 5)};
    localparam integer PB = $clog2(P2D);
    reg [603:0] pf [0:P2D-1];
    reg [PB-1:0] ph, pt; reg [PB:0] pn;
    reg ov; reg [603:0] od;                    // output register (c_l0v / c_l0d)
    wire take = ov && c_l0r[0];
    wire ld = (!ov || take) && (pn != 0 || mv);
    wire byp = pn == 0;                        // the arriving flit goes straight to the output register
    wire push = mv && !(ld && byp);
    wire popq = ld && !byp;
    assign c_l0v = ov; assign c_l0d = od;
    reg p_ovf, p_mis;
    always @(posedge clk) begin
        if (!rn) begin ph <= 0; pt <= 0; pn <= 0; ov <= 1'b0; t_p2c <= 1'b0; p_ovf <= 1'b0; p_mis <= 1'b0; end
        else begin
            if (push) begin pf[pt] <= flit; pt <= (pt == P2D - 1) ? 0 : pt + 1'b1; end
            if (popq) ph <= (ph == P2D - 1) ? 0 : ph + 1'b1;
            pn <= pn + push - popq;
            if (ld) begin ov <= 1'b1; od <= byp ? flit : pf[ph]; end
            else if (take) ov <= 1'b0;
            t_p2c <= take;
            if (push && pn == P2D) p_ovf <= 1'b1;
            if (mv != v0[5]) p_mis <= 1'b1;    // metadata / read-data alignment check
        end
    end
    // ---------------------------------------------------------------- status
    reg s_mis; reg [15:0] fv; integer ss;
    always @(posedge clk) begin
        if (!rn) begin s_mis <= 1'b0; flt <= 1'b0; fvec <= 16'd0; t_err <= 1'b0; max_occ <= 3'd0; end
        else begin
            for (ss = 1; ss < NS; ss = ss + 1) if (q_v[ss*NP +: NP] != q_v[NP-1:0] || q_f[ss*4 +: 4] != q_f[3:0]) s_mis <= 1'b1;
            // [3:0] memory {fault, und, mis, ovf}; [11:4] FE vector (port-3 lane); [12] P2 FIFO overflow;
            // [13] P2 metadata misalignment; [14] slice mismatch
            fv = {1'b0, s_mis, p_mis, p_ovf, q_d[3*128 +: 8], q_f[3:0]};
            fvec <= fvec | fv;
            flt <= flt | (|fv);
            t_err <= t_err | (|fv);
            max_occ <= (q_o[2:0] > max_occ) ? q_o[2:0] : max_occ;
        end
    end
endmodule

// ================================================================================================ composition
// dsfd_sp_vm_m: the exact composition netlist (bench + composition record): FE, NS x 4 dsfd_vm_bgq (NSTG 2), BE.
// The die places the FE, the 16 tiles and the BE by abutment (physical/s81_ph_views/vm_master/composition.json).
module dsfd_sp_vm_m #(
    parameter integer NS = 4, parameter integer NSTG = 2, parameter integer QD = 4, parameter integer MACRO = 1,
    parameter integer CF = 8, parameter integer CR = 8, parameter integer VF = 13, parameter integer VR = 13,
    parameter integer NSLOT = 4, parameter integer P2D = 40, parameter integer CQD = 4
) (
    input  wire [0:0]    ck, input wire [0:0] rst,
    input  wire [0:0]    f_swv, input wire [526:0] f_swd, output wire [0:0] t_swg,
    input  wire [0:0]    f_srv, input wire [30:0]  f_srd, output wire [0:0] t_srg,
    output wire [52:0]   t_ks,
    output wire [1025:0] t_srq, output wire [0:0] t_err,
    input  wire [0:0]    f_cwv, input wire [541:0] f_cwd, output wire [0:0] t_cwg,
    input  wire [0:0]    vwe, input wire [13:0] vwa, input wire [511:0] vwd,
    input  wire [0:0]    vre, input wire [13:0] vra, output wire [0:0] vrv, output wire [511:0] vrq,
    input  wire [0:0]    cv, input wire [83:0] cd, output wire [0:0] dv, output wire [7:0] dt,
    input  wire [1:0]    x_v, input wire [1:0] x_we, input wire [27:0] x_row, input wire [31:0] x_mask,
    input  wire [1023:0] x_d, output wire [1:0] x_ov, output wire [1023:0] x_od,
    output wire [0:0]    c_wv, output wire [9:0] c_wd, input wire [0:0] c_wr,
    output wire [0:0]    c_l0v, output wire [603:0] c_l0d, input wire [0:0] c_l0r,
    output wire [0:0]    flt, output wire [15:0] fvec, output wire [2:0] max_occ
);
    localparam integer NP = 8, NT = 4, RA = 14, OW = 3;
    // tile-3 f_* (request exit, 4 x (NSTG + 1) after the tile-0 pins) -> o_* (read data): measured 9 at NSTG 2 / QD 4
    // (the read-latency formula L = 4*NSTG + QD + 8 counts from the cycle the requester drives the pins)
    localparam integer MD = 4 * NSTG + QD + 9 - 4 * (NSTG + 1);
    wire [NS*NP-1:0] mv, mwe, mrv; wire [NS*NP*RA-1:0] mrow; wire [NS*NP*4-1:0] mm; wire [NS*NP*128-1:0] md, mrd;
    wire [NS*4-1:0] mrf; wire [NS*3-1:0] mro; wire [7:0] fe_flt;
    wire p2c;
    dsfd_vm_fe #(.NS(NS), .CF(CF), .CR(CR), .VF(VF), .VR(VR), .NSLOT(NSLOT), .P2D(P2D), .CQD(CQD)) u_fe (
        .ck(ck), .rst(rst), .f_swv(f_swv), .f_swd(f_swd), .t_swg(t_swg), .f_srv(f_srv), .f_srd(f_srd), .t_srg(t_srg),
        .t_ks(t_ks), .f_cwv(f_cwv), .f_cwd(f_cwd), .t_cwg(t_cwg), .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra),
        .cv(cv), .cd(cd), .dv(dv), .dt(dt), .x_v(x_v), .x_we(x_we), .x_row(x_row), .x_mask(x_mask), .x_d(x_d),
        .c_wv(c_wv), .c_wd(c_wd), .c_wr(c_wr), .f_p2c(p2c),
        .m_v(mv), .m_we(mwe), .m_row(mrow), .m_mask(mm), .m_d(md), .m_rv(mrv), .m_rd(mrd), .m_rf(mrf), .m_ro(mro),
        .fe_flt(fe_flt));
    wire [NS*NP-1:0] ov; wire [NS*NP*128-1:0] od; wire [NS*4-1:0] of; wire [NS*3-1:0] oo;
    wire [NP-1:0] f0v, f0we; wire [NP*128-1:0] f0d;
    genvar h, t;
    generate for (h = 0; h < NS; h = h + 1) begin : g_h
        wire [NP-1:0] cv_ [0:NT], cwe [0:NT], cov [0:NT];
        wire [NP*RA-1:0] crow [0:NT]; wire [NP*4-1:0] cm [0:NT]; wire [NP*128-1:0] cd_ [0:NT], cod [0:NT];
        wire [3:0] cof [0:NT]; wire [OW-1:0] coo [0:NT];
        assign cv_[0] = mv[h*NP +: NP]; assign cwe[0] = mwe[h*NP +: NP]; assign crow[0] = mrow[h*NP*RA +: NP*RA];
        assign cm[0] = mm[h*NP*4 +: NP*4]; assign cd_[0] = md[h*NP*128 +: NP*128];
        assign cov[0] = mrv[h*NP +: NP]; assign cod[0] = mrd[h*NP*128 +: NP*128]; assign cof[0] = mrf[h*4 +: 4];
        assign coo[0] = mro[h*3 +: 3];
        for (t = 0; t < NT; t = t + 1) begin : g_t
            wire [1:0] gid = t;
            dsfd_vm_bgq #(.NP(NP), .NB(32), .NBL(8), .QD(QD), .RQ(8), .MACRO(MACRO), .DW(128), .NSTG(NSTG)) u_bg (
                .ck(ck), .rs(rst), .grp(gid),
                .i_v(cv_[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cm[t]), .i_d(cd_[t]),
                .f_v(cv_[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cm[t+1]), .f_d(cd_[t+1]),
                .r_v(cov[t]), .r_d(cod[t]), .r_f(cof[t]), .r_o(coo[t]),
                .o_v(cov[t+1]), .o_d(cod[t+1]), .o_f(cof[t+1]), .o_o(coo[t+1]));
        end
        assign ov[h*NP +: NP] = cov[NT]; assign od[h*NP*128 +: NP*128] = cod[NT]; assign of[h*4 +: 4] = cof[NT];
        assign oo[h*3 +: 3] = coo[NT];
        if (h == 0) begin : g_f
            assign f0v = cv_[NT]; assign f0we = cwe[NT]; assign f0d = cd_[NT];
        end
    end endgenerate
    dsfd_vm_be #(.NS(NS), .P2D(P2D), .MD(MD)) u_be (
        .ck(ck), .rst(rst), .o_v(ov), .o_d(od), .o_f(of), .o_o(oo), .f_v5(f0v[5]), .f_we5(f0we[5]), .f_m5(f0d[5*128 +: 92]),
        .t_srq(t_srq), .t_err(t_err), .vrv(vrv), .vrq(vrq), .x_ov(x_ov), .x_od(x_od),
        .c_l0v(c_l0v), .c_l0d(c_l0d), .c_l0r(c_l0r), .t_p2c(p2c), .flt(flt), .fvec(fvec), .max_occ(max_occ));
endmodule
