`timescale 1ns/1ps
// QW-SLICE7-LEAVES red2 lockstep bench: DUT `DUTMOD vs REF `REFMOD on the same random legal segment stream
// (SUM / MAX, optional SQ, 1..16 vectors, partial last vectors, gaps 0..3, back to back).  Every reduction result
// (red_addr, red_data) must match in order, each exactly `OFF edges later; rd_v exactly `RDOFF later; fault 0 on both.
module tb_red2;
    reg ck = 0; always #5 ck = ~ck;
    reg rst_n = 0;
    reg [7:0] l_ov = 0; reg [255:0] l_out = 0; reg [1:0] l_red0 = 0; reg l_redsq0 = 0, l_last0 = 0; reg [23:0] l_raddr0 = 0;
    wire d_we, r_we, d_rdv, r_rdv, d_busy, r_busy, d_f, r_f;
    wire [23:0] d_addr, r_addr; wire [31:0] d_data, r_data;
    `DUTMOD dut (.ck(ck), .rst_n(rst_n), .l_ov(l_ov), .l_out(l_out), .l_red0(l_red0), .l_redsq0(l_redsq0), .l_last0(l_last0),
        .l_raddr0(l_raddr0), .red_we(d_we), .red_addr(d_addr), .red_data(d_data), .rd_v(d_rdv), .busy(d_busy), .fault(d_f));
    `REFMOD refm (.ck(ck), .rst_n(rst_n), .l_ov(l_ov), .l_out(l_out), .l_red0(l_red0), .l_redsq0(l_redsq0), .l_last0(l_last0),
        .l_raddr0(l_raddr0), .red_we(r_we), .red_addr(r_addr), .red_data(r_data), .rd_v(r_rdv), .busy(r_busy), .fault(r_f));
    integer cyc = 0;
    integer rq_t[$], dq_t[$]; reg [55:0] rq_v[$], dq_v[$];
    reg [4095:0] rdv_hist = 0;
    integer nseg = 0, nmax = 0, nsq = 0, ncheck = 0, errors = 0;
    function automatic [31:0] rnd_f();
        reg [31:0] r; integer c;
        c = $urandom % 32;
        if (c == 0) rnd_f = 32'd0;
        else if (c == 1) rnd_f = 32'h80000000;
        else if (c == 2) rnd_f = {$urandom % 2, 8'd0, 23'($urandom)};          // subnormal
        else rnd_f = {1'($urandom % 2), 8'(110 + $urandom % 31), 23'($urandom)};
    endfunction
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (r_we) begin rq_t.push_back(cyc); rq_v.push_back({r_addr, r_data}); end
        if (d_we) begin dq_t.push_back(cyc); dq_v.push_back({d_addr, d_data}); end
        rdv_hist <= {rdv_hist[4094:0], r_rdv};
        if (rst_n && cyc > 4 + `RDOFF && d_rdv !== rdv_hist[`RDOFF - 1]) begin
            errors = errors + 1; if (errors < 5) $display("MISMATCH rd_v cyc=%0d", cyc); end
        if (rst_n && (d_f !== 1'b0 || r_f !== 1'b0)) begin errors = errors + 1; if (errors < 5) $display("MISMATCH fault cyc=%0d d=%b r=%b", cyc, d_f, r_f); end
    end
    integer s, vv, nv, m, gap, j, mode, sq, total;
    initial begin
        if (!$value$plusargs("seed=%d", s)) s = 1;
        void'($urandom(s));
        if (!$value$plusargs("segs=%d", total)) total = 3000;
        repeat (6) @(negedge ck); rst_n = 1;
        repeat (12) @(negedge ck);
        for (nseg = 0; nseg < total; nseg = nseg + 1) begin
            nv = 1 + $urandom % 16; mode = 1 + $urandom % 2; sq = ($urandom % 3) == 0;
            if (mode == 2) nmax = nmax + 1; if (sq) nsq = nsq + 1;
            for (vv = 0; vv < nv; vv = vv + 1) begin
                m = (vv == nv - 1) ? 1 + $urandom % 8 : 8;
                l_ov = 8'((1 << m) - 1);
                for (j = 0; j < 8; j = j + 1)
                    l_out[32*j +: 32] = (j < m) ? rnd_f() : (mode == 2 ? 32'h0 : (($urandom % 4 == 0) ? 32'd0 : rnd_f()));
                l_red0 = 2'(mode); l_redsq0 = sq; l_last0 = (vv == nv - 1); l_raddr0 = 24'($urandom);
                @(negedge ck);
            end
            l_ov = 0; l_red0 = 0; l_last0 = 0; l_redsq0 = 0; l_out = {8{rnd_f()}};
            gap = $urandom % 4; if ($urandom % 3 == 0) gap = 0;
            repeat (gap) @(negedge ck);
        end
        l_ov = 0; l_red0 = 0;
        repeat (400) @(negedge ck);
        if (rq_t.size() != dq_t.size()) begin errors = errors + 1; $display("MISMATCH count ref=%0d dut=%0d", rq_t.size(), dq_t.size()); end
        for (j = 0; j < rq_t.size() && j < dq_t.size(); j = j + 1) begin
            ncheck = ncheck + 1;
            if (rq_v[j] !== dq_v[j] || dq_t[j] - rq_t[j] != `OFF) begin
                errors = errors + 1;
                if (errors < 8) $display("MISMATCH result %0d ref t=%0d %h dut t=%0d %h", j, rq_t[j], rq_v[j], dq_t[j], dq_v[j]);
            end
        end
        if (d_busy !== 1'b0) begin errors = errors + 1; $display("MISMATCH busy stuck"); end
        if (ncheck < 100) begin errors = errors + 1; $display("MISMATCH too few results %0d", ncheck); end
        if (errors) begin $display("RED2_EQ FAIL errors=%0d results=%0d", errors, ncheck); $fatal(1, "RED2_EQ FAIL"); end
        $display("RED2_EQ PASS results=%0d segments=%0d max=%0d sq=%0d offset=%0d rdv_offset=%0d", ncheck, nseg, nmax, nsq, `OFF, `RDOFF);
        $finish;
    end
endmodule
