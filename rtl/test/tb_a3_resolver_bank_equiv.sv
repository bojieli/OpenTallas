`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Equivalence sweep for the resolver bank's fast slot walk and the view
// resolver's fast term walk.
//
// Two changes are under test, both cycle removals with no change of function:
//
//   * FAST_SCAN elides ot_a3_resolver_bank's scan state.  The six operand slot
//     IDs are compared with NO_ID at once instead of one per cycle, a priority
//     encoder names the lowest slot still owed a descriptor, and the request
//     for it leaves in the cycle that consumed the previous record instead of
//     the cycle after it.
//   * FAST_WALK folds ot_a3_view_resolver's S_SELECT into the states that
//     already advance the term counter, and accumulates the bounding walk's
//     axis i while presenting axis i + 1.
//
// Their correctness argument is by construction -- the same comparisons, in
// the same order, one state earlier -- but an argument is not a measurement.
// This bench drives BOTH builds from ONE stimulus and requires every published
// result to be bit-identical: the fault flag, the trap class, the per-slot
// valid and descriptor-ID vectors, and all of the resolved per-slot fields
// (offset, extent, extent axis, rank, object, write, lo, hi, scale object,
// scale valid).  It also requires the two builds to have asked the descriptor
// port for the same IDs in the same order, which is what makes "the fault of
// the lowest faulting slot" the same fault in both.
//
// What this bench CANNOT establish, and what caught this change out once:
// both of its builds are elaborations of the same modified source, so a
// difference between the FAST_*=0 build and the block that actually shipped is
// invisible here -- both DUTs would carry it, and once did.  That question is
// rtl/test/tb_a3_resolver_bank_inert.sv's: it drives the 0 build against a
// verbatim copy of the shipped source, taken from the repository history by
// tools/rtl_abi3_resolver_inertness_check.py, and requires cycle-exact
// identity.  Read the two together, inertness first; this bench alone is an
// equivalence between two modified builds.
//
// What is deliberately NOT compared: latency.  Latency is the whole point of
// the change, so requiring the builds to agree on it would be requiring the
// change not to have happened.  Each build is timed from the same start pulse
// against one free-running counter, following
// rtl/test/tb_a3_shared_divider_equiv.sv, and both figures are reported.
//
// The stimulus is hostile rather than kind.  Every one of the 64 slot
// occupancy patterns is driven, so the priority encoder is asked for a first
// slot at every position and for an operator that names nothing.  Every
// fail-closed path the resolver has is driven at a slot other than zero as
// well as at zero, so a change in the walk ORDER would show up as a changed
// trap class rather than a changed cycle count: a malformed descriptor header
// (bad magic, wrong type, wrong major, wrong payload offset), an out-of-range
// descriptor ID, an A18 axis at or beyond the rank, a rejected CONSTANT
// selector, a loop induction naming a closed loop, an unbound runtime symbol,
// a symbol index outside the frozen registry, and an edge mask naming a closed
// loop.  The A18 divider path, the A26 edge phase, the 64-bit symbol second
// pass, rank zero, rank six and offsets that overflow the 40-bit range are all
// driven, because the fast walk changes the state each of them returns to.
// ---------------------------------------------------------------------------
module tb_a3_resolver_bank_equiv;

    localparam integer NDESC = 64;      // descriptor IDs the store model holds
    localparam integer NLOOP = 8;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg clear = 1'b0;
    always #5 clk = ~clk;

    integer cycle = 0;
    always @(posedge clk) cycle = cycle + 1;

    // -- one stimulus ------------------------------------------------------
    reg [1535:0] desc_mem [0:NDESC-1];
    reg [511:0]  op_payload = 512'd0;
    reg          start = 1'b0;

    // the loop stack, modelled here so the stimulus is under this bench's
    // control and identical for both builds
    reg [31:0] l_id     [0:NLOOP-1];
    reg        l_active [0:NLOOP-1];
    reg [31:0] l_value  [0:NLOOP-1];
    reg        l_sym    [0:NLOOP-1];
    reg [31:0] l_div    [0:NLOOP-1];
    reg [31:0] l_bound  [0:NLOOP-1];

    // {active, value, symbolic, divisor, bound}
    function [97:0] loop_lookup;
        input [31:0] qid;
        integer j;
        reg found;
        begin
            loop_lookup = 98'd0;
            found = 1'b0;
            for (j = 0; j < NLOOP; j = j + 1) begin
                if (!found && l_active[j] && (l_id[j] == qid)) begin
                    found = 1'b1;
                    loop_lookup = {1'b1, l_value[j], l_sym[j], l_div[j], l_bound[j]};
                end
            end
        end
    endfunction

    reg [ot_a3_pkg::A3_SYMBOL_COUNT*64-1:0] sym_values =
        {(ot_a3_pkg::A3_SYMBOL_COUNT*64){1'b0}};
    reg [ot_a3_pkg::A3_SYMBOL_COUNT-1:0] sym_bound =
        {ot_a3_pkg::A3_SYMBOL_COUNT{1'b0}};

    // -- per-build descriptor port -----------------------------------------
    // ot_a3_device_top's model exactly: valid one cycle after the request, the
    // record read out of the array's registered output, an ID at or beyond the
    // store's bound answered with desc_fault and a zero record.  The port is
    // per build because the two builds request at different times; its
    // behaviour, and every record in it, is the same one stimulus.
    wire        req_f, req_s;
    wire [31:0] id_f,  id_s;
    reg         dv_f = 1'b0, dv_s = 1'b0;
    reg         df_f = 1'b0, df_s = 1'b0;
    reg [31:0]  rid_f = 32'd0, rid_s = 32'd0;
    wire [1535:0] dd_f = df_f ? 1536'd0 : desc_mem[rid_f[5:0]];
    wire [1535:0] dd_s = df_s ? 1536'd0 : desc_mem[rid_s[5:0]];

    // the request order each build asked for, so a reordered walk is caught
    integer reads_f = 0, reads_s = 0;
    reg [31:0] order_f [0:15];
    reg [31:0] order_s [0:15];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dv_f <= 1'b0; df_f <= 1'b0; rid_f <= 32'd0;
        end else begin
            dv_f <= req_f;
            if (req_f) begin
                df_f  <= (id_f >= NDESC);
                rid_f <= id_f;
                if (reads_f < 16) order_f[reads_f] = id_f;
                reads_f = reads_f + 1;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dv_s <= 1'b0; df_s <= 1'b0; rid_s <= 32'd0;
        end else begin
            dv_s <= req_s;
            if (req_s) begin
                df_s  <= (id_s >= NDESC);
                rid_s <= id_s;
                if (reads_s < 16) order_s[reads_s] = id_s;
                reads_s = reads_s + 1;
            end
        end
    end

    // -- the two builds ----------------------------------------------------
    wire [6*32-1:0] lq_id_f, lq_id_s;
    wire [5:0]      lq_act_f, lq_act_s, lq_sym_f, lq_sym_s;
    wire [6*32-1:0] lq_val_f, lq_val_s, lq_div_f, lq_div_s, lq_bnd_f, lq_bnd_s;
    genvar q;
    generate
        for (q = 0; q < 6; q = q + 1) begin : g_lq
            wire [97:0] hit_f = loop_lookup(lq_id_f[q*32 +: 32]);
            wire [97:0] hit_s = loop_lookup(lq_id_s[q*32 +: 32]);
            assign lq_act_f[q]           = hit_f[97];
            assign lq_val_f[q*32 +: 32]  = hit_f[96:65];
            assign lq_sym_f[q]           = hit_f[64];
            assign lq_div_f[q*32 +: 32]  = hit_f[63:32];
            assign lq_bnd_f[q*32 +: 32]  = hit_f[31:0];
            assign lq_act_s[q]           = hit_s[97];
            assign lq_val_s[q*32 +: 32]  = hit_s[96:65];
            assign lq_sym_s[q]           = hit_s[64];
            assign lq_div_s[q*32 +: 32]  = hit_s[63:32];
            assign lq_bnd_s[q*32 +: 32]  = hit_s[31:0];
        end
    endgenerate

    wire [5:0]      dreq_f, dreq_s;
    wire [6*64-1:0] dnum_f, dnum_s;
    wire [6*32-1:0] dden_f, dden_s;
    wire [5:0]      ddone_f, ddone_s;
    wire [63:0]     dquot_f, dquot_s, drem_f, drem_s;

    ot_a3_shared_divider #(.REQUESTERS(6)) div_f (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .req(dreq_f), .num(dnum_f), .den(dden_f),
        .grant(), .busy(), .done(ddone_f), .quot(dquot_f), .rem(drem_f));
    ot_a3_shared_divider #(.REQUESTERS(6)) div_s (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .req(dreq_s), .num(dnum_s), .den(dden_s),
        .grant(), .busy(), .done(ddone_s), .quot(dquot_s), .rem(drem_s));

    wire        busy_f, done_f, fault_f;
    wire [15:0] trap_f;
    wire [5:0]  sv_f, swr_f, ssv_f;
    wire [6*32-1:0] sdid_f, sext_f, sso_f;
    wire [6*8-1:0]  sax_f, srk_f;
    wire [6*64-1:0] soff_f;
    wire [6*16-1:0] sobj_f;
    wire [6*40-1:0] slo_f, shi_f;

    wire        busy_s, done_s, fault_s;
    wire [15:0] trap_s;
    wire [5:0]  sv_s, swr_s, ssv_s;
    wire [6*32-1:0] sdid_s, sext_s, sso_s;
    wire [6*8-1:0]  sax_s, srk_s;
    wire [6*64-1:0] soff_s;
    wire [6*16-1:0] sobj_s;
    wire [6*40-1:0] slo_s, shi_s;

    ot_a3_resolver_bank #(.FAST_SCAN(1), .FAST_WALK(1)) dut_fast (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .start(start), .op_payload(op_payload),
        .desc_req(req_f), .desc_id(id_f), .desc_valid(dv_f),
        .desc_fault(df_f), .desc_data(dd_f),
        .loop_query_id(lq_id_f), .loop_query_active(lq_act_f),
        .loop_query_value(lq_val_f), .loop_query_symbol_bounded(lq_sym_f),
        .loop_query_divisor(lq_div_f), .loop_query_bound_value(lq_bnd_f),
        .sym_values(sym_values), .sym_bound(sym_bound),
        .div_req(dreq_f), .div_num(dnum_f), .div_den(dden_f),
        .div_done(ddone_f), .div_quot(dquot_f), .div_rem(drem_f),
        .busy(busy_f), .done(done_f), .fault(fault_f), .trap_class(trap_f),
        .slot_valid(sv_f), .slot_descriptor_id(sdid_f), .slot_extent(sext_f),
        .slot_axis(sax_f), .slot_offset(soff_f), .slot_rank(srk_f),
        .slot_object(sobj_f), .slot_lo(slo_f), .slot_hi(shi_f),
        .slot_write(swr_f), .slot_scale_object(sso_f), .slot_scale_valid(ssv_f));

    ot_a3_resolver_bank #(.FAST_SCAN(0), .FAST_WALK(0)) dut_slow (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .start(start), .op_payload(op_payload),
        .desc_req(req_s), .desc_id(id_s), .desc_valid(dv_s),
        .desc_fault(df_s), .desc_data(dd_s),
        .loop_query_id(lq_id_s), .loop_query_active(lq_act_s),
        .loop_query_value(lq_val_s), .loop_query_symbol_bounded(lq_sym_s),
        .loop_query_divisor(lq_div_s), .loop_query_bound_value(lq_bnd_s),
        .sym_values(sym_values), .sym_bound(sym_bound),
        .div_req(dreq_s), .div_num(dnum_s), .div_den(dden_s),
        .div_done(ddone_s), .div_quot(dquot_s), .div_rem(drem_s),
        .busy(busy_s), .done(done_s), .fault(fault_s), .trap_class(trap_s),
        .slot_valid(sv_s), .slot_descriptor_id(sdid_s), .slot_extent(sext_s),
        .slot_axis(sax_s), .slot_offset(soff_s), .slot_rank(srk_s),
        .slot_object(sobj_s), .slot_lo(slo_s), .slot_hi(shi_s),
        .slot_write(swr_s), .slot_scale_object(sso_s), .slot_scale_valid(ssv_s));

    // -- capture and compare ----------------------------------------------
    integer cases = 0, checks = 0, mismatch = 0;
    integer fast_lat_total = 0, slow_lat_total = 0, timed = 0;
    integer fast_worst = 0, slow_worst = 0;
    integer faulting_cases = 0;

    reg         c_fault_f, c_fault_s;
    reg [15:0]  c_trap_f,  c_trap_s;
    reg [5:0]   c_sv_f, c_sv_s, c_wr_f, c_wr_s, c_scv_f, c_scv_s;
    reg [6*32-1:0] c_did_f, c_did_s, c_ext_f, c_ext_s, c_sco_f, c_sco_s;
    reg [6*8-1:0]  c_ax_f, c_ax_s, c_rk_f, c_rk_s;
    reg [6*64-1:0] c_off_f, c_off_s;
    reg [6*16-1:0] c_ob_f, c_ob_s;
    reg [6*40-1:0] c_lo_f, c_lo_s, c_hi_f, c_hi_s;

    task expect_eq;
        input [255:0] name;
        input [383:0] got;
        input [383:0] want;
        begin
            checks = checks + 1;
            if (got !== want) begin
                mismatch = mismatch + 1;
                $display("FAIL case=%0d %0s: fast=%0h slow=%0h",
                         cases, name, got, want);
            end
        end
    endtask

    integer t_req, t_f, t_s, waited, k;

    task run_case;
        begin
            cases = cases + 1;
            reads_f = 0; reads_s = 0;
            @(negedge clk);
            start = 1'b1;
            t_req = cycle;
            @(negedge clk);
            start = 1'b0;
            t_f = -1; t_s = -1; waited = 0;
            while ((t_f < 0 || t_s < 0) && waited < 4000) begin
                if (done_f && t_f < 0) begin
                    t_f = cycle - t_req;
                    c_fault_f = fault_f; c_trap_f = trap_f;
                    c_sv_f = sv_f; c_did_f = sdid_f; c_ext_f = sext_f;
                    c_ax_f = sax_f; c_off_f = soff_f; c_rk_f = srk_f;
                    c_ob_f = sobj_f; c_lo_f = slo_f; c_hi_f = shi_f;
                    c_wr_f = swr_f; c_sco_f = sso_f; c_scv_f = ssv_f;
                end
                if (done_s && t_s < 0) begin
                    t_s = cycle - t_req;
                    c_fault_s = fault_s; c_trap_s = trap_s;
                    c_sv_s = sv_s; c_did_s = sdid_s; c_ext_s = sext_s;
                    c_ax_s = sax_s; c_off_s = soff_s; c_rk_s = srk_s;
                    c_ob_s = sobj_s; c_lo_s = slo_s; c_hi_s = shi_s;
                    c_wr_s = swr_s; c_sco_s = sso_s; c_scv_s = ssv_s;
                end
                @(negedge clk); waited = waited + 1;
            end
            if (t_f < 0 || t_s < 0) begin
                mismatch = mismatch + 1;
                $display("FAIL case=%0d a build never asserted done (fast=%0d slow=%0d)",
                         cases, t_f, t_s);
            end else begin
                expect_eq("fault",         {383'd0, c_fault_f}, {383'd0, c_fault_s});
                expect_eq("trap_class",    {368'd0, c_trap_f},  {368'd0, c_trap_s});
                expect_eq("slot_valid",    {378'd0, c_sv_f},    {378'd0, c_sv_s});
                expect_eq("descriptor_id", {192'd0, c_did_f},   {192'd0, c_did_s});
                expect_eq("extent",        {192'd0, c_ext_f},   {192'd0, c_ext_s});
                expect_eq("extent_axis",   {336'd0, c_ax_f},    {336'd0, c_ax_s});
                expect_eq("offset",        c_off_f,             c_off_s);
                expect_eq("rank",          {336'd0, c_rk_f},    {336'd0, c_rk_s});
                expect_eq("object",        {288'd0, c_ob_f},    {288'd0, c_ob_s});
                expect_eq("lo",            {144'd0, c_lo_f},    {144'd0, c_lo_s});
                expect_eq("hi",            {144'd0, c_hi_f},    {144'd0, c_hi_s});
                expect_eq("write",         {378'd0, c_wr_f},    {378'd0, c_wr_s});
                expect_eq("scale_object",  {192'd0, c_sco_f},   {192'd0, c_sco_s});
                expect_eq("scale_valid",   {378'd0, c_scv_f},   {378'd0, c_scv_s});
                // the descriptor port saw the same IDs in the same order
                expect_eq("read_count", {352'd0, reads_f[31:0]},
                                        {352'd0, reads_s[31:0]});
                if (reads_f == reads_s)
                    for (k = 0; k < reads_f && k < 16; k = k + 1)
                        expect_eq("read_order", {352'd0, order_f[k]},
                                                {352'd0, order_s[k]});
                if (c_fault_f) faulting_cases = faulting_cases + 1;
                timed = timed + 1;
                fast_lat_total = fast_lat_total + t_f;
                slow_lat_total = slow_lat_total + t_s;
                if (t_f > fast_worst) fast_worst = t_f;
                if (t_s > slow_worst) slow_worst = t_s;
            end
            repeat (3) @(negedge clk);
        end
    endtask

    // -- descriptor construction ------------------------------------------
    integer d, i;
    reg [1023:0] pay;

    // A well-formed TENSOR_VIEW header around a payload.
    task put_view;
        input integer  id;
        input [31:0]   object;
        input [31:0]   perms;
        input [1023:0] payload;
        begin
            desc_mem[id] = 1536'd0;
            desc_mem[id][31:0]     = ot_a3_pkg::A3_DESCRIPTOR_MAGIC;
            desc_mem[id][47:32]    = ot_a3_pkg::A3_DESC_TENSOR_VIEW;
            desc_mem[id][55:48]    = ot_a3_pkg::A3_TYPE_MAJOR;
            desc_mem[id][159:128]  = object;
            desc_mem[id][287:256]  = perms;
            desc_mem[id][351:320]  = 32'd64;
            desc_mem[id][1535:512] = payload;
        end
    endtask

    task base_payload;
        input [7:0]  dtype;
        input [7:0]  rank;
        input [7:0]  terms;
        input [63:0] offset;
        begin
            pay = 1024'd0;
            pay[7:0]     = dtype;
            pay[15:8]    = rank;
            pay[31:24]   = terms;
            pay[63:32]   = ot_a3_pkg::A3_NO_ID;     // no scale object
            pay[127:96]  = ot_a3_pkg::A3_NO_ID;     // no edge mask
            pay[191:128] = offset;
            pay[223:192] = 32'd8;   pay[415:384] = 32'd1;
            pay[255:224] = 32'd4;   pay[447:416] = 32'd8;
            pay[287:256] = 32'd3;   pay[479:448] = 32'd32;
            pay[319:288] = 32'd2;   pay[511:480] = 32'd96;
            pay[351:320] = 32'd5;   pay[543:512] = 32'd192;
            pay[383:352] = 32'd7;   pay[575:544] = 32'd960;
        end
    endtask

    task set_term;
        input integer  which;
        input [15:0]   kind;
        input [15:0]   index;
        input [31:0]   stride;
        begin
            case (which)
                0: begin pay[591:576] = kind; pay[607:592] = index;
                         pay[639:608] = stride; end
                1: begin pay[655:640] = kind; pay[671:656] = index;
                         pay[703:672] = stride; end
                2: begin pay[719:704] = kind; pay[735:720] = index;
                         pay[767:736] = stride; end
                default: begin pay[783:768] = kind; pay[799:784] = index;
                               pay[831:800] = stride; end
            endcase
        end
    endtask

    task set_a18;
        input [31:0] unit;
        input [31:0] numerator;
        input [31:0] bias;
        input [7:0]  axis;
        begin
            pay[895:864] = unit;
            pay[927:896] = numerator;
            pay[959:928] = bias;
            pay[967:960] = axis;
        end
    endtask

    task set_slots;
        input [31:0] a, b, c2, d2, e, f;
        begin
            op_payload = 512'd0;
            op_payload[223:192] = a;
            op_payload[255:224] = b;
            op_payload[287:256] = c2;
            op_payload[319:288] = d2;
            op_payload[351:320] = e;
            op_payload[383:352] = f;
        end
    endtask

    task slots_from_mask;
        input [5:0]  mask;
        input [31:0] id;
        begin
            op_payload = 512'd0;
            op_payload[223:192] = mask[0] ? id : ot_a3_pkg::A3_NO_ID;
            op_payload[255:224] = mask[1] ? id : ot_a3_pkg::A3_NO_ID;
            op_payload[287:256] = mask[2] ? id : ot_a3_pkg::A3_NO_ID;
            op_payload[319:288] = mask[3] ? id : ot_a3_pkg::A3_NO_ID;
            op_payload[351:320] = mask[4] ? id : ot_a3_pkg::A3_NO_ID;
            op_payload[383:352] = mask[5] ? id : ot_a3_pkg::A3_NO_ID;
        end
    endtask

    integer m, s, seed;
    reg [5:0] rmask;
    reg [31:0] rid;

    initial begin
        for (d = 0; d < NDESC; d = d + 1) desc_mem[d] = 1536'd0;
        for (i = 0; i < NLOOP; i = i + 1) begin
            l_id[i] = ot_a3_pkg::A3_NO_ID; l_active[i] = 1'b0;
            l_value[i] = 32'd0; l_sym[i] = 1'b0;
            l_div[i] = 32'd1; l_bound[i] = 32'd0;
        end

        // Four open loops: one plain, two symbol-bounded with different
        // divisors, one symbol-bounded whose iteration is already past the
        // extent so the S_SCALE early exit is driven.
        l_id[0] = 32'd10; l_active[0] = 1'b1; l_value[0] = 32'd3;
        l_sym[0] = 1'b0;  l_div[0] = 32'd1;  l_bound[0] = 32'd0;
        l_id[1] = 32'd11; l_active[1] = 1'b1; l_value[1] = 32'd2;
        l_sym[1] = 1'b1;  l_div[1] = 32'd8;  l_bound[1] = 32'd20;
        l_id[2] = 32'd12; l_active[2] = 1'b1; l_value[2] = 32'd1;
        l_sym[2] = 1'b1;  l_div[2] = 32'd3;  l_bound[2] = 32'd7;
        l_id[3] = 32'd13; l_active[3] = 1'b1; l_value[3] = 32'd9;
        l_sym[3] = 1'b1;  l_div[3] = 32'd8;  l_bound[3] = 32'd4;

        // Bound symbols; symbol 5 carries a value above 2^32 so the offset's
        // second pass is driven, and symbols 7..15 stay unbound.
        for (i = 0; i < 6; i = i + 1) begin
            sym_values[i*64 +: 64] = {32'd0, 32'd4 + i[31:0]};
            sym_bound[i] = 1'b1;
        end
        sym_values[5*64 +: 64] = 64'h0000_0003_0000_0007;
        sym_bound[6] = 1'b1;
        sym_values[6*64 +: 64] = 64'd0;

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        // ---- 1. a plain rank-2, one-term view in every slot pattern ------
        base_payload(8'h04, 8'd2, 8'd1, 64'd64);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd10, 32'd8);
        put_view(1, 32'd7, 32'd2, pay);
        for (m = 0; m < 64; m = m + 1) begin
            slots_from_mask(m[5:0], 32'd1);
            run_case;
        end

        // ---- 2. a different view per slot, so a reorder is visible -------
        for (d = 2; d < 8; d = d + 1) begin
            base_payload(8'h04, 8'd3, 8'd1, {58'd0, d[5:0]});
            set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL},
                     {13'd0, d[2:0]}, 32'd16);
            put_view(d, {26'd0, d[5:0]}, (d[0] ? 32'd2 : 32'd1), pay);
        end
        set_slots(32'd2, 32'd3, 32'd4, 32'd5, 32'd6, 32'd7);
        run_case;
        set_slots(32'd7, 32'd6, 32'd5, 32'd4, 32'd3, 32'd2);
        run_case;

        // ---- 3. every fail-closed path, at slot 0 and away from it -------
        // 3a. malformed headers
        base_payload(8'h04, 8'd2, 8'd0, 64'd0);
        put_view(20, 32'd1, 32'd1, pay);
        desc_mem[20][31:0] = 32'hdead_beef;              // bad magic
        put_view(21, 32'd1, 32'd1, pay);
        desc_mem[21][47:32] = 16'h0003;                  // not a TENSOR_VIEW
        put_view(22, 32'd1, 32'd1, pay);
        desc_mem[22][55:48] = 8'd9;                      // wrong major
        put_view(23, 32'd1, 32'd1, pay);
        desc_mem[23][351:320] = 32'd128;                 // wrong payload offset
        for (d = 20; d <= 23; d = d + 1) begin
            set_slots(d[31:0], 32'd1, ot_a3_pkg::A3_NO_ID, ot_a3_pkg::A3_NO_ID,
                      32'd1, ot_a3_pkg::A3_NO_ID);
            run_case;
            set_slots(32'd1, ot_a3_pkg::A3_NO_ID, 32'd1, ot_a3_pkg::A3_NO_ID,
                      d[31:0], 32'd1);
            run_case;
        end
        // 3b. an ID beyond the store: desc_fault
        set_slots(32'd1, 32'd999, ot_a3_pkg::A3_NO_ID, ot_a3_pkg::A3_NO_ID,
                  ot_a3_pkg::A3_NO_ID, 32'd1);
        run_case;
        set_slots(ot_a3_pkg::A3_NO_ID, 32'd1, ot_a3_pkg::A3_NO_ID,
                  ot_a3_pkg::A3_NO_ID, 32'd999, ot_a3_pkg::A3_NO_ID);
        run_case;

        // 3c. resolver refusals, each its own descriptor
        base_payload(8'h04, 8'd2, 8'd0, 64'd0);
        set_a18(32'd1, 32'd1, 32'd0, 8'd5);              // axis >= rank
        put_view(24, 32'd1, 32'd1, pay);
        base_payload(8'h04, 8'd2, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_CONSTANT}, 16'd0, 32'd4);
        put_view(25, 32'd1, 32'd1, pay);                 // CONSTANT is rejected
        base_payload(8'h04, 8'd2, 8'd1, 64'd0);
        set_term(0, 16'd77, 16'd0, 32'd4);
        put_view(26, 32'd1, 32'd1, pay);                 // unknown selector kind
        base_payload(8'h04, 8'd2, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd99, 32'd4);
        put_view(27, 32'd1, 32'd1, pay);                 // loop is not open
        base_payload(8'h04, 8'd2, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL}, 16'd9, 32'd4);
        put_view(28, 32'd1, 32'd1, pay);                 // symbol unbound
        base_payload(8'h04, 8'd2, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL}, 16'd40, 32'd4);
        put_view(29, 32'd1, 32'd1, pay);                 // outside the registry
        base_payload(8'h04, 8'd2, 8'd0, 64'd0);
        pay[127:96] = 32'd99;                            // edge mask, loop closed
        put_view(30, 32'd1, 32'd1, pay);
        // a refusal on the SECOND term of a view, so the fold of S_SELECT is
        // exercised with a term still to come
        base_payload(8'h04, 8'd2, 8'd3, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd10, 32'd4);
        set_term(1, {8'd0, ot_a3_pkg::A3_SELECTOR_CONSTANT}, 16'd0, 32'd4);
        set_term(2, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd10, 32'd4);
        put_view(31, 32'd1, 32'd1, pay);
        for (d = 24; d <= 31; d = d + 1) begin
            set_slots(d[31:0], 32'd1, ot_a3_pkg::A3_NO_ID, 32'd1,
                      ot_a3_pkg::A3_NO_ID, ot_a3_pkg::A3_NO_ID);
            run_case;
            set_slots(32'd1, ot_a3_pkg::A3_NO_ID, 32'd1, ot_a3_pkg::A3_NO_ID,
                      d[31:0], 32'd1);
            run_case;
            // and alone, so the trap is not masked by a lower slot
            slots_from_mask(6'b010000, d[31:0]);
            run_case;
        end

        // ---- 4. the shapes the fast walk changes the exit state of -------
        // 4a. zero terms, ranks 0 through 6
        for (i = 0; i <= 6; i = i + 1) begin
            base_payload(8'h30, i[7:0], 8'd0, 64'd12);
            put_view(32, 32'd3, 32'd2, pay);
            slots_from_mask(6'b001011, 32'd32);
            run_case;
        end
        // 4b. one to four terms, mixed kinds
        for (i = 1; i <= 4; i = i + 1) begin
            base_payload(8'h02, 8'd4, i[7:0], 64'd5);
            set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd11, 32'd8);
            set_term(1, {8'd0, ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL}, 16'd2, 32'd3);
            set_term(2, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd12, 32'd1);
            set_term(3, {8'd0, ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL}, 16'd5, 32'd2);
            put_view(33, 32'd3, 32'd2, pay);
            slots_from_mask(6'b111111, 32'd33);
            run_case;
        end
        // 4c. the A18 divider path: a unit that divides, one that does not,
        //     a bias, and a non-zero extent axis
        base_payload(8'h04, 8'd4, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd11, 32'd8);
        set_a18(32'd2, 32'd4, 32'd0, 8'd0);
        put_view(34, 32'd3, 32'd2, pay);
        base_payload(8'h04, 8'd4, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd12, 32'd8);
        set_a18(32'd5, 32'd3, 32'd0, 8'd0);
        put_view(35, 32'd3, 32'd2, pay);
        base_payload(8'h04, 8'd4, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd11, 32'd64);
        set_a18(32'd1, 32'd1, 32'd128, 8'd1);
        put_view(36, 32'd3, 32'd2, pay);
        // 4d. an iteration past the extent: the S_SCALE early exit
        base_payload(8'h04, 8'd4, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd13, 32'd8);
        put_view(37, 32'd3, 32'd2, pay);
        // 4e. an A26 edge mask on an open symbol-bounded loop, with terms
        base_payload(8'h04, 8'd4, 8'd2, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL}, 16'd1, 32'd4);
        set_term(1, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd10, 32'd2);
        pay[127:96] = 32'd11;
        put_view(38, 32'd3, 32'd2, pay);
        // 4f. an edge mask on an open loop that is NOT symbol bounded
        base_payload(8'h04, 8'd4, 8'd0, 64'd0);
        pay[127:96] = 32'd10;
        put_view(39, 32'd3, 32'd2, pay);
        // 4g. an edge mask with a non-identity A18, so the divider is entered
        //     inside the edge phase, both when the unit divides and when it
        //     does not
        base_payload(8'h04, 8'd4, 8'd0, 64'd0);
        pay[127:96] = 32'd12;
        set_a18(32'd5, 32'd3, 32'd0, 8'd0);
        put_view(40, 32'd3, 32'd2, pay);
        base_payload(8'h04, 8'd4, 8'd0, 64'd0);
        pay[127:96] = 32'd11;
        set_a18(32'd2, 32'd4, 32'd1, 8'd0);
        put_view(41, 32'd3, 32'd2, pay);
        // 4h. a symbol above 2^32: the offset's second pass
        base_payload(8'h04, 8'd2, 8'd1, 64'd0);
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_RUNTIME_SYMBOL}, 16'd5, 32'd6);
        put_view(42, 32'd3, 32'd2, pay);
        // 4i. an offset and strides that overflow the 40-bit range
        base_payload(8'h06, 8'd6, 8'd0, 64'hFFFF_FFFF_0000_0000);
        put_view(43, 32'd3, 32'd2, pay);
        // 4j. a scale object, so out_scale_valid is not always zero
        base_payload(8'h05, 8'd3, 8'd1, 64'd9);
        pay[63:32] = 32'd77;
        set_term(0, {8'd0, ot_a3_pkg::A3_SELECTOR_LOOP_INDUCTION}, 16'd11, 32'd8);
        put_view(44, 32'd3, 32'd2, pay);
        for (d = 34; d <= 44; d = d + 1) begin
            slots_from_mask(6'b100001, d[31:0]);
            run_case;
            slots_from_mask(6'b111111, d[31:0]);
            run_case;
            slots_from_mask(6'b001000, d[31:0]);
            run_case;
        end

        // ---- 5. randomised operators over the whole descriptor set -------
        // A mix of the well-formed views above, the malformed ones, IDs that
        // hold a zero record (which is not a TENSOR_VIEW and must trap) and
        // IDs past the store's bound.
        seed = 32'd20260909;
        for (i = 0; i < 600; i = i + 1) begin
            rmask = $random(seed);
            op_payload = 512'd0;
            for (s = 0; s < 6; s = s + 1) begin
                if (rmask[s]) begin
                    rid = $random(seed);
                    rid = (rid % 50) + 1;
                    op_payload[192 + s*32 +: 32] = rid;
                end else begin
                    op_payload[192 + s*32 +: 32] = ot_a3_pkg::A3_NO_ID;
                end
            end
            run_case;
        end

        // ---- 6. an abort in mid-walk, at every offset it can land on ----
        // The fast build carries a ``pending`` register the shipped walk does
        // not, and it is further into the walk than the shipped one is when
        // the abort arrives.  What must agree is the transaction AFTER the
        // abort, so the recovery is what is compared: every slot is named in
        // it, so no result carried over from the aborted walk survives into
        // the comparison.
        for (i = 1; i <= 24; i = i + 1) begin
            slots_from_mask(6'b111111, 32'd33);
            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            repeat (i) @(negedge clk);
            clear = 1'b1;
            @(negedge clk);
            clear = 1'b0;
            repeat (4) @(negedge clk);
            if (busy_f || busy_s) begin
                mismatch = mismatch + 1;
                $display("FAIL: a build is still busy after clear (fast=%0d slow=%0d) at offset %0d",
                         busy_f, busy_s, i);
            end
            slots_from_mask(6'b111111, 32'd38);
            run_case;
        end

        $display("cases=%0d checks=%0d mismatches=%0d faulting=%0d",
                 cases, checks, mismatch, faulting_cases);
        $display("mean latency: fast=%0d slow=%0d over %0d case(s); worst fast=%0d slow=%0d",
                 fast_lat_total / timed, slow_lat_total / timed, timed,
                 fast_worst, slow_worst);
        if (mismatch == 0)
            $display("PASS: fast resolver walk equals the shipped walk cases=%0d checks=%0d",
                     cases, checks);
        else
            $display("FAIL: %0d mismatch(es)", mismatch);
        $finish;
    end

endmodule
