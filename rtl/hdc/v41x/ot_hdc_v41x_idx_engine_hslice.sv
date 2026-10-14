`timescale 1ns/1ps
`default_nettype none
// Native scorer structural candidate: exact legacy engine queue/tail semantics,
// with real head-key hslice composition through chunk_el. FPL+16 extra edges
// are explicitly carried by keep metadata, in-flight sizing and the tail.
// Existing closed constituents and legacy functional engine stay unchanged.
// MUT1 swaps both sibling chunk pairs (a symmetric diagnostic).
// MUT2 duplicates heads8..15 in chunk0, omitting heads0..7 (proof-only).
module ot_hdc_v41x_idx_engine_hslice #(
    parameter integer NK = 8,          // keys per cycle
    parameter integer IH = 32,         // index heads
    parameter integer NB = 4,          // 32-blocks per head
    parameter integer FD = 64,         // output FIFO depth (beats), at least
    parameter integer FPL = 3,         // binary32 add latency
    parameter integer FML = 3,         // head-weight product latency
    parameter integer MUT = 0,
    parameter integer QL  = 3          // block-dot latency
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 ql_v,
    input  wire [7:0]           ql_head,
    input  wire [NB*128-1:0]    ql_codes,
    input  wire [NB*8-1:0]      ql_sc,
    input  wire [15:0]          ql_w,
    input  wire                 k_valid,
    output wire                 k_ready,
    input  wire [NK-1:0]        k_kv,
    input  wire [NK-1:0]        k_keep,
    input  wire [NK*NB*136-1:0] k_key,
    output reg                  o_valid,
    input  wire                 o_ready,
    output reg  [NK-1:0]        o_kv,
    output reg  [NK*16-1:0]     o_score,
    output reg  [NK-1:0]        o_fault,
    // activation counters (since reset; for the benches): keys scored (score
    // slots delivered), head terms fused (ReLU x weight terms summed inside the
    // engine: IH per scored key), keys whose score faulted
    output reg  [47:0]          cnt_keys_scored,
    output reg  [47:0]          cnt_headsums_fused,
    output reg  [47:0]          cnt_faults
);
    localparam integer NCH = IH / 8;
    localparam integer LVT = (NCH <= 1) ? 0 : $clog2(NCH);
    localparam integer XLAT = FPL + 16;
    localparam integer LAT_C = 1 + QL + FPL * (NB - 1) + 1 + FML + FPL * 7 + 1 + XLAT;   // chunk in-reg .. out-reg
    localparam integer LAT_T = 1 + FPL * LVT + 1;
    localparam integer LAT = LAT_C + LAT_T;                              // k beat -> tail output
    localparam integer FDE = (FD >= LAT + 2) ? FD : (1 << $clog2(LAT + 2));   // effective FIFO depth
    localparam integer CW = $clog2(FDE + 1);

    wire take = k_valid && k_ready;

    // chunks
    wire [NCH-1:0]        cv;
    wire [NK-1:0]         ckv [0:NCH-1];
    wire [NK*32-1:0]      csum [0:NCH-1];
    wire [NK-1:0]         cfl [0:NCH-1];
    genvar c, g;
    generate
        for (c = 0; c < NCH; c = c + 1) begin : g_ch
            ot_hdc_v41x_idx_chunk_el #(.NB(NB), .NKT(NK), .FPL(FPL), .FML(FML), .QL(QL)) u_c (
                .clk(clk), .rst_n(rst_n), .hb(8'(8 * ((MUT == 1) ? (c ^ 1) : ((MUT == 2 && c == 0) ? 1 : c)))), .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
                .ql_w(ql_w), .k_v(take), .k_kv(k_kv), .k_key(k_key),
                .c_v(cv[c]), .c_kv(ckv[c]), .c_sum(csum[c]), .c_fault(cfl[c]));
        end
    endgenerate
    // the mask travels beside the chunks
    wire [NK-1:0] keep_d;
    ot_hdc_delay #(.W(NK), .D(LAT_C)) u_keep (.clk(clk), .rst_n(rst_n), .d(k_keep), .q(keep_d));
    reg [NK*NCH*32-1:0] tsum;
    reg [NK*NCH-1:0]    tfl;
    integer ci, gi;
    always @* begin
        for (gi = 0; gi < NK; gi = gi + 1)
            for (ci = 0; ci < NCH; ci = ci + 1) begin
                tsum[(gi * NCH + ci) * 32 +: 32] = csum[ci][32 * gi +: 32];
                tfl[gi * NCH + ci] = cfl[ci][gi];
            end
    end
    wire              tv;
    wire [NK-1:0]     tkv, tf;
    wire [NK*16-1:0]  ts;
    ot_hdc_v41x_idx_tail_l #(.NCH(NCH), .NKT(NK), .FPL(FPL)) u_t (.clk(clk), .rst_n(rst_n), .i_v(cv[0]), .i_kv(ckv[0]),
        .i_keep(keep_d), .i_sum(tsum), .i_fault(tfl), .o_v(tv), .o_kv(tkv), .o_score(ts), .o_fault(tf));

    // output FIFO behind a registered output; a beat bypasses the FIFO when it
    // is empty and the output register is free.  Credit: beats in flight plus
    // beats in the FIFO plus the output register stay within FD.
    localparam integer EW = NK * 18;
    localparam integer PW = (FDE <= 2) ? 1 : $clog2(FDE);
    reg [EW-1:0] fm [0:FDE-1];
    reg [CW-1:0] fcnt, infl;
    reg [PW-1:0] wp, rp;
    wire deq = o_valid && o_ready;
    integer ck;
    reg [$clog2(NK+1)-1:0] nk_out, nf_out;
    always @* begin
        nk_out = 0; nf_out = 0;
        for (ck = 0; ck < NK; ck = ck + 1) begin
            nk_out = nk_out + o_kv[ck];
            nf_out = nf_out + (o_kv[ck] & o_fault[ck]);
        end
    end
    always @(posedge clk)
        if (!rst_n) begin
            cnt_keys_scored <= 0; cnt_headsums_fused <= 0; cnt_faults <= 0;
        end else if (deq) begin
            cnt_keys_scored <= cnt_keys_scored + nk_out;
            cnt_headsums_fused <= cnt_headsums_fused + nk_out * IH;
            cnt_faults <= cnt_faults + nf_out;
        end
    wire out_free = !o_valid || o_ready;
    wire from_fifo = (fcnt != 0) && out_free;
    wire bypass = tv && (fcnt == 0) && out_free;
    wire push = tv && !bypass;
    // a q-load beat reaches the query registers 3 edges after it is presented
    // (tile input register, enable register, write); keys wait for it
    reg [1:0] qsettle;
    always @(posedge clk)
        if (!rst_n) qsettle <= 2'd0;
        else if (ql_v) qsettle <= 2'd3;
        else if (qsettle != 0) qsettle <= qsettle - 2'd1;
    assign k_ready = rst_n && !ql_v && (qsettle == 0) && ((infl + fcnt + (o_valid ? 1 : 0)) < FDE);
    always @(posedge clk) begin
        if (!rst_n) begin
            fcnt <= 0; infl <= 0; wp <= 0; rp <= 0; o_valid <= 1'b0;
        end else begin
            infl <= infl + (take ? 1 : 0) - (tv ? 1 : 0);
            if (push) begin
                fm[wp] <= {tf, tkv, ts};
                wp <= (wp == FDE - 1) ? 0 : wp + 1;
            end
            fcnt <= fcnt + (push ? 1 : 0) - (from_fifo ? 1 : 0);
            if (from_fifo) begin
                {o_fault, o_kv, o_score} <= fm[rp];
                rp <= (rp == FDE - 1) ? 0 : rp + 1;
                o_valid <= 1'b1;
            end else if (bypass) begin
                {o_fault, o_kv, o_score} <= {tf, tkv, ts};
                o_valid <= 1'b1;
            end else if (deq) o_valid <= 1'b0;
        end
    end
endmodule
`default_nettype wire
