`timescale 1ns/1ps
// Exact gate of ot_s81_cfg7_seq_bfp (S-BIND 2026-10-15): seven ot_rom_4096x72_m8 functional models hold, per phase,
// the 25 configuration words in rd_out[47:0] and the phase's 82-bit programme descriptor in the spare columns
// rd_out[71:48] of rows 0..3.  Lockstep vs the reference pair (ot_s81_cfg7_seq_bf fed the same macros + ot_s81_bf_prog_seq
// fed the descriptor TABLE directly): cfg, go_e, st and f_prog must be identical on every edge over NPH random
// broadcast / go phases (random descriptors, every programme finishes before the next go).  Negative control:
// +define+OT_S81_CFG7_BFP_MUT_ROW (descriptor rows captured one row late) must FAIL.
module tb_ot_s81_cfg7_seq_bfp;
    localparam integer PHW = 10, CW = 25, NW = CW << PHW, NPH = 160;
    reg clk = 0;
    always #0.416667 clk = ~clk;
    reg rst_n = 0, cfg_go = 0, go = 0;
    reg [PHW-1:0] phase = 0;
    reg [2:0] np = 0;
    reg [81:0] dtab [0:(1<<PHW)-1];
    reg [71:0] mem [0:6][0:4095];
    integer g, p, k, cyc = 0, nissue = 0, ngo = 0;
    reg [31:0] rng = 32'h5eed1015;
    function automatic [31:0] nx(input [31:0] r); nx = {r[30:0], r[31] ^ r[21] ^ r[1] ^ r[0]}; endfunction
    initial begin
        for (p = 0; p < (1 << PHW); p = p + 1) begin
            reg [81:0] d; reg [13:0] n; reg [7:0] per, off;
            rng = nx(rng); n = 14'(rng % 24); rng = nx(rng); per = 8'(2 + rng % 6); rng = nx(rng); off = 8'(1 + rng % 9);
            rng = nx(rng);
            d = 82'd0;
            d[13:0] = n; d[14] = rng[0]; d[22:15] = off; d[30:23] = per; d[44:31] = 14'(rng[15:2]); d[58:45] = 14'h7f;
            d[59] = rng[16]; d[61:60] = 2'(rng[18:17] % 2); d[68:66] = 3'(rng[21:19] % 3); d[71:69] = 3'd7; d[75:72] = rng[0] ? 4'hf : 4'h7;
            dtab[p] = d;
        end
        for (g = 0; g < NW; g = g + 1) begin
            reg [71:0] w; reg [23:0] sp;
            p = g / CW; k = g % CW;
            w[47:0] = {16'(g ^ 16'hb51d), 16'(g * 37 + 19), 16'(g * 73 + 7)};
            if (k >= 8 && k < 16) w[0] = 1'b1;                       // every phase active (go_e follows go)
            sp = (k < 4) ? 24'({14'd0, dtab[p]} >> (24 * k)) : 24'(g * 131 + 5);   // other rows: unrelated spare bits
            w[71:48] = sp;
            mem[g / 4096][g % 4096] = w;
        end
    end
    wire [11:0] a, ra;
    wire [6:0] ce, rce;
    reg  [71:0] q [0:6], rq [0:6];
    integer m;
    // synchronous macro read models (ot_rom_4096x72_m8 timing: rd_out = word at the edge ce is sampled)
    always @(posedge clk) for (m = 0; m < 7; m = m + 1) begin if (ce[m]) q[m] <= mem[m][a]; if (rce[m]) rq[m] <= mem[m][ra]; end
    wire [53:0] cfg, rcfg; wire ge, rge; wire [1:0] st, rst_; wire [37:0] fp, rfp;
    ot_s81_cfg7_seq_bfp dut (.clk(clk), .rst_n(rst_n), .lc({np, phase, cfg_go, go}), .a(a),
        .ce0(ce[0]), .ce1(ce[1]), .ce2(ce[2]), .ce3(ce[3]), .ce4(ce[4]), .ce5(ce[5]), .ce6(ce[6]),
        .q0(q[0]), .q1(q[1]), .q2(q[2]), .q3(q[3]), .q4(q[4]), .q5(q[5]), .q6(q[6]), .cfg(cfg), .go_e(ge), .st(st), .f_prog(fp));
    ot_s81_cfg7_seq_bf ref_ld (.clk(clk), .rst_n(rst_n), .lc({np, phase, cfg_go, go}), .a(ra),
        .ce0(rce[0]), .ce1(rce[1]), .ce2(rce[2]), .ce3(rce[3]), .ce4(rce[4]), .ce5(rce[5]), .ce6(rce[6]),
        .q0(rq[0][47:0]), .q1(rq[1][47:0]), .q2(rq[2][47:0]), .q3(rq[3][47:0]), .q4(rq[4][47:0]), .q5(rq[5][47:0]), .q6(rq[6][47:0]),
        .cfg(rcfg), .go_e(rge), .st(rst_));
    reg [PHW-1:0] cur = 0;
    wire rpf;
    ot_s81_bf_prog_seq ref_prog (.ck(clk), .rst_n(rst_n), .go(rge), .desc(dtab[cur]), .f_prog(rfp), .fault(rpf));
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if ({cfg, ge, st, fp} !== {rcfg, rge, {rst_[1] | rpf, rst_[0]}, rfp})
            $fatal(1, "BFP MISMATCH cyc=%0d phase=%0d fp=%h ref=%h cfg=%h ref=%h", cyc, cur, fp, rfp, cfg, rcfg);
        if (fp[0]) nissue <= nissue + 1;
        if (st[1]) $fatal(1, "BFP unexpected fault cyc=%0d", cyc);
    end
    integer ph_i, w8;
    initial begin
        repeat (5) @(posedge clk); #0.1 rst_n = 1;
        for (ph_i = 0; ph_i < NPH; ph_i = ph_i + 1) begin
            rng = nx(rng);
            @(negedge clk); phase = PHW'(rng % (1 << PHW)); np = 3'(rng[13:11]); cfg_go = 1;
            @(negedge clk); cfg_go = 0;
            repeat (40) @(negedge clk);
            cur = phase; go = 1; ngo = ngo + 1;
            @(negedge clk); go = 0;
            repeat (24 * 8 + 30) @(negedge clk);
        end
        $display("PASS ot_s81_cfg7_seq_bfp lockstep phases=%0d issues=%0d cycles=%0d", ngo, nissue, cyc);
        $finish;
    end
endmodule
