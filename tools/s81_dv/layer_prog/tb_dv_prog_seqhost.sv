`timescale 1ns/1ps
// LAYERBENCH-S81 (10-18): the compiled layer programme (tools/s81_dv/dv_layer_compile.py prog/host_boot.memh) booted into
// the REAL dsdv_seq_host (p4l RTL of record) through its host lane, one host word every 5th edge (the compiler's host
// slots), then ONE job start on f_ks.  Logs every V beat (vo_s / vo_n), gunit cw word, svc job and KIT done with its edge,
// and the unit status; tools/s81_dv/layer_prog/check_seqhost.py compares them with the compiled calendar (every command
// must leave on calendar issue + one fixed offset; payload = the template; no fault).
// MU-S81/TOK (10-19): +mu=<file> (default absent = the single-user bench above, unchanged): K job starts on f_ks, one a
// line "shift user pos tok" (decimal; shift in edges after the single-user launch edge, user 0 = shift 0), each on its
// launch edge + shift (the static shift calendar, tools/s81_dv/dv_mu_calendar.py); tools/s81_dv/layer_prog/check_mu.py
// checks user 0 == the single-user run and user k == user 0 shifted by shift_k with its own context.  +drop_user (bench
// mutant): the issuer's job_user input forced to 0 (the user field dropped).  The issuer fault / fault code are logged.
module tb_dv_prog_seqhost;
    localparam integer V = 276;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    reg [V-1:0] vi_s = 0, vi_n = 0; wire [V-1:0] vo_s, vo_n;
    reg [514:0] f_host = 0; wire [76:0] t_host; reg [52:0] f_ks = 0; wire [53:0] t_kd;
    wire cw_v; wire [9:0] cw_a; wire [255:0] cw_d;
    wire [32:0] s_j; reg [1:0] s_jd_w = 0, s_jd_e = 0; wire [291:0] s_hw_w, s_hw_e; reg [8:0] s_hc_w = 0, s_hc_e = 0;
    reg [1:0] st_rg_w = 2'b01, st_rg_e = 2'b01;
    dsdv_seq_host #(.V(V)) dut (.ck(ck), .rst_n(rst_n), .tap_k(8'h00), .sink_k(8'h00), .vi_s(vi_s), .vo_s(vo_s),
        .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(4'b0101), .f_ks(f_ks), .t_kd(t_kd),
        .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e),
        .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    reg [514:0] HS [0:8191];
    reg [1023:0] dir;
    integer nhs, hsp = 0, cyc = 0, t_ks = -1, ncy, launch0 = -1;
    // MU: up to 64 job starts {shift, user, pos, tok}
    integer nmu = 0, kmu = 0, fd, rc, t_end = -1;
    integer mu_sh [0:63]; reg [9:0] mu_us [0:63]; reg [20:0] mu_ps [0:63], mu_tk [0:63];
    reg [1023:0] mufile;
    integer a0, a1, a2, a3;
    reg flt_q = 0;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) $fatal(1, "+dir required");
        if (!$value$plusargs("n=%d", nhs)) $fatal(1, "+n required");
        if (!$value$plusargs("cyc=%d", ncy)) ncy = 3000;
        $readmemh({dir, "/prog/host_boot.memh"}, HS, 0, nhs - 1);
        if ($value$plusargs("mu=%s", mufile)) begin
            fd = $fopen(mufile, "r");
            if (fd == 0) $fatal(1, "+mu file");
            while (!$feof(fd) && nmu < 64) begin
                rc = $fscanf(fd, "%d %d %d %d\n", a0, a1, a2, a3);
                if (rc == 4) begin mu_sh[nmu] = a0; mu_us[nmu] = a1[9:0]; mu_ps[nmu] = a2[20:0]; mu_tk[nmu] = a3[20:0]; nmu = nmu + 1; end
            end
            $fclose(fd);
            $display("PROG MU %0d users", nmu);
        end
        repeat (10) @(posedge ck); #0.2 rst_n = 1;
    end
    always @(posedge ck) if (rst_n) cyc <= cyc + 1;
    always @(negedge ck) if (rst_n) begin
        f_host <= 515'd0; f_ks <= 53'd0;
        if (cyc > 30 && cyc % 5 == 0 && hsp < nhs) begin f_host <= HS[hsp]; hsp = hsp + 1; end
        // the job start f_ks {v, user 10, pos 21, tok 21}: once sealed, on the calendar's start phase (ot_dsdv_fixed_issue
        // accepts job_v only when phase_q + 1 == start_phase; the same launch rule as tb_dsdv_seq_host: phase_q 0 seen
        // at edge cyc -> f_ks driven for edge cyc + 29)
        if (launch0 < 0 && hsp == nhs && dut.u_l1.u_iss.sealed && dut.u_l1.u_iss.phase_q == 2'd0 && cyc > 200)
            launch0 = cyc + 29;
        if (nmu > 0 && launch0 >= 0 && kmu < nmu && cyc + 1 == launch0 + mu_sh[kmu]) begin
            // f_ks = {start, user 10, tok 21, pos 21}
            f_ks <= {1'b1, mu_us[kmu], mu_tk[kmu], mu_ps[kmu]}; t_ks = cyc + 1;
            $display("PROG KS %0d user %0d pos %0d tok %0d shift %0d", t_ks, mu_us[kmu], mu_ps[kmu], mu_tk[kmu], mu_sh[kmu]);
            kmu = kmu + 1;
        end
        if (nmu == 0 && launch0 >= 0 && t_ks < 0 && cyc + 1 == launch0) begin
            f_ks <= {1'b1, 10'd37, 21'd1000, 21'd5000}; t_ks = cyc + 1;   // captured on the next posedge
            $display("PROG KS %0d", t_ks);
        end
    end
    always @(posedge ck) if (rst_n) begin
        if (vo_s[0]) $display("PROG VO S %0d %h", cyc, vo_s);
        if (vo_n[0]) $display("PROG VO N %0d %h", cyc, vo_n);
        if (cw_v) $display("PROG CW %0d %h %h", cyc, cw_a, cw_d);
        if (s_j[32]) $display("PROG SJ %0d %h", cyc, s_j);
        if (t_kd[53]) $display("PROG KD %0d %h", cyc, t_kd);
        if (dut.u_l1.u_iss.fault && !flt_q) $display("PROG FAULT %0d code %0d", cyc, dut.u_l1.u_iss.fault_code);
        flt_q <= dut.u_l1.u_iss.fault;
        if (t_ks >= 0 && cyc == t_ks + ncy && kmu == nmu) begin
            if (nmu > 0) $display("PROG FCODE %0d fault %0d jobs %0d", dut.u_l1.u_iss.fault_code, dut.u_l1.u_iss.fault,
                                  dut.u_l1.u_iss.st_jobs);
            $display("PROG STATUS %0d t_host %h", cyc, t_host);
            $display("PROG END");
            $finish;
        end
    end
    initial if ($test$plusargs("drop_user")) force dut.u_l1.u_iss.job_user = 10'd0;
    initial begin #2000000; $display("PROG TIMEOUT"); $finish; end
endmodule
