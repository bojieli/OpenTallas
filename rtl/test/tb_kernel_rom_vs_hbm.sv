`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Kernel execution: the SAME compute unit under ROM and HBM weight refill.
//
// This is the comparison this project exists to make, done at equal fidelity.
// Both runs use identical RTL, identical operands and identical expected results.
// The only difference is how often refill_valid is asserted:
//
//   ROM design   on-die mask ROM: a column is always available. refill_valid = 1.
//   HBM design   off-chip: a column arrives every REFILL_PERIOD cycles, so the
//                array stalls in between.
//
// REFILL_PERIOD is a plusarg rather than a constant, because the honest value
// comes from bandwidth divided by bytes-per-column and belongs in the analysis,
// not hidden in a testbench. What this bench establishes is that the hardware
// behaves correctly under stall and how many cycles each regime costs -- both
// measured, on the same gates.
//
// Correctness under stall is the load-bearing part: a unit that produced the
// right answer only when never starved would be useless, and the accumulators
// must hold across a stall rather than drift.
//
// THREE KNOBS WERE ADDED FOR THE OPERAND-DELIVERY WORK, and the default of every
// one of them reproduces the published table (46/0, 78/31, 142/95, 266/219) bit
// for bit, because that table is the baseline this bench must keep measuring.
//
//   -GREFILL_DECOUPLED / -GWGT_BANKS  passed straight to the DUT.  0 / 1 is the
//        lockstep handshake the table was measured on; 1 / 2 is the fill frontier
//        plus the double buffer.  Same file, same operands, same expected results,
//        so the two columns are comparable by construction.
//   +passes=P   run P passes of ONE descriptor, asserting wgt_reload on the first
//        only.  Each pass clears and re-walks the same K resident columns, so the
//        accumulator after P passes must equal the accumulator after one -- which
//        is what makes reuse measurable here rather than asserted: a unit that
//        re-fetched a resident tile would show P times the refill grants.
//   +nopreload=1  do not use the host image port at all, so every weight column
//        the unit computes with must have ARRIVED over the refill port.  Under
//        WGT_BANKS=2 the walk reads a bank the host never wrote, so this is the
//        run in which a residency or bank-select fault becomes a wrong
//        accumulator instead of a cycle count.
//
// REFILL GRANTS are counted alongside stall cycles.  Cycles say what it cost;
// grants say how many columns were actually fetched, which is the term reuse is
// supposed to divide.
// ---------------------------------------------------------------------------
module tb_kernel_rom_vs_hbm #(
    parameter integer REFILL_DECOUPLED = 0,
    parameter integer WGT_BANKS        = 1
);
    localparam integer LANES = 16;
    localparam integer ACC_W = 40;
    localparam integer K     = 32;

    reg clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;

    reg [15:0]      act_mem [0:K-1];
    reg [15:0]      wgt_mem [0:K*LANES-1];
    reg [ACC_W-1:0] expected_mem [0:LANES-1];
    reg [4095:0]    act_path, wgt_path, exp_path;
    reg [31:0]      refill_period;
    reg [31:0]      npass, nopreload;

    reg                 start = 1'b0;
    reg [8:0]           cfg_k = K;
    reg [7:0]           cfg_scale = 8'd240;
    reg                 wgt_reload = 1'b1;
    reg                 wr_en = 1'b0;
    reg [7:0]           wr_addr = 8'b0;
    reg [16*LANES-1:0]  wr_data = {(16*LANES){1'b0}};
    reg                 act_we = 1'b0;
    reg [8:0]           act_waddr = 9'b0;
    reg [15:0]          act_wdata = 16'b0;
    reg [4:0]           res_sel = 5'b0;
    reg                 refill_valid = 1'b1;

    wire busy, done, refill_ready, stalled;
    wire [8:0]       refill_col;
    wire [ACC_W-1:0] res_data;
    wire [LANES-1:0] dropped_mask;

    integer k, l, mism, cycles, stalls, tick, grants, p, prewin;

    //: the refill payload: the column the unit is asking for, taken from the same
    //: vector file the expected results were generated from.  A DMA would read it
    //: out of the weight store it serves; here the bench is that store.
    reg [16*LANES-1:0] refill_data;
    integer rl;
    always @* begin
        refill_data = {(16*LANES){1'b0}};
        for (rl = 0; rl < LANES; rl = rl + 1)
            if (refill_col < K[8:0])
                refill_data[16*rl +: 16] = wgt_mem[refill_col*LANES + rl];
    end

    ot_compute_unit #(.LANES(LANES), .ACC_W(ACC_W),
                      .REFILL_DECOUPLED(REFILL_DECOUPLED),
                      .WGT_BANKS(WGT_BANKS)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_k(cfg_k),
        .cfg_scale(cfg_scale), .wgt_reload(wgt_reload), .acc_continue(1'b0),
        .acc_scale_violation(),
        .busy(busy), .done(done),
        .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),
        .act_we(act_we), .act_waddr(act_waddr), .act_wdata(act_wdata),
        .refill_valid(refill_valid), .refill_data(refill_data),
        .refill_col(refill_col), .refill_ready(refill_ready),
        .stalled(stalled), .res_sel(res_sel), .res_data(res_data),
        .dropped_mask(dropped_mask)
    );

    // refill_valid every refill_period cycles; 1 means never starved (ROM)
    always @(posedge clk)
        if (refill_period <= 1) refill_valid <= 1'b1;
        else refill_valid <= ((tick % refill_period) == 0);

    always @(posedge clk) tick <= tick + 1;

    //: every accepted column, counted on the same edge the DUT writes it.
    always @(posedge clk)
        if (rst_n && refill_valid && refill_ready) grants = grants + 1;

    initial begin
        tick = 0; grants = 0;
        if (!$value$plusargs("act=%s", act_path)) begin $display("FAIL: +act="); $finish; end
        if (!$value$plusargs("wgt=%s", wgt_path)) begin $display("FAIL: +wgt="); $finish; end
        if (!$value$plusargs("exp=%s", exp_path)) begin $display("FAIL: +exp="); $finish; end
        if (!$value$plusargs("period=%d", refill_period)) begin $display("FAIL: +period="); $finish; end
        if (!$value$plusargs("passes=%d", npass)) npass = 1;
        if (!$value$plusargs("nopreload=%d", nopreload)) nopreload = 0;
        $readmemh(act_path, act_mem);
        $readmemh(wgt_path, wgt_mem);
        $readmemh(exp_path, expected_mem);

        repeat (4) @(posedge clk); rst_n = 1'b1; @(posedge clk);

        //: the host image port.  Skipped entirely under +nopreload=1, which is
        //: what makes the refill port the only weight source in that run.
        prewin = 0;
        if (nopreload == 0)
            for (k = 0; k < K; k = k + 1) begin
                wr_en = 1'b1; wr_addr = k[7:0];
                for (l = 0; l < LANES; l = l + 1)
                    wr_data[16*l +: 16] = wgt_mem[k*LANES + l];
                @(posedge clk);
                prewin = prewin + 1;
            end
        wr_en = 1'b0;
        for (k = 0; k < K; k = k + 1) begin
            act_we = 1'b1; act_waddr = k[8:0]; act_wdata = act_mem[k];
            @(posedge clk);
            prewin = prewin + 1;
        end
        act_we = 1'b0; @(posedge clk);
        prewin = prewin + 1;

        //: PASS 1 reloads the tile; the rest re-walk what is already resident.
        cycles = 0; stalls = 0;
        for (p = 0; p < npass; p = p + 1) begin
            wgt_reload = (p == 0);
            start = 1'b1; @(posedge clk); start = 1'b0;
            while (!done && cycles < 200000) begin
                @(posedge clk);
                cycles = cycles + 1;
                if (stalled) stalls = stalls + 1;
            end
            if (!done) begin $display("FAIL: timeout"); $finish; end
            @(posedge clk);
        end
        wgt_reload = 1'b1;

        mism = 0;
        for (l = 0; l < LANES; l = l + 1) begin
            res_sel = l[4:0]; @(posedge clk);
            if (res_data !== expected_mem[l]) mism = mism + 1;
        end

        if (mism == 0)
            $display("PASS period=%0d: %0d lanes correct, %0d cycles, %0d stall cycles, passes=%0d grants=%0d prewindow=%0d decoupled=%0d banks=%0d nopreload=%0d",
                     refill_period, LANES, cycles, stalls, npass, grants,
                     prewin, REFILL_DECOUPLED, WGT_BANKS, nopreload);
        else
            $display("FAIL period=%0d: %0d lanes wrong after %0d cycles, passes=%0d grants=%0d decoupled=%0d banks=%0d nopreload=%0d",
                     refill_period, mism, cycles, npass, grants,
                     REFILL_DECOUPLED, WGT_BANKS, nopreload);
        $finish;
    end
endmodule
