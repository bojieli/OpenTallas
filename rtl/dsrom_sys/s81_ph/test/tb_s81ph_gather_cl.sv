`timescale 1ns/1ps
// tb_s81ph_gather_cl (s81-gather 2026-10-13): lockstep of the gather CLUSTER (ctrl_c/dsfd_sp_gather_c_cl.sv: 32 hardened
// 4-root leaves with SRAM roots + the control leaf) against the FLAT master ctrl_c/dsfd_sp_gather_c.sv (128 flop roots)
// on the same trunk lanes, VM control words, fld descriptors and capture done events.
//   rows      root r = 16 g + 4 k + s: the cluster's row lane equals the flat master's EVERY cycle after the stated
//             shift of c + k - 2 cycles (c = leaves passed on the row: g on the W half, 7 - g on the E half);
//   control   t_capture[6943:6784] (control lane), t_xgo, c_done, c_st: equal every cycle, no shift;
//   status    {live, busy, fault} equal at every quiet point (they arrive over a registered chain).
//   +EXPECT=0 (default) no fault anywhere.  +EXPECT=1: the capacity case: the cluster must show fault
//   (t_capture[6944]), the flat master must not, and no cluster row before the fault differs from the flat rows.
//   COVERAGE REFUSAL (+NEED=1): PASS is refused unless every one of the 128 roots returned a row, a phase word was
//   released (t_xgo), a done came back (c_done) and busy was seen.
// +STIM=<file> (gen_gather_cl_stim.py): P <phase> | C <gap> <root> <tag> <data> <e> | E
module tb_s81ph_gather_cl;
    localparam integer NR = 128;
    reg ck = 0, ckv = 0;
    always #3 ck = ~ck;     // period 6
    always #4 ckv = ~ckv;   // period 8  (1.2 / 0.9 GHz, related, as the die PLL)
    reg rst = 0, rsv = 0;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    reg [NR-1:0] s_v; reg [31:0] s_t [0:NR-1]; reg [31:0] s_d [0:NR-1]; reg [NR-1:0] s_e, s_b;
    localparam integer NC [0:5] = '{10, 11, 11, 11, 11, 10};
    reg [760:0] tp [0:11];
    reg [511:0] f_vm = 0; reg [84:0] c_cmd = 0; reg [11:0] f_cd = 0;
    `ifdef S81PH_GTH_CONTROL_STRIP
    // Exact flat semantic reference observes the same priced completion transport.
    // tc transport is checked against the flat output delayed exactly one cycle.
    reg [11:0] fcd_reference = 0;
    reg [159:0] tf_control = 0;
    always @(posedge ckv) fcd_reference <= f_cd;
    always @(posedge ck) tf_control <= tf[6943:6784];
`else
    wire [11:0] fcd_reference = f_cd;
    wire [159:0] tf_control = tf[6943:6784];
`endif
    wire [6946:0] tf, tc; wire [8:0] df, dc; wire [1:0] sf, sc; wire [10:0] xf, xc;
    dsfd_sp_gather_c u_f (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_vm(f_vm), .t_capture(tf),
        .rW0(tp[0][691:0]), .rW1(tp[1][760:0]), .rW2(tp[2][760:0]), .rW3(tp[3][760:0]), .rW4(tp[4][760:0]), .rW5(tp[5][691:0]),
        .rE0(tp[6][691:0]), .rE1(tp[7][760:0]), .rE2(tp[8][760:0]), .rE3(tp[9][760:0]), .rE4(tp[10][760:0]), .rE5(tp[11][691:0]),
        .c_cmd(c_cmd), .c_done(df), .c_st(sf), .f_cd(fcd_reference), .t_xgo(xf));
    dsfd_sp_gather_c_cl u_c (
`ifdef S81PH_GTH_CONTROL_STRIP
        .ck_r({ckv, {132{ck}}}),
`endif
`ifdef S81PH_GTH_DIE_CLOCKS
        .ck_l({32{ck}}),
`endif
        .ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_vm(f_vm), .t_capture(tc),
        .rW0(tp[0][691:0]), .rW1(tp[1][760:0]), .rW2(tp[2][760:0]), .rW3(tp[3][760:0]), .rW4(tp[4][760:0]), .rW5(tp[5][691:0]),
        .rE0(tp[6][691:0]), .rE1(tp[7][760:0]), .rE2(tp[8][760:0]), .rE3(tp[9][760:0]), .rE4(tp[10][760:0]), .rE5(tp[11][691:0]),
        .c_cmd(c_cmd), .c_done(dc), .c_st(sc), .f_cd(f_cd), .t_xgo(xc));
    function automatic integer port_of(input integer r);
        integer h, t, b;
        begin h = r / 64; b = h * 64; port_of = -1;
            for (t = 0; t < 6; t = t + 1) begin if (port_of < 0 && r < b + NC[t]) port_of = 6 * h + t; b = b + NC[t]; end end
    endfunction
    function automatic integer lane_of(input integer r);
        integer h, t, b;
        begin h = r / 64; b = h * 64; lane_of = -1;
            for (t = 0; t < 6; t = t + 1) begin if (lane_of < 0 && r < b + NC[t]) lane_of = NC[t] - 1 - (r - b); b = b + NC[t]; end end
    endfunction
    integer pi, li, rr;
    always @* begin
        for (pi = 0; pi < 12; pi = pi + 1) begin
            tp[pi] = 761'd0;
            tp[pi][69 * NC[pi % 6] +: 2] = 2'b01;           // {fault 0, live 1}
        end
        for (rr = 0; rr < NR; rr = rr + 1) begin
            pi = port_of(rr); li = lane_of(rr);
            tp[pi][69 * li] = s_v[rr];
            tp[pi][69 * li + 1 +: 68] = {1'b0, s_b[rr], s_e[rr], s_d[rr], s_t[rr], s_v[rr]};
        end
    end
    // ---------------- compare
    function automatic integer shift_of(input integer r);   // c + k (flat delayed by this, cluster by 2)
        integer g, k;
        begin g = r / 16; k = (r % 16) / 4; shift_of = ((g < 4) ? g : 7 - g) + k; end
    endfunction
    reg [52:0] hf [0:NR-1][0:7]; reg [52:0] hc [0:NR-1][0:7];
    integer k, j, expect_ = 0, need = 0;
    integer row_mism = 0, ctl_mism = 0, st_mism = 0, rows_f = 0, rows_c = 0, first_bad = -1, n_xgo = 0, n_done = 0, n_ctl = 0,
            busy_seen = 0, bad_before_fault = 0, late = 0;
    reg [NR-1:0] got = 0;
    reg armed = 0;
    reg [31:0] frow [bit [26:0]];            // flat rows by {root, pos, row}
    always @(posedge ck) begin
        for (k = 0; k < NR; k = k + 1) begin
            for (j = 7; j > 0; j = j - 1) begin hf[k][j] <= hf[k][j-1]; hc[k][j] <= hc[k][j-1]; end
            hf[k][0] <= tf[53*k +: 53]; hc[k][0] <= tc[53*k +: 53];
        end
        if (armed) begin
            for (k = 0; k < NR; k = k + 1) begin
                if (tf[53*k]) begin rows_f = rows_f + 1; frow[{k[6:0], tf[53*k + 33 +: 19], 1'b0}] = tf[53*k + 1 +: 32]; end
                if (tc[53*k]) begin
                    rows_c = rows_c + 1; got[k] = 1'b1;
                end
                // row lane {e, pos3, row16, fp32, v}: valid equal, and with valid the whole word
                if (expect_ == 0 && (hf[k][shift_of(k)][0] !== hc[k][2][0] ||
                                     (hc[k][2][0] && hf[k][shift_of(k)] !== hc[k][2]))) begin
                    row_mism = row_mism + 1; if (first_bad < 0) first_bad = cyc;
                    if (row_mism < 6) $display("ROW MISMATCH cycle %0d root %0d: flat %h cluster %h", cyc, k, hf[k][shift_of(k)], hc[k][2]);
                end
                if (expect_ == 1 && tc[53*k] && !tc[6944]) begin   // before the fault: must be a flat row (may come later there)
                    if (!frow.exists({k[6:0], tc[53*k + 33 +: 19], 1'b0})) late = late + 1;
                    else if (frow[{k[6:0], tc[53*k + 33 +: 19], 1'b0}] !== tc[53*k + 1 +: 32]) bad_before_fault = bad_before_fault + 1;
                end
            end
            if (tf_control !== tc[6943:6784] || xf !== xc || df !== dc || sf !== sc) begin
                ctl_mism = ctl_mism + 1; if (first_bad < 0) first_bad = cyc;
                if (ctl_mism < 6) $display("CTL MISMATCH cycle %0d: lane %b xgo %h/%h done %h/%h st %b/%b", cyc, tf_control !== tc[6943:6784], xf, xc, df, dc, sf, sc);
            end
            if (xc[10]) n_xgo = n_xgo + 1;
            if (dc[8]) n_done = n_done + 1;
            if (tc[6784]) n_ctl = n_ctl + 1;
            if (tc[6945]) busy_seen = 1;
        end
    end
    // ---------------- driver
    integer fd, rc, root, n_ph = 0, quiet, restart = 0;
    reg [8*8-1:0] cmd; reg [63:0] a0, a1, a2, a3, a4;
    reg [NR-1:0] n_v; reg [31:0] n_t [0:NR-1]; reg [31:0] n_d [0:NR-1]; reg [NR-1:0] n_e;
    reg [9:0] ph; reg tgl = 0;
    string stim;
    task automatic flush; begin
        for (k = 0; k < NR; k = k + 1) begin s_v[k] = n_v[k]; s_t[k] = n_t[k]; s_d[k] = n_d[k]; s_e[k] = n_e[k]; s_b[k] = $random; end
        n_v = 0; n_e = 0;
        @(negedge ck); s_v = 0;
    end endtask
    task automatic idle(input integer n); integer q; begin for (q = 0; q < n; q = q + 1) @(negedge ck); end endtask
    task automatic settle; begin        // both sides quiet for 200 cycles
        quiet = 0; j = 0;
        while (quiet < 200 && j < 300000) begin @(negedge ck); j = j + 1; quiet = ((|s_v) || (|(tf[6783:0] & {128{53'd1}})) || (|(tc[6783:0] & {128{53'd1}}))) ? 0 : quiet + 1; end
    end endtask
    task automatic status_check; begin
        // the last lane word of every root has busy 0 in the stimulus tail (flush with s_b = 0), so both settle to equal
        if (tf[6946:6944] !== tc[6946:6944] && expect_ == 0) begin st_mism = st_mism + 1; $display("STATUS MISMATCH cycle %0d: flat %b cluster %b", cyc, tf[6946:6944], tc[6946:6944]); end
    end endtask
    initial begin
        s_v = 0; s_e = 0; s_b = 0; n_v = 0; n_e = 0;
        for (k = 0; k < NR; k = k + 1) begin s_t[k] = 0; s_d[k] = 0; end
        if (!$value$plusargs("STIM=%s", stim)) $fatal(1, "+STIM");
        if (!$value$plusargs("EXPECT=%d", expect_)) expect_ = 0;
        if (!$value$plusargs("NEED=%d", need)) need = 0;
        if (!$value$plusargs("RESTART=%d", restart)) restart = 0;
        fd = $fopen(stim, "r");
        if (fd == 0) $fatal(1, "cannot open %s", stim);
        idle(10); rst = 1; rsv = 1; idle(80); armed = 1;
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%s", cmd);
            if (rc != 1) break;
            if (cmd == "P") begin
                rc = $fscanf(fd, "%h", a0); ph = a0[9:0];
                @(negedge ckv);
                f_vm = 0; f_vm[0] = 1; f_vm[159:1] = {100'd0, ph, 47'd0 + n_ph, 2'b00};
                @(negedge ckv); f_vm[0] = 0;
                idle(30);
                c_cmd = {1'b1, 1'b0, 66'd0, ph, n_ph[6:0]}; @(negedge ck); c_cmd = 0;
                idle(40);
            end else if (cmd == "C") begin
                rc = $fscanf(fd, "%h %h %h %h %h", a0, a1, a2, a3, a4);
                if (a0 != 0) begin flush; if (a0 > 1) idle(a0 - 1); end
                root = a1; n_v[root] = 1; n_t[root] = a2; n_d[root] = a3; n_e[root] = a4;
            end else if (cmd == "E") begin
                flush; settle; status_check;
                f_cd = {~tgl, 1'b0, ph}; tgl = ~tgl;            // the capture's phase-drained event
                idle(40);
                n_ph = n_ph + 1;
                if (restart && expect_ == 0 && n_ph % 2 == 0) begin
                    // Restart only at the documented drained boundary; clear both domains.
                    // Subsequent field commands/rows must still match after the priced rc6 release.
                    armed=0;rst=0;rsv=0;f_vm=0;c_cmd=0;f_cd=0;tgl=0;
                    idle(10);rst=1;rsv=1;idle(80);armed=1;
                    $display("RESTART drained boundary after phase %0d",n_ph);
                end

            end
        end
        idle(300); status_check;
        $display("SUMMARY phases=%0d rows_flat=%0d rows_cluster=%0d row_mismatch=%0d ctl_mismatch=%0d status_mismatch=%0d first=%0d roots_with_rows=%0d xgo=%0d done=%0d ctl_words=%0d busy_seen=%0d fault_flat=%b fault_cluster=%b bad_before_fault=%0d shift=c+k-2",
                 n_ph, rows_f, rows_c, row_mism, ctl_mism, st_mism, first_bad, $countones(got), n_xgo, n_done, n_ctl, busy_seen, tf[6944], tc[6944], bad_before_fault);
        if (need != 0 && !($countones(got) == NR && n_xgo == n_ph && n_done == n_ph && n_ctl >= n_ph && n_ph > 0 && busy_seen))
            $display("RESULT REFUSED coverage: roots %0d/128 xgo %0d done %0d busy %0d", $countones(got), n_xgo, n_done, busy_seen);
        else if (expect_ == 0 && row_mism == 0 && ctl_mism == 0 && st_mism == 0 && rows_f == rows_c && rows_f > 0 && !tf[6944] && !tc[6944]) $display("RESULT PASS");
        else if (expect_ == 1 && tc[6944] && !tf[6944] && bad_before_fault == 0 && ctl_mism == 0) $display("RESULT PASS");
        else $display("RESULT FAIL");
        $finish;
    end
endmodule
