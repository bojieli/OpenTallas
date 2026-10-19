`timescale 1ns/1ps
// Compare three-bank23-bit expanded leaf PINREG0/1 against every expected
// explicit start across two cyclic admission/retirement epochs. The input
// fixture has8216 entries, crossing both ROM bank boundaries and time bit22.
// MUT7 corrupts pin-anchor compensation; BAD_BANK aliases bank2 to bank0.
// Both mutations must fail. EXPECTED contains time,user,stage,first,cnt,INIT.
module tb_dhuser_expanded;
    parameter integer MUT = 0;
    parameter integer SEED = 7;
    parameter integer BAD_BANK = 0;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    reg  [43:0] dh_run = 44'd0;
    wire [1:0] r_du, r_ru, d_du, d_ru; wire r_mf, d_mf;
    wire r_v, d_v, r_ff, d_ff; wire [1:0] r_u, d_u; wire [5:0] r_s, d_s; wire [9:0] r_f, d_f, r_c, d_c;
    wire [3:0] r_fc, d_fc;
    qfd_sys_face_mu_dhuser #(.NU(4), .OPSEG(1), .EXPANDED(1), .INSTANCE1("qfd_tt_ctlm_opseg_b1"), .INSTANCE2(BAD_BANK ? "qfd_tt_ctlm_opseg" : "qfd_tt_ctlm_opseg_b2"), .LAST_STAGE(37), .INSTANCE("qfd_tt_ctlm_opseg"), .PINREG(0), .MUT(0))
        u_ref (.ck(ck), .rst_n(rst_n), .dh_run(dh_run), .dh_user(r_du), .res_user(r_ru), .mu_fault(r_mf), .op_v(r_v),
               .op_user(r_u), .op_stage(r_s), .op_first(r_f), .op_cnt(r_c), .op_ff(r_ff), .op_fcode(r_fc));
    qfd_sys_face_mu_dhuser #(.NU(4), .OPSEG(1), .EXPANDED(1), .INSTANCE1("qfd_tt_ctlm_opseg_b1"), .INSTANCE2(BAD_BANK ? "qfd_tt_ctlm_opseg" : "qfd_tt_ctlm_opseg_b2"), .LAST_STAGE(37), .INSTANCE("qfd_tt_ctlm_opseg"), .PINREG(1), .MUT(MUT))
        u_dut (.ck(ck), .rst_n(rst_n), .dh_run(dh_run), .dh_user(d_du), .res_user(d_ru), .mu_fault(d_mf), .op_v(d_v),
               .op_user(d_u), .op_stage(d_s), .op_first(d_f), .op_cnt(d_c), .op_ff(d_ff), .op_fcode(d_fc));
    integer seed, T, H, anchor, cyc, nend, mism, first_mism, starts, k, drift, drift_at, drift_seen, ri;
    integer per_u [0:3];
    integer et [0:12287], eu [0:12287], es [0:12287], ef [0:12287], ec [0:12287], eff [0:12287];
    integer expected_n, fd, scan, expect_i, row, phase;
    string expected_path;
    reg [3:0] r_fc_q, d_fc_q;
    reg [43:0] nx;
    initial begin
        expected_n = 0;
        if (!$value$plusargs("EXPECTED=%s",expected_path)) $fatal(1,"missing EXPECTED");
        fd = $fopen(expected_path,"r");
        if (!fd) $fatal(1,"cannot read EXPECTED");
        while (!$feof(fd)) begin
            scan = $fscanf(fd,"%d %d %d %d %d %d\n",et[expected_n],eu[expected_n],es[expected_n],ef[expected_n],ec[expected_n],eff[expected_n]);
            if (scan == 6) expected_n = expected_n+1;
        end
        $fclose(fd);
        expect_i = 0;
        seed = SEED; mism = 0; first_mism = -1; starts = 0; drift = 0; drift_seen = -1; r_fc_q = 4'd0; d_fc_q = 4'd0;
        for (k = 0; k < 4; k = k + 1) per_u[k] = 0;
        if ($test$plusargs("DRIFT")) drift = 1;
        repeat (3) @(posedge ck);
        #0.1 rst_n = 1;
        cyc = 0;
        while (u_ref.g_op.bst != 2'd2 && cyc < 100) begin @(posedge ck); cyc = cyc + 1; end
        if (u_ref.g_op.bst != 2'd2) begin $display("TB_DHUSER_EXPANDED FAIL MUT=%0d header never good", MUT); $finish; end
        T = u_ref.g_op.tm1 + 1; H = u_ref.g_op.hm1 + 1;
        anchor = cyc + 20 + ($urandom(seed) % 200);
        drift_at = anchor + H + 3 * T;              // frame 1: the 4th L0 start one edge late
        nend = anchor + 2 * H + 40000;
        $display("TB_DHUSER_EXPANDED info T=%0d H=%0d anchor=%0d end=%0d drift=%0d", T, H, anchor, nend, drift);
        while (cyc < nend) begin
            // drive the next edge's dh_run (changes away from the sampling edge)
            #0.25;
            nx = {$urandom, $urandom};
            nx[42] = 1'b0;
            if (cyc >= anchor && ((cyc - anchor) % T == 0) && !(drift && cyc == drift_at)) begin
                nx[42] = 1'b1; nx[41:36] = 6'd1;
            end else if (drift && cyc == drift_at + 1) begin
                nx[42] = 1'b1; nx[41:36] = 6'd1;
            end else if (($urandom % 16) == 0) begin
                nx[42] = 1'b1; nx[41:36] = 6'd2 + 6'($urandom % 36);
            end
            dh_run = nx;
            @(posedge ck); #0.1;
            cyc = cyc + 1;
            if ({r_v, r_u, r_s, r_f, r_c, r_ff, r_fc[3:2], r_fc[0]} !== {d_v, d_u, d_s, d_f, d_c, d_ff, d_fc[3:2], d_fc[0]} ||
                d_fc[1] !== r_fc_q[1] || d_mf !== |d_fc_q ||
                {r_du, r_ru, d_du, d_ru} !== 8'd0) begin
                mism = mism + 1;
                if (first_mism < 0) begin
                    first_mism = cyc;
                    $display("TB_DHUSER_EXPANDED mismatch edge %0d ref v%0d u%0d s%0d f%0d c%0d fc%h | dut v%0d u%0d s%0d f%0d c%0d fc%h | fc_q r%h d%h mf d%0d",
                             cyc, r_v, r_u, r_s, r_f, r_c, r_fc, d_v, d_u, d_s, d_f, d_c, d_fc, r_fc_q, d_fc_q, d_mf);
                end
            end
            r_fc_q = r_fc; d_fc_q = d_fc;
            if (r_v) begin
                row = expect_i % expected_n; phase = expect_i / expected_n;
                if (cyc-anchor != et[row]+phase*H || r_u != eu[row] || r_s != es[row] ||
                    r_f != ef[row] || r_c != ec[row] || r_ff != eff[row]) begin
                    mism = mism+1;
                    if (first_mism < 0) begin
                        first_mism = cyc;
                        $display("EXPANDED_TIMELINE_MISMATCH cyc=%0d relative=%0d want=%0d row=%0d fields=%0d/%0d/%0d/%0d/%0d expected=%0d/%0d/%0d/%0d/%0d",
                            cyc,cyc-anchor,et[row]+phase*H,row,r_u,r_s,r_f,r_c,r_ff,eu[row],es[row],ef[row],ec[row],eff[row]);
                    end
                end
                expect_i = expect_i+1; starts = starts+1; per_u[r_u] = per_u[r_u]+1;
            end
            if (drift_seen < 0 && r_fc[1]) drift_seen = cyc;
            #0.15;
        end
        if (mism == 0 && starts == 2*expected_n && (drift ? (r_fc == 4'b0010 && drift_seen > 0) : (r_fc == 4'd0)))
            $display("TB_DHUSER_EXPANDED PASS MUT=%0d drift=%0d edges=%0d starts=%0d per_user=%0d/%0d/%0d mism=0 ref_fcode=%h dut_fcode=%h drift_edge=%0d",
                     MUT, drift, cyc, starts, per_u[1], per_u[2], per_u[3], r_fc, d_fc, drift_seen);
        else
            $display("TB_DHUSER_EXPANDED FAIL MUT=%0d drift=%0d edges=%0d starts=%0d per_user=%0d/%0d/%0d mism=%0d first=%0d ref_fcode=%h dut_fcode=%h drift_edge=%0d",
                     MUT, drift, cyc, starts, per_u[1], per_u[2], per_u[3], mism, first_mism, r_fc, d_fc, drift_seen);
        $finish;
    end
endmodule
