`timescale 1ns/1ps
// tb_s81ph_svc_fault (s81-die-2 2026-10-08): the IO-hub fault path of the tiled svc hub ot_s81ph_svc_io_t.
// A clean phase (random well-formed od / a0 frames, 400 cycles) must leave fault low; then one malformed od header
// (len 300 > LMAX 255) is accepted on a random quadrant: fault must rise exactly LAT cycles after the accept, stay
// high (sticky), and LAT is printed per FSTN so the script can check FSTN 1 = FSTN 0 + 1.  +SEED.
module tb_s81ph_svc_fault;
    parameter integer FSTN = 1;
    reg ck = 0, rst = 0;
    always #0.4166 ck = ~ck;
    reg [514:0] q = 0; wire [513:0] od, xd; wire [1025:0] ad; wire fault; wire [2059:0] q_q;
    reg [3:0] od_v = 0, a0_v = 0; reg [2047:0] od_d = 0, a0_d = 0; wire [3:0] od_r, a0_r;
    wire a1_r, x_r; wire of, xf, af;
    ot_s81ph_svc_io_t #(.FSTN(FSTN)) dut (.ck(ck), .rst(rst), .q(q), .od(od), .xd(xd), .ad(ad), .fault(fault), .q_q(q_q),
        .od_v(od_v), .od_d(od_d), .od_r(od_r), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(1'b0), .a1_d(512'd0), .a1_r(a1_r),
        .x_v(1'b0), .x_d(512'd0), .x_r(x_r), .of(of), .xf(xf), .af(af));
    integer busy, seed, cyc = 0, t_acc = -1, t_flt = -1, errs = 0, src, k;
    // well-formed frames: header len 0..3 then len payload words, per quadrant
    integer rem [0:3];
    always @(posedge ck) cyc <= cyc + 1;
    reg [3:0] acc = 0;                                         // handshakes sampled at the posedge (pre-update values)
    always @(posedge ck) acc <= od_v & od_r;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        for (k = 0; k < 4; k = k + 1) rem[k] = -1;
        repeat (5) @(posedge ck); rst = 1; repeat (8) @(posedge ck);
        repeat (400) begin
            @(negedge ck);
            for (k = 0; k < 4; k = k + 1) begin
                if (acc[k]) rem[k] = rem[k] - 1;                    // accepted at the last posedge
                if (acc[k] || !od_v[k]) if ($urandom(seed) % 3 == 0) begin
                    od_v[k] = 1'b1;
                    if (rem[k] < 0) begin od_d[512*k +: 512] = 0; od_d[512*k + 480 +: 12] = $urandom(seed) % 4; rem[k] = od_d[512*k + 480 +: 12]; end
                    else od_d[512*k +: 512] = {16{$urandom(seed)}};
                end else od_v[k] = 1'b0;
            end
            if (fault) begin errs = errs + 1; if (errs < 3) $display("unexpected fault at %0d", cyc); end
        end
        // drain the open frames (an offered word stays until accepted; then the rest of its frame)
        busy = 1;
        while (busy) begin
            @(negedge ck); busy = 0;
            for (k = 0; k < 4; k = k + 1) begin
                if (acc[k]) begin rem[k] = rem[k] - 1; od_v[k] = 1'b0; end
                if (!od_v[k] && rem[k] >= 0) begin od_v[k] = 1'b1; od_d[512*k +: 512] = {16{$urandom(seed)}}; end
                if (od_v[k]) busy = 1;
            end
        end
        repeat (60) @(negedge ck);
        if (fault) begin errs = errs + 1; $display("fault after clean phase"); end
        // one malformed header on a random quadrant
        src = $urandom(seed) % 4;
        od_d[512*src +: 512] = 0; od_d[512*src + 480 +: 12] = 12'd300; od_v[src] = 1'b1;
        @(posedge ck); while (!od_r[src]) @(posedge ck);
        t_acc = cyc; @(negedge ck); od_v[src] = 1'b0;
        // keep the malformed frame fed (payload words) so the merge reaches the header
        repeat (200) begin
            @(posedge ck);
            if (fault && t_flt < 0) t_flt = cyc;
            if (t_flt >= 0 && !fault) begin errs = errs + 1; $display("fault not sticky"); end
        end
        if (t_flt < 0) begin errs = errs + 1; $display("no fault"); end
        $display("SVC_FAULT_BENCH %s FSTN %0d seed %0d src %0d lat %0d errors %0d", errs ? "FAIL" : "PASS", FSTN, seed, src,
                 t_flt < 0 ? -1 : t_flt - t_acc, errs);
        $finish;
    end
endmodule
