`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SM element of the GPU-organised HBM comparator (Qwen3-8B INT8; V4.1 BF16
// matrices): SUB sub-partitions of an exact tensor core, LS lanes each, NC
// columns (tokens of a verify block / users), the x store, the row-scale
// store, the cross-sub-partition tree, one streaming stack and one row-scale
// multiplier per column, and the barrier arrive/release handshake.
//
// Exactness (tools/hdc_golden.py matvec / hdc_golden_v41.csum): an op is
// R rows x K, K cut into C golden chunks of c contiguous elements (Qwen:
// C = split, c = K / split; V4.1 BF16: c = 8, C = ceil(K / 8)); lane j of the
// SM (sub-partition j / LS) holds chunk g * L + j of its slot's row in group g
// (L = SUB * LS), so the LS-leaf column trees and the SUB-leaf combine tree
// are the golden tree's bottom log2(L) levels and the stack continues it over
// the G = ceil(C / L) groups.  Lanes past C in the last group carry +0 (the
// golden's pad).  A row's whole K and tree stay in this SM.
//
// Schedule (row-slot): IL = 8 slots, slot s holds row  rb * 8 + s;  the
// weight stream is the lockstep order  rb, g, t, s  of L-weight lines, one
// line per cycle, pre-swizzled in HBM (weights are static).  The issue slot
// is the free-running phase; a line that is not there when its slot comes
// round waits one revolution (the order is fixed, so later slots wait too).
//
// Barrier: `arrive` toggles when the op's last row has left the stack and
// been scaled (the SM's results are committed); `release` toggling from the
// barrier network lets the next op start (ot_gpu_barrier_node).
// ---------------------------------------------------------------------------
module ot_gpu_sm #(
    parameter integer SUB   = 4,
    parameter integer LS    = 32,
    parameter integer NC    = 2,
    parameter integer IL    = 8,
    parameter integer XDEPTH = 96,     // x store words (K_max / L); Qwen K 12,288 / 128 = 96
    parameter integer RMAX  = 4096,    // rows per SM op
    parameter integer LEV   = 5,       // stack levels (G <= 32)
    parameter integer INT8  = 1        // 1: weight bytes are INT8 codes; 0: weight halfwords are BF16
) (
    input  wire                    clk,
    input  wire                    rst_n,
    // op descriptor, sampled at start
    input  wire                    start,
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,        // chunk length (k-steps per group)
    input  wire [7:0]              op_g,        // groups per row
    input  wire                    op_gs,       // group-slot issue (ot_gpu_issue)
    input  wire                    op_scale,    // multiply by the BF16 row scale
    output wire                    busy,
    // weight stream (bulk-copy staging): one L-weight line per cycle
    input  wire                    w_valid,
    output wire                    w_ready,
    input  wire [SUB*LS*(INT8 ? 8 : 16)-1:0] w_data,
    // x store and row-scale store write ports
    input  wire                    xw_en,
    input  wire [$clog2(XDEPTH)-1:0] xw_addr,
    input  wire [SUB*LS*NC*16-1:0] xw_data,     // [col][lane] BF16
    input  wire                    sw_en,
    input  wire [$clog2(RMAX)-1:0] sw_addr,
    input  wire [15:0]             sw_data,
    // results: one row, all columns
    output reg                     rv,
    output reg  [$clog2(RMAX)-1:0] rrow,
    output reg  [NC*32-1:0]        rdata,
    output reg                     fault,
    // barrier network
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released
);
    localparam integer MLAT = 7;                    // row-scale multiply depth (ot_gpu_fmul)
    localparam integer L   = SUB * LS;
    localparam integer SW  = $clog2(IL);
    localparam integer RW  = $clog2(RMAX);
    localparam integer XW  = $clog2(XDEPTH);
    localparam integer WB  = INT8 ? 8 : 16;
    localparam integer TAGW = RW + 1 + SW;        // {row, group-last, slot}

    // ---------------- issue sequencer ----------------
    reg         scale_q;
    wire        sv;                                // a scaled row result leaves (below)
    wire        adv, row_ok, i_first, i_last, i_glast;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [XW-1:0] xa;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) scale_q <= 1'b0;
        else if (start && !busy) scale_q <= op_scale;
    ot_gpu_issue #(.IL(IL), .RMAX(RMAX), .XDEPTH(XDEPTH)) u_issue (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(op_gs),
        .w_valid(w_valid), .x_rdy(1'b1), .w_ready(w_ready), .rdone(sv), .busy(busy), .iss_v(adv), .iss_row_ok(row_ok),
        .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last), .iss_glast(i_glast), .iss_rev_end(),
        .xa(xa), .arrive(arrive), .release_in(release_in), .released(released));

    // ---------------- x store (one word = every lane's x for every column at one (g, t)) ----------------
    reg [L*NC*16-1:0] xmem [0:XDEPTH-1];
    always @(posedge clk) if (xw_en) xmem[xw_addr] <= xw_data;
    // ---------------- row-scale store ----------------
    reg [15:0] smem [0:RMAX-1];
    always @(posedge clk) if (sw_en) smem[sw_addr] <= sw_data;

    // ---------------- issue stage: weight decode, x read ----------------
    function automatic [15:0] i8_bf16(input [7:0] code);
        reg s; reg [7:0] m; reg [2:0] msb; reg [7:0] nrm; integer b;
        begin
            s = code[7];
            m = s ? (~code + 8'd1) : code;
            msb = 3'd0;
            for (b = 0; b < 8; b = b + 1) if (m[b]) msb = b[2:0];
            nrm = m << (3'd7 - msb);
            i8_bf16 = (m == 8'd0) ? 16'd0 : {s, 8'd127 + {5'd0, msb}, nrm[6:0]};
        end
    endfunction
    reg              iv, ifirst, ilast;
    reg [TAGW-1:0]   itag;
    reg [L*16-1:0]   iw;
    reg [L*NC*16-1:0] ix;
    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv <= 1'b0; ifirst <= 1'b0; ilast <= 1'b0; end
        else begin
            iv <= adv && row_ok;
            ifirst <= i_first;
            ilast <= i_last;
        end
    end
    always @(posedge clk) begin
        itag <= {row_now[RW-1:0], i_glast, si};
        ix <= xmem[xa];
        for (j = 0; j < L; j = j + 1)
            iw[16*j +: 16] <= INT8 ? i8_bf16(w_data[8*j +: 8]) : w_data[WB*j +: 16];
    end

    // ---------------- columns: SUB column macros each, combine tree, stack, scale ----------------
    wire [NC-1:0] cv, cf;
    wire [NC*32-1:0] cy;
    wire [NC*TAGW-1:0] ctag;
    genvar col, sp;
    generate for (col = 0; col < NC; col = col + 1) begin : g_col
        wire [SUB-1:0] sov, sfault;
        wire [SUB*32-1:0] sy;
        wire [SUB*TAGW-1:0] stag;
        for (sp = 0; sp < SUB; sp = sp + 1) begin : g_sub
            wire [LS*16-1:0] xs;
            for (genvar q = 0; q < LS; q = q + 1) begin : g_x
                assign xs[16*q +: 16] = ix[(col * L + sp * LS + q) * 16 +: 16];
            end
            ot_gpu_tc_col #(.L(LS), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[sp*LS*16 +: LS*16]), .x(xs),
                .ov(sov[sp]), .y(sy[32*sp +: 32]), .otag(stag[TAGW*sp +: TAGW]), .fault(sfault[sp]));
        end
        wire tv, tf;
        wire [31:0] ty;
        wire [TAGW-1:0] tt;
        ot_gpu_tree #(.N(SUB), .TAGW(TAGW), .ALAT(8)) u_comb (.clk(clk), .rst_n(rst_n), .v(sov[0]), .d(sy),
                                                  .tag(stag[TAGW-1:0]), .ov(tv), .y(ty), .otag(tt), .fault(tf));
        wire kv, kf;
        wire [31:0] ky;
        wire [RW-1:0] krow;
        ot_gpu_stack #(.LEV(LEV), .IL(IL), .TAGW(RW), .ALAT(8)) u_stack (
            .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
            .itag(tt[TAGW-1:SW+1]), .ov(kv), .y(ky), .otag(krow), .fault(kf));
        assign cv[col] = kv;
        assign cy[32*col +: 32] = ky;
        assign ctag[TAGW*col +: TAGW] = {krow, 1'b0, {SW{1'b0}}};
        assign cf[col] = (|sfault) | tf | kf;
    end endgenerate

    // row scale: one FP32 x BF16 multiply per column after the whole tree (ot_hdc_qwen_int8_arith order)
    wire [RW-1:0] krow0 = ctag[TAGW-1:SW+1];
    reg  [15:0] ksc;
    reg  [NC*32-1:0] ky_q;
    reg  kv_q;
    reg  [RW-1:0] krow_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) kv_q <= 1'b0;
        else kv_q <= cv[0];
    always @(posedge clk) begin
        ksc <= smem[krow0];
        ky_q <= cy;
        krow_q <= krow0;
    end
    wire [NC*32-1:0] sy_out;
    wire [NC-1:0] mf;
    generate for (col = 0; col < NC; col = col + 1) begin : g_scale
        ot_gpu_fmul #(.LAT(MLAT)) u_mul (.clk(clk), .rst_n(rst_n), .v(kv_q && scale_q), .a(ky_q[32*col +: 32]),
                           .b({ksc, 16'd0}), .y(sy_out[32*col +: 32]), .fault(mf[col]));
    end endgenerate
    wire [MLAT:0] svl;
    ot_hdc_vline #(.D(MLAT)) u_sv (.clk(clk), .rst_n(rst_n), .v(kv_q), .vd(svl));
    wire [RW-1:0] srow;
    ot_hdc_delay #(.W(RW), .D(MLAT)) u_sr (.clk(clk), .rst_n(rst_n), .d(krow_q), .q(srow));
    wire [NC*32-1:0] ky_d;
    ot_hdc_delay #(.W(NC*32), .D(MLAT)) u_sy (.clk(clk), .rst_n(rst_n), .d(ky_q), .q(ky_d));
    assign sv = svl[MLAT];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv <= 1'b0; fault <= 1'b0; end
        else begin
            rv <= sv;
            fault <= fault | (|cf) | (|mf);
        end
    end
    always @(posedge clk) begin
        rrow <= srow;
        rdata <= scale_q ? sy_out : ky_d;
    end
endmodule
