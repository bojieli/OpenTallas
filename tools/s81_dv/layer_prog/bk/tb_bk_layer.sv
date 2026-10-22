`timescale 1ns/1ps
// TOK-S81-GAPS/IDX (10-18): layer-job bench of the S81-DV bk selector dsdv_bk_sel, instantiated exactly as die.v u_bk_sel
// (bind_p4l3_g8 straps: tap_k 0x11, sink_k 0x10, ik 4, ek 5, uid 0x5B, eg_n 0).  The stimulus is the COMPILER's plan
// (tools/s81_dv/layer_prog/lower_bk.py gen): BK ingress beats on vi_s and the drain CTL on vi_n at their edges, from the
// layer fixture (attn.idx.score).  Edge convention: "edge e" = the posedge that samples the value driven for e; VO lines
// print vo_s right after posedge e.  The checker (lower_bk.py check) compares every non-zero vo_s beat with exp.txt.
module tb_bk_layer;
    localparam integer V = 276;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg  [V-1:0] vi_s = 0, vi_n = 0;
    wire [V-1:0] vo_s, vo_n;
    wire fault;
    dsdv_bk_sel u_bk_sel (.clk(clk), .rst_n(rst_n), .tap_k(8'h11), .sink_k(8'h10), .ik(3'd4), .ek(3'd5), .uid(8'h5B),
        .eg_n(1'b0), .vi_s(vi_s), .vo_n(vo_n), .vi_n(vi_n), .vo_s(vo_s), .fault(fault));
    reg [V-1:0] ss [int]; reg [V-1:0] sn [int];
    int ncyc, cyc = 0, fd, e, r, fault_at = -1, nvo = 0;
    reg [V-1:0] a, b;
    string fn;
    initial begin
        if (!$value$plusargs("STIM=%s", fn)) fn = "stim.txt";
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 1000;
        fd = $fopen(fn, "r");
        if (fd == 0) begin $display("TB_BK no stim %s", fn); $finish; end
        while (!$feof(fd)) begin
            r = $fscanf(fd, "%d %h %h\n", e, a, b);
            if (r == 3) begin ss[e] = a; sn[e] = b; end
        end
        $fclose(fd);
        $display("TB_BK stim edges %0d ncyc %0d", ss.num(), ncyc);
    end
    always @(negedge clk) begin
        vi_s <= ss.exists(cyc) ? ss[cyc] : '0;
        vi_n <= sn.exists(cyc) ? sn[cyc] : '0;
        if (cyc == 10) rst_n <= 1'b1;
    end
    always @(posedge clk) begin
        #0.1;
        if (vo_s != 0) begin $display("VO %0d %h", cyc, vo_s); nvo++; end
        if (rst_n && fault === 1'b1 && fault_at < 0) begin fault_at = cyc; $display("FAULT %0d", cyc); end
        if (vo_n != 0) $display("VON %0d %h", cyc, vo_n);
        if (u_bk_sel.u_g.vdv) $display("VD %0d %h", cyc, u_bk_sel.u_g.vdd[511:496]);   // a vd word enters the egress buffer
        cyc++;
        if (cyc == 20) $display("DV_SLICE_T0=%0d", $time);
        if (cyc >= ncyc) begin
            $display("TB_BK done cycles %0d vo_beats %0d fault_at %0d", cyc, nvo, fault_at);
            $finish;
        end
    end
endmodule
