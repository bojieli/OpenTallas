`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.OWNED (IDX op 3, G24, hgi-takeover 2026-10-09; review ~16:40: ROW_GATHER = R3 software slots + this
// one op).  From the replicated selection list it computes, on every rank, what the software ROW_GATHER needs:
//
//   A  VM U32 [K]   the selected row ids (list order; id < 2^20)
//   O  VM U32 [M]   THIS rank's owned local rows in list order, padded with 0 up to M (row 0 always exists)
//   R  VM U32 [K]   for every list entry i: its row in the gathered output, j * G + owner r (j = its slot among r's)
//   D  VM U32 [2]   D[0] = the largest owned count in the group; D[1] = ceil(M / c), c=0/1 means 1
//   param [7:0] B (owner block, a power of two 1 .. 128), [15:8] G (1, 2, 4, 8 or 96), [23:16] c; rank = die id mod G
// Owner rule (spec 6.7 ROW_GATHER): row i is owned by rank (i div B) mod G and lives there at local row
// (i div (B G)) B + i mod B.  Then for each slot j < M: DMA.LOAD (indexed by O[j]) -> COLL.ALL_GATHER -> DMA.STORE of
// the G rows to j * G + r: the network moves exactly the rows, the attention unit reads list order through R.
// Passes: P1 count per owner (ids streamed, VM fast path), P2 M = max, P3 R / O by a running slot per owner, P4 pad O,
// write M.  One id a cycle when the VM keeps up.  An id >= 2^20 or an illegal B / G: fault (E_RANGE).
module ot_hgi_idx_owned #(
    parameter integer MUT = 0          // mutants: 1 wrong owner, 2 obsolete owner-major R, 3 unbatched D[1]
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [7:0]    blk,
    input  wire [7:0]    grp,
    input  wire [7:0]    die,
    input  wire [7:0]    batch,
    input  wire [19:0]   k,            // list length
    input  wire [17:0]   a_base, o_base, r_base, d_base,
    output reg           done,
    output reg           fault,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr
);
    // ---------------------------------------------------------------- owner arithmetic (registered per id)
    reg [2:0] lb;                     // log2 B
    reg [2:0] lg;                     // log2 G (G <= 8)
    reg g96;
    reg [6:0] rank;
    function automatic [33:0] own(input [31:0] id);   // {owner 7, local row 20, unused}
        reg [19:0] x; reg [14:0] q; reg [6:0] o; reg [19:0] lr;
        begin
            x = (MUT == 1) ? id[19:0] : (id[19:0] >> lb);
            if (g96) begin
                q = x[19:5];
                o = {(q % 15'd3), x[4:0]};
                lr = ((q / 15'd3) << lb) | (id[19:0] & ((20'd1 << lb) - 20'd1));
            end else begin
                o = 7'(x & ((20'd1 << lg) - 20'd1));
                lr = ((x >> lg) << lb) | (id[19:0] & ((20'd1 << lb) - 20'd1));
            end
            own = {7'd0, o, lr};
        end
    endfunction
    // ---------------------------------------------------------------- VM: A stream (4 outstanding, in-order buffer)
    reg [2:0] ocnt; reg iss, a_iss, af_push, af_pop;
    reg [14:0] a_req, a_last; reg [2:0] a_fl; reg [255:0] af [0:3]; reg [1:0] af_h, af_t; reg [2:0] af_n;
    reg [2:0] aw;                     // word within the head sector
    // packers: 0 O, 1 R
    reg [17:0] pk_a [0:1]; reg [255:0] pk_d [0:1]; reg [7:0] pk_m [0:1]; reg [14:0] pk_s [0:1]; reg [1:0] pk_full;
    reg wp_v; reg wp;
    always @* begin wp_v = |pk_full; wp = pk_full[0] ? 1'b0 : 1'b1; end
    // ---------------------------------------------------------------- state
    localparam S_IDLE = 4'd0, S_CNT = 4'd1, S_MAX = 4'd2, S_MAP = 4'd3, S_PAD = 4'd4, S_M = 4'd5, S_FLUSH = 4'd6, S_DIV_INIT = 4'd7, S_DIV = 4'd8, S_D1 = 4'd9;
    reg [3:0] st;
    reg [7:0] batch_q;
    reg [12:0] div_num, div_rem;
    reg [11:0] batches;
    reg [3:0] div_bit;
    reg [12:0] trial;
    reg [11:0] cnt [0:95];            // P1: per-owner counts; P3: running slot
    reg [19:0] idx;                   // ids consumed this pass
    reg [11:0] m, mine;
    reg [6:0] mi;
    reg [31:0] id; reg [33:0] ow; integer i;
    reg first;                        // P3 restart of the stream
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; vmq <= 338'd0; ocnt <= 3'd0; a_fl <= 3'd0; af_n <= 3'd0;
            af_h <= 2'd0; af_t <= 2'd0; pk_full <= 2'd0; pk_m[0] <= 8'd0; pk_m[1] <= 8'd0;
        end else begin
            done <= 1'b0; fault <= 1'b0; vmq[337] <= 1'b0; iss = 1'b0; a_iss = 1'b0; af_push = 1'b0; af_pop = 1'b0;
            if (vmr[273] && vmr[272:257] == 16'h0930) begin af[af_t] <= vmr[255:0]; af_t <= af_t + 2'd1; af_push = 1'b1; end
            // A stream request (passes P1 and P3)
            if ((st == S_CNT || st == S_MAP) && a_req != a_last && ocnt < 3'd4 && a_fl + af_n < 3'd4 && !wp_v) begin
                iss = 1'b1; a_iss = 1'b1;
                vmq <= {1'b1, 1'b0, {12'd0, a_req, 5'd0}, 256'd0, 32'd0, 16'h0930}; a_req <= a_req + 15'd1;
            end
            case (st)
                S_IDLE: if (go) begin
                    lb = (blk == 8'd1) ? 3'd0 : (blk == 8'd2) ? 3'd1 : (blk == 8'd4) ? 3'd2 : (blk == 8'd8) ? 3'd3 :
                         (blk == 8'd16) ? 3'd4 : (blk == 8'd32) ? 3'd5 : (blk == 8'd64) ? 3'd6 : 3'd7;
                    if (!(blk != 0 && (blk & (blk - 8'd1)) == 0) || !(grp == 1 || grp == 2 || grp == 4 || grp == 8 || grp == 96) ||
                        k == 20'd0 || k > 20'd2048) fault <= 1'b1;
                    else begin
                        batch_q <= batch; g96 <= grp == 8'd96; lg <= (grp == 8'd2) ? 3'd1 : (grp == 8'd4) ? 3'd2 : (grp == 8'd8) ? 3'd3 : 3'd0;
                        rank <= (grp == 8'd96) ? ((die >= 8'd192) ? 7'(die - 8'd192) : (die >= 8'd96) ? 7'(die - 8'd96) : die[6:0])
                                               : 7'(die & (grp - 8'd1));
                        for (i = 0; i < 96; i = i + 1) cnt[i] <= 12'd0;
                        a_req <= a_base[17:3]; a_last <= 15'((a_base + k + 18'd7) >> 3); aw <= a_base[2:0];
                        idx <= 20'd0; st <= S_CNT; m <= 12'd0; mi <= 7'd0;
                        pk_a[0] <= o_base; pk_a[1] <= r_base; pk_m[0] <= 8'd0; pk_m[1] <= 8'd0;
                    end
                end
                // ---- P1: count per owner, one id a cycle
                S_CNT: if (af_n != 3'd0) begin
                    id = af[af_h][aw * 32 +: 32]; ow = own(id);
                    if (id[31:20] != 12'd0) begin st <= S_IDLE; fault <= 1'b1; end
                    else cnt[ow[26:20]] <= cnt[ow[26:20]] + 12'd1;
                    idx <= idx + 20'd1; aw <= aw + 3'd1;
                    if (aw == 3'd7 || idx + 20'd1 == k) begin af_h <= af_h + 2'd1; af_pop = 1'b1; end
                    if (idx + 20'd1 == k) begin st <= S_MAX; mi <= 7'd0; end
                end
                // ---- P2: M = the largest count; the running slots restart at 0; this rank's count kept
                S_MAX: begin
                    if (cnt[mi] > m) m <= cnt[mi];
                    if (mi == rank) mine <= cnt[mi];
                    cnt[mi] <= 12'd0;
                    if (mi == 7'd95) begin
                        st <= S_DIV_INIT; idx <= 20'd0; a_req <= a_base[17:3]; aw <= a_base[2:0];
                    end else mi <= mi + 7'd1;
                end
                S_DIV_INIT: begin
                    if (batch_q <= 8'd1) begin batches <= m; st <= S_MAP; end
                    else begin div_num <= {1'b0,m} + {5'd0,batch_q} - 13'd1;
                        div_rem <= 13'd0; batches <= 12'd0; div_bit <= 4'd12; st <= S_DIV; end
                end
                S_DIV: begin
                    trial = (div_rem << 1) | {12'd0,div_num[div_bit]};
                    if (trial >= {5'd0,batch_q}) begin
                        div_rem <= trial - {5'd0,batch_q};
                        if (div_bit < 12) batches[div_bit] <= 1'b1;
                    end else div_rem <= trial;
                    if (div_bit == 0) st <= S_MAP; else div_bit <= div_bit - 4'd1;
                end
                // ---- P3: R[i] = slot * G + owner; this rank's local rows to O
                S_MAP: if (af_n != 3'd0 && !pk_full[0] && !pk_full[1]) begin
                    id = af[af_h][aw * 32 +: 32]; ow = own(id);
                    pk_d[1][pk_a[1][2:0] * 32 +: 32] <= {14'd0, (MUT == 2) ? (18'(ow[26:20] * m) + 18'(cnt[ow[26:20]])) : ((g96 ? ((18'(cnt[ow[26:20]]) << 6) + (18'(cnt[ow[26:20]]) << 5)) : (18'(cnt[ow[26:20]]) << lg)) + 18'(ow[26:20]))};
                    pk_m[1][pk_a[1][2:0]] <= 1'b1; pk_s[1] <= pk_a[1][17:3]; pk_a[1] <= pk_a[1] + 18'd1;
                    if (pk_a[1][2:0] == 3'd7) pk_full[1] <= 1'b1;
                    if (ow[26:20] == rank) begin
                        pk_d[0][pk_a[0][2:0] * 32 +: 32] <= {12'd0, ow[19:0]}; pk_m[0][pk_a[0][2:0]] <= 1'b1;
                        pk_s[0] <= pk_a[0][17:3]; pk_a[0] <= pk_a[0] + 18'd1; if (pk_a[0][2:0] == 3'd7) pk_full[0] <= 1'b1;
                    end
                    cnt[ow[26:20]] <= cnt[ow[26:20]] + 12'd1;
                    idx <= idx + 20'd1; aw <= aw + 3'd1;
                    if (aw == 3'd7 || idx + 20'd1 == k) begin af_h <= af_h + 2'd1; af_pop = 1'b1; end
                    if (idx + 20'd1 == k) st <= S_PAD;
                end
                // ---- P4: pad O up to M with row 0
                S_PAD: if (!pk_full[0]) begin
                    if (mine >= m) st <= S_M;
                    else begin
                        pk_d[0][pk_a[0][2:0] * 32 +: 32] <= 32'd0; pk_m[0][pk_a[0][2:0]] <= 1'b1;
                        pk_s[0] <= pk_a[0][17:3]; pk_a[0] <= pk_a[0] + 18'd1; if (pk_a[0][2:0] == 3'd7) pk_full[0] <= 1'b1;
                        mine <= mine + 12'd1;
                    end
                end
                // ---- M to D (through packer 1, flushed first)
                S_M: begin
                    if (pk_m[0] != 8'd0) pk_full[0] <= 1'b1;
                    if (pk_m[1] != 8'd0) pk_full[1] <= 1'b1;
                    if (!wp_v && pk_m[0] == 8'd0 && pk_m[1] == 8'd0) begin
                        pk_a[1] <= d_base; pk_s[1] <= d_base[17:3];
                        pk_d[1][d_base[2:0] * 32 +: 32] <= {20'd0, m}; pk_m[1] <= 8'd1 << d_base[2:0]; pk_full[1] <= 1'b1;
                        st <= S_D1;
                    end
                end
                S_D1: if (!wp_v && pk_m[1] == 8'd0) begin
                    pk_s[1] <= (d_base + 18'd1) >> 3;
                    pk_d[1][((d_base + 18'd1) & 18'd7) * 32 +: 32] <= {20'd0, (MUT == 3 ? m : batches)};
                    pk_m[1] <= 8'd1 << ((d_base + 18'd1) & 18'd7); pk_full[1] <= 1'b1;
                    st <= S_FLUSH;
                end
                S_FLUSH: if (!wp_v && ocnt == 3'd0) begin st <= S_IDLE; done <= 1'b1; end
                default: st <= S_IDLE;
            endcase
            // ---- packer writes
            if (wp_v && !iss && ocnt < 3'd4) begin
                iss = 1'b1;
                vmq <= {1'b1, 1'b1, {12'd0, pk_s[wp], 5'd0}, pk_d[wp],
                        {{4{pk_m[wp][7]}}, {4{pk_m[wp][6]}}, {4{pk_m[wp][5]}}, {4{pk_m[wp][4]}},
                         {4{pk_m[wp][3]}}, {4{pk_m[wp][2]}}, {4{pk_m[wp][1]}}, {4{pk_m[wp][0]}}}, 16'h0931};
                pk_full[wp] <= 1'b0; pk_m[wp] <= 8'd0;
            end
            ocnt <= ocnt + {2'd0, iss} - {2'd0, vmr[273]};
            a_fl <= a_fl + {2'd0, a_iss} - {2'd0, af_push};
            af_n <= af_n + {2'd0, af_push} - {2'd0, af_pop};
        end
    end
endmodule
`default_nettype wire
