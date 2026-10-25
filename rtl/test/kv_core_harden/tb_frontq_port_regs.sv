`timescale 1ns/1ps
// KVG3-CORES 10-24 (COORD ruling 2): miter ot_qkh_head_frontq_native PORT_REGS=1 vs PORT_REGS=0 (the original shared
// relay stage).  Random c / row / e / lt / hid / q stream (valid bursts, FP32 beat pairs incl. broken pairs) for N edges
// after reset: f_t0..f_t3 and pack_fault must be identical EVERY edge (0 cycles).  -DKVG3_FRONTQ_PRMUT (port ft takes the
// neighbouring port's Q slice) must FAIL.  usage: tools/kv_core_harden/frontq_port_regs_bench.sh
module tb_frontq_port_regs;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    reg [3:0] c; reg [255:0] row; reg [15:0] e; reg [11:0] lt; reg [1:0] hid; reg qv; reg [5:0] qb; reg [511:0] qd;
    wire [232:0] a0, a1, a2, a3, b0, b1, b2, b3; wire pa, pb;
    ot_qkh_head_frontq_native #(.Q_FP32(1), .MUT(0), .PORT_REGS(0)) u_a (.clk(clk), .rst_n(rst_n), .c_in(c), .row_in(row),
        .e_in(e), .lt_in(lt), .hid(hid), .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd),
        .f_t0(a0), .f_t1(a1), .f_t2(a2), .f_t3(a3), .pack_fault(pa));
    ot_qkh_head_frontq_native #(.Q_FP32(1), .MUT(0), .PORT_REGS(1)) u_b (.clk(clk), .rst_n(rst_n), .c_in(c), .row_in(row),
        .e_in(e), .lt_in(lt), .hid(hid), .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd),
        .f_t0(b0), .f_t1(b1), .f_t2(b2), .f_t3(b3), .pack_fault(pb));
    integer i, k, mism = 0, edges = 0, beat = 0;
    initial begin
        c = 0; row = 0; e = 0; lt = 0; hid = 0; qv = 0; qb = 0; qd = 0;
        repeat (8) @(posedge clk);
        #0.1 rst_n = 1;
        for (i = 0; i < 6000; i = i + 1) begin
            #0.1;
            c = $urandom; e = $urandom; lt = $urandom; hid = $urandom;
            for (k = 0; k < 8; k = k + 1) row[32*k +: 32] = $urandom;
            for (k = 0; k < 16; k = k + 1) qd[32*k +: 32] = $urandom;
            qv = ($urandom % 3) != 0;
            if (qv) begin qb = {beat[4:0], beat[0]}; if (($urandom % 50) == 0) qb = $urandom; beat = beat + 1; end
            @(posedge clk); #0.05;
            edges = edges + 1;
            if ({a0, a1, a2, a3, pa} !== {b0, b1, b2, b3, pb}) begin
                mism = mism + 1;
                if (mism < 4) $display("MISMATCH edge %0d port0 %0d port1 %0d port2 %0d port3 %0d pf %b/%b", edges,
                                       a0 !== b0, a1 !== b1, a2 !== b2, a3 !== b3, pa, pb);
            end
        end
        if (mism == 0) $display("PASS frontq_port_regs edges=%0d mismatches=0", edges);
        else $display("FAIL frontq_port_regs edges=%0d mismatches=%0d", edges, mism);
        $finish;
    end
endmodule
