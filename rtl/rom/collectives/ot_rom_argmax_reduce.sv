`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Vocabulary-split lm_head reduction: the carried argmax.
//
// docs/HDC_DEEPSEEK_V41_OPERATOR_INVENTORY.md section 3 splits lm_head by
// vocabulary across packages: "the best {row, logit} is carried forward, and
// replaced only when strictly greater (lowest id on ties)".  The golden picks
// the token as int(np.argmax(logits)) -- the lowest id among the maxima -- so
// with slices in ascending id order along the chain, and ascending ids within
// a slice, "replace only when strictly greater" reproduces it exactly.  This
// is the only reduction the inventory's partitioning needs: no partitioning
// splits a contraction dimension across packages (experts are split by id,
// layers at sublayer boundaries, lm_head by output rows), so no binary32
// all-reduce -- which could not keep the golden's sequential order anyway --
// is required.
//
// Local side: this package's logits stream in LANES binary32 values per beat
// (lane l has id lg_base + l; lg_mask marks valid lanes), a pipelined
// comparison tree picks the beat's best (the lower lane on ties) and a
// running register keeps the slice's best, replaced only when strictly
// greater.  Logits compare as reals: -0 equals +0, a NaN raises `fault`.
//
// Chain side: an ARGMAX record (one flit) from the previous slice carries the
// best so far.  When both are present the engine forwards one ARGMAX record
// with the better of the two to NEXT (the first slice, FIRST = 1, has no
// upstream).  Tokens are matched in order and their tags checked.  One jn
// per cycle; nothing waits on a handshake.
// ---------------------------------------------------------------------------
import ot_rom_coll_pkg::*;

module ot_rom_argmax_reduce
#(
    parameter integer FLIT_W = 512,
    parameter integer LANES  = 16,
    parameter integer SELF   = 1,
    parameter integer NEXT   = 2,
    parameter integer FIRST  = 0,
    parameter integer DEPTH  = 8                // tokens the local side may run ahead
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               lg_valid,
    output wire               lg_ready,
    input  wire [LANES*32-1:0] lg_data,
    input  wire [LANES-1:0]   lg_mask,
    input  wire [31:0]        lg_base,
    input  wire [7:0]         lg_tag,
    input  wire               lg_last,
    input  wire               up_valid,
    output wire               up_ready,
    input  wire [FLIT_W-1:0]  up_data,
    input  wire               up_last,
    output wire               dn_valid,
    input  wire               dn_ready,
    output wire [FLIT_W-1:0]  dn_data,
    output wire               dn_last,
    output reg  [31:0]        tokens_out,
    output reg                fault
);
    localparam integer LV = (LANES > 1) ? $clog2(LANES) : 1;   // tree levels
    localparam integer LW = LV;
    localparam integer DW = $clog2(DEPTH + 1);
    localparam [7:0] SELF8 = SELF;
    localparam [7:0] NEXT8 = NEXT;

    function [31:0] okey(input [31:0] x);         // order-preserving key; -0 as +0
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'd0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function isnan(input [31:0] x);
        isnan = (x[30:23] == 8'hFF) && (x[22:0] != 23'd0);
    endfunction

    // -- local: the beat's best through a registered tree, one level per stage ------------------
    reg [DW-1:0] pend;                            // tokens accepted but not yet joined
    assign lg_ready = (pend < DEPTH);
    wire lg_fire = lg_valid && lg_ready;

    // the tree, flattened: level s, entry l lives at OFF(s) + l, OFF(s) = 2 LANES - 2 LANES / 2^s
    localparam integer NE = 2 * LANES;
    reg [NE*32-1:0] tv;                            // value
    reg [NE*LW-1:0] tl;                            // lane
    reg [NE-1:0]    tok;                           // lane valid
    reg [LV:0]      tsv, tsl, tnan;                // beat valid / slice last / NaN seen
    reg [(LV+1)*32-1:0] tsb;                       // base id
    reg [(LV+1)*8-1:0]  tst;                       // tag
    integer l, s, o, q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tsv <= {(LV+1){1'b0}};
        else tsv <= {tsv[LV-1:0], lg_fire};
    end
    always @(posedge clk) begin
        tsl[0] <= lg_last; tsb[31:0] <= lg_base; tst[7:0] <= lg_tag;
        tnan[0] <= 1'b0;
        for (l = 0; l < LANES; l = l + 1) begin
            tv[32 * l +: 32] <= lg_data[32 * l +: 32];
            tl[LW * l +: LW] <= l;
            tok[l] <= lg_mask[l];
            if (lg_mask[l] && isnan(lg_data[32 * l +: 32])) tnan[0] <= 1'b1;
        end
        for (s = 1; s <= LV; s = s + 1) begin
            tsl[s] <= tsl[s-1]; tnan[s] <= tnan[s-1];
            tsb[32 * s +: 32] <= tsb[32 * (s-1) +: 32]; tst[8 * s +: 8] <= tst[8 * (s-1) +: 8];
            q = NE - (NE >> (s - 1));              // previous level's offset
            o = NE - (NE >> s);
            for (l = 0; l < (LANES >> s); l = l + 1) begin
                // right replaces left only when valid and strictly greater (or left invalid)
                if (tok[q + 2*l + 1] && (!tok[q + 2*l]
                        || okey(tv[32 * (q + 2*l + 1) +: 32]) > okey(tv[32 * (q + 2*l) +: 32]))) begin
                    tv[32 * (o + l) +: 32] <= tv[32 * (q + 2*l + 1) +: 32];
                    tl[LW * (o + l) +: LW] <= tl[LW * (q + 2*l + 1) +: LW];
                    tok[o + l] <= 1'b1;
                end else begin
                    tv[32 * (o + l) +: 32] <= tv[32 * (q + 2*l) +: 32];
                    tl[LW * (o + l) +: LW] <= tl[LW * (q + 2*l) +: LW];
                    tok[o + l] <= tok[q + 2*l];
                end
            end
        end
    end
    localparam integer OT = NE - (NE >> LV);       // the root's offset

    wire              u_valid, u_last;
    wire [FLIT_W-1:0] u_data;
    wire              d_ready;
    // -- running best over the slice ---------------------------------------------------------------
    wire [31:0] c_val = tv[32 * OT +: 32];
    wire [31:0] c_id  = tsb[32 * LV +: 32] + tl[LW * OT +: LW];
    wire        c_ok  = tok[OT];
    reg  [31:0] b_val, b_id;
    reg         b_ok;
    wire        take_c = c_ok && (!b_ok || okey(c_val) > okey(b_val));
    wire [31:0] n_val = take_c ? c_val : b_val;
    wire [31:0] n_id  = take_c ? c_id  : b_id;
    wire        n_ok  = take_c || b_ok;
    // local FIFO of finished slices
    reg [31:0] f_val [0:DEPTH-1];
    reg [31:0] f_id  [0:DEPTH-1];
    reg        f_ok  [0:DEPTH-1];
    reg [7:0]  f_tag [0:DEPTH-1];
    reg [DW-1:0] f_wp, f_rp, f_n;
    wire f_push = tsv[LV] && tsl[LV];
    wire jn;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            b_ok <= 1'b0; f_wp <= 0; f_rp <= 0; f_n <= 0; pend <= 0; tokens_out <= 32'd0; fault <= 1'b0;
        end else begin
            if (tsv[LV]) begin
                b_ok <= f_push ? 1'b0 : n_ok;
                if (tnan[LV]) fault <= 1'b1;
            end
            if (f_push) f_wp <= (f_wp == DEPTH - 1) ? 0 : f_wp + 1'b1;
            if (jn)   f_rp <= (f_rp == DEPTH - 1) ? 0 : f_rp + 1'b1;
            f_n  <= f_n + f_push - jn;
            pend <= pend + (lg_fire && lg_last) - jn;
            if (jn) tokens_out <= tokens_out + 32'd1;
            if (jn && FIRST == 0 && u_data[H_TAG +: 8] != f_tag[f_rp]) fault <= 1'b1;
            if (jn && FIRST == 0 && u_data[H_KIND +: 4] != K_ARGMAX) fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        if (tsv[LV]) begin b_val <= n_val; b_id <= n_id; end
        if (f_push) begin
            f_val[f_wp] <= n_val; f_id[f_wp] <= n_id; f_ok[f_wp] <= n_ok; f_tag[f_wp] <= tst[8 * LV +: 8];
        end
    end

    // -- chain jn ----------------------------------------------------------------------------------
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_su (
        .clk(clk), .rst_n(rst_n), .in_valid(up_valid), .in_ready(up_ready), .in_data({up_last, up_data}),
        .out_valid(u_valid), .out_ready(jn && FIRST == 0), .out_data({u_last, u_data}));
    assign jn = (f_n != 0) && (FIRST != 0 || u_valid) && d_ready;
    wire        up_ok  = (FIRST == 0) && u_data[H_ARG_OK];
    wire [31:0] up_val = u_data[H_ARG_VAL +: 32];
    wire [31:0] up_id  = u_data[H_ARG_ID +: 32];
    wire        loc_wins = f_ok[f_rp] && (!up_ok || okey(f_val[f_rp]) > okey(up_val));
    reg [FLIT_W-1:0] rec;
    always @* begin
        rec = {FLIT_W{1'b0}};
        rec[H_KIND +: 4]    = K_ARGMAX;
        rec[H_DST +: 8]     = NEXT8;
        rec[H_SRC +: 8]     = SELF8;
        rec[H_MASK +: 16]   = 16'd1 << NEXT;
        rec[H_TAG +: 8]     = f_tag[f_rp];
        rec[H_ARG_VAL +: 32] = loc_wins ? f_val[f_rp] : up_val;
        rec[H_ARG_ID +: 32]  = loc_wins ? f_id[f_rp]  : up_id;
        rec[H_ARG_OK]        = loc_wins || up_ok;
    end
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_sd (
        .clk(clk), .rst_n(rst_n), .in_valid(jn), .in_ready(d_ready), .in_data({1'b1, rec}),
        .out_valid(dn_valid), .out_ready(dn_ready), .out_data({dn_last, dn_data}));
endmodule
