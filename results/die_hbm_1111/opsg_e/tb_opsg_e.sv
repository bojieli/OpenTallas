// HBM-CORES-B opsbg form E lock-step bench: dut = ot_hgi_su_lgroup2_gp (OT_OPSG_GP+ROT+E); ref = the main module
// (GP+ROT, renamed _ref) fed with sw_v/sw_addr/sw_mask/sw_d delayed ONE edge by the bench (declared EQ_CYCLE_SHIFTED).
// rd and flt compared every cycle; rst_n pulses every 400 cycles so the sticky flt keeps being compared.
`timescale 1ns/1ps
module tb;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg [15:0] rq, rr; reg [383:0] ra;
    reg [7:0] sw_v; reg [119:0] sw_addr; reg [63:0] sw_mask; reg [2047:0] sw_d;
    reg [7:0] d_v; reg [119:0] d_addr; reg [63:0] d_mask; reg [2047:0] d_d;
    wire [511:0] rd_dut, rd_ref; wire flt_dut, flt_ref;
    ot_hgi_su_lgroup2_gp u_dut (.clk(clk), .rst_n(rst_n), .rq(rq), .rr(rr), .ra(ra), .rd(rd_dut),
        .sw_v(sw_v), .sw_addr(sw_addr), .sw_mask(sw_mask), .sw_d(sw_d), .flt(flt_dut));
    ot_hgi_su_lgroup2_gp_ref u_ref (.clk(clk), .rst_n(rst_n), .rq(rq), .rr(rr), .ra(ra), .rd(rd_ref),
        .sw_v(d_v), .sw_addr(d_addr), .sw_mask(d_mask), .sw_d(d_d), .flt(flt_ref));
    always @(posedge clk) begin d_v <= sw_v; d_addr <= sw_addr; d_mask <= sw_mask; d_d <= sw_d; end
    integer nrdnz = 0, cyc = 0, bad = 0, nwr = 0, nrd = 0, nflt = 0, nflt_rise = 0, l, s, w;
    reg flt_q = 0;
    task rnd;
        begin
            for (l = 0; l < 16; l = l + 1) begin
                rr[l] = ($random % 4) == 0;
                rq[l] = rr[l] && (($random % 8) != 0);
                ra[l*24 +: 24] = {9'd0, 11'($unsigned($random) % 4), 4'($random)};
            end
            for (s = 0; s < 8; s = s + 1) begin
                sw_v[s] = ($unsigned($random) % 6) == 0;
                sw_addr[s*15 +: 15] = {11'($unsigned($random) % 4), 4'($random)};
                sw_mask[s*8 +: 8] = $random;
            end
`ifdef QUIET
            // QUIET: legal traffic (one reading lane on its own bank, one writing sector lane; 1 in 300 a second writer),
            // so the sticky flt stays low and its edges (incl. the +1 write-collision term) are compared
            rr = 0; rq = 0; sw_v = 0;
            if ($unsigned($random) % 2 == 0) begin l = $unsigned($random) % 16; rr[l] = 1'b1; rq[l] = 1'b1; ra[l*24 +: 4] = 4'(l); end
            if ($unsigned($random) % 3 == 0) sw_v[$unsigned($random) % 8] = 1'b1;
            if ($unsigned($random) % 300 == 0) sw_v[$unsigned($random) % 8] = 1'b1;
`endif
            for (w = 0; w < 64; w = w + 1) sw_d[w*32 +: 32] = $random;
        end
    endtask
    initial begin
        rq = 0; rr = 0; ra = 0; sw_v = 0; sw_addr = 0; sw_mask = 0; sw_d = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        while (cyc < 60000) begin
            @(negedge clk);
            if (cyc > 8 && (rd_dut !== rd_ref || flt_dut !== flt_ref)) begin
                bad = bad + 1;
                if (bad <= 5) $display("MISMATCH cyc %0d rd %0d flt %0d/%0d", cyc, rd_dut !== rd_ref, flt_dut, flt_ref);
            end
            if (rd_ref != 0) nrdnz = nrdnz + 1;
            if (flt_ref) nflt = nflt + 1;
            if (flt_ref && !flt_q) nflt_rise = nflt_rise + 1;
            flt_q = flt_ref;
            nwr = nwr + $countones(sw_v); nrd = nrd + $countones(rq);
            rnd;
            rst_n = (cyc % 400) != 399;
            cyc = cyc + 1;
        end
        $display("DONE rd_nonzero_cycles %0d cycles %0d mismatches %0d writes %0d reads %0d flt_cycles %0d flt_rises %0d", nrdnz, cyc, bad, nwr, nrd, nflt, nflt_rise);
        $finish;
    end
endmodule
