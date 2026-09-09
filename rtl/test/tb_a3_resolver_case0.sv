`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The (FAST_SCAN, FAST_WALK) control matrix, on the shipped case-0 payloads.
//
// Two optimisations were reported as one, and the build with both turned off
// was measured "not inert".  Two knobs have four settings, so the question is
// not "is it inert" but "which of the four is the block that shipped".  This
// bench answers it by measurement rather than by reading parameter defaults:
// FIVE resolver banks are driven from ONE stimulus, on the same clock, from
// the same start pulse --
//
//     dut[0]  ot_a3_resolver_bank #(.FAST_SCAN(0), .FAST_WALK(0))
//     dut[1]  ot_a3_resolver_bank #(.FAST_SCAN(0), .FAST_WALK(1))
//     dut[2]  ot_a3_resolver_bank #(.FAST_SCAN(1), .FAST_WALK(0))
//     dut[3]  ot_a3_resolver_bank #(.FAST_SCAN(1), .FAST_WALK(1))
//     dut[4]  ot_a3_resolver_bank_shipped -- a verbatim copy of
//             rtl/abi3/ot_a3_resolver_bank.sv and ot_a3_view_resolver.sv at
//             the commit the deployment campaign's counts were recorded from,
//             taken out of git and renamed, never hand-copied.
//
// Every build's parameters are given at the instantiation, so no default in
// any module decides anything here; the defaults are settled separately, by
// reading them, and this bench settles what each SETTING costs.  dut[4] is the
// control that makes "baseline-equivalent" a measurement: whichever of the
// four reproduces the shipped bank's cycle count, transaction by transaction,
// is the baseline build, and the other three are not.
//
// The stimulus is the shipped case-0 payloads, not constructed traffic:
// tools/build_abi3_resolver_case0_vectors.py replays Qwen3-8B on ROM, prefill,
// sixteen prompt tokens -- case 0 of tools/rtl_abi3_deployment_campaign.py --
// on runtime.sim.device.Device and writes out, per issued OPERATOR, the six
// operand view IDs, the TENSOR_VIEW records verbatim, and the loop stack as
// ot_a3_loop_stack would be holding it.  691 transactions, 2,143 operand
// views.
//
// The cycle counts are only worth reading if every build resolved the right
// views, so each build's published extent, extent axis, rank and element
// offset is checked against the golden resolver's own answer for all 2,143
// views, and the four parameterised builds are checked field-for-field
// against the shipped one.  A build that got a view wrong fails here rather
// than reporting a faster number.
//
// What this bench does NOT establish.  The totals are BANK latency summed over
// the case, not whole-design transaction cycles: the descriptor port is
// modelled (valid one cycle after the request, as ot_a3_device_top's store
// presents it) and nothing else of the sequencer is here.  The same model
// serves all five builds, so the differences between them are sound; the
// whole-design number remains tools/rtl_abi3_deployment_campaign.py's.
//
// To run it, build the stimulus, take the shipped copies out of the history
// the way tools/rtl_abi3_resolver_inertness_check.py does -- never by hand --
// and elaborate them beside the working tree's build:
//
//   python3 tools/build_abi3_resolver_case0_vectors.py --out-dir DIR \
//       --deployment <the certified qwen3-8b-rom bundle> --root <checkpoint>
//   iverilog -g2012 -s tb_a3_resolver_case0 -o case0.vvp \
//       rtl/abi3/ot_a3_pkg.sv rtl/abi3/ot_a3_shared_divider.sv \
//       rtl/abi3/ot_a3_view_resolver.sv rtl/abi3/ot_a3_resolver_bank.sv \
//       <the two resolver sources at the shipped commit, module identifiers
//        suffixed _shipped> rtl/test/tb_a3_resolver_case0.sv
//   (cd DIR && vvp .../case0.vvp +ntxn=691 +ndesc=76)
// ---------------------------------------------------------------------------
module tb_a3_resolver_case0;

    localparam integer NB        = 5;      // builds under test
    localparam integer DESC_MAX  = 1024;   // descriptor records the store holds
    localparam integer TXN_MAX   = 4096;   // transactions
    localparam integer TXN_WORDS = 56;     // 6 view IDs + 4*5 loop + 6*5 golden
    localparam integer LOOP_DEPTH = 4;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg clear = 1'b0;
    always #5 clk = ~clk;

    integer cycle = 0;
    always @(posedge clk) cycle = cycle + 1;

    // -- stimulus ----------------------------------------------------------
    reg [1535:0] desc_mem [0:DESC_MAX-1];
    reg [31:0]   txn_mem  [0:TXN_MAX*TXN_WORDS-1];
    reg [31:0]   sym_mem  [0:2*16];

    integer ntxn = 0;
    integer ndesc = 0;

    reg [511:0] op_payload = 512'd0;
    reg         start = 1'b0;

    // The loop stack of the transaction in flight, held in PACKED vectors and
    // read by an always block with an explicit sensitivity list.  It was first
    // written as an array plus a function called from a continuous assign,
    // copying rtl/test/tb_a3_resolver_bank_equiv.sv, and that is wrong here:
    // this stimulus queries ONE loop ID for hundreds of consecutive
    // transactions while its induction value advances, and a function call in
    // a continuous assign is re-evaluated when its ARGUMENT changes, not when
    // a memory it reads does.  The query port then answered every iteration
    // with iteration zero's value.  All five builds read the same stale value,
    // so it cost no build a cycle and hid in a build-to-build comparison; it
    // showed up only against the golden model's own offsets, which is why they
    // are checked.  Packed vectors and a named sensitivity list cannot go
    // stale.
    reg [LOOP_DEPTH*32-1:0] l_id_v;
    reg [LOOP_DEPTH*32-1:0] l_value_v;
    reg [LOOP_DEPTH-1:0]    l_sym_v;
    reg [LOOP_DEPTH*32-1:0] l_div_v;
    reg [LOOP_DEPTH*32-1:0] l_bound_v;

    reg [ot_a3_pkg::A3_SYMBOL_COUNT*64-1:0] sym_values =
        {(ot_a3_pkg::A3_SYMBOL_COUNT*64){1'b0}};
    reg [ot_a3_pkg::A3_SYMBOL_COUNT-1:0] sym_bound =
        {ot_a3_pkg::A3_SYMBOL_COUNT{1'b0}};

    // -- five builds -------------------------------------------------------
    wire [NB-1:0]      b_req;
    wire [NB*32-1:0]   b_id;
    reg  [NB-1:0]      b_dv, b_df;
    reg  [NB*32-1:0]   b_rid;
    wire [NB-1:0]      b_busy, b_done, b_fault;
    wire [NB*16-1:0]   b_trap;
    wire [NB*6-1:0]    b_sv, b_wr, b_scv;
    wire [NB*6*32-1:0] b_did, b_ext, b_sco;
    wire [NB*6*8-1:0]  b_ax, b_rk;
    wire [NB*6*64-1:0] b_off;
    wire [NB*6*16-1:0] b_obj;
    wire [NB*6*40-1:0] b_lo, b_hi;

    integer reads [0:NB-1];

    genvar b, q;
    generate
        for (b = 0; b < NB; b = b + 1) begin : g_build
            // descriptor port: ot_a3_device_top's model exactly -- valid one
            // cycle after the request, the record out of the array's
            // registered output, an ID at or beyond the store's bound
            // answered with desc_fault and a zero record.
            wire [31:0]   this_id = b_id[b*32 +: 32];
            wire [1535:0] this_dd = b_df[b] ? 1536'd0
                                            : desc_mem[b_rid[b*32 +: 10]];
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    b_dv[b] <= 1'b0;
                    b_df[b] <= 1'b0;
                    b_rid[b*32 +: 32] <= 32'd0;
                end else begin
                    b_dv[b] <= b_req[b];
                    if (b_req[b]) begin
                        b_df[b] <= (this_id >= ndesc);
                        b_rid[b*32 +: 32] <= this_id;
                        reads[b] = reads[b] + 1;
                    end
                end
            end

            // loop stack query ports, six per build
            wire [6*32-1:0] lq_id;
            wire [5:0]      lq_act, lq_sym;
            wire [6*32-1:0] lq_val, lq_div, lq_bnd;
            for (q = 0; q < 6; q = q + 1) begin : g_lq
                reg        hit_act;
                reg [31:0] hit_val;
                reg        hit_sym;
                reg [31:0] hit_div;
                reg [31:0] hit_bnd;
                integer    j;
                always @(lq_id or l_id_v or l_value_v or l_sym_v or
                         l_div_v or l_bound_v) begin
                    hit_act = 1'b0;
                    hit_val = 32'd0;
                    hit_sym = 1'b0;
                    hit_div = 32'd1;
                    hit_bnd = 32'd0;
                    for (j = 0; j < LOOP_DEPTH; j = j + 1) begin
                        if (!hit_act &&
                            (l_id_v[j*32 +: 32] != 32'hffff_ffff) &&
                            (l_id_v[j*32 +: 32] == lq_id[q*32 +: 32])) begin
                            hit_act = 1'b1;
                            hit_val = l_value_v[j*32 +: 32];
                            hit_sym = l_sym_v[j];
                            hit_div = l_div_v[j*32 +: 32];
                            hit_bnd = l_bound_v[j*32 +: 32];
                        end
                    end
                end
                assign lq_act[q]          = hit_act;
                assign lq_val[q*32 +: 32] = hit_val;
                assign lq_sym[q]          = hit_sym;
                assign lq_div[q*32 +: 32] = hit_div;
                assign lq_bnd[q*32 +: 32] = hit_bnd;
            end

            wire [5:0]      dreq;
            wire [6*64-1:0] dnum;
            wire [6*32-1:0] dden;
            wire [5:0]      ddone;
            wire [63:0]     dquot, drem;
            ot_a3_shared_divider #(.REQUESTERS(6)) divider (
                .clk(clk), .rst_n(rst_n), .clear(clear),
                .req(dreq), .num(dnum), .den(dden),
                .grant(), .busy(), .done(ddone), .quot(dquot), .rem(drem));

            if (b < 4) begin : g_knob
                ot_a3_resolver_bank #(
                    .FAST_SCAN((b / 2) % 2),
                    .FAST_WALK(b % 2)
                ) dut (
                    .clk(clk), .rst_n(rst_n), .clear(clear),
                    .start(start), .op_payload(op_payload),
                    .desc_req(b_req[b]), .desc_id(b_id[b*32 +: 32]),
                    .desc_valid(b_dv[b]), .desc_fault(b_df[b]),
                    .desc_data(this_dd),
                    .loop_query_id(lq_id), .loop_query_active(lq_act),
                    .loop_query_value(lq_val),
                    .loop_query_symbol_bounded(lq_sym),
                    .loop_query_divisor(lq_div),
                    .loop_query_bound_value(lq_bnd),
                    .sym_values(sym_values), .sym_bound(sym_bound),
                    .div_req(dreq), .div_num(dnum), .div_den(dden),
                    .div_done(ddone), .div_quot(dquot), .div_rem(drem),
                    .busy(b_busy[b]), .done(b_done[b]), .fault(b_fault[b]),
                    .trap_class(b_trap[b*16 +: 16]),
                    .slot_valid(b_sv[b*6 +: 6]),
                    .slot_descriptor_id(b_did[b*6*32 +: 6*32]),
                    .slot_extent(b_ext[b*6*32 +: 6*32]),
                    .slot_axis(b_ax[b*6*8 +: 6*8]),
                    .slot_offset(b_off[b*6*64 +: 6*64]),
                    .slot_rank(b_rk[b*6*8 +: 6*8]),
                    .slot_object(b_obj[b*6*16 +: 6*16]),
                    .slot_lo(b_lo[b*6*40 +: 6*40]),
                    .slot_hi(b_hi[b*6*40 +: 6*40]),
                    .slot_write(b_wr[b*6 +: 6]),
                    .slot_scale_object(b_sco[b*6*32 +: 6*32]),
                    .slot_scale_valid(b_scv[b*6 +: 6]));
            end else begin : g_shipped
                ot_a3_resolver_bank_shipped dut (
                    .clk(clk), .rst_n(rst_n), .clear(clear),
                    .start(start), .op_payload(op_payload),
                    .desc_req(b_req[b]), .desc_id(b_id[b*32 +: 32]),
                    .desc_valid(b_dv[b]), .desc_fault(b_df[b]),
                    .desc_data(this_dd),
                    .loop_query_id(lq_id), .loop_query_active(lq_act),
                    .loop_query_value(lq_val),
                    .loop_query_symbol_bounded(lq_sym),
                    .loop_query_divisor(lq_div),
                    .loop_query_bound_value(lq_bnd),
                    .sym_values(sym_values), .sym_bound(sym_bound),
                    .div_req(dreq), .div_num(dnum), .div_den(dden),
                    .div_done(ddone), .div_quot(dquot), .div_rem(drem),
                    .busy(b_busy[b]), .done(b_done[b]), .fault(b_fault[b]),
                    .trap_class(b_trap[b*16 +: 16]),
                    .slot_valid(b_sv[b*6 +: 6]),
                    .slot_descriptor_id(b_did[b*6*32 +: 6*32]),
                    .slot_extent(b_ext[b*6*32 +: 6*32]),
                    .slot_axis(b_ax[b*6*8 +: 6*8]),
                    .slot_offset(b_off[b*6*64 +: 6*64]),
                    .slot_rank(b_rk[b*6*8 +: 6*8]),
                    .slot_object(b_obj[b*6*16 +: 6*16]),
                    .slot_lo(b_lo[b*6*40 +: 6*40]),
                    .slot_hi(b_hi[b*6*40 +: 6*40]),
                    .slot_write(b_wr[b*6 +: 6]),
                    .slot_scale_object(b_sco[b*6*32 +: 6*32]),
                    .slot_scale_valid(b_scv[b*6 +: 6]));
            end
        end
    endgenerate

    // -- capture and compare ----------------------------------------------
    integer total   [0:NB-1];   // summed bank latency over the case
    integer worst   [0:NB-1];
    integer arrived [0:NB-1];
    integer lat     [0:NB-1];

    reg         c_fault [0:NB-1];
    reg [15:0]  c_trap  [0:NB-1];
    reg [5:0]   c_sv    [0:NB-1];
    reg [5:0]   c_wr    [0:NB-1];
    reg [5:0]   c_scv   [0:NB-1];
    reg [6*32-1:0] c_did [0:NB-1];
    reg [6*32-1:0] c_ext [0:NB-1];
    reg [6*32-1:0] c_sco [0:NB-1];
    reg [6*8-1:0]  c_ax  [0:NB-1];
    reg [6*8-1:0]  c_rk  [0:NB-1];
    reg [6*64-1:0] c_off [0:NB-1];
    reg [6*16-1:0] c_obj [0:NB-1];
    reg [6*40-1:0] c_lo  [0:NB-1];
    reg [6*40-1:0] c_hi  [0:NB-1];

    integer checks = 0;
    integer mismatches = 0;
    integer golden_checks = 0;
    integer golden_mismatches = 0;
    integer views_seen = 0;
    integer identical_to_shipped [0:NB-1];

    task expect_eq;
        input integer build;
        input [255:0] name;
        input [383:0] got;
        input [383:0] want;
        begin
            checks = checks + 1;
            if (got !== want) begin
                mismatches = mismatches + 1;
                if (mismatches <= 20)
                    $display("FAIL txn=%0d build=%0d %0s: got=%0h shipped=%0h",
                             txn, build, name, got, want);
            end
        end
    endtask

    task expect_golden;
        input integer build;
        input integer slot;
        input [255:0] name;
        input [63:0]  got;
        input [63:0]  want;
        begin
            golden_checks = golden_checks + 1;
            if (got !== want) begin
                golden_mismatches = golden_mismatches + 1;
                if (golden_mismatches <= 20)
                    $display("FAIL txn=%0d build=%0d slot=%0d %0s: rtl=%0d golden=%0d",
                             txn, build, slot, name, got, want);
            end
        end
    endtask

    integer txn, i, s, w, t_req, waited, base;
    reg [31:0] view_id;
    reg [63:0] g_off;
    integer pending;

    initial begin
        for (i = 0; i < DESC_MAX; i = i + 1) desc_mem[i] = 1536'd0;
        for (i = 0; i < TXN_MAX*TXN_WORDS; i = i + 1) txn_mem[i] = 32'd0;
        for (i = 0; i <= 32; i = i + 1) sym_mem[i] = 32'd0;
        for (i = 0; i < NB; i = i + 1) begin
            total[i] = 0; worst[i] = 0; reads[i] = 0;
            identical_to_shipped[i] = 1;
        end
        if (!$value$plusargs("ntxn=%d", ntxn))
            begin $display("FAIL: +ntxn is required"); $finish; end
        if (!$value$plusargs("ndesc=%d", ndesc))
            begin $display("FAIL: +ndesc is required"); $finish; end
        if (ntxn > TXN_MAX || ndesc > DESC_MAX)
            begin $display("FAIL: vector set is larger than this bench"); $finish; end
        $readmemh("resolver_case0_desc.hex", desc_mem, 0, ndesc - 1);
        $readmemh("resolver_case0_txn.hex", txn_mem, 0, ntxn*TXN_WORDS - 1);
        $readmemh("resolver_case0_sym.hex", sym_mem, 0, 32);
        for (i = 0; i < 16; i = i + 1) begin
            sym_values[i*64 +: 64] = {sym_mem[i*2+1], sym_mem[i*2]};
            sym_bound[i] = sym_mem[32][i];
        end

        rst_n = 1'b0;
        repeat (8) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        for (txn = 0; txn < ntxn; txn = txn + 1) begin
            base = txn*TXN_WORDS;
            op_payload = 512'd0;
            for (s = 0; s < 6; s = s + 1)
                op_payload[192 + s*32 +: 32] = txn_mem[base + s];
            for (i = 0; i < LOOP_DEPTH; i = i + 1) begin
                l_id_v[i*32 +: 32]    = txn_mem[base + 6 + i*5 + 0];
                l_value_v[i*32 +: 32] = txn_mem[base + 6 + i*5 + 1];
                l_sym_v[i]            = txn_mem[base + 6 + i*5 + 2][0];
                l_div_v[i*32 +: 32]   = txn_mem[base + 6 + i*5 + 3];
                l_bound_v[i*32 +: 32] = txn_mem[base + 6 + i*5 + 4];
            end

            for (i = 0; i < NB; i = i + 1) begin
                arrived[i] = 0;
                lat[i] = -1;
            end
            @(negedge clk);
            start = 1'b1;
            t_req = cycle;
            @(negedge clk);
            start = 1'b0;
            pending = NB;
            waited = 0;
            while (pending > 0 && waited < 10000) begin
                for (i = 0; i < NB; i = i + 1) begin
                    if (b_done[i] && !arrived[i]) begin
                        arrived[i] = 1;
                        pending = pending - 1;
                        lat[i] = cycle - t_req;
                        c_fault[i] = b_fault[i];
                        c_trap[i]  = b_trap[i*16 +: 16];
                        c_sv[i]    = b_sv[i*6 +: 6];
                        c_did[i]   = b_did[i*6*32 +: 6*32];
                        c_ext[i]   = b_ext[i*6*32 +: 6*32];
                        c_ax[i]    = b_ax[i*6*8 +: 6*8];
                        c_off[i]   = b_off[i*6*64 +: 6*64];
                        c_rk[i]    = b_rk[i*6*8 +: 6*8];
                        c_obj[i]   = b_obj[i*6*16 +: 6*16];
                        c_lo[i]    = b_lo[i*6*40 +: 6*40];
                        c_hi[i]    = b_hi[i*6*40 +: 6*40];
                        c_wr[i]    = b_wr[i*6 +: 6];
                        c_sco[i]   = b_sco[i*6*32 +: 6*32];
                        c_scv[i]   = b_scv[i*6 +: 6];
                    end
                end
                @(negedge clk);
                waited = waited + 1;
            end
            if (pending > 0) begin
                mismatches = mismatches + 1;
                $display("FAIL txn=%0d: %0d builds never asserted done", txn, pending);
            end else begin
                for (i = 0; i < NB; i = i + 1) begin
                    total[i] = total[i] + lat[i];
                    if (lat[i] > worst[i]) worst[i] = lat[i];
                end
                // every build against the shipped block, field for field
                for (i = 0; i < NB-1; i = i + 1) begin
                    if (lat[i] != lat[NB-1]) identical_to_shipped[i] = 0;
                    expect_eq(i, "fault",        {383'd0, c_fault[i]}, {383'd0, c_fault[NB-1]});
                    expect_eq(i, "trap_class",   {368'd0, c_trap[i]},  {368'd0, c_trap[NB-1]});
                    expect_eq(i, "slot_valid",   {378'd0, c_sv[i]},    {378'd0, c_sv[NB-1]});
                    expect_eq(i, "descriptor_id",{192'd0, c_did[i]},   {192'd0, c_did[NB-1]});
                    expect_eq(i, "extent",       {192'd0, c_ext[i]},   {192'd0, c_ext[NB-1]});
                    expect_eq(i, "extent_axis",  {336'd0, c_ax[i]},    {336'd0, c_ax[NB-1]});
                    expect_eq(i, "offset",       c_off[i],             c_off[NB-1]);
                    expect_eq(i, "rank",         {336'd0, c_rk[i]},    {336'd0, c_rk[NB-1]});
                    expect_eq(i, "object",       {288'd0, c_obj[i]},   {288'd0, c_obj[NB-1]});
                    expect_eq(i, "lo",           {144'd0, c_lo[i]},    {144'd0, c_lo[NB-1]});
                    expect_eq(i, "hi",           {144'd0, c_hi[i]},    {144'd0, c_hi[NB-1]});
                    expect_eq(i, "write",        {378'd0, c_wr[i]},    {378'd0, c_wr[NB-1]});
                    expect_eq(i, "scale_object", {192'd0, c_sco[i]},   {192'd0, c_sco[NB-1]});
                    expect_eq(i, "scale_valid",  {378'd0, c_scv[i]},   {378'd0, c_scv[NB-1]});
                end
                // and every build against the golden resolver's own answers
                for (s = 0; s < 6; s = s + 1) begin
                    view_id = txn_mem[base + s];
                    if (view_id !== 32'hffff_ffff) begin
                        w = base + 6 + LOOP_DEPTH*5 + s*5;
                        g_off = {txn_mem[w+4], txn_mem[w+3]};
                        views_seen = views_seen + 1;
                        for (i = 0; i < NB; i = i + 1) begin
                            expect_golden(i, s, "slot_valid",
                                {63'd0, c_sv[i][s]}, 64'd1);
                            expect_golden(i, s, "extent",
                                {32'd0, c_ext[i][s*32 +: 32]},
                                {32'd0, txn_mem[w+0]});
                            expect_golden(i, s, "extent_axis",
                                {56'd0, c_ax[i][s*8 +: 8]},
                                {56'd0, txn_mem[w+1][7:0]});
                            expect_golden(i, s, "rank",
                                {56'd0, c_rk[i][s*8 +: 8]},
                                {56'd0, txn_mem[w+2][7:0]});
                            expect_golden(i, s, "element_offset",
                                c_off[i][s*64 +: 64], g_off);
                        end
                    end
                end
            end
        end

        $display("");
        $display("case 0 = qwen3-8b-rom-single-chip/prefill, %0d transactions, %0d operand views",
                 ntxn, views_seen);
        $display("build                       cycles   worst  reads  same-as-shipped");
        $display("FAST_SCAN=0 FAST_WALK=0  %8d %7d %6d  %0s",
                 total[0], worst[0], reads[0],
                 identical_to_shipped[0] ? "yes" : "NO");
        $display("FAST_SCAN=0 FAST_WALK=1  %8d %7d %6d  %0s",
                 total[1], worst[1], reads[1],
                 identical_to_shipped[1] ? "yes" : "NO");
        $display("FAST_SCAN=1 FAST_WALK=0  %8d %7d %6d  %0s",
                 total[2], worst[2], reads[2],
                 identical_to_shipped[2] ? "yes" : "NO");
        $display("FAST_SCAN=1 FAST_WALK=1  %8d %7d %6d  %0s",
                 total[3], worst[3], reads[3],
                 identical_to_shipped[3] ? "yes" : "NO");
        $display("shipped block (control)  %8d %7d %6d  --", total[4], worst[4], reads[4]);
        $display("");
        $display("saving vs shipped: FAST_SCAN alone=%0d FAST_WALK alone=%0d both=%0d",
                 total[4]-total[2], total[4]-total[1], total[4]-total[3]);
        if (mismatches == 0 && golden_mismatches == 0)
            $display("PASS: resolver case-0 control matrix txns=%0d checks=%0d golden_checks=%0d",
                     ntxn, checks, golden_checks);
        else
            $display("FAIL: mismatches=%0d golden_mismatches=%0d",
                     mismatches, golden_mismatches);
        $finish;
    end
endmodule
