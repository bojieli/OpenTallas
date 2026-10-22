`timescale 1ns/1ps
// QW-TLPROD 10-20: unit bench of the TABLE_REL table-load producer in qfd_dv_cmd_cal_mu (NU 4, CTX_DW, UFOLD, CALENDAR_ROM,
// TABLE_ROM = the CTLM u_cal configuration).  The produced CALR10 image (+OT_ROM_DIR: calendar_m0/m1 + dw.hex, from
// tools/qwen_layerbench/calr_table_producer.py) is installed; then for every stage 1..36 user 0 starts the stage from the
// decode DESCRIPTOR (= the face's dh start) and users 1..3 start it as an explicit RANGE over the decode entries (= the
// OPSEG leaf's filler start of the layer's first op group).  Checks: every table_load carries the stage its playhead was
// started on and the playhead's user, exactly 36 per user (144), one fixed issue latency from the start, no fault.
// MUT 35 (drop the stage-17 REL load): 140 loads -> FAIL.
module tb_qfd_dv_cmd_cal_mu_calr_rel #(parameter integer MUT = 0);
    reg ck = 0; always #5 ck = ~ck;
    reg rst_n = 0, start = 0, start_rng = 0; reg [5:0] stage = 0; reg [1:0] uid = 0; reg [9:0] sfirst = 0, scnt = 0;
    reg pw_v = 0, dw_v = 0; reg [9:0] pw_addr = 0; reg [2:0] dw_addr = 0; reg [63:0] dw_data = 0;
    reg [63:0] dw_image [0:7];
    wire [115:0] cmd; wire [1:0] cu, du, tu; wire le, ls, si, xi, tlv, ir, run, dn, f, cl;
    wire [11:0] lb; wire [8:0] sp; wire [5:0] ts, fc; wire [1087:0] tl; wire [75:0] po; wire [68:0] dob; wire [3:0] ru; wire [127:0] cd;
    qfd_dv_cmd_cal_mu #(.MUT(MUT), .NU(4), .CTX_DW(1), .UFOLD(1), .CALENDAR_ROM(1), .TABLE_ROM(1), .UVM_STRIDE(4096),
        .PIDX_STRIDE(128)) dut (.ck(ck), .rst_n(rst_n), .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(64'd0), .dw_v(dw_v),
        .dw_addr(dw_addr), .dw_data(dw_data), .start(start), .stage(stage), .start_user(uid), .start_rng(start_rng),
        .start_first(sfirst), .start_cnt(scnt), .cmd(cmd), .cmd_user(cu), .loc_emb(le), .loc_seg(ls), .loc_base(lb),
        .su_issue(si), .su_pidx(sp), .xc_issue(xi), .table_load(tlv), .table_stage(ts), .table_user(tu), .tl(tl),
        .program_obs(po), .descriptor_obs(dob), .image_ready(ir), .running(run), .running_u(ru), .done(dn),
        .done_user(du), .fault(f), .fault_code(fc), .ctx_dw(cd), .ctx_load(cl));
    integer cyc = 0, k, s, u, nload = 0, nbad = 0, lat0 = -1, st_cyc = 0;
    integer nu_load [0:3];
    reg [5:0] cur_stage = 0; reg [1:0] cur_user = 0;
    string dir;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        #1;
        if (rst_n && tlv) begin
            if (ts != cur_stage || tu != cur_user || (lat0 >= 0 && cyc - st_cyc != lat0)) begin
                nbad = nbad + 1;
                if (nbad <= 5) $display("CALR_REL_BAD cyc=%0d stage=%0d user=%0d (playing %0d/%0d) lat=%0d first_lat=%0d", cyc, ts, tu, cur_stage, cur_user, cyc - st_cyc, lat0);
            end
            if (lat0 < 0) lat0 = cyc - st_cyc;
            nload = nload + 1; nu_load[tu] = nu_load[tu] + 1;
        end
    end
    task automatic go(input [1:0] uu, input [5:0] st, input rng, input [9:0] fr, input [9:0] c);
        begin @(negedge ck); uid = uu; stage = st; start_rng = rng; sfirst = fr; scnt = c; start = 1;
              cur_stage = st; cur_user = uu; st_cyc = cyc; @(negedge ck); start = 0; start_rng = 0; end
    endtask
    task automatic idle_wait(input [1:0] uu);
        integer w; begin w = 0; @(negedge ck); while (ru[uu] && w < 200000) begin @(negedge ck); w = w + 1; end end
    endtask
    initial begin
        for (u = 0; u < 4; u = u + 1) nu_load[u] = 0;
        if (!$value$plusargs("OT_ROM_DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/dw.hex"}, dw_image);
        repeat (4) @(negedge ck); rst_n = 1; repeat (5) @(negedge ck);
        for (k = 0; k < 1024; k++) begin pw_v = 1; pw_addr = k; @(negedge ck); end
        pw_v = 0;
        for (k = 0; k < 8; k++) begin dw_v = 1; dw_addr = k; dw_data = dw_image[k]; @(negedge ck); end
        dw_v = 0; repeat (40) @(negedge ck);
        if (!ir) $display("CALR_REL_NOTE image not ready after seal (fault=%0d fc=%b)", f, fc);
        idle_wait(0);
        for (s = 1; s <= 36; s = s + 1)
            for (u = 0; u < 4; u = u + 1) begin
                if (u == 0) go(2'd0, 6'(s), 0, 0, 0);
                else go(u[1:0], 6'(s), 1, dw_image[2][25:16], dw_image[2][9:0]);
                idle_wait(u[1:0]);
                repeat (4) @(negedge ck);
            end
        repeat (50) @(negedge ck);
        $display("CALR_REL_SUMMARY mut=%0d cycles=%0d loads=%0d u0=%0d u1=%0d u2=%0d u3=%0d bad=%0d latency=%0d fault=%0d fc=%b",
            MUT, cyc, nload, nu_load[0], nu_load[1], nu_load[2], nu_load[3], nbad, lat0, f, fc);
        if (nload == 144 && nbad == 0 && !f && nu_load[0] == 36 && nu_load[1] == 36 && nu_load[2] == 36 && nu_load[3] == 36)
            $display("CALR_REL_PASS");
        else $display("CALR_REL_FAIL");
        $finish;
    end
    initial begin repeat (3000000) @(posedge ck); $display("CALR_REL_TIMEOUT"); $finish; end
endmodule
