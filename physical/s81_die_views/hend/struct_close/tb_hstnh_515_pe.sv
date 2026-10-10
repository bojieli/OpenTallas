`timescale 1ns/1ps
// struct-close 2026-10-09: dsfd_hstnh_515 posedge station vs the glue master's function (ot_fwd_link_stage on fck = ~ck,
// negedge capture = posedge ck): random di for 2,000 cycles, dq must equal di of the previous rising edge on every bit.
module tb_hstnh_515_pe;
    parameter integer MUT = 0;
    reg ck = 0; always #1 ck = ~ck;
    reg [514:0] di = 0; wire [514:0] dq; reg [514:0] prev; integer c, bad = 0, s = 7, k;
    dsfd_hstnh_515 #(.MUT(MUT)) dut (.ck(ck), .di(di), .dq(dq));
    initial begin
        @(posedge ck); #0.5 for (k = 0; k < 515; k = k + 32) di[k +: 32] = $random(s);
        for (c = 0; c < 2000; c = c + 1) begin
            @(posedge ck); prev = di; #0.5;
            if (dq !== prev) bad = bad + 1;
            for (k = 0; k < 515; k = k + 32) di[k +: 32] = $random(s);
            #0.2 if (dq !== prev) bad = bad + 1;   // stable until the next edge
        end
        if (bad == 0) $display("HSTNH_PE PASS cycles=2000"); else $display("HSTNH_PE FAIL mismatches=%0d", bad);
        $finish;
    end
endmodule
