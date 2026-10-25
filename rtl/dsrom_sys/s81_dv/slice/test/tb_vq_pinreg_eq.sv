`timescale 1ns/1ps
// S81-NATIVE3 (10-17): ot_s81sl_vq with pin-registered mode/valid inputs vs the CLOSED view's RTL (b6d9d4515, renamed
// ot_s81sl_vq_ref by tools/s81_slice/vq_pinreg_eq.sh).  Random vectors on the y and the u streams under the static
// schedule (a mode command, then the 8 sub-beats in order with random gaps; the next command only after the previous
// vector's last fragment, at the tightest spacing 0..4 edges): xf_v, xf_s and xf must be identical on every edge and
// fault must stay 0.  Then a collision phase (y_v && u_v): both must raise fault on the same edge.
module tb_vq_pinreg_eq;
    parameter integer NVEC = 400;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg y_v = 0, u_v = 0, m_v = 0, m_q = 0, m_b = 0, um_v = 0, um_q = 0, um_b = 0;
    reg [2:0] y_i = 0, u_i = 0; reg [255:0] y = 0, u = 0; reg [7:0] m_i = 0, um_i = 0;
    wire [3:0] sid = 4'd9; wire [2:0] k = 3'd3;
    wire rv, rs, nv, ns, rf, nf; wire [275:0] rx, nx;
    ot_s81sl_vq_ref #(.AQ_XMEM(2)) u_ref (.clk(clk), .rst_n(rst_n), .y_v(y_v), .y_i(y_i), .y(y), .u_v(u_v), .u_i(u_i), .u(u),
        .sid(sid), .k(k), .m_v(m_v), .m_q(m_q), .m_b(m_b), .m_i(m_i), .um_v(um_v), .um_q(um_q), .um_b(um_b), .um_i(um_i),
        .xf_v(rv), .xf_s(rs), .xf(rx), .fault(rf));
    ot_s81sl_vq #(.AQ_XMEM(2)) u_new (.clk(clk), .rst_n(rst_n), .y_v(y_v), .y_i(y_i), .y({y[255:240], y[223:208], y[191:176], y[159:144], y[127:112], y[95:80], y[63:48], y[31:16]}), .u_v(u_v), .u_i(u_i), .u(u),
        .sid(sid), .k(k), .m_v(m_v), .m_q(m_q), .m_b(m_b), .m_i(m_i), .um_v(um_v), .um_q(um_q), .um_b(um_b), .um_i(um_i),
        .xf_v(nv), .xf_s(ns), .xf(nx), .fault(nf));
    integer cyc = 0, mism = 0, frags = 0, starts = 0, vec = 0, i, j, gap, chk = 1, rf_at = -1, nf_at = -1;
    function [31:0] rf32; input integer dummy; begin rf32 = {$urandom % 2 == 1, 8'd100 + 8'($urandom % 50), 23'($urandom)}; end endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
`ifdef TRACE
        if (cyc < 120 && (u_ref.sv_ || u_ref.bv || u_ref.vo || u_ref.run)) $display("T%0d sv%b si%0d bv%b bbk%b vo%b blo%b run%b st%0d", cyc, u_ref.sv_, u_ref.si_, u_ref.bv, u_ref.bbk, u_ref.vo, u_ref.blo, u_ref.run, u_ref.st);
`endif
        if (chk && rst_n) begin
            if (rv !== nv || rs !== ns || (rv && rx !== nx) || rf !== nf) begin
                mism = mism + 1; if (mism <= 8) $display("MISMATCH cyc=%0d ref v%b s%b f%b new v%b s%b f%b xf_eq=%b", cyc, rv, rs, rf, nv, ns, nf, rx === nx);
            end
            if (rv) frags = frags + 1; if (rs) starts = starts + 1;
        end
        if (!rf && rf_at < 0 && ((u_ref.af && u_ref.vo) || u_ref.ord_f || u_ref.mcol || (u_ref.vo && u_ref.blo && u_ref.run))) $display("REFFAULT cyc=%0d af=%b ord=%b mcol=%b runclash=%b", cyc, u_ref.af && u_ref.vo, u_ref.ord_f, u_ref.mcol, u_ref.vo && u_ref.blo && u_ref.run);
        if (rf && rf_at < 0) rf_at = cyc; if (nf && nf_at < 0) nf_at = cyc;
    end
    // garbage on every command/data field in idle cycles (a raw-pin mux select or a crossed field shows up)
    task idle; begin m_q = $urandom; m_b = $urandom; m_i = $urandom; um_q = $urandom; um_b = $urandom; um_i = $urandom;
        y = {8{rf32(0)}} & {8{32'hFFFF0000}}; /* vn's y is BF16: low halves 0 (packed pins) */ u = {8{rf32(0)}}; y_i = $urandom; u_i = $urandom; end endtask
    task tick; begin @(negedge clk); end endtask
    initial begin
        idle; repeat (4) tick; rst_n = 1; repeat (8) tick;
        for (vec = 0; vec < NVEC; vec = vec + 1) begin
            // command: m (vp) or um (vs); families q / BF16 / both
            idle; if ($urandom % 2) begin m_v = 1; m_q = ($urandom % 3) != 1; m_b = !m_q || ($urandom % 2); end
            else begin um_v = 1; um_q = ($urandom % 3) != 1; um_b = !um_q || ($urandom % 2); end
            tick; m_v = 0; um_v = 0; idle;
            gap = $urandom % 6; repeat (gap) begin tick; idle; end
            i = $urandom % 2;    // stream y or u for this vector
            for (j = 0; j < 8; j = j + 1) begin
                if (i) begin y_v = 1; y_i = j; for (gap = 0; gap < 8; gap = gap + 1) y[32 * gap +: 32] = rf32(0); end
                else begin u_v = 1; u_i = j; for (gap = 0; gap < 8; gap = gap + 1) u[32 * gap +: 32] = rf32(0); end
                tick; y_v = 0; u_v = 0; idle;
                gap = $urandom % 3; repeat (gap) begin tick; idle; end
            end
            // tightest legal spacing: next command once the ref leaf has sent the last fragment
            while (!u_ref.run) begin tick; idle; end
            while (u_ref.run) begin tick; idle; end
            gap = $urandom % 5; repeat (gap) begin tick; idle; end
        end
        repeat (60) begin tick; idle; end
        $display("VQEQ vectors=%0d fragments=%0d starts=%0d mismatches=%0d fault ref=%b new=%b", NVEC, frags, starts, mism, rf, nf);
        if (mism != 0 || rf || nf || frags == 0) begin $display("FAIL vq pin-register equivalence"); $finish; end
        // collision phase: y_v && u_v
        chk = 0; y_v = 1; u_v = 1; y_i = 0; u_i = 0; tick; y_v = 0; u_v = 0; repeat (8) tick;
        $display("VQCOL y&u fault ref@%0d new@%0d", rf_at, nf_at);
        if (rf_at < 0 || nf_at < 0 || nf_at != rf_at) begin $display("FAIL collision"); $finish; end
        $display("PASS vq pin-register equivalence (xf and fault identical every edge)");
        $finish;
    end
endmodule
