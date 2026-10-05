`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Directed bench: two hyper-connection projection ops (ot_hdc_v41_hcproj) issued with a gap of 0 .. 40
// cycles after the first is accepted (back to back: the op-major MTP verify pass issues one HE op per slot).
// Each op's results must land at its own obase and equal the same op run alone.  Reference: op A alone,
// then op B alone (spaced by an idle unit).  Prints one line per gap and PASS/FAIL.
// ---------------------------------------------------------------------------
module tb_hdc_v41_hcproj_b2b;
    localparam integer NL = 3, IL = 8, S = 8, AW = 24, NW = 16, K = 4, TMO = 4000;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg go = 0;
    reg [NW-1:0] i_nout = 24, i_k = K;
    reg [AW-1:0] i_wbase = 0, i_xbase = 0, i_obase = 0;
    wire ready, idle, hr_re, fault;
    wire [AW-1:0] hr_addr;
    reg  [S*NL*32-1:0] hr_q;
    wire [S-1:0] x_re;
    wire [S*AW-1:0] x_addr;
    reg  [S*32-1:0] x_q;
    wire [0:0] o_we;
    wire [AW-1:0] o_addr;
    wire [31:0] o_mask;
    wire [1023:0] o_data;
    ot_hdc_v41_hcproj #(.NL(NL), .IL(IL), .S(S), .AW(AW), .NW(NW), .MP(1)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle), .i_nout(i_nout), .i_k(i_k),
        .i_wbase(i_wbase), .i_xbase(i_xbase), .i_obase(i_obase), .i_m(3'd0), .i_xps(24'd0), .i_ops(24'd0),
        .hr_re(hr_re), .hr_addr(hr_addr), .hr_q(hr_q), .x_re(x_re), .x_addr(x_addr), .x_q(x_q),
        .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data), .fault(fault));
    // weight ROM and vector memory: small normal binary32 values
    reg [S*NL*32-1:0] wrom [0:255];
    reg [31:0] xmem [0:1023];
    reg [31:0] omem [0:1023];
    integer i, c, q;
    function automatic [31:0] val(input integer s);
        val = {s[0], 8'd120 + 8'(s % 7), 23'(s * 2654435761)};
    endfunction
    initial begin
        for (i = 0; i < 256; i = i + 1) for (c = 0; c < S*NL; c = c + 1) wrom[i][32*c +: 32] = val(i * 97 + c);
        for (i = 0; i < 1024; i = i + 1) xmem[i] = val(i * 31 + 5);
    end
    always @(posedge clk) begin
        if (hr_re) hr_q <= wrom[hr_addr[7:0]];
        for (c = 0; c < S; c = c + 1) if (x_re[c]) x_q[32*c +: 32] <= xmem[x_addr[c*AW +: 10]];
        if (o_we[0]) for (q = 0; q < 32; q = q + 1) if (o_mask[q]) omem[o_addr[9:0] + q] <= o_data[32*q +: 32];
    end
    task automatic issue(input [AW-1:0] wb, input [AW-1:0] xb, input [AW-1:0] ob);
        reg acc;
        begin
            go = 1'b1; i_wbase = wb; i_xbase = xb; i_obase = ob; acc = 1'b0;
            while (!acc) begin acc = ready; @(posedge clk); #0.25; end
            go = 1'b0;
        end
    endtask
    task automatic drain;
        integer t;
        begin t = 0; while (!(idle && !go) && t < TMO) begin @(posedge clk); #0.25; t = t + 1; end
              repeat (4) begin @(posedge clk); #0.25; end end
    endtask
    reg [31:0] refm [0:1023];
    integer gap, g, nbad, nfail;
    initial begin
        nfail = 0;
        repeat (3) @(posedge clk); #0.25 rst_n = 1;
        for (i = 0; i < 1024; i = i + 1) omem[i] = 32'hDEADBEEF;
        issue(0, 0, 100); drain; issue(64, 32, 200); drain;
        for (i = 0; i < 1024; i = i + 1) refm[i] = omem[i];
        for (gap = 0; gap <= 40; gap = gap + 1) begin
            for (i = 0; i < 1024; i = i + 1) omem[i] = 32'hDEADBEEF;
            issue(0, 0, 100);
            for (g = 0; g < gap; g = g + 1) begin @(posedge clk); #0.25; end
            issue(64, 32, 200); drain;
            nbad = 0;
            for (i = 0; i < 1024; i = i + 1) if (omem[i] !== refm[i]) nbad = nbad + 1;
            if (nbad != 0) nfail = nfail + 1;
            $display("gap=%0d %s bad_words=%0d", gap, (nbad == 0) ? "ok" : "BAD", nbad);
        end
        $display("%s cases=41 fail=%0d", (nfail == 0) ? "PASS" : "FAIL", nfail);
        $finish;
    end
endmodule
