`timescale 1ns/1ps
// tb_dsfd_hend_static: production bench of a generated S81 hub end / start block in the --hend-static form.
// Time base: 1 ns = one VCO tick of a 12-tick hyperperiod: stream period 12, serial period 16 (3:4, one PLL).
//   -DM2L  NL lanes of PW b (+v +marker unless RAW) on forwarded clocks fi<j> (stream, lane phase PH+5j) -> ck stream
//   -DR2L  one lane, forwarded stream fi0 -> ck serial (4:3): source phase 3 is a compiled bubble
//   -DL2R  i on ck (serial with RATIO, else stream) -> od on cks stream (3:4: one stream phase in four is a bubble)
// Every output edge after the epoch must carry exactly the next scheduled word of its lane (no skip / duplicate /
// hold), {fault, live} = {0, 1}, and the first word's latency (ticks from its source launch edge) must equal LAT
// (the compiled constant) when LAT >= 0.  `DUT = master; port lists by define.
module tb_dsfd_hend_static;
    parameter integer NL = 1, PW = 8, PH = 0, LAT = -1, REL = 4;
`ifdef M2L
    localparam integer PO = 12, PI = 12;
`elsif R2L
    localparam integer PO = 16, PI = 12;
`else
`ifdef RATIO
    localparam integer PO = 12, PI = 16;
`else
    localparam integer PO = 12, PI = 12;
`endif
`endif
    reg ck = 0, cks = 0; reg [NL-1:0] fi = 0; reg rs = 0, rss = 0;
    integer t = 0; always #0.5 t = t + 0;
    // clocks: ck period PO (ends) / PI (starts), lanes period PI with phase
    initial forever begin #1 t = t + 1; end
    always @(t) begin
`ifdef L2R
        ck <= ((t + 3) % PI) < PI / 2; cks <= (t % PO) < PO / 2;
`else
        ck <= (t % PO) < PO / 2;
`endif
    end
    genvar g;
    for (g = 0; g < NL; g = g + 1) begin : g_fi
        always @(t) fi[g] <= ((t + PH + 5 * g) % PI) < PI / 2;
    end
    function automatic [PW-1:0] word(input integer lane, input integer k);
        reg [PW+63:0] x; integer s; begin s = lane * 7919 + k * 104729 + 17; x = {$random(s), $random(s), $random(s)}; word = (PW < 16) ? PW'(k * 5 + lane + 1) : (x[PW-1:0] | 1); end
    endfunction
    function automatic bubble(input integer k);
`ifdef R2L
        bubble = (k % 4) == 3;
`else
        bubble = 0;
`endif
    endfunction
`ifdef L2R
    reg [PW:0] i = 0; wire [PW+1:0] od; wire fo;
`ifdef HAS_ST
    wire [2:0] st;
    `DUT dut (.ck(ck), .cks(cks), .fo(fo), .i(i), .od(od), .rs(rs), .rss(rss), .st(st));
`else
    `DUT dut (.ck(ck), .cks(cks), .fo(fo), .i(i), .od(od), .rs(rs), .rss(rss));
`endif
    integer k = 0; integer lt [0:8191];
    always @(posedge ck) begin #2; if (rs && rss) begin i = {word(0, k), 1'b1}; lt[k] = t + (PI - 2); k = k + 1; end else i = 0; end
`else
`ifdef RAW
    localparam integer DW = PW;
`else
    localparam integer DW = PW + 2;
`endif
    reg [NL*DW-1:0] di = 0;
    wire [NL*(PW+1)+1:0] o;
    `DUT dut (.ck(ck), .o(o), .rs(rs) `PORTS );
    integer kk [0:NL-1]; integer lt [0:NL-1][0:4095]; integer nf [0:NL-1];
    for (g = 0; g < NL; g = g + 1) begin : g_src
        initial begin kk[g] = 0; nf[g] = 0; end
        always @(posedge fi[g]) begin
            #2;
            nf[g] = nf[g] + 1;
`ifdef RAW
            if (rs) begin di[g*DW +: DW] = word(g, kk[g]); lt[g][kk[g]] = t + PI - 2; kk[g] = kk[g] + 1; end
`else
            if (nf[g] > REL) begin
                di[g*DW +: DW] = bubble(kk[g]) ? {{PW{1'b0}}, 1'b0, 1'b1} : {word(g, kk[g]), 1'b1, 1'b1};
                lt[g][kk[g]] = t + PI - 2; kk[g] = kk[g] + 1;
            end else di[g*DW +: DW] = 0;
`endif
        end
    end
`endif
    // checker
    integer exp_k [0:NL-1]; integer started [0:NL-1]; integer bad = 0, seen = 0, j, q, lat0 = -999;
    initial for (j = 0; j < NL; j = j + 1) begin exp_k[j] = -1; started[j] = 0; end
`ifdef L2R
    integer bub = 0, oute = 0;
    always @(posedge cks) begin
        #1;
        if (od[0] === 1'b1) begin
            oute = oute + 1;
            if (od[1] === 1'b1) begin
                if (exp_k[0] < 0) begin
                    for (q = 0; q < k; q = q + 1) if (od[PW+1:2] === word(0, q) && (k - q) < 40) exp_k[0] = q;
                    if (exp_k[0] < 0) begin bad = bad + 1; $display("HEND first word unrecognized"); end
                    else begin lat0 = t - lt[exp_k[0]]; if (LAT >= 0 && lat0 != LAT) begin bad = bad + 1; $display("HEND latency %0d want %0d", lat0, LAT); end end
                end else if (od[PW+1:2] !== word(0, exp_k[0])) begin bad = bad + 1; if (bad < 5) $display("HEND mismatch word %0d", exp_k[0]); end
                exp_k[0] = exp_k[0] + 1; seen = seen + 1;
            end else if (exp_k[0] >= 0) bub = bub + 1;
        end
    end
`else
    always @(posedge ck) begin
        #1;
        if (o[NL*(PW+1)] === 1'b1) begin
            if (o[NL*(PW+1)+1] !== 1'b0) begin bad = bad + 1; if (bad < 5) $display("HEND fault"); end
            for (j = 0; j < NL; j = j + 1) begin
                if (o[j*(PW+1)] === 1'b1) begin
                    if (exp_k[j] < 0) begin
                        for (q = 0; q < kk[j]; q = q + 1) if (o[j*(PW+1)+1 +: PW] === word(j, q) && (kk[j] - q) < 40) exp_k[j] = q;
                        if (exp_k[j] < 0) begin bad = bad + 1; $display("HEND lane %0d first word unrecognized", j); end
                        else if (j == 0) begin lat0 = t - lt[0][exp_k[0]]; if (LAT >= 0 && lat0 != LAT) begin bad = bad + 1; $display("HEND latency %0d want %0d", lat0, LAT); end end
                    end else if (o[j*(PW+1)+1 +: PW] !== word(j, exp_k[j])) begin bad = bad + 1; if (bad < 5) $display("HEND lane %0d mismatch word %0d", j, exp_k[j]); end
                    exp_k[j] = exp_k[j] + 1; if (bubble(exp_k[j])) exp_k[j] = exp_k[j] + 1; seen = seen + 1; started[j] = 1;
                end else if (started[j]) begin bad = bad + 1; if (bad < 5) $display("HEND lane %0d hole after start", j); end
            end
        end
    end
`endif
    initial begin
        #30 rs = 1; #20 rss = 1;
        #4000;
`ifdef L2R
`ifdef RATIO
        if (bub * 4 < oute - 8 || bub * 4 > oute + 8) begin bad = bad + 1; $display("HEND bubble pattern %0d of %0d", bub, oute); end
`else
        if (bub != 0) begin bad = bad + 1; $display("HEND unexpected bubbles %0d", bub); end
`endif
`endif
        if (seen < 150 * NL) begin bad = bad + 1; $display("HEND too few words %0d", seen); end
        if (bad) begin $display("HEND_STATIC FAIL %0d", bad); $fatal(1); end
        $display("HEND_STATIC PASS %0d words exact, first-word latency %0d ticks (phase %0d)", seen, lat0, PH);
        $finish;
    end
endmodule
