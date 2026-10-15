`timescale 1ns/1ps
// tb_dsfd_status_static: a 2-bit status lane end to end in the --hend-static form: start dsfd_l2r_vs<F>_1x1 (written on
// the stream clock) -> forwarded {od, fo} -> end dsfd_m2l_vs<F>_1x1 (stream ck).  Input {avail|done, fault} levels
// change at random edges (held >= 2 edges); the end's o must reproduce every input state with ONE fixed edge delay D
// (measured at the first change, then checked on every edge), xf folds all live / no fault.  +MUT: none here; the
// offset mutant is applied to the end master text by the gate script.
module tb_dsfd_status_static;
    parameter integer F = 0, NXS = 4, NXE = 2;
    reg ck = 0; always #6 ck = ~ck;
    reg rs = 0;
    reg [1:0] i = 0;
    wire [2*NXS-1:0] xs = {NXS{2'b01}};
    wire [2*NXE-1:0] xe = {NXE{2'b01}};
    wire fo; wire [2:0] od; wire [1:0] o;
    `DUT_S us (.ck(ck), .cks(ck), .fo(fo), .i(i), .od(od), .rs(rs), .rss(rs), .xf(xs));
    `DUT_E ue (.ck(ck), .o(o), .rs(rs), .xf(xe), .di0(od), .fi0(fo));
    reg [1:0] hist [0:4095]; integer n = 0, D = -1, bad = 0, chk = 0, seed = 11, hold = 0, k;
    // expected end output for input state s: o[F] = fault, o[1-F] = avail & !fault (fault wins the shared payload)
    function automatic [1:0] expo(input [1:0] s);
        reg flt, av; begin flt = s[F]; av = s[1-F] & !flt; expo = 2'b00; expo[F] = flt; expo[1-F] = av; end
    endfunction
    always @(posedge ck) begin
        #1;
        if (rs) begin
            hist[n] = i;
            if (D < 0 && n > 40 && o !== 2'b00) begin
                for (k = n; k >= 0; k = k - 1) if (expo(hist[k]) === o && (k == 0 || expo(hist[k-1]) !== o)) begin D = n - k; k = -1; end
            end else if (D >= 0) begin
                if (o !== expo(hist[n - D])) begin bad = bad + 1; if (bad < 5) $display("STATUS mismatch edge %0d o %b want %b", n, o, expo(hist[n-D])); end
                chk = chk + 1;
            end
            n = n + 1;
            if (n > 40) begin
                if (hold == 0) begin i = $random(seed); if (i[F]) i[1-F] = 0; hold = 2 + ($random(seed) & 3); end
                hold = hold - 1;
            end
        end
    end
    initial begin
        #30 rs = 1;
        #(12 * 1200);
        if (D < 0 || chk < 800) begin $display("STATUS FAIL no fixed delay (D %0d, %0d checked)", D, chk); $fatal(1); end
        if (bad) begin $display("STATUS FAIL %0d", bad); $fatal(1); end
        $display("STATUS_STATIC PASS %0d edges exact, fixed delay %0d edges", chk, D);
        $finish;
    end
endmodule
