`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// R25 ATT ENTRY STAGER (hgi-1010/att 2026-10-11, lead-approved P1).  One per ACTIVE attention entry, on the svc PS row
// route ks<g> -> hfd_attn_half_lo.ks (KVIB = 1).  The tile is BF16-stationary (ld) x FP8-stored (ib), so the KV rows
// must reach it as ISSUE beats; the PS rows reach this entry in HBM / group round-robin order and the tile pipe carries
// no tag, so the order is restored HERE, before the tiles (results then leave the row end in a fixed order).
//
// ROW-WORD (one PS row, 1,024 b = 4 sectors of one PC; the compiler's --attps layout writes it):
//   [575:0] ib = 32 elements x {pad, fmt, code8, scale8} (element e at 18 e), [1023:576] = 0.
// BLOCK = 32 row-words (rows 32 b .. 32 b + 31 of one 32-dim slice s): row-word r of local block lb is PS row rq = 8 lb +
//   r / 4 of PC c = r mod 4 of this entry's group (meta pcid[1:0] = c).  An entry's blocks are (beta, s) row-block-major:
//   lb = beta_local x S + s.
// LOAD TAG (meta[32:20], from the e2 stream command): {mode, lgG 3, S - 1 4, ph, 4'b0}: mode 0 QK / 1 PV; G = 2^lgG
//   slices a q bank (QK ibank = s >> lgG); PV ibank = beta_local mod 5; ph toggles every stream (counters restart).
// EMISSION (one beat a cycle, block lb in order, only with a block TOKEN from the controller, bt = {fclk, v}: the
//   block's stationary bank is loaded): QK beat r = row-word r (ibank s >> lgG); PV beat d = element d of row-words
//   0..31 (the transpose: one dim of the block's 32 rows; ibank beta mod 5).
// CREDITS (N9, kq = {fclk, v}, one a row, in ARRIVAL order as ot_svs_grp maps them to PCs): a row's credit returns
//   once its block has been emitted and every earlier-arrived row's credit has returned.  NBUF = 2 block buffers is
//   enough at CRR 16 rows a PC (8 rows a PC a block: a PC's window spans at most the oldest unemitted block + 1).
// Faults (sticky flt): a row past the buffer window, a new stream while credits are owed, idx rows.
// Mutants: OT_ATT_STG_MUT_TAG (rows placed by arrival count, not tag: B2), OT_ATT_STG_MUT_TP (PV not transposed: B4),
//   OT_ATT_STG_MUT_KQ (credit on arrival), OT_ATT_STG_MUT_BANK (QK ibank = s).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_att_stager #(
    parameter integer NBUF = 2
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1101:0] ks_i,       // svc PS row port {fclk x3, meta64, row1024, rq10, v}
    output wire [1:0]    kq_o,       // line credit to the svc group unit {fclk, v}
    input  wire [1:0]    bt_i,       // block token from the controller {fclk, v}
    output wire [1101:0] ks_o,       // tile beats to hfd_attn_half_lo.ks (KVIB): row[578:0] = {ibank, ib}
    output reg           flt
);
    localparam integer BW = (NBUF > 1) ? $clog2(NBUF) : 1;
    // ---- pin registers
    reg rv; reg [63:0] rmeta; reg [575:0] rrow; reg [9:0] rrq; reg tv;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rv <= 1'b0; tv <= 1'b0; end
        else begin rv <= ks_i[0]; tv <= bt_i[0]; end
    always @(posedge clk) begin rmeta <= ks_i[1098:1035]; rrow <= ks_i[11 +: 576]; rrq <= ks_i[10:1]; end
    wire [12:0] tag = rmeta[32:20];
    wire        ridx = rmeta[19];
    wire [1:0]  rc = rmeta[15:14];                       // PC within the group (pcid[1:0])
    // ---- configuration (latched per row; constant over a stream)
    reg mode; reg [2:0] lgG; reg [3:0] sm1; reg ph, ph_seen;
    // ---- buffers
    reg [575:0] b [0:NBUF-1][0:31];
    reg [5:0]   cnt [0:NBUF-1];
    reg [6:0]   elb;                                     // blocks emitted this stream
    reg [7:0]   tok;                                     // block tokens held
    reg [5:0]   acnt;                                    // MUT_TAG: arrival count
    // arrival FIFO (credits in arrival order)
    localparam integer AQ = 128;
    reg [6:0] aq [0:AQ-1]; reg [6:0] ah, at; reg [7:0] an;
    wire [6:0]  lb = rrq[9:3];
`ifdef OT_ATT_STG_MUT_TAG
    wire [4:0]  r  = acnt[4:0];
`else
    wire [4:0]  r  = {rrq[2:0], rc};
`endif
    wire [BW-1:0] wsl = lb[BW-1:0];
    wire land = rv && !ridx;
    wire newst = land && (!ph_seen || tag[4] != ph);
    // ---- emission state
    reg em; reg [4:0] ei; reg [BW-1:0] esl; reg [3:0] sc; reg [2:0] bm5; reg [2:0] eib;
    wire [BW-1:0] nsl = elb[BW-1:0];
    wire go = !em && (cnt[nsl] == 6'd32) && (tok != 8'd0 || tv);
    // ---- the beat
    reg ov; reg [575:0] ob; reg [2:0] obk;
    integer x, y;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (x = 0; x < NBUF; x = x + 1) cnt[x] <= 6'd0;
            elb <= 7'd0; tok <= 8'd0; em <= 1'b0; ei <= 5'd0; sc <= 4'd0; bm5 <= 3'd0; flt <= 1'b0; ph_seen <= 1'b0;
            ph <= 1'b0; mode <= 1'b0; lgG <= 3'd0; sm1 <= 4'd0; ah <= 7'd0; at <= 7'd0; an <= 8'd0; ov <= 1'b0; acnt <= 6'd0;
        end else begin
            ov <= 1'b0;
            if (rv && ridx) flt <= 1'b1;
            tok <= tok + (tv ? 8'd1 : 8'd0) - (go ? 8'd1 : 8'd0);
            if (newst) begin
                if (an != 8'd0 || em) flt <= 1'b1;               // credits still owed from the last stream
                ph <= tag[4]; ph_seen <= 1'b1; elb <= 7'd0; sc <= 4'd0; bm5 <= 3'd0; acnt <= 6'd0;
            end
            if (land) begin
                mode <= tag[12]; lgG <= tag[11:9]; sm1 <= tag[8:5];
                if ({1'b0, lb} >= {1'b0, (newst ? 7'd0 : elb)} + NBUF) flt <= 1'b1;   // past the window
                acnt <= (newst ? 6'd0 : acnt) + 6'd1;
            end
            // emission
            if (go) begin em <= 1'b1; ei <= 5'd0; esl <= nsl; end
            if (em) begin
                ov <= 1'b1; ei <= ei + 5'd1;
                if (!mode) ob <= b[esl][ei];
                else for (y = 0; y < 32; y = y + 1)
`ifdef OT_ATT_STG_MUT_TP
                    ob[18*y +: 18] <= b[esl][ei][18*y +: 18];
`else
                    ob[18*y +: 18] <= b[esl][y][18*ei +: 18];
`endif
`ifdef OT_ATT_STG_MUT_BANK
                obk <= mode ? bm5 : sc[2:0];
`else
                obk <= mode ? bm5 : (sc >> lgG);
`endif
                if (ei == 5'd31) begin
                    em <= 1'b0; elb <= elb + 7'd1;
                    if (sc == sm1) begin sc <= 4'd0; bm5 <= (bm5 == 3'd4) ? 3'd0 : bm5 + 3'd1; end
                    else sc <= sc + 4'd1;
                end
            end
            // block counts (a landing and the end of an emission never share a slot: the window check)
            for (x = 0; x < NBUF; x = x + 1) begin
                if (em && ei == 5'd31 && esl == x[BW-1:0]) cnt[x] <= 6'd0;
                else if (land && wsl == x[BW-1:0]) cnt[x] <= cnt[x] + 6'd1;
            end
            // arrival FIFO and credits
`ifdef OT_ATT_STG_MUT_KQ
            an <= 8'd0;
`else
            if (land) at <= at + 7'd1;
            if (an != 8'd0 && aq[ah] < elb && !newst) ah <= ah + 7'd1;
            an <= an + (land ? 8'd1 : 8'd0) - ((an != 8'd0 && aq[ah] < elb && !newst) ? 8'd1 : 8'd0);
`endif
        end
    end
    always @(posedge clk) begin
        if (land) begin b[wsl][r] <= rrow; aq[at] <= lb; end
    end
    // credit pulse (registered)
    reg kv;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) kv <= 1'b0;
`ifdef OT_ATT_STG_MUT_KQ
        else kv <= land;
`else
        else kv <= an != 8'd0 && aq[ah] < elb && !newst;
`endif
    wire fck; ot_fwd_clk_inv u_fk (.a(clk), .y(fck));
    assign kq_o = {fck, kv};
    assign ks_o = {3'b000, 64'd0, 445'd0, obk, ob, 10'd0, ov};
endmodule
`default_nettype wire
