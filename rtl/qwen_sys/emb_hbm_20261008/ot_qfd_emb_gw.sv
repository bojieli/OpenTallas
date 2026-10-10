`timescale 1ns/1ps
// Embedding gateway in the hub (emb-hbm 2026-10-08): the die face the SU's embedding requester talks to, now that the
// table sits in each die's attached HBM instead of the on-die ROM.  The SU face is the r21f embedding ROM's, unchanged
// (ot_qfd_su_embed_pf / ot_qfd_io_embedding_rom): one request word {kind, 24-b address} with credits (the SU starts
// with RQD credits, ea_cr returns one a request retired), one 512-b response word a request, in request order.
//   kind 0: code word a = t * 64 + w (the 64 bytes 64 w .. 64 w + 63 of row t), kind 1: the BF16 scale of row t.
// The SU fetches a row as 64 code words in order then the scale (a token already buffered is not fetched again), so:
//   * code word 0 of row t opens a FETCH: one EMB-class FETCH word {t, sequence} broadcast on the four stack links
//     (only once the boot load is complete and checked: emb_ready; until then the request waits = the first-token
//     gate); every stack returns its 16 code words in order (code words 16 k .. 16 k + 15 from stack k) and the stack
//     holding the scale returns it after them;
//   * the requests are answered in order from the link receive FIFOs: code word w from link w[5:4], the scale from
//     link (t >> 9) & 3.  No row buffer: the hub's per-link receive buffers hold the words (the link credits cover
//     them); a one-word slot a link (e_take loads it) keeps the FIFO read off the decision path.
//   * boot: the loader's RAW sector stream reaches the strips as EMB BOOT_WR words through the existing x3 path; the
//     BOOT_END word that closes it carries the expected count / checksum (bend_*, snooped by the hub at send).  The four
//     strips answer with STATUS words {count, checksum}; their sums must match: emb_ready (sticky), else fault.
// Fail closed: a request out of sequence or out of range, a link word of the wrong kind / sequence, a POISONED word
// (uncorrectable ECC in HBM) or a failed boot check latches fault and nothing more is answered.
// MUT = 4 (bench mutant, must FAIL): the boot gate is ignored (a fetch before the load is complete).
module ot_qfd_emb_gw #(
    parameter integer RQD = 32,
    parameter integer MUT = 0
) (
    input  wire              ck,
    input  wire              rn,
    // SU face (registered at the hub pins by the caller)
    input  wire              ea_v,
    input  wire              ea_kind,
    input  wire [23:0]       ea_addr,
    output reg               ea_cr,
    output reg               eq_v,
    output reg  [511:0]      eq_d,
    // link receive heads, EMB class (the caller pops with e_take)
    input  wire [3:0]        e_v,
    input  wire [4*523-1:0]  e_d,
    output wire [3:0]        e_take,
    // command words to the links (broadcast FETCH)
    output reg               g_v,
    output reg  [10:0]       g_tag,
    output reg  [511:0]      g_d,
    input  wire              g_rdy,
    // the BOOT_END word as the hub sends it (expected sectors [31:0], checksum [63:32])
    input  wire              bend_v,
    input  wire [63:0]       bend_d,
    output reg               emb_ready,
    output wire              fault,
    output reg  [7:0]        fault_code,
    output reg  [31:0]       fetches
);
    import ot_qfd_emb_pkg::*;
    localparam integer RA = $clog2(RQD);
    // ---- request FIFO ------------------------------------------------------------------------------------------------
    reg [24:0] rq [0:RQD-1];
    reg [RA:0] rw, rr;
    wire r_ne = rw != rr;
    wire r_full = (rw[RA-1:0] == rr[RA-1:0]) && (rw[RA] != rr[RA]);
    wire [24:0] rh = rq[rr[RA-1:0]];
    wire hk = rh[24];
    wire [23:0] ha = rh[23:0];
    always @(posedge ck) if (ea_v) rq[rw[RA-1:0]] <= {ea_kind, ea_addr};
    // ---- per-link one-word slots -------------------------------------------------------------------------------------
    reg [3:0] sv;
    reg [522:0] sd [0:3];
    assign e_take = e_v & ~sv;
    // ---- row state -------------------------------------------------------------------------------------------------
    localparam [1:0] S_IDLE = 0, S_ISSUE = 1, S_ROW = 2, S_DEAD = 3;
    reg [1:0] st;
    reg [17:0] ct; reg [3:0] seq; reg [6:0] w;
    wire [1:0] lk = (w == 7'd64) ? ct[10:9] : w[5:4];
    wire [522:0] sl = sd[lk];
    wire sl_ok = sl[522] && sl[521:520] == ((w == 7'd64) ? K_SCALE : K_CODE) && sl[515:512] == seq && !sl[519];
    wire hd_ok = (w == 7'd64) ? (hk && ha == {6'd0, ct}) : (!hk && ha == {ct, w[5:0]});
    wire serve = st == S_ROW && r_ne && sv[lk] && hd_ok && sl_ok;
    // ---- boot status ---------------------------------------------------------------------------------------------
    reg bend; reg [31:0] x_cnt, x_csum, a_cnt, a_csum; reg [2:0] nst;
    reg [3:0] stv;                               // slots holding a STATUS word
    integer i;
    always @(*) for (i = 0; i < 4; i = i + 1) stv[i] = sv[i] && sd[i][522] && sd[i][521:520] == K_STATUS;
    wire [1:0] sp = stv[0] ? 2'd0 : stv[1] ? 2'd1 : stv[2] ? 2'd2 : 2'd3;
    reg f_q;
    assign fault = f_q;
    always @(posedge ck) for (i = 0; i < 4; i = i + 1) if (e_take[i]) sd[i] <= e_d[i*523 +: 523];
    always @(posedge ck or negedge rn)
        if (!rn) begin
            rw <= 0; rr <= 0; sv <= 0; st <= S_IDLE; ct <= 0; seq <= 0; w <= 0; ea_cr <= 1'b0; eq_v <= 1'b0; g_v <= 1'b0;
            bend <= 1'b0; x_cnt <= 0; x_csum <= 0; a_cnt <= 0; a_csum <= 0; nst <= 0; emb_ready <= 1'b0;
            f_q <= 1'b0; fault_code <= 0; fetches <= 0;
        end else begin
            ea_cr <= 1'b0; eq_v <= 1'b0;
            if (ea_v) begin rw <= rw + 1'b1; if (r_full) begin f_q <= 1'b1; fault_code[0] <= 1'b1; end end
            // slots: load / free
            for (i = 0; i < 4; i = i + 1) if (e_take[i]) sv[i] <= 1'b1;
            // boot status words (one a cycle)
            if (|stv) begin
                sv[sp] <= 1'b0;
                if (!bend) begin f_q <= 1'b1; fault_code[6] <= 1'b1; end
                a_cnt <= a_cnt + sd[sp][31:0]; a_csum <= a_csum + sd[sp][63:32]; nst <= nst + 1'b1;
            end
            if (bend_v) begin bend <= 1'b1; x_cnt <= bend_d[31:0]; x_csum <= bend_d[63:32]; a_cnt <= 0; a_csum <= 0; nst <= 0; end
            if (bend && nst == 3'd4) begin
                bend <= 1'b0;
                if (a_cnt == x_cnt && a_csum == x_csum) emb_ready <= 1'b1;
                else begin f_q <= 1'b1; fault_code[5] <= 1'b1; end
            end
            case (st)
                S_IDLE: if (r_ne) begin
                    if (hk || ha[5:0] != 6'd0) begin f_q <= 1'b1; fault_code[1] <= 1'b1; st <= S_DEAD; end
                    else if (ha[23:6] >= 18'(VOCAB)) begin f_q <= 1'b1; fault_code[2] <= 1'b1; st <= S_DEAD; end
                    else if (emb_ready || MUT == 4) begin
                        ct <= ha[23:6]; seq <= seq + 1'b1; w <= 0; st <= S_ISSUE;
                        g_v <= 1'b1; g_tag <= {1'b1, K_FETCH, 1'b0, 3'd0, 4'(seq + 1'b1)}; g_d <= {494'd0, ha[23:6]};
                    end
                end
                S_ISSUE: if (g_rdy) begin g_v <= 1'b0; st <= S_ROW; fetches <= fetches + 1'b1; end
                S_ROW: if (r_ne) begin
                    if (!hd_ok) begin f_q <= 1'b1; fault_code[1] <= 1'b1; st <= S_DEAD; end
                    else if (sv[lk] && !(sd[lk][521:520] == K_STATUS)) begin
                        if (sl[519]) begin f_q <= 1'b1; fault_code[4] <= 1'b1; st <= S_DEAD; end
                        else if (!sl_ok) begin f_q <= 1'b1; fault_code[3] <= 1'b1; st <= S_DEAD; end
                        else begin
                            eq_v <= 1'b1; eq_d <= (w == 7'd64) ? {496'd0, sl[15:0]} : sl[511:0];
                            sv[lk] <= 1'b0; rr <= rr + 1'b1; ea_cr <= 1'b1;
                            w <= w + 1'b1;
                            if (w == 7'd64) st <= S_IDLE;
                        end
                    end
                end
                default: ;
            endcase
            if (f_q) st <= S_DEAD;
        end
endmodule
