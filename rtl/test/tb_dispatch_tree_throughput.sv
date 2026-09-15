`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Does a HIERARCHICAL distributor keep a WIDE array busy, and does it keep it
// busy with the RIGHT operands?
//
// This is rtl/test/tb_cluster_dispatch_throughput.sv taken to the widths the
// capabilities actually require. tools/audit_control_path_throughput.py reports
// required_fanout 34 for the 16-unit capabilities, 68 for rom_qwen3 and 1,076
// for rom_deepseek_v4 and rom_deepseek_v41_wafer; the flat dispatcher has a
// routed record at 16 units and nothing beyond it. The unit count is a parameter
// here -- UNITS = LEAVES x GROUP -- so the same bench and the same metric run at
// every one of those widths.
//
// FOUR THINGS ARE MEASURED, and the first two gate the third.
//
//  1. FUNCTIONAL, at width. Every unit is given the same weight tile and the
//     same activations, so every accumulator in every unit must be bit-identical
//     to testdata/rtl/a3_mac_tile/expected.hex -- the vectors ot_mac_tile was
//     qualified against. UNITS x LANES results are checked, not one.
//  2. SUB-RANGE, at width. A broadcast that gave every unit the same work would
//     pass check 1 and still be useless for a real GEMM, because the units must
//     differ by which output tile they own. So every leaf's `cu_tile_base` is
//     sampled on its own launch and checked to be exactly the descriptor's grid
//     origin plus that leaf's index times GROUP -- all LEAVES of them, all
//     distinct and correctly spaced.
//  3. ARRAY UTILISATION. Summed busy cycles over all units, divided by
//     UNITS x elapsed cycles. The control plane is modelled as what it is
//     measured to be: one descriptor every `interval` datapath cycles (567 =
//     116.4 sequencer cycles at 265 MHz seen from 1,290 MHz), holding
//     desc_valid until the queue takes it, because that is what a stalled
//     sequencer does.
//  4. RETIRED PASSES. Utilisation counts a unit as busy while it is STALLED on
//     an unbacked refill, which it is -- it is holding its accumulators and
//     burning a cycle. Under SKEW that makes utilisation an occupancy figure and
//     not a work figure, so passes_launched is reported alongside it and the
//     campaign derives the pass rate from it.
//
// TWO SWITCHES, SO THE COMPARISON IS AGAINST THE INCUMBENT AND NOT AGAINST AIR
// ----------------------------------------------------------------------------
//  FLAT=1   replaces the tree with ot_cluster_dispatcher at UNITS: same units,
//           same control model, same metric, flat fan-out. With identical units
//           the two structures retire nearly identical cycle counts, which is
//           worth measuring precisely because it localises the tree's advantage:
//           it is PHYSICAL, not cycle-level, and the physical difference is in
//           the place-and-route records.
//  SKEW     0 every unit always fed; 1 every unit slowed a little and by a
//           different amount; 2 STRAGGLERS -- one unit in sixteen at a 50 %
//           refill duty; 3 one unit in sixteen at a 25 % duty; 4 EVERY unit at a
//           50 % duty. Results must stay bit-identical in every regime, because a
//           stalled refill holds the accumulators rather than dropping a column.
//           3 and 4 exist because the operand-delivery fix has a NEW bound -- one
//           tile fetch per descriptor rather than one column fetch per column
//           consumed -- and a regime that does not cross that bound would only
//           show the fix winning. 3 crosses it; 4 does not, at these passes.
//
// TWO PARAMETERS REACH THE COMPUTE UNITS, so the operand-delivery change is
// measured on the same bench, the same vectors and the same control model as the
// baseline it replaces:
//   REFILL_DECOUPLED  0 lockstep handshake (the baseline: 99.13 % at skew 0,
//                     54.13 % at skew 2), 1 the fill frontier.
//   WGT_BANKS         1 single buffer, 2 double buffer.
//
// THE REFILL PORT CARRIES DATA under REFILL_DECOUPLED=1: each unit asks for a
// column index and the bench supplies that column of the SAME tile the expected
// results were generated from. The host image port writes bank 0 only, so under
// WGT_BANKS=2 the walk reads a bank the host never touched and every one of the
// UNITS x LANES checked accumulators depends on the fill frontier having
// delivered the right column to the right bank. A residency or bank-select fault
// is a wrong result here, not an unverifiable cycle count.
//
// FLAT=1 CANNOT SUPPLY THE FLAG. ot_cluster_dispatcher has no per-pass output, so
// its units are given wgt_wgt_reload=1 -- a fetch charged on every pass. The flat
// structure is therefore only comparable to the tree at REFILL_DECOUPLED=0, and
// the campaign does not run it decoupled.
// ---------------------------------------------------------------------------
module tb_dispatch_tree_throughput #(
    parameter integer LEAVES  = 16,   // token buffers, one per group
    parameter integer GROUP    = 1,   // compute units per leaf
    parameter integer RADIX   = 16,
    parameter integer CREDITS = 2,
    parameter integer LANES   = 16,
    parameter integer ACC_W   = 40,
    parameter integer K_W     = 9,
    parameter integer SC_W    = 8,
    parameter integer PASS_W  = 6,
    parameter integer FLAT    = 0,
    parameter integer SKEW    = 0,
    parameter integer REFILL_DECOUPLED = 0,
    parameter integer WGT_BANKS        = 1
);
    localparam integer UNITS  = LEAVES * GROUP;
    localparam integer TILE_W = $clog2(UNITS);

    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;

    reg                desc_valid;
    wire               desc_ready;
    reg  [K_W-1:0]     desc_k;
    reg  [SC_W-1:0]    desc_scale;
    reg  [PASS_W-1:0]  desc_passes;
    reg  [TILE_W-1:0]  desc_base;

    wire [LEAVES-1:0]        lf_start;
    wire [LEAVES-1:0]        lf_reload;
    wire [LEAVES*K_W-1:0]    lf_k;
    wire [LEAVES*SC_W-1:0]   lf_scale;
    wire [LEAVES*TILE_W-1:0] lf_tile;
    wire [UNITS-1:0]         cu_done, cu_obs, cu_busy;

    wire [31:0] descs, passes, cl_cycles, starved;
    wire [31:0] completions, root_stall;
    wire        signature;

    generate
    if (FLAT == 0) begin : g_tree
        ot_dispatch_tree #(.LEAVES(LEAVES), .GROUP(GROUP), .TILE_W(TILE_W),
                           .RADIX(RADIX), .CREDITS(CREDITS), .QUEUE_LOG2(3),
                           .PASS_W(PASS_W), .K_W(K_W), .SC_W(SC_W)) tree (
            .clk(clk), .rst_n(rst_n),
            .desc_valid(desc_valid), .desc_ready(desc_ready),
            .desc_k(desc_k), .desc_scale(desc_scale), .desc_passes(desc_passes),
            .desc_tile_base(desc_base),
            .cu_start(lf_start), .cu_wgt_reload(lf_reload),
            .cu_cfg_k(lf_k), .cu_cfg_scale(lf_scale),
            .cu_tile_base(lf_tile), .cu_done(cu_done), .cu_obs(cu_obs),
            .descriptors_retired(descs), .passes_launched(passes),
            .unit_completions(completions), .root_stall_cycles(root_stall),
            .cluster_cycles(cl_cycles), .starved_cycles(starved),
            .payload_signature(signature));
    end else begin : g_flat
        //: the incumbent, at the same width and on the same units. It has no
        //: sub-range to give a unit, so every leaf's tile is tied to the grid
        //: origin and the sub-range check is reported as not applicable.
        wire             f_start;
        wire [K_W-1:0]   f_k;
        wire [SC_W-1:0]  f_scale;
        wire [63:0]      f_busy_cycles;
        ot_cluster_dispatcher #(.UNITS(UNITS), .QUEUE_LOG2(3),
                                .PASS_W(PASS_W)) flat (
            .clk(clk), .rst_n(rst_n),
            .desc_valid(desc_valid), .desc_ready(desc_ready),
            .desc_k(desc_k), .desc_scale(desc_scale), .desc_passes(desc_passes),
            .cu_start(f_start), .cu_cfg_k(f_k), .cu_cfg_scale(f_scale),
            .cu_busy(cu_busy), .cu_done(cu_done),
            .descriptors_retired(descs), .passes_launched(passes),
            .unit_busy_cycles(f_busy_cycles), .cluster_cycles(cl_cycles),
            .starved_cycles(starved));
        assign lf_start    = {LEAVES{f_start}};
        //: no per-pass output exists on the flat dispatcher; every pass is charged
        //: a fresh tile.  See the header.
        assign lf_reload   = {LEAVES{1'b1}};
        assign completions = 32'b0;
        assign root_stall  = 32'b0;
        assign signature   = 1'b0;
        genvar fg;
        for (fg = 0; fg < LEAVES; fg = fg + 1) begin : fan
            assign lf_k[fg*K_W +: K_W]         = f_k;
            assign lf_scale[fg*SC_W +: SC_W]   = f_scale;
            assign lf_tile[fg*TILE_W +: TILE_W] = desc_base;
        end
    end
    endgenerate

    //: the operand vectors, declared ahead of the unit array because the refill
    //: payload is sourced from them.
    localparam integer KF = 32;
    reg [15:0] act_mem [0:1023];
    reg [15:0] wgt_mem [0:16383];
    reg [39:0] exp_mem [0:LANES-1];

    // ---- operand load ports, broadcast so every unit holds the same tile ----
    reg                wr_en = 0, act_we = 0;
    reg [7:0]          wr_addr = 0;
    reg [16*LANES-1:0] wr_data = 0;
    reg [8:0]          act_waddr = 0;
    reg [15:0]         act_wdata = 0;
    reg [4:0]          res_sel = 0;

    //: per-unit refill duty, deterministic so the comparison between structures
    //: is repeatable.  See the header for the three regimes.
    wire [UNITS-1:0]  refill_v;
    wire [UNITS-1:0]  cu_grant;      // columns accepted, per unit, per cycle
    reg  [15:0]       skew_cnt  [0:UNITS-1];
    wire [ACC_W-1:0]  res_data  [0:UNITS-1];
    reg  [TILE_W-1:0] seen_tile [0:LEAVES-1];
    reg  [LEAVES-1:0] seen;

    //: REAL compute units. Modelling them as counters would assume away exactly
    //: what is being measured -- that a token that walked DEPTH registered levels
    //: still starts every unit and that every unit still computes correctly.
    genvar g, j;
    generate
        for (g = 0; g < LEAVES; g = g + 1) begin : leaf
            //: sub-range capture: what origin did THIS leaf actually hand its
            //: group?
            always @(posedge clk)
                if (lf_start[g]) begin
                    seen_tile[g] <= lf_tile[g*TILE_W +: TILE_W];
                    seen[g]      <= 1'b1;
                end

            for (j = 0; j < GROUP; j = j + 1) begin : unit
                localparam integer U = g * GROUP + j;
                wire [ACC_W-1:0] res;
                wire [LANES-1:0] drop;
                wire rr, st;
                wire [8:0] rcol;
                //: the operand-delivery payload.  Column rcol of the same tile the
                //: expected results came from, wrapped at KF so every delivered
                //: column is real data rather than an unwritten vector slot.
                reg [16*LANES-1:0] rdata;
                integer rl;
                always @* begin
                    rdata = {(16*LANES){1'b0}};
                    for (rl = 0; rl < LANES; rl = rl + 1)
                        rdata[16*rl +: 16] = wgt_mem[(rcol % KF)*LANES + rl];
                end
                ot_compute_unit #(.LANES(LANES), .ACC_W(ACC_W), .K_MAX(256),
                                  .REFILL_DECOUPLED(REFILL_DECOUPLED),
                                  .WGT_BANKS(WGT_BANKS)) cu (
                    .clk(clk), .rst_n(rst_n),
                    .start(lf_start[g]), .cfg_k(lf_k[g*K_W +: K_W]),
                    .cfg_scale(lf_scale[g*SC_W +: SC_W]),
                    .wgt_reload(lf_reload[g]),
                    .busy(cu_busy[U]), .done(cu_done[U]),
                    .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),
                    .act_we(act_we), .act_waddr(act_waddr), .act_wdata(act_wdata),
                    .refill_valid(refill_v[U]), .refill_data(rdata),
                    .refill_col(rcol), .refill_ready(rr), .stalled(st),
                    .res_sel(res_sel), .res_data(res), .dropped_mask(drop));
                assign res_data[U] = res;
                assign cu_grant[U] = rr && refill_v[U];

                //: the one-bit descriptor signature a unit returns to its leaf,
                //: which the tree XOR-reduces. The probe's unit model computes
                //: the same function, so the routed block and this bench agree.
                reg obs_r;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) obs_r <= 1'b0;
                    else obs_r <= lf_start[g]
                                ? (^{lf_tile[g*TILE_W +: TILE_W],
                                     lf_scale[g*SC_W +: SC_W],
                                     lf_k[g*K_W +: K_W]})
                                : 1'b0;
                assign cu_obs[U] = obs_r;

                localparam integer PERIOD = 8 + (U % 8);
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) skew_cnt[U] <= 16'b0;
                    else skew_cnt[U] <= (skew_cnt[U] >= PERIOD[15:0] - 16'd1)
                                        ? 16'b0 : skew_cnt[U] + 16'd1;
                assign refill_v[U] =
                    (SKEW == 0) ? 1'b1 :
                    (SKEW == 1) ? (skew_cnt[U] != 16'b0) :
                    (SKEW == 4) ? skew_cnt[U][0] :
                    ((U % 16) != 0) ? 1'b1 :
                    (SKEW == 3) ? (skew_cnt[U][1:0] == 2'b00) : skew_cnt[U][0];
            end
        end
    endgenerate

    // ---- utilisation accounting, bench-side so it costs the design nothing ----
    integer ii;
    reg [63:0] busy_acc, grant_acc;
    reg [31:0] busy_now, grant_now;
    always @* begin
        busy_now = 32'b0;
        grant_now = 32'b0;
        for (ii = 0; ii < UNITS; ii = ii + 1) begin
            busy_now  = busy_now  + {31'b0, cu_busy[ii]};
            grant_now = grant_now + {31'b0, cu_grant[ii]};
        end
    end
    reg acct;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin busy_acc <= 64'b0; grant_acc <= 64'b0; end
        else if (acct) begin
            busy_acc  <= busy_acc  + {32'b0, busy_now};
            //: WEIGHT COLUMNS FETCHED.  The term reuse is meant to divide: at
            //: three passes per descriptor a unit that re-fetched a resident tile
            //: would show three times this.
            grant_acc <= grant_acc + {32'b0, grant_now};
        end

    // ---- functional phase ---------------------------------------------------
    integer kk, ll, uu, gg, mism, tmism, guard;
    reg [TILE_W-1:0] want;

    string act_path, wgt_path, exp_path;

    task load_and_verify;
        begin
            if (!$value$plusargs("act=%s", act_path))
                act_path = "testdata/rtl/a3_mac_tile/act.hex";
            if (!$value$plusargs("wgt=%s", wgt_path))
                wgt_path = "testdata/rtl/a3_mac_tile/wgt.hex";
            if (!$value$plusargs("exp=%s", exp_path))
                exp_path = "testdata/rtl/a3_mac_tile/expected.hex";
            $readmemh(act_path, act_mem);
            $readmemh(wgt_path, wgt_mem);
            $readmemh(exp_path, exp_mem);

            rst_n = 0; desc_valid = 0; acct = 0; seen = {LEAVES{1'b0}};
            repeat (4) @(negedge clk);
            rst_n = 1;
            @(negedge clk);

            for (kk = 0; kk < KF; kk = kk + 1) begin
                wr_en = 1'b1; wr_addr = kk[7:0];
                for (ll = 0; ll < LANES; ll = ll + 1)
                    wr_data[16*ll +: 16] = wgt_mem[kk*LANES + ll];
                @(negedge clk);
            end
            wr_en = 1'b0;
            for (kk = 0; kk < KF; kk = kk + 1) begin
                act_we = 1'b1; act_waddr = kk[8:0]; act_wdata = act_mem[kk];
                @(negedge clk);
            end
            act_we = 1'b0;

            //: One descriptor, three passes, grid origin 1. Each pass clears and
            //: re-walks the same K columns, so the final accumulator must equal a
            //: single walk -- which also checks that a multi-pass descriptor does
            //: not double-accumulate anywhere in the tree.
            desc_k = KF[K_W-1:0]; desc_scale = 8'd240; desc_passes = 3;
            desc_base = {{(TILE_W-1){1'b0}}, 1'b1};
            desc_valid = 1'b1;
            @(negedge clk);
            while (!desc_ready) @(negedge clk);
            desc_valid = 1'b0;
            guard = 0;
            while (descs == 32'd0 && guard < 200000) begin
                @(negedge clk); guard = guard + 1;
            end
            repeat (8) @(negedge clk);

            mism = 0;
            for (ll = 0; ll < LANES; ll = ll + 1) begin
                res_sel = ll[4:0];
                @(negedge clk);
                for (uu = 0; uu < UNITS; uu = uu + 1)
                    if (res_data[uu] !== exp_mem[ll]) begin
                        if (mism < 6)
                            $display("FAIL unit %0d lane %0d: %010x expected %010x",
                                     uu, ll, res_data[uu], exp_mem[ll]);
                        mism = mism + 1;
                    end
            end

            tmism = 0;
            if (FLAT == 0)
                for (gg = 0; gg < LEAVES; gg = gg + 1) begin
                    want = desc_base + gg[TILE_W-1:0] * GROUP;
                    if (!seen[gg] || seen_tile[gg] !== want) begin
                        if (tmism < 6)
                            $display("FAIL subrange leaf %0d: seen=%0d tile=%0d expected %0d",
                                     gg, seen[gg], seen_tile[gg], want);
                        tmism = tmism + 1;
                    end
                end

            if (mism == 0 && tmism == 0)
                $display("PASS functional units=%0d leaves=%0d group=%0d radix=%0d flat=%0d skew=%0d: %0d units x %0d lanes = %0d results bit-identical to the reference, 3-pass descriptor, retired=%0d, %0d sub-range origins checked and correct, signature=%0d",
                         UNITS, LEAVES, GROUP, RADIX, FLAT, SKEW, UNITS, LANES,
                         UNITS*LANES, descs, (FLAT == 0) ? LEAVES : 0, signature);
            else
                $display("FAIL functional units=%0d leaves=%0d group=%0d radix=%0d flat=%0d skew=%0d: %0d of %0d results wrong, %0d of %0d sub-ranges wrong",
                         UNITS, LEAVES, GROUP, RADIX, FLAT, SKEW,
                         mism, UNITS*LANES, tmism, LEAVES);
        end
    endtask

    // ---- utilisation phase --------------------------------------------------
    task run_case(input integer k, input integer np, input integer interval,
                  input integer ndesc, input integer maxcyc);
        integer sent, countdown, gd;
        real util, starve_frac, stall_frac;
        begin
            rst_n = 0; desc_valid = 0; acct = 0;
            desc_k = k[K_W-1:0]; desc_scale = 8'd200;
            desc_passes = np[PASS_W-1:0]; desc_base = {TILE_W{1'b0}};
            repeat (4) @(negedge clk);
            rst_n = 1; acct = 1;
            @(negedge clk);

            sent = 0; countdown = 0; gd = 0;
            while (!(descs >= ndesc) && gd < maxcyc) begin
                desc_valid = (countdown == 0) && (sent < ndesc);
                @(negedge clk);
                if (desc_valid && desc_ready) begin
                    sent = sent + 1; countdown = interval - 1;
                end else if (countdown > 0) countdown = countdown - 1;
                gd = gd + 1;
            end
            desc_valid = 0; acct = 0;

            util = (cl_cycles > 0)
                 ? 100.0 * busy_acc / (1.0 * UNITS * cl_cycles) : 0.0;
            starve_frac = (cl_cycles > 0) ? 100.0 * starved / cl_cycles : 0.0;
            stall_frac  = (cl_cycles > 0) ? 100.0 * root_stall / cl_cycles : 0.0;
            $display("UTIL units=%0d leaves=%0d group=%0d radix=%0d flat=%0d skew=%0d K=%0d passes=%0d interval=%0d descs=%0d passes_launched=%0d completions=%0d cycles=%0d util=%0.2f starved=%0.2f rootstall=%0.2f timeout=%0d grants=%0d decoupled=%0d banks=%0d",
                     UNITS, LEAVES, GROUP, RADIX, FLAT, SKEW, k, np, interval,
                     descs, passes, completions, cl_cycles, util, starve_frac,
                     stall_frac, (gd >= maxcyc) ? 1 : 0, grant_acc,
                     REFILL_DECOUPLED, WGT_BANKS);
        end
    endtask

    integer iv, nd, only_func;
    initial begin
        if (!$value$plusargs("interval=%d", iv)) iv = 567;
        if (!$value$plusargs("ndesc=%d", nd))    nd = 12;
        if (!$value$plusargs("func_only=%d", only_func)) only_func = 0;
        $display("operand delivery: REFILL_DECOUPLED=%0d WGT_BANKS=%0d", REFILL_DECOUPLED, WGT_BANKS);
        $display("dispatch %0s: UNITS=%0d LEAVES=%0d GROUP=%0d RADIX=%0d CREDITS=%0d SKEW=%0d, real ot_compute_unit at every unit",
                 (FLAT == 0) ? "tree" : "FLAT (ot_cluster_dispatcher)",
                 UNITS, LEAVES, GROUP, RADIX, CREDITS, SKEW);
        load_and_verify;
        wr_en = 0; act_we = 0; res_sel = 0;
        if (only_func == 0) begin
            run_case(256, 1, iv, nd, 400000);
            run_case(256, 2, iv, nd, 400000);
            run_case(256, 3, iv, nd, 400000);
            run_case(256, 4, iv, nd, 400000);
            run_case(256, 8, iv, nd, 400000);
            run_case( 64, 1, iv, nd, 400000);
            run_case( 64, 8, iv, nd, 400000);
            run_case(256, 1, 1,  nd, 400000);
            run_case(256, 4, 1,  nd, 400000);
        end
        $display("DONE dispatch sweep UNITS=%0d LEAVES=%0d GROUP=%0d RADIX=%0d FLAT=%0d SKEW=%0d",
                 UNITS, LEAVES, GROUP, RADIX, FLAT, SKEW);
        $finish;
    end
endmodule
