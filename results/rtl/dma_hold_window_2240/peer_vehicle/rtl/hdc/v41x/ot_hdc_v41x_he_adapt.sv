`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HE ADAPTER of the re-specified V4.1 decode core (ot_hdc_core_v41x): keeps the
// as-built hyper-connection engine's contract (ot_hdc_v41_hcproj: go / ready /
// idle, the he_* fields, mx_m / mx_xps / mx_ops, the per-chunk vector-memory x
// reads and the masked element writes) and runs the op on the re-specified
// projection engine ot_hdc_v41x_hcp (8 x HW FP32 lanes, R-ARITH chunk8 csum,
// raw mode cmd_scale = 0).
//
// An HE op is out[row] = csum_k w[row, k] * x[k] over K = HC_SPLIT * he_k
// contiguous x elements (tools/hdc_program_v41.Machine.he under R-ARITH "he":
// the S*K products in K order, csum'd).  The engine wants K / 8 = he_k chunks
// (HC_SPLIT is 8, so nchunk = he_k exactly) with x in BF16 x banks:
//     x bank k, word p*R + r, lane l  =  x_p[8*(r*HW + l) + k]        R = ceil(he_k / HW)
// and its weights in 8 binary32 weight banks (outside, tools/hdc_images_v41x.py):
//     weight bank k, word wbase + o*R + r, lane l  =  w[o][8*(r*HW + l) + k]
// at the SAME base as the as-built HE ROM word (identity translation: the new
// footprint nout*R words fits the old he_k*IL, checked by the image tool).
//
// Sequence per op: LOAD copies the x of each served position (mx_m of them, at
// + p*mx_xps) from the vector memory through the 8 per-chunk read ports -- one
// chunk (8 elements, one per bank) per cycle -- into the local x banks (the
// element's top 16 bits: the residual is BF16, hdc_golden_v41 asserts it), then
// RUN issues one engine command (npos = mx_m) and writes each result as one
// masked element at obase + p*mx_ops + o.  x elements whose low 16 bits are not
// zero fault (the BF16 contract the golden asserts).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_he_adapt #(
    parameter integer HW   = 8,            // engine lanes per group (8 * HW FP32 MAC lanes)
    parameter integer TL   = 9,            // engine tail levels
    parameter integer KCMAX = 128,         // largest he_k (chunks per row)
    parameter integer PMAX = 8,            // positions per op (power of two >= MP)
    parameter integer BAW  = 16,           // weight bank word address width
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer S    = 8,            // x read ports (the as-built HC_SPLIT)
    parameter integer MP   = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_k,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_obase,
    input  wire [2:0]        i_m,
    input  wire [AW-1:0]     i_xps,
    input  wire [AW-1:0]     i_ops,
    // weight banks (binary32), bank k at [k*...]
    output wire [7:0]        w_re,
    output wire [8*BAW-1:0]  w_addr,
    input  wire [8*HW*32-1:0] w_data,
    // vector memory: x reads (the as-built HE's per-chunk ports) and the masked write
    output reg  [MP*S-1:0]   x_re,
    output reg  [MP*S*AW-1:0] x_addr,
    input  wire [MP*S*32-1:0] x_q,
    output reg  [MP-1:0]     o_we,
    output reg  [MP*AW-1:0]  o_addr,
    output reg  [MP*32-1:0]  o_mask,
    output reg  [MP*1024-1:0] o_data,
    output reg               fault
);
    localparam integer LHW  = $clog2(HW);
    localparam integer RMAX = (KCMAX + HW - 1) / HW;
    localparam integer XD   = PMAX * RMAX;            // x bank words
    localparam integer XAW  = $clog2(XD);
    localparam integer PW   = (PMAX > 1) ? $clog2(PMAX) : 1;
    localparam integer OXW  = 5;                      // OMAX = 32 rows
    localparam [1:0] A_IDLE = 0, A_LOAD = 1, A_CMD = 2, A_RUN = 3;

    reg  [1:0]    st;
    reg  [NW-1:0] nout, kc;
    reg  [AW-1:0] wbase, xbase, obase, xps, ops;
    reg  [PW:0]   m;
    reg  [PW:0]   lp;                                 // position being loaded
    reg  [NW-1:0] lc;                                 // chunk being loaded (read issue)
    reg  [NW-1:0] nrun;
    assign ready = (st == A_IDLE);

    // ---- LOAD: one chunk a cycle through the 8 read ports; the write lands 2 cycles later
    reg           l_v, l2_v;
    reg  [XAW-1:0] l_word, l2_word;
    reg  [LHW-1:0] l_lane, l2_lane;
    wire          l_last = (lc + 1 == kc);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= A_IDLE; x_re <= 0; l_v <= 1'b0; l2_v <= 1'b0;
        end else begin
            x_re <= 0;
            l_v <= 1'b0;
            l2_v <= l_v;
            case (st)
                A_IDLE: if (go) begin
                    st <= A_LOAD; lp <= 0; lc <= 0;
                end
                A_LOAD: begin
                    x_re[S-1:0] <= {S{1'b1}};
                    l_v <= 1'b1;
                    lc <= lc + 1'b1;
                    if (l_last) begin
                        lc <= 0;
                        lp <= lp + 1'b1;
                        if (lp + 1 == m) st <= A_CMD;
                    end
                end
                A_CMD: if (!l_v && !l2_v && cmd_ready) st <= A_RUN;
                A_RUN: if (o_valid && o_last) st <= A_IDLE;
                default: st <= A_IDLE;
            endcase
        end
    end
    integer c;
    always @(posedge clk) begin
        if (st == A_IDLE && go) begin
            nout <= i_nout; kc <= i_k; wbase <= i_wbase; xbase <= i_xbase; obase <= i_obase;
            xps <= i_xps; ops <= i_ops; m <= (i_m == 3'd0) ? 3'd1 : i_m;
            nrun <= (i_k + HW - 1) >> LHW;
        end
        for (c = 0; c < S; c = c + 1)
            x_addr[c*AW +: AW] <= xbase + lp * xps + lc * 8 + c;
        //: chunk lc = r*HW + l of position lp
        l_word <= lp * nrun + (lc >> LHW);
        l_lane <= lc[LHW-1:0];
        l2_word <= l_word; l2_lane <= l_lane;
    end

    // ---- local x banks (BF16), synchronous read, written at l2 (the read data is at x_q then)
    reg  [15:0] xb [0:8*XD*HW-1];
    reg         xlow;                                 // an x element that is not BF16
    integer b;
    always @(posedge clk) begin
        if (l2_v)
            for (b = 0; b < 8; b = b + 1)
                xb[(b * XD + l2_word) * HW + l2_lane] <= x_q[32*b + 16 +: 16];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) xlow <= 1'b0;
        else if (st == A_IDLE && go) xlow <= 1'b0;
        else if (l2_v) for (b = 0; b < 8; b = b + 1) if (x_q[32*b +: 16] != 16'd0) xlow <= 1'b1;
    end

    // ---- the engine
    wire              cmd_ready, o_valid, o_last, e_fault, e_idle;
    wire [7:0]        ex_re;
    wire [8*BAW-1:0]  ex_addr;
    reg  [8*HW*16-1:0] ex_data;
    wire [PW-1:0]     o_pos;
    wire [OXW-1:0]    o_idx;
    wire [31:0]       o_d;
    integer bl;
    always @(posedge clk)
        for (b = 0; b < 8; b = b + 1)
            if (ex_re[b])
                for (bl = 0; bl < HW; bl = bl + 1)
                    ex_data[16*(HW*b + bl) +: 16] <= xb[(b * XD + ex_addr[BAW*b +: XAW]) * HW + bl];
    ot_hdc_v41x_hcp #(.W(HW), .TL(TL), .PMAX(PMAX), .OMAX(32), .AW(BAW), .CW(NW), .ML(1), .DF(32)) u_hcp (
        .clk(clk), .rst_n(rst_n), .cmd_valid(st == A_CMD && !l_v && !l2_v), .cmd_ready(cmd_ready),
        .cmd_npos(m), .cmd_nout(nout[OXW:0]), .cmd_nchunk(kc), .cmd_scale(1'b0), .cmd_nf(32'd0),
        .cmd_eps(32'd0), .cmd_wbase(wbase[BAW-1:0]), .cmd_xbase({BAW{1'b0}}),
        .w_re(w_re), .w_addr(w_addr), .w_data(w_data), .x_re(ex_re), .x_addr(ex_addr), .x_data(ex_data),
        .o_valid(o_valid), .o_ready(1'b1), .o_pos(o_pos), .o_idx(o_idx), .o_data(o_d), .o_last(o_last),
        .fault(e_fault), .idle(e_idle));

    // ---- results: one masked element write per result (copy 0's port, positions by mx_ops)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we <= 0;
        else o_we <= {{(MP-1){1'b0}}, o_valid};
    end
    always @(posedge clk) begin
        o_addr <= 0; o_mask <= 0; o_data <= 0;
        o_addr[AW-1:0] <= obase + o_pos * ops + o_idx;
        o_mask[31:0] <= 32'd1;
        o_data[31:0] <= o_d;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; end
        else begin
            idle <= (st == A_IDLE) && !go && e_idle && !o_valid && !(|o_we);
            fault <= (e_fault && st == A_RUN) || xlow;
        end
    end
    // ---- activation counters (bench only, read hierarchically by rtl/test/tb_hdc_core_v41x.sv): ops this
    // engine ran and the elements it processed -- the campaign fails a selected unit whose counters stay 0
    reg [31:0] dbg_ops, dbg_elems;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin dbg_ops <= 0; dbg_elems <= 0; end
        else begin
            if (st == A_IDLE && go) dbg_ops <= dbg_ops + 1;
            dbg_elems <= dbg_elems + (u_hcp.iss ? 8 * HW : 0);        // MACs issued (one task of 8 x HW terms)
        end
    end
endmodule
