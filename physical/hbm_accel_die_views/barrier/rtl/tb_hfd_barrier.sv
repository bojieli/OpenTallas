`timescale 1ns/1ps
// lockstep bench of hfd_barrier (tools/hbm_die_wrap.py --tb): one seed 20261006
module tb_hfd_barrier;
    reg [0:0] ck;
    reg [63:0] f_cmdproc;
    reg [0:0] rst;
    wire [63:0] t_cmdproc;
    hfd_barrier dut(.ck(ck), .f_cmdproc(f_cmdproc), .rst(rst), .t_cmdproc(t_cmdproc));
    reg clk = 0; always #0.4165 clk = ~clk;
    always @* ck[0] = clk;
    reg [0:0] d0_ck; always @(posedge clk) d0_ck <= ck;
    reg [0:0] d1_ck; always @(posedge clk) d1_ck <= d0_ck;
    reg [0:0] d_ck; always @(posedge clk) d_ck <= d1_ck;
    reg [63:0] d0_f_cmdproc; always @(posedge clk) d0_f_cmdproc <= f_cmdproc;
    reg [63:0] d1_f_cmdproc; always @(posedge clk) d1_f_cmdproc <= d0_f_cmdproc;
    reg [63:0] d_f_cmdproc; always @(posedge clk) d_f_cmdproc <= d1_f_cmdproc;
    reg [0:0] d0_rst; always @(posedge clk) d0_rst <= rst;
    reg [0:0] d1_rst; always @(posedge clk) d1_rst <= d0_rst;
    reg [0:0] d_rst; always @(posedge clk) d_rst <= d1_rst;
    wire [0:0] r_n0_clk;
    assign r_n0_clk = dut.w_n0_clk;
    wire [0:0] r_n0_rst_n;
    assign r_n0_rst_n = dut.w_n0_rst_n;
    wire [31:0] r_n0_arr;
    assign r_n0_arr = {d_f_cmdproc[31:0]};
    wire [0:0] r_n0_up;
    reg [0:0] q0_n0_up; always @(posedge clk) q0_n0_up <= r_n0_up;
    reg [0:0] q1_n0_up; always @(posedge clk) q1_n0_up <= q0_n0_up;
    reg [0:0] q_n0_up; always @(posedge clk) q_n0_up <= q1_n0_up;
    wire [0:0] r_n0_rel_in;
    assign r_n0_rel_in = dut.w_n0_rel_in;
    wire [31:0] r_n0_rel;
    reg [31:0] q0_n0_rel; always @(posedge clk) q0_n0_rel <= r_n0_rel;
    reg [31:0] q1_n0_rel; always @(posedge clk) q1_n0_rel <= q0_n0_rel;
    reg [31:0] q_n0_rel; always @(posedge clk) q_n0_rel <= q1_n0_rel;
    ot_gpu_barrier_node #(.K(32)) ref_n0 (.clk(r_n0_clk), .rst_n(r_n0_rst_n), .arr(r_n0_arr), .up(r_n0_up), .rel_in(r_n0_rel_in), .rel(r_n0_rel));
    wire [0:0] r_n1_clk;
    assign r_n1_clk = dut.w_n1_clk;
    wire [0:0] r_n1_rst_n;
    assign r_n1_rst_n = dut.w_n1_rst_n;
    wire [31:0] r_n1_arr;
    assign r_n1_arr = {d_f_cmdproc[63:32]};
    wire [0:0] r_n1_up;
    reg [0:0] q0_n1_up; always @(posedge clk) q0_n1_up <= r_n1_up;
    reg [0:0] q1_n1_up; always @(posedge clk) q1_n1_up <= q0_n1_up;
    reg [0:0] q_n1_up; always @(posedge clk) q_n1_up <= q1_n1_up;
    wire [0:0] r_n1_rel_in;
    assign r_n1_rel_in = dut.w_n1_rel_in;
    wire [31:0] r_n1_rel;
    reg [31:0] q0_n1_rel; always @(posedge clk) q0_n1_rel <= r_n1_rel;
    reg [31:0] q1_n1_rel; always @(posedge clk) q1_n1_rel <= q0_n1_rel;
    reg [31:0] q_n1_rel; always @(posedge clk) q_n1_rel <= q1_n1_rel;
    ot_gpu_barrier_node #(.K(32)) ref_n1 (.clk(r_n1_clk), .rst_n(r_n1_rst_n), .arr(r_n1_arr), .up(r_n1_up), .rel_in(r_n1_rel_in), .rel(r_n1_rel));
    integer err = 0, nchk = 0, cyc;
    integer seed = 20261006;
    task automatic randomize_inputs; begin
        f_cmdproc[31:0] = $urandom(seed); seed = seed + 1;
        f_cmdproc[63:32] = $urandom(seed); seed = seed + 1;
    end endtask
    initial begin
        rst = 1;
        randomize_inputs;
        repeat (8) @(posedge clk);
        #0.05 rst = 0;
        for (cyc = 0; cyc < 400; cyc = cyc + 1) begin
            @(negedge clk);
            nchk = nchk + 1; if (t_cmdproc[31:0] !== q_n0_rel[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_cmdproc[31:0] %h ref %h cyc %0d", t_cmdproc[31:0], q_n0_rel[31:0], cyc); end
            nchk = nchk + 1; if (t_cmdproc[63:32] !== q_n1_rel[31:0]) begin err = err + 1; if (err < 10) $display("MISMATCH t_cmdproc[63:32] %h ref %h cyc %0d", t_cmdproc[63:32], q_n1_rel[31:0], cyc); end
            randomize_inputs;
        end
        $display("TB_hfd_barrier checks=%0d mismatches=%0d", nchk, err);
        if (err != 0 || nchk == 0) $fatal(1, "FAIL");
        $finish;
    end
endmodule
