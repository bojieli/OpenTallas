`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX frame adapter ix2 (hbm-redesign-idx 2026-10-13): ONE VM read lane.  Lane LN owns every sector with
// sector mod 8 == LN of the three static frame ranges, walked in the order B (head weights, <= 1 sector a lane) ->
// C (keep_en: an id sector, then the value sector of the same entries at + C.stride, which is a multiple of 8 sectors
// and so on the same lane) -> A (64 query sectors).  The cross-lane order is static (lane = sector mod 8): there is no
// issue log and no shared pointer.  Two copies of the walker: the ISSUE walker names the next request, the LANDING
// walker names the kind of the next response (responses of one lane return in order).
// Landing: a 4-deep FIFO with a kind tag.  The lane issues without reserving landing room (the round trip is 8..24
// cycles; a reservation of 4 would cap the lane at 4 reads a round trip); a response that finds the FIFO full is
// dropped and the lane REWINDS: the issue walker is reloaded from the landing walker and the responses still in flight
// are skipped by count.  After a rewind the lane issues under a landing reservation until its FIFO has drained.
// Exact for any consumer stall; no rewind happens while the consumers keep up (A is issued every other cycle = the
// selector's one block a cycle).
// Consumers: B sector -> ab_d with b_v; C id sector held, then its value sector reduces the pair to 8 candidate
// flags (in range, id < 2^18, id[4:0] == rank[4:0], value != -inf = the reference's exact value test) and the pair
// leaves to the keep tile under KC credits only if a flag is set; A sectors leave on ab_d with a_v under QC = 2 credits
// of the query tile (its two sector slots of this lane; a_cr returns one).
// Every pin lands in a flop, every output leaves a flop; payload registers carry no reset.
// HARDENED ONCE, x8: the lane index is the pin strap lid (tied by the parent, registered here), not a parameter.
module ot_hgi_idx_ix2_lane #(
    parameter integer LQ = 10,
    parameter integer KC = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [2:0]   lid,            // lane index strap (constant)
    input  wire         start,          // frame start pulse (ct)
    input  wire         run,            // frame running (ct)
    input  wire         keep_en_i,
    input  wire [6:0]   rank_i,
    input  wire [17:0]  a_base_i, b_base_i, c_base_i, c_stride_i,
    input  wire [11:0]  c_n_i,
    // VM read lane
    output reg  [15:0]  wrq,
    input  wire         wrq_cr,
    input  wire [256:0] wrr,
    input  wire         rg_gnt,
    // query tile
    output reg  [255:0] ab_d,
    output reg          b_v,
    output reg          a_v,
    input  wire         a_cr,
    // keep tile
    output reg          c_v,
    output reg  [103:0] c_h,            // 8 x id[17:5]
    output reg  [7:0]   c_f,
    input  wire         c_cr,
    output reg          c_done,         // every C pair of this lane has been reduced and its matches set
    output reg          idle            // every read of this lane has landed and left
);
    localparam [1:0] P_B = 2'd0, P_C = 2'd1, P_A = 2'd2, P_E = 2'd3;
    localparam [1:0] K_B = 2'd0, K_CI = 2'd1, K_CV = 2'd2, K_A = 2'd3;
    reg [2:0] L3; always @(posedge clk) L3 <= lid;
    localparam integer CB = $clog2(LQ) + 1;
    integer p;
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    // ---------------------------------------------------------------- pin registers
    reg st_q, st_2, run_q, keep_en, rcr_q, rgnt_q, rr_v, tk_q, ccr_q;
    reg [4:0] rank; reg [17:0] pa, pb, pc, pcs; reg [11:0] pcn; reg [255:0] rr_d;
    always @(posedge clk or negedge rn)
        if (!rn) begin st_q <= 1'b0; st_2 <= 1'b0; run_q <= 1'b0; rcr_q <= 1'b0; rgnt_q <= 1'b0; rr_v <= 1'b0;
            tk_q <= 1'b0; ccr_q <= 1'b0; end
        else begin st_q <= start; st_2 <= st_q; run_q <= run; rcr_q <= wrq_cr; rgnt_q <= rg_gnt; rr_v <= wrr[256];
            tk_q <= a_cr; ccr_q <= c_cr; end
    always @(posedge clk) begin
        keep_en <= keep_en_i; rank <= rank_i[4:0]; pa <= a_base_i; pb <= b_base_i; pc <= c_base_i; pcs <= c_stride_i;
        pcn <= c_n_i; rr_d <= wrr[255:0];
    end
    // ---------------------------------------------------------------- frame constants of this lane (st_q -> st_2)
    wire [17:0] b_end = pb + 18'd31;
    wire [17:0] c_end = pc + {6'd0, pcn} - 18'd1;
    reg [11:0] hb0, hc0, ha0, cs_hi; reg [12:0] hcl; reg has_b, has_c, cfirst, clast; reg [2:0] c_lo, c_hi;
    wire [11:0] hb0_w = pb[17:6] + {11'd0, L3 < pb[5:3]};
    wire [11:0] hc0_w = pc[17:6] + {11'd0, L3 < pc[5:3]};
    wire [12:0] hcl_w = {1'b0, c_end[17:6]} - {12'd0, L3 > c_end[5:3]};
    always @(posedge clk) if (st_q) begin
        hb0 <= hb0_w; has_b <= {hb0_w, L3} <= b_end[17:3];
        hc0 <= hc0_w; hcl <= hcl_w; has_c <= keep_en && pcn != 12'd0 && !hcl_w[12] && hc0_w <= hcl_w[11:0];
        ha0 <= pa[17:6] + {11'd0, L3 < pa[5:3]};
        cs_hi <= pcs[17:6]; cfirst <= L3 == pc[5:3]; clast <= L3 == c_end[5:3]; c_lo <= pc[2:0]; c_hi <= c_end[2:0];
    end
    // ---------------------------------------------------------------- the walker (state {phase, cv, hi, n})
    localparam integer WW = 2 + 1 + 12 + 7;
    function automatic [WW-1:0] w_init(input reg dummy);
        w_init = has_b ? {P_B, 1'b0, hb0, 7'd0} : has_c ? {P_C, 1'b0, hc0, 7'd0} : {P_A, 1'b0, ha0, 7'd0};
    endfunction
    function automatic [WW-1:0] w_next(input [WW-1:0] s);
        reg [1:0] ph; reg cv; reg [11:0] hi; reg [6:0] n;
        begin
            {ph, cv, hi, n} = s;
            case (ph)
                P_B: w_next = has_c ? {P_C, 1'b0, hc0, 7'd0} : {P_A, 1'b0, ha0, 7'd0};
                P_C: w_next = !cv ? {P_C, 1'b1, hi, 7'd0} : (hi == hcl[11:0]) ? {P_A, 1'b0, ha0, 7'd0} : {P_C, 1'b0, hi + 12'd1, 7'd0};
                P_A: w_next = (n == 7'd63) ? {P_E, 1'b0, hi, 7'd0} : {P_A, 1'b0, hi + 12'd1, n + 7'd1};
                default: w_next = s;
            endcase
        end
    endfunction
    reg [WW-1:0] wi, wl;                    // issue walker, landing walker
    wire [1:0] wi_ph = wi[WW-1 -: 2]; wire wi_cv = wi[WW-3]; wire [11:0] wi_hi = wi[18:7];
    wire [1:0] wl_ph = wl[WW-1 -: 2]; wire wl_cv = wl[WW-3]; wire [11:0] wl_hi = wl[18:7];
    wire [11:0] wi_sec = (wi_ph == P_C && wi_cv) ? wi_hi + cs_hi : wi_hi;
    wire [1:0] wl_kind = (wl_ph == P_B) ? K_B : (wl_ph == P_A) ? K_A : wl_cv ? K_CV : K_CI;
    // ---------------------------------------------------------------- landing FIFO (4 deep, kind tag)
    reg [255:0] lm [0:3]; reg [3:0] lt [0:3]; reg [1:0] lwp, lrp; reg [2:0] lcnt;
    reg armed, caut, pause, a_tgl;
    reg [CB-1:0] cred; reg [6:0] infl, skip; reg [1:0] acred;
    reg hold_v; reg [103:0] hold_h; reg [7:0] hold_f; reg [2:0] kcred;
    wire land = rr_v && skip == 7'd0 && armed;
    wire ovf  = land && lcnt == 3'd4;
    wire acc  = land && lcnt != 3'd4;
    wire [255:0] hd = lm[lrp]; wire [3:0] ht = lt[lrp];
    wire hv = lcnt != 3'd0 && armed;
    wire [1:0] hk = ht[3:2];
    wire pop_b  = hv && hk == K_B;
    wire pop_ci = hv && hk == K_CI && !hold_v;
    reg [7:0] vf;
    always @* for (p = 0; p < 8; p = p + 1) vf[p] = hold_f[p] && hd[p*32 +: 32] != 32'hFF80_0000;
    wire cv_any = |vf;
    wire pop_cv = hv && hk == K_CV && hold_v && (!cv_any || kcred != 3'd0);
    wire pop_a  = hv && hk == K_A && run_q && (acred != 2'd0 || tk_q);
    wire pop = pop_b || pop_ci || pop_cv || pop_a;
    wire room = !caut || ({4'd0, lcnt} + infl) < 7'd4;
    wire iss = armed && run_q && !pause && wi_ph != P_E && cred != '0 && rgnt_q && !ovf && room && !(wi_ph == P_A && a_tgl);
    always @(posedge clk) begin
        if (acc) begin lm[lwp] <= rr_d; lt[lwp] <= {wl_kind, cfirst && wl_hi == hc0, clast && wl_hi == hcl[11:0]}; end
        if (pop_b || pop_a) ab_d <= hd;
        if (pop_ci)
            for (p = 0; p < 8; p = p + 1) begin
                hold_h[p*13 +: 13] <= hd[p*32 + 5 +: 13];
                hold_f[p] <= hd[p*32 + 18 +: 14] == 14'd0 && hd[p*32 +: 5] == rank &&
                             !(ht[1] && p[2:0] < c_lo) && !(ht[0] && p[2:0] > c_hi);
            end
        if (pop_cv) begin c_h <= hold_h; c_f <= vf; end
        if (iss) wrq[14:0] <= {wi_sec, L3[2], L3[1:0]};
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin
            armed <= 1'b0; caut <= 1'b0; pause <= 1'b0; a_tgl <= 1'b0; cred <= CB'(LQ); infl <= 7'd0; skip <= 7'd0; acred <= 2'd2;
            hold_v <= 1'b0; kcred <= 3'(KC); lwp <= 2'd0; lrp <= 2'd0; lcnt <= 3'd0; wi <= '0; wl <= '0;
            wrq[15] <= 1'b0; b_v <= 1'b0; a_v <= 1'b0; c_v <= 1'b0; c_done <= 1'b0; idle <= 1'b0;
        end else begin
            wrq[15] <= iss; b_v <= pop_b; a_v <= pop_a; c_v <= pop_cv && cv_any;
            cred <= cred + CB'(rcr_q) - CB'(iss);
            infl <= infl + 7'(iss) - 7'(rr_v);
            kcred <= kcred + 3'(ccr_q) - 3'(pop_cv && cv_any);
            if (rr_v && skip != 7'd0) skip <= skip - 7'd1;
            if (acc) begin lwp <= lwp + 2'd1; wl <= w_next(wl); end
            if (pop) lrp <= lrp + 2'd1;
            lcnt <= lcnt + 3'(acc) - 3'(pop);
            acred <= acred + 2'(tk_q) - 2'(pop_a);
            if (pop_ci) hold_v <= 1'b1; else if (pop_cv) hold_v <= 1'b0;
            if (iss) begin wi <= w_next(wi); a_tgl <= wi_ph == P_A; end else a_tgl <= 1'b0;
            if (ovf) begin wi <= wl; skip <= infl - 7'd1; pause <= 1'b1; caut <= 1'b1; end
            else if (lcnt <= 3'd1) pause <= 1'b0;
            if (lcnt == 3'd0 && !ovf) caut <= 1'b0;         // the consumer has caught up: full rate again
            c_done <= armed && run_q && (wl_ph == P_A || wl_ph == P_E) && !hold_v && !(hv && hk != K_A) && kcred == 3'(KC);
            idle <= armed && wl_ph == P_E && lcnt == 3'd0;
            if (!run_q) begin armed <= 1'b0; end
            if (st_q) begin                                  // frame start: stale responses of an aborted frame are skipped
                armed <= 1'b0; skip <= infl - 7'(rr_v); lwp <= 2'd0; lrp <= 2'd0; lcnt <= 3'd0; acred <= 2'd2;
                hold_v <= 1'b0; kcred <= 3'(KC); caut <= 1'b0; pause <= 1'b0; a_tgl <= 1'b0; c_done <= 1'b0; idle <= 1'b0;
            end
            if (st_2) begin wi <= w_init(1'b0); wl <= w_init(1'b0); armed <= 1'b1; end
        end
endmodule
`default_nettype wire
