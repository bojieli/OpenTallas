`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Auxiliary unit (XU) of the DeepSeek-V4.1 hardwired decode core.
//
// SEL      top-k of n values read from the vector memory (one per cycle) by the
//          SELECT unit ot_hdc_select (ties to the lower index, ascending index
//          out); the k indices are written back as integers.  Router top-6 and
//          the indexer's top-16.
// SINK     the 40 Sinkhorn normalisations of a 4 x 4 mix (after the row-max
//          exponential): 16 values in, 16 out.  The latency-optimised unit
//          ot_hdc_sinkhorn (one normalisation per unit clock) as a multicycle
//          path of SK_STEP core cycles a step (ot_hdc_sinkhorn_mc); with
//          HDC_SINKHORN_SEQ the simple sequential unit ot_hdc_sinkhorn_seq.
// EHASH    the new token's compressed id (constant-ROM token map) into the
//          Engram hash unit ot_hdc_engram_hash; its row addresses for both
//          Engram layers are held until the next EHASH.
// EGATHER  the 24 rows of one Engram layer from the Engram table ROM, each 32
//          E4M3 codes times 2^scale, written as BF16 (exact: E4M3 fits BF16;
//          a scaled value outside the normal binary32 range fails closed).
//
// `prime_*` feed the hash unit's history directly (a single-step test that
// starts mid-sequence primes it with the preceding tokens).
// ---------------------------------------------------------------------------
module ot_hdc_v41_xu #(
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer K = 16,
    parameter integer SK_STEP = 7          // core cycles per Sinkhorn step (ot_hdc_sinkhorn_mc)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [1:0]        i_op,
    input  wire [AW-1:0]     i_src, i_dst,
    input  wire [NW-1:0]     i_n,
    input  wire [4:0]        i_k,
    input  wire              i_layer,
    input  wire [NW-1:0]     token,
    input  wire              first,           // position 0: the hash history restarts
    input  wire              prime_v,
    input  wire              prime_first,
    input  wire [11:0]       prime_cid,
    // vector memory: element read, 32-element read, element write, masked 32-element write
    output reg               vr_re,
    output reg  [AW-1:0]     vr_addr,
    input  wire [31:0]       vr_q,
    output reg               xr_re,
    output reg  [AW-1:0]     xr_addr,
    input  wire [1023:0]     xr_q,
    output reg               vw_we,
    output reg  [AW-1:0]     vw_addr,
    output reg  [31:0]       vw_data,
    output reg               w_we,
    output reg  [AW-1:0]     w_addr,
    output reg  [31:0]       w_mask,
    output reg  [1023:0]     w_data,
    // constant ROM (token map) and Engram table ROM
    output reg               cr_re,
    output reg  [AW-1:0]     cr_addr,
    input  wire [63:0]       cr_q,
    output reg               er_re,
    output reg  [AW-1:0]     er_addr,
    input  wire [263:0]      er_q,
    output reg               fault
);
    import ot_hdc_engram_tables_pkg::*;
    localparam [1:0] OP_SEL = 0, OP_SINK = 1, OP_EHASH = 2, OP_EGATHER = 3;
    localparam [3:0] S_IDLE = 0, S_SEL = 1, S_SELW = 2, S_SK0 = 3, S_SK1 = 4, S_SKW = 5, S_EH0 = 6, S_EH1 = 7,
                     S_EHW = 8, S_EG = 9, S_EGW = 10, S_EHC = 11;
    localparam integer KW = $clog2(K + 1);
    reg [3:0]    st;
    reg [1:0]    op;
    reg [AW-1:0] src, dst;
    reg [NW-1:0] n, ni, nw;
    reg [4:0]    k;
    reg          layer;
    reg [5:0]    cnt;
    assign ready = (st == S_IDLE) && !sel_busy;
    wire accept = go && ready;

    // -- SELECT -----------------------------------------------------------------------------------
    reg          s_v, s_last;
    reg [NW-1:0] s_idx;
    wire         sel_ready, sel_busy, so_v, so_last, so_ninf;
    wire [15:0]  so_idx;
    reg          r1_v, r1_last;
    reg [NW-1:0] r1_idx;
    wire [KW-1:0] kk = (k > n) ? n[KW-1:0] : k[KW-1:0];
    ot_hdc_select #(.K(K), .VW(32), .IW(16), .ORDER(1)) u_sel (.clk(clk), .rst_n(rst_n),
        .in_valid(s_v), .in_ready(sel_ready), .in_last(s_last), .in_val(vr_q), .in_idx(s_idx[15:0]),
        .in_k(kk), .out_valid(so_v), .out_last(so_last), .out_idx(so_idx), .out_ninf(so_ninf), .busy(sel_busy));

    // -- Sinkhorn -----------------------------------------------------------------------------------
    reg          sk_in;                     // request, held until the unit is busy
    wire         sk_ready, sk_ov, sk_f, sk_busy;
    wire [511:0] sk_y;
`ifdef HDC_SINKHORN_SEQ
    ot_hdc_sinkhorn_seq u_sk (.clk(clk), .rst_n(rst_n), .in_valid(sk_in), .in_ready(sk_ready),
        .in_e(xr_q[511:0]), .out_valid(sk_ov), .y(sk_y), .fault(sk_f), .busy(sk_busy));
`else
    ot_hdc_sinkhorn_mc #(.STEP_CYC(SK_STEP)) u_sk (.clk(clk), .rst_n(rst_n), .req(sk_in), .in_e(xr_q[511:0]),
        .busy(sk_busy), .done(sk_ov), .y(sk_y), .fault(sk_f));
`endif

    // -- Engram hash ------------------------------------------------------------------------------------
    reg          h_v, h_first;
    reg [11:0]   h_cid;
    wire         h_ov;
    wire [ENG_ROW_W*ENG_LAYERS*ENG_COLS-1:0] h_rows;
    reg  [ENG_ROW_W*ENG_LAYERS*ENG_COLS-1:0] rows;
    ot_hdc_engram_hash u_hash (.clk(clk), .rst_n(rst_n), .in_valid(h_v || (prime_v && st == S_IDLE)),
        .in_first(h_v ? h_first : prime_first), .in_cid(h_v ? h_cid : prime_cid), .out_valid(h_ov),
        .out_row(h_rows));

    // -- Engram gather: dequantise a row (E4M3 code * 2^scale -> binary32, exact) ------------------------
    function automatic [32:0] deq(input [7:0] c, input signed [7:0] sc);   // {bad, value}
        reg signed [10:0] e;
        reg [2:0] m;
        reg [22:0] f;
        begin
            m = c[2:0];
            if (c[6:0] == 7'h7F) deq = {1'b1, 32'd0};
            else if (c[6:3] == 4'd0 && m == 3'd0) deq = {1'b0, c[7], 31'd0};        // +-0 keeps its sign
            else begin
                if (c[6:3] != 4'd0) begin e = $signed({7'd0, c[6:3]}) - 11'sd7; f = {m, 20'd0}; end
                else if (m[2]) begin e = -11'sd7; f = {m[1:0], 21'd0}; end
                else if (m[1]) begin e = -11'sd8; f = {m[0], 22'd0}; end
                else begin e = -11'sd9; f = 23'd0; end
                e = e + sc + 11'sd127;
                if (e < 11'sd1 || e > 11'sd254) deq = {1'b1, 32'd0};
                else deq = {1'b0, c[7], e[7:0], f};
            end
        end
    endfunction

    reg flt;
    reg [4:0] eg_c;
    integer q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; vr_re <= 0; xr_re <= 0; vw_we <= 0; w_we <= 0; cr_re <= 0; er_re <= 0;
            s_v <= 0; sk_in <= 0; h_v <= 0; flt <= 0; fault <= 0;
        end else begin
            vr_re <= 0; xr_re <= 0; vw_we <= 0; w_we <= 0; cr_re <= 0; er_re <= 0; h_v <= 0;
            if (sk_busy) sk_in <= 1'b0;
            s_v <= r1_v; s_last <= r1_last; s_idx <= r1_idx;
            r1_v <= 0;
            fault <= flt;
            case (st)
                S_IDLE: if (accept) begin
                    op <= i_op; src <= i_src; dst <= i_dst; n <= i_n; k <= i_k; layer <= i_layer; ni <= 0; nw <= 0;
                    cnt <= 0;
                    case (i_op)
                        OP_SEL: st <= S_SEL;
                        OP_SINK: st <= S_SK0;
                        OP_EHASH: st <= S_EH0;
                        default: st <= S_EG;
                    endcase
                end
                // one value per cycle; it reaches the SELECT unit two cycles later
                S_SEL: begin
                    vr_re <= 1'b1; vr_addr <= src + ni; ni <= ni + 1'b1;
                    r1_v <= 1'b1; r1_idx <= ni; r1_last <= (ni + 1 == n);
                    if (ni + 1 == n) st <= S_SELW;
                end
                S_SELW: if (nw == ((k > n) ? n : k) && !sel_busy) st <= S_IDLE;
                S_SK0: begin xr_re <= 1'b1; xr_addr <= src; st <= S_SK1; end
                S_SK1: begin cnt <= cnt + 1'b1; if (cnt == 6'd1) begin sk_in <= 1'b1; st <= S_SKW; end end
                S_SKW: if (sk_ov) begin
                    w_we <= 1'b1; w_addr <= dst; w_mask <= 32'h0000FFFF; w_data <= {512'd0, sk_y};
                    if (sk_f) flt <= 1'b1;
                    st <= S_IDLE;
                end
                S_EH0: begin cr_re <= 1'b1; cr_addr <= src + token; st <= S_EH1; end
                S_EH1: begin cnt <= cnt + 1'b1; if (cnt == 6'd1) begin h_v <= 1'b1; h_cid <= cr_q[11:0]; h_first <= first; st <= S_EHW; end end
                S_EHW: if (h_ov) begin rows <= h_rows; st <= S_IDLE; end
                S_EG: begin
                    er_re <= 1'b1; er_addr <= src + rows[ENG_ROW_W*(layer*ENG_COLS + eg_c) +: ENG_ROW_W];
                    if (eg_c + 1 == ENG_COLS) st <= S_EGW;
                end
                S_EGW: begin cnt <= cnt + 1'b1; if (cnt == 6'd3) st <= S_IDLE; end
                default: st <= S_IDLE;
            endcase
            if (so_v) begin vw_we <= 1'b1; vw_addr <= dst + nw; vw_data <= {16'd0, so_idx}; nw <= nw + 1'b1; end
            if (s_v && !sel_ready) flt <= 1'b1;                     // never: one segment per op
            // gathered rows: the ROM answers two cycles after the address
            if (eg_v1) begin
                w_we <= 1'b1; w_addr <= dst + {eg_i1, 5'd0}; w_mask <= 32'hFFFFFFFF;
                for (q = 0; q < 32; q = q + 1) begin
                    w_data[32*q +: 32] <= deq(er_q[8*q +: 8], er_q[263:256]);
                    if (deq(er_q[8*q +: 8], er_q[263:256]) >> 32) flt <= 1'b1;
                end
            end
        end
    end
    always @(posedge clk) begin
        if (st == S_IDLE) eg_c <= 0; else if (st == S_EG) eg_c <= eg_c + 1'b1;
    end
    reg eg_v1, eg_v2;
    reg [4:0] eg_i1, eg_i2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin eg_v1 <= 0; eg_v2 <= 0; end
        else begin eg_v1 <= er_re; eg_v2 <= eg_v1; end
    end
    always @(posedge clk) begin eg_i1 <= eg_c - 1'b1; eg_i2 <= eg_i1; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= (st == S_IDLE) && !accept && !sel_busy && !vw_we && !w_we && !sk_busy && !sk_in && !eg_v1 &&
                     !eg_v2;
    end
endmodule
