`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19: lockstep bench of the attention tile's boot-age successors against the closed modules
//   qkd_attn_service_root_b (cfg_pv_lead) vs qkd_attn_service_root #(.PV_LEAD(PL), .CAL_PIPE(1))
//   qkd_attn_result_face_sb (cfg_f_dly)   vs qkd_attn_result_face_s #(.NF(10), .F_DLY(FD), .CAL_PIPE(1))
// The root pair runs with cfg_f_dly = 1 (the closed root's END law).  A third root (qkd_attn_service_root_b, cfg_f_dly = FD:
// END = PV_START + LAST + 48 + FD - 1) drives the face pair (running / start_qk / age / ep / layer / cal), with a final-join model
// that emits the 32 result beats on the reference's RESULT_AGE window (fault-free path), plus commands with a beat
// moved (fault path).  Every output of both pairs is compared on every edge; phase C: invalid boot ages (PV_LEAD > bound,
// F_DLY 0 / > bound) must fault the successors.
// Prints "KVBA_ATTN PASS PL=.. FD=.. mut=.. checks=N" or "KVBA_ATTN FAIL ...".
module tb_kvba_attn;
    parameter integer PL = 37, FD = 49, MUT = 0, FMUT = 0, NCMD = 24, SEED = 1;
    localparam integer PLB = 63, FDB = 127;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg [7:0] c_pl, c_fd;
    reg rv = 0; reg [15:0] r_ep = 0; reg [5:0] r_ly = 0; reg [17:0] r_pos = 0; reg [175:0] r_cal = 0;
    reg qv = 0; reg [4:0] qb = 0;
    // root pair
    wire a_rr, b_rr, a_qr, b_qr, a_run, b_run, a_sq, b_sq, a_sp, b_sp, a_lf, b_lf, a_if, b_if;
    wire [15:0] a_age, b_age, a_ep, b_ep; wire [5:0] a_ly, b_ly; wire [13:0] a_ctx, b_ctx; wire [175:0] a_cal, b_cal;
    wire [31:0] a_cy, b_cy;
    qkd_attn_service_root #(.PV_LEAD(PL), .CAL_PIPE(1), .MUT(0)) u_rref (.ck(ck), .rst_n(rst_n), .request_valid(rv),
        .request_ready(a_rr), .request_epoch(r_ep), .request_layer(r_ly), .request_position(r_pos), .fused_program_capability(1'b1),
        .request_calendar(r_cal), .q_valid(qv), .q_beat(qb), .q_ready(a_qr), .running(a_run), .start_qk(a_sq), .start_pv(a_sp),
        .age(a_age), .ep(a_ep), .layer(a_ly), .ctx(a_ctx), .cal(a_cal), .cycles(a_cy), .local_fault(a_lf), .io_fault(a_if));
    qkd_attn_service_root_b #(.PV_LEAD(PLB), .CAL_PIPE(1), .MUT(MUT)) u_rdut (.ck(ck), .rst_n(rst_n), .cfg_pv_lead(c_pl), .cfg_f_dly(8'd1),
        .request_valid(rv), .request_ready(b_rr), .request_epoch(r_ep), .request_layer(r_ly), .request_position(r_pos),
        .fused_program_capability(1'b1), .request_calendar(r_cal), .q_valid(qv), .q_beat(qb), .q_ready(b_qr), .running(b_run),
        .start_qk(b_sq), .start_pv(b_sp), .age(b_age), .ep(b_ep), .layer(b_ly), .ctx(b_ctx), .cal(b_cal), .cycles(b_cy),
        .local_fault(b_lf), .io_fault(b_if));
    // face-driving root: the successor with the boot F_DLY (its END covers the face's last beat)
    wire c_rr, c_qr, c_run, c_sq, c_sp, c_lf, c_if; wire [15:0] c_age, c_ep; wire [5:0] c_ly; wire [13:0] c_ctx;
    wire [175:0] c_cal; wire [31:0] c_cy;
    qkd_attn_service_root_b #(.PV_LEAD(PLB), .CAL_PIPE(1), .MUT(MUT)) u_rface (.ck(ck), .rst_n(rst_n), .cfg_pv_lead(c_pl),
        .cfg_f_dly(c_fd), .request_valid(rv), .request_ready(c_rr), .request_epoch(r_ep), .request_layer(r_ly),
        .request_position(r_pos), .fused_program_capability(1'b1), .request_calendar(r_cal), .q_valid(qv), .q_beat(qb),
        .q_ready(c_qr), .running(c_run), .start_qk(c_sq), .start_pv(c_sp), .age(c_age), .ep(c_ep), .layer(c_ly), .ctx(c_ctx),
        .cal(c_cal), .cycles(c_cy), .local_fault(c_lf), .io_fault(c_if));
    // face pair (both driven by the face-driving root)
    reg fv = 0; reg [4:0] fb = 0; reg [511:0] fdat = 0; reg [15:0] fe = 0; reg [9:0] uf = 0;
    wire a_xv, b_xv, a_xd, b_xd, a_sf, b_sf, a_rf, b_rf; wire [4:0] a_xb, b_xb; wire [511:0] a_xdat, b_xdat;
    wire [15:0] a_xe, b_xe; wire [5:0] a_xl, b_xl; wire [7:0] a_h, b_h;
    qkd_attn_result_face_s #(.NF(10), .RESULT_RELAY(0), .F_DLY(FD), .CAL_PIPE(1), .MUT(0)) u_fref (.ck(ck), .rst_n(rst_n),
        .running(c_run), .start_qk(c_sq), .age(c_age), .ep(c_ep), .layer(c_ly), .cal(c_cal), .root_local_fault(c_lf),
        .root_io_fault(c_if), .f_valid(fv), .f_beat(fb), .f_data(fdat), .f_epoch(fe), .unit_fault(uf),
        .result_valid(a_xv), .result_beat(a_xb), .result_data(a_xdat), .result_epoch(a_xe), .result_layer(a_xl),
        .result_done(a_xd), .service_fault(a_sf), .result_fault(a_rf), .hdr_l(a_h));
    qkd_attn_result_face_sb #(.NF(10), .RESULT_RELAY(0), .F_DLY(FDB), .CAL_PIPE(1), .MUT(FMUT)) u_fdut (.ck(ck), .rst_n(rst_n),
        .cfg_f_dly(c_fd), .running(c_run), .start_qk(c_sq), .age(c_age), .ep(c_ep), .layer(c_ly), .cal(c_cal),
        .root_local_fault(c_lf), .root_io_fault(c_if), .f_valid(fv), .f_beat(fb), .f_data(fdat), .f_epoch(fe), .unit_fault(uf),
        .result_valid(b_xv), .result_beat(b_xb), .result_data(b_xdat), .result_epoch(b_xe), .result_layer(b_xl),
        .result_done(b_xd), .service_fault(b_sf), .result_fault(b_rf), .hdr_l(b_h));
    integer checks = 0, errs = 0, seed, cmds = 0, clean_ok = 0, clean = 0, pvs = 0, k, n, res, skew;
    task cmp; begin
        checks = checks + 1;
        if ({a_rr, a_qr, a_run, a_sq, a_sp, a_age, a_ep, a_ly, a_ctx, a_cal, a_cy, a_lf, a_if} !==
            {b_rr, b_qr, b_run, b_sq, b_sp, b_age, b_ep, b_ly, b_ctx, b_cal, b_cy, b_lf, b_if}) begin
            errs = errs + 1;
            if (errs < 6) $display("ROOT MISMATCH t=%0t start_pv %b/%b running %b/%b age %0d/%0d lf %b/%b", $time,
                                   a_sp, b_sp, a_run, b_run, a_age, b_age, a_lf, b_lf);
        end
        if ({a_xv, a_xb, a_xdat, a_xe, a_xl, a_xd, a_sf, a_rf, a_h} !== {b_xv, b_xb, b_xdat, b_xe, b_xl, b_xd, b_sf, b_rf, b_h}) begin
            errs = errs + 1;
            if (errs < 6) $display("FACE MISMATCH t=%0t valid %b/%b beat %0d/%0d done %b/%b rfault %b/%b", $time,
                                   a_xv, b_xv, a_xb, b_xb, a_xd, b_xd, a_rf, b_rf);
        end
    end endtask
    reg [4:0] pfl = 0; integer nfl = 0;
    always @(posedge ck) begin
        pfl <= {a_lf, a_if, c_lf, c_if, a_rf};
        if (({a_lf, a_if, c_lf, c_if, a_rf} & ~pfl) != 0 && nfl < 6) begin nfl = nfl + 1;
            $display("DBG fault t=%0t {a_lf,a_if,c_lf,c_if,a_rf}=%b a_age=%0d c_age=%0d run %b/%b rr %b/%b rv %b qv %b qr %b", $time,
                     {a_lf, a_if, c_lf, c_if, a_rf}, a_age, c_age, a_run, c_run, a_rr, c_rr, rv, qv, a_qr); end
    end
    task do_reset; begin rst_n = 0; rv = 0; qv = 0; fv = 0; repeat (6) @(negedge ck); rst_n = 1; end endtask
    reg [15:0] pv, p0, p1, rr, last; integer t_req, bad_ok;
    initial begin
        seed = SEED; c_pl = 8'(PL); c_fd = 8'(FD);
        do_reset;
        while (!(a_rr && c_rr)) @(negedge ck);
        for (k = 0; k < NCMD; k = k + 1) begin
            // calendar: R [175:160], P1 [159:144], P0 [143:128], PV_START [127:112]; held >= 3 edges before the request
            pv = 16'(PL + 2 + ($unsigned($random(seed)) % 120)); p0 = 16'($unsigned($random(seed)) % 90);
            p1 = 16'($unsigned($random(seed)) % 90); rr = 16'($unsigned($random(seed)) % 120);
            last = (p0 > p1) ? ((p0 > rr) ? p0 : rr) : ((p1 > rr) ? p1 : rr);
            r_cal = {rr, p1, p0, pv, 16'($random(seed)), 32'($random(seed)), 32'($random(seed)), 32'($random(seed))};
            r_ep = 16'h0b00 + 16'(k); r_ly = 6'(k); r_pos = 18'($unsigned($random(seed)) % 8000);
            repeat (3) begin @(posedge ck); #0.1 cmp; @(negedge ck); end
            res = pv + last + 16 + FD;              // RESULT_AGE: beat b presented at age res + b (CAL_PIPE face law)
            skew = (k % 4 == 3) ? 1 : 0;            // every 4th command: beats one edge late (fault path)
            rv = 1; t_req = 0; n = 0;
            while (n < 3000) begin
                // q beats in the root's q window (age 1..32 after start_qk), the final join's 32 beats on the face window
                qv = a_qr; qb = 5'(a_age - 16'd1);
                fv = c_run && !c_sq && (c_age >= 16'(res + skew)) && (c_age < 16'(res + skew + 32));
                fb = 5'(c_age - 16'(res + skew)); fe = c_ep;
                for (int w = 0; w < 16; w = w + 1) fdat[32*w +: 32] = $random(seed);
                @(posedge ck); #0.1 cmp; if (a_sp) pvs = pvs + 1; @(negedge ck);
                rv = 0; n = n + 1;
                if (n > 4 && !a_run && a_rr && !c_run && c_rr) n = 3000;
            end
            qv = 0; fv = 0; cmds = cmds + 1;
            if (!skew) begin clean = clean + 1; if (!a_rf && !a_lf && !a_if && !c_lf && !c_if) clean_ok = clean_ok + 1; end
            if (a_rf || a_lf || a_if || c_lf || c_if) begin do_reset; while (!(a_rr && c_rr)) @(negedge ck); end
        end
        // ---- phase C: invalid boot ages
        bad_ok = 0;
        c_pl = 8'(PLB + 1); do_reset; while (!b_rr) @(negedge ck);
        pv = 16'd200; r_cal = {16'd10, 16'd10, 16'd10, pv, 112'd0}; repeat (3) @(negedge ck);
        rv = 1; @(negedge ck); rv = 0; repeat (4) @(negedge ck);
        if (b_lf) bad_ok = bad_ok + 1; else $display("PHASE_C PV_LEAD %0d > bound accepted", c_pl);
        c_pl = 8'(PL);
        for (k = 0; k < 2; k = k + 1) begin
            c_fd = (k == 0) ? 8'd0 : 8'(FDB + 1); do_reset; while (!c_rr) @(negedge ck);
            repeat (3) @(negedge ck); rv = 1; @(negedge ck); rv = 0; repeat (4) @(negedge ck);
            if (b_rf) bad_ok = bad_ok + 1; else $display("PHASE_C F_DLY %0d accepted", c_fd);
        end
        if (errs == 0 && clean > 0 && clean_ok == clean && pvs >= clean && bad_ok == 3)
            $display("KVBA_ATTN PASS PL=%0d FD=%0d mut=%0d fmut=%0d checks=%0d cmds=%0d clean=%0d", PL, FD, MUT, FMUT, checks, cmds, clean);
        else
            $display("KVBA_ATTN FAIL PL=%0d FD=%0d mut=%0d fmut=%0d checks=%0d errors=%0d cmds=%0d clean_ok=%0d/%0d start_pv=%0d invalid_caught=%0d/3",
                     PL, FD, MUT, FMUT, checks, errs, cmds, clean_ok, clean, pvs, bad_ok);
        $finish;
    end
endmodule
