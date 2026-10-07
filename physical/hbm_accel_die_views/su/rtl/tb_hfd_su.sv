`timescale 1ns/1ps
// connectivity bench of hfd_su: 6 random die input words (seed 20261006), each held 44 cycles; the die output must
// settle to the generator's reference (tools/hbm_hub_quarter_gen.py Plan.model) and match exactly; exit 1 on mismatch.
module tb;
    reg clk = 0; always #0.4165 clk = ~clk;
    reg rst = 1;
    reg [9498:0] din;
    wire [6399:0] dout;
    reg [9498:0] vin [0:5];
    reg [6399:0] vout [0:5];
    integer v, c, bad, lat, first;
    hfd_su dut(.ck(clk), .rst(rst), .a(din[1057:0]), .f_cmdproc(din[1121:1058]), .f_coll(din[1701:1122]), .f_quant(din[2213:1702]), .f_sfu(din[3237:2214]), .f_su_ew(din[4261:3238]), .f_su_ns(din[5285:4262]), .f_vm(din[7333:5286]), .r(din[9498:7334]), .t_coll(dout[1023:0]), .t_router(dout[1279:1024]), .t_sfu(dout[2303:1280]), .t_su_ew(dout[3327:2304]), .t_su_ns(dout[4351:3328]), .t_vm(dout[6399:4352]));
    initial begin
        $readmemh("tb_in.mem", vin); $readmemh("tb_out.mem", vout);
        bad = 0; lat = 0;
        din = 0; repeat (6) @(posedge clk); rst = 0;
        for (v = 0; v < 6; v = v + 1) begin
            din = vin[v]; first = -1;
            for (c = 0; c < 44; c = c + 1) begin
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
