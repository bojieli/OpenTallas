`timescale 1ns/1ps
// tb_dsfd_svc_pc (CLAUDE S81-PH svc): transaction-level gate of the per-PC tile.  Random request words (valid with a
// random duty) from the quadrant side, random response words / rk / wd pulses from the ctrl side; scoreboards:
// every request word reaches rq exactly once, in order, bit-exact; every response word reaches qr_* in order; rk and
// wd pulse counts equal.  Prints TB_SVC_PC PASS / FAIL.
module tb_dsfd_svc_pc;
    reg ck = 0, rst = 0;
    always #0.4165 ck = ~ck;
    reg [340:0] qrq = 0; reg rk = 0, wd = 0, rv = 0; reg [255:0] r_data = 0; reg [16:0] r_tag = 0; reg [3:0] r_beat = 0;
    wire [340:0] rq; wire qrk, qwd, qrv; wire [255:0] qr_data; wire [16:0] qr_tag; wire [3:0] qr_beat;
    dsfd_svc_pc dut (.ck(ck), .rst(rst), .qrq(qrq), .rq(rq), .rk(rk), .qrk(qrk), .wd(wd), .qwd(qwd), .rv(rv), .r_data(r_data),
        .r_tag(r_tag), .r_beat(r_beat), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat));
    localparam integer N = 4000;
    reg [340:0] sq [0:N-1]; reg [276:0] sr [0:N-1];
    integer nq = 0, nr = 0, cq = 0, cr = 0, krk_i = 0, krk_o = 0, kwd_i = 0, kwd_o = 0, err = 0, cyc = 0, i, seed;
    reg [340:0] w; reg [276:0] x;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        void'($urandom(seed));
        repeat (5) @(posedge ck);
        rst = 1;
        repeat (5) @(posedge ck);
        while (nq < N || nr < N) begin
            @(negedge ck);
            qrq = 0; rv = 0; rk = 0; wd = 0;
            if (nq < N && ($urandom % 100) < 70) begin
                for (i = 0; i < 341; i = i + 32) w[i +: 32] = $urandom;
                w[0] = 1'b1; qrq = w; sq[nq] = w; nq = nq + 1;
            end
            if (nr < N && ($urandom % 100) < 80) begin
                for (i = 0; i < 277; i = i + 32) x[i +: 32] = $urandom;
                {r_beat, r_tag, r_data} = x; rv = 1; sr[nr] = x; nr = nr + 1;
            end
            if ($urandom % 3 == 0) begin rk = 1; krk_i = krk_i + 1; end
            if ($urandom % 5 == 0) begin wd = 1; kwd_i = kwd_i + 1; end
        end
        @(negedge ck); qrq = 0; rv = 0; rk = 0; wd = 0;
        repeat (10) @(posedge ck);
        if (cq != N || cr != N || krk_o != krk_i || kwd_o != kwd_i) err = err + 1;
        $display("requests %0d/%0d responses %0d/%0d rk %0d/%0d wd %0d/%0d errors %0d", cq, N, cr, N, krk_o, krk_i, kwd_o, kwd_i, err);
        $display("TB_SVC_PC %s", err == 0 ? "PASS" : "FAIL");
        $finish;
    end
    always @(posedge ck) if (rst) begin
        if (rq[0]) begin if (cq >= N || rq !== sq[cq]) err = err + 1; cq = cq + 1; end
        if (qrv) begin if (cr >= N || {qr_beat, qr_tag, qr_data} !== sr[cr]) err = err + 1; cr = cr + 1; end
        if (qrk) krk_o = krk_o + 1;
        if (qwd) kwd_o = kwd_o + 1;
    end
endmodule
