`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// XU ADAPTER of the re-specified V4.1 decode core (ot_hdc_core_v41x): the as-built
// auxiliary unit ot_hdc_v41_xu recomposed, port for port and op for op (go / ready /
// idle, i_op / src / dst / n / k / layer, token / first / i_hslot, rst_v / rst_slot,
// sel_first, prime_*, the vector-memory, constant-ROM and Engram-ROM ports), with two
// of its four ops moved onto the re-specified engines:
//
//   SEL      (X_SEL, and only an INDEX-score select: i_bf16)  ot_hdc_v41x_sel, the
//            streaming exact filter + threshold select, Q quarters x SW lanes of BF16
//            scores a cycle.  The n scores at src are cut into Q contiguous ranges of
//            R = SW * ceil(n / (Q*SW)) positions; quarter q streams its range on port q,
//            one SW-lane beat a cycle read from the vector memory through its own
//            SW-element read port (vsl_*), the last beat masked; an empty quarter sends
//            one empty last beat.  The select's line memories (1R1W, one per quarter) are
//            here.  Its output (per quarter, packed, position order; the concatenation
//            in quarter order is the selection) is written as masked words at dst + the
//            running count; sel_first is the first index written (TOKX latches it).  On
//            the overflow fallback (rep_req) the whole segment is streamed again.
//            A SELECT whose count is STATIC (i_bf16 = 0: the router's top-k over FP32
//            biased scores, a draft's top-1 over FP32 logits) keeps the as-built FP32
//            streaming select ot_hdc_select: the re-specified select takes BF16 keys, and
//            only the index scores are BF16 (red_rnd).  An index-score value whose low 16
//            bits are not zero faults (fail closed).
//   EGATHER  (X_EG)  the per-bank Engram gather: ENG_COLS column-bank slices
//            ot_hdc_v41x_egather_slice (one per hash column; the reduced vehicle's 32-code
//            rows are BEATS = 1) and the consuming die's assembler ot_hdc_v41x_egather_asm
//            (a token slot per op, NL = 1 layer, NC = ENG_COLS columns).  The EGATHER's row
//            ids (the Engram hash's rows of layer i_layer, plus the layer table's base src)
//            go to slice c in cycle c of the op, so the slices' ROM reads (a fixed request
//            -> read latency) leave one per cycle; here the Engram table ROM er_* stands in
//            for the 24 column-bank ROMs (one read a cycle, answered in order, a read tag
//            routes the data back to its slice).  The as-built ROM carries the row scale as
//            a signed exponent; the slice takes UE8M0 (value = E4M3 x 2^(scale - 127)), so the
//            side byte passes as exponent + 127.  Beats merge onto the assembler's one input
//            by a fixed-priority arbiter (any order is legal); the assembler writes each row
//            as 32 BF16 into the vector memory at dst + 32 * column (as {bf16, 16'h0}
//            binary32: the as-built gather's exact values).  A code / scale the as-built
//            gather refuses (NaN code, a value outside the normal binary32 range) faults.
//   SINK, EHASH: as built (ot_hdc_sinkhorn_mc / ot_hdc_engram_hash).
//
// X_SEL = 0 / X_EG = 0 keep the as-built SELECT / gather inside this adapter.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_xu_adapt #(
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer K = 16,              // the as-built FP32 select's k
    parameter integer SK_STEP = 7,
    parameter integer X_SEL = 1,
    parameter integer X_EG = 1,
    parameter integer SQ = 4,              // re-specified select: quarters
    parameter integer SW = 16,             //   lanes per quarter
    parameter integer SK = 512,            //   largest k
    parameter integer SLAW = 8             //   line-memory address width per quarter
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
    input  wire              i_bf16,          // SEL: an index-score select (dynamic count, BF16 scores)
    input  wire [NW-1:0]     token,
    input  wire              first,
    input  wire [2:0]        i_hslot,
    input  wire              rst_v,
    input  wire [2:0]        rst_slot,
    output reg  [15:0]       sel_first,
    input  wire              prime_v,
    input  wire              prime_first,
    input  wire [11:0]       prime_cid,
    output reg               vr_re,
    output reg  [AW-1:0]     vr_addr,
    input  wire [31:0]       vr_q,
    output reg               xr_re,
    output reg  [AW-1:0]     xr_addr,
    input  wire [1023:0]     xr_q,
    // the re-specified select's score reads: SQ ports of SW consecutive elements
    output reg  [SQ-1:0]     vsl_re,
    output reg  [SQ*AW-1:0]  vsl_addr,
    input  wire [SQ*SW*32-1:0] vsl_q,
    output reg               vw_we,
    output reg  [AW-1:0]     vw_addr,
    output reg  [31:0]       vw_data,
    output reg               w_we,
    output reg  [AW-1:0]     w_addr,
    output reg  [31:0]       w_mask,
    output reg  [1023:0]     w_data,
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
                     S_EHW = 8, S_EG = 9, S_EGW = 10, S_EHC = 11,
                     S_XS0 = 12, S_XS1 = 13, S_XSW = 14, S_XEG = 15;
    localparam integer KW = $clog2(K + 1);
    localparam integer SKW = $clog2(SK + 1);
    localparam integer IW = 20;
    localparam integer EW = 17 + IW;
    localparam integer LSW = $clog2(SW);
    localparam integer LQ = $clog2(SQ);
    reg [3:0]    st;
    reg [1:0]    op;
    reg [AW-1:0] src, dst;
    reg [NW-1:0] n, ni, nw;
    reg [4:0]    k;
    reg          layer;
    reg [NW-1:0] tok_l;
    reg          first_l;
    reg [2:0]    hslot;
    reg [5:0]    cnt;
    wire         x_busy;
    assign ready = (st == S_IDLE) && !sel_busy && !x_busy;
    wire accept = go && ready;

    // -- as-built SELECT (FP32) ---------------------------------------------------------------------
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

    // -- Sinkhorn (as built) -----------------------------------------------------------------------
    reg          sk_in;
    wire         sk_ready, sk_ov, sk_f, sk_busy;
    wire [511:0] sk_y;
`ifdef HDC_SINKHORN_SEQ
    ot_hdc_sinkhorn_seq u_sk (.clk(clk), .rst_n(rst_n), .in_valid(sk_in), .in_ready(sk_ready),
        .in_e(xr_q[511:0]), .out_valid(sk_ov), .y(sk_y), .fault(sk_f), .busy(sk_busy));
`else
    ot_hdc_sinkhorn_mc #(.STEP_CYC(SK_STEP)) u_sk (.clk(clk), .rst_n(rst_n), .req(sk_in), .in_e(xr_q[511:0]),
        .busy(sk_busy), .done(sk_ov), .y(sk_y), .fault(sk_f));
`endif

    // -- Engram hash (as built) --------------------------------------------------------------------
    reg          h_v, h_first;
    reg [11:0]   h_cid;
    wire         h_ov;
    wire [ENG_ROW_W*ENG_LAYERS*ENG_COLS-1:0] h_rows;
    reg  [ENG_ROW_W*ENG_LAYERS*ENG_COLS-1:0] rows;
    wire [ENG_ID_W*(ENG_N-1)-1:0] h_hist;
    reg  [ENG_ID_W*(ENG_N-1)-1:0] snap [0:7];
    ot_hdc_engram_hash u_hash (.clk(clk), .rst_n(rst_n), .in_valid(h_v || (prime_v && st == S_IDLE)),
        .in_first(h_v ? h_first : prime_first), .in_cid(h_v ? h_cid : prime_cid),
        .hist_o(h_hist), .ld_v(rst_v && st == S_IDLE && !h_v), .ld_hist(snap[rst_slot]), .out_valid(h_ov),
        .out_row(h_rows));

    // -- the as-built gather's decode (the values; here also the re-specified path's fault check) ----
    function automatic [32:0] deq(input [7:0] c, input signed [7:0] sc);   // {bad, value}
        reg signed [10:0] e;
        reg [2:0] m;
        reg [22:0] f;
        begin
            m = c[2:0];
            if (c[6:0] == 7'h7F) deq = {1'b1, 32'd0};
            else if (c[6:3] == 4'd0 && m == 3'd0) deq = {1'b0, c[7], 31'd0};
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

    // ================================================================= re-specified SELECT
    wire [SQ-1:0]      xs_in_ready, xs_out_valid, xs_out_last, xs_mem_we, xs_mem_re;
    wire [SQ*SW-1:0]   xs_out_lv, xs_out_ninf;
    wire [SQ*SW*16-1:0] xs_out_val;
    wire [SQ*SW*IW-1:0] xs_out_idx;
    wire [SQ*SLAW-1:0] xs_mem_waddr, xs_mem_raddr;
    wire [SQ*SW*EW-1:0] xs_mem_wdata;
    reg  [SQ*SW*EW-1:0] xs_mem_rdata;
    wire               xs_rep, xs_ovf, xs_busy;
    reg  [SQ-1:0]      xs_v, xs_l;                 // the beat at the select's input
    reg  [SQ*SW-1:0]   xs_lv;
    reg  [SQ*SW*IW-1:0] xs_idx;
    reg  [SQ-1:0]      xr1_v, xr1_l;               // beat whose read is in flight
    reg  [SQ*SW-1:0]   xr1_lv;
    reg  [SQ*SW*IW-1:0] xr1_idx;
    reg  [SKW-1:0]     xs_k;
    reg  [NW-1:0]      xs_nb, xs_b;                // beats per full quarter; the beat being read
    reg  [NW-1:0]      xs_R;                       // positions per quarter
    reg  [SQ-1:0]      xs_qo;                      // (one-hot of the quarter being written)
    reg  [LQ:0]        xs_q;
    reg                xs_pass;                    // a stream pass is running
    reg                xs_bad;
    wire [SQ*SW*16-1:0] xs_val;
    genvar gq, gl;
    generate for (gq = 0; gq < SQ; gq = gq + 1) begin : g_xv
        for (gl = 0; gl < SW; gl = gl + 1) begin : g_l
            assign xs_val[16*(SW*gq + gl) +: 16] = vsl_q[32*(SW*gq + gl) + 16 +: 16];
        end
    end endgenerate
    generate if (X_SEL != 0) begin : g_xsel
        ot_hdc_v41x_sel #(.Q(SQ), .W(SW), .IW(IW), .K(SK), .AW(SLAW)) u_xsel (.clk(clk), .rst_n(rst_n),
            .in_valid(xs_v), .in_ready(xs_in_ready), .in_last(xs_l), .in_lv(xs_lv), .in_val(xs_val),
            .in_idx(xs_idx), .in_k(xs_k),
            .out_valid(xs_out_valid), .out_ready(xs_qo & {SQ{st == S_XSW}}), .out_last(xs_out_last),
            .out_lv(xs_out_lv), .out_val(xs_out_val), .out_idx(xs_out_idx), .out_ninf(xs_out_ninf),
            .mem_we(xs_mem_we), .mem_waddr(xs_mem_waddr), .mem_wdata(xs_mem_wdata), .mem_re(xs_mem_re),
            .mem_raddr(xs_mem_raddr), .mem_rdata(xs_mem_rdata), .rep_req(xs_rep), .ovf(xs_ovf), .busy(xs_busy),
            .stats());
        // the line memories: one 1R1W synchronous-read memory per quarter
        reg [SW*EW-1:0] lm [0:SQ*(1<<SLAW)-1];
        integer mq;
        always @(posedge clk)
            for (mq = 0; mq < SQ; mq = mq + 1) begin
                if (xs_mem_we[mq]) lm[mq * (1 << SLAW) + xs_mem_waddr[SLAW*mq +: SLAW]] <= xs_mem_wdata[SW*EW*mq +: SW*EW];
                if (xs_mem_re[mq]) xs_mem_rdata[SW*EW*mq +: SW*EW] <= lm[mq * (1 << SLAW) + xs_mem_raddr[SLAW*mq +: SLAW]];
            end
    end else begin : g_nxsel
        assign xs_in_ready = {SQ{1'b1}}; assign xs_out_valid = 0; assign xs_out_last = 0; assign xs_out_lv = 0;
        assign xs_out_val = 0; assign xs_out_idx = 0; assign xs_out_ninf = 0; assign xs_mem_we = 0;
        assign xs_mem_re = 0; assign xs_mem_waddr = 0; assign xs_mem_raddr = 0; assign xs_mem_wdata = 0;
        assign xs_rep = 1'b0; assign xs_ovf = 1'b0; assign xs_busy = 1'b0;
    end endgenerate
    // beat b of quarter q: positions q*R + b*SW + l; lanes below n; the quarter's beats
    function automatic [NW:0] qbeats(input [NW-1:0] nn, input [NW-1:0] R, input integer q);
        reg [NW+1:0] lo, len;
        begin
            lo = q * R;
            len = (nn > lo) ? ((nn - lo > R) ? R : nn - lo) : 0;
            qbeats = (len == 0) ? 1 : (len + SW - 1) >> LSW;
        end
    endfunction

    // ================================================================= re-specified gather
    localparam integer NC = ENG_COLS;
    localparam integer ETAG = 1 + 1 + 5 + 1 + 8;   // {slot, layer, column, beat, scale}
    wire [NC-1:0]       eq_ready, esl_re, esl_bv;
    reg  [NC-1:0]       eq_v, esl_bready;
    reg  [NC-1:0]       esl_rv;
    wire [NC*(AW+1)-1:0] esl_addr;
    wire [NC*256-1:0]   esl_bd;
    wire [NC*ETAG-1:0]  esl_bt;
    reg  [263:0]        erd;                       // the ROM word, side byte as UE8M0
    wire                ea_tok_ready, ea_bready, ea_wv, ea_fault;
    wire [0:0]          ea_tok_tag;
    wire [$clog2(2*NC)-1:0] ea_waddr;
    wire [511:0]        ea_wdata;
    wire [1:0]          ea_rdy;
    reg                 ea_tok_v, ea_rel_v;
    reg  [0:0]          eslot;
    reg  [4:0]          ec;                         // request column
    reg                 e_coll;
    reg  [4:0]          e_rid1, e_rid2;             // ROM read tag (slice) in flight
    reg                 e_rv1, e_rv2;
    // beat arbitration: the lowest-numbered slice with a beat
    reg  [4:0]          e_g;
    reg                 e_any;
    integer ci;
    always @(*) begin
        e_any = 1'b0; e_g = 5'd0;
        for (ci = NC - 1; ci >= 0; ci = ci - 1) if (esl_bv[ci]) begin e_any = 1'b1; e_g = ci; end
        esl_bready = {NC{1'b0}};
        esl_bready[e_g] = ea_bready && e_any;
    end
    reg  [AW:0]         e_raddr;
    reg                 e_rre;
    always @(*) begin
        e_rre = |esl_re; e_raddr = {(AW+1){1'b0}};
        for (ci = 0; ci < NC; ci = ci + 1) if (esl_re[ci]) e_raddr = e_raddr | esl_addr[(AW+1)*ci +: AW+1];
    end
    reg  [4:0]          e_rsel;
    always @(*) begin
        e_rsel = 5'd0;
        for (ci = 0; ci < NC; ci = ci + 1) if (esl_re[ci]) e_rsel = ci;
    end
    generate if (X_EG != 0) begin : g_xeg
        genvar gc;
        for (gc = 0; gc < NC; gc = gc + 1) begin : g_slice
            ot_hdc_v41x_egather_slice #(.RW(AW), .AW(AW), .BEATS(1), .TW(1), .LW(1), .CW(5), .DQ(2)) u_slice (
                .clk(clk), .rst_n(rst_n), .cfg_base({AW{1'b0}}), .cfg_layer(1'b0), .cfg_col(gc),
                .req_valid(eq_v[gc]), .req_ready(eq_ready[gc]),
                .req_row(src + rows[ENG_ROW_W*(layer*ENG_COLS + gc) +: ENG_ROW_W]), .req_tag(eslot),
                .rom_re(esl_re[gc]), .rom_addr(esl_addr[(AW+1)*gc +: AW+1]), .rom_rvalid(esl_rv[gc]),
                .rom_rdata(erd), .b_valid(esl_bv[gc]), .b_ready(esl_bready[gc]), .b_data(esl_bd[256*gc +: 256]),
                .b_tag(esl_bt[ETAG*gc +: ETAG]));
        end
        ot_hdc_v41x_egather_asm #(.NL(1), .NC(NC), .BEATS(1), .TW(1), .LW(1), .CW(5)) u_asm (
            .clk(clk), .rst_n(rst_n), .tok_valid(ea_tok_v), .tok_ready(ea_tok_ready), .tok_tag(ea_tok_tag),
            .b_valid(e_any), .b_ready(ea_bready), .b_data(esl_bd[256*e_g +: 256]), .b_tag(esl_bt[ETAG*e_g +: ETAG]),
            .wr_valid(ea_wv), .wr_ready(1'b1), .wr_addr(ea_waddr), .wr_data(ea_wdata), .rdy(ea_rdy),
            .rel_valid(ea_rel_v), .rel_tag(eslot), .fault(ea_fault));
    end else begin : g_nxeg
        assign eq_ready = {NC{1'b1}}; assign esl_re = 0; assign esl_addr = 0; assign esl_bv = 0; assign esl_bd = 0;
        assign esl_bt = 0; assign ea_tok_ready = 1'b1; assign ea_tok_tag = 1'b0; assign ea_bready = 1'b0;
        assign ea_wv = 1'b0; assign ea_waddr = 0; assign ea_wdata = 0; assign ea_rdy = 2'b11; assign ea_fault = 1'b0;
    end endgenerate
    assign x_busy = xs_busy;

    reg flt;
    reg [4:0] eg_c;
    integer q, l;
    reg [NW-1:0] pc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; vr_re <= 0; xr_re <= 0; vw_we <= 0; w_we <= 0; cr_re <= 0; er_re <= 0;
            s_v <= 0; sk_in <= 0; h_v <= 0; flt <= 0; fault <= 0;
            vsl_re <= 0; xs_v <= 0; xs_l <= 0; xr1_v <= 0; xr1_l <= 0; xs_pass <= 1'b0;
            eq_v <= 0; ea_tok_v <= 1'b0; ea_rel_v <= 1'b0; e_rv1 <= 1'b0; e_rv2 <= 1'b0;
        end else begin
            vr_re <= 0; xr_re <= 0; vw_we <= 0; w_we <= 0; cr_re <= 0; er_re <= 0; h_v <= 0;
            vsl_re <= 0; eq_v <= 0; ea_rel_v <= 1'b0;
            if (sk_busy) sk_in <= 1'b0;
            s_v <= r1_v; s_last <= r1_last; s_idx <= r1_idx;
            r1_v <= 0;
            // re-specified select: the beat read last cycle reaches the select now
            xs_v <= xr1_v; xs_l <= xr1_l; xs_lv <= xr1_lv; xs_idx <= xr1_idx;
            xr1_v <= 0; xr1_l <= 0;
            fault <= flt;
            case (st)
                S_IDLE: if (accept) begin
                    op <= i_op; src <= i_src; dst <= i_dst; n <= i_n; k <= i_k; layer <= i_layer; ni <= 0; nw <= 0;
                    cnt <= 0; tok_l <= token; first_l <= first; hslot <= i_hslot;
                    case (i_op)
                        OP_SEL: st <= (X_SEL != 0 && i_bf16) ? S_XS0 : S_SEL;
                        OP_SINK: st <= S_SK0;
                        OP_EHASH: st <= S_EH0;
                        default: st <= (X_EG != 0) ? S_XEG : S_EG;
                    endcase
                end
                S_SEL: begin
                    vr_re <= 1'b1; vr_addr <= src + ni; ni <= ni + 1'b1;
                    r1_v <= 1'b1; r1_idx <= ni; r1_last <= (ni + 1 == n);
                    if (ni + 1 == n) st <= S_SELW;
                end
                S_SELW: if (nw == ((k > n) ? n : k) && !sel_busy) st <= S_IDLE;
                // -- re-specified select: set up, then stream passes, then write the quarters in order
                S_XS0: begin
                    xs_nb <= (n + SQ*SW - 1) >> (LQ + LSW);
                    xs_R <= ((n + SQ*SW - 1) >> (LQ + LSW)) << LSW;
                    xs_k <= (k > n) ? n : k;
                    xs_b <= 0; xs_q <= 0; xs_qo <= 1; xs_pass <= 1'b0;
                    st <= S_XS1;
                end
                S_XS1: begin
                    //: a pass starts when every quarter takes beats, and then streams one beat a cycle
                    if (!xs_pass && (&xs_in_ready) && !(|xr1_v) && !(|xs_v)) xs_pass <= 1'b1;
                    if (xs_pass) begin
                        for (q = 0; q < SQ; q = q + 1)
                            if (xs_b < qbeats(n, xs_R, q)) begin
                                vsl_re[q] <= 1'b1;
                                vsl_addr[AW*q +: AW] <= src + q * xs_R + (xs_b << LSW);
                                xr1_v[q] <= 1'b1;
                                xr1_l[q] <= (xs_b + 1 == qbeats(n, xs_R, q));
                                for (l = 0; l < SW; l = l + 1) begin
                                    pc = q * xs_R + (xs_b << LSW) + l;
                                    xr1_lv[SW*q + l] <= (pc < n) && (pc < (q + 1) * xs_R);
                                    xr1_idx[IW*(SW*q + l) +: IW] <= pc;
                                end
                            end
                        xs_b <= xs_b + 1'b1;
                        if (xs_b + 1 >= xs_nb) begin xs_pass <= 1'b0; st <= S_XSW; end
                    end
                end
                S_XSW: begin
                    if (xs_rep) begin xs_b <= 0; st <= S_XS1; end            // the overflow fallback: stream again
                    if (|(xs_out_valid & xs_qo)) begin
                        w_we <= 1'b1; w_addr <= dst + nw; w_mask <= 32'd0; w_data <= 1024'd0;
                        for (l = 0; l < SW; l = l + 1) begin
                            w_mask[l] <= xs_out_lv[SW*xs_q + l];
                            w_data[32*l +: 32] <= {{(32-IW){1'b0}}, xs_out_idx[IW*(SW*xs_q + l) +: IW]};
                        end
                        pc = 0;
                        for (l = 0; l < SW; l = l + 1) pc = pc + xs_out_lv[SW*xs_q + l];
                        nw <= nw + pc;
                        if (nw == 0 && xs_out_lv[SW*xs_q]) sel_first <= xs_out_idx[IW*SW*xs_q +: 16];
                        if (xs_out_last[xs_q]) begin
                            xs_qo <= xs_qo << 1; xs_q <= xs_q + 1'b1;
                            if (xs_q + 1 == SQ) st <= S_IDLE;
                        end
                    end
                end
                S_SK0: begin xr_re <= 1'b1; xr_addr <= src; st <= S_SK1; end
                S_SK1: begin cnt <= cnt + 1'b1; if (cnt == 6'd1) begin sk_in <= 1'b1; st <= S_SKW; end end
                S_SKW: if (sk_ov) begin
                    w_we <= 1'b1; w_addr <= dst; w_mask <= 32'h0000FFFF; w_data <= {512'd0, sk_y};
                    if (sk_f) flt <= 1'b1;
                    st <= S_IDLE;
                end
                S_EH0: begin cr_re <= 1'b1; cr_addr <= src + tok_l; st <= S_EH1; end
                S_EH1: begin cnt <= cnt + 1'b1; if (cnt == 6'd1) begin h_v <= 1'b1; h_cid <= cr_q[11:0]; h_first <= first_l; st <= S_EHW; end end
                S_EHW: if (h_ov) begin rows <= h_rows; snap[hslot] <= h_hist; st <= S_IDLE; end
                S_EG: begin
                    er_re <= 1'b1; er_addr <= src + rows[ENG_ROW_W*(layer*ENG_COLS + eg_c) +: ENG_ROW_W];
                    if (eg_c + 1 == ENG_COLS) st <= S_EGW;
                end
                S_EGW: begin cnt <= cnt + 1'b1; if (cnt == 6'd3) st <= S_IDLE; end
                // -- re-specified gather: a token slot, one row request per column a cycle, then the rows
                S_XEG: begin
                    case (cnt)
                        6'd0: begin
                            ea_tok_v <= 1'b1;
                            if (ea_tok_v && ea_tok_ready) begin
                                ea_tok_v <= 1'b0; eslot <= ea_tok_tag; ec <= 5'd0; cnt <= 6'd1;
                            end
                        end
                        6'd1: begin
                            if (eq_ready[ec]) begin
                                eq_v[ec] <= 1'b1;
                                ec <= ec + 1'b1;
                                if (ec + 1 == NC) cnt <= 6'd2;
                            end
                        end
                        default: if (ea_rdy[eslot] && !ea_wv && !w_we) begin
                            ea_rel_v <= 1'b1; st <= S_IDLE;
                        end
                    endcase
                end
                default: st <= S_IDLE;
            endcase
            if (so_v) begin
                vw_we <= 1'b1; vw_addr <= dst + nw; vw_data <= {16'd0, so_idx}; nw <= nw + 1'b1;
                if (nw == 0) sel_first <= so_idx;
            end
            if (s_v && !sel_ready) flt <= 1'b1;
            // re-specified select: a beat the select did not take, or a score that is not BF16
            for (q = 0; q < SQ; q = q + 1) begin
                if (xs_v[q] && !xs_in_ready[q]) flt <= 1'b1;
                for (l = 0; l < SW; l = l + 1)
                    if (xs_v[q] && xs_lv[SW*q + l] && vsl_q[32*(SW*q + l) +: 16] != 16'd0) flt <= 1'b1;
            end
            // as-built gathered rows: the ROM answers two cycles after the address
            if (eg_v1) begin
                w_we <= 1'b1; w_addr <= dst + {eg_i1, 5'd0}; w_mask <= 32'hFFFFFFFF;
                for (q = 0; q < 32; q = q + 1) begin
                    w_data[32*q +: 32] <= deq(er_q[8*q +: 8], er_q[263:256]);
                    if (deq(er_q[8*q +: 8], er_q[263:256]) >> 32) flt <= 1'b1;
                end
            end
            // re-specified gather: the slices' ROM reads (one a cycle; a collision faults), the data back
            if (e_rre) begin er_re <= 1'b1; er_addr <= e_raddr[AW:1]; end
            if ($countones(esl_re) > 1) flt <= 1'b1;
            //: a slice read registered here in cycle t is sampled by the ROM at the end of t+1 and its word is
            //: on er_q in t+2: the read tag rides two registers
            e_rv1 <= e_rre; e_rid1 <= e_rsel;
            e_rv2 <= e_rv1; e_rid2 <= e_rid1;
            if (e_rv2) begin
                for (q = 0; q < 32; q = q + 1) if (deq(er_q[8*q +: 8], er_q[263:256]) >> 32) flt <= 1'b1;
                if ($signed(er_q[263:256]) == -8'sd128) flt <= 1'b1;
            end
            if (ea_wv) begin
                w_we <= 1'b1; w_addr <= dst + {ea_waddr - eslot * NC, 5'd0}; w_mask <= 32'hFFFFFFFF;
                for (q = 0; q < 32; q = q + 1) w_data[32*q +: 32] <= {ea_wdata[16*q +: 16], 16'h0000};
            end
            if (ea_fault) flt <= 1'b1;
        end
    end
    // -- activation counters (bench only: the proof the re-specified paths ran) -------------------
    //   sel: ops run on ot_hdc_v41x_sel, scores it ingested on the FIRST pass (valid lanes accepted),
    //        and whole-segment replays (the overflow fallback)
    //   eg:  ops run on the per-bank gather, rows the assembler wrote (one word per row: BEATS = 1)
    reg [31:0] dbg_sel_ops, dbg_sel_elems, dbg_sel_reps, dbg_eg_ops, dbg_eg_elems;
    reg        xs_first;
    integer    cq, cl;
    reg [31:0] xs_acc;
    always @(*) begin
        xs_acc = 0;
        for (cq = 0; cq < SQ; cq = cq + 1)
            if (xs_v[cq] && xs_in_ready[cq])
                for (cl = 0; cl < SW; cl = cl + 1) xs_acc = xs_acc + xs_lv[SW*cq + cl];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dbg_sel_ops <= 0; dbg_sel_elems <= 0; dbg_sel_reps <= 0; dbg_eg_ops <= 0; dbg_eg_elems <= 0;
            xs_first <= 1'b0;
        end else begin
            if (st == S_XS0) begin dbg_sel_ops <= dbg_sel_ops + 1; xs_first <= 1'b1; end
            if (st == S_XSW && xs_rep) begin dbg_sel_reps <= dbg_sel_reps + 1; xs_first <= 1'b0; end
            if (xs_first) dbg_sel_elems <= dbg_sel_elems + xs_acc;
            if (st == S_IDLE && accept && i_op == OP_EGATHER && X_EG != 0) dbg_eg_ops <= dbg_eg_ops + 1;
            if (ea_wv) dbg_eg_elems <= dbg_eg_elems + 1;
        end
    end

    //: the slice data: the ROM word of the read answered, its side byte (a signed exponent) as UE8M0
    always @(*) begin
        erd = {er_q[263:256] + 8'd127, er_q[255:0]};
        esl_rv = {NC{1'b0}};
        esl_rv[e_rid2] = e_rv2;
    end
    always @(posedge clk) begin
        if (st == S_IDLE) eg_c <= 0; else if (st == S_EG) eg_c <= eg_c + 1'b1;
    end
    reg eg_v1, eg_v2;
    reg [4:0] eg_i1, eg_i2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin eg_v1 <= 0; eg_v2 <= 0; end
        else begin eg_v1 <= er_re && (st == S_EG || st == S_EGW); eg_v2 <= eg_v1; end
    end
    always @(posedge clk) begin eg_i1 <= eg_c - 1'b1; eg_i2 <= eg_i1; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= (st == S_IDLE) && !accept && !sel_busy && !xs_busy && !vw_we && !w_we && !sk_busy && !sk_in &&
                     !eg_v1 && !eg_v2;
    end
endmodule
