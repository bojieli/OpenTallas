`timescale 1ns/1ps
// connectivity bench of hfd_su: 8 random die input words (seed 20261006), each held 64 cycles; the die output must
// settle to the generator's reference (tools/hbm_hub_quarter_gen.py Plan.model) and match exactly; exit 1 on mismatch.
module tb;
    reg clk = 0; always #0.4165 clk = ~clk;
    reg rst = 1;
    reg [11538:0] din;
    wire [6486:0] dout;
    reg [11538:0] vin [0:7];
    reg [6486:0] vout [0:7];
    integer v, c, bad, lat, first;
    parameter integer QID = 0;
    reg cg_en = 1;
    hfd_su dut(.ck0(clk), .ck1(clk), .ck2(clk), .ck3(clk), .ck4(clk), .ck5(clk), .ck6(clk), .ck7(clk), .rst(rst), .a(din[1057:0]), .f_cmdproc(din[1121:1058]), .f_coll(din[1701:1122]), .f_hgi_cmdproc(din[3899:1702]), .f_hgi_vmaddr(din[3979:3900]), .f_hgi_vmr(din[4253:3980]), .f_sfu(din[5277:4254]), .f_su_ew(din[6301:5278]), .f_su_ns(din[7325:6302]), .f_vm(din[9373:7326]), .r(din[11538:9374]), .t_coll(dout[1023:0]), .t_hgi_cmdproc(dout[1026:1024]), .t_hgi_vmq(dout[1364:1027]), .t_router(dout[1366:1365]), .t_sfu(dout[2390:1367]), .t_su_ew(dout[3414:2391]), .t_su_ns(dout[4438:3415]), .t_vm(dout[6486:4439]), .qid(QID[1:0]), .cg_en(cg_en));
    initial begin
        $readmemh("tb_in.mem", vin); $readmemh($sformatf("tb_out_q%0d.mem", QID), vout);
        bad = 0; lat = 0;
        din = 0; repeat (6) @(posedge clk); rst = 0;
        for (v = 0; v < 8; v = v + 1) begin
            // cg: a fully gated gap before each vector; wake uses the model-priced input lead
            cg_en = 0; repeat (200) @(posedge clk); #0.1 cg_en = 1; repeat (5) @(posedge clk); #0.1;
            din = vin[v]; first = -1;
            for (c = 0; c < 64; c = c + 1) begin
                @(posedge clk); #0.1;
                if (first < 0 && dout === vout[v]) first = c;
            end
            if (dout !== vout[v]) begin bad = bad + 1; $display("MISMATCH vec %0d", v); end
            if (first > lat) lat = first;
        end
        $display("OT_RESULT vectors=8 qid=%0d mismatches=%0d settle_cycles=%0d", QID, bad, lat + 1);
        if (bad != 0) $fatal(1, "FAIL");
        $finish;
    end
endmodule
