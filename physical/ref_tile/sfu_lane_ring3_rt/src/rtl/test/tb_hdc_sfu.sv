`timescale 1ns/1ps
// Streams golden vectors ("func x y", func 0 exp / 1 recip / 2 rsqrt) through
// the three special-function pipelines with random bubbles and checks every
// result bit for bit, in order, per function.
module tb_hdc_sfu;
    localparam integer MAXV = 1 << 16;
    reg clk = 1'b0, rst_n = 1'b0;
    always #0.5 clk = ~clk;
    reg [1:0]  vf [0:MAXV-1];
    reg [31:0] vx [0:MAXV-1];
    reg [31:0] vy [0:MAXV-1];
    integer nvec, fd, rc, i;
    // per-function expected queues
    reg [31:0] q [0:2][0:MAXV-1];
    integer qw [0:2];
    integer qr [0:2];
    integer errors = 0, checked = 0, first_err = -1;

    reg        v_in;
    reg [1:0]  f_in;
    reg [31:0] x_in;
    wire [31:0] y0, y1, y2;
    wire vo0, vo1, vo2, fl0, fl1, fl2;
    ot_hdc_exp   u_exp (.clk(clk), .rst_n(rst_n), .v(v_in && f_in == 2'd0), .x(x_in), .y(y0), .vo(vo0), .fault(fl0));
    ot_hdc_recip u_rcp (.clk(clk), .rst_n(rst_n), .v(v_in && f_in == 2'd1), .x(x_in), .y(y1), .vo(vo1), .fault(fl1));
    ot_hdc_rsqrt u_rsq (.clk(clk), .rst_n(rst_n), .v(v_in && f_in == 2'd2), .x(x_in), .y(y2), .vo(vo2), .fault(fl2));

    task automatic check(input integer f, input [31:0] got);
        begin
            if (got !== q[f][qr[f]]) begin
                if (errors < 10) $display("MISMATCH func=%0d idx=%0d got=%h exp=%h", f, qr[f], got, q[f][qr[f]]);
                errors = errors + 1;
            end
            qr[f] = qr[f] + 1;
            checked = checked + 1;
        end
    endtask

    always @(posedge clk) if (rst_n) begin
        if (vo0) check(0, y0);
        if (vo1) check(1, y1);
        if (vo2) check(2, y2);
        if (fl0 || fl1 || fl2) begin errors = errors + 1; $display("FAULT"); end
    end

    integer seed = 7, cyc = 0;
    initial begin
        begin : load
            reg [8*256-1:0] path;
            if (!$value$plusargs("VEC=%s", path)) path = "sfu_vectors.txt";
            fd = $fopen(path, "r");
            nvec = 0;
            while (!$feof(fd)) begin
                rc = $fscanf(fd, "%h %h %h\n", vf[nvec], vx[nvec], vy[nvec]);
                if (rc == 3) nvec = nvec + 1;
            end
            $fclose(fd);
        end
        for (i = 0; i < 3; i = i + 1) begin qw[i] = 0; qr[i] = 0; end
        for (i = 0; i < nvec; i = i + 1) begin q[vf[i]][qw[vf[i]]] = vy[i]; qw[vf[i]] = qw[vf[i]] + 1; end
        v_in = 0; f_in = 0; x_in = 0;
        repeat (3) @(posedge clk);
        rst_n = 1'b1;
        i = 0;
        while (i < nvec) begin
            @(negedge clk);
            if (($random(seed) & 7) != 0) begin
                v_in = 1; f_in = vf[i]; x_in = vx[i]; i = i + 1;
            end else v_in = 0;
            cyc = cyc + 1;
        end
        @(negedge clk) v_in = 0;
        repeat (120) @(posedge clk);
        $display("SFU vectors=%0d checked=%0d errors=%0d", nvec, checked, errors);
        if (errors == 0 && checked == nvec) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
