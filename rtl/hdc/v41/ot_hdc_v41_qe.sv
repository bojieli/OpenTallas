`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Quantised engine (QE) of the DeepSeek-V4.1 hardwired decode core.
//
// LINQ (tools/hdc_golden_v41.linear_q).  The op first quantises the activation:
// nb 32-element blocks are read from the vector memory (one 32-element word per
// cycle) through ot_hdc_actquant (E4M3 codes and a UE8M0 exponent per block)
// into a block buffer.  Then the quantised weight ROM streams words in
// (round r, block kb, slot j) order -- the word address is simply
// wbase + (r*nb + kb)*IL + j -- and BL ot_hdc_blockdot lanes each take block kb
// of row (r*IL + j)*BL + l: an exact 32-term block dot, scaled by
// 2^(e_w + e_x), accumulated over blocks in order on the lane's circulating
// adder ring, BF16 out.  The ring's slot counter (`phase`) runs free, so the
// op starts its word stream on the cycle that lines slot 0 up with phase 0 and
// then issues one word per cycle without a stall.  Results leave in slot
// order: the k-th result is rows k*BL .. k*BL+BL-1, written as one masked word.
//
// The weight base may add an expert id (read from the vector memory) times a
// stride: the routed experts sit at a fixed stride in the ROM.
//
// QDQ8 / QDQ4 (qdq_fp8 / qdq_fp4_e8m0 through ot_hdc_actquant's dequantised
// output) and QDQ4E (qdq_fp4_e4m3, block 16, ot_hdc_fp4qdq) write the BF16
// quantise-dequantise of nb blocks, one 32-element word per cycle.
//
// Faults (a NaN code, a scaled block past the binary32 range, a nonfinite
// activation) are ORed into a registered status bit.
// ---------------------------------------------------------------------------
module ot_hdc_v41_qe #(
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer BL = 16,
    parameter integer IL = 8,
    parameter integer NBMAX = 32,
    parameter integer QLB = 272              // bits per lane in a weight word: 32 codes, 16-bit exponent
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [1:0]        i_mode,
    input  wire              i_fp4,
    input  wire [AW-1:0]     i_xbase,
    input  wire [7:0]        i_nb,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [AW-1:0]     i_wbase,
    input  wire              i_ind,
    input  wire [AW-1:0]     i_ibase,
    input  wire [AW-1:0]     i_istride,
    input  wire [AW-1:0]     i_obase,
    // vector memory: index read, 32-element read, masked 32-element write
    output reg               vi_re,
    output reg  [AW-1:0]     vi_addr,
    input  wire [31:0]       vi_q,
    output reg               xr_re,
    output reg  [AW-1:0]     xr_addr,
    input  wire [1023:0]     xr_q,
    output reg               w_we,
    output reg  [AW-1:0]     w_addr,
    output reg  [31:0]       w_mask,
    output reg  [1023:0]     w_data,
    // quantised weight ROM
    output reg               qr_re,
    output reg  [AW-1:0]     qr_addr,
    input  wire [BL*QLB-1:0] qr_q,
    output reg               fault
);
    localparam [1:0] LINQ = 0, QDQ8 = 1, QDQ4 = 2, QDQ4E = 3;
    localparam [2:0] S_IDLE = 0, S_IDX = 1, S_IDXW = 2, S_LOAD = 3, S_ALIGN = 4, S_ROWS = 5, S_DRAIN = 6;
    localparam integer PW = $clog2(IL);
    reg [2:0]    st;
    reg [1:0]    mode;
    reg          fp4;
    reg [AW-1:0] xbase, wbase, obase, ibase, istride;
    reg [7:0]    nb;
    reg [NW-1:0] nout, tiles;
    reg [7:0]    rd_n, got_n;          // blocks read / quantised
    reg [31:0]   wn, wtotal;           // weight words issued
    reg [NW+PW:0] oc, otot;            // results written
    reg [1:0]    iw;
    assign ready = (st == S_IDLE);
    wire accept = go && ready;
    wire [PW-1:0] phase;

    // -- control --------------------------------------------------------------------------
    wire aq_vo, fq_vo;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; vi_re <= 0; xr_re <= 0; qr_re <= 0;
        end else begin
            vi_re <= 0; xr_re <= 0; qr_re <= 0;
            case (st)
                S_IDLE: if (go) begin
                    mode <= i_mode; fp4 <= i_fp4; xbase <= i_xbase; wbase <= i_wbase; obase <= i_obase;
                    ibase <= i_ibase; istride <= i_istride; nb <= i_nb; nout <= i_nout; tiles <= i_tiles;
                    rd_n <= 0; got_n <= 0; wn <= 0; oc <= 0;
                    wtotal <= i_tiles * i_nb * IL; otot <= i_tiles * IL;
                    st <= i_ind ? S_IDX : S_LOAD;
                end
                S_IDX: begin vi_re <= 1'b1; vi_addr <= ibase; iw <= 0; st <= S_IDXW; end
                S_IDXW: begin
                    iw <= iw + 1'b1;
                    if (iw == 2'd1) begin wbase <= wbase + vi_q[AW-1:0] * istride; st <= S_LOAD; end
                end
                S_LOAD: begin
                    if (rd_n != nb) begin
                        xr_re <= 1'b1; xr_addr <= xbase + {rd_n, 5'd0}; rd_n <= rd_n + 1'b1;
                    end
                    if (got_n == nb) st <= (mode == LINQ) ? S_ALIGN : S_DRAIN;
                end
                //: the word issued at cycle c reaches the lanes at c+3, which must be phase 0:
                //: leave on phase IL-4, so the first word issues on phase IL-3
                S_ALIGN: if (phase == IL - 4) st <= S_ROWS;
                S_ROWS: begin
                    qr_re <= 1'b1; qr_addr <= wbase + wn[AW-1:0]; wn <= wn + 1;
                    if (wn + 1 == wtotal) st <= S_DRAIN;
                end
                S_DRAIN: if ((mode == LINQ) ? (oc == otot && !w_we) : !pend) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
            if (l_ov[0] && mode == LINQ) oc <= oc + 1'b1;
            if (st == S_LOAD && got_ev) got_n <= got_n + 1'b1;
        end
    end

    // -- activation quantiser and FP4 (E4M3 scale) QDQ ---------------------------------------
    reg  x_v;
    reg  [7:0] x_b;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) x_v <= 1'b0; else x_v <= xr_re;
    end
    always @(posedge clk) if (xr_re) x_b <= rd_n;
    // xr_q is valid the cycle after xr_re (synchronous read registered at that edge)
    wire [255:0] aq_q;
    wire signed [9:0] aq_e;
    wire [511:0] aq_y, fq_y;
    wire aq_f, fq_f;
    ot_hdc_actquant u_aq (.clk(clk), .rst_n(rst_n), .v(x_v && mode != QDQ4E), .fp4(mode == QDQ4), .x(xr_q),
                          .vo(aq_vo), .q(aq_q), .e(aq_e), .y(aq_y), .fault(aq_f));
    ot_hdc_fp4qdq u_fq (.clk(clk), .rst_n(rst_n), .v(x_v && mode == QDQ4E), .x(xr_q), .vo(fq_vo), .y(fq_y),
                        .fault(fq_f));
    wire got_ev = aq_vo || fq_vo;
    reg [7:0] qb;                       // block index of the quantiser's output
    always @(posedge clk) if (st == S_IDLE) qb <= 0; else if (got_ev) qb <= qb + 1'b1;
    reg [255:0] xq_buf [0:NBMAX-1];
    reg signed [9:0] xe_buf [0:NBMAX-1];
    always @(posedge clk) if (aq_vo) begin xq_buf[qb[$clog2(NBMAX)-1:0]] <= aq_q; xe_buf[qb[$clog2(NBMAX)-1:0]] <= aq_e; end
    wire pend = (rd_n != got_n) || x_v || w_we;
    // QDQ writes
    function automatic [1023:0] widen(input [511:0] y);
        integer k;
        begin
            for (k = 0; k < 32; k = k + 1) widen[32*k +: 32] = {y[16*k +: 16], 16'h0000};
        end
    endfunction

    // -- block-dot lanes --------------------------------------------------------------------------
    // stream counters (kb, j) of the issued word, 2 cycles to the lanes' inputs
    reg [7:0]    kb_c;
    reg [PW-1:0] j_c;
    reg          iv0, iv1;
    reg [7:0]    kb0, kb1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv0 <= 0; iv1 <= 0; end
        else begin iv0 <= (st == S_ROWS); iv1 <= iv0; end
    end
    always @(posedge clk) begin
        if (st == S_ALIGN) begin kb_c <= 0; j_c <= 0; end
        else if (st == S_ROWS) begin
            j_c <= j_c + 1'b1;
            if (j_c == IL - 1) kb_c <= (kb_c + 1 == nb) ? 8'd0 : kb_c + 1'b1;
        end
        kb0 <= kb_c; kb1 <= kb0;
    end
    reg          b_v, b_first, b_last, b_fp4;
    reg [255:0]  b_xq;
    reg signed [9:0] b_xe;
    reg [BL*QLB-1:0] b_w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) b_v <= 1'b0; else b_v <= iv1;
    end
    always @(posedge clk) begin
        b_first <= (kb1 == 0); b_last <= (kb1 + 1 == nb); b_fp4 <= fp4;
        b_xq <= xq_buf[kb1[$clog2(NBMAX)-1:0]]; b_xe <= xe_buf[kb1[$clog2(NBMAX)-1:0]];
        b_w <= qr_q;
    end
    wire [BL-1:0] l_ov, l_f;
    wire [16*BL-1:0] l_y;
    wire [PW-1:0] ph [0:BL-1];
    genvar l;
    generate
        for (l = 0; l < BL; l = l + 1) begin : g_lane
            wire [31:0] acc_unused;
            ot_hdc_blockdot #(.IL(IL)) u_bd (.clk(clk), .rst_n(rst_n), .v(b_v), .first(b_first), .last(b_last),
                .fp4(b_fp4), .xq(b_xq), .xe(b_xe), .wq(b_w[QLB*l +: 256]), .we(b_w[QLB*l + 256 +: 10]),
                .phase(ph[l]), .ov(l_ov[l]), .y(l_y[16*l +: 16]), .acc(acc_unused), .fault(l_f[l]));
        end
    endgenerate
    assign phase = ph[0];

    // -- writes -------------------------------------------------------------------------------------
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) w_we <= 1'b0;
        else w_we <= (mode == LINQ) ? l_ov[0] : ((aq_vo || fq_vo) && mode != LINQ);
    end
    reg [7:0] wb_i;
    always @(posedge clk) if (st == S_IDLE) wb_i <= 0; else if ((aq_vo || fq_vo) && mode != LINQ) wb_i <= wb_i + 1'b1;
    always @(posedge clk) begin
        if (mode == LINQ) begin
            w_addr <= obase + oc * BL;
            for (k = 0; k < 32; k = k + 1) begin
                w_mask[k] <= (k < BL) && (oc * BL + k < nout);
                w_data[32*k +: 32] <= (k < BL) ? {l_y[16*k +: 16], 16'h0000} : 32'd0;
            end
        end else begin
            w_addr <= obase + {wb_i, 5'd0};
            w_mask <= 32'hFFFFFFFF;
            w_data <= widen(fq_vo ? fq_y : aq_y);
        end
    end

    // -- status ---------------------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= (st == S_IDLE) && !accept && !w_we;
    end
    reg f_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin f_q <= 1'b0; fault <= 1'b0; end
        else begin
            f_q <= (aq_vo && aq_f) | (fq_vo && fq_f) | (|(l_ov & l_f));
            fault <= f_q;
        end
    end
endmodule
