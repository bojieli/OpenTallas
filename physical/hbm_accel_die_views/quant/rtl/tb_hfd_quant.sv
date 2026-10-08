`timescale 1ns/1ps
// lockstep bench of hfd_quant (tools/hbm_die_wrap.py --tb): one seed 20261006
module tb_hfd_quant;
    reg [0:0] ck;
    reg [1023:0] f_vm;
    reg [0:0] rst;
    wire [511:0] t_su_NE;
    wire [511:0] t_su_NW;
    wire [511:0] t_su_SE;
    wire [511:0] t_su_SW;
    hfd_quant dut(.ck(ck), .f_vm(f_vm), .rst(rst), .t_su_NE(t_su_NE), .t_su_NW(t_su_NW), .t_su_SE(t_su_SE), .t_su_SW(t_su_SW));
    reg clk = 0; always #0.4165 clk = ~clk;
    always @* ck[0] = clk;
    reg [0:0] d0_ck; always @(posedge clk) d0_ck <= ck;
    reg [0:0] d1_ck; always @(posedge clk) d1_ck <= d0_ck;
    reg [0:0] d2_ck; always @(posedge clk) d2_ck <= d1_ck;
    reg [0:0] d3_ck; always @(posedge clk) d3_ck <= d2_ck;
    reg [0:0] d_ck; always @(posedge clk) d_ck <= d3_ck;
    reg [1023:0] d0_f_vm; always @(posedge clk) d0_f_vm <= f_vm;
    reg [1023:0] d_f_vm; always @(posedge clk) d_f_vm <= d0_f_vm;
    reg [0:0] d0_rst; always @(posedge clk) d0_rst <= rst;
    reg [0:0] d1_rst; always @(posedge clk) d1_rst <= d0_rst;
    reg [0:0] d2_rst; always @(posedge clk) d2_rst <= d1_rst;
    reg [0:0] d3_rst; always @(posedge clk) d3_rst <= d2_rst;
    reg [0:0] d_rst; always @(posedge clk) d_rst <= d3_rst;
    wire [0:0] r_aq_clk;
    assign r_aq_clk = dut.w_aq_clk;
    wire [0:0] r_aq_rst_n;
    assign r_aq_rst_n = dut.w_aq_rst_n;
    wire [0:0] r_aq_v;
    assign r_aq_v = dut.w_aq_v;
    wire [0:0] r_aq_fp4;
    assign r_aq_fp4 = dut.w_aq_fp4;
    wire [1023:0] r_aq_x;
    assign r_aq_x = {d_f_vm[1023:0]};
    wire [0:0] r_aq_vo;
    reg [0:0] q1_aq_vo; always @(posedge clk) q1_aq_vo <= r_aq_vo;
    reg [0:0] q2_aq_vo; always @(posedge clk) q2_aq_vo <= q1_aq_vo;
    reg [0:0] q3_aq_vo; always @(posedge clk) q3_aq_vo <= q2_aq_vo;
    reg [0:0] q4_aq_vo; always @(posedge clk) q4_aq_vo <= q3_aq_vo;
    reg [0:0] q5_aq_vo; always @(posedge clk) q5_aq_vo <= q4_aq_vo;
    wire [255:0] r_aq_q;
    reg [255:0] q1_aq_q; always @(posedge clk) q1_aq_q <= r_aq_q;
    reg [255:0] q2_aq_q; always @(posedge clk) q2_aq_q <= q1_aq_q;
    reg [255:0] q3_aq_q; always @(posedge clk) q3_aq_q <= q2_aq_q;
    reg [255:0] q4_aq_q; always @(posedge clk) q4_aq_q <= q3_aq_q;
    reg [255:0] q5_aq_q; always @(posedge clk) q5_aq_q <= q4_aq_q;
    wire [9:0] r_aq_e;
    reg [9:0] q1_aq_e; always @(posedge clk) q1_aq_e <= r_aq_e;
    reg [9:0] q2_aq_e; always @(posedge clk) q2_aq_e <= q1_aq_e;
    reg [9:0] q3_aq_e; always @(posedge clk) q3_aq_e <= q2_aq_e;
    reg [9:0] q4_aq_e; always @(posedge clk) q4_aq_e <= q3_aq_e;
    reg [9:0] q5_aq_e; always @(posedge clk) q5_aq_e <= q4_aq_e;
    wire [511:0] r_aq_y;
    reg [511:0] q1_aq_y; always @(posedge clk) q1_aq_y <= r_aq_y;
    reg [511:0] q2_aq_y; always @(posedge clk) q2_aq_y <= q1_aq_y;
    reg [511:0] q3_aq_y; always @(posedge clk) q3_aq_y <= q2_aq_y;
    reg [511:0] q4_aq_y; always @(posedge clk) q4_aq_y <= q3_aq_y;
    reg [511:0] q5_aq_y; always @(posedge clk) q5_aq_y <= q4_aq_y;
    wire [0:0] r_aq_fault;
    reg [0:0] q1_aq_fault; always @(posedge clk) q1_aq_fault <= r_aq_fault;
    reg [0:0] q2_aq_fault; always @(posedge clk) q2_aq_fault <= q1_aq_fault;
    reg [0:0] q3_aq_fault; always @(posedge clk) q3_aq_fault <= q2_aq_fault;
    reg [0:0] q4_aq_fault; always @(posedge clk) q4_aq_fault <= q3_aq_fault;
    reg [0:0] q5_aq_fault; always @(posedge clk) q5_aq_fault <= q4_aq_fault;
    ot_hfd_actquant_m #(.MR(1), .MLAT(6), .TS0(1), .TSPL(1)) ref_aq (.clk(r_aq_clk), .rst_n(r_aq_rst_n), .v(r_aq_v), .fp4(r_aq_fp4), .x(r_aq_x), .vo(r_aq_vo), .q(r_aq_q), .e(r_aq_e), .y(r_aq_y), .fault(r_aq_fault));
    integer err = 0, nchk = 0, cyc;
    integer seed = 20261006;
    task automatic randomize_inputs; begin
        f_vm[31:0] = $urandom(seed); seed = seed + 1;
        f_vm[63:32] = $urandom(seed); seed = seed + 1;
        f_vm[95:64] = $urandom(seed); seed = seed + 1;
        f_vm[127:96] = $urandom(seed); seed = seed + 1;
        f_vm[159:128] = $urandom(seed); seed = seed + 1;
        f_vm[191:160] = $urandom(seed); seed = seed + 1;
        f_vm[223:192] = $urandom(seed); seed = seed + 1;
        f_vm[255:224] = $urandom(seed); seed = seed + 1;
        f_vm[287:256] = $urandom(seed); seed = seed + 1;
        f_vm[319:288] = $urandom(seed); seed = seed + 1;
        f_vm[351:320] = $urandom(seed); seed = seed + 1;
        f_vm[383:352] = $urandom(seed); seed = seed + 1;
        f_vm[415:384] = $urandom(seed); seed = seed + 1;
        f_vm[447:416] = $urandom(seed); seed = seed + 1;
        f_vm[479:448] = $urandom(seed); seed = seed + 1;
        f_vm[511:480] = $urandom(seed); seed = seed + 1;
        f_vm[543:512] = $urandom(seed); seed = seed + 1;
        f_vm[575:544] = $urandom(seed); seed = seed + 1;
        f_vm[607:576] = $urandom(seed); seed = seed + 1;
        f_vm[639:608] = $urandom(seed); seed = seed + 1;
        f_vm[671:640] = $urandom(seed); seed = seed + 1;
        f_vm[703:672] = $urandom(seed); seed = seed + 1;
        f_vm[735:704] = $urandom(seed); seed = seed + 1;
        f_vm[767:736] = $urandom(seed); seed = seed + 1;
        f_vm[799:768] = $urandom(seed); seed = seed + 1;
        f_vm[831:800] = $urandom(seed); seed = seed + 1;
        f_vm[863:832] = $urandom(seed); seed = seed + 1;
        f_vm[895:864] = $urandom(seed); seed = seed + 1;
        f_vm[927:896] = $urandom(seed); seed = seed + 1;
        f_vm[959:928] = $urandom(seed); seed = seed + 1;
        f_vm[991:960] = $urandom(seed); seed = seed + 1;
        f_vm[1023:992] = $urandom(seed); seed = seed + 1;
    end endtask
    initial begin
        rst = 1;
        randomize_inputs;
        repeat (8) @(posedge clk);
        #0.05 rst = 0;
        for (cyc = 0; cyc < 400; cyc = cyc + 1) begin
            @(negedge clk);
            nchk = nchk + 1; if (t_su_SW[511:0] !== q4_aq_y[511:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_su_SW[511:0] %h ref %h cyc %0d", t_su_SW[511:0], q4_aq_y[511:0], cyc); end
            nchk = nchk + 1; if (t_su_NW[511:0] !== q4_aq_y[511:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_su_NW[511:0] %h ref %h cyc %0d", t_su_NW[511:0], q4_aq_y[511:0], cyc); end
            nchk = nchk + 1; if (t_su_SE[511:0] !== q4_aq_y[511:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_su_SE[511:0] %h ref %h cyc %0d", t_su_SE[511:0], q4_aq_y[511:0], cyc); end
            nchk = nchk + 1; if (t_su_NE[511:0] !== q4_aq_y[511:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_su_NE[511:0] %h ref %h cyc %0d", t_su_NE[511:0], q4_aq_y[511:0], cyc); end
            randomize_inputs;
        end
        $display("TB_hfd_quant checks=%0d mismatches=%0d", nchk, err);
        if (err != 0 || nchk == 0) $fatal(1, "FAIL");
        $finish;
    end
endmodule
