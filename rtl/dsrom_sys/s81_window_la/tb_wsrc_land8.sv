`timescale 1ns/1ps
// Leaf bench for ot_dsrom_wsrc_land8 (el1011-ds-misc 2026-10-11): random accepted beats on 8 lanes (tags spanning the
// 2,176-sector region and beyond, scale sectors, poison codes / scales planted) against a behavioural model of the
// stream engine's landing checks (s = {tag,00} + beat; range s >= 2176; scale sector s mod 17 == 16 -> poison =
// any of bytes 0..15 == ff, else any byte[6:0] == 7f).  bad must equal the OR of the lanes' bad beats 7 edges after
// the beat is presented, nb the popcount of the valids 6 edges after.  Mutant: +define+OT_LAND8_MUTANT.
module tb_wsrc_land8;
    localparam integer NL = 8, TAGW = 13, BEATW = 4, NSECT = 2176;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    reg [NL-1:0] v = 0; reg [NL*TAGW-1:0] tag = 0; reg [NL*BEATW-1:0] beat = 0; reg [NL*256-1:0] data = 0;
    wire bad; wire [3:0] nb; wire sim_bad;
    ot_dsrom_wsrc_land8 dut (.clk(clk), .rst_n(rst_n), .b(30'd0), .acc_v(v), .acc_tag(tag), .acc_beat(beat),
        .acc_data(data), .bad(bad), .nb(nb), .sim_bad(sim_bad));
    reg exp_bad [0:8191]; reg [3:0] exp_nb [0:8191];
    integer cyc, l, z, errors = 0, nbad = 0, nk16 = 0, n = 0, checked = 0;
    reg [31:0] rng = 32'h1d872b41;
    reg [11:0] s; reg lb, pc, ps, ob; reg [3:0] cnt; reg [255:0] d;
    task step_rng; begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5); end endtask
    initial begin
        repeat (3) @(posedge clk);
        @(negedge clk) rst_n = 1;
        for (cyc = 0; cyc < 3000; cyc = cyc + 1) begin
            @(negedge clk);
            for (l = 0; l < NL; l = l + 1) begin
                step_rng; v[l] = rng[0] | rng[1];
                step_rng; tag[l*TAGW +: TAGW] = (rng[5:3] != 0) ? (rng[12:0] % 544) : (rng[12:0] % 600);
                step_rng; beat[l*BEATW +: BEATW] = rng[3:0];
                for (z = 0; z < 8; z = z + 1) begin step_rng; d[32*z +: 32] = rng & 32'hfefefefe; end
                step_rng; if (rng[4:0] == 0) d[8*(rng[9:5]) +: 7] = 7'h7f;          // plant a poisoned code
                step_rng; if (rng[2:0] == 0) d[8*(rng[6:3]) +: 8] = 8'hff;          // plant a poisoned scale
                data[l*256 +: 256] = d;
            end
        end
        @(negedge clk); v = 0;
        repeat (12) @(posedge clk);
        if (errors == 0 && checked > 2900 && nbad > 100 && nk16 > 100)
            $display("PASS LAND8 checked=%0d bad_cycles=%0d scale_sectors=%0d", checked, nbad, nk16);
        else $fatal(1, "LAND8 errors=%0d checked=%0d bad_cycles=%0d scale_sectors=%0d", errors, checked, nbad, nk16);
        $finish;
    end
    // expectation of the inputs sampled at edge n: nb after edge n+5, bad after edge n+6
    always @(posedge clk) if (rst_n) begin
        ob = 0; cnt = 0;
        for (l = 0; l < NL; l = l + 1) begin
            s = {tag[l*TAGW +: TAGW], 2'b00} + beat[l*BEATW +: BEATW];
            pc = 0; ps = 0;
            for (z = 0; z < 32; z = z + 1) if (data[l*256 + 8*z +: 7] == 7'h7f) pc = 1;
            for (z = 0; z < 16; z = z + 1) if (data[l*256 + 8*z +: 8] == 8'hff) ps = 1;
            lb = v[l] && (s >= NSECT || ((s % 17) == 16 ? ps : pc));
            if (v[l] && s < NSECT && (s % 17) == 16) nk16 = nk16 + 1;
            ob = ob | lb; cnt = cnt + v[l];
        end
        exp_bad[n] = ob; exp_nb[n] = cnt; if (ob) nbad = nbad + 1;
        #1;
        if (n >= 6) begin
            checked = checked + 1;
            if (bad !== exp_bad[n - 6]) begin
                errors = errors + 1;
                if (errors < 5) $display("LAND8_BAD_MISMATCH edge=%0d got=%b exp=%b", n - 6, bad, exp_bad[n - 6]);
            end
            if (nb !== exp_nb[n - 5]) begin
                errors = errors + 1;
                if (errors < 5) $display("LAND8_NB_MISMATCH edge=%0d got=%0d exp=%0d", n - 5, nb, exp_nb[n - 5]);
            end
        end
        n = n + 1;
    end
endmodule
