`timescale 1ns/1ps
// QW-F16SUB 10-19: CALR port check.  The CALPIPE/FIREDQ calendar (rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv, CTLM3/CTLM4) with the
// ported CALENDAR_ROM / TABLE_ROM options against the QW-F16PROG4 reference calendar (qfd_dv_cmd_cal_mu_f16ref, the
// module the F16 table-join bench validated), both NU 4 / CTX_DW / UFOLD / CALENDAR_ROM / TABLE_ROM, each with its own
// real two-ROM calendar (same CALR10 image from finite_calendar_body.py).  Every output compared on every edge:
// descriptor segments for 4 overlapping users (boot, mid stages, LAST), explicit ranges (cnt 1 / 4), a start for a
// playing user (fault path).  MUT (port only): passed to the ported calendar.
module tb_qfd_dv_cmd_cal_mu_calr_port #(parameter integer MUT = 0);
    reg ck = 0; always #5 ck = ~ck;
    reg rst_n = 0, start = 0, start_rng = 0; reg [5:0] stage = 0; reg [1:0] uid = 0; reg [9:0] sfirst = 0, scnt = 0;
    reg pw_v = 0, dw_v = 0; reg [9:0] pw_addr = 0; reg [2:0] dw_addr = 0; reg [63:0] dw_data = 0;
    reg [63:0] dw_image [0:7]; reg [9:0] preload_first [0:35];
`define OUTS(p) wire [115:0] p``cmd; wire [1:0] p``cu, p``du, p``tu; wire p``le, p``ls, p``si, p``xi, p``tlv, p``ir, p``run, p``dn, p``f, p``cl; \
    wire [11:0] p``lb; wire [8:0] p``sp; wire [5:0] p``ts, p``fc; wire [1087:0] p``tl; wire [75:0] p``po; wire [68:0] p``do; \
    wire [3:0] p``ru; wire [127:0] p``cd;
    `OUTS(a_)
    `OUTS(b_)
`define PORTS(p) .ck(ck), .rst_n(rst_n), .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(64'd0), .dw_v(dw_v), .dw_addr(dw_addr), \
    .dw_data(dw_data), .start(start), .stage(stage), .start_user(uid), .start_rng(start_rng), .start_first(sfirst), \
    .start_cnt(scnt), .cmd(p``cmd), .cmd_user(p``cu), .loc_emb(p``le), .loc_seg(p``ls), .loc_base(p``lb), .su_issue(p``si), \
    .su_pidx(p``sp), .xc_issue(p``xi), .table_load(p``tlv), .table_stage(p``ts), .table_user(p``tu), .tl(p``tl), \
    .program_obs(p``po), .descriptor_obs(p``do), .image_ready(p``ir), .running(p``run), .running_u(p``ru), .done(p``dn), \
    .done_user(p``du), .fault(p``f), .fault_code(p``fc), .ctx_dw(p``cd), .ctx_load(p``cl)
    qfd_dv_cmd_cal_mu #(.MUT(MUT), .NU(4), .CTX_DW(1), .UFOLD(1), .CALENDAR_ROM(1), .TABLE_ROM(1), .UVM_STRIDE(4096),
        .PIDX_STRIDE(128)) dut (`PORTS(a_));
    qfd_dv_cmd_cal_mu_f16ref #(.NU(4), .CTX_DW(1), .UFOLD(1), .CALENDAR_ROM(1), .TABLE_ROM(1), .UVM_STRIDE(4096),
        .PIDX_STRIDE(128)) ref0 (`PORTS(b_));
    wire [1500:0] va = {a_cmd, a_cu, a_le, a_ls, a_lb, a_si, a_sp, a_xi, a_tlv, a_ts, a_tu, a_ir, a_run, a_ru, a_dn, a_du, a_f, a_fc, a_cd, a_cl};
    wire [1500:0] vb = {b_cmd, b_cu, b_le, b_ls, b_lb, b_si, b_sp, b_xi, b_tlv, b_ts, b_tu, b_ir, b_run, b_ru, b_dn, b_du, b_f, b_fc, b_cd, b_cl};
    integer cyc = 0, mism = 0, ncmd = 0, ntab = 0, ndone = 0, k, r, u;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        #1;
        if (rst_n) begin
            if (va !== vb || a_tl !== b_tl) begin
                mism = mism + 1;
                if (mism <= 5) $display("CALR_PORT_EDGE_MISMATCH cyc=%0d port cmd=%h u=%0d tl=%0d f=%0d fc=%b run=%b | ref cmd=%h u=%0d tl=%0d f=%0d fc=%b run=%b",
                    cyc, a_cmd, a_cu, a_tlv, a_f, a_fc, a_ru, b_cmd, b_cu, b_tlv, b_f, b_fc, b_ru);
            end
            if (b_cmd != 0 || b_le || b_ls) ncmd = ncmd + 1;
            if (b_tlv) ntab = ntab + 1;
            if (b_dn) ndone = ndone + 1;
        end
    end
    task automatic go(input [1:0] uu, input [5:0] st, input rng, input [9:0] f, input [9:0] c);
        begin @(negedge ck); uid = uu; stage = st; start_rng = rng; sfirst = f; scnt = c; start = 1; @(negedge ck); start = 0; start_rng = 0; end
    endtask
    task automatic idle_wait(input [1:0] uu);
        integer w; begin w = 0; while (a_ru[uu] && w < 200000) begin @(negedge ck); w = w + 1; end end
    endtask
    initial begin
        $readmemh("rtl/test/qwen_dv/calr_port/dw.hex", dw_image);
        $readmemh("rtl/test/qwen_dv/calr_port/preload_first.hex", preload_first);
        repeat (4) @(negedge ck); rst_n = 1; repeat (5) @(negedge ck);
        for (k = 0; k < 1024; k++) begin pw_v = 1; pw_addr = k; @(negedge ck); end
        pw_v = 0;
        for (k = 0; k < 8; k++) begin dw_v = 1; dw_addr = k; dw_data = dw_image[k]; @(negedge ck); end
        dw_v = 0; repeat (40) @(negedge ck);
        if (!b_ir) $display("CALR_PORT_NOTE ref image not ready after seal (fault=%0d fc=%b)", b_f, b_fc);
        idle_wait(0);
        // four overlapping users on descriptor segments: mid stage, LAST, stage 0
        for (r = 0; r < 3; r = r + 1)
            for (u = 0; u < 4; u = u + 1) begin
                idle_wait(u[1:0]);
                go(u[1:0], (r == 0) ? 6'd5 : (r == 1) ? 6'd37 : 6'd0, 0, 0, 0);
                repeat (37 + 11 * u) @(negedge ck);
            end
        for (u = 0; u < 4; u = u + 1) idle_wait(u[1:0]);
        // explicit ranges: the table-load preloads (cnt 1) of every stage for every user, and 4-entry rows
        for (r = 0; r < 36; r = r + 1)
            for (u = 0; u < 4; u = u + 1) begin
                idle_wait(u[1:0]);
                go(u[1:0], 6'(r + 1), 1, preload_first[r], 10'd1);
                repeat (3) @(negedge ck);
            end
        for (u = 0; u < 4; u = u + 1) idle_wait(u[1:0]);
        for (u = 0; u < 4; u = u + 1) begin go(u[1:0], 6'd3, 1, 10'(68 + 8 * u), 10'd4); repeat (2) @(negedge ck); end
        // a start for a playing user (fault path, both)
        go(2'd1, 6'd5, 0, 0, 0); repeat (5) @(negedge ck); go(2'd1, 6'd5, 0, 0, 0);
        repeat (3000) @(negedge ck);
        $display("CALR_PORT_SUMMARY mut=%0d edges=%0d mismatched_edges=%0d issued=%0d table_loads=%0d done=%0d ref_fault=%0d port_fault=%0d",
            MUT, cyc, mism, ncmd, ntab, ndone, b_f, a_f);
        if (mism == 0 && ncmd > 100 && ntab > 0) $display("CALR_PORT_PASS");
        else $display("CALR_PORT_FAIL");
        $finish;
    end
    initial begin repeat (3000000) @(posedge ck); $display("CALR_PORT_TIMEOUT"); $finish; end
endmodule
