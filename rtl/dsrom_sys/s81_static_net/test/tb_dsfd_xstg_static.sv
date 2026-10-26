`timescale 1ns/1ps
// tb_dsfd_xstg_static: production bench of dsfd_xstg_515 (--hend-static): end block (cw) -> band block (ck), same
// frequency, PHASE ps static skew, marker after TRUNK edges.  Every ck edge after the epoch must deliver the next source
// word (bubbles included) on ONE fixed edge offset, o = {data, valid, live}; the offset must equal the expected constant.
module tb_dsfd_xstg_static;
    parameter integer PHASE = 2, TRUNK = 5;
    reg cw = 0, ck = 0, marker = 0;
    always #5 cw = ~cw; initial begin #(PHASE); forever #5 ck = ~ck; end
    reg [512:0] data = 0; reg v = 0;
    wire [514:0] o;
    `DUT dut (.ck(ck), .cw(cw), .i({data, v, marker}), .o(o));
    integer cyc = 0, first = -1, expected = 0, seen = 0, j;
    reg [513:0] gold [0:4095];
    function automatic [513:0] word(input integer n);
        integer k; begin for (k = 0; k < 514; k = k + 1) word[k] = ((n * 1103515245 + 12345) >> (k % 29)) ^ (k / 29) ^ (n >> (k % 5)); word[0] = n[0] | n[1]; end
    endfunction
    always @(negedge cw) begin {data, v} = word(cyc); gold[cyc] = word(cyc); cyc = cyc + 1; end
    always @(posedge ck) begin
        #1;
        if (o[0] === 1'b1 && o[514:1] !== 0) begin
            if (first < 0) begin
                for (j = 0; j < cyc; j = j + 1) if (o[514:1] === gold[j]) first = j;
                if (first < 0) $fatal(1, "XSTG unrecognized first word");
                if (first != TRUNK + 2) $fatal(1, "XSTG wrong first source epoch %0d expected %0d", first, TRUNK + 2);
                expected = first;
            end
            if ($time != 10 * expected + `LAT + PHASE) $fatal(1, "XSTG wrong fixed edge %0t for source %0d", $time, expected);
            if (o[514:1] !== gold[expected]) $fatal(1, "XSTG mismatch source %0d", expected);
            expected = expected + 1; seen = seen + 1;
        end
    end
    initial begin
        #30; repeat (TRUNK) @(negedge cw); #1 marker = 1;
        repeat (300) @(negedge cw); #1;
        if (seen < 280) $fatal(1, "XSTG too few words %0d", seen);
        $display("XSTG_STATIC PASS phase %0d trunk %0d first %0d words %0d", PHASE, TRUNK, first, seen); $finish;
    end
endmodule
