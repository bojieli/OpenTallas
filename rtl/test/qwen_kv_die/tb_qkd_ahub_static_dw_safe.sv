`timescale 1ns/1ps
// HKV-AHUB5 2026-10-19: tb_qkd_ahub_static_dw at the KV DIE's FULL binding: Z_IN_STRIDE 4 AND the actual post-station
// offsets the die binds (HKV-DIE3 593596f40, OT_KV_AHUB_OFS; kv_static_params ahub_ages of the kvs14p-fa7fe4ff9 netlist
// table, results/rtl/qwen_kv_die/hkv_die2_1019/static_params_fa7fe4ff9_netlist_vs_90dedf84f_model.json):
//   relays D(ks_ahs) 46, D(ks_ahfr) 0, D(ks_pvfst) 40, D(ap_WS/WN/ES/EN) 8/8/10/9, root PV_LEAD 0
//   -> AP_OFS_s = 2 + D(ap_s) - D(hs) = [-36, -36, -34, -35], FR_OFS = D(pvfst) - PV_LEAD - D(fr) - D(hs) - 1 = -7.
// Calendars = HKV-DIE3 kv_static_programme.attention_calendar(T, profile('die'), service_end 1779) under
// OT_KV_ASTK_EXPAND=1 and the BOUND FR_OFS -7 (one attention calendar for hub export + pvfin join; R stretched to the
// link slot, legal at the F3 qkd_pv_fin_s b6d08acc2 = origin/main 2f79e9b59 that joins on max(P0, P1, R)).  Every hub
// field and R are the compiled values; P0 / P1 are compiled too EXCEPT at T 1 / 128 where the compiled pair skew 32 > the
// die's pvfin SKEW 1 (HKV-DIE3 ATTN_CALENDAR PVFIN_PAIR_SKEW: pair-hardware finding, outside this hub): there P1 := P0.
// Structure as tb_qkd_ahub_static_dw_s4 (ACTUAL root -> die relays -> DUT -> relays -> ACTUAL pvfin, lockstep against the
// sealed ot_qkd_ahub_static_die_cal at stride 4).
// MUT: 1..4 = the DUT's own negative controls; 5 = DUT at stride 16 (the a3 kit); 6 / 7 = slot_h / slot_k decode +1 (sed
// copy); 8 = DUT at the RTL default offsets {4{2}} / 0 (the a4 kit) against this die; 9 = DUT FR_OFS + 1; 10 = DUT
// AP_OFS[ES] + 1; 11 = DUT tree-select relay bypassed (DUT MUT 5); 12 = DUT W-face export relay bypassed (DUT MUT 6).
// All must FAIL.
// KV-AHUB7 10-19 (COORD 17:00, a7): the DUT has one registered relay stage on each > 405 um leg (tree select RS 1,
// reciprocal y RY 2, W-face export WF 1): its reciprocal loop is R_ISSUE + 71 (was + 69), so the compiled HUB_PUB law
// is HUB_RECIP + 75 (attn_calendar.hub pub = recip + 67 + 2 + 2 + 4; was + 73).  Every calendar below is the HKV-DIE3
// one with HUB_PUB + 2; PV_START / R are unchanged at every T (EXP binds PV_START: pub + RZ_MARGIN - max(P) stays below
// it by >= 6 edges), so the service end and fr's R slot do not move.  The reference sealed hub runs RX_RLY 2 / RY_RLY 2
// (the same loop latency).
module tb_qkd_ahub_static_dw_safe;
    parameter integer MUT = 0;
    localparam integer ZS = 4;                                   // the die's Z_IN_STRIDE (kv_static_die ASTK_Z_STRIDE)
    localparam integer DUT_ZS = (MUT == 5) ? 16 : ZS;
    localparam integer DUT_MUT = (MUT <= 4) ? MUT : (MUT == 11) ? 5 : (MUT == 12) ? 6 : 0;
    localparam integer D_HS = 47, D_FR = 0, PVL = 0, D_PVFST = 41;   // the die's relay stages (fa7fe4ff9 table)
    localparam integer D_AP0 = 5, D_AP1 = 5, D_AP2 = 7, D_AP3 = 6;     // stacks WS WN ES EN
    localparam integer LH = D_HS + 1;
    localparam integer FR_OFS = D_PVFST - PVL - D_FR - D_HS - 1;         // -7
    localparam [63:0] AP_OFS = {16'(2 + D_AP3 - D_HS), 16'(2 + D_AP2 - D_HS), 16'(2 + D_AP1 - D_HS), 16'(2 + D_AP0 - D_HS)};
    localparam [63:0] DUT_AP = (MUT == 8) ? {4{16'd2}} : (MUT == 10) ? AP_OFS + 64'h0000_0001_0000_0000 : AP_OFS;
    localparam integer DUT_FR = (MUT == 8) ? 0 : (MUT == 9) ? FR_OFS + 1 : FR_OFS;
    localparam integer NP = 7;
    // production calendars (11 x 16 b): {R, P1, P0, PV_START, HUB_PUB, HUB_RECIP, HUB_Z, HUB_LMAX, Z, LMAX, EXP}
    function automatic [175:0] pcal(input integer T);
        case (T)
            1:       pcal = {16'd1067, 16'd248, 16'd280, 16'd663, 16'd935, 16'd860, 16'd779, 16'd236, 16'd518, 16'd229, 16'd244};
            128:     pcal = {16'd1037, 16'd248, 16'd280, 16'd693, 16'd965, 16'd890, 16'd809, 16'd251, 16'd548, 16'd244, 16'd259};
            1000:    pcal = {16'd1054, 16'd328, 16'd328, 16'd676, 16'd996, 16'd921, 16'd840, 16'd267, 16'd579, 16'd260, 16'd275};
            2048:    pcal = {16'd1056, 16'd392, 16'd392, 16'd674, 16'd1058, 16'd983, 16'd902, 16'd299, 16'd641, 16'd292, 16'd307};
            4096:    pcal = {16'd1041, 16'd520, 16'd520, 16'd689, 16'd1182, 16'd1107, 16'd1026, 16'd363, 16'd765, 16'd356, 16'd371};
            6144:    pcal = {16'd906, 16'd648, 16'd648, 16'd824, 16'd1338, 16'd1263, 16'd1182, 16'd459, 16'd921, 16'd452, 16'd467};
            default: pcal = {16'd814, 16'd776, 16'd776, 16'd916, 16'd1430, 16'd1355, 16'd1274, 16'd491, 16'd1013, 16'd484, 16'd499};
        endcase
    endfunction
    reg [175:0] CAL = 0;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    // ---- attention service root (actual RTL) ----
    reg req_v = 0;  reg [15:0] req_ep = 0;  reg [5:0] req_layer = 0;  reg [17:0] req_pos = 0;
    wire req_rdy, q_rdy, running, start_qk, start_pv, lf, iof;
    wire [15:0] age, ep;  wire [5:0] layer;  wire [13:0] ctx;  wire [175:0] cal;  wire [31:0] cycles;
    qkd_attn_service_root #(.PV_LEAD(PVL)) u_root (.ck(ck), .rst_n(rst_n), .request_valid(req_v), .request_ready(req_rdy),
        .request_epoch(req_ep), .request_layer(req_layer), .request_position(req_pos), .fused_program_capability(1'b1),
        .request_calendar(CAL), .q_valid(q_rdy), .q_beat(5'(age - 16'd1)), .q_ready(q_rdy), .running(running),
        .start_qk(start_qk), .start_pv(start_pv), .age(age), .ep(ep), .layer(layer), .ctx(ctx), .cal(cal),
        .cycles(cycles), .local_fault(lf), .io_fault(iof));
    // ---- reference hub (the native service's block) ----
    reg [63:0] r_hep;  reg [23:0] r_hla;
    always @(posedge ck) if (start_qk) begin r_hep <= {4{ep}}; r_hla <= {4{layer}}; end
    wire [15:0] LIN = cal[31:16] + 16'd2, ZIN = cal[47:32] + 16'd2;
    reg  [3:0] g_v, g_g, g_a;  reg [7:0] g_t, g_h;  reg [15:0] g_k;  reg [127:0] g_d;
    wire [143:0] r_am;  wire r_rzv, r_pub, r_fault;  wire [1:0] r_rzh;  wire [31:0] r_rzd;  wire [15:0] r_rze;
    wire [127:0] r_rz;
    ot_qkd_ahub_static_die_cal #(.Z_IN_STRIDE(ZS), .Z_LEVEL_GAP(10), .ZW_RLY(0), .ZR_RLY(0), .RX_RLY(2), .RY_RLY(2)) u_ref (
        .cal({cal[111:96], cal[95:80], cal[79:64], cal[63:48], ZIN, ZIN, ZIN, ZIN, LIN, LIN, LIN, LIN}),
        .ck_core(ck), .ck_recip(ck), .ck_zh({4{ck}}), .rst_n(rst_n), .start(start_qk), .active_layer_parity(layer[0]),
        .request_epoch(ep), .active_layer(layer), .T(ctx), .si_valid(g_v), .si_g(g_g), .si_any(g_a), .si_epoch(r_hep),
        .si_layer(r_hla), .si_type(g_t), .si_hh(g_h), .si_k(g_k), .si_data(g_d), .am(r_am), .rz_valid(r_rzv),
        .rz_head(r_rzh), .rz_data(r_rzd), .rz_epoch(r_rze), .rz_publish(r_pub), .rz_vector(r_rz), .fault(r_fault));
    function automatic [31:0] fpint(input integer n);
        integer top;
        begin top = 0; for (integer b = 0; b < 16; b = b + 1) if ((n >> b) != 0) top = b;
              fpint = ((127 + top) << 23) | ((n << (23 - top)) & 32'h007fffff); end
    endfunction
    // stack words on the reference's compiled slots (the producer the compiler schedules); 0 off-slot
    always @* begin
        g_v = 0; g_g = 0; g_a = 0; g_t = 0; g_h = 0; g_k = 0; g_d = 0;
        for (integer s = 0; s < 4; s = s + 1) begin
            if (u_ref.u_core.lm_slot[s]) begin
                g_v[s] = 1; g_a[s] = 1; g_h[2*s +: 2] = u_ref.u_core.slot_h[2*s +: 2];
                g_d[32*s +: 32] = fpint(1 + 4 * s + u_ref.u_core.slot_h[2*s +: 2]);
            end else if (u_ref.u_core.z_slot[s]) begin
                g_v[s] = 1; g_a[s] = 1; g_t[2*s +: 2] = 2'd1; g_h[2*s +: 2] = u_ref.u_core.slot_h[2*s +: 2];
                g_k[4*s +: 4] = u_ref.u_core.slot_k[4*s +: 4];
                g_d[32*s +: 32] = fpint((s * 16 + u_ref.u_core.slot_k[4*s +: 4] + 1) * (u_ref.u_core.slot_h[2*s +: 2] + 1));
            end else if (u_ref.u_core.done_slot[s]) begin
                g_v[s] = 1; g_t[2*s +: 2] = 2'd2;
            end
        end
    end
    // ---- the die: relays + DUT + pvfin ----
    wire [164:0] hs_d;
    ot_qkd_drly #(.W(165), .N(D_HS)) u_rhs (.clk(ck), .d({cal[175:160], cal[127:16], ctx, layer, ep, start_qk}), .q(hs_d));
    wire [42:0] ap_g [0:3];  wire [42:0] ap_d [0:3];
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_ap
        assign ap_g[s] = {g_d[32*s +: 32], g_a[s], g_k[4*s +: 4], g_h[2*s +: 2], g_g[s], g_t[2*s +: 2], g_v[s]};
    end endgenerate
    ot_qkd_drly #(.W(43), .N(D_AP0)) u_ra0 (.clk(ck), .d(ap_g[0]), .q(ap_d[0]));
    ot_qkd_drly #(.W(43), .N(D_AP1)) u_ra1 (.clk(ck), .d(ap_g[1]), .q(ap_d[1]));
    ot_qkd_drly #(.W(43), .N(D_AP2)) u_ra2 (.clk(ck), .d(ap_g[2]), .q(ap_d[2]));
    ot_qkd_drly #(.W(43), .N(D_AP3)) u_ra3 (.clk(ck), .d(ap_g[3]), .q(ap_d[3]));
    wire [35:0] am0, am1, am2, am3;  wire fr_v, hf;  wire [15:0] fr_e;  wire [127:0] fr_rz;
    qkd_ahub_static_dw_safe #(.Z_IN_STRIDE(DUT_ZS), .AP_OFS(DUT_AP), .FR_OFS(DUT_FR), .MUT(DUT_MUT)) dut (.ck(ck), .rst_n(rst_n),
        .hs_start(hs_d[0]), .hs_ep(hs_d[16:1]), .hs_layer(hs_d[22:17]), .hs_ctx(hs_d[36:23]), .hs_cal_lo(hs_d[148:37]),
        .hs_cal_r(hs_d[164:149]), .ap0(ap_d[0]), .ap1(ap_d[1]), .ap2(ap_d[2]), .ap3(ap_d[3]),
        .am0(am0), .am1(am1), .am2(am2), .am3(am3), .fr_valid(fr_v), .fr_epoch(fr_e), .fr_rz(fr_rz), .hf(hf));
    wire [144:0] fr_d;  wire [64:0] fs_d;
    ot_qkd_drly #(.W(145), .N(D_FR)) u_rfr (.clk(ck), .d({fr_rz, fr_e, fr_v}), .q(fr_d));
    ot_qkd_drly #(.W(65), .N(D_PVFST)) u_rfs (.clk(ck), .d({cal[175:128], ep, start_pv}), .q(fs_d));
    // pair streams on pvfin's P0 / P1 slots: pair 0 = 1.0 x 16, pair 1 = +0.0, so out = rz[head] exactly
    integer fs_cyc = -100000;
    always @(posedge ck) if (fs_d[0]) fs_cyc <= cyc;
    wire [15:0] fs_ep = fs_d[16:1];
    reg [15:0] cur_ep = 0, C_P0 = 0, C_P1 = 0, C_R = 0;
    always @(posedge ck) if (fs_d[0]) begin cur_ep <= fs_ep; C_P0 <= fs_d[32:17]; C_P1 <= fs_d[48:33]; C_R <= fs_d[64:49]; end
    wire        p0v = (cyc - fs_cyc >= C_P0) && (cyc - fs_cyc < C_P0 + 32);
    wire        p1v = (cyc - fs_cyc >= C_P1) && (cyc - fs_cyc < C_P1 + 32);
    wire [4:0]  p0b = 5'(cyc - fs_cyc - C_P0), p1b = 5'(cyc - fs_cyc - C_P1);
    wire o_v;  wire [4:0] o_b;  wire [15:0] o_e;  wire [511:0] o_d;  wire pf;
    qkd_pv_fin_s #(.ADD_LAT(7), .MUL_LAT(6), .SKEW(1), .MUT(0)) u_fin (.ck(ck), .rst_n(rst_n), .start(fs_d[0]),
        .epoch(fs_ep), .cal(fs_d[64:17]), .p0_valid(p0v), .p0_beat(p0b), .p0_epoch(cur_ep), .p0_data({16{32'h3f800000}}),
        .p1_valid(p1v), .p1_beat(p1b), .p1_epoch(cur_ep), .p1_data(512'd0), .rz_valid(fr_d[0]), .rz_epoch(fr_d[16:1]),
        .rz(fr_d[144:17]), .out_valid(o_v), .out_beat(o_b), .out_epoch(o_e), .out_data(o_d), .fault(pf));
    // ---- reference am delayed by the hub's die lag ----
    wire [143:0] r_am_d;
    ot_qkd_drly #(.W(144), .N(LH)) u_ramd (.clk(ck), .d(r_am), .q(r_am_d));
    function automatic [35:0] am_astk(input [35:0] h);
        am_astk = {h[31:0], h[33:32], h[34], h[35]};
    endfunction
    function automatic amv(input [35:0] d, input [35:0] h);
        amv = (d[0] !== h[35]) || (h[35] && d !== am_astk(h));
    endfunction
    // external golden (tb_qkd_ahub_static, T 8192 with these words)
    function automatic [31:0] gold8192(input integer head);
        case (head) 0: gold8192 = 32'h39fc0fc0; 1: gold8192 = 32'h397c0fc0; 2: gold8192 = 32'h39280a81;
                    default: gold8192 = 32'h38fc0fc0; endcase
    endfunction
    // ---- checks ----
    integer zwn = 0, errors = 0, pass_i = -1, frn [0:NP-1], outn [0:NP-1], amn = 0, pubn = 0, done = 0;
    reg [127:0] gold;  reg [15:0] pep [0:NP-1];  integer pT [0:NP-1];
    task automatic err(input [8*96-1:0] what);
        begin
            if (errors == 0) $display("AHUB_DW FAIL mut=%0d first error cycle %0d pass %0d: %0s", MUT, cyc, pass_i, what);
            errors = errors + 1;
        end
    endtask
    always @(negedge ck) if (rst_n) begin
        if (r_fault) err("reference hub fault");
        if (hf) err("die hub fault hf");
        if (pf) err("pvfin fault");
        if (lf || iof) err("root fault");
        // valid every edge; the word when valid (the data flops have no reset: 2-state power-up values differ)
        if (amv(am0, r_am_d[35:0]) || amv(am1, r_am_d[71:36]) || amv(am2, r_am_d[107:72]) || amv(am3, r_am_d[143:108]))
            err("am at the ASTK pins != reference");
        if (am0[0]) amn = amn + 1;
        for (integer s2 = 0; s2 < 4; s2 = s2 + 1) if (u_ref.u_core.z_slot[s2]) zwn = zwn + 1;
        if (r_pub) begin gold = r_rz; pubn = pubn + 1; end
        if (fr_d[0]) begin
            if (pass_i < 0) err("fr outside a pass");
            else begin
                frn[pass_i] = frn[pass_i] + 1;
                if (cyc != fs_cyc + C_R) err("fr not on pvfin's R slot");
                if (fr_d[144:17] !== gold) err("reciprocals at pvfin.fr != reference rz_vector");
                if (fr_d[16:1] !== pep[pass_i]) err("rz_epoch at pvfin.fr != pass epoch");
                if (pT[pass_i] == 8192)
                    for (integer h = 0; h < 4; h = h + 1)
                        if (fr_d[17 + 32*h +: 32] !== gold8192(h)) err("reciprocal != external golden (T 8192)");
            end
        end
        if (o_v && pass_i >= 0) begin
            outn[pass_i] = outn[pass_i] + 1;
            if (o_d !== {16{gold[32*(o_b/8) +: 32]}}) err("pvfin out beat != 1.0 x rz[head]");
            if (o_e !== pep[pass_i]) err("pvfin out epoch");
        end
    end
    initial begin
        for (integer i = 0; i < NP; i = i + 1) begin frn[i] = 0; outn[i] = 0; end
        pT[0] = 8192; pT[1] = 2048; pT[2] = 1; pT[3] = 1000; pT[4] = 128; pT[5] = 6144; pT[6] = 4096;
        pep[0] = 16'h1234; pep[1] = 16'h1235; pep[2] = 16'h2001; pep[3] = 16'h2002; pep[4] = 16'h2003; pep[5] = 16'h3001;
        pep[6] = 16'h3002;
        repeat (6) @(negedge ck); rst_n = 1;
        for (integer i = 0; i < NP; i = i + 1) begin
            while (!req_rdy) @(negedge ck);
            repeat (3) @(negedge ck);
            pass_i = i;
            CAL = pcal(pT[i]);
            if (CAL[159:144] + 16'd1 < CAL[143:128] || CAL[143:128] + 16'd1 < CAL[159:144])
                CAL[159:144] = CAL[143:128];                            // P1 := P0 only where the pair skew > SKEW (header)
            req_v = 1; req_ep = pep[i]; req_layer = 6'(3 + i); req_pos = 18'(pT[i] - 1);
            @(negedge ck); req_v = 0;
            repeat (1950) @(negedge ck);
            if (frn[i] != 1) err("not exactly one fr edge in the pass");
            if (outn[i] != 32) err("pvfin did not emit 32 beats");
        end
        repeat (20) @(negedge ck);
        if (amn != 4 * NP) err("am valid count");
        if (pubn != NP) err("reference publication count");
        // 4 heads x sum_s nblk_s(T): T 8192 256, 2048 64, 1 4, 1000 32, 128 4, 6144 192, 4096 128
        if (zwn != 680) err("Z word count on the stride-4 slots != 680");
        if (errors == 0)
            $display("AHUB_DW PASS mut=%0d passes=%0d Z_IN_STRIDE=%0d zwords=%0d fr=%0d/%0d/%0d/%0d/%0d/%0d/%0d beats=%0d/%0d/%0d/%0d/%0d/%0d/%0d am=%0d FR_OFS=%0d AP_OFS=%h",
                     MUT, NP, DUT_ZS, zwn, frn[0], frn[1], frn[2], frn[3], frn[4], frn[5], frn[6], outn[0], outn[1], outn[2],
                     outn[3], outn[4], outn[5], outn[6], amn, DUT_FR, DUT_AP);
        else $display("AHUB_DW FAIL mut=%0d errors=%0d", MUT, errors);
        $finish;
    end
endmodule
