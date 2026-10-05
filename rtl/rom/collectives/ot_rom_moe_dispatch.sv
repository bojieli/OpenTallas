`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MoE expert-parallel DISPATCH engine of the DeepSeek-V4.1 ROM array.
//
// The home package of a layer's MoE half routes a token (router top-6 of the
// routed experts plus the one shared expert) and must deliver the token's FP8
// activation to the packages that own those experts.  The input is one
// DISPATCH record per token, as ot_rom_coll_pkg specifies: a descriptor flit
// naming the six routed expert ids and their routing weights (the golden's
// wgt = score / (sum + 1e-20) * 1.5, binary32), then ACT_FLITS flits of the
// activation exactly as tools/hdc_golden_v41.quant_fp8 quantises it (the
// E4M3 codes and the per-block exponents ot_hdc_actquant emits).
//
// Per descriptor the engine, in one pipeline stage and with no stall:
//   * adds the shared expert as item 6 (id N_EXP),
//   * looks every item's owning package up in PLACE (4 bits per expert id:
//     the expert -> package placement table, a parameter ROM),
//   * stamps each item's RANK, its position in ascending-id order -- the
//     order tools/hdc_golden_v41.Model.moe sums the experts in -- so that the
//     combine engine can restore that order whatever order results come back
//     in; the shared expert is rank 6, summed last, as in the golden,
//   * forms the destination set (one bit per owning package).
//
// Two delivery modes (parameter MCAST):
//   MCAST = 1  one record per token, dst_mask = the destination set; the
//              fabric (ot_rom_fabric_router, or a chain of ot_rom_mcast_node)
//              replicates it.  The activation is injected once per token no
//              matter how many packages need it.  Cut-through, II = 1, and
//              the descriptor is stamped in flight: zero bubbles per message.
//   MCAST = 0  unicast over direct links.  Tokens are collected into a
//              micro-batch (up to TAGS tokens, closed early by the
//              descriptor's eob bit) in one of two banks, and re-emitted
//              DESTINATION-MAJOR: for each package, every token of the batch
//              that has at least one expert there, as one packet (`last` only
//              after that package's final record).  A token's activation
//              goes to a package once however many of its experts live
//              there.  The other bank fills meanwhile; a batch costs two
//              bubble cycles at its start (loading the walk mask).
//
// Every item carries its owning package, so a receiving package keeps the
// items whose dest is itself (ot_rom_moe_expert_port) in either mode.
// ---------------------------------------------------------------------------
import ot_rom_coll_pkg::*;

module ot_rom_moe_dispatch
#(
    parameter integer FLIT_W    = 512,
    parameter integer NPKG      = 5,           // packages in the array (<= 16)
    parameter integer SELF      = 0,
    parameter integer N_EXP     = 12,          // routed experts; the shared one is id N_EXP
    parameter integer ACT_FLITS = 3,           // activation flits per token
    parameter integer MCAST     = 1,
    parameter integer TAGS      = 4,           // unicast: tokens per micro-batch bank
    // expert e lives on package PLACE[4e +: 4]; default: routed e on 1 + (e mod 4), shared on 0
    parameter [4*(N_EXP+1)-1:0] PLACE = 52'h0_4321_4321_4321
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    output wire              in_ready,
    input  wire [FLIT_W-1:0] in_data,
    input  wire              in_last,
    output wire              out_valid,
    input  wire              out_ready,
    output wire [FLIT_W-1:0] out_data,
    output wire              out_last,
    output reg  [31:0]       tokens_in,
    output reg  [31:0]       records_out,
    output reg  [31:0]       flits_out,
    output reg               fault
);
    localparam integer RF = 1 + ACT_FLITS;             // flits per record
    localparam integer PW = (RF > 2) ? $clog2(RF) : 1;
    localparam integer K  = N_ITEMS - 1;               // routed items (6)
    localparam [8:0] SHARED_ID = N_EXP;
    localparam [7:0] SELF8     = SELF;
    localparam [7:0] RLEN      = ACT_FLITS;

    // -- stage A: input slice -----------------------------------------------------------
    wire              a_valid, a_ready, a_last;
    wire [FLIT_W-1:0] a_data;
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_a (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_data({in_last, in_data}),
        .out_valid(a_valid), .out_ready(a_ready), .out_data({a_last, a_data}));
    wire a_fire = a_valid && a_ready;

    reg [PW-1:0] pos;                                  // flit index within the record
    wire is_desc = (pos == 0);

    // -- descriptor stamping (one combinational stage) ----------------------------------------
    reg [8:0]         id   [0:N_ITEMS-1];
    reg [3:0]         dst  [0:N_ITEMS-1];
    reg [2:0]         rnk  [0:N_ITEMS-1];
    reg [N_ITEMS-1:0] ival;
    reg [15:0]        dmask;
    reg               bad_id;
    reg [FLIT_W-1:0]  stamped;
    integer i, j, e;
    always @* begin
        ival = {1'b1, a_data[H_IVAL +: K]};
        bad_id = (a_data[H_IVAL +: K] != {K{1'b1}});   // the router always names six experts
        for (i = 0; i < N_ITEMS; i = i + 1)
            id[i] = (i == K) ? SHARED_ID : a_data[H_ITEM + ITEM_W * i + I_ID +: 9];
        dmask = 16'd0;
        for (i = 0; i < N_ITEMS; i = i + 1) begin
            dst[i] = 4'd0;
            for (e = 0; e <= N_EXP; e = e + 1)
                if (id[i] == e) dst[i] = PLACE[4 * e +: 4];
            if (id[i] > N_EXP) bad_id = 1'b1;
            if (ival[i]) dmask = dmask | (16'd1 << dst[i]);
            // rank = number of routed items with a smaller id (the shared item: all six)
            rnk[i] = 3'd0;
            for (j = 0; j < K; j = j + 1)
                if (j != i && ival[j] && (i == K || id[j] < id[i])) rnk[i] = rnk[i] + 3'd1;
        end
        stamped = a_data;
        stamped[H_KIND +: 4] = K_DISPATCH;
        stamped[H_SRC +: 8]  = SELF8;
        stamped[H_LEN +: 8]  = RLEN;
        // multicast: the group id of the destination set (the router's table expands it)
        stamped[H_DST +: 8]  = GROUP_BASE + dmask[NPKG-1:0];
        stamped[H_IVAL +: N_ITEMS] = ival;
        stamped[H_MASK +: 16] = dmask;
        for (i = 0; i < N_ITEMS; i = i + 1) begin
            if (i == K) begin
                stamped[H_ITEM + ITEM_W * i + I_WGT +: 32] = 32'd0;
                stamped[H_ITEM + ITEM_W * i + I_ID +: 9]   = SHARED_ID;
            end
            stamped[H_ITEM + ITEM_W * i + I_RANK +: 3] = rnk[i];
            stamped[H_ITEM + ITEM_W * i + I_DEST +: 4] = dst[i];
        end
    end
    wire [FLIT_W-1:0] a_word = is_desc ? stamped : a_data;

    // framing, statistics and faults of the input side
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pos <= 0; tokens_in <= 32'd0; fault <= 1'b0;
        end else if (a_fire) begin
            pos <= (pos == ACT_FLITS) ? {PW{1'b0}} : pos + 1'b1;
            if (is_desc) tokens_in <= tokens_in + 32'd1;
            if (a_last && pos != ACT_FLITS) fault <= 1'b1;   // a packet ends only at a record end
            if (is_desc && bad_id) fault <= 1'b1;
        end
    end

    // -- output slice ------------------------------------------------------------------------
    wire              b_in_valid, b_in_ready, b_in_last;
    wire [FLIT_W-1:0] b_in_data;
    ot_rom_coll_skid #(.W(FLIT_W + 1)) u_b (
        .clk(clk), .rst_n(rst_n), .in_valid(b_in_valid), .in_ready(b_in_ready), .in_data({b_in_last, b_in_data}),
        .out_valid(out_valid), .out_ready(out_ready), .out_data({out_last, out_data}));
    wire b_is_desc;                                    // the flit into u_b opens a record
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            records_out <= 32'd0; flits_out <= 32'd0;
        end else if (b_in_valid && b_in_ready) begin
            flits_out <= flits_out + 32'd1;
            if (b_is_desc) records_out <= records_out + 32'd1;
        end
    end

    generate if (MCAST != 0) begin : g_mcast
        // one record per token; the fabric replicates it to dst_mask
        assign a_ready    = b_in_ready;
        assign b_in_valid = a_valid;
        assign b_in_data  = a_word;
        assign b_in_last  = a_last;
        assign b_is_desc  = is_desc;
    end else begin : g_unicast
        localparam integer SLOTS = 2 * TAGS * RF;
        localparam integer TW    = (TAGS > 1) ? $clog2(TAGS) : 1;
        localparam integer MW    = NPKG * TAGS;
        localparam integer XW    = $clog2(MW + 1);
        reg [FLIT_W-1:0] bank_mem [0:SLOTS-1];
        reg [MW-1:0]     mm [0:1];                     // [d*TAGS + t]: token t of the batch needs package d
        reg [1:0]        full;
        // writer
        reg          wb;
        reg [TW-1:0] wt;
        reg          weob;
        // reader
        reg          rb;
        reg [1:0]    rstate;                           // 0 idle, 1 load, 2 run
        reg [MW-1:0] rem;
        reg [XW-1:0] nxt;                              // registered first set bit of rem (MW = none)
        reg          in_rec;
        reg [PW-1:0] rpos;
        reg [3:0]    cd;
        reg [TW-1:0] ct;
        reg          emit, emit_last;
        reg [FLIT_W-1:0] emit_word;
        integer k, d;
        reg [MW-1:0] spread;
        always @* begin
            spread = {MW{1'b0}};
            for (d = 0; d < NPKG; d = d + 1)
                spread[d * TAGS + wt] = dmask[d];
        end
        assign a_ready = !full[wb];
        // first set bit of rem, lowest index first: destination-major, then token order
        reg [XW-1:0] ffs;
        always @* begin
            ffs = MW[XW-1:0];
            for (k = MW - 1; k >= 0; k = k - 1)
                if (rem[k]) ffs = k[XW-1:0];
        end
        wire [3:0]    nd = nxt / TAGS;
        wire [TW-1:0] nt = nxt % TAGS;
        wire          nok = (nxt != MW[XW-1:0]);
        reg  [TAGS-1:0] row;                           // rem restricted to package cd
        always @* for (k = 0; k < TAGS; k = k + 1) row[k] = rem[cd * TAGS + k];
        always @* begin
            emit = 1'b0; emit_last = 1'b0; emit_word = bank_mem[(rb * TAGS + ct) * RF + rpos];
            if (rstate == 2'd2 && b_in_ready) begin
                if (!in_rec) begin
                    emit = nok;
                    emit_word = bank_mem[(rb * TAGS + nt) * RF];
                    emit_word[H_DST +: 8]  = {4'd0, nd};
                    emit_word[H_MASK +: 16] = 16'd1 << nd;
                end else begin
                    emit = 1'b1;
                    emit_last = (rpos == ACT_FLITS) && (row == {TAGS{1'b0}});
                end
            end
        end
        assign b_in_valid = emit;
        assign b_in_data  = emit_word;
        assign b_in_last  = emit_last;
        assign b_is_desc  = !in_rec;
        always @(posedge clk) begin
            if (a_fire) bank_mem[(wb * TAGS + wt) * RF + pos] <= a_word;
            if (a_fire && is_desc) mm[wb] <= ((wt == 0) ? {MW{1'b0}} : mm[wb]) | spread;
        end
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                full <= 2'b00; wb <= 1'b0; wt <= {TW{1'b0}}; weob <= 1'b0;
                rb <= 1'b0; rstate <= 2'd0; rem <= {MW{1'b0}}; nxt <= MW[XW-1:0];
                in_rec <= 1'b0; rpos <= {PW{1'b0}}; cd <= 4'd0; ct <= {TW{1'b0}};
            end else begin
                nxt <= ffs;
                // writer: close the bank after eob or TAGS tokens
                if (a_fire) begin
                    if (is_desc) weob <= a_data[H_EOB];
                    if (pos == ACT_FLITS) begin
                        if (weob || wt == TAGS - 1) begin
                            wb <= !wb; wt <= {TW{1'b0}};
                        end else wt <= wt + 1'b1;
                    end
                end
                // reader
                case (rstate)
                    2'd0: if (full[rb]) begin rem <= mm[rb]; rstate <= 2'd1; end
                    2'd1: rstate <= 2'd2;
                    default: begin
                        if (b_in_ready) begin
                            if (!in_rec) begin
                                if (nok) begin
                                    rem[nxt] <= 1'b0; cd <= nd; ct <= nt; in_rec <= 1'b1; rpos <= 1;
                                end else begin
                                    rb <= !rb; rstate <= 2'd0;
                                end
                            end else begin
                                rpos <= (rpos == ACT_FLITS) ? {PW{1'b0}} : rpos + 1'b1;
                                if (rpos == ACT_FLITS) in_rec <= 1'b0;
                            end
                        end
                    end
                endcase
                // bank ownership: set by the writer when it closes, cleared when the reader finishes
                full <= (full
                         | ((a_fire && pos == ACT_FLITS && (weob || wt == TAGS - 1)) ? (2'b01 << wb) : 2'b00))
                        & ~((rstate == 2'd2 && b_in_ready && !in_rec && !nok) ? (2'b01 << rb) : 2'b00);
            end
        end
    end endgenerate
endmodule
