`timescale 1ns/1ps
// Leaf bench for ot_dsrom_wsrc_mirror (el1011-ds-misc 2026-10-11): random write commands (tag / user write, mv set /
// clear, slot = row[6:0]) interleaved with four bank reads per cycle (bank b reads a row with row[1:0] == b, half of
// them recently written rows of a small user set) against a behavioural 128-entry mirror: a write sampled at edge n
// is applied at edge n+1; a read sampled at edge n sees every command sampled before edge n and reports bad = use && (!mv || tag != row || user != j_user) after edge n+3.  Mutant: +define+OT_MIRROR_MUTANT.
module tb_wsrc_mirror;
    localparam integer POS_W = 21, USER_W = 10;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    reg wr_tag = 0, wr_set = 0, wr_clr = 0; reg [6:0] wr_slot = 0; reg [POS_W-1:0] wr_row = 0; reg [USER_W-1:0] wr_user = 0;
    reg [4*POS_W-1:0] rd_row = 0; reg [3:0] rd_use = 0; reg [USER_W-1:0] j_user = 0;
    wire [3:0] bad;
    ot_dsrom_wsrc_mirror dut (.clk(clk), .rst_n(rst_n), .wr_tag(wr_tag), .wr_set(wr_set), .wr_clr(wr_clr),
        .wr_slot(wr_slot), .wr_row(wr_row), .wr_user(wr_user), .rd_row(rd_row), .rd_use(rd_use), .j_user(j_user), .bad(bad));
    reg [POS_W-1:0] mt [0:127]; reg [USER_W-1:0] mu [0:127]; reg [127:0] mvv;
    reg [POS_W-1:0] hist [0:15];
    reg p_tag, p_set, p_clr; reg [6:0] p_slot; reg [POS_W-1:0] p_row; reg [USER_W-1:0] p_user;
    reg [3:0] exp [0:8191];
    integer cyc, b, n = 0, errors = 0, checked = 0, nbad = 0, ngood = 0, k;
    reg [31:0] rng = 32'h6b8b4567;
    reg [POS_W-1:0] r; reg [3:0] e;
    task step_rng; begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5); end endtask
    initial begin
        for (k = 0; k < 16; k = k + 1) hist[k] = k;
        repeat (3) @(posedge clk);
        @(negedge clk) rst_n = 1;
        for (cyc = 0; cyc < 128; cyc = cyc + 1) begin             // fill: the leaf's table has no reset
            @(negedge clk);
            wr_tag = 1; wr_set = 0; wr_clr = 1; wr_row = cyc; wr_slot = cyc; wr_user = 0; rd_use = 0;
        end
        for (cyc = 0; cyc < 4000; cyc = cyc + 1) begin
            @(negedge clk);
            step_rng;
            wr_tag = rng[0] & rng[1]; wr_set = rng[2] | rng[3]; wr_clr = rng[4] & rng[5];
            step_rng; wr_row = {rng[13:0], 7'd0} | rng[20:14]; wr_row[20:17] = 0; wr_slot = wr_row[6:0];
            step_rng; wr_user = rng[0];
            if (wr_tag) begin hist[rng[7:4]] = wr_row; end
            step_rng; j_user = rng[0];
            for (b = 0; b < 4; b = b + 1) begin
                step_rng;
                r = (rng[0] | rng[27]) ? hist[rng[4:1]] : {4'd0, rng[20:4]};
                r = r + (b - r[1:0]) % 4;
                r[1:0] = b;
                rd_row[b*POS_W +: POS_W] = r; rd_use[b] = rng[25] | rng[26];
            end
        end
        @(negedge clk); wr_tag = 0; wr_set = 0; wr_clr = 0; rd_use = 0;
        repeat (8) @(posedge clk);
        if (errors == 0 && checked > 4000 && nbad > 500 && ngood > 300)
            $display("PASS MIRROR checked=%0d bad_reads=%0d good_reads=%0d", checked, nbad, ngood);
        else $fatal(1, "MIRROR errors=%0d checked=%0d bad_reads=%0d good_reads=%0d", errors, checked, nbad, ngood);
        $finish;
    end
    always @(posedge clk) if (!rst_n) begin mvv = 0; p_tag = 0; p_set = 0; p_clr = 0; end
    else begin
        // apply the command sampled at the previous edge, then latch this edge's command
        if (p_tag) begin mt[p_slot] = p_row; mu[p_slot] = p_user; end
        if (p_set) mvv[p_slot] = 1'b1; else if (p_clr) mvv[p_slot] = 1'b0;
        p_tag = wr_tag; p_set = wr_set; p_clr = wr_clr; p_slot = wr_slot; p_row = wr_row; p_user = wr_user;
        // reads sampled now see every command sampled at earlier edges
        e = 0;
        for (b = 0; b < 4; b = b + 1) begin
            r = rd_row[b*POS_W +: POS_W];
            e[b] = rd_use[b] && (!mvv[r[6:0]] || mt[r[6:0]] != r || mu[r[6:0]] != j_user);
            if (rd_use[b]) begin if (e[b]) nbad = nbad + 1; else ngood = ngood + 1; end
        end
        exp[n] = e;
        #1;
        if (n >= 3) begin
            checked = checked + 1;
            if (bad !== exp[n - 3]) begin
                errors = errors + 1;
                if (errors < 5) $display("MIRROR_MISMATCH edge=%0d got=%b exp=%b", n - 3, bad, exp[n - 3]);
            end
        end
        n = n + 1;
    end
endmodule
