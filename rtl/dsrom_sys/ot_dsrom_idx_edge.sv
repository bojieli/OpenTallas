`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DeepSeek-V4.1 ROM EDGE INDEX SCORER (default-off; selected by the die's
// index-scorer location, IDX_SCORER_LOC = 1 in rtl/dsrom_sys/ot_dsrom_idx_scorer_loc.sv
// of the DS ROM system stream; nothing in the default build instantiates it).
//
// Pricing: claude/dsrom-nearhbm-20261003 @ 723243a4a, results/uarch/dsrom_nearhbm_20261003
// (variant (i): near-HBM scan, per-stack top-512, hub merge).  The index scan
// moves next to each HBM service strip; attention stays in the hub.
//
//   ot_dsrom_edge_stack  one per HBM stack, at its service strip: ingests the
//                        stack's index keys at the stack rate (16-key beats,
//                        68 B per key), scores them on NSL x NK lanes of the
//                        qualified streaming-domain score slice
//                        (ot_hdc_v41x_idx_score_slice_l, FPL/FML/QL latencies
//                        of the 1.2 GHz build), and keeps the stack's exact
//                        top-K in a streamed fold (ot_dsrom_edge_lsel);
//   ot_dsrom_edge_hub    the four lists merged by position, the exact global
//                        top-K (ot_hdc_tselect), ascending position;
//   ot_dsrom_idx_edge    the die composition: q broadcast, four stacks, hub.
//
// Position ownership (16-key round robin, results/rtl/v41_idx_stack_major_ingest.json):
//   global position p = 64 * (j >> 4) + 16 * s + (j & 15) for local key j of stack s.
// Exactness is class A (see ot_dsrom_edge_lsel.sv): scores are key-local, every
// selection step is the golden's total order.
// ---------------------------------------------------------------------------
module ot_dsrom_edge_stack #(
    parameter integer NSL   = 4,      // score slices (NSL x NK = 16 keys per beat)
    parameter integer NK    = 4,
    parameter integer NB    = 4,      // 32-blocks per head
    parameter integer IH    = 32,     // index heads
    parameter integer IW    = 20,     // global position width
    parameter integer K     = 512,
    parameter integer FPL   = 7,      // 1.2 GHz streaming build (results/physical_abi3/asap7/hdc/v41x/w11_stream)
    parameter integer FML   = 5,
    parameter integer QL    = 5,
    parameter integer NC    = 32,
    parameter integer FA    = 7,
    parameter integer LO    = 16,
    parameter integer MACRO = 0,
    parameter integer CONTIGUOUS = 0
) (
    input  wire                      clk,
    input  wire                      rst_n,
    input  wire [1:0]                stack_id,
    input  wire                      start,
    input  wire [IW:0]               layout_n,
    input  wire                      layout_installed,
    // q load (broadcast from the hub, one head per cycle, before the scan)
    input  wire                      ql_v,
    output wire                      ql_ready,
    input  wire [7:0]                ql_head,
    input  wire [NB*128-1:0]         ql_codes,
    input  wire [NB*8-1:0]           ql_sc,
    input  wire [15:0]               ql_w,
    // keys from the HBM service, stack-local order
    input  wire                      k_valid,
    output wire                      k_ready,
    input  wire                      k_last,
    input  wire [IW-1:0]             k_first,        // local index of slot 0 (a multiple of 16)
    input  wire [NSL*NK-1:0]         k_kv,           // valid prefix
    input  wire [NSL*NK-1:0]         k_keep,         // candidate mask (0 -> -inf)
    input  wire [NSL*NK-1:0]         k_ref,          // reader refusal
    input  wire [NSL*NK*NB*136-1:0]  k_key,
    // candidate list to the hub
    output wire                      c_valid,
    input  wire                      c_ready,
    output wire                      c_last,
    output wire [LO-1:0]             c_lv,
    output wire [LO*16-1:0]          c_val,
    output wire [LO*IW-1:0]          c_idx,
    output reg                       fault,
    output wire                      busy,
    output wire [31:0]               st_folds,
    output wire [31:0]               st_pass,
    output wire [31:0]               st_stall
);
    localparam integer LI = NSL * NK;
    reg [IW:0] n_q;
    reg installed_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin n_q <= 0; installed_q <= 0; end
        else if (start) begin n_q <= layout_n; installed_q <= layout_installed; end
    end
    wire [4*(IW+1)-1:0] bases, counts;
    ot_dsrom_edge_layout #(.IW(IW)) u_map (.n(n_q), .position({IW{1'b0}}),
        .bases(bases), .counts(counts), .stack(), .local_row(), .valid());
    wire [IW:0] stack_base = bases[(IW+1)*stack_id +: IW+1];
    wire [IW:0] stack_count = counts[(IW+1)*stack_id +: IW+1];
    // global positions of the beat's slots
    wire [LI*IW-1:0] gidx;
    genvar g;
    generate
        for (g = 0; g < LI; g = g + 1) begin : g_ix
            localparam [IW-1:0] L = g;
            assign gidx[IW*g +: IW] = CONTIGUOUS ? stack_base + k_first + L : {k_first[IW-1:4], 6'd0} + {{(IW-6){1'b0}}, stack_id, 4'd0} + L;
        end
    endgenerate

    wire              s_valid, s_ready, s_pf;
    wire [NSL-1:0]    s_last;
    wire [LI-1:0]     s_kv, s_fault;
    wire [LI*16-1:0]  s_score;
    wire [LI*IW-1:0]  s_index;
    ot_hdc_v41x_idx_array_l #(.NS(NSL), .NK(NK), .NB(NB), .IH(IH), .IW(IW), .FPL(FPL), .FML(FML), .QL(QL)) u_score (
        .clk(clk), .rst_n(rst_n),
        .ql_v(ql_v), .ql_ready(ql_ready), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w),
        .i_valid(k_valid), .i_ready(k_ready), .i_last({NSL{k_last}}), .i_kv(k_kv), .i_ref(k_ref),
        .i_keep(k_keep), .i_index(gidx), .i_key(k_key),
        .o_valid(s_valid), .o_ready(s_ready), .o_last(s_last), .o_kv(s_kv), .o_fault(s_fault),
        .o_score(s_score), .o_index(s_index), .protocol_fault(s_pf));

    wire [31:0] st_lines;
    ot_dsrom_edge_lsel #(.LI(LI), .W(64), .VW(16), .IW(IW), .K(K), .NC(NC), .FA(FA), .LO(LO), .MACRO(MACRO)) u_sel (
        .clk(clk), .rst_n(rst_n), .start(start),
        .in_valid(s_valid), .in_ready(s_ready), .in_last(s_last[0]),
        .in_lv(s_kv), .in_val(s_score), .in_idx(s_index),
        .out_valid(c_valid), .out_ready(c_ready), .out_last(c_last), .out_lv(c_lv), .out_val(c_val),
        .out_idx(c_idx), .busy(busy), .st_folds(st_folds), .st_pass(st_pass), .st_lines(st_lines),
        .st_stall(st_stall));

    reg bad_range;
    integer lane;
    always @* begin
        bad_range = !installed_q;
        for (lane=0; lane<LI; lane=lane+1)
            if (k_kv[lane] && ({1'b0,k_first}+lane >= stack_count)) bad_range=1'b1;
    end
    // a refused or faulted key (golden intermediate not finite) fails the query closed
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if (start) fault <= CONTIGUOUS && !layout_installed;
        else if ((CONTIGUOUS && k_valid && k_ready && bad_range) || (s_valid && s_ready && |(s_fault & s_kv)) || s_pf) fault <= 1'b1;
    end
endmodule

// The die composition: four edge stacks and the hub.  The q broadcast is one
// port; each stack's key stream is its own HBM service's.
module ot_dsrom_idx_edge #(
    parameter integer NSL   = 4,
    parameter integer NK    = 4,
    parameter integer NB    = 4,
    parameter integer IH    = 32,
    parameter integer IW    = 20,
    parameter integer K     = 512,
    parameter integer FPL   = 7,
    parameter integer FML   = 5,
    parameter integer QL    = 5,
    parameter integer NC    = 32,
    parameter integer FA    = 7,
    parameter integer LO    = 16,
    parameter integer MACRO = 0,
    parameter integer CONTIGUOUS = 0
) (
    input  wire                        clk,
    input  wire                        rst_n,
    input  wire                        start,
    input  wire [IW:0]                 layout_n,
    input  wire                        layout_installed,
    input  wire                        ql_v,
    output wire                        ql_ready,
    input  wire [7:0]                  ql_head,
    input  wire [NB*128-1:0]           ql_codes,
    input  wire [NB*8-1:0]             ql_sc,
    input  wire [15:0]                 ql_w,
    input  wire [3:0]                  k_valid,
    output wire [3:0]                  k_ready,
    input  wire [3:0]                  k_last,
    input  wire [4*IW-1:0]             k_first,
    input  wire [4*NSL*NK-1:0]         k_kv,
    input  wire [4*NSL*NK-1:0]         k_keep,
    input  wire [4*NSL*NK-1:0]         k_ref,
    input  wire [4*NSL*NK*NB*136-1:0]  k_key,
    output wire                        o_valid,
    output wire                        o_last,
    output wire [63:0]                 o_lv,
    output wire [64*16-1:0]            o_val,
    output wire [64*IW-1:0]            o_idx,
    output wire                        fault,
    output wire                        busy,
    output wire [4*32-1:0]             st_folds,
    output wire [4*32-1:0]             st_pass,
    output wire [4*32-1:0]             st_stall
);
    localparam integer LI = NSL * NK;
    localparam integer KB = NB * 136;
    wire [3:0]          qr, cv, cr, cl, sf, sb;
    wire [4*LO-1:0]     clv;
    wire [4*LO*16-1:0]  cval;
    wire [4*LO*IW-1:0]  cidx;
    wire                hb;
    assign ql_ready = &qr;
    genvar s;
    generate
        for (s = 0; s < 4; s = s + 1) begin : g_stack
            localparam [1:0] SID = s;
            ot_dsrom_edge_stack #(.NSL(NSL), .NK(NK), .NB(NB), .IH(IH), .IW(IW), .K(K), .FPL(FPL), .FML(FML),
                                  .QL(QL), .NC(NC), .FA(FA), .LO(LO), .MACRO(MACRO), .CONTIGUOUS(CONTIGUOUS)) u_st (
                .clk(clk), .rst_n(rst_n), .stack_id(SID), .start(start), .layout_n(layout_n), .layout_installed(layout_installed),
                .ql_v(ql_v && ql_ready), .ql_ready(qr[s]), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
                .ql_w(ql_w),
                .k_valid(k_valid[s]), .k_ready(k_ready[s]), .k_last(k_last[s]), .k_first(k_first[IW*s +: IW]),
                .k_kv(k_kv[LI*s +: LI]), .k_keep(k_keep[LI*s +: LI]), .k_ref(k_ref[LI*s +: LI]),
                .k_key(k_key[LI*KB*s +: LI*KB]),
                .c_valid(cv[s]), .c_ready(cr[s]), .c_last(cl[s]), .c_lv(clv[LO*s +: LO]),
                .c_val(cval[LO*16*s +: LO*16]), .c_idx(cidx[LO*IW*s +: LO*IW]),
                .fault(sf[s]), .busy(sb[s]), .st_folds(st_folds[32*s +: 32]), .st_pass(st_pass[32*s +: 32]),
                .st_stall(st_stall[32*s +: 32]));
        end
    endgenerate
    ot_dsrom_edge_hub #(.WM(LO), .W(64), .VW(16), .IW(IW), .K(K), .MACRO(MACRO), .CONTIGUOUS(CONTIGUOUS)) u_hub (
        .clk(clk), .rst_n(rst_n), .start(start),
        .i_valid(cv), .i_ready(cr), .i_last(cl), .i_lv(clv), .i_val(cval), .i_idx(cidx),
        .o_valid(o_valid), .o_last(o_last), .o_lv(o_lv), .o_val(o_val), .o_idx(o_idx), .busy(hb));
    assign fault = |sf;
    assign busy  = |sb || hb;
endmodule
