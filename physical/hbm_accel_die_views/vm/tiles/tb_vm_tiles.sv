`timescale 1ns/1ps
// r19 VM quadrant tiles joined vs the monolithic hfd_vm (views agent, 2026-10-07).
//   `MODE 1 (transaction): one reactive environment per design, indexed by transaction count: writes (f_su_NW request +
//     f_su_SW data), reads of written rows (f_su_SE), the tap ACKs forced on the root's cfg register (the die feeds them
//     from the static cfg chain), one wrong-owner ACK at op KF (sticky fault).  Compared (hash + count): every write ACK
//     owner, every publish (tap owners + the row at all four x faces), final fault / drained.
//   `MODE 2 (structure): random die inputs with the root idle (wr_v / rd_v held 0); every output bit of both designs is
//     dumped each cycle (trace_ref.hex / trace_dut.hex) for check_vm_tiles.py (one constant latency per output bit).
//   `MUT_XBUS: SW -> SE write bus bits 10/11 swapped in the joined design (SE slice data) -- must FAIL mode 1.
`ifndef MODE
`define MODE 1
`endif
`ifndef SEED
`define SEED 1
`endif
`ifndef NOPS
`define NOPS 60
`endif
`ifndef KF
`define KF 50
`endif
module vm_joined (input wire [0:0] ck, input wire [0:0] rst,
    input wire [2047:0] f_su_SW, f_su_NW, f_su_SE, f_su_NE, input wire [511:0] iSW, iNW, iSE, iNE,
    output wire [2047:0] t_su_SW, t_su_NW, t_su_SE, t_su_NE, output wire [581:0] qSW, qNW, qSE, qNE,
    output wire [2067:0] xSW, xNW, xSE, xNE, output wire [1023:0] t_quant, output wire [511:0] t_router);
    wire [2263:0] sw_n_wr, nw_s_wr, sw_e_wr, se_w_wr, nw_e_wr, ne_w_wr, se_n_wr, ne_s_wr;
    wire [2255:0] sw_n_row, nw_s_row, sw_e_row, se_w_row, nw_e_row, ne_w_row, se_n_row, ne_s_row;
    wire [255:0] sw_n_ctl, nw_s_ctl, sw_e_ctl, se_w_ctl, nw_e_ctl, ne_w_ctl, se_n_ctl, ne_s_ctl;
`ifdef MUT_XBUS
    wire [2263:0] sw_e_wr_x = {sw_e_wr[2263:12], sw_e_wr[10], sw_e_wr[11], sw_e_wr[9:0]};
`else
    wire [2263:0] sw_e_wr_x = sw_e_wr;
`endif
    hfd_vm_sw u_sw (.ck(ck), .rst(rst), .f_su_SW(f_su_SW), .iSW(iSW), .qSW(qSW), .xSW(xSW), .t_su_SW(t_su_SW), .t_router(t_router),
        .f_n_wr(nw_s_wr), .f_n_row(nw_s_row), .f_n_ctl(nw_s_ctl), .t_n_wr(sw_n_wr), .t_n_row(sw_n_row), .t_n_ctl(sw_n_ctl),
        .f_e_wr(se_w_wr), .f_e_row(se_w_row), .f_e_ctl(se_w_ctl), .t_e_wr(sw_e_wr), .t_e_row(sw_e_row), .t_e_ctl(sw_e_ctl));
    hfd_vm_nw u_nw (.ck(ck), .rst(rst), .f_su_NW(f_su_NW), .iNW(iNW), .qNW(qNW), .xNW(xNW), .t_su_NW(t_su_NW), .t_quant(t_quant),
        .f_s_wr(sw_n_wr), .f_s_row(sw_n_row), .f_s_ctl(sw_n_ctl), .t_s_wr(nw_s_wr), .t_s_row(nw_s_row), .t_s_ctl(nw_s_ctl),
        .f_e_wr(ne_w_wr), .f_e_row(ne_w_row), .f_e_ctl(ne_w_ctl), .t_e_wr(nw_e_wr), .t_e_row(nw_e_row), .t_e_ctl(nw_e_ctl));
    hfd_vm_se u_se (.ck(ck), .rst(rst), .f_su_SE(f_su_SE), .iSE(iSE), .qSE(qSE), .xSE(xSE), .t_su_SE(t_su_SE),
        .f_w_wr(sw_e_wr_x), .f_w_row(sw_e_row), .f_w_ctl(sw_e_ctl), .t_w_wr(se_w_wr), .t_w_row(se_w_row), .t_w_ctl(se_w_ctl),
        .f_n_wr(ne_s_wr), .f_n_row(ne_s_row), .f_n_ctl(ne_s_ctl), .t_n_wr(se_n_wr), .t_n_row(se_n_row), .t_n_ctl(se_n_ctl));
    hfd_vm_ne u_ne (.ck(ck), .rst(rst), .f_su_NE(f_su_NE), .iNE(iNE), .qNE(qNE), .xNE(xNE), .t_su_NE(t_su_NE),
        .f_s_wr(se_n_wr), .f_s_row(se_n_row), .f_s_ctl(se_n_ctl), .t_s_wr(ne_s_wr), .t_s_row(ne_s_row), .t_s_ctl(ne_s_ctl),
        .f_w_wr(nw_e_wr), .f_w_row(nw_e_row), .f_w_ctl(nw_e_ctl), .t_w_wr(ne_w_wr), .t_w_row(ne_w_row), .t_w_ctl(ne_w_ctl));
endmodule

module vm_env #(parameter integer SPLIT = 0) (input wire clk, output reg [63:0] h, output integer nev, output reg done,
                                              output reg fault_end);
    reg [0:0] rst = 1;
    reg [2047:0] f_su_SW = 0, f_su_NW = 0, f_su_SE = 0, f_su_NE = 0; reg [511:0] iSW = 0, iNW = 0, iSE = 0, iNE = 0;
    wire [2047:0] t_su_SW, t_su_NW, t_su_SE, t_su_NE; wire [581:0] qSW, qNW, qSE, qNE; wire [2067:0] xSW, xNW, xSE, xNE;
    wire [1023:0] t_quant; wire [511:0] t_router;
    generate if (SPLIT) begin : g_t
        vm_joined u (.ck(clk), .rst(rst), .*);
    end else begin : g_m
        hfd_vm u (.ck(clk), .rst(rst), .*);
    end endgenerate
    task automatic ack(input [3:0] v, input [767:0] own);
        if (SPLIT) force g_t.u.u_sw.cfg = {own, v}; else force g_m.u.cfg = {own, v};
        @(posedge clk); #0.1;
        if (SPLIT) force g_t.u.u_sw.cfg = 772'd0; else force g_m.u.cfg = 772'd0;
    endtask
    function automatic [63:0] mix(input [63:0] a, input [63:0] b); mix = {a[62:0], a[63]} ^ b ^ (a >> 7); endfunction
    reg [63:0] lf; function automatic [63:0] nx(input [63:0] x); nx = {x[62:0], x[63] ^ x[62] ^ x[60] ^ x[59]}; endfunction
    integer k, j, g, nw; reg [7:0] wa [0:63]; reg [2062:0] dat; reg [191:0] own; reg [7:0] ba;
    initial begin
        h = 0; nev = 0; done = 0; fault_end = 0; lf = 64'h9e3779b97f4a7c15 ^ `SEED; nw = 0;
        if (`MODE == 1) begin if (SPLIT) force g_t.u.u_sw.cfg = 772'd0; else force g_m.u.cfg = 772'd0; end
        repeat (8) @(posedge clk); #0.1 rst = 0; repeat (40) @(posedge clk);
if (`MODE == 1) begin
        for (k = 0; k < `NOPS && !fault_end; k = k + 1) begin
            lf = nx(lf); lf = nx(lf);
            for (j = 0; j < 33; j = j + 1) begin lf = nx(lf); dat[j*63 +: 63] = lf[62:0]; end
            lf = nx(lf); own = {lf, nx(lf), nx(nx(lf))}; lf = nx(nx(nx(lf)));
            if (nw == 0 || (lf[3:0] < 7 && nw < 64)) begin         // write
                ba = lf[15:8]; wa[nw] = ba; nw = nw + 1;
                @(negedge clk); f_su_SW = dat[2047:0]; f_su_NW[14:0] = dat[2062:2048]; f_su_NW[15] = 1; f_su_NW[16] = ba[7];
                f_su_NW[23:17] = ba[6:0]; f_su_NW[215:24] = own; f_su_NW[216] = 0;
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
                ba = wa[lf[13:8] % nw];
                @(negedge clk); f_su_SE[0] = 1; f_su_SE[1] = ba[7]; f_su_SE[8:2] = ba[6:0]; f_su_SE[200:9] = own;
                while (t_su_SW[9:6] == 0 && !t_su_SW[5]) @(posedge clk);
                if (t_su_SW[5]) fault_end = 1;
                else begin
                    @(negedge clk); f_su_SE[0] = 0;
                    repeat (40) @(posedge clk);                 // x faces settle; rd_v drop reaches the root
                    h = mix(h, {8'h52, t_su_SW[969:202]}); h = mix(h, xSW[2062:0]); h = mix(h, xNW[2062:0]);
                    h = mix(h, xSE[2062:0]); h = mix(h, xNE[2062:0]);
                    for (j = 0; j < 33; j = j + 1) begin h = mix(h, xSW[j*63 +: 63]); h = mix(h, xNE[j*63 +: 63]); end
                    nev = nev + 1;
                    ack(4'hF, (k == `KF) ? ~t_su_SW[969:202] : t_su_SW[969:202]);
                    for (g = 0; g < 200 && !(t_su_SW[4] || t_su_SW[5]); g = g + 1) @(posedge clk);
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
            f_su_NW[15] = 0; f_su_SE[0] = 0;
        end
        done = 1;
        end
    end
    generate if (`MODE == 2) begin : g_tr
    integer fd;
    initial fd = $fopen(SPLIT ? "trace_dut.hex" : "trace_ref.hex", "w");
    always @(posedge clk) if (!rst && !done) $fdisplay(fd, "%h %h %h %h %h %h %h %h %h %h %h %h %h %h", t_su_SW, t_su_NW, t_su_SE, t_su_NE,
                                                        qSW, qNW, qSE, qNE, xSW, xNW, xSE, xNE, t_quant, t_router);
    end endgenerate
endmodule

module tb_vm_tiles;
    reg clk = 0; always #0.5 clk = ~clk;
    wire [63:0] ha, hb; integer na, nb; wire da, db, fa, fb;
    vm_env #(.SPLIT(0)) a (.clk(clk), .h(ha), .nev(na), .done(da), .fault_end(fa));
    vm_env #(.SPLIT(1)) b (.clk(clk), .h(hb), .nev(nb), .done(db), .fault_end(fb));
    integer t = 0;
    always @(posedge clk) begin
        t <= t + 1;
        if ((da && db) || t > 2000000) begin
            $display("VM_TILES mode=%0d seed=%0d events=%0d/%0d fault=%0d/%0d hash=%s", `MODE, `SEED, na, nb, fa, fb,
                     (ha === hb) ? "MATCH" : "DIFF");
            if (`MODE == 1 && (!(da && db) || ha !== hb || na != nb || fa != fb || na < 10)) $fatal(1, "VM_TILES FAIL");
            $finish;
        end
    end
endmodule
