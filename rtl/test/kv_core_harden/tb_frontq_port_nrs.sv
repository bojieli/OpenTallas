`timescale 1ns/1ps
// DIE-KV-93 11-08: lock-step bench ot_qkh_head_frontq_native PORT_REGS=1 PORT_NRS=2 vs PORT_NRS=1 delayed one edge.
// Random c / row / e / lt / hid / q stream (valid bursts, FP32 beat pairs incl. broken pairs) for N edges after reset:
// new f_t0..f_t3 at edge i must equal old f_t0..f_t3 at edge i-1 EVERY edge from the 4th edge after reset release, and
// pack_fault must be identical at the same edge.  -DKV93_NRS_MUT (ports compared in reverse order) must FAIL.
module tb_frontq_port_nrs;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    reg [3:0] c; reg [255:0] row; reg [15:0] e; reg [11:0] lt; reg [1:0] hid; reg qv; reg [5:0] qb; reg [511:0] qd;
    wire [232:0] a0, a1, a2, a3, b0, b1, b2, b3; wire pa, pb;
    reg  [932:0] a_prev;
    ot_qkh_head_frontq_native #(.Q_FP32(1), .MUT(0), .PORT_REGS(1), .PORT_NRS(1)) u_a (.clk(clk), .rst_n(rst_n), .c_in(c),
        .row_in(row), .e_in(e), .lt_in(lt), .hid(hid), .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd),
        .f_t0(a0), .f_t1(a1), .f_t2(a2), .f_t3(a3), .pack_fault(pa));
`ifdef KV93_NRS_MUT
    localparam integer MB = 1;
`else
    localparam integer MB = 0;
`endif
    ot_qkh_head_frontq_native #(.Q_FP32(1), .MUT(0), .PORT_REGS(1), .PORT_NRS(2)) u_b (.clk(clk), .rst_n(rst_n), .c_in(c),
        .row_in(row), .e_in(e), .lt_in(lt), .hid(hid), .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd),
        .f_t0(b0), .f_t1(b1), .f_t2(b2), .f_t3(b3), .pack_fault(pb));
    integer i, k, mism = 0, edges = 0, beat = 0;
    initial begin
        c = 0; row = 0; e = 0; lt = 0; hid = 0; qv = 0; qb = 0; qd = 0; a_prev = 0;
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
            if (edges > 4 && ({b0, b1, b2, b3} !== (MB ? {a_prev[232:0], a_prev[465:233], a_prev[698:466], a_prev[931:699]}
                                                         : a_prev[931:0]) || pa !== pb)) begin
                mism = mism + 1;
                if (mism < 4) $display("MISMATCH edge %0d", edges);
            end
            a_prev = {1'b0, a0, a1, a2, a3};
        end
        if (mism == 0) $display("PASS frontq_port_nrs edges=%0d mismatches=0", edges);
        else $display("FAIL frontq_port_nrs edges=%0d mismatches=%0d", edges, mism);
        $finish;
    end
endmodule
