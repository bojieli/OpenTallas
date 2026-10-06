`timescale 1ns/1ps
// lockstep bench of hfd_router (tools/hbm_die_wrap.py --tb): one seed 20261006
module tb_hfd_router;
    reg [0:0] ck;
    wire [128:0] eNE;
    wire [128:0] eNW;
    wire [128:0] eSE;
    wire [128:0] eSW;
    reg [255:0] f_su_NE;
    reg [255:0] f_su_NW;
    reg [255:0] f_su_SE;
    reg [255:0] f_su_SW;
    reg [511:0] f_vm;
    reg [0:0] rst;
    wire [63:0] t_cmdproc;
    hfd_router dut(.ck(ck), .eNE(eNE), .eNW(eNW), .eSE(eSE), .eSW(eSW), .f_su_NE(f_su_NE), .f_su_NW(f_su_NW), .f_su_SE(f_su_SE), .f_su_SW(f_su_SW), .f_vm(f_vm), .rst(rst), .t_cmdproc(t_cmdproc));
    reg clk = 0; always #0.4165 clk = ~clk;
    always @* ck[0] = clk;
    reg [0:0] d0_ck; always @(posedge clk) d0_ck <= ck;
    reg [0:0] d1_ck; always @(posedge clk) d1_ck <= d0_ck;
    reg [0:0] d2_ck; always @(posedge clk) d2_ck <= d1_ck;
    reg [0:0] d3_ck; always @(posedge clk) d3_ck <= d2_ck;
    reg [0:0] d_ck; always @(posedge clk) d_ck <= d3_ck;
    reg [255:0] d0_f_su_NE; always @(posedge clk) d0_f_su_NE <= f_su_NE;
    reg [255:0] d1_f_su_NE; always @(posedge clk) d1_f_su_NE <= d0_f_su_NE;
    reg [255:0] d2_f_su_NE; always @(posedge clk) d2_f_su_NE <= d1_f_su_NE;
    reg [255:0] d3_f_su_NE; always @(posedge clk) d3_f_su_NE <= d2_f_su_NE;
    reg [255:0] d_f_su_NE; always @(posedge clk) d_f_su_NE <= d3_f_su_NE;
    reg [255:0] d0_f_su_NW; always @(posedge clk) d0_f_su_NW <= f_su_NW;
    reg [255:0] d1_f_su_NW; always @(posedge clk) d1_f_su_NW <= d0_f_su_NW;
    reg [255:0] d2_f_su_NW; always @(posedge clk) d2_f_su_NW <= d1_f_su_NW;
    reg [255:0] d3_f_su_NW; always @(posedge clk) d3_f_su_NW <= d2_f_su_NW;
    reg [255:0] d_f_su_NW; always @(posedge clk) d_f_su_NW <= d3_f_su_NW;
    reg [255:0] d0_f_su_SE; always @(posedge clk) d0_f_su_SE <= f_su_SE;
    reg [255:0] d1_f_su_SE; always @(posedge clk) d1_f_su_SE <= d0_f_su_SE;
    reg [255:0] d2_f_su_SE; always @(posedge clk) d2_f_su_SE <= d1_f_su_SE;
    reg [255:0] d3_f_su_SE; always @(posedge clk) d3_f_su_SE <= d2_f_su_SE;
    reg [255:0] d_f_su_SE; always @(posedge clk) d_f_su_SE <= d3_f_su_SE;
    reg [255:0] d0_f_su_SW; always @(posedge clk) d0_f_su_SW <= f_su_SW;
    reg [255:0] d1_f_su_SW; always @(posedge clk) d1_f_su_SW <= d0_f_su_SW;
    reg [255:0] d2_f_su_SW; always @(posedge clk) d2_f_su_SW <= d1_f_su_SW;
    reg [255:0] d3_f_su_SW; always @(posedge clk) d3_f_su_SW <= d2_f_su_SW;
    reg [255:0] d_f_su_SW; always @(posedge clk) d_f_su_SW <= d3_f_su_SW;
    reg [511:0] d0_f_vm; always @(posedge clk) d0_f_vm <= f_vm;
    reg [511:0] d1_f_vm; always @(posedge clk) d1_f_vm <= d0_f_vm;
    reg [511:0] d2_f_vm; always @(posedge clk) d2_f_vm <= d1_f_vm;
    reg [511:0] d3_f_vm; always @(posedge clk) d3_f_vm <= d2_f_vm;
    reg [511:0] d_f_vm; always @(posedge clk) d_f_vm <= d3_f_vm;
    reg [0:0] d0_rst; always @(posedge clk) d0_rst <= rst;
    reg [0:0] d1_rst; always @(posedge clk) d1_rst <= d0_rst;
    reg [0:0] d2_rst; always @(posedge clk) d2_rst <= d1_rst;
    reg [0:0] d3_rst; always @(posedge clk) d3_rst <= d2_rst;
    reg [0:0] d_rst; always @(posedge clk) d_rst <= d3_rst;
    wire [0:0] r_rt_clk;
    assign r_rt_clk = dut.w_rt_clk;
    wire [0:0] r_rt_rst_n;
    assign r_rt_rst_n = dut.w_rt_rst_n;
    wire [0:0] r_rt_in_valid;
    assign r_rt_in_valid = {d_f_su_SW[0:0]};
    wire [511:0] r_rt_in_vals;
    assign r_rt_in_vals = {d_f_vm[511:0]};
    wire [0:0] r_rt_in_last;
    assign r_rt_in_last = {d_f_su_SW[1:1]};
    wire [0:0] r_rt_out_valid;
    reg [0:0] q1_rt_out_valid; always @(posedge clk) q1_rt_out_valid <= r_rt_out_valid;
    reg [0:0] q2_rt_out_valid; always @(posedge clk) q2_rt_out_valid <= q1_rt_out_valid;
    reg [0:0] q3_rt_out_valid; always @(posedge clk) q3_rt_out_valid <= q2_rt_out_valid;
    reg [0:0] q4_rt_out_valid; always @(posedge clk) q4_rt_out_valid <= q3_rt_out_valid;
    reg [0:0] q5_rt_out_valid; always @(posedge clk) q5_rt_out_valid <= q4_rt_out_valid;
    wire [53:0] r_rt_out_ids;
    reg [53:0] q1_rt_out_ids; always @(posedge clk) q1_rt_out_ids <= r_rt_out_ids;
    reg [53:0] q2_rt_out_ids; always @(posedge clk) q2_rt_out_ids <= q1_rt_out_ids;
    reg [53:0] q3_rt_out_ids; always @(posedge clk) q3_rt_out_ids <= q2_rt_out_ids;
    reg [53:0] q4_rt_out_ids; always @(posedge clk) q4_rt_out_ids <= q3_rt_out_ids;
    reg [53:0] q5_rt_out_ids; always @(posedge clk) q5_rt_out_ids <= q4_rt_out_ids;
    ot_gpu_router_topk_ps #(.N(384), .P(16), .K(6), .IW(9), .PIPESEL(1)) ref_rt (.clk(r_rt_clk), .rst_n(r_rt_rst_n), .in_valid(r_rt_in_valid), .in_vals(r_rt_in_vals), .in_last(r_rt_in_last), .out_valid(r_rt_out_valid), .out_ids(r_rt_out_ids));
    integer err = 0, nchk = 0, cyc;
    integer seed = 20261006;
    task automatic randomize_inputs; begin
        f_su_NE[31:0] = $urandom(seed); seed = seed + 1;
        f_su_NE[63:32] = $urandom(seed); seed = seed + 1;
        f_su_NE[95:64] = $urandom(seed); seed = seed + 1;
        f_su_NE[127:96] = $urandom(seed); seed = seed + 1;
        f_su_NE[159:128] = $urandom(seed); seed = seed + 1;
        f_su_NE[191:160] = $urandom(seed); seed = seed + 1;
        f_su_NE[223:192] = $urandom(seed); seed = seed + 1;
        f_su_NE[255:224] = $urandom(seed); seed = seed + 1;
        f_su_NW[31:0] = $urandom(seed); seed = seed + 1;
        f_su_NW[63:32] = $urandom(seed); seed = seed + 1;
        f_su_NW[95:64] = $urandom(seed); seed = seed + 1;
        f_su_NW[127:96] = $urandom(seed); seed = seed + 1;
        f_su_NW[159:128] = $urandom(seed); seed = seed + 1;
        f_su_NW[191:160] = $urandom(seed); seed = seed + 1;
        f_su_NW[223:192] = $urandom(seed); seed = seed + 1;
        f_su_NW[255:224] = $urandom(seed); seed = seed + 1;
        f_su_SE[31:0] = $urandom(seed); seed = seed + 1;
        f_su_SE[63:32] = $urandom(seed); seed = seed + 1;
        f_su_SE[95:64] = $urandom(seed); seed = seed + 1;
        f_su_SE[127:96] = $urandom(seed); seed = seed + 1;
        f_su_SE[159:128] = $urandom(seed); seed = seed + 1;
        f_su_SE[191:160] = $urandom(seed); seed = seed + 1;
        f_su_SE[223:192] = $urandom(seed); seed = seed + 1;
        f_su_SE[255:224] = $urandom(seed); seed = seed + 1;
        f_su_SW[31:0] = $urandom(seed); seed = seed + 1;
        f_su_SW[63:32] = $urandom(seed); seed = seed + 1;
        f_su_SW[95:64] = $urandom(seed); seed = seed + 1;
        f_su_SW[127:96] = $urandom(seed); seed = seed + 1;
        f_su_SW[159:128] = $urandom(seed); seed = seed + 1;
        f_su_SW[191:160] = $urandom(seed); seed = seed + 1;
        f_su_SW[223:192] = $urandom(seed); seed = seed + 1;
        f_su_SW[255:224] = $urandom(seed); seed = seed + 1;
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
    end endtask
    initial begin
        rst = 1;
        randomize_inputs;
        repeat (8) @(posedge clk);
        #0.05 rst = 0;
        for (cyc = 0; cyc < 4000; cyc = cyc + 1) begin
            @(negedge clk);
            nchk = nchk + 1; if (t_cmdproc[54:54] !== q5_rt_out_valid[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_cmdproc[54:54] %h ref %h cyc %0d", t_cmdproc[54:54], q5_rt_out_valid[0:0], cyc); end
            nchk = nchk + 1; if (eSW[54:54] !== q5_rt_out_valid[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH eSW[54:54] %h ref %h cyc %0d", eSW[54:54], q5_rt_out_valid[0:0], cyc); end
            nchk = nchk + 1; if (eNW[54:54] !== q5_rt_out_valid[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH eNW[54:54] %h ref %h cyc %0d", eNW[54:54], q5_rt_out_valid[0:0], cyc); end
            nchk = nchk + 1; if (eSE[54:54] !== q5_rt_out_valid[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH eSE[54:54] %h ref %h cyc %0d", eSE[54:54], q5_rt_out_valid[0:0], cyc); end
            nchk = nchk + 1; if (eNE[54:54] !== q5_rt_out_valid[0:0]) begin err = err + 1; if (err < 10) $display("MISMATCH eNE[54:54] %h ref %h cyc %0d", eNE[54:54], q5_rt_out_valid[0:0], cyc); end
            nchk = nchk + 1; if (t_cmdproc[53:0] !== q5_rt_out_ids[53:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_cmdproc[53:0] %h ref %h cyc %0d", t_cmdproc[53:0], q5_rt_out_ids[53:0], cyc); end
            nchk = nchk + 1; if (eSW[53:0] !== q5_rt_out_ids[53:0]) begin err = err + 1; if (err < 10) $display("MISMATCH eSW[53:0] %h ref %h cyc %0d", eSW[53:0], q5_rt_out_ids[53:0], cyc); end
            nchk = nchk + 1; if (eNW[53:0] !== q5_rt_out_ids[53:0]) begin err = err + 1; if (err < 10) $display("MISMATCH eNW[53:0] %h ref %h cyc %0d", eNW[53:0], q5_rt_out_ids[53:0], cyc); end
            nchk = nchk + 1; if (eSE[53:0] !== q5_rt_out_ids[53:0]) begin err = err + 1; if (err < 10) $display("MISMATCH eSE[53:0] %h ref %h cyc %0d", eSE[53:0], q5_rt_out_ids[53:0], cyc); end
            nchk = nchk + 1; if (eNE[53:0] !== q5_rt_out_ids[53:0]) begin err = err + 1; if (err < 10) $display("MISMATCH eNE[53:0] %h ref %h cyc %0d", eNE[53:0], q5_rt_out_ids[53:0], cyc); end
            randomize_inputs;
        end
        $display("TB_hfd_router checks=%0d mismatches=%0d", nchk, err);
        if (err != 0 || nchk == 0) $fatal(1, "FAIL");
        $finish;
    end
endmodule
