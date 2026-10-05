`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Campaign for rtl/proto/ot_compute_unit_gemm.sv.
//
// It does both jobs the GEMV unit needed two benches for, because for this unit
// they are the same question: are all LANES*NCOL accumulators bit-identical to
// runtime.reference.mac_tile, and how many cycles does the pass take under a given
// weight-refill rate? Correctness under starvation is the load-bearing half --
// NCOL tiles now share one stalled weight bus, so a stall that corrupted one
// column's accumulator while another advanced would be invisible in a
// never-starved run.
//
// +period=P asserts refill_valid every P cycles, exactly as tb_kernel_rom_vs_hbm
// does for the GEMV unit, so the two cycle counts are directly comparable.
//
// EVERY STIMULUS WRITE IS DRIVEN ON THE NEGATIVE EDGE. Driving a synchronous
// write port from an initial block that assigns at the positive edge is a race
// with the always block that samples it, and it is not theoretical: under Icarus
// the same pattern in tb_compute_unit lands only the even-addressed activation
// words, leaves the odd ones X, and reports every lane wrong.
module tb_compute_unit_gemm;
    localparam integer LANES = 16;
    localparam integer ACC_W = 40;
    localparam integer NCOL  = `OT_NCOL;
`ifdef OT_K
    localparam integer K     = `OT_K;
`else
    localparam integer K     = 32;
`endif
    localparam integer KW    = $clog2(256 + 1);
    localparam integer AW    = $clog2(256);

    reg clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;

    reg [16*NCOL-1:0] act_mem [0:K-1];
    reg [15:0]        wgt_mem [0:K*LANES-1];
    reg [ACC_W-1:0]   expected_mem [0:LANES*NCOL-1];
    reg [3:0]         dropped_mem  [0:LANES*NCOL-1];
    reg [4095:0]      act_path, wgt_path, exp_path, drop_path;
    reg [31:0]        refill_period;

    reg                    start = 1'b0;
    reg [KW-1:0]           cfg_k = KW'(K);
    reg [7:0]              cfg_scale = 8'd240;
    reg                    wr_en = 1'b0;
    reg [AW-1:0]           wr_addr = {AW{1'b0}};
    reg [16*LANES-1:0]     wr_data = {(16*LANES){1'b0}};
    reg                    act_we = 1'b0;
    reg [AW-1:0]           act_waddr = {AW{1'b0}};
    reg [16*NCOL-1:0]      act_wdata = {(16*NCOL){1'b0}};
    reg [$clog2(LANES)-1:0] res_sel = {$clog2(LANES){1'b0}};
    reg                    refill_valid = 1'b1;

    wire busy, done, refill_ready, stalled;
    wire [ACC_W*NCOL-1:0]   res_data;
    wire [LANES*NCOL-1:0]   dropped_mask;

    integer k, l, n, mism, dmism, cycles, stalls, tick, guard;

    ot_compute_unit_gemm #(.LANES(LANES), .ACC_W(ACC_W), .K_MAX(256), .NCOL(NCOL)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_k(cfg_k),
        .cfg_scale(cfg_scale), .busy(busy), .done(done),
        .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),
        .act_we(act_we), .act_waddr(act_waddr), .act_wdata(act_wdata),
        .refill_valid(refill_valid), .refill_ready(refill_ready),
        .stalled(stalled), .res_sel(res_sel), .res_data(res_data),
        .dropped_mask(dropped_mask)
    );

    always @(posedge clk) begin
        tick <= tick + 1;
        if (refill_period <= 1) refill_valid <= 1'b1;
        else refill_valid <= ((tick % refill_period) == 0);
    end

    initial begin
        tick = 0;
        if (!$value$plusargs("act=%s", act_path))   begin $display("FAIL: +act="); $finish; end
        if (!$value$plusargs("wgt=%s", wgt_path))   begin $display("FAIL: +wgt="); $finish; end
        if (!$value$plusargs("exp=%s", exp_path))   begin $display("FAIL: +exp="); $finish; end
        if (!$value$plusargs("drop=%s", drop_path)) begin $display("FAIL: +drop="); $finish; end
        if (!$value$plusargs("period=%d", refill_period)) begin $display("FAIL: +period="); $finish; end
        $readmemh(act_path, act_mem);
        $readmemh(wgt_path, wgt_mem);
        $readmemh(exp_path, expected_mem);
        $readmemh(drop_path, dropped_mem);

        repeat (4) @(posedge clk); rst_n = 1'b1;

        // weight store fill: one column of LANES weights per word
        for (k = 0; k < K; k = k + 1) begin
            @(negedge clk);
            wr_en = 1'b1; wr_addr = k[AW-1:0];
            for (l = 0; l < LANES; l = l + 1)
                wr_data[16*l +: 16] = wgt_mem[k*LANES + l];
        end
        @(negedge clk); wr_en = 1'b0;

        // activation store fill: NCOL columns at one K index per word
        for (k = 0; k < K; k = k + 1) begin
            @(negedge clk);
            act_we = 1'b1; act_waddr = k[AW-1:0]; act_wdata = act_mem[k];
        end
        @(negedge clk); act_we = 1'b0;

        @(negedge clk); start = 1'b1;
        @(negedge clk); start = 1'b0;

        cycles = 0; stalls = 0; guard = 200000;
        while (!done && cycles < guard) begin
            @(posedge clk);
            cycles = cycles + 1;
            if (stalled) stalls = stalls + 1;
        end
        if (!done) begin $display("FAIL: timeout after %0d cycles", cycles); $finish; end

        mism = 0; dmism = 0;
        for (l = 0; l < LANES; l = l + 1) begin
            res_sel = l[$clog2(LANES)-1:0];
            //: TWO edges, because ot_compute_unit_gemm registers its drain: the
            //: read-out mux was the worst post-route path in the design and the
            //: cycle of read latency is free, since the drain runs once per pass
            //: rather than once per column. Sampling one edge early reads the
            //: PREVIOUS lane and every column looks wrong.
            @(negedge clk);
            @(negedge clk);
            for (n = 0; n < NCOL; n = n + 1) begin
                if (res_data[ACC_W*n +: ACC_W] !== expected_mem[n*LANES + l]) begin
                    if (mism < 8)
                        $display("COL %0d LANE %0d: observed %010x expected %010x",
                                 n, l, res_data[ACC_W*n +: ACC_W],
                                 expected_mem[n*LANES + l]);
                    mism = mism + 1;
                end
                if (dropped_mask[LANES*n + l] !== dropped_mem[n*LANES + l][0])
                    dmism = dmism + 1;
            end
        end

        if (mism == 0 && dmism == 0)
            $display("PASS period=%0d: %0d accumulators (%0d lanes x %0d columns) bit-identical to the reference, %0d cycles, %0d stall cycles, %0d MAC",
                     refill_period, LANES*NCOL, LANES, NCOL, cycles, stalls,
                     LANES*NCOL*K);
        else
            $display("FAIL period=%0d: %0d value mismatches, %0d dropped mismatches",
                     refill_period, mism, dmism);
        $finish;
    end
endmodule
