`timescale 1ns/1ps
// connectivity bench of hfd_sfu: 6 random die input words (seed 20261006), each held 32 cycles; the die output must
// settle to the generator's reference (tools/hbm_hub_quarter_gen.py Plan.model) and match exactly; exit 1 on mismatch.
module tb;
    reg clk = 0; always #0.4165 clk = ~clk;
    reg rst = 1;
    reg [2047:0] din;
    wire [2047:0] dout;
    reg [2047:0] vin [0:5];
    reg [2047:0] vout [0:5];
    integer v, c, bad, lat, first;
    hfd_sfu dut(.ck(clk), .rst(rst), .f_hc(din[1023:0]), .f_su(din[2047:1024]), .t_hc(dout[1023:0]), .t_su(dout[2047:1024]));
    initial begin
        $readmemh("tb_in.mem", vin); $readmemh("tb_out.mem", vout);
        bad = 0; lat = 0;
        din = 0; repeat (6) @(posedge clk); rst = 0;
        for (v = 0; v < 6; v = v + 1) begin
            din = vin[v]; first = -1;
            for (c = 0; c < 32; c = c + 1) begin
                @(posedge clk); #0.1;
                if (first < 0 && dout === vout[v]) first = c;
            end
            if (dout !== vout[v]) begin bad = bad + 1; $display("MISMATCH vec %0d", v); end
            if (first > lat) lat = first;
        end
        $display("OT_RESULT vectors=6 mismatches=%0d settle_cycles=%0d", bad, lat + 1);
        if (bad != 0) $fatal(1, "FAIL");
        $finish;
    end
endmodule
