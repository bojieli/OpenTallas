`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT-UNITS-IDX 2026-10-19: IDX.UNION (HGI-1R op 5, CMTP spec results/arch/hbm_next_1019/cmtp/isa_rows.md R6), the
// verify expert-union record. NEW master beside the IDX.TOPK row engine (same VM faces: one read group sector an edge,
// the idx packet client cq/cr with the topk tag 0x0244 and a 12-edge ack), so the compiler calendar is built the same way.
//   A = N rows of k U32 expert ids at a_base + r a_str, each row strictly ascending (IDX.TOPK order 1), ids < E;
//   O = the union ids ascending (U words at o_base, 8-aligned; words >= U untouched);
//   D[0] = U (one word at d_base);
//   R = one 32-word row table per union expert at r_base + 32 i (r_base 32-aligned): word 0 = c_u, words 1..c_u =
//       {rho[3:0], e[15:8]} in ascending rho, e = rho x K + kappa, kappa = rank of u in row rho (golden:
//       tools/hbm_next/isa_rows.idx_union / entry_word).
// STATIC: the write count is data-independent: T = N k table slots (U <= N k), each TS = ceil((1 + N) / 8) sector
// writes (slot i >= U writes byte mask 0), one O sector after every 8 slots (and after the last), then D: W = T TS +
// ceil(T / 8) + 1 writes. The idx packet client has 4 sequence numbers and a write's ack frees its number at W + 10,
// so writes go in groups of 4 every 10 edges (write x at W0 + 10 (x div 4) + x mod 4). Union ids come from a 384-b bitmap, popped lowest-first one per slot (ascending = the
// golden's G15 slot order, gate E2); each popped id is matched against the N x k captured ids (rho, kappa).
// Timeline (G = the edge that samples go; tools/hbm_next/hnx_idx_union_vectors.py replays it edge by edge):
//   G+1 CHK (illegal descriptor -> fault, no traffic); G+2.. RD: one sector an edge, rows back to back (row r: sectors
//   a_r >> 3 .. (a_r + k - 1) >> 3); FULL 12 edges after the last read edge -> ORD (range / strict-ascending check) ->
//   PRE 3 edges (pop / match / pack pipeline fill) -> W write edges -> NEXT -> done / fault ACK edges after NEXT.
// Faults: illegal descriptor at G+1; an id >= E or a row not strictly ascending: every write keeps its slot with byte
// mask 0, fault at the done edge; read / ack schedule mismatch -> fault.
// MUT (bench): 1 pop highest first (descending union = E2 order violated), 2 kappa dropped (e = rho K), 3 row stride
//              dropped (every row reads row 0), 4 U counts every slot (D[0] = N k instead of the union size).
module ot_hnx_idx_union_static #(
    parameter integer MUT = 0,
    parameter integer EMAX = 384,
    parameter integer ACK = 12
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    sid,
    input  wire          go,
    input  wire [3:0]    k,            // ids a row (A.n), 1..8
    input  wire [4:0]    n_rows,       // N (A.m), 1..16
    input  wire [9:0]    experts,      // E (imm_a), 1..EMAX
    input  wire [3:0]    pitch_k,      // K (imm_b), k..15
    input  wire          a_mirror,
    input  wire [17:0]   a_base,
    input  wire [17:0]   a_str,
    input  wire [17:0]   o_base,
    input  wire [17:0]   d_base,
    input  wire [17:0]   r_base,
    output reg  [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output reg  [337:0]  cq,
    output reg  [1:0]    cq_seq,
    input  wire [273:0]  cr,
    output reg           busy,
    output reg           done,
    output reg           fault,
    output wire          union_v,
    output wire [9:0]    union_count
);
    assign union_v = done;
    assign union_count = ucount;
    localparam [3:0] S_IDLE = 0, S_CHK = 1, S_RD = 2, S_WAITC = 3, S_ORD = 4, S_PRE = 5, S_WT = 6, S_NEXT = 7, S_END = 8;
    localparam [1:0] P_TAB = 0, P_O = 1, P_D = 2;
    integer l, r, j, w;
    // ------------------------------------------------------------ descriptor (sampled with go)
    reg [3:0] k_q, kk_q; reg [4:0] n_q; reg [9:0] e_q; reg am_q;
    reg [17:0] a_base_q, a_str_q, o_base_q, d_base_q, r_base_q;
    always @(posedge clk) if (go && !busy) begin
        k_q <= k; n_q <= n_rows; e_q <= experts; kk_q <= pitch_k; am_q <= a_mirror;
        a_base_q <= a_base; a_str_q <= a_str; o_base_q <= o_base; d_base_q <= d_base; r_base_q <= r_base;
    end
    wire legal = k >= 4'd1 && k <= 4'd8 && n_rows >= 5'd1 && n_rows <= 5'd16 && experts >= 10'd1 && experts <= 10'(EMAX) &&
                 pitch_k >= k && (a_mirror ? a_base[17:16] == 2'd0 : a_base[17:16] == sid) &&
                 o_base[17:16] == sid && o_base[2:0] == 3'd0 && d_base[17:16] == sid && r_base[17:16] == sid && r_base[4:0] == 5'd0;
    reg legal_q;
    always @(posedge clk) if (go && !busy) legal_q <= legal;
    // derived (stable after CHK)
    wire [1:0] ts = (n_q <= 5'd7) ? 2'd1 : 2'd2 + ((n_q >= 5'd16) ? 2'd1 : 2'd0);     // ceil((1 + N) / 8)
    wire [7:0] tslots = 8'(n_q) * 8'(k_q);                                               // T = N k
    // ------------------------------------------------------------ reader: one sector an edge, rows back to back
    reg [3:0] st; reg [1:0] ph;
    reg [4:0] rd_row; reg [17:0] c_rb; reg [14:0] i_sec; reg i_s;
    wire [14:0] row_last_sec = 15'((c_rb + 18'(k_q) - 18'd1) >> 3);
    wire rd_now = st == S_RD;
    wire rd_row_last = i_sec == row_last_sec;
    wire rd_last = rd_now && rd_row_last && rd_row + 5'd1 == n_q;
    wire rsid_bad = !am_q && i_sec[14:13] != sid;
    // read pipeline info {v, vmbank3, row4, s1, off3}
    reg [11:0] dp [0:8];
    wire [11:0] di = dp[7];
    reg cap_v, cap_s; reg [3:0] cap_row; reg [2:0] cap_off; reg [255:0] cap_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vm_rq <= 136'd0; cap_v <= 1'b0;
            for (integer d = 0; d < 9; d = d + 1) dp[d] <= 12'd0;
        end else begin
            vm_rq <= 136'd0;
            for (integer d = 1; d < 9; d = d + 1) dp[d] <= dp[d-1];
            dp[0] <= 12'd0;
            if (rd_now && !rsid_bad) begin
                vm_rq[17*i_sec[2:0] +: 17] <= {1'b1, am_q, i_sec};
                dp[0] <= {1'b1, i_sec[2:0], rd_row[3:0], i_s, c_rb[2:0]};
            end
            cap_v <= di[11];
        end
    end
    always @(posedge clk) begin
        cap_d <= vm_rr[257*di[10:8] +: 256];
        {cap_row, cap_s, cap_off} <= di[7:0];
    end
    reg rd_bad;
    always @* begin
        rd_bad = 1'b0;
        for (l = 0; l < 8; l = l + 1)
            if (vm_rr[257*l+256] != (di[11] && di[10:8] == 3'(l))) rd_bad = 1'b1;
    end
    // ------------------------------------------------------------ capture: ids[r][j], bitmap, range flag
    reg [8:0] ids [0:15][0:7];
    reg [EMAX-1:0] bmp;
    reg rng_bad;
    reg [4:0] cj [0:7];
    always @* for (l = 0; l < 8; l = l + 1) cj[l] = 5'(8 * int'(cap_s) + l) - 5'(cap_off);
    // ------------------------------------------------------------ pop / match / pack pipeline (tick = advance one slot)
    reg tick;
    reg p0_v; reg [8:0] p0_u;
    reg p1_v; reg [8:0] p1_u; reg [15:0] p1_hit; reg [2:0] p1_kap [0:15];
    reg p2_v; reg [8:0] p2_u; reg [4:0] p2_c; reg [31:0] p2_w [0:23];
    reg pop_v; reg [8:0] pop_u;
    always @* begin                                        // lowest (MUT 1: highest) set bit of the bitmap
        pop_v = |bmp; pop_u = 9'd0;
        if (MUT == 1) begin for (l = 0; l < EMAX; l = l + 1) if (bmp[l]) pop_u = 9'(l); end
        else begin for (l = EMAX - 1; l >= 0; l = l - 1) if (bmp[l]) pop_u = 9'(l); end
    end
    reg [15:0] m_hit; reg [2:0] m_kap [0:15];
    always @* for (r = 0; r < 16; r = r + 1) begin
        m_hit[r] = 1'b0; m_kap[r] = 3'd0;
        for (j = 0; j < 8; j = j + 1)
            if (r < int'(n_q) && j < int'(k_q) && ids[r][j] == p0_u) begin m_hit[r] = p0_v; m_kap[r] = 3'(j); end
    end
    reg [4:0] pre [0:16]; reg [31:0] pw [0:23];
    always @* begin
        pre[0] = 5'd0;
        for (r = 0; r < 16; r = r + 1) pre[r+1] = pre[r] + {4'd0, p1_hit[r]};
        for (w = 0; w < 24; w = w + 1) pw[w] = 32'd0;
        pw[0] = {27'd0, pre[16]};
        for (w = 1; w < 17; w = w + 1)
            for (r = 0; r < 16; r = r + 1)
                if (p1_hit[r] && pre[r] == 5'(w - 1))
                    pw[w] = pw[w] | {16'd0, 8'(r * int'(kk_q) + ((MUT == 2) ? 0 : int'(p1_kap[r]))), 4'd0, 4'(r)};
    end
    // ------------------------------------------------------------ writer
    reg [7:0] slot; reg [1:0] sct; reg [4:0] ogrp; reg [255:0] obuf; reg [7:0] omask; reg [9:0] ucount;
    reg flt, dbad; reg [3:0] cnt; reg [1:0] wi; reg [2:0] gap;
    function automatic [31:0] bmask(input [7:0] wm);
        for (integer q = 0; q < 8; q = q + 1) bmask[4*q +: 4] = {4{wm[q]}};
    endfunction
    // table sector sct of the current slot: words 8 sct .. 8 sct + 7 of the 32-word row, valid words 0..c_u
    reg [255:0] t_data; reg [7:0] t_wm;
    always @* begin
        for (l = 0; l < 8; l = l + 1) begin
            t_data[32*l +: 32] = p2_w[8*int'(sct) + l];
            t_wm[l] = p2_v && (8 * int'(sct) + l) <= int'(p2_c);
        end
    end
    wire [14:0] t_sec = 15'((r_base_q >> 3) + 18'(4 * int'(slot)) + 18'(sct));
    wire [14:0] o_sec = 15'((o_base_q >> 3) + 18'(ogrp));
    wire [14:0] d_sec = d_base_q[17:3];
    wire last_slot = slot + 8'd1 == tslots;
    reg [2:0] ap [0:ACK];
    reg cr_v; reg [15:0] cr_tag; reg cr_we;
    wire [2:0] ax = ap[ACK-1];
    wire ack_bad = cr_v != ax[2] || (ax[2] && (cr_tag != {14'h0244, ax[1:0]} || !cr_we));
    reg wr_now;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cr_v <= 1'b0;
            for (integer d = 0; d <= ACK; d = d + 1) ap[d] <= 3'd0;
        end else begin
            cr_v <= cr[273];
            for (integer d = 1; d <= ACK; d = d + 1) ap[d] <= ap[d-1];
            ap[0] <= {wr_now, cq_seq};
        end
    always @(posedge clk) begin cr_tag <= cr[272:257]; cr_we <= cr[256]; end
    // FULL token: last read edge + 12
    reg [11:0] ft_v; reg full;
    wire wkill = flt || dbad;
    // ------------------------------------------------------------ datapath registers (no reset)
    always @(posedge clk) begin
        if (st == S_CHK) bmp <= {EMAX{1'b0}};
        if (cap_v)
            for (l = 0; l < 8; l = l + 1)
                if (cj[l] < 5'(k_q) && !cj[l][4]) begin
                    ids[cap_row][cj[l][2:0]] <= cap_d[32*l +: 9];
                    if (cap_d[32*l +: 32] < 32'(e_q)) bmp[cap_d[32*l +: 9]] <= 1'b1;
                end
        if (tick) begin
            if (pop_v) bmp[pop_u] <= 1'b0;
            p0_v <= pop_v; p0_u <= pop_u;
            p1_v <= p0_v; p1_u <= p0_u; p1_hit <= m_hit; for (r = 0; r < 16; r = r + 1) p1_kap[r] <= m_kap[r];
            p2_v <= p1_v; p2_u <= p1_u; p2_c <= pre[16]; for (w = 0; w < 24; w = w + 1) p2_w[w] <= pw[w];
        end
    end
    // ------------------------------------------------------------ control
    always @* tick = st == S_PRE || (st == S_WT && gap == 3'd0 && ph == P_TAB && sct + 2'd1 == ts);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; ph <= P_TAB; busy <= 1'b0; done <= 1'b0; fault <= 1'b0; flt <= 1'b0; dbad <= 1'b0; rng_bad <= 1'b0;
            cq <= 338'd0; cq_seq <= 2'd0; wr_now <= 1'b0; wi <= 2'd0; gap <= 3'd0; cnt <= 4'd0; ft_v <= 12'd0; full <= 1'b0;
            slot <= 8'd0; sct <= 2'd0; ogrp <= 5'd0; obuf <= 256'd0; omask <= 8'd0; ucount <= 10'd0;
            rd_row <= 5'd0; c_rb <= 18'd0; i_sec <= 15'd0; i_s <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cq[337] <= 1'b0; wr_now <= 1'b0;
            if (busy && (rd_bad || ack_bad) && st != S_CHK) flt <= 1'b1;
            if (rd_now && rsid_bad) flt <= 1'b1;
            if (cap_v)
                for (l = 0; l < 8; l = l + 1)
                    if (cj[l] < 5'(k_q) && !cj[l][4] && cap_d[32*l +: 32] >= 32'(e_q)) rng_bad <= 1'b1;
            ft_v <= {ft_v[10:0], rd_last};
            if (ft_v[11]) full <= 1'b1;
            case (st)
                S_IDLE: if (go) begin busy <= 1'b1; st <= S_CHK; end
                S_CHK: begin                                              // G+1
                    flt <= 1'b0; dbad <= 1'b0; rng_bad <= 1'b0; full <= 1'b0; ft_v <= 12'd0;
                    rd_row <= 5'd0; c_rb <= a_base_q; i_sec <= a_base_q[17:3]; i_s <= 1'b0;
                    slot <= 8'd0; sct <= 2'd0; ogrp <= 5'd0; obuf <= 256'd0; omask <= 8'd0; ucount <= 10'd0; ph <= P_TAB; wi <= 2'd0; gap <= 3'd0;
                    if (!legal_q) begin fault <= 1'b1; busy <= 1'b0; st <= S_IDLE; end
                    else st <= S_RD;
                end
                S_RD: begin                                               // one sector an edge
                    if (rd_row_last) begin
                        if (rd_last) st <= S_WAITC;
                        else begin
                            rd_row <= rd_row + 5'd1; i_s <= 1'b0;
                            if (MUT != 3) begin c_rb <= c_rb + a_str_q; i_sec <= 15'((c_rb + a_str_q) >> 3); end
                            else i_sec <= c_rb[17:3];
                        end
                    end else begin i_sec <= i_sec + 15'd1; i_s <= 1'b1; end
                end
                S_WAITC: if (full) begin full <= 1'b0; st <= S_ORD; end
                S_ORD: begin                                              // range + strict ascending, then fill 3 edges
                    dbad <= rng_bad;
                    for (r = 0; r < 16; r = r + 1)
                        for (j = 0; j < 7; j = j + 1)
                            if (r < int'(n_q) && j + 1 < int'(k_q) && ids[r][j] >= ids[r][j+1]) dbad <= 1'b1;
                    cnt <= 4'd2; st <= S_PRE;
                end
                S_PRE: if (cnt == 4'd0) st <= S_WT; else cnt <= cnt - 4'd1;
                S_WT: if (gap != 3'd0) gap <= gap - 3'd1;          // seq reuse: write x + 4 >= 10 edges after write x
                else begin
                    wr_now <= 1'b1; cq_seq <= wi; wi <= wi + 2'd1; if (wi == 2'd3) gap <= 3'd6;
                    case (ph)
                        P_TAB: begin
                            cq <= {1'b1, 1'b1, 11'd0, 1'b0, t_sec, 5'd0, t_data, wkill ? 32'd0 : bmask(t_wm), {14'h0244, wi}};
                            if (sct == 2'd0) begin
                                obuf[32*int'(slot[2:0]) +: 32] <= {23'd0, p2_u}; omask[slot[2:0]] <= p2_v;
                                if (p2_v || MUT == 4) ucount <= ucount + 10'd1;
                            end
                            if (sct + 2'd1 == ts) begin
                                sct <= 2'd0;
                                if (slot[2:0] == 3'd7 || last_slot) ph <= P_O;
                                slot <= slot + 8'd1;
                            end else sct <= sct + 2'd1;
                        end
                        P_O: begin
                            cq <= {1'b1, 1'b1, 11'd0, 1'b0, o_sec, 5'd0, obuf, wkill ? 32'd0 : bmask(omask), {14'h0244, wi}};
                            obuf <= 256'd0; omask <= 8'd0; ogrp <= ogrp + 5'd1;
                            ph <= (slot == tslots) ? P_D : P_TAB;
                        end
                        default: begin                                    // P_D: D[0] = U
                            cq <= {1'b1, 1'b1, 11'd0, 1'b0, d_sec, 5'd0, {8{22'd0, ucount}},
                                   wkill ? 32'd0 : bmask(8'd1 << d_base_q[2:0]), {14'h0244, wi}};
                            st <= S_NEXT;
                        end
                    endcase
                end
                S_NEXT: begin cnt <= 4'(ACK - 1); st <= S_END; end
                S_END: if (cnt == 4'd0) begin
                    done <= !(flt || dbad || ack_bad); fault <= flt || dbad || ack_bad;
                    busy <= 1'b0; st <= S_IDLE;
                end else cnt <= cnt - 4'd1;
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
