`timescale 1ns/1ps
// HARD-S81-SVC-1 (11-13) service cut lock-step: dsdv_svc_att (f) vs dsdv_svc_att_cut (c) and its two negative controls
// (CUTMUT 1: hw lane not captured; CUTMUT 2: pv_o lane not registered), same random frame stream / PC responses / warm
// resets as tb_svc_att_mem.  The cut copy gets the page-cache responses and the reset one edge later (the PC stages and
// the reset epoch belong to the attention part).  Every cycle: c.qrq == f.qrq one edge earlier, every other output of c
// == f two edges earlier.  The controls must differ.
module tb_svc_att_cut;
    parameter integer NCYC = 200000;
    integer SEED = 1;
    localparam integer H = 8;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0, err = 0, err_mm = 0, chk = 0, nrst = 0, first_err = -1, first_mm = -1;
    reg [31:0] rng;
    function automatic [31:0] rnd(); rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5); rnd = rng; endfunction
    // stimulus
    reg q_v = 0; reg [511:0] q_d = 0; reg hw_v = 0; reg [290:0] hw_d = 0;
    reg [1:0] qrk = 0, qwd = 0, qrv = 0; reg [511:0] qr_data = 0; reg [33:0] qr_tag = 0; reg [7:0] qr_beat = 0;
    integer left = 0, gap = 0, wr_left = 0, k;
    reg [3:0] ftype;
    function automatic [3:0] pick_type();
        integer r; r = rnd() % 100;
        if (r < 25) pick_type = 4'd7; else if (r < 40) pick_type = 4'd5; else if (r < 55) pick_type = 4'd1;
        else if (r < 62) pick_type = 4'd12; else if (r < 70) pick_type = 4'd13; else if (r < 80) pick_type = 4'd2;
        else if (r < 88) pick_type = 4'd3; else pick_type = 4'(rnd());
    endfunction
    always @(negedge clk) begin
        q_v = 0;
        if (gap > 0) gap = gap - 1;
        else if (left > 0) begin
            q_v = 1; for (k = 0; k < 16; k++) q_d[32*k +: 32] = rnd();
            if (rnd() % 4 == 0) q_d[31:0] = rnd() % 64;            // small fields (counts / indices / ranks)
            left = left - 1; if (rnd() % 8 == 0) gap = rnd() % 3;
        end else if (rnd() % 3 != 0) begin
            q_v = 1; for (k = 0; k < 16; k++) q_d[32*k +: 32] = rnd();
            ftype = pick_type();
            q_d[511:508] = ftype; q_d[506:503] = (rnd() % 8 == 0) ? 4'(rnd()) : 4'b0001;
            left = (ftype == 4'd7 || ftype == 4'd5) ? 1 + rnd() % 40 : (ftype == 4'd1) ? H : rnd() % 12;
            q_d[491:480] = 12'(left);
            q_d[88:81] = 8'(rnd() % 32); q_d[98:89] = 10'(rnd() % 64);     // WIN_LOAD wcount / nsel small
            gap = rnd() % 2;
        end
        hw_v = rnd() % 16 == 0; hw_d = {rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), rnd(), 3'(rnd())};
        qrk = 2'(rnd()); qwd = 2'(rnd() % 4 == 0 ? rnd() : 0); qrv = 2'(rnd() % 2 ? rnd() : 0);
        for (k = 0; k < 16; k++) qr_data[32*k +: 32] = rnd();
        qr_tag = {2'(rnd()), 32'(rnd() % 1024)}; qr_beat = 8'(rnd() % 4);
        // warm reset mid-stream (1..80 cycles), state non-zero
        if (cyc == 5) rst_n = 1;
        if (cyc > 50) begin
            if (wr_left > 0) begin wr_left = wr_left - 1; if (wr_left == 0) rst_n = 1; end
            else if (rnd() % 3000 == 0) begin rst_n = 0; wr_left = 1 + rnd() % 80; nrst = nrst + 1; left = 0; end
        end
    end
`define ATT_PORTS(P) \
        .clk(clk), .rst_n(rst_n), .sid(4'd3), .tile(4'd5), .gd(8'd17), .pvs(10'd40), .root(1'b0), \
        .q_v(q_v), .q_d(q_d), .hw_v(hw_v), .hw_d(hw_d), .qrq(P``_qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), \
        .qr_tag(qr_tag), .qr_beat(qr_beat), .l_v(P``_l_v), .l_d(P``_l_d), .pv_ov(P``_pv_ov), .pv_od(P``_pv_od), \
        .sm_st(P``_o[0]), .sm_kind(P``_o[4:1]), .sm_jid(P``_o[12:5]), .sm_rv(P``_o[13]), .sm_rp(P``_o[14]), .sm_rj(P``_o[17:15]), \
        .sm_rd(P``_sm_rd), .go_o(P``_o[18]), .tjob_o(P``_o[28:19]), .done(P``_o[29]), .tagj(P``_o[37:30]), .hcr(P``_o[39:38]), \
        .hack(P``_o[41:40]), .fault(P``_o[42]), .fault_code(P``_fc), .pio_o(P``_x[15:0]), .pvo_o(P``_x[31:16]), .jc_o(P``_x[47:32]), \
        .st_o(P``_x[49:48]), .allq_o(P``_x[50]), .hb_o(P``_x[51])
`define ATT_PORTS_C(P) \
        .clk(clk), .rst_n(rst_c), .sid(4'd3), .tile(4'd5), .gd(8'd17), .pvs(10'd40), .root(1'b0), \
        .q_v(q_v), .q_d(q_d), .hw_v(hw_v), .hw_d(hw_d), .qrq(P``_qrq), .qrk(qrk_c), .qwd(qwd_c), .qrv(qrv_c), .qr_data(qr_data_c), \
        .qr_tag(qr_tag_c), .qr_beat(qr_beat_c), .l_v(P``_l_v), .l_d(P``_l_d), .pv_ov(P``_pv_ov), .pv_od(P``_pv_od), \
        .sm_st(P``_o[0]), .sm_kind(P``_o[4:1]), .sm_jid(P``_o[12:5]), .sm_rv(P``_o[13]), .sm_rp(P``_o[14]), .sm_rj(P``_o[17:15]), \
        .sm_rd(P``_sm_rd), .go_o(P``_o[18]), .tjob_o(P``_o[28:19]), .done(P``_o[29]), .tagj(P``_o[37:30]), .hcr(P``_o[39:38]), \
        .hack(P``_o[41:40]), .fault(P``_o[42]), .fault_code(P``_fc), .pio_o(P``_x[15:0]), .pvo_o(P``_x[31:16]), .jc_o(P``_x[47:32]), \
        .st_o(P``_x[49:48]), .allq_o(P``_x[50]), .hb_o(P``_x[51])
`define ATT_WIRES(P) \
    wire [681:0] P``_qrq; wire P``_l_v; wire [H*132+19:0] P``_l_d; wire P``_pv_ov; wire [512:0] P``_pv_od; wire [42:0] P``_o; \
    wire [511:0] P``_sm_rd; wire [31:0] P``_fc; wire [51:0] P``_x; \
    wire [681+1+H*132+20+1+513+43+512+32+52-1:0] P``_all = {P``_qrq, P``_l_v, P``_l_d, P``_pv_ov, P``_pv_od, P``_o, P``_sm_rd, P``_fc, P``_x};
    `ATT_WIRES(f)
    `ATT_WIRES(c)
    `ATT_WIRES(m1)
    `ATT_WIRES(m2)
    // the cut copies see the page-cache responses and the reset one edge later
    reg rst_c = 0; reg [1:0] qrk_c = 0, qwd_c = 0, qrv_c = 0; reg [511:0] qr_data_c = 0; reg [33:0] qr_tag_c = 0; reg [7:0] qr_beat_c = 0;
    always @(posedge clk) begin
        rst_c <= rst_n; qrk_c <= qrk; qwd_c <= qwd; qrv_c <= qrv; qr_data_c <= qr_data; qr_tag_c <= qr_tag; qr_beat_c <= qr_beat;
    end
    dsdv_svc_att     #(.H(H), .SRAM_MACRO(1), .PV_IDENTITY(1)) u_f (`ATT_PORTS(f));
    dsdv_svc_att_cut #(.H(H), .SRAM_MACRO(1), .PV_IDENTITY(1)) u_c (`ATT_PORTS_C(c));
    dsdv_svc_att_cut #(.H(H), .SRAM_MACRO(1), .PV_IDENTITY(1), .CUTMUT(1)) u_m1 (`ATT_PORTS_C(m1));
    dsdv_svc_att_cut #(.H(H), .SRAM_MACRO(1), .PV_IDENTITY(1), .CUTMUT(2)) u_m2 (`ATT_PORTS_C(m2));
    initial begin if ($value$plusargs("seed=%d", SEED)) ; rng = 32'h9E37_79B9 ^ SEED; end
    localparam integer AW = 681 + 1 + H*132 + 20 + 1 + 513 + 43 + 512 + 32 + 52;   // = the ATT_WIRES _all width (qrq[681] is not in it)
    localparam integer RW = AW - 681;                 // everything below qrq
    reg [AW-1:0] f_d1 = 0, f_d2 = 0;
    reg [2:0] rdy = 0;                                // edges since the last reset activity (both copies released)
    integer nf = 0, nsel = 0, nq = 0, npv = 0, nl = 0, err_m1 = 0, err_m2 = 0;
    wire c_ok  = (c_all[AW-1:RW]  === f_d1[AW-1:RW]) && (c_all[RW-1:0]  === f_d2[RW-1:0]);
    wire m1_ok = (m1_all[AW-1:RW] === f_d1[AW-1:RW]) && (m1_all[RW-1:0] === f_d2[RW-1:0]);
    wire m2_ok = (m2_all[AW-1:RW] === f_d1[AW-1:RW]) && (m2_all[RW-1:0] === f_d2[RW-1:0]);
    always @(posedge clk) begin
        cyc <= cyc + 1;
        f_d1 <= f_all; f_d2 <= f_d1;
        if (q_v && q_d[511:508] == 4'd7) nsel = nsel + 1;
        if (cyc > 12) begin
            chk = chk + 1;
            if (!c_ok) begin err = err + 1; if (first_err < 0) first_err = cyc; end
            if (!m1_ok) err_m1 = err_m1 + 1;
            if (!m2_ok) err_m2 = err_m2 + 1;
            if (f_o[42]) nf = nf + 1;
            if (f_qrq != 0) nq = nq + 1;
            if (f_pv_ov) npv = npv + 1;
            if (f_l_v) nl = nl + 1;
        end
        if (cyc == NCYC) begin
            $display("ATT_CUT seed=%0d checks=%0d warm_resets=%0d sel_hdr=%0d f_fault_cycles=%0d qrq_cycles=%0d pv_beats=%0d score_beats=%0d", SEED, chk, nrst, nsel, nf, nq, npv, nl);
            $display("%s cut form vs as built (qrq +1, other lanes +2): mismatching cycles=%0d first=%0d", err == 0 ? "PASS" : "FAIL", err, first_err);
            $display("%s CUTMUT 1 (hw lane not captured): mismatching cycles=%0d", err_m1 != 0 ? "CAUGHT" : "MISSED", err_m1);
            $display("%s CUTMUT 2 (pv_o lane not registered): mismatching cycles=%0d", err_m2 != 0 ? "CAUGHT" : "MISSED", err_m2);
            $finish;
        end
    end
endmodule
