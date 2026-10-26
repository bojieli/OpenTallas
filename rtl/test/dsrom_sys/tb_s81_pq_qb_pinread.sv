`timescale 1ns/1ps
module tb_s81_pq_qb_pinread;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg [9:0] aqi = 0;
    reg [511:0] aq_q = 0;
    reg [19:0] aq_e = 0;
    reg [15:0] h_b0 = 0, h_b1 = 0;
    reg [1:0] hw_sv = 0;
    wire [255:0] q0, q1, ref0, ref1;
    wire [9:0] e0, e1, refe0, refe1;
    wire fault;
    ot_s81_pq_qb_pinread_native dut (.clk(clk), .rst_n(rst_n), .consume(1'b1), .clk_bank({4{clk}}), .aq_p(aq_p), .aqi_d(aqi), .aq_q(aq_q), .aq_e(aq_e),
        .h_b0(h_b0), .h_b1(h_b1), .hw_sv(hw_sv), .hq0(q0), .hq1(q1), .he0(e0), .he1(e1), .fault(fault));
    ot_v41_pqc_qb #(.KMAX(6144)) ref_qb (.clk(clk), .rst_n(rst_n), .aqi_d(aqi), .aq_q(aq_q), .aq_e(aq_e),
        .h_b0(h_b0), .h_b1(h_b1), .hw_sv(hw_sv), .hq0(ref0), .hq1(ref1), .he0(refe0), .he1(refe1));
    wire [9:0] aq_p = {^aq_e[19:10], ^aq_q[511:448], ^aq_q[447:384], ^aq_q[383:320], ^aq_q[319:256],
                                  ^aq_e[9:0], ^aq_q[255:192], ^aq_q[191:128], ^aq_q[127:64], ^aq_q[63:0]};
    reg[531:0] ref_d1,ref_d2,ref_d3,ref_d4;
    always @(posedge clk) begin ref_d1<={ref0,ref1,refe0,refe1};ref_d2<=ref_d1;ref_d3<=ref_d2;ref_d4<=ref_d3; end
    reg compare = 0;
    integer checks = 0, cycle = 0, par, block, k, i;
    always @(negedge clk) begin
        cycle = cycle + 1;
        if (compare) begin
            if ({q0,q1,e0,e1} !== ref_d4) begin
                $display("PQ_QB_PINREAD FAIL cycle=%0d q0=%h ref0=%h q1=%h ref1=%h", cycle,q0,ref0,q1,ref1);
                $fatal(1, "bit-exact mismatch");
            end
            if (fault) $fatal(1, "unexpected parity fault");
            checks = checks + 532;
        end
    end
    initial begin
        repeat (8) @(negedge clk); rst_n = 1;
        repeat (8) @(negedge clk);
        for (par = 0; par < 2; par = par + 1)
            for (block = 0; block < 192; block = block + 2) begin
                aqi = {1'b1,8'(block),1'(par)};
                for (k = 0; k < 16; k = k + 1)
                    aq_q[32*k +: 32] = 32'h9f135ac2 ^ 32'(block * 145 + k * 1031 + par * 3451);
                aq_e = 20'(block * 1717 + par * 313);
                repeat (3) @(negedge clk);
            end
        aqi = 0; repeat (8) @(negedge clk);
        compare = 1;
        for (i = 0; i < 384; i = i + 1) begin
            h_b0 = 16'(i);
            h_b1 = 16'(((i + 16) % 384) ^ 8);
            hw_sv = 3;
            @(negedge clk);
        end
        for (i = 0; i < 256; i = i + 1) begin
            h_b0 = 16'((13*i) % 384);
            h_b1 = 16'((((13*i) % 384 + 32) % 384) ^ 8);
            hw_sv = 2'(i);
            @(negedge clk);
        end
        hw_sv = 0; repeat (10) @(negedge clk);
        compare = 0;
        if (checks < 300000) $fatal(1, "insufficient production coverage");
        // Corrupt a stored exponent bit: protection includes the flop side
        // data as well as all four physical 256-bit SRAM banks.
        dut.u_head.meta[0][0][0] = ~dut.u_head.meta[0][0][0];
        h_b0 = 0; hw_sv = 1;
        repeat (8) @(negedge clk);
        if (!fault) $fatal(1, "exponent corruption was not caught");
        hw_sv = 0; repeat (4) @(negedge clk);
        if (!fault) $fatal(1, "parity fault not sticky");
        $display("PQ_QB_PINREAD PASS checks=%0d logical_words=384 rows=96 macros=4 exponent_fault=1 read_latency_delta=4", checks);
        $finish;
    end
endmodule
