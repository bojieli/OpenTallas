`timescale 1ns/1ps
// HKV-AHUB4 2026-10-19: tb_qkd_ahub_static_dw at the KV DIE's binding, Z_IN_STRIDE = 4 (kv_static_die ASTK_Z_STRIDE = the
// CLOSED qkd_astk_ctl_s Z stride; the die passes ONLY Z_IN_STRIDE, so AP_OFS / FR_OFS are the RTL defaults {4{2}} / 0)
// on the PRODUCTION calendars of the native case: kv_static_programme.compile_all(profile('die')) attention samples under
// OT_KV_ASTK_EXPAND=1 (RL3 law: LMAX / EXP +16, Z / HUB_Z / HUB_RECIP / HUB_PUB +40; service_end 1779, R stretched so
// PV_START + R = 1730 for every T; claude/hkv-die-1019 90dedf84f, die ages qwen_kv_static_programme_1017/die_ages.json).
// One calendar per pass (T 8192 / 2048 / 1 / 1000 / 128 / 6144 / 4096).  Every hub field (EXP .. PV_START, R) is the
// compiled value; ONLY the synthetic pair-stream slots P0 / P1 given to qkd_pv_fin_s are set to R: the compiled stretched
// {R, P1, P0} violate qkd_pv_fin_s cal_bad (R <= max(P0, P1) + ADD_LAT + 1, |P0 - P1| <= SKEW) at every T (T 8192 R 843 vs
// LASTP 776; T 1 skew 32) -- a die compiler / pvfin finding for HKV-DIE, outside this hub kit.  (Unstretched R fails the
// HUB instead: the dw export needs PV_START + R + FR_OFS >= HUB_PUB + 3, the compiler's RZ_MARGIN is 2.)  Same structure as tb_qkd_ahub_static_dw:
// ACTUAL qkd_attn_service_root -> die relays -> DUT -> relays -> ACTUAL qkd_pv_fin_s, lockstep against the sealed
// ot_qkd_ahub_static_die_cal at Z_IN_STRIDE 4 fed by the root with no die stages; the stack words ride the reference's
// compiled slots (slot_h / slot_k at stride 4 = one Z word EVERY edge of a 4 x nblk window), and the DUT's own slot
// checks (si_hh / si_k / type vs its stride-4 decode) feed hf.  Relays satisfy the default offsets: D_AP[s] = D_HS
// (AP_OFS 2), D_PVFST = PVL + D_FR + D_HS + 1 (FR_OFS 0).  T 8192 reciprocals == the external golden (same word set).
// MUT: 1..4 = the DUT's own negative controls; 5 = DUT hardened at the RTL default Z_IN_STRIDE 16 (the a3 kit) against the
// stride-4 die; 6 / 7 = slot_h / slot_k decode shifted by one (bench script seds a copy of the DUT RTL).  All must FAIL.
module tb_qkd_ahub_static_dw_s4;
    parameter integer MUT = 0;
    localparam integer ZS = 4;                                   // the die's Z_IN_STRIDE (kv_static_die ASTK_Z_STRIDE)
    localparam integer DUT_ZS = (MUT == 5) ? 16 : ZS;
    localparam integer DUT_MUT = (MUT <= 4) ? MUT : 0;
    localparam integer D_HS = 3, D_FR = 2, PVL = 2;
    localparam integer D_PVFST = PVL + D_FR + D_HS + 1;          // FR_OFS = D_PVFST - PVL - D_FR - D_HS - 1 = 0 (default)
    localparam integer D_AP0 = D_HS, D_AP1 = D_HS, D_AP2 = D_HS, D_AP3 = D_HS;   // AP_OFS[s] = 2 + D_AP - D_HS = 2 (default)
    localparam integer LH = D_HS + 1;
    localparam integer FR_OFS = D_PVFST - PVL - D_FR - D_HS - 1;
    localparam [63:0] AP_OFS = {4{16'd2}};
    localparam integer NP = 7;
    // production calendars (11 x 16 b): {R, P1, P0, PV_START, HUB_PUB, HUB_RECIP, HUB_Z, HUB_LMAX, Z, LMAX, EXP}
    function automatic [175:0] pcal(input integer T);
        case (T)
            1:       pcal = {16'd1104, 16'd248, 16'd280, 16'd626, 16'd904, 16'd831, 16'd750, 16'd207, 16'd489, 16'd200, 16'd215};
            128:     pcal = {16'd1074, 16'd248, 16'd280, 16'd656, 16'd934, 16'd861, 16'd780, 16'd222, 16'd519, 16'd215, 16'd230};
            1000:    pcal = {16'd1091, 16'd328, 16'd328, 16'd639, 16'd965, 16'd892, 16'd811, 16'd238, 16'd550, 16'd231, 16'd246};
            2048:    pcal = {16'd1093, 16'd392, 16'd392, 16'd637, 16'd1027, 16'd954, 16'd873, 16'd270, 16'd612, 16'd263, 16'd278};
            4096:    pcal = {16'd1070, 16'd520, 16'd520, 16'd660, 16'd1151, 16'd1078, 16'd997, 16'd334, 16'd736, 16'd327, 16'd342};
            6144:    pcal = {16'd935, 16'd648, 16'd648, 16'd795, 16'd1307, 16'd1234, 16'd1153, 16'd430, 16'd892, 16'd423, 16'd438};
            default: pcal = {16'd843, 16'd776, 16'd776, 16'd887, 16'd1399, 16'd1326, 16'd1245, 16'd462, 16'd984, 16'd455, 16'd470};
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
    ot_qkd_ahub_static_die_cal #(.Z_IN_STRIDE(ZS), .Z_LEVEL_GAP(10), .ZW_RLY(0), .ZR_RLY(0), .RX_RLY(1), .RY_RLY(1)) u_ref (
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
    qkd_ahub_static_dw #(.Z_IN_STRIDE(DUT_ZS), .MUT(DUT_MUT)) dut (.ck(ck), .rst_n(rst_n),
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
            CAL[159:144] = CAL[175:160]; CAL[143:128] = CAL[175:160];   // pvfin pair slots P0 = P1 = R (see header)
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
                     outn[3], outn[4], outn[5], outn[6], amn, FR_OFS, AP_OFS);
        else $display("AHUB_DW FAIL mut=%0d errors=%0d", MUT, errors);
        $finish;
    end
endmodule
