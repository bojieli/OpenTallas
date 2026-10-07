`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE S81-PH capture, TILED (redesign pass 2026-10-06, DESIGN SIMPLIFICATION RULES).  cap_m3 (ot_s81ph_cap_p as
// one 1015 x 302 view) reached post-CTS WNS -1678 ps: 200k flops on one 132k-sink clock tree (1.9 ns insertion),
// synthesis merged the kept per-group constant copies across the view (g_grp[8].rs -> g_grp[0] w_dt), the quota
// multiply sat in front of exp_q, and the reset tree failed recovery.  The capture is split into hardened tiles:
//
//   dsfd_capt_grp   16 roots (replicated x8): pin flops on every input, the per-root capture (bf16 RNE, quota,
//                   received count, checks, address, pair packer, stream->serial ratio CDC), its own reset
//                   synchronisers, a registered 16-root fault OR and done AND, outputs from flops.
//   dsfd_capt_ctl   the phase word, the accept decision and the central state, one registered constant bus per tile
//                   (with that tile's share of the profile quota precomputed: no root index inside the tile), the
//                   8-input fault OR / done AND, the status lane CDC.
//   ot_s81ph_cap_t  the composition: ctl + 8 tiles joined by pin-to-pin registered hops (<= ~450 um, no station).
//
// Exactness is transaction-level against the rd64 reference (bench tb_s81ph_gather_capture +UNORD): every root's VM
// writes of a non-fault phase are the reference's; fault phases fault and write only individually valid rows.
// Phase alignment: the tile sees an accepted phase's constants from cycle t'+5 (t' = the phase word in the ctl pin
// flop); a row in the tile pin flop at cycle t is checked (quota / position / error) in R4 at t+4, so it belongs to
// the phases accepted at t' <= t-1 exactly as in rd64.  The address / range / format terms are computed AFTER the
// check (W1..W3), with the held constants of the row's own phase (a new phase is accepted only after `drained`,
// which waits for every row stage of every tile to be empty).  A range-error row is never written (fail closed);
// its fault lands 3 cycles after the check.  Writes stop at most ~11 cycles after the first bad row (cap_p: 6).
// ---------------------------------------------------------------------------------------------------------------

// tile constant bus (ctl -> grp), KB bits: {gate, go, ob30, ops30, np3, fmt2, rs16, rows_hi8, lo_t6, lo, hi}
`define CAPT_KB 99

module dsfd_capt_grp #(
    parameter integer NR = 16,               // roots per tile
    parameter integer LD = 4
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,          // stream die reset net (active low, asynchronous assert)
    input  wire [0:0]          ckv,
    input  wire [0:0]          rsv,          // serial die reset net
    input  wire [NR*53-1:0]    f_row,        // per root {e, pos3, row16, fp32 32, v} (the gather's t_capture slice)
    input  wire [`CAPT_KB-1:0] f_k,          // from dsfd_capt_ctl (registered there)
    output wire [NR*104-1:0]   t_vm,         // per root {row1 {data32, addr19}, v1, row0 {data32, addr19}, v0} (serial)
    output wire [1:0]          t_sb,         // {all done, any bad} (stream, from flops)
    // status lane crossing (r6: moved out of dsfd_capt_ctl, which is single-clock now): only the tile next to the
    // control tile uses it (the others get 0 and leave t_st open)
    input  wire [63:0]         f_sn,         // status word (stream, from dsfd_capt_ctl t_sn)
    output wire [63:0]         t_st          // status word (serial)
);
    localparam integer KB = `CAPT_KB;
    localparam integer NH = 2;               // reset / constant copies (one per 8 roots)
    integer i;
    genvar g;
    // ---- reset synchronisers (2 kept copies per domain); rst_s[1] = the view SDC's rst_mcp2 cell
    reg [1:0] rst_s, rv_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rv_s <= 2'b00; else rv_s <= {rv_s[0], 1'b1};
    (* keep *) reg [NH-1:0] rst_h, rsv_h;
    always @(posedge ck[0] or negedge rst_s[1]) if (!rst_s[1]) rst_h <= {NH{1'b0}}; else rst_h <= {NH{1'b1}};
    always @(posedge ckv[0] or negedge rv_s[1]) if (!rv_s[1]) rsv_h <= {NH{1'b0}}; else rsv_h <= {NH{1'b1}};
    // ---- pin flops (data: no reset; valid bits reset)
    reg [NR*53-1:0] fr;
    always @(posedge ck[0]) fr <= f_row;
    reg [KB-1:0] kq;
    always @(posedge ck[0]) kq <= f_k;
    wire        k_gate = kq[98], k_go = kq[97];
    // ---- K2: kept copies of the constants + per-root quota precompute (t'+4)
    (* keep *) reg [KB-1:0] k2 [0:NH-1];
    always @(posedge ck[0]) for (i = 0; i < NH; i = i + 1) k2[i] <= kq;
    // grp r7 (as capt_g2 g2b; capt_grp-48203c4d9-f SS -242: address multiply / adds / compare at 20-25 levels): one more constant stage K3 (the
    // phase constants and go move one cycle later, the rows gain one stage R5 in front of the check, so every
    // row-vs-phase relation is unchanged) and the address path split W1 / W1b / W2 with kept Kogge-Stone adds
    (* keep *) reg [KB-1:0] k3 [0:NH-1];
    always @(posedge ck[0]) for (i = 0; i < NH; i = i + 1) k3[i] <= k2[i];
    // g2c / r8 (capt_g2 54b6490d5 SS -31 on the quota multiply pr -> q2, -1 on ob + row): K4 constant stage + R6 row
    // stage (relations unchanged), quota multiply as two registered shift-add levels, low address add kept KS
    (* keep *) reg [KB-1:0] k4 [0:NH-1];
    always @(posedge ck[0]) for (i = 0; i < NH; i = i + 1) k4[i] <= k3[i];
    wire [7:0]  k_rhi = kq[15:8];
    wire [5:0]  k_lot = kq[7:2];
    wire [2:0]  k_np  = kq[36:34];
    wire [3:0]  positions = {1'b0, k_np} + 4'd1;

    wire [NR-1:0] r_bad, r_done, hovf_now;
    wire [2*NR-1:0] wv_o; wire [NR*102-1:0] wd_o;
    generate for (g = 0; g < NR; g = g + 1) begin : g_r
        localparam integer H = g / (NR / NH);
        wire          rs_n = rst_h[H];
        wire [KB-1:0] k = k4[H];
        wire          go = k[97];
        // held constants of the phase (updated by go at the K2 stage: visible from t'+5)
        reg [29:0] ob, ops; reg [2:0] np; reg [1:0] fmt; reg [15:0] rs; reg lo, hi, gate;
        always @(posedge ck[0]) if (go) {ob, ops, np, fmt, rs, lo, hi} <= {k[96:67], k[66:37], k[36:34], k[33:32],
                                                                          k[31:16], k[1], k[0]};
        reg gate0;
        always @(posedge ck[0] or negedge rs_n) if (!rs_n) begin gate0 <= 1'b0; gate <= 1'b0; end else begin gate0 <= k[98]; gate <= gate0; end
        // quota exactly as ot_dsrom_s81_phase_capture_profile for this root: the ctl sends lo_t = clamp(rows[7:0] -
        // 32 * tile, 0, 32), so (rows[7:0] > 2R) == (lo_t > 2g) for R = 16 * tile + g
        reg [13:0] q2; reg [9:0] rr; reg [3:0] pr;
        wire [9:0] rows_r = {1'b0, k_rhi, 1'b0} + 10'(k_lot > 6'(2 * g)) + 10'(k_lot > 6'(2 * g + 1));
        reg [13:0] qa, qb;
        always @(posedge ck[0]) begin
            rr <= rows_r; pr <= positions;
            qa <= (pr[0] ? {4'd0, rr} : 14'd0) + (pr[1] ? {3'd0, rr, 1'b0} : 14'd0);
            qb <= (pr[2] ? {2'd0, rr, 2'b0} : 14'd0) + (pr[3] ? {1'd0, rr, 3'b0} : 14'd0);
            q2 <= qa + qb;
        end
        // rows: pin (t) -> R1 bf16 RNE (t+1) -> R2 -> R3 -> R4 (t+4): check
        reg v1, v2, v3, v4, v5, v6; reg [51:0] d1, d2, d3, d4, d5, d6; reg [15:0] bf1, bf2, bf3, bf4, bf5, bf6;
        wire [51:0] d0 = fr[53 * g + 1 +: 52];
        wire [32:0] rb = {1'b0, d0[31:0]} + 33'h7FFF + {32'd0, d0[16]};
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin v1 <= 1'b0; v2 <= 1'b0; v3 <= 1'b0; v4 <= 1'b0; v5 <= 1'b0; v6 <= 1'b0; end
            else begin v1 <= fr[53 * g]; v2 <= v1; v3 <= v2; v4 <= v3; v5 <= v4; v6 <= v5; end
        always @(posedge ck[0]) begin d5 <= d4; bf5 <= bf4; d6 <= d5; bf6 <= bf5; end
`ifdef S81PH_MUTANT_BF16_TRUNC
        always @(posedge ck[0]) begin d1 <= d0; bf1 <= d0[31:16]; d2 <= d1; bf2 <= bf1; d3 <= d2; bf3 <= bf2;
                                      d4 <= d3; bf4 <= bf3; end
`else
        always @(posedge ck[0]) begin d1 <= d0; bf1 <= rb[31:16]; d2 <= d1; bf2 <= bf1; d3 <= d2; bf3 <= bf2;
                                      d4 <= d3; bf4 <= bf3; end
`endif
        // quota / received (reset by the accept)
        reg [13:0] exp_q; reg [18:0] rcv;
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin exp_q <= 14'd0; rcv <= 19'd0; end
            else if (go) begin exp_q <= q2; rcv <= 19'd0; end
            else if (v6) rcv <= rcv + 19'd1;
        // check (R4)
        wire [15:0] row = d6[47:32]; wire [2:0] pos = d6[50:48]; wire e = d6[51];
`ifdef S81PH_MUT_NOOVER
        wire over = 1'b0;
`else
        wire over = rcv >= {5'd0, exp_q};
`endif
        wire bad1 = v6 && (e || pos > np || over);
        // W1: partial products / low address half / split compare; constants sampled here only (carried along)
        reg w1v, w1ok, w1bad; reg [16:0] s1lo; reg [13:0] obh; reg [32:0] pp01, pp2; reg hlt, heq, llt;
        reg [31:0] f1; reg [15:0] b1; reg [1:0] fmt1; reg lo1, hi1;
        wire [32:0] t0 = pos[0] ? {3'd0, ops} : 33'd0, t1 = pos[1] ? {2'd0, ops, 1'b0} : 33'd0;
        wire [32:0] p01; wire p01c; wire [15:0] sls; wire slc;
        ot_hdc_ksadd_k #(.W(16)) u_sl (.a(ob[15:0]), .b(row), .cin(1'b0), .s(sls), .cout(slc));
        ot_hdc_ksadd_k #(.W(33)) u_p01 (.a(t0), .b(t1), .cin(1'b0), .s(p01), .cout(p01c));
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin w1v <= 1'b0; w1ok <= 1'b0; w1bad <= 1'b0; end
            else begin w1v <= v6; w1ok <= v6 && !bad1; w1bad <= bad1; end
        always @(posedge ck[0]) begin
            s1lo <= {slc, sls}; obh <= ob[29:16];
            pp01 <= p01; pp2 <= pos[2] ? {1'b0, ops, 2'b0} : 33'd0;
            hlt <= row[15:8] < rs[15:8]; heq <= row[15:8] == rs[15:8]; llt <= row[7:0] < rs[7:0];
            f1 <= d6[31:0]; b1 <= bf6; fmt1 <= fmt; lo1 <= lo; hi1 <= hi;
        end
        // W1b: address halves, product, compare
        reg w1bv, w1bok, w1bbad; reg [30:0] s1; reg [32:0] m1; reg lt1; reg [31:0] f2; reg [15:0] b2; reg [1:0] fmt2; reg lo2, hi2;
        wire [32:0] mp; wire mpc;
        ot_hdc_ksadd_k #(.W(33)) u_m (.a(pp01), .b(pp2), .cin(1'b0), .s(mp), .cout(mpc));
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin w1bv <= 1'b0; w1bok <= 1'b0; w1bbad <= 1'b0; end
            else begin w1bv <= w1v; w1bok <= w1ok; w1bbad <= w1bad; end
        always @(posedge ck[0]) begin
            s1 <= {{1'b0, obh} + {14'd0, s1lo[16]}, s1lo[15:0]};
            m1 <= mp; lt1 <= hlt | (heq & llt);
            f2 <= f1; b2 <= b1; fmt2 <= fmt1; lo2 <= lo1; hi2 <= hi1;
        end
        // W2: address, data select
        reg w2v, w2ok, w2bad; reg [33:0] a2; reg [31:0] dt2;
        wire [33:0] as; wire asc;
        ot_hdc_ksadd_k #(.W(34)) u_a (.a({3'd0, s1}), .b({1'b0, m1}), .cin(1'b0), .s(as), .cout(asc));
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin w2v <= 1'b0; w2ok <= 1'b0; w2bad <= 1'b0; end
            else begin w2v <= w1bv; w2ok <= w1bok; w2bad <= w1bbad; end
        always @(posedge ck[0]) begin
            a2 <= as;
            dt2 <= (fmt2 == 2'd1 || (fmt2 == 2'd0 && (lt1 ? lo2 : hi2))) ? f2 : {b2, 16'b0};
        end
        // W3 (t+7): range, write
        wire range_error = |a2[33:19];
        reg w_ok, w_bad, wv3; reg [18:0] w_a; reg [31:0] w_dt;
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin w_ok <= 1'b0; w_bad <= 1'b0; wv3 <= 1'b0; end
            else begin w_ok <= w2ok && !range_error; w_bad <= w2bad || (w2v && range_error); wv3 <= w2v; end
        always @(posedge ck[0]) begin w_a <= a2[18:0]; w_dt <= dt2; end
        wire vm_valid = w_ok && !gate;
        assign r_bad[g]  = w_bad;
        assign r_done[g] = rcv == {5'd0, exp_q} && !(v1 || v2 || v3 || v4 || v5 || v6 || w1v || w1bv || w2v || wv3);
        // ---- pair packer + crossing (as ot_s81ph_cap_p)
        reg [50:0] h [0:3];
        reg [1:0] hr, hw;
        reg [2:0] hc;
        reg hovf;
        wire wr;
        wire [50:0] din = {w_dt, w_a};
        wire [2:0] npop = (!wr || hc == 3'd0) ? 3'd0 : (hc == 3'd1) ? 3'd1 : 3'd2;
        wire crdy = (hc - npop) < 3'd4;
        assign hovf_now[g] = vm_valid && !crdy;
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin hr <= 2'd0; hw <= 2'd0; hc <= 3'd0; hovf <= 1'b0; end
            else begin
                hr <= hr + npop[1:0];
                if (vm_valid && crdy) begin hw <= hw + 2'd1; h[hw] <= din; end
                hc <= hc - npop + ((vm_valid && crdy) ? 3'd1 : 3'd0);
                if (vm_valid && !crdy) hovf <= 1'b1;
            end
        wire cv; wire [102:0] cd;
        ot_ratio_cdc_fifo #(.W(103), .DEPTH(LD)) u_x (.wclk(ck[0]), .wrst_n(rs_n), .w_v(hc != 3'd0), .w_rdy(wr),
            .w_d({h[hr + 2'd1], hc >= 3'd2, h[hr]}), .rclk(ckv[0]), .rrst_n(rsv_h[H]), .r_v(cv), .r_rdy(1'b1),
            .r_d(cd), .w_live(), .r_live());
        reg [1:0] ov; reg [101:0] od;
        always @(posedge ckv[0] or negedge rsv_h[H]) if (!rsv_h[H]) ov <= 2'b00; else ov <= {cv & cd[51], cv};
        always @(posedge ckv[0]) begin od[50:0] <= cd[50:0]; od[101:51] <= cd[102:52]; end
        assign t_vm[104 * g +: 104] = {od[101:51], ov[1], od[50:0], ov[0]};
    end endgenerate
    // ---- registered 16-root fault OR / done AND (two levels), outputs from flops
    reg [3:0] o1, a1; reg o2, a2r;
    integer q;
    always @(posedge ck[0] or negedge rst_h[0])
        if (!rst_h[0]) begin o1 <= 4'd0; a1 <= 4'd0; o2 <= 1'b0; a2r <= 1'b0; end
        else begin
            for (q = 0; q < 4; q = q + 1) begin
                o1[q] <= |(r_bad[4 * q +: 4] | hovf_now[4 * q +: 4]);
                a1[q] <= &r_done[4 * q +: 4];
            end
            o2 <= |o1; a2r <= &a1;
        end
    assign t_sb = {a2r, o2};
    reg [63:0] snq;
    always @(posedge ck[0]) snq <= f_sn;
    wire s_v; wire [63:0] s_d;
    ot_ratio_cdc_fifo #(.W(64), .DEPTH(2)) u_s (.wclk(ck[0]), .wrst_n(rst_h[1]), .w_v(1'b1), .w_rdy(), .w_d(snq),
        .rclk(ckv[0]), .rrst_n(rsv_h[1]), .r_v(s_v), .r_rdy(1'b1), .r_d(s_d), .w_live(), .r_live());
    reg [63:0] stq;
    always @(posedge ckv[0] or negedge rsv_h[1]) if (!rsv_h[1]) stq <= 64'd0; else if (s_v) stq <= s_d;
    assign t_st = stq;
`ifndef SYNTHESIS
    initial if (NR != 16) $fatal(1, "dsfd_capt_grp: NR must be 16");
`endif
endmodule

module dsfd_capt_g2 #(
    parameter integer NR = 16,               // roots per tile
    parameter integer LD = 4
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,          // stream die reset net (active low, asynchronous assert)
    input  wire [NR*53-1:0]    f_row,        // per root {e, pos3, row16, fp32 32, v} (the gather's t_capture slice)
    input  wire [`CAPT_KB-1:0] f_k,          // from dsfd_capt_ctl (registered there)
    output wire [NR*52-1:0]    t_w,          // per root {data32, addr19, v}: the VM write, from a flop (to dsfd_capt_x)
    input  wire [0:0]          f_ho,         // dsfd_capt_x: sticky hold-buffer overflow (fault)
    output wire [1:0]          t_sb          // {all done, any bad} (stream, from flops)
);
    localparam integer KB = `CAPT_KB;
    localparam integer NH = 2;               // reset / constant copies (one per 8 roots)
    integer i;
    genvar g;
    // ---- reset synchronisers (2 kept copies per domain); rst_s[1] = the view SDC's rst_mcp2 cell
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    (* keep *) reg [NH-1:0] rst_h;
    always @(posedge ck[0] or negedge rst_s[1]) if (!rst_s[1]) rst_h <= {NH{1'b0}}; else rst_h <= {NH{1'b1}};
    // ---- pin flops (data: no reset; valid bits reset)
    reg [NR*53-1:0] fr;
    always @(posedge ck[0]) fr <= f_row;
    reg [KB-1:0] kq;
    always @(posedge ck[0]) kq <= f_k;
    wire        k_gate = kq[98], k_go = kq[97];
    // ---- K2: kept copies of the constants + per-root quota precompute (t'+4)
    (* keep *) reg [KB-1:0] k2 [0:NH-1];
    always @(posedge ck[0]) for (i = 0; i < NH; i = i + 1) k2[i] <= kq;
    // g2b (capt_g2 safe SS -266: address multiply / adds / compare at 20-25 levels): one more constant stage K3 (the
    // phase constants and go move one cycle later, the rows gain one stage R5 in front of the check, so every
    // row-vs-phase relation is unchanged) and the address path split W1 / W1b / W2 with kept Kogge-Stone adds
    (* keep *) reg [KB-1:0] k3 [0:NH-1];
    always @(posedge ck[0]) for (i = 0; i < NH; i = i + 1) k3[i] <= k2[i];
    // g2c / r8 (capt_g2 54b6490d5 SS -31 on the quota multiply pr -> q2, -1 on ob + row): K4 constant stage + R6 row
    // stage (relations unchanged), quota multiply as two registered shift-add levels, low address add kept KS
    (* keep *) reg [KB-1:0] k4 [0:NH-1];
    always @(posedge ck[0]) for (i = 0; i < NH; i = i + 1) k4[i] <= k3[i];
    wire [7:0]  k_rhi = kq[15:8];
    wire [5:0]  k_lot = kq[7:2];
    wire [2:0]  k_np  = kq[36:34];
    wire [3:0]  positions = {1'b0, k_np} + 4'd1;

    wire [NR-1:0] r_bad, r_done, hovf_now;
    wire [2*NR-1:0] wv_o; wire [NR*102-1:0] wd_o;
    generate for (g = 0; g < NR; g = g + 1) begin : g_r
        localparam integer H = g / (NR / NH);
        wire          rs_n = rst_h[H];
        wire [KB-1:0] k = k4[H];
        wire          go = k[97];
        // held constants of the phase (updated by go at the K2 stage: visible from t'+5)
        reg [29:0] ob, ops; reg [2:0] np; reg [1:0] fmt; reg [15:0] rs; reg lo, hi, gate;
        always @(posedge ck[0]) if (go) {ob, ops, np, fmt, rs, lo, hi} <= {k[96:67], k[66:37], k[36:34], k[33:32],
                                                                          k[31:16], k[1], k[0]};
        reg gate0;
        always @(posedge ck[0] or negedge rs_n) if (!rs_n) begin gate0 <= 1'b0; gate <= 1'b0; end else begin gate0 <= k[98]; gate <= gate0; end
        // quota exactly as ot_dsrom_s81_phase_capture_profile for this root: the ctl sends lo_t = clamp(rows[7:0] -
        // 32 * tile, 0, 32), so (rows[7:0] > 2R) == (lo_t > 2g) for R = 16 * tile + g
        reg [13:0] q2; reg [9:0] rr; reg [3:0] pr;
        wire [9:0] rows_r = {1'b0, k_rhi, 1'b0} + 10'(k_lot > 6'(2 * g)) + 10'(k_lot > 6'(2 * g + 1));
        reg [13:0] qa, qb;
        always @(posedge ck[0]) begin
            rr <= rows_r; pr <= positions;
            qa <= (pr[0] ? {4'd0, rr} : 14'd0) + (pr[1] ? {3'd0, rr, 1'b0} : 14'd0);
            qb <= (pr[2] ? {2'd0, rr, 2'b0} : 14'd0) + (pr[3] ? {1'd0, rr, 3'b0} : 14'd0);
            q2 <= qa + qb;
        end
        // rows: pin (t) -> R1 bf16 RNE (t+1) -> R2 -> R3 -> R4 (t+4): check
        reg v1, v2, v3, v4, v5, v6; reg [51:0] d1, d2, d3, d4, d5, d6; reg [15:0] bf1, bf2, bf3, bf4, bf5, bf6;
        wire [51:0] d0 = fr[53 * g + 1 +: 52];
        wire [32:0] rb = {1'b0, d0[31:0]} + 33'h7FFF + {32'd0, d0[16]};
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin v1 <= 1'b0; v2 <= 1'b0; v3 <= 1'b0; v4 <= 1'b0; v5 <= 1'b0; v6 <= 1'b0; end
            else begin v1 <= fr[53 * g]; v2 <= v1; v3 <= v2; v4 <= v3; v5 <= v4; v6 <= v5; end
        always @(posedge ck[0]) begin d5 <= d4; bf5 <= bf4; d6 <= d5; bf6 <= bf5; end
`ifdef S81PH_MUTANT_BF16_TRUNC
        always @(posedge ck[0]) begin d1 <= d0; bf1 <= d0[31:16]; d2 <= d1; bf2 <= bf1; d3 <= d2; bf3 <= bf2;
                                      d4 <= d3; bf4 <= bf3; end
`else
        always @(posedge ck[0]) begin d1 <= d0; bf1 <= rb[31:16]; d2 <= d1; bf2 <= bf1; d3 <= d2; bf3 <= bf2;
                                      d4 <= d3; bf4 <= bf3; end
`endif
        // quota / received (reset by the accept)
        reg [13:0] exp_q; reg [18:0] rcv;
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin exp_q <= 14'd0; rcv <= 19'd0; end
            else if (go) begin exp_q <= q2; rcv <= 19'd0; end
            else if (v6) rcv <= rcv + 19'd1;
        // check (R4)
        wire [15:0] row = d6[47:32]; wire [2:0] pos = d6[50:48]; wire e = d6[51];
`ifdef S81PH_MUT_NOOVER
        wire over = 1'b0;
`else
        wire over = rcv >= {5'd0, exp_q};
`endif
        wire bad1 = v6 && (e || pos > np || over);
        // W1: partial products / low address half / split compare; constants sampled here only (carried along)
        reg w1v, w1ok, w1bad; reg [16:0] s1lo; reg [13:0] obh; reg [32:0] pp01, pp2; reg hlt, heq, llt;
        reg [31:0] f1; reg [15:0] b1; reg [1:0] fmt1; reg lo1, hi1;
        wire [32:0] t0 = pos[0] ? {3'd0, ops} : 33'd0, t1 = pos[1] ? {2'd0, ops, 1'b0} : 33'd0;
        wire [32:0] p01; wire p01c; wire [15:0] sls; wire slc;
        ot_hdc_ksadd_k #(.W(16)) u_sl (.a(ob[15:0]), .b(row), .cin(1'b0), .s(sls), .cout(slc));
        ot_hdc_ksadd_k #(.W(33)) u_p01 (.a(t0), .b(t1), .cin(1'b0), .s(p01), .cout(p01c));
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin w1v <= 1'b0; w1ok <= 1'b0; w1bad <= 1'b0; end
            else begin w1v <= v6; w1ok <= v6 && !bad1; w1bad <= bad1; end
        always @(posedge ck[0]) begin
            s1lo <= {slc, sls}; obh <= ob[29:16];
            pp01 <= p01; pp2 <= pos[2] ? {1'b0, ops, 2'b0} : 33'd0;
            hlt <= row[15:8] < rs[15:8]; heq <= row[15:8] == rs[15:8]; llt <= row[7:0] < rs[7:0];
            f1 <= d6[31:0]; b1 <= bf6; fmt1 <= fmt; lo1 <= lo; hi1 <= hi;
        end
        // W1b: address halves, product, compare
        reg w1bv, w1bok, w1bbad; reg [30:0] s1; reg [32:0] m1; reg lt1; reg [31:0] f2; reg [15:0] b2; reg [1:0] fmt2; reg lo2, hi2;
        wire [32:0] mp; wire mpc;
        ot_hdc_ksadd_k #(.W(33)) u_m (.a(pp01), .b(pp2), .cin(1'b0), .s(mp), .cout(mpc));
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin w1bv <= 1'b0; w1bok <= 1'b0; w1bbad <= 1'b0; end
            else begin w1bv <= w1v; w1bok <= w1ok; w1bbad <= w1bad; end
        always @(posedge ck[0]) begin
            s1 <= {{1'b0, obh} + {14'd0, s1lo[16]}, s1lo[15:0]};
            m1 <= mp; lt1 <= hlt | (heq & llt);
            f2 <= f1; b2 <= b1; fmt2 <= fmt1; lo2 <= lo1; hi2 <= hi1;
        end
        // W2: address, data select
        reg w2v, w2ok, w2bad; reg [33:0] a2; reg [31:0] dt2;
        wire [33:0] as; wire asc;
        ot_hdc_ksadd_k #(.W(34)) u_a (.a({3'd0, s1}), .b({1'b0, m1}), .cin(1'b0), .s(as), .cout(asc));
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin w2v <= 1'b0; w2ok <= 1'b0; w2bad <= 1'b0; end
            else begin w2v <= w1bv; w2ok <= w1bok; w2bad <= w1bbad; end
        always @(posedge ck[0]) begin
            a2 <= as;
            dt2 <= (fmt2 == 2'd1 || (fmt2 == 2'd0 && (lt1 ? lo2 : hi2))) ? f2 : {b2, 16'b0};
        end
        // W3 (t+7): range, write
        wire range_error = |a2[33:19];
        reg w_ok, w_bad, wv3; reg [18:0] w_a; reg [31:0] w_dt;
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin w_ok <= 1'b0; w_bad <= 1'b0; wv3 <= 1'b0; end
            else begin w_ok <= w2ok && !range_error; w_bad <= w2bad || (w2v && range_error); wv3 <= w2v; end
        always @(posedge ck[0]) begin w_a <= a2[18:0]; w_dt <= dt2; end
        wire vm_valid = w_ok && !gate;
        assign r_bad[g]  = w_bad;
        assign r_done[g] = rcv == {5'd0, exp_q} && !(v1 || v2 || v3 || v4 || v5 || v6 || w1v || w1bv || w2v || wv3);
        // ---- the VM write leaves from a flop (pair packer + crossing in dsfd_capt_x)
        reg [51:0] wq;
        always @(posedge ck[0] or negedge rs_n) if (!rs_n) wq <= 52'd0; else wq <= {w_dt, w_a, vm_valid};
        assign t_w[52 * g +: 52] = wq;
        assign hovf_now[g] = 1'b0;
    end endgenerate
    // ---- registered 16-root fault OR / done AND (two levels), outputs from flops
    reg [3:0] o1, a1; reg o2, a2r, hoq;
    always @(posedge ck[0] or negedge rst_h[0]) if (!rst_h[0]) hoq <= 1'b0; else hoq <= f_ho[0];
    integer q;
    always @(posedge ck[0] or negedge rst_h[0])
        if (!rst_h[0]) begin o1 <= 4'd0; a1 <= 4'd0; o2 <= 1'b0; a2r <= 1'b0; end
        else begin
            for (q = 0; q < 4; q = q + 1) begin
                o1[q] <= |(r_bad[4 * q +: 4] | hovf_now[4 * q +: 4]);
                a1[q] <= &r_done[4 * q +: 4];
            end
            o2 <= (|o1) | hoq; a2r <= &a1;
        end
    assign t_sb = {a2r, o2};
`ifndef SYNTHESIS
    initial if (NR != 16) $fatal(1, "dsfd_capt_g2: NR must be 16");
`endif
endmodule

// SAFE capture (owner SAFE-variant directive 2026-10-06): the 17 stream -> serial crossings of a group leave the root
// tile.  dsfd_capt_g2 = dsfd_capt_grp without the pair packers / ratio CDCs / status crossing (single clock); the
// crossings live in dsfd_capt_x, a small two-clock tile whose ck and ckv trees drive similar sink counts (write-side
// storage + packer vs read-side shadows + output flops), so the 278-ps ck -> ckv window and the coincident-edge hold
// are not eaten by a tree imbalance (capt_ctl r5: ser_clk 100 ps ahead of core_clk in a view where ck drove 4x the
// sinks).  Every dsfd_capt_x input is captured at its pin, every output leaves from a flop.  +2 write latency.
module dsfd_capt_x #(
    parameter integer NR = 16,
    parameter integer LD = 4
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rst,
    input  wire [0:0]        ckv,
    input  wire [0:0]        rsv,
    input  wire [NR*52-1:0]  f_w,            // per root {data32, addr19, v} (dsfd_capt_g2 t_w)
    output wire [NR*104-1:0] t_vm,           // per root {row1 {data32, addr19}, v1, row0 {data32, addr19}, v0} (serial)
    output wire [0:0]        t_ho,           // sticky hold-buffer overflow (stream)
    input  wire [63:0]       f_sn,           // status word (stream; used in the tile next to the control tile)
    output wire [63:0]       t_st            // status word (serial)
);
    reg [1:0] rst_s, rv_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rv_s <= 2'b00; else rv_s <= {rv_s[0], 1'b1};
    (* keep *) reg [1:0] rst_h, rsv_h;
    always @(posedge ck[0] or negedge rst_s[1]) if (!rst_s[1]) rst_h <= 2'b00; else rst_h <= 2'b11;
    always @(posedge ckv[0] or negedge rv_s[1]) if (!rv_s[1]) rsv_h <= 2'b00; else rsv_h <= 2'b11;
    reg [NR*52-1:0] fw;
    always @(posedge ck[0]) fw <= f_w;
    wire [NR-1:0] hovf;
    genvar g;
    generate for (g = 0; g < NR; g = g + 1) begin : g_r
        localparam integer H = g / (NR / 2);
        wire rs_n = rst_h[H];
        wire vm_valid = fw[52 * g];
        wire [50:0] din = fw[52 * g + 1 +: 51];
        reg [50:0] h [0:3];
        reg [1:0] hr, hw;
        reg [2:0] hc;
        reg ho;
        wire wr;
        wire [2:0] npop = (!wr || hc == 3'd0) ? 3'd0 : (hc == 3'd1) ? 3'd1 : 3'd2;
        wire crdy = (hc - npop) < 3'd4;
        always @(posedge ck[0] or negedge rs_n)
            if (!rs_n) begin hr <= 2'd0; hw <= 2'd0; hc <= 3'd0; ho <= 1'b0; end
            else begin
                hr <= hr + npop[1:0];
                if (vm_valid && crdy) begin hw <= hw + 2'd1; h[hw] <= din; end
                hc <= hc - npop + ((vm_valid && crdy) ? 3'd1 : 3'd0);
                if (vm_valid && !crdy) ho <= 1'b1;
            end
        assign hovf[g] = ho;
        wire cv; wire [102:0] cd;
        ot_ratio_cdc_fifo #(.W(103), .DEPTH(LD)) u_x (.wclk(ck[0]), .wrst_n(rs_n), .w_v(hc != 3'd0), .w_rdy(wr),
            .w_d({h[hr + 2'd1], hc >= 3'd2, h[hr]}), .rclk(ckv[0]), .rrst_n(rsv_h[H]), .r_v(cv), .r_rdy(1'b1),
            .r_d(cd), .w_live(), .r_live());
        reg [1:0] ov; reg [101:0] od;
        always @(posedge ckv[0] or negedge rsv_h[H]) if (!rsv_h[H]) ov <= 2'b00; else ov <= {cv & cd[51], cv};
        always @(posedge ckv[0]) begin od[50:0] <= cd[50:0]; od[101:51] <= cd[102:52]; end
        assign t_vm[104 * g +: 104] = {od[101:51], ov[1], od[50:0], ov[0]};
    end endgenerate
    reg hq;
    always @(posedge ck[0] or negedge rst_h[0]) if (!rst_h[0]) hq <= 1'b0; else hq <= |hovf;
    assign t_ho = hq;
    reg [63:0] snq;
    always @(posedge ck[0]) snq <= f_sn;
    wire s_v; wire [63:0] s_d;
    ot_ratio_cdc_fifo #(.W(64), .DEPTH(2)) u_s (.wclk(ck[0]), .wrst_n(rst_h[1]), .w_v(1'b1), .w_rdy(), .w_d(snq),
        .rclk(ckv[0]), .rrst_n(rsv_h[1]), .r_v(s_v), .r_rdy(1'b1), .r_d(s_d), .w_live(), .r_live());
    reg [63:0] stq;
    always @(posedge ckv[0] or negedge rsv_h[1]) if (!rsv_h[1]) stq <= 64'd0; else if (s_v) stq <= s_d;
    assign t_st = stq;
endmodule


module dsfd_capt_ctl #(
    parameter integer NT = 8
) (
    input  wire [0:0]             ck,
    input  wire [0:0]             rst,
    input  wire [162:0]           f_ctl,     // the gather's t_capture[6946:6784] = {live, busy, fault, f_vm[159:1], v}
    output wire [NT*`CAPT_KB-1:0] t_k,       // one constant bus per tile
    input  wire [NT*2-1:0]        f_sb,      // per tile {done, bad} (stream)
    output wire [63:0]            t_sn       // status word (stream, from a flop; crossed in dsfd_capt_grp)
);
    localparam integer KB = `CAPT_KB;
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // pin flops
    reg c0_v; reg [158:0] c0_d; reg g_fault, g_busy, g_live; reg [NT*2-1:0] stq;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) c0_v <= 1'b0; else c0_v <= f_ctl[0];
    always @(posedge ck[0]) begin c0_d <= f_ctl[159:1]; {g_live, g_busy, g_fault} <= f_ctl[162:160]; end
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) stq <= {NT*2{1'b0}}; else stq <= f_sb;
    // tile fault OR / done AND (registered)
    reg any_bad, all_done;
    integer t;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) begin any_bad <= 1'b0; all_done <= 1'b0; end
        else begin
            any_bad <= 1'b0; all_done <= 1'b1;
            for (t = 0; t < NT; t = t + 1) begin
                if (stq[2 * t]) any_bad <= 1'b1;
                if (!stq[2 * t + 1]) all_done <= 1'b0;
            end
        end
    wire [1:0]  kind     = c0_d[1:0];
    wire [46:0] identity = c0_d[48:2];
    wire [9:0]  phase_id = c0_d[58:49];
    wire [15:0] prows    = c0_d[157:142];
    wire [1:0]  fmt_in   = c0_d[123:122];
    reg act, stk, rq, drained, proto_fault;
    reg [4:0] hold;
    wire phase_v  = c0_v && kind == 2'd0;
    wire phase_ok = !act && !stk && !rq && prows != 16'd0 && fmt_in != 2'd3;
    wire go = phase_v && phase_ok;
    reg c_go; reg [29:0] c_ob, c_ops; reg [2:0] c_np; reg [1:0] c_fmt; reg [15:0] c_rs, c_rows; reg c_lo, c_hi;
    reg [46:0] h_id; reg [9:0] h_ph;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) begin
            act <= 1'b0; stk <= 1'b0; rq <= 1'b0; drained <= 1'b1; proto_fault <= 1'b0; hold <= 5'd0; c_go <= 1'b0;
            h_id <= 47'd0; h_ph <= 10'd0;
        end else begin
            c_go <= go;
            if (c0_v && kind == 2'd1) rq <= c0_d[158];
            if (phase_v && !phase_ok) proto_fault <= 1'b1;
            if (rq || any_bad) stk <= 1'b1;
            // holdoff covers go -> tile constants (t'+5) -> tile AND (2 levels) -> pins -> all_done
            if (go) begin act <= 1'b1; drained <= 1'b0; hold <= 5'd14; h_id <= identity; h_ph <= phase_id; end
            else begin
                if (hold != 5'd0) hold <= hold - 5'd1;
                if (act && hold == 5'd0 && all_done && !stk) begin act <= 1'b0; drained <= 1'b1; end
            end
        end
    always @(posedge ck[0]) if (go) begin
        c_ob <= c0_d[88:59]; c_ops <= c0_d[118:89]; c_np <= c0_d[121:119]; c_fmt <= fmt_in; c_rs <= c0_d[139:124];
        c_lo <= c0_d[140]; c_hi <= c0_d[141]; c_rows <= prows;
    end
    // per-tile constant bus, launched from flops at the pins
    reg [KB-1:0] kq [0:NT-1];
    genvar g;
    generate for (g = 0; g < NT; g = g + 1) begin : g_k
        wire [8:0] lo_d = {1'b0, c_rows[7:0]} - 9'(32 * g);
        wire [5:0] lo_t = lo_d[8] ? 6'd0 : (lo_d[7:0] > 8'd32) ? 6'd32 : lo_d[5:0];
        always @(posedge ck[0] or negedge rst_n)
            if (!rst_n) kq[g] <= {KB{1'b0}};
            else kq[g] <= {stk | rq, c_go, c_ob, c_ops, c_np, c_fmt, c_rs, c_rows[15:8], lo_t, c_lo, c_hi};
        assign t_k[KB * g +: KB] = kq[g];
    end endgenerate
    // status lane
    wire phase_live = act, phase_idle = !rq && !act && !stk, phase_drained = !rq && drained && !stk;
    wire cfault = stk || rq;
    reg [63:0] s_now;
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) s_now <= 64'd0;
        else s_now <= {g_busy, g_live, 1'b0, h_id, h_ph, cfault | proto_fault | g_fault, phase_drained, phase_idle, phase_live};
    assign t_sn = s_now;
endmodule

// the composition (bench / die generator reference): ctl + NT tiles, pin-to-pin hops
module ot_s81ph_cap_t #(
    parameter integer SAFE = 0,              // 1: dsfd_capt_g2 + dsfd_capt_x per group (crossings in their own tile)
    parameter integer NT = 8,
    parameter integer LD = 4
) (
    input  wire          ck, rst, ckv, rsv,      // raw die nets
    input  wire [6946:0] f_gather,
    output wire [13375:0] t_vm
);
    localparam integer KB = `CAPT_KB;
    wire [NT*KB-1:0] k;
    wire [NT*2-1:0]  st;
    wire [63:0] sn;
    wire [NT*64-1:0] stv;
    dsfd_capt_ctl #(.NT(NT)) u_ctl (.ck(ck), .rst(rst), .f_ctl(f_gather[6946:6784]), .t_k(k), .f_sb(st), .t_sn(sn));
    assign t_vm[13375:13312] = stv[64 * (NT / 2 - 1) +: 64];   // the tile left of the control tile
    genvar g;
    generate for (g = 0; g < NT; g = g + 1) begin : g_t
        if (SAFE != 0) begin : g_s
            wire [16*52-1:0] w; wire ho;
            dsfd_capt_g2 #(.NR(16)) u_g (.ck(ck), .rst(rst), .f_row(f_gather[53 * 16 * g +: 53 * 16]),
                .f_k(k[KB * g +: KB]), .t_w(w), .f_ho(ho), .t_sb(st[2 * g +: 2]));
            dsfd_capt_x #(.NR(16), .LD(LD)) u_x (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_w(w),
                .t_vm(t_vm[104 * 16 * g +: 104 * 16]), .t_ho(ho), .f_sn(g == NT / 2 - 1 ? sn : 64'd0),
                .t_st(stv[64 * g +: 64]));
        end else begin : g_n
        dsfd_capt_grp #(.NR(16), .LD(LD)) u_g (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv),
            .f_row(f_gather[53 * 16 * g +: 53 * 16]), .f_k(k[KB * g +: KB]), .t_vm(t_vm[104 * 16 * g +: 104 * 16]),
            .t_sb(st[2 * g +: 2]), .f_sn(g == NT / 2 - 1 ? sn : 64'd0), .t_st(stv[64 * g +: 64]));
        end
    end endgenerate
endmodule
