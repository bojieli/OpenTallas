`timescale 1ns/1ps
// Q-DV slice bench harness: two qfd_dv_slice instances (sid 0, 1) wired as neighbours:
//   scalar tree   ring s0.sc_o -> s1.sc_i, s1.sc_o -> s0.sc_i
//   level 9       s1.nb9_o -> s0.nb9_i, s0.nb9_o -> s1.nb9_i
//   stream        TB -> s0.sw_i (west edge), s0.so_e -> s1.sw_i, s1.so_w -> s0.se_i, east edge input idle
// Stimulus: +EV=<file> lines "cycle port hex" (a value is applied for that one cycle, otherwise 0); ports:
//   0/1 CMD  2/3 CW0  4/5 CW1  6/7 AR  8/9 DD  10 SWI (port = 2*kind + slice for the per-slice ones).
// Log (+LOG=<file>): every valid output word "cycle name hex": S<i>AR, S<i>DD, S<i>SC, S1E (east edge stream),
// S0W (west edge stream), plus "<cycle> S<i>ST <status>" at the end.  Checking is done by dv_check.py.
module tb_qfd_dv (input wire ck);
    parameter integer MUT = 0;
    reg rst_n = 1'b0;
    reg  [115:0]  cmd [0:1];
    reg  [513:0]  cw0 [0:1], cw1 [0:1];
    reg  [517:0]  ar [0:1];
    reg  [519:0]  dd [0:1];
    reg  [1087:0] swi;
    wire [513:0]  nb0_o, nb1_o;
    wire [1087:0] s0e, s0w, s1e, s1w;
    wire [95:0]   sc0, sc1;
    wire [545:0]  ar0_o, ar1_o;
    wire [547:0]  dd0_o, dd1_o;
    wire [44:0]   st0, st1;
    qfd_dv_slice #(.MUT(MUT)) s0 (.ck(ck), .rst_n(rst_n), .sid(4'd0), .cmd(cmd[0]), .cw0(cw0[0]), .cw1(cw1[0]),
        .nb9_i(nb1_o), .nb9_o(nb0_o), .sw_i(swi), .so_e(s0e), .se_i(s1w), .so_w(s0w), .sc_i(sc1), .sc_o(sc0),
        .ar_o(ar0_o), .ar_i(ar[0]), .dd_o(dd0_o), .dd_i(dd[0]), .st(st0));
    qfd_dv_slice #(.MUT(MUT)) s1 (.ck(ck), .rst_n(rst_n), .sid(4'd1), .cmd(cmd[1]), .cw0(cw0[1]), .cw1(cw1[1]),
        .nb9_i(nb0_o), .nb9_o(nb1_o), .sw_i(s0e), .so_e(s1e), .se_i(1088'd0), .so_w(s1w), .sc_i(sc0), .sc_o(sc1),
        .ar_o(ar1_o), .ar_i(ar[1]), .dd_o(dd1_o), .dd_i(dd[1]), .st(st1));
    // ---------------------------------------------------------------- stimulus
    integer fd, lg, cyc, ncyc, ec, ep, r;
    reg [1087:0] ev;
    reg have;
    reg [1023:0] evf, lgf;
    task automatic clear;
        integer i;
        begin
            for (i = 0; i < 2; i = i + 1) begin cmd[i] = 0; cw0[i] = 0; cw1[i] = 0; ar[i] = 0; dd[i] = 0; end
            swi = 0;
        end
    endtask
    task automatic apply(input integer p, input [1087:0] v);
        begin
            case (p)
                0, 1: cmd[p % 2] = v[115:0];
                2, 3: cw0[p % 2] = v[513:0];
                4, 5: cw1[p % 2] = v[513:0];
                6, 7: ar[p % 2] = v[517:0];
                8, 9: dd[p % 2] = v[519:0];
                10:   swi = v;
                default: $fatal(1, "bad port %0d", p);
            endcase
        end
    endtask
    integer pre = 0;
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w");
        clear;
        cyc = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
    end
    // stimulus and log on the falling edge (outputs settled after the rising edge)
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            if (ar0_o[545]) $fdisplay(lg, "%0d S0AR %h", cyc, ar0_o);
            if (ar1_o[545]) $fdisplay(lg, "%0d S1AR %h", cyc, ar1_o);
            if (dd0_o[547]) $fdisplay(lg, "%0d S0DD %h", cyc, dd0_o);
            if (dd1_o[547]) $fdisplay(lg, "%0d S1DD %h", cyc, dd1_o);
            if (sc0[95])    $fdisplay(lg, "%0d S0SC %h", cyc, sc0);
            if (sc1[95])    $fdisplay(lg, "%0d S1SC %h", cyc, sc1);
            if (s1e[1087])  $fdisplay(lg, "%0d S1E %h", cyc, s1e);
            if (s0w[1087])  $fdisplay(lg, "%0d S0W %h", cyc, s0w);
            clear;
            while (have && ec == cyc) begin
                apply(ep, ev);
                r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
            end
            if (have && ec < cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d S0ST %h", cyc, st0);
                $fdisplay(lg, "%0d S1ST %h", cyc, st1);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
