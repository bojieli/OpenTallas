`timescale 1ns/1ps
`default_nettype none
// ix2 KEEP walk, one lane quad (hbm-redesign-idx 2026-10-13).  Per lane 8 candidates a pair: block id b = 32 h + l
// (h = id[17:5] < 2^13; the lane tile already tested l == rank[4:0], the range, id < 2^18 and the value).  Here:
// h div 3 and h mod 3 by a base-4 digit recurrence (q = (4 r + d) div 3, r' = (4 r + d) mod 3; no multiplier, no
// divider; 7 digits in 4 free-running registered stages 2 + 2 + 2 + 1), then owned = (h mod 3 == rank[6:5]) and
// h div 3 < 1,368 (the reference's K2 / K3 mapping; bit position = h div 3).  A pair with a match waits in a 4-deep
// per-lane FIFO (the lane's KC credits = its depth) and its matches leave one a cycle (4-way rotating priority) into
// one registered (valid, ordinal) port to the keep-set tile; the lane credit returns when the pair is finished.
module ot_hgi_idx_ix2_kp #(
    parameter integer MUT = 0       // 3: bench mutant, the digit recurrence returns remainder 2 for 4r + d = 7
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire [6:0]    rank_i,
    input  wire [3:0]    c_v,
    input  wire [415:0]  c_h,
    input  wire [31:0]   c_f,
    output reg  [3:0]    c_cr,
    output reg           ks_v,
    output reg  [10:0]   ks_ord
);
    function automatic [3:0] dig(input [1:0] r, input [1:0] d);     // {q, r'} of (4 r + d) / 3, r <= 2
        reg [3:0] x;
        begin
            x = {r, d};
            case (x)
                4'd0: dig = {2'd0, 2'd0};  4'd1: dig = {2'd0, 2'd1};  4'd2: dig = {2'd0, 2'd2};  4'd3: dig = {2'd1, 2'd0};
                4'd4: dig = {2'd1, 2'd1};  4'd5: dig = {2'd1, 2'd2};  4'd6: dig = {2'd2, 2'd0};
                4'd7: dig = (MUT == 3) ? {2'd2, 2'd2} : {2'd2, 2'd1};
                4'd8: dig = {2'd2, 2'd2};  4'd9: dig = {2'd3, 2'd0};  4'd10: dig = {2'd3, 2'd1}; default: dig = {2'd3, 2'd2};
            endcase
        end
    endfunction
    function automatic [5:0] dig2(input [1:0] r, input [3:0] d);    // two digits: {q1, q0, r'}
        reg [3:0] a, b;
        begin a = dig(r, d[3:2]); b = dig(a[1:0], d[1:0]); dig2 = {a[3:2], b[3:2], b[1:0]}; end
    endfunction
    integer l, p;
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    reg st_q; reg [6:0] rank;
    reg [3:0] i_v; reg [415:0] i_h; reg [31:0] i_f;
    always @(posedge clk or negedge rn) if (!rn) begin st_q <= 1'b0; i_v <= 4'd0; end else begin st_q <= start; i_v <= c_v; end
    always @(posedge clk) begin rank <= rank_i; i_h <= c_h; i_f <= c_f; end
    // ---------------------------------------------------------------- divide pipeline (32 candidates, free-running)
    reg [3:0] v1, v2, v3, v4;
    reg [31:0] f1, f2, f3, m4;
    reg [3:0]  q1 [0:31]; reg [1:0] r1 [0:31]; reg [9:0] h1 [0:31];
    reg [7:0]  q2 [0:31]; reg [1:0] r2 [0:31]; reg [5:0] h2 [0:31];
    reg [11:0] q3 [0:31]; reg [1:0] r3 [0:31]; reg [1:0] h3 [0:31];
    reg [10:0] o4 [0:31];
    reg [5:0] t; reg [3:0] u; reg [12:0] hh; reg [13:0] qq;
    always @(posedge clk or negedge rn)
        if (!rn) begin v1 <= 4'd0; v2 <= 4'd0; v3 <= 4'd0; v4 <= 4'd0; end
        else if (st_q) begin v1 <= 4'd0; v2 <= 4'd0; v3 <= 4'd0; v4 <= 4'd0; end
        else begin v1 <= i_v; v2 <= v1; v3 <= v2; v4 <= v3; end
    always @(posedge clk) begin
        f1 <= i_f; f2 <= f1; f3 <= f2;
        for (p = 0; p < 32; p = p + 1) begin
            hh = i_h[p*13 +: 13];
            t = dig2(2'd0, {1'b0, hh[12:10]});   q1[p] <= t[5:2]; r1[p] <= t[1:0]; h1[p] <= hh[9:0];
            t = dig2(r1[p], h1[p][9:6]);         q2[p] <= {q1[p], t[5:2]}; r2[p] <= t[1:0]; h2[p] <= h1[p][5:0];
            t = dig2(r2[p], h2[p][5:2]);         q3[p] <= {q2[p], t[5:2]}; r3[p] <= t[1:0]; h3[p] <= h2[p][1:0];
            u = dig(r3[p], h3[p]);               qq = {q3[p], u[3:2]};
            m4[p] <= f3[p] && u[1:0] == rank[6:5] && qq < 14'd1368;
            o4[p] <= qq[10:0];
        end
    end
    // ---------------------------------------------------------------- per-lane pair FIFO (pairs with a match), drain
    reg [95:0] fm [0:15]; reg [1:0] fw [0:3], fr [0:3]; reg [2:0] fc [0:3];       // entry: lane * 4 + slot
    reg [3:0] w_v; reg [7:0] w_m [0:3]; reg [87:0] w_o [0:3];
    reg [1:0] rr; reg [2:0] crp [0:3];             // credits owed to the lane (two can fall due in one cycle)
    reg [3:0] any4, push, wld, fin; reg [2:0] pk [0:3]; reg [3:0] pk_v; reg [7:0] w_left [0:3]; reg [95:0] e; reg [1:0] gl; reg g_v; reg [1:0] cl;
    always @* for (l = 0; l < 4; l = l + 1) begin
        any4[l] = |m4[l*8 +: 8];
        push[l] = v4[l] && any4[l];
        pk[l] = 3'd0; pk_v[l] = 1'b0;
        for (p = 7; p >= 0; p = p - 1) if (w_m[l][p]) begin pk[l] = 3'(p); pk_v[l] = 1'b1; end
        w_left[l] = w_m[l] & ~(8'd1 << pk[l]);
    end
    always @* begin
        g_v = 1'b0; gl = rr;
        for (l = 3; l >= 0; l = l - 1) begin cl = rr + 2'(l); if (w_v[cl]) begin g_v = 1'b1; gl = cl; end end
        for (l = 0; l < 4; l = l + 1) begin
            fin[l] = w_v[l] && g_v && gl == 2'(l) && w_left[l] == 8'd0;
            wld[l] = fc[l] != 3'd0 && (!w_v[l] || fin[l]);
        end
    end
    always @(posedge clk) begin
        for (l = 0; l < 4; l = l + 1) begin
            if (push[l]) begin
                for (p = 0; p < 8; p = p + 1) e[8 + p*11 +: 11] = o4[l*8 + p];
                e[7:0] = m4[l*8 +: 8];
                fm[l*4 + {30'd0, fw[l]}] <= e;
            end
            if (wld[l]) begin w_m[l] <= fm[l*4 + {30'd0, fr[l]}][7:0]; w_o[l] <= fm[l*4 + {30'd0, fr[l]}][95:8]; end
            else if (g_v && gl == 2'(l)) w_m[l] <= w_left[l];
        end
        ks_ord <= w_o[gl][pk[gl]*11 +: 11];
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin
            rr <= 2'd0; w_v <= 4'd0; ks_v <= 1'b0; c_cr <= 4'd0;
            for (l = 0; l < 4; l = l + 1) begin fw[l] <= 2'd0; fr[l] <= 2'd0; fc[l] <= 3'd0; crp[l] <= 3'd0; end
        end else if (st_q) begin
            w_v <= 4'd0; ks_v <= 1'b0; c_cr <= 4'd0;
            for (l = 0; l < 4; l = l + 1) begin fw[l] <= 2'd0; fr[l] <= 2'd0; fc[l] <= 3'd0; crp[l] <= 3'd0; end
        end else begin
            rr <= rr + 2'd1;
            ks_v <= g_v;
            for (l = 0; l < 4; l = l + 1) begin
                c_cr[l] <= crp[l] != 3'd0;
                crp[l] <= crp[l] + 3'(v4[l] && !any4[l]) + 3'(fin[l]) - 3'(crp[l] != 3'd0);
                if (push[l]) fw[l] <= fw[l] + 2'd1;
                if (wld[l]) fr[l] <= fr[l] + 2'd1;
                fc[l] <= fc[l] + 3'(push[l]) - 3'(wld[l]);
                if (wld[l]) w_v[l] <= 1'b1; else if (fin[l]) w_v[l] <= 1'b0;
            end
        end
endmodule

// ix2 keep set (hbm-redesign-idx 2026-10-13): two registered (valid, ordinal) ports, a registered two-part one-hot
// predecode a port, the four 342-bit quarter bitmaps (bit = ordinal, quarter = ordinal div 342), and the kin beats:
// sent in quarter order, 4 cycles apart, once every lane has reported its C walk done for 8 cycles in a row.
module ot_hgi_idx_ix2_ks (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire          run,
    input  wire          keep_en_i,
    input  wire [1:0]    ks_v,
    input  wire [21:0]   ks_ord,
    input  wire [7:0]    c_done,
    output reg  [344:0]  kin,
    output reg           kin_sent
);
    integer b, x;
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    reg st_q, run_q, keep_en; reg [1:0] i_v; reg [21:0] i_o; reg [7:0] cd_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin st_q <= 1'b0; run_q <= 1'b0; i_v <= 2'd0; cd_q <= 8'd0; end
        else begin st_q <= start; run_q <= run; i_v <= ks_v; cd_q <= c_done; end
    always @(posedge clk) begin keep_en <= keep_en_i; i_o <= ks_ord; end
    reg [21:0] dh [0:1]; reg [63:0] dl [0:1];
    reg [1367:0] keep;
    reg [3:0] dcnt; reg [1:0] kq; reg [1:0] kgap; reg all_q;
    always @(posedge clk) begin
        for (x = 0; x < 2; x = x + 1) begin
            for (b = 0; b < 22; b = b + 1) dh[x][b] <= i_v[x] && i_o[x*11 + 6 +: 5] == 5'(b);
            for (b = 0; b < 64; b = b + 1) dl[x][b] <= i_o[x*11 +: 6] == 6'(b);
        end
        if (st_q) keep <= '0;
        else for (b = 0; b < 1368; b = b + 1)
            if ((dh[0][b / 64] && dl[0][b % 64]) || (dh[1][b / 64] && dl[1][b % 64])) keep[b] <= 1'b1;
        if (kgap == 2'd0) kin[344:1] <= {keep[kq*342 +: 342], kq};
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin dcnt <= 4'd0; kq <= 2'd0; kgap <= 2'd0; kin_sent <= 1'b0; kin[0] <= 1'b0; all_q <= 1'b0; end
        else begin
            kin[0] <= 1'b0;
            all_q <= &cd_q;
            if (st_q || !run_q) begin dcnt <= 4'd0; kq <= 2'd0; kgap <= 2'd0; if (st_q) kin_sent <= 1'b0; end
            else if (keep_en && !kin_sent) begin
                if (!all_q) dcnt <= 4'd0;
                else if (dcnt != 4'd8) dcnt <= dcnt + 4'd1;
                else begin
                    kgap <= kgap + 2'd1;
                    if (kgap == 2'd0) begin kin[0] <= 1'b1; if (kq == 2'd3) kin_sent <= 1'b1; else kq <= kq + 2'd1; end
                end
            end
        end
endmodule
`default_nettype wire
