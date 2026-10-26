`timescale 1ns/1ps
// Q-PORTMAP b2 (2026-10-16): per-side half-band lanes + TP4-form tree top against TODAY's TP8 band layout and the lane.
//   golden : NL copies of ot_qwen_spine_lane (the existing reference, GT 3,072 lane; groups g < 3072 >> s)
//   REF    : today's TP8 die structure: 3 x ot_qfd_band_lanes (GP 8, levels 8..10) + ot_qfd_band_upper NB 3 LG 12 (level 11)
//   DUT    : 6 half bands hb = 2b + h (h 0 = W positions 8b..8b+3, h 1 = E positions 8b+4..8b+7), ot_qfd_band_lanes
//            GP 4 (levels 8, 9) + ot_qfd_band_upper NB 6, TCUT 6, LG 12 (NU 2: level 10 = W+E of each band, level 11 =
//            band0+band1, band2 held), half-band 0 takes the upper's words.
// TP8 GT3072 has nonempty groups only for split7..11; split12 yields zero groups,
// so it is excluded from production-output coverage. Golden uses the actual GT3072 tree.
// Result frame (DUT, tools/qwen_split/b2_frame.py): split s <= 9: g = hb * 2^(9-s) + k (k < 2^(9-s)); s >= 10: hb 0
// slot k = g (k < 3072 >> s).  REF frame (BANDF 1): s <= 10: g = b * 2^(10-s) + k; s >= 11: band 0 slot g.
// Check for every valid op, split 7..11, every in-range group, every lane: DUT word == REF word == lane word, bit-exact,
// and the DUT word on the SAME edge as the REF word (zero added cycles).  Faults: finite phase 0/0, NaN phase 1/1.
// Negatives (must FAIL): MUT 1 = half-band level-8 pairing (0,2)(1,3); MUT 2 = upper level-10 pairing (hb, hb+3);
// MUT 5 = DUT checked in the REF (BANDF 1) frame (the compiler not absorbing the moved result positions).
module tb_qfd_halfband;
    parameter integer NL = 4, LNK = 0, MUT = 0, NOPS = 3000, SEED = 1, RDMEM = 0, SLOT = 0, S4 = 0;
    localparam integer NB = 3, LG = 12, LAT_L = 33, LAT_B = 46 + 2 * LNK - 8;
    reg clk = 0, rst_n = 0;
    reg break_return;
    initial break_return=$test$plusargs("BREAK_RETURN");
    always #5 clk = ~clk;
    reg [24*NL*32-1:0] din;
    reg [13:0] sel, tv;
    // ---- golden lanes ----------------------------------------------------------------------------------------------
    wire [24*NL*32-1:0] ry;
    wire [NL-1:0] rf;
    genvar l, p, b, h;
    generate for (l = 0; l < NL; l = l + 1) begin : g_ref
        wire [24*32-1:0] ti, yo;
        for (p = 0; p < 24; p = p + 1) begin : g_p
            assign ti[32*p +: 32] = din[32*(p*NL + l) +: 32];
            assign ry[32*(p*NL + l) +: 32] = yo[32*p +: 32];
        end
        ot_qwen_me_sptree_w12 #(.GT(3072), .SMIN(7), .TCUT(7), .TREE_LAT(7), .TINREG(1)) u_lane
            (.clk(clk), .rst_n(rst_n), .t_in(ti), .sel_e(sel[LG:0]), .tv_e(tv[LG:0]), .y(yo), .fault(rf[l]));
    end endgenerate
    // ---- REF: today's TP8 layout -------------------------------------------------------------------------------------
    wire [NB*NL*32-1:0] pw, pw_r;
    wire [NB-1:0] pv, pv_r, bf, bf_r;
    wire [8*NL*32-1:0] ty [0:NB-1];
    wire [3*NL*32-1:0] tt, tt_r;
    wire tu, tvv, tu_r, tv_r2, uf;
    generate for (b = 0; b < NB; b = b + 1) begin : g_band
        ot_qfd_band_lanes #(.NL(NL), .LNK(LNK), .RDMEM(RDMEM), .LG(LG)) u_b (
            .clk(clk), .rst_n(rst_n), .b0(b == 0), .tw(din[b*8*NL*32 +: 8*NL*32]), .sel_e(sel[LG:0]), .tv_e(tv[LG:0]),
            .tt_ty(b == 0 ? tt_r : {3*NL*32{1'b0}}), .tt_use(b == 0 ? tu_r : 1'b0), .tt_v(b == 0 ? tv_r2 : 1'b0),
            .pw(pw[b*NL*32 +: NL*32]), .pw_v(pv[b]), .ty(ty[b]), .fault(bf[b]));
    end endgenerate
    ot_hdc_delay #(.W(NB*NL*32), .D(LNK)) u_l1 (.clk(clk), .rst_n(rst_n), .d(pw), .q(pw_r));
    ot_hdc_delay #(.W(2*NB), .D(LNK), .RESET(1)) u_l2 (.clk(clk), .rst_n(rst_n), .d({pv, bf}), .q({pv_r, bf_r}));
    ot_hdc_delay #(.W(3*NL*32), .D(LNK)) u_l3 (.clk(clk), .rst_n(rst_n), .d(tt), .q(tt_r));
    ot_hdc_delay #(.W(2), .D(LNK), .RESET(1)) u_l4 (.clk(clk), .rst_n(rst_n), .d({tu, tvv}), .q({tu_r, tv_r2}));
    ot_qfd_band_upper #(.NL(NL), .NB(NB), .LNK(LNK), .LG(LG)) u_up (
        .clk(clk), .rst_n(rst_n), .pw(pw_r), .pw_v(pv_r), .lf(bf_r), .sel_e(sel[LG:0]), .tv_e(tv[LG:0]),
        .tt_ty(tt), .tt_use(tu), .tt_v(tvv), .fault(uf));
    // ---- DUT: 6 half bands + upper NB 6 (TCUT 6) ----------------------------------------------------------------------
    localparam integer NH = 2 * NB;
    wire [NH*NL*32-1:0] hpw, hpw_r;
    wire [NH-1:0] hpv, hpv_r, hbf, hbf_r;
    wire [4*NL*32-1:0] hty [0:NH-1];
    wire [3*NL*32-1:0] htt, htt_r;
    wire htu, htv, htu_r, htv_r, huf;
    wire [7:0] observed_upper_faults;
    wire [8*192-1:0] hret_d,hret_dr;
    wire [15:0] hret_f,hret_fr;
    wire [8*194-1:0] hreturn_r;
    ot_hdc_delay #(.W(8*192),.D(LNK)) u_return_payload(.clk(clk),.rst_n(rst_n),.d(hret_d),.q(hret_dr));
    ot_hdc_delay #(.W(16),.D(LNK),.RESET(1)) u_return_flags(.clk(clk),.rst_n(rst_n),.d(hret_f),.q(hret_fr));
    generate for(genvar ru=0;ru<8;ru=ru+1)begin:g_return_bundle
        assign hreturn_r[194*ru+:194]={hret_fr[2*ru+:2],hret_dr[192*ru+:192]};
    end endgenerate
    wire [NH*8*65-1:0] hface,hface_r;
    wire [NH*8-1:0] hface_fault,hface_fault_r;
    generate for (b = 0; b < NH; b = b + 1) begin : g_half
        if (SLOT == 0) begin : g_flat
        ot_qfd_band_lanes #(.NL(NL), .LNK(LNK), .RDMEM(RDMEM), .LG(LG), .GP(4), .MUT(MUT == 1 ? 1 : 0)) u_h (
            .clk(clk), .rst_n(rst_n), .b0(b == 0), .tw(din[b*4*NL*32 +: 4*NL*32]), .sel_e(sel[LG:0]), .tv_e(tv[LG:0]),
            .tt_ty(b == 0 ? htt_r : {3*NL*32{1'b0}}), .tt_use(b == 0 ? htu_r : 1'b0), .tt_v(b == 0 ? htv_r : 1'b0),
            .pw(hpw[b*NL*32 +: NL*32]), .pw_v(hpv[b]), .ty(hty[b]), .fault(hbf[b]));
        end else if(SLOT==1) begin : g_slot
            wire [512:0] hp;
            initial if (NL != 16) $fatal(1,"slot requires actual16 lanes");
            qfd_sp_halfband_lanes u_h (
                .ck(clk), .ck_l0(clk),.ck_l1(clk),.ck_l2(clk),.ck_l3(clk),
                .ck_l4(clk),.ck_l5(clk),.ck_l6(clk),.ck_l7(clk),
                .ck_l8(clk),.ck_l9(clk),.ck_l10(clk),.ck_l11(clk),
                .ck_l12(clk),.ck_l13(clk),.ck_l14(clk),.ck_l15(clk),
                .rst_n(rst_n),.b0(b==0),.lnk(6'(LNK)),.tw(din[b*4*NL*32+:4*NL*32]),
                .c({tv[LG:0],sel[LG:0]}),
                .tt(b==0?{htv_r,htu_r,htt_r}:1538'd0),
                .pw(hp),.ty(hty[b]),.f(hbf[b]));
            assign hpw[b*NL*32+:NL*32]=hp[511:0];assign hpv[b]=hp[512];
        end else begin:g_slot_l2
            wire [512:0] hp;
            initial if(NL!=16)$fatal(1,"NL2 upper composition requires16 lanes");
            qfd_sp_halfband_lanes_b2_l2 u_h (
                .ck(clk),.ck_l0(clk),.ck_l1(clk),.ck_l2(clk),.ck_l3(clk),
                .ck_l4(clk),.ck_l5(clk),.ck_l6(clk),.ck_l7(clk),
                .ck_l8(clk),.ck_l9(clk),.ck_l10(clk),.ck_l11(clk),
                .ck_l12(clk),.ck_l13(clk),.ck_l14(clk),.ck_l15(clk),
                .rst_n(rst_n),.b0(b==0),.lnk(6'(LNK)),.tw(din[b*4*NL*32+:4*NL*32]),
                .c({tv[LG:0],sel[LG:0]}),
                .tt_l0(b==0?hreturn_r[194*0+:194]:194'd0),
                .tt_l1(b==0?hreturn_r[194*1+:194]:194'd0),
                .tt_l2(b==0?hreturn_r[194*2+:194]:194'd0),
                .tt_l3(b==0?hreturn_r[194*3+:194]:194'd0),
                .tt_l4(b==0?hreturn_r[194*4+:194]:194'd0),
                .tt_l5(b==0?hreturn_r[194*5+:194]:194'd0),
                .tt_l6(b==0?hreturn_r[194*6+:194]:194'd0),
                .tt_l7(b==0?hreturn_r[194*7+:194]:194'd0),

                .pw_l0(hface[65*(8*b+0)+:65]),.pw_l1(hface[65*(8*b+1)+:65]),
                .pw_l2(hface[65*(8*b+2)+:65]),.pw_l3(hface[65*(8*b+3)+:65]),
                .pw_l4(hface[65*(8*b+4)+:65]),.pw_l5(hface[65*(8*b+5)+:65]),
                .pw_l6(hface[65*(8*b+6)+:65]),.pw_l7(hface[65*(8*b+7)+:65]),
                .f_up(hface_fault[8*b+:8]),.pw(hp),.ty(hty[b]),.f(hbf[b]));
            assign hpw[b*NL*32+:NL*32]=hp[511:0];assign hpv[b]=hp[512];
        end
    end endgenerate
    ot_hdc_delay #(.W(NH*NL*32), .D(LNK)) u_h1 (.clk(clk), .rst_n(rst_n), .d(hpw), .q(hpw_r));
    ot_hdc_delay #(.W(2*NH), .D(LNK), .RESET(1)) u_h2 (.clk(clk), .rst_n(rst_n), .d({hpv, hbf}), .q({hpv_r, hbf_r}));
    ot_hdc_delay #(.W(3*NL*32), .D(LNK)) u_h3 (.clk(clk), .rst_n(rst_n), .d(htt), .q(htt_r));
    ot_hdc_delay #(.W(2), .D(LNK), .RESET(1)) u_h4 (.clk(clk), .rst_n(rst_n), .d({htu, htv}), .q({htu_r, htv_r}));
    ot_hdc_delay #(.W(NH*8*65),.D(LNK)) u_face_delay(.clk(clk),.rst_n(rst_n),.d(hface),.q(hface_r));
    ot_hdc_delay #(.W(NH*8),.D(LNK),.RESET(1)) u_face_fault_delay(.clk(clk),.rst_n(rst_n),.d(hface_fault),.q(hface_fault_r));
    generate if (SLOT==0) begin:g_flatupper
    assign observed_upper_faults=8'hff;
    ot_qfd_band_upper #(.NL(NL), .NB(NH), .LNK(LNK), .TCUT(6), .LG(LG), .MUT(MUT == 2 ? 2 : 0)) u_hup (
        .clk(clk), .rst_n(rst_n), .pw(hpw_r), .pw_v(hpv_r), .lf(hbf_r), .sel_e(sel[LG:0]), .tv_e(tv[LG:0]),
        .tt_ty(htt), .tt_use(htu), .tt_v(htv), .fault(huf));
    end else if(SLOT==1) begin:g_realupper
        assign observed_upper_faults=8'hff;
        // The wrapper's DLY1 gets the explicit three control transport edges before its DLY1.
        // This is the existing parent-lane station contract, not an arithmetic stage.
        wire [25:0] uc;
        wire [3:0] uv,uu,uf;
        ot_hdc_delay #(.W(26),.D(3+LNK)) u_control(.clk(clk),.rst_n(rst_n),.d({tv[12:0],sel[12:0]}),.q(uc));
        for(genvar u=0;u<4;u=u+1)begin:g_up
            wire [767:0] w;
            wire [383:0] y;
            for(genvar hh=0;hh<6;hh=hh+1)begin:g_in
                assign w[128*hh+:128]=hpw_r[32*(hh*16+4*u)+:128];
            end
            for(genvar pp=0;pp<3;pp=pp+1)begin:g_out
                assign htt[32*(pp*16+4*u)+:128]=y[128*pp+:128];
            end
            qfd_band_upper_b2 u_up(.clk(clk),.rst_n(rst_n),.pw(w),.pw_v(hpv_r),.lf(hbf_r),
              .sel_e(uc[12:0]),.tv_e(uc[25:13]),.tt_ty(y),.tt_use(uu[u]),.tt_v(uv[u]),.fault(uf[u]));
        end
        assign htu=uu[0];assign htv=uv[0];assign huf=(|uf) | (|(uu^{4{uu[0]}})) | (|(uv^{4{uv[0]}}));
    end else begin:g_realupper_l2
        wire [25:0] uc;
        wire [7:0] uv,uu,uf;
        reg [7:0] fault_seen;
        always @(posedge clk)if(!rst_n)fault_seen<=0;else fault_seen<=fault_seen|uf;
        assign observed_upper_faults=fault_seen;
        ot_hdc_delay #(.W(26),.D(3+LNK)) u_control(.clk(clk),.rst_n(rst_n),.d({tv[12:0],sel[12:0]}),.q(uc));
        for(genvar u=0;u<8;u=u+1)begin:g_up
            wire [383:0] w;
            wire [191:0] y;
            wire [5:0] vv,ff;
            assign hret_d[192*u+:192]=y;
            assign hret_f[2*u+:2]={(break_return && u==7)?1'b0:uv[u],uu[u]};
            for(genvar hh=0;hh<6;hh=hh+1)begin:g_in
                assign w[64*hh+:64]=hface_r[65*(hh*8+u)+:64];
                assign vv[hh]=hface_r[65*(hh*8+u)+64];
                assign ff[hh]=hface_fault_r[hh*8+u];
            end
            for(genvar pp=0;pp<3;pp=pp+1)begin:g_out
                assign htt[32*(pp*16+2*u)+:64]=y[64*pp+:64];
            end
            if(S4)begin:g_s4
              qfd_band_upper_b2_l2_s4 u_up(.clk(clk),.rst_n(rst_n),.pw(w),.pw_v(vv),.lf(ff),
                .sel_e(uc[11:10]),.tv_e(uc[24:23]),.tt_ty(y),.tt_use(uu[u]),.tt_v(uv[u]),.fault(uf[u]));
            end else begin:g_legacy_selector
            qfd_band_upper_b2_l2 u_up(.clk(clk),.rst_n(rst_n),.pw(w),.pw_v(vv),.lf(ff),
              .sel_e(uc[12:0]),.tv_e(uc[25:13]),.tt_ty(y),.tt_use(uu[u]),.tt_v(uv[u]),.fault(uf[u]));
            end
        end
        assign htu=uu[0];assign htv=uv[0];assign huf=(|uf) | (|(uu^{8{uu[0]}})) | (|(uv^{8{uv[0]}}));
    end endgenerate
    // ---- frames ----------------------------------------------------------------------------------------------------
    function automatic integer band_of(input integer s_, input integer g_);   // REF (BANDF 1)
        if (s_ <= 10) band_of = g_ >> (10 - s_); else band_of = 0;
    endfunction
    function automatic integer slot_of(input integer s_, input integer g_);
        if (s_ <= 10) slot_of = g_ & ((1 << (10 - s_)) - 1); else slot_of = g_;
    endfunction
    function automatic integer hb_of(input integer s_, input integer g_);     // DUT (BANDF 2)
        if (s_ <= 9) hb_of = g_ >> (9 - s_); else hb_of = 0;
    endfunction
    function automatic integer hslot_of(input integer s_, input integer g_);
        if (s_ <= 9) hslot_of = g_ & ((1 << (9 - s_)) - 1); else hslot_of = g_;
    endfunction
    // MUT 5: the DUT read in the REF frame (band b's slot k -> half band 2b + k/4, slot k%4: the BANDF-1 position)
    function automatic integer dhb(input integer s_, input integer g_);
        if (MUT == 5) dhb = 2 * band_of(s_, g_) + (slot_of(s_, g_) >> 2); else dhb = hb_of(s_, g_);
    endfunction
    function automatic integer dsl(input integer s_, input integer g_);
        if (MUT == 5) dsl = slot_of(s_, g_) & 3; else dsl = hslot_of(s_, g_);
    endfunction
    // ---- history + check -------------------------------------------------------------------------------------------
    localparam integer LAT_D = LAT_B + ((SLOT != 0) ? 4 : 0);
    localparam integer HN = 1 << 14;
    reg        hv [0:HN-1];
    reg [3:0]  hs [0:HN-1];
    reg [24*NL*32-1:0] yh [0:127];
    reg [8*NL*32-1:0] tyh [0:NB-1][0:127];
    reg [4*NL*32-1:0] htyh [0:NH-1][0:127];
    localparam integer LAT_C = (LAT_L > LAT_D) ? LAT_L : LAT_D;
    integer n = 0, i, k, g, s, ops = 0, checks = 0, groups = 0, errors = 0, rerrors = 0, seed = SEED;
    integer cnt_s [7:11];
    initial begin seed = SEED; $display("SEED=%0d", seed); end
    integer lv, d;
    reg rstick = 0, dstick = 0, hstick = 0;
    function automatic [31:0] rfp(input integer dummy);
        reg [31:0] r;
        begin r = $random(seed); rfp = {r[31], 8'd112 + {3'd0, r[27:23]}, r[22:0]}; end
    endfunction
    integer phase = 1, nan_at = -1;
    reg [3:0] csplit; reg cv;
    reg [31:0] wl, wr, wd;
    initial begin
        din = 0; sel = 0; tv = 0;
        for (i = 7; i <= 11; i = i + 1) cnt_s[i] = 0;
        for (i = 0; i < HN; i = i + 1) begin hv[i] = 0; hs[i] = 7; end
        repeat (3) @(posedge clk);
        @(negedge clk); rst_n = 1;
        while (n < NOPS + 200) begin
            yh[n % 128] = ry;
            for (i = 0; i < NB; i = i + 1) tyh[i][n % 128] = ty[i];
            for (i = 0; i < NH; i = i + 1) htyh[i][n % 128] = hty[i];
            if (n >= LAT_C && hv[(n - LAT_C) % HN]) begin
                s = hs[(n - LAT_C) % HN];
                cnt_s[s] = cnt_s[s] + 1;
                for (g = 0; g < ((NB * 1024) >> s); g = g + 1) begin
                    for (k = 0; k < NL; k = k + 1) begin
                        wl = yh[(n - LAT_C + LAT_L) % 128][32*(g*NL + k) +: 32];
                        wr = tyh[band_of(s, g)][(n - LAT_C + LAT_B) % 128][32*(slot_of(s, g)*NL + k) +: 32];
                        wd = htyh[dhb(s, g)][(n - LAT_C + LAT_D) % 128][32*(dsl(s, g)*NL + k) +: 32];
                        if (wr !== wl) rerrors = rerrors + 1;
                        if (wd !== wr || wd !== wl) begin
                            if (errors < 5) $display("MISMATCH op@%0d split %0d group %0d lane %0d: b2 %h today %h lane %h", n - LAT_C, s, g, k, wd, wr, wl);
                            errors = errors + 1;
                        end
                        checks = checks + 1;
                    end
                    groups = groups + 1;
                end
            end
            rstick = rstick | (|rf); dstick = dstick | uf; hstick = hstick | huf;
            if (n == NOPS / 2 + 120) begin
                if (rstick || dstick || hstick) begin $display("FAIL qfd_halfband finite-phase fault lane %0d today %0d b2 %0d", rstick, dstick, hstick); $fatal(1); end
                phase = 2;
            end
            cv = (n < NOPS / 2 || (n >= NOPS / 2 + 130 && n < NOPS)) && ((n % 97) < 60 ? 1'b1 : ($random(seed) & 1));
            csplit = 7 + ({$random(seed)} % (LG - 7));
            if (phase == 2 && nan_at < 0 && cv) begin csplit = 11; nan_at = n; end
            hv[n % HN] = cv; hs[n % HN] = csplit;
            for (i = 0; i < 24 * NL; i = i + 1) din[32*i +: 32] = rfp(0);
            if (nan_at == n) for(i=0;i<NL;i=i+1)din[32*i+:32]=32'h7FC00001;
            if (cv) ops = ops + 1;
            sel = 0; tv = 0;
            for (lv = 8; lv <= 12; lv = lv + 1) begin
                d = 8 * (lv - 8);
                if (n - d >= 0) tv[lv] = hv[(n - d) % HN] && (hs[(n - d) % HN] >= lv);
                if (n - d - 7 >= 0) sel[lv] = hs[(n - d - 7) % HN] >= lv;
            end
            @(posedge clk); @(negedge clk);
            n = n + 1;
        end
        if (!(rstick && dstick && hstick)) begin $display("FAIL qfd_halfband NaN phase: lane %0d today %0d b2 %0d", rstick, dstick, hstick); $fatal(1); end
        if(observed_upper_faults!==8'hff)$fatal(1,"upper fault face coverage %h",observed_upper_faults);
        if (rerrors != 0) begin $display("FAIL qfd_halfband reference (today vs lane) %0d mismatches: bench broken", rerrors); $fatal(1); end
        for (i = 7; i <= 11; i = i + 1) if (cnt_s[i] == 0) begin $display("FAIL qfd_halfband split %0d never exercised", i); $fatal(1); end
        if (errors != 0) begin $display("FAIL qfd_halfband %0d mismatching words of %0d (ops %0d, NL %0d, LNK %0d, MUT %0d)",
            errors, checks, ops, NL, LNK, MUT); $fatal(1); end
        $display("PASS qfd_halfband b2 == today == lane ops=%0d groups=%0d words=%0d NL=%0d LNK=%0d ops/split 7..11 = %0d %0d %0d %0d %0d, DUT stage delta=%0d, faults(finite 0/0/0, NaN 1/1/1)",
            ops, groups, checks, NL, LNK, cnt_s[7], cnt_s[8], cnt_s[9], cnt_s[10], cnt_s[11],LAT_D-LAT_B);
        $finish;
    end
endmodule
