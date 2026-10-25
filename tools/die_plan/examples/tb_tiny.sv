`timescale 1ns/1ps
// Bench for the generated tiny die (gen.py rtl): (1) ft slot = ST cycles (ST stations: R3 <= 405 um, ruling 9.4), data
// passes during reset, epoch held 0 while
// the partition is in reset; (2) die top: the lane epoch reaches pb exactly LAT_X - 1 cycles after pa's out flop
// releases, so dout leaves 0 at a fixed cycle; (3) a din change reaches dout after the lane-table delay.
module tb_tiny;
    localparam int ST = 3;      // stations of the mid fx slot (examples/tiny_plan.json)
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg  [64:0] fx_i = 0;
    wire [64:0] fx_o;
    wire [8:0] cfg_o;
    wire [16:0] fr_o;
    tiny_mid_part u_mid (.clk(clk), .arst_n(rst_n), .cfg_i(9'h1ff), .cfg_o(cfg_o), .fx_i(fx_i), .fx_o(fx_o),
                         .fr_i(17'h1ffff), .fr_o(fr_o));
    reg  [31:0] din = 0;
    wire [31:0] dout;
    tiny_top u_top (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout));
    integer cyc = 0, first_nz = -1, errors = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (first_nz < 0 && dout != 0) first_nz = cyc;
    end
    initial begin
        fx_i = {1'b1, 64'hdead_beef_0000_0001};
        repeat (ST) @(posedge clk);
        #0.1;
        if (fx_o[63:0] !== 64'hdead_beef_0000_0001) begin $display("FAIL data not passed in reset"); errors = errors + 1; end
        if (fx_o[64] !== 1'b0) begin $display("FAIL epoch not held in reset"); errors = errors + 1; end
        din = 32'h0000_0003;
        rst_n = 1;
        repeat (6 + ST) @(posedge clk);
        #0.1;
        if (fx_o[64] !== 1'b1) begin $display("FAIL epoch not released"); errors = errors + 1; end
        fx_i = {1'b1, 64'h1234};
        repeat (ST - 1) @(posedge clk); #0.1;
        if (fx_o[63:0] === 64'h1234) begin $display("FAIL slot latency < ST"); errors = errors + 1; end
        @(posedge clk); #0.1;
        if (fx_o[63:0] !== 64'h1234) begin $display("FAIL slot latency != ST"); errors = errors + 1; end
        repeat (40) @(posedge clk);
        $display("first nonzero dout at cycle %0d (reset released at cycle %0d)", first_nz, ST);
        if (first_nz < 0) begin $display("FAIL dout never left 0"); errors = errors + 1; end
        if (errors == 0) $display("TB_TINY PASS"); else $display("TB_TINY FAIL %0d", errors);
        $finish;
    end
endmodule
