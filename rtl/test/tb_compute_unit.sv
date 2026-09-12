`timescale 1ns/1ps
// Campaign for rtl/proto/ot_compute_unit.sv: the tile PLUS its operand delivery.
//
// This is the first campaign that exercises the memory access path -- weights
// read from SRAM one column per cycle, activations read from the register file and
// broadcast. The tile was already qualified in isolation, so what this adds is
// that the sequencer presents the right operand pair at the right cycle. An
// off-by-one in the SRAM read latency would show up as every lane wrong, which is
// exactly how the earlier hierarchical-tile bug announced itself.
module tb_compute_unit;
    localparam integer LANES = 16;
    localparam integer ACC_W = 40;
    localparam integer K     = 32;

    reg clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;

    reg [15:0]      act_mem [0:K-1];
    reg [15:0]      wgt_mem [0:K*LANES-1];
    reg [ACC_W-1:0] expected_mem [0:LANES-1];
    reg [3:0]       dropped_mem  [0:LANES-1];
    reg [4095:0]    act_path, wgt_path, exp_path, drop_path;

    reg                 start = 1'b0;
    reg [8:0]           cfg_k = K;
    reg [7:0]           cfg_scale = 8'd240;
    reg                 wr_en = 1'b0;
    reg [7:0]           wr_addr = 8'b0;
    reg [16*LANES-1:0]  wr_data = {(16*LANES){1'b0}};
    reg                 act_we = 1'b0;
    reg [8:0]           act_waddr = 9'b0;
    reg [15:0]          act_wdata = 16'b0;
    reg [4:0]           res_sel = 5'b0;

    wire                busy, done;
    wire [ACC_W-1:0]    res_data;
    wire [LANES-1:0]    dropped_mask;

    integer k, l, mism, dmism, guard;

    ot_compute_unit #(.LANES(LANES), .ACC_W(ACC_W)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_k(cfg_k),
        .cfg_scale(cfg_scale), .busy(busy), .done(done),
        .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),
        .act_we(act_we), .act_waddr(act_waddr), .act_wdata(act_wdata),
        .res_sel(res_sel), .res_data(res_data), .dropped_mask(dropped_mask)
    );

    initial begin
        if (!$value$plusargs("act=%s", act_path))   begin $display("FAIL: +act="); $finish; end
        if (!$value$plusargs("wgt=%s", wgt_path))   begin $display("FAIL: +wgt="); $finish; end
        if (!$value$plusargs("exp=%s", exp_path))   begin $display("FAIL: +exp="); $finish; end
        if (!$value$plusargs("drop=%s", drop_path)) begin $display("FAIL: +drop="); $finish; end
        $readmemh(act_path, act_mem);
        $readmemh(wgt_path, wgt_mem);
        $readmemh(exp_path, expected_mem);
        $readmemh(drop_path, dropped_mem);

        repeat (4) @(posedge clk); rst_n = 1'b1; @(posedge clk);

        // fill the weight SRAM: one word per column, lanes packed across width
        for (k = 0; k < K; k = k + 1) begin
            wr_en = 1'b1; wr_addr = k[7:0];
            for (l = 0; l < LANES; l = l + 1)
                wr_data[16*l +: 16] = wgt_mem[k*LANES + l];
            @(posedge clk);
        end
        wr_en = 1'b0;

        // fill the activation register file
        for (k = 0; k < K; k = k + 1) begin
            act_we = 1'b1; act_waddr = k[8:0]; act_wdata = act_mem[k];
            @(posedge clk);
        end
        act_we = 1'b0;
        @(posedge clk);

        start = 1'b1; @(posedge clk); start = 1'b0;

        guard = 0;
        while (!done && guard < 100000) begin @(posedge clk); guard = guard + 1; end
        if (!done) begin $display("FAIL: timeout after %0d cycles", guard); $finish; end

        mism = 0; dmism = 0;
        for (l = 0; l < LANES; l = l + 1) begin
            res_sel = l[4:0];
            @(posedge clk);
            if (res_data !== expected_mem[l]) begin
                if (mism < 6)
                    $display("LANE %0d: observed %010x expected %010x", l, res_data, expected_mem[l]);
                mism = mism + 1;
            end
            if (dropped_mask[l] !== dropped_mem[l][0]) dmism = dmism + 1;
        end

        if (mism == 0 && dmism == 0)
            $display("PASS: %0d lanes through SRAM operand delivery bit-identical to the reference, %0d cycles",
                     LANES, guard);
        else
            $display("FAIL: %0d value mismatches, %0d dropped mismatches", mism, dmism);
        $finish;
    end
endmodule
