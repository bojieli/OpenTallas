`timescale 1ns/1ps
// tb_aq12_xmem_eq (S81-TILES2 2026-10-17; S81-TILES3 10-17 fork): the vq-only fork ot_s81sl_aq12x, its xd driven with
// x delayed 12 cycles by a testbench line, against the shared ot_dsrom_aq12 (flop wait line), side by side on one random
// stimulus; every output compared every cycle (vo / fault from reset release, the unreset data outputs q / e / y once
// both lines hold written data: cycle >= WARM).  +define+OT_AQ12_MUT_XPTR delays xd by 11 only: the bench must FAIL
// (aq_err).  Second: ot_s81sl_vq AQ_XMEM 2 (one-macro sub-beat ring + the fork) vs 0 (shared aq12) on random in-order
// sub-beat streams, beats alternating at random between the y and the u port (xf / xf_v / xf_s / fault every cycle);
// +define+OT_VQ_MUT_XPTR (ring one row short) must FAIL (vq2_err).
module tb_aq12_xmem_eq #(parameter integer N = 20000, parameter integer SEED = 1017);
    localparam integer WARM = 40;
    reg clk = 1'b0, rst_n = 1'b0;
    always #0.5 clk = ~clk;
    reg v; reg [1023:0] x;
    wire vo0, vo1, f0, f1; wire [255:0] q0, q1; wire signed [9:0] e0, e1; wire [511:0] y0, y1;
    ot_dsrom_aq12 u_ref (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .vo(vo0), .q(q0), .e(e0), .y(y0), .fault(f0));
`ifdef OT_AQ12_MUT_XPTR
    localparam integer XD = 11;     // mutant: one cycle short
`else
    localparam integer XD = 12;
`endif
    reg [1023:0] xl [0:XD-1];
    integer t;
    always @(posedge clk) begin xl[0] <= x; for (t = 1; t < XD; t = t + 1) xl[t] <= xl[t-1]; end
    ot_s81sl_aq12x u_dut (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .vo(vo1), .q(q1), .e(e1), .y(y1), .fault(f1), .xd(xl[XD-1]));
    // vq pair
    reg yv; reg [2:0] yi; reg [255:0] yd; reg mv, mq, mb; reg [7:0] mi;
    wire xfv0, xfv1, xfs0, xfs1, vf0, vf1; wire [275:0] xf0, xf1;
    ot_s81sl_vq #(.AQ_XMEM(0)) v_ref (.clk(clk), .rst_n(rst_n), .y_v(yv), .y_i(yi), .y({yd[255:240], yd[223:208], yd[191:176], yd[159:144], yd[127:112], yd[95:80], yd[63:48], yd[31:16]}), .u_v(1'b0), .u_i(3'd0), .u(256'd0),
        .sid(4'd3), .k(3'd2), .m_v(mv), .m_q(mq), .m_b(mb), .m_i(mi), .um_v(1'b0), .um_q(1'b0), .um_b(1'b0), .um_i(8'd0),
        .xf_v(xfv0), .xf_s(xfs0), .xf(xf0), .fault(vf0));
    wire xfv2, xfs2, vf2; wire [275:0] xf2;
    reg uon;
    ot_s81sl_vq #(.AQ_XMEM(2)) v_d2 (.clk(clk), .rst_n(rst_n), .y_v(yv && !uon), .y_i(yi), .y({yd[255:240], yd[223:208], yd[191:176], yd[159:144], yd[127:112], yd[95:80], yd[63:48], yd[31:16]}), .u_v(yv && uon), .u_i(yi), .u(yd),
        .sid(4'd3), .k(3'd2), .m_v(mv), .m_q(mq), .m_b(mb), .m_i(mi), .um_v(1'b0), .um_q(1'b0), .um_b(1'b0), .um_i(8'd0),
        .xf_v(xfv2), .xf_s(xfs2), .xf(xf2), .fault(vf2));
    integer seed, cyc, err, nvo, nxf, verr, verr2, i, gap, sb;
    function automatic [31:0] rword(input integer r1, input integer r2, input integer r3);
        reg [7:0] ex;
        begin
            ex = 8'd100 + (r1 % 50);
            if ((r2 % 64) == 0) ex = 8'd0;                 // subnormal / zero
            if ((r2 % 64) == 1) ex = 8'd1;
            if ((r2 % 4096) == 2) ex = 8'hFF;              // nonfinite: fault path
            if ((r2 % 97) == 3) ex = 8'd60 + (r1 % 40);    // tiny: floor path
            rword = {r3[31], ex, r3[22:0] ^ r1[22:0]};
        end
    endfunction
    initial begin
        seed = SEED; uon = 1'b0; verr2 = 0; err = 0; nvo = 0; nxf = 0; verr = 0; gap = 0; sb = 0;
        v = 1'b0; x = 1024'd0; yv = 1'b0; yi = 3'd0; yd = 256'd0; mv = 1'b0; mq = 1'b1; mb = 1'b0; mi = 8'd0;
        i = $urandom(seed);
        repeat (3) @(posedge clk);
        rst_n = 1'b1;
        for (cyc = 0; cyc < N; cyc = cyc + 1) begin
            @(negedge clk);
            // compare (values settled after the posedge)
            if (vo0 !== vo1 || f0 !== f1) begin err = err + 1; if (err < 10) $display("MISMATCH aq ctl cyc=%0d vo %b/%b fault %b/%b", cyc, vo0, vo1, f0, f1); end
            if (cyc >= WARM && (q0 !== q1 || e0 !== e1 || y0 !== y1)) begin
                err = err + 1; if (err < 10) $display("MISMATCH aq data cyc=%0d vo=%b", cyc, vo0);
            end
            if (vo0) nvo = nvo + 1;
            if (xfv0) nxf = nxf + 1;
            if (xfv0 !== xfv2 || xfs0 !== xfs2 || vf0 !== vf2 || (cyc >= WARM && xf0 !== xf2)) begin
                verr2 = verr2 + 1; if (verr2 < 10) $display("MISMATCH vq2 cyc=%0d xf_v %b/%b fault %b/%b", cyc, xfv0, xfv2, vf0, vf2);
            end
            // aq stimulus: a block on ~70 % of cycles
            v = ($urandom % 10) < 7;
            for (i = 0; i < 32; i = i + 1) x[32*i +: 32] = rword($urandom, $urandom, $urandom);
            // vq stimulus: 8 in-order sub-beats (one beat), then a gap longer than vq's 40 send steps; a mode command
            // now and then in the gaps
            mv = 1'b0;
            if (gap > 0) begin yv = 1'b0; gap = gap - 1; end
            else begin
                yv = 1'b1; yi = sb[2:0];
                for (i = 0; i < 8; i = i + 1) begin yd[32*i +: 32] = rword($urandom, $urandom, $urandom); yd[32*i +: 16] = 16'd0; end  // vn's y: BF16 (low half 0)
                sb = sb + 1;
                if (sb == 8) begin sb = 0; gap = 44 + ($urandom % 20); uon = $urandom; end
            end
            if (!yv && ($urandom % 8) == 0) begin mv = 1'b1; mq = $urandom; mb = $urandom; mi = $urandom; end
        end
        $display("SUMMARY aq12_xmem_eq N=%0d aq_valid=%0d aq_err=%0d vq_frag=%0d vq_err=%0d vq2_err=%0d", N, nvo, err, nxf, verr, verr2);
        if (err == 0 && verr == 0 && verr2 == 0 && nvo > 1000 && nxf > 100) $display("PASS aq12_xmem_eq");
        else $display("FAIL aq12_xmem_eq");
        $finish;
    end
endmodule
