// tb_vm_tiles.sv environment body (included twice: monolithic / joined tiles)
module `VM_ENV_NAME (input wire clk, output reg [63:0] h, output integer nev, output reg done,
                                              output reg fault_end);
    reg [0:0] rst = 1; reg pd_end = 0;
    reg [2047:0] f_su_SW = 0, f_su_NW = 0, f_su_SE = 0, f_su_NE = 0; reg [511:0] iSW = 0, iNW = 0, iSE = 0, iNE = 0;
    wire [2047:0] t_su_SW, t_su_NW, t_su_SE, t_su_NE; wire [581:0] qSW, qNW, qSE, qNE; wire [2067:0] xSW, xNW, xSE, xNE;
    wire [1023:0] t_quant; wire [511:0] t_router;
    `VM_DUT u (.ck(clk), .rst(rst), .*);
    task automatic ack(input [3:0] v, input [767:0] own);
        @(negedge clk); force `VM_CFG = {own, v};     // present across exactly one rising edge
        @(negedge clk); force `VM_CFG = 772'd0;
    endtask
    function automatic [63:0] mix(input [63:0] a, input [63:0] b); mix = {a[62:0], a[63]} ^ b ^ (a >> 7); endfunction
    reg [63:0] lf; function automatic [63:0] nx(input [63:0] x); nx = {x[62:0], x[63] ^ x[62] ^ x[60] ^ x[59]}; endfunction
    integer k, j, g, nw, ri; reg [7:0] wa [0:63]; reg [191:0] wo [0:63]; reg [2062:0] dat; reg [191:0] own; reg [7:0] ba;
    initial begin
        h = 0; nev = 0; done = 0; fault_end = 0; lf = 64'h9e3779b97f4a7c15 ^ `SEED; nw = 0;
        if (`MODE == 1) begin force `VM_CFG = 772'd0; end
        repeat (8) @(posedge clk); #0.1 rst = 0; repeat (40) @(posedge clk);
if (`MODE == 1) begin
        for (k = 0; k < `NOPS && !fault_end; k = k + 1) begin
            lf = nx(lf); lf = nx(lf);
            for (j = 0; j < 33; j = j + 1) begin lf = nx(lf); dat[j*63 +: 63] = lf[62:0]; end
            lf = nx(lf); own = {lf, nx(lf), nx(nx(lf))}; lf = nx(nx(nx(lf)));
            if (`VM_DBG) $display("%m OP k=%0d nw=%0d st=%0d sticky=%0d t=%0t", k, nw, `VM_ROOT.state, `VM_ROOT.sticky, $time);
            if (nw == 0 || (lf[3:0] < 7 && nw < 64)) begin         // write
                ba = lf[15:8]; wa[nw] = ba; wo[nw] = own; nw = nw + 1;
                if (`VM_DBG) $display("%m WR k=%0d ba=%h d=%h", k, ba, dat[63:0]);
                // request fields first, valid 12 cycles later: the monolithic wrapper gives wr_data (f_su_SW, 5 input
                // stages) one stage more than wr_v (f_su_NW, 4), so data launched with valid would be latched stale there
                @(negedge clk); f_su_SW = dat[2047:0]; f_su_NW[14:0] = dat[2062:2048]; f_su_NW[16] = ba[7];
                f_su_NW[23:17] = ba[6:0]; f_su_NW[215:24] = own; f_su_NW[216] = 0;
                repeat (12) @(negedge clk); f_su_NW[15] = 1;
                while (!t_su_SW[1] && !t_su_SW[5]) @(posedge clk);
                if (t_su_SW[5]) begin fault_end = 1; end
                else begin
                    h = mix(h, {8'h57, t_su_SW[201:10]}); nev = nev + 1;
                    g = lf[19:16]; repeat (g) @(posedge clk);
                    @(negedge clk); f_su_NW[15] = 0; f_su_NW[216] = 1;
                    while (t_su_SW[1]) @(posedge clk);
                    @(negedge clk); f_su_NW[216] = 0;
                end
            end else begin                                          // read of a written row
                ri = lf[13:8] % nw; ba = wa[ri]; own = wo[ri];   // a read presents the row's owner
                @(negedge clk); f_su_SE[1] = ba[7]; f_su_SE[8:2] = ba[6:0]; f_su_SE[200:9] = own;
                repeat (12) @(negedge clk); f_su_SE[0] = 1;
                while (t_su_SW[9:6] == 0 && !t_su_SW[5]) @(posedge clk);
                if (t_su_SW[5]) fault_end = 1;
                else begin
                    @(negedge clk); f_su_SE[0] = 0;
                    repeat (40) @(posedge clk);                 // x faces settle; rd_v drop reaches the root
                    if (`VM_DBG) $display("%m RD k=%0d ba=%h own=%h tapown=%h sw=%h nw=%h se=%h ne=%h st=%h", k, ba, own[31:0], t_su_SW[233:202], xSW[63:0], xNW[63:0], xSE[63:0], xNE[63:0], t_su_SW[9:0]);
                    h = mix(h, {8'h52, t_su_SW[969:202]}); h = mix(h, xSW[2062:0]); h = mix(h, xNW[2062:0]);
                    h = mix(h, xSE[2062:0]); h = mix(h, xNE[2062:0]);
                    for (j = 0; j < 33; j = j + 1) begin h = mix(h, xSW[j*63 +: 63]); h = mix(h, xNE[j*63 +: 63]); end
                    nev = nev + 1;
                    ack(4'hF, (k == `KF) ? ~t_su_SW[969:202] : t_su_SW[969:202]);
                    for (g = 0; g < 200 && !(t_su_SW[4] || t_su_SW[5]); g = g + 1) @(posedge clk);
                    if (`VM_DBG) $display("%m RDDONE k=%0d st=%h root=%0d sent=%h acked=%h", k, t_su_SW[9:0], `VM_ROOT.state, `VM_ROOT.sent, `VM_ROOT.acked);
                    repeat (20) @(posedge clk);
                    if (t_su_SW[5]) fault_end = 1;
                end
            end
        end
        repeat (60) @(posedge clk);
        h = mix(h, {t_su_SW[5], t_su_SW[4]}); fault_end = t_su_SW[5];
        done = 1;
        end else begin
        for (k = 0; k < 400; k = k + 1) begin
            @(negedge clk);
            for (j = 0; j < 33; j = j + 1) begin lf = nx(lf); f_su_SW[j*62 +: 62] = lf; lf = nx(lf); f_su_NW[j*62 +: 62] = lf;
                lf = nx(lf); f_su_SE[j*62 +: 62] = lf; lf = nx(lf); f_su_NE[j*62 +: 62] = lf; end
            for (j = 0; j < 8; j = j + 1) begin lf = nx(lf); iSW[j*64 +: 64] = lf; lf = nx(lf); iNW[j*64 +: 64] = lf;
                lf = nx(lf); iSE[j*64 +: 64] = lf; lf = nx(lf); iNE[j*64 +: 64] = lf; end
            if (`MODE == 2) begin f_su_NW[15] = 0; f_su_SE[0] = 0; end   // MODE 3: valids random too
        end
        pd_end = 1; repeat (4) @(posedge clk);
        done = 1;
        end
    end
    // MODE 3 (port depth, coordinator vm_wr_skew_finding.md): random die inputs, valids included; at every edge each field of
    // the root's logical write port (wr_v / bank / addr / owner / data[2062:2048] / data[2047:0]) and read port (rd_v /
    // bank / addr / owner) is matched against the die-pin history at lags 0..15.  A port is ONE-DEPTH iff all its fields
    // share a lag.  Expected: tiles wr 5 / rd 5; the monolithic wrapper wr_data[2047:0] 5 vs wr_v 4 (negative control).
    generate if (`MODE == 3) begin : g_pd
    localparam integer D = 16;
    reg [216:0] hN [0:D-1]; reg [2047:0] hS [0:D-1]; reg [200:0] hE [0:D-1];
    reg [D-1:0] bad [0:9]; integer i, cyc = 0; reg [D-1:0] wr_ok, rd_ok; reg reported = 0;
    initial for (i = 0; i < 10; i = i + 1) bad[i] = 0;
    always @(posedge clk) if (!rst && !reported) begin
        for (i = D - 1; i > 0; i = i - 1) begin hN[i] = hN[i-1]; hS[i] = hS[i-1]; hE[i] = hE[i-1]; end
        hN[0] = f_su_NW[216:0]; hS[0] = f_su_SW; hE[0] = f_su_SE[200:0]; cyc = cyc + 1;
        if (cyc > D + 2 && !pd_end) for (i = 0; i < D; i = i + 1) begin
            if (`VM_RT.wr_v !== hN[i][15]) bad[0][i] = 1'b1;
            if (`VM_RT.wr_bank !== hN[i][16]) bad[1][i] = 1'b1;
            if (`VM_RT.wr_addr !== hN[i][23:17]) bad[2][i] = 1'b1;
            if (`VM_RT.wr_owner !== hN[i][215:24]) bad[3][i] = 1'b1;
            if (`VM_RT.wr_data[2062:2048] !== hN[i][14:0]) bad[4][i] = 1'b1;
            if (`VM_RT.wr_data[2047:0] !== hS[i]) bad[5][i] = 1'b1;
            if (`VM_RT.rd_v !== hE[i][0]) bad[6][i] = 1'b1;
            if (`VM_RT.rd_bank !== hE[i][1]) bad[7][i] = 1'b1;
            if (`VM_RT.rd_addr !== hE[i][8:2]) bad[8][i] = 1'b1;
            if (`VM_RT.rd_owner !== hE[i][200:9]) bad[9][i] = 1'b1;
        end
        if (pd_end) begin
            reported = 1;
            wr_ok = ~(bad[0] | bad[1] | bad[2] | bad[3] | bad[4] | bad[5]); rd_ok = ~(bad[6] | bad[7] | bad[8] | bad[9]);
            $display("VM_PORT_DEPTH %s lag masks (bit L = matches at depth L): wr_v=%b wr_bank=%b wr_addr=%b wr_owner=%b wr_data_hi=%b wr_data_lo=%b rd_v=%b rd_bank=%b rd_addr=%b rd_owner=%b",
                     `VM_TRACE, ~bad[0], ~bad[1], ~bad[2], ~bad[3], ~bad[4], ~bad[5], ~bad[6], ~bad[7], ~bad[8], ~bad[9]);
            $display("VM_PORT_DEPTH %s wr=%s rd=%s", `VM_TRACE, (wr_ok != 0 && $countones(wr_ok) == 1) ? "ONE_DEPTH" : "SKEWED",
                     (rd_ok != 0 && $countones(rd_ok) == 1) ? "ONE_DEPTH" : "SKEWED");
        end
    end
    end endgenerate
    generate if (`MODE == 2) begin : g_tr
    integer fd;
    initial fd = $fopen(`VM_TRACE, "w");
    always @(posedge clk) if (!rst && !done) $fdisplay(fd, "%h %h %h %h %h %h %h %h %h %h %h %h %h %h", t_su_SW, t_su_NW, t_su_SE, t_su_NE,
                                                        qSW, qNW, qSE, qNE, xSW, xNW, xSE, xNE, t_quant, t_router);
    end endgenerate
endmodule
