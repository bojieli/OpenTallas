`timescale 1ns/1ps
// Opt-in registered-transport successor of tb_dsrom_su_norm.
// Bench of ot_dsrom_su_norm (DS-ROM recovery lever su_norm): one row of golden operands, timed at the unit's clock
// (1.2 GHz), with the hub traverse in front (HUB_IN stages from the vector memory to the unit) and behind (HUB_OUT
// stages to the consumer) charged as stage counts on the valid / index lines (the data are constants of the row, so
// delaying the index is cycle-identical to delaying the vector).
// Files (cwd, $readmemh, one 32-bit word a line unless noted):
//   x.mem    (HC ? 4 : 1) * D words, copy k element j at k*D + j       w.mem   D words (gain)
//   cfg.mem  pre0 pre1 pre2 pre3 n_f eps                               cs.mem  RD/2 cos, RD/2 sin (RD > 0)
//   ey.mem   D words: the normalised row (BF16 as binary32)            er.mem  D words: after the RoPE tail (RD > 0)
//   eqc.mem  D/32 x 256-bit codes   eqe.mem D/32 x 16-bit exponent   eqy.mem D/32 x 512-bit dequantised BF16 (QUANT)
// Prints  SUN go=<cycle> y_last=<landing> r=<rstd cycle> ro_last=<landing> q_last=<landing> (cycles after go,
// landings include HUB_OUT) ey=<errors> er=<errors> eq=<errors> checked_y=.. checked_q=.. fault=..
module tb_dsrom_su_norm_transport #(
    parameter integer N = 1024, parameter integer D = 5120, parameter integer HC = 1, parameter integer RD = 0,
    parameter integer QUANT = 1, parameter integer RW = 9, parameter integer BW = 9,
    parameter integer HUB_IN = 33, parameter integer HUB_OUT = 23,
    parameter integer REGISTER_OUTPUT = 0
);
    localparam integer NV = (D + N - 1) / N;
    localparam integer NX = (HC ? 4 : 1) * D;
    localparam integer NB = D / 32;
    reg clk = 1'b0;
    always #0.416666667 clk = ~clk;
    reg [31:0]  xm [0:NX-1];
    reg [31:0]  wm [0:D-1];
    reg [31:0]  cfg [0:5];
    reg [31:0]  csm [0:(RD ? RD : 2)-1];
    reg [31:0]  ey [0:D-1];
    reg [31:0]  er [0:D-1];
    reg [255:0] eqc [0:NB-1];
    reg [15:0]  eqe [0:NB-1];
    reg [511:0] eqy [0:NB-1];
    initial begin
        $readmemh("x.mem", xm);
        $readmemh("w.mem", wm);
        $readmemh("cfg.mem", cfg);
        $readmemh("ey.mem", ey);
        if (RD > 0) begin $readmemh("cs.mem", csm); $readmemh("er.mem", er); end
        if (QUANT) begin $readmemh("eqc.mem", eqc); $readmemh("eqe.mem", eqe); $readmemh("eqy.mem", eqy); end
    end

    reg rst_n = 1'b0, go = 1'b0, in_v = 1'b0, wl_v = 1'b0;
    reg [7:0] wl_i = 0;
    reg [N*32-1:0] wl_d;
    reg [(HC ? 4 : 1)*N*32-1:0] in_x;
    wire y_v, r_v, q_v, ro_v, fault;
    wire [7:0] y_i, q_i;
    wire [N*32-1:0] y, ro;
    wire [31:0] r;
    wire [(QUANT ? N/32 : 1)*256-1:0] q_codes;
    wire [(QUANT ? N/32 : 1)*10-1:0] q_e;
    wire [(QUANT ? N/32 : 1)*512-1:0] q_y;
    reg  [(RD ? RD/2 : 1)*32-1:0] cos_t, sin_t;
    integer i, j, k;
    initial begin
        cos_t = 0; sin_t = 0;
        #0.1;
        for (i = 0; i < RD / 2; i = i + 1) begin
            cos_t[i * 32 +: 32] = csm[i];
            sin_t[i * 32 +: 32] = csm[RD / 2 + i];
        end
    end
    wire raw_y_v, raw_q_v, raw_ro_v;
    wire [7:0] raw_y_i, raw_q_i;
    wire [N*32-1:0] raw_y, raw_ro;
    wire [(QUANT ? N/32 : 1)*256-1:0] raw_q_codes;
    wire [(QUANT ? N/32 : 1)*10-1:0] raw_q_e;
    wire [(QUANT ? N/32 : 1)*512-1:0] raw_q_y;
    ot_dsrom_su_norm #(.N(N), .D(D), .HC(HC), .RD(RD), .QUANT(QUANT), .RW(RW), .BW(BW)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre({cfg[3], cfg[2], cfg[1], cfg[0]}),
        .n_f(cfg[4]), .eps(cfg[5]), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t(cos_t), .sin_t(sin_t),
        .y_v(raw_y_v), .y_i(raw_y_i), .y(raw_y), .r_v(r_v), .r(r), .q_v(raw_q_v), .q_i(raw_q_i), .q_codes(raw_q_codes), .q_e(raw_q_e), .q_y(raw_q_y),
        .ro_v(raw_ro_v), .ro(raw_ro), .fault(fault));
    localparam integer OD = REGISTER_OUTPUT ? HUB_OUT : 0;
    ot_dsrom_su_transport_delay #(.W(N*32+8), .D(OD)) dy (
        .clk(clk), .rst_n(rst_n), .v(raw_y_v), .d({raw_y_i,raw_y}),
        .vo(y_v), .q({y_i,y}));
    ot_dsrom_su_transport_delay #(.W(N*32), .D(OD)) dro (
        .clk(clk), .rst_n(rst_n), .v(raw_ro_v), .d(raw_ro), .vo(ro_v), .q(ro));
    ot_dsrom_su_transport_delay #(.W((QUANT ? N/32 : 1)*778+8), .D(OD)) dq (
        .clk(clk), .rst_n(rst_n), .v(raw_q_v), .d({raw_q_i,raw_q_codes,raw_q_e,raw_q_y}),
        .vo(q_v), .q({q_i,q_codes,q_e,q_y}));


    // the hub traverse in front: issue at go+1 .. go+NV, arrival HUB_IN later
    reg [HUB_IN:0] hv;
    reg [7:0]      hi [0:HUB_IN];
    integer cyc = 0, go_cyc = -1, iss = 0, ey_err = 0, er_err = 0, eq_err = 0, ny = 0, nq = 0, nr = 0;
    integer y_last = -1, ro_last = -1, q_last = -1, r_cyc = -1, idle = 0, ro_cnt = 0;
    reg [7:0] vi;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        // gain ROM load
        wl_v <= 1'b0;
        if (cyc >= 5 && cyc < 5 + NV) begin
            wl_v <= 1'b1;
            wl_i <= cyc - 5;
            for (j = 0; j < N; j = j + 1)
                wl_d[j * 32 +: 32] <= ((cyc - 5) * N + j < D) ? wm[(cyc - 5) * N + j] : 32'd0;
        end
        go <= (cyc == 10 + NV);
        if (cyc == 10 + NV) go_cyc <= cyc + 1;
        // issue
        hv[0] <= (go_cyc >= 0 && iss < NV && cyc >= go_cyc);
        hi[0] <= iss;
        if (go_cyc >= 0 && iss < NV && cyc >= go_cyc) iss <= iss + 1;
        for (k = 1; k <= HUB_IN; k = k + 1) begin hv[k] <= hv[k - 1]; hi[k] <= hi[k - 1]; end
        // arrival at the unit
        in_v <= hv[HUB_IN - 1];
        vi = hi[HUB_IN - 1];
        for (k = 0; k < (HC ? 4 : 1); k = k + 1)
            for (j = 0; j < N; j = j + 1)
                in_x[(k * N + j) * 32 +: 32] <= (vi * N + j < D) ? xm[k * D + vi * N + j] : 32'd0;
        if (wl_v) $display("SU_BOUNDARY gain_load cycle=%0d vector=%0d", cyc, wl_i);
        if (go) $display("SU_BOUNDARY go cycle=%0d", cyc);
        if (in_v) $display("SU_BOUNDARY lane_input cycle=%0d vector=%0d", cyc, dut.in_i);
        if (dut.x_v) $display("SU_BOUNDARY mix_output cycle=%0d vector=%0d", cyc, dut.xi);
        if (dut.ss_v) $display("SU_BOUNDARY sumsq_root cycle=%0d", cyc);
        if (dut.ssw[32]) $display("SU_BOUNDARY scalar_input cycle=%0d", cyc);
        if (dut.rb[32]) $display("SU_BOUNDARY scalar_broadcast cycle=%0d", cyc);
        if (raw_y_v) $display("SU_BOUNDARY raw_y cycle=%0d vector=%0d", cyc, raw_y_i);
        if (raw_q_v) $display("SU_BOUNDARY raw_q cycle=%0d vector=%0d", cyc, raw_q_i);
        if (y_v) $display("SU_BOUNDARY consumer_y cycle=%0d vector=%0d", cyc, y_i);
        if (q_v) $display("SU_BOUNDARY consumer_q cycle=%0d vector=%0d", cyc, q_i);
        if (r_v) $display("SU_BOUNDARY reduction_scalar cycle=%0d", cyc);
        if (r_v && r_cyc < 0) r_cyc <= cyc - go_cyc;
        if (y_v) begin
            y_last <= cyc - go_cyc + (REGISTER_OUTPUT ? 0 : HUB_OUT);
            for (j = 0; j < N; j = j + 1)
                if (y_i * N + j < D) begin
                    ny = ny + 1;
                    if (y[j * 32 +: 32] !== ey[y_i * N + j]) begin
                        if (ey_err < 5) $display("Y mismatch el %0d got %08x want %08x", y_i * N + j, y[j * 32 +: 32],
                                                 ey[y_i * N + j]);
                        ey_err = ey_err + 1;
                    end
                end
        end
        if (ro_v) begin
            ro_last <= cyc - go_cyc + (REGISTER_OUTPUT ? 0 : HUB_OUT);
            for (j = 0; j < N; j = j + 1)
                if (ro_cnt * N + j < D) begin
                    nr = nr + 1;
                    if (ro[j * 32 +: 32] !== er[ro_cnt * N + j]) begin
                        if (er_err < 5) $display("R mismatch el %0d got %08x want %08x", ro_cnt * N + j, ro[j * 32 +: 32],
                                                 er[ro_cnt * N + j]);
                        er_err = er_err + 1;
                    end
                end
            ro_cnt = ro_cnt + 1;
        end
        if (q_v) begin
            q_last <= cyc - go_cyc + (REGISTER_OUTPUT ? 0 : HUB_OUT);
            for (k = 0; k < (QUANT ? N / 32 : 0); k = k + 1)
                if (q_i * (N / 32) + k < NB) begin
                    nq = nq + 1;
                    if (q_codes[k * 256 +: 256] !== eqc[q_i * (N / 32) + k] ||
                        q_e[k * 10 +: 10] !== eqe[q_i * (N / 32) + k][9:0] ||
                        q_y[k * 512 +: 512] !== eqy[q_i * (N / 32) + k]) begin
                        if (eq_err < 5) $display("Q mismatch block %0d e %0d want %0d", q_i * (N / 32) + k,
                                                 $signed(q_e[k * 10 +: 10]), $signed(eqe[q_i * (N / 32) + k][9:0]));
                        eq_err = eq_err + 1;
                    end
                end
        end
        if (go_cyc >= 0 && cyc > go_cyc + 2000) begin
            $display("SUN go=%0d y_last=%0d r=%0d ro_last=%0d q_last=%0d ey=%0d er=%0d eq=%0d checked_y=%0d checked_r=%0d checked_q=%0d fault=%0d",
                     go_cyc, y_last, r_cyc, ro_last, q_last, ey_err, er_err, eq_err, ny, nr, nq, fault);
            if (ey_err == 0 && er_err == 0 && eq_err == 0 && ny == D && (RD == 0 || nr == D) && (!QUANT || nq == NB)
                && !fault) $display("PASS");
            else $display("FAIL");
            $finish;
        end
    end
endmodule

// Bench-only transport successor. Payload, index and valid share the same
// registered path. The original engine and arithmetic are unchanged.
module ot_dsrom_su_transport_delay #(parameter integer W=32, D=0)(
 input wire clk, rst_n, v, input wire [W-1:0] d,
 output wire vo, output wire [W-1:0] q);
 generate if (D==0) begin
   assign vo=v; assign q=d;
 end else begin
   reg [D-1:0] vv;
   reg [W-1:0] dd [0:D-1];
   integer i;
   always @(posedge clk or negedge rst_n)
     if (!rst_n) vv <= 0;
     else vv <= (vv << 1) | v;
   always @(posedge clk) begin
     dd[0] <= d;
     for(i=1;i<D;i=i+1) dd[i] <= dd[i-1];
   end
   assign vo=vv[D-1]; assign q=dd[D-1];
 end endgenerate
endmodule
