`timescale 1ns/1ps
// Checks of the V4.1 hyper-connection Sinkhorn unit (rtl/hdc/v41/ot_hdc_sinkhorn.sv)
// against vectors from tools/hdc_golden_v41.py (tools/rtl_hdc_v41_sinkhorn_campaign.py).
//
// tb_hdc_sinkhorn -- the whole unit.
//   +IN=<file>   one case per line: 16 input words (hex, row-major e), then the 16
//                expected output words, then the expected fault flag (0/1)
//   +GAP=<p>     percent of cases followed by an idle gap of up to 8 cycles
//   +EARLY=<p>   percent of cases presented while the unit is still busy
//   +SEED=<n>    driver PRNG seed
//   Every output word and the fault flag are compared; out_valid must arrive
//   exactly LAT = 2 ITERS + 1 clock edges after the accepting edge.
//
// tb_hdc_sk_arith -- the combinational arithmetic alone, one operation per clock.
//   +IN=<file>   "<op> <a hex> <b hex> <expected hex> <flag>" per line; op 0: positive add
//                (flag = overflow), op 1: general divide with gradual underflow (norm ->
//                seed -> quotient SUBN=1; flag = overflow), op 2: the steady-step divide
//                (normal operands, normal quotient, SUBN=0; flag = range), op 3: the add of
//                op 0 with a's exponent presented as (field - 1) + a late increment, the
//                form in which a chain feeds its running sum (a normal, field >= 2)
module tb_hdc_sinkhorn
`ifdef VERILATOR
    (input wire clk)
`endif
    ;
`ifndef VERILATOR
    reg clk = 1'b0;
    always #0.5 clk = !clk;
`endif
    parameter integer ITERS = 20;
    localparam integer LAT = 2 * ITERS + 1;
    localparam integer MAXC = 1 << 22;

    reg          rst_n = 1'b0;
    reg          in_valid = 1'b0;
    reg  [511:0] in_e = 512'd0;
    wire         in_ready, out_valid, fault, busy;
    wire [511:0] y;
    ot_hdc_sinkhorn #(.ITERS(ITERS)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_e(in_e),
        .out_valid(out_valid), .y(y), .fault(fault), .busy(busy));

    integer fin, rc, k;
    integer gap = 0, early = 0, maxcyc = 2000000000;
    reg [31:0] rng = 32'h1B873593;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg [8*512-1:0] fname;
    integer cyc = 0, idle_left = 0;
    integer n_in = 0, n_out = 0, errors = 0, faults = 0, word_err = 0;
    integer lat_min = 1 << 30, lat_max = -1;
    reg have = 1'b0, eof = 1'b0;
    reg [31:0] w;
    reg [511:0] f_in, f_exp;
    reg [31:0]  f_flt;
    // expected outputs queue (the unit holds one case at a time, but keep a short FIFO)
    reg [511:0] q_exp [0:7];
    reg         q_flt [0:7];
    integer     q_acc [0:7];
    integer     q_w = 0, q_r = 0;

    task automatic fetch;
        begin
            have = 1'b0;
            for (k = 0; k < 16; k = k + 1) begin
                rc = $fscanf(fin, "%h", w);
                if (rc != 1) eof = 1'b1;
                f_in[32*k +: 32] = w;
            end
            for (k = 0; k < 16; k = k + 1) begin
                rc = $fscanf(fin, "%h", w);
                if (rc != 1) eof = 1'b1;
                f_exp[32*k +: 32] = w;
            end
            rc = $fscanf(fin, "%d", f_flt);
            if (rc != 1) eof = 1'b1;
            if (!eof) have = 1'b1;
        end
    endtask

    initial begin
        if (!$value$plusargs("IN=%s", fname)) begin $display("need +IN"); $finish; end
        fin = $fopen(fname, "r");
        if (fin == 0) begin $display("cannot open vectors"); $finish; end
        if (!$value$plusargs("GAP=%d", gap)) gap = 0;
        if (!$value$plusargs("EARLY=%d", early)) early = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 2000000000;
        if ($value$plusargs("SEED=%d", rc)) rng = rng ^ rc;
        fetch;
    end

    // -- driver ----------------------------------------------------------------------
    reg show;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rst_n) begin
            if (in_valid && in_ready) begin
                q_exp[q_w % 8] = f_exp;
                q_flt[q_w % 8] = f_flt[0];
                q_acc[q_w % 8] = cyc;
                q_w = q_w + 1;
                n_in = n_in + 1;
                rng = xs(rng);
                if ((rng % 100) < gap) begin rng = xs(rng); idle_left = 1 + rng % 8; end
                fetch;
            end
            // present the next case: at once (while busy) for EARLY percent, else once idle
            rng = xs(rng);
            // (a presented case stays presented until accepted; the unit accepts only when idle)
            show = have && idle_left == 0 &&
                   (!busy || (rng % 100) < early || (in_valid && !in_ready));
            if (idle_left > 0 && !busy) idle_left = idle_left - 1;
            in_valid <= show;
            in_e     <= f_in;
        end
    end

    // -- checker ---------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst_n && out_valid) begin
            n_out = n_out + 1;
            if (q_r == q_w) begin
                if (errors < 20) $display("EXTRA output at cycle %0d", cyc);
                errors = errors + 1;
            end else begin
                if (cyc - 1 - q_acc[q_r % 8] < lat_min) lat_min = cyc - 1 - q_acc[q_r % 8];
                if (cyc - 1 - q_acc[q_r % 8] > lat_max) lat_max = cyc - 1 - q_acc[q_r % 8];
                if (fault) faults = faults + 1;
                if (y !== q_exp[q_r % 8] || fault !== q_flt[q_r % 8]) begin
                    for (k = 0; k < 16; k = k + 1)
                        if (y[32*k +: 32] !== q_exp[q_r % 8][32*k +: 32]) word_err = word_err + 1;
                    if (errors < 10)
                        $display("MISMATCH case=%0d fault=%b expect=%b y0=%h exp0=%h y15=%h exp15=%h",
                                 q_r, fault, q_flt[q_r % 8], y[31:0], q_exp[q_r % 8][31:0],
                                 y[511:480], q_exp[q_r % 8][511:480]);
                    errors = errors + 1;
                end
                q_r = q_r + 1;
            end
        end
        if (rst_n && eof && !have && q_r == q_w && !busy && !in_valid && cyc > 16) begin
            $display("SINKHORN ITERS=%0d cases=%0d outputs=%0d errors=%0d word_errors=%0d faults=%0d lat_min=%0d lat_max=%0d lat_expect=%0d cycles=%0d",
                     ITERS, n_in, n_out, errors, word_err, faults, lat_min, lat_max, LAT, cyc);
            if (errors == 0 && n_out == n_in && (n_out == 0 || (lat_min == LAT && lat_max == LAT)))
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
        if (cyc > maxcyc) begin $display("TIMEOUT n_in=%0d n_out=%0d", n_in, n_out); $finish; end
    end
endmodule

module tb_hdc_sk_arith
`ifdef VERILATOR
    (input wire clk)
`endif
    ;
`ifndef VERILATOR
    reg clk = 1'b0;
    always #0.5 clk = !clk;
`endif
    reg [31:0] a = 32'd0, b = 32'd0;

    // op 0: positive add on the unpacked form
    wire [7:0]  ea = (a[30:23] == 8'd0) ? 8'd1 : a[30:23];
    wire [23:0] ma = {a[30:23] != 8'd0, a[22:0]};
    wire [7:0]  eb = (b[30:23] == 8'd0) ? 8'd1 : b[30:23];
    wire [23:0] mb = {b[30:23] != 8'd0, b[22:0]};
    wire [7:0]  se, sg;
    wire [23:0] sm;
    wire        sovf, su;
    ot_hdc_sk_add u_add (.ea(ea), .ua(1'b0), .ma(ma), .eb(eb), .mb(mb), .eg(sg), .up(su), .e(se), .m(sm), .ovf(sovf));
    wire [31:0] add_y = {1'b0, sm[23] ? se : 8'd0, sm[22:0]};
    // op 3: the same add with a's exponent presented as (ea - 1) + late increment, as a chain feeds it
    wire [7:0]  ce, cg;
    wire [23:0] cm;
    wire        covf, cu;
    ot_hdc_sk_add u_addc (.ea(ea - 8'd1), .ua(1'b1), .ma(ma), .eb(eb), .mb(mb), .eg(cg), .up(cu), .e(ce), .m(cm),
                          .ovf(covf));
    wire [31:0] addc_y = {1'b0, cm[23] ? ce : 8'd0, cm[22:0]};

    // op 1: general divide (the step-0 path)
    wire [23:0]       xm, tm;
    wire signed [9:0] xe, te;
    wire              xz, tz;
    ot_hdc_sk_norm u_nx (.x(a[30:0]), .m(xm), .e(xe), .z(xz));
    ot_hdc_sk_norm u_nt (.x(b[30:0]), .m(tm), .e(te), .z(tz));
    wire [28:0] rg;
    ot_hdc_sk_seed u_sg (.tm(tm), .r(rg));
    wire [30:0] qg;
    wire        rgo;
    ot_hdc_sk_quot #(.SUBN(1)) u_qg (.xm(xm), .xe(xe), .xz(xz), .tm(tm), .te(te), .r(rg), .y(qg), .range(rgo));

    // op 2: steady divide (normal operands as the step datapath feeds them)
    wire [28:0] rs;
    ot_hdc_sk_seed u_ss (.tm(mb), .r(rs));
    wire [30:0] qs;
    wire        rso;
    ot_hdc_sk_quot #(.SUBN(0)) u_qs (.xm(ma), .xe($signed({2'b00, a[30:23]}) - 10'sd127), .xz(1'b0),
                                     .tm(mb), .te($signed({2'b00, b[30:23]}) - 10'sd127), .r(rs),
                                     .y(qs), .range(rso));

    integer fin, rc, cyc = 0, n = 0, errors = 0;
    integer n_op [0:3];
    reg [31:0] op, ra, rb, ex, fl;
    reg [8*512-1:0] fname;
    reg        live = 1'b0;
    reg [31:0] c_op, c_ex, c_fl;
    reg [31:0] got;
    reg        gflag;
    initial begin
        n_op[0] = 0; n_op[1] = 0; n_op[2] = 0; n_op[3] = 0;
        if (!$value$plusargs("IN=%s", fname)) begin $display("need +IN"); $finish; end
        fin = $fopen(fname, "r");
        if (fin == 0) begin $display("cannot open vectors"); $finish; end
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (live) begin                         // check the operation applied last edge
            got = (c_op == 0) ? add_y : (c_op == 1) ? {1'b0, qg} : (c_op == 2) ? {1'b0, qs} : addc_y;
            gflag = (c_op == 0) ? sovf : (c_op == 1) ? rgo : (c_op == 2) ? rso : covf;
            n = n + 1;
            n_op[c_op] = n_op[c_op] + 1;
            if (gflag !== c_fl[0] || (!c_fl[0] && got !== c_ex)) begin
                if (errors < 20) $display("MISMATCH op=%0d a=%h b=%h got=%h/%b expect=%h/%0d", c_op, a, b, got, gflag, c_ex, c_fl);
                errors = errors + 1;
            end
        end
        rc = $fscanf(fin, "%d %h %h %h %d", op, ra, rb, ex, fl);
        if (rc == 5) begin
            a = ra; b = rb; c_op = op; c_ex = ex; c_fl = fl; live = 1'b1;
        end else begin
            $display("SKARITH ops=%0d add=%0d div=%0d div_steady=%0d add_chained=%0d errors=%0d", n, n_op[0], n_op[1], n_op[2], n_op[3], errors);
            if (errors == 0 && n > 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
