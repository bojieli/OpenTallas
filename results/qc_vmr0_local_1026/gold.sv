module ORIG_vmr #(parameter integer MUT = 0, parameter integer MIF = 0) (
    input  wire            ck,
    input  wire            rst_n,
    // read port (W face)
    input  wire [7:0]      re,
    input  wire [8*24-1:0] addr,
    output reg  [8*32-1:0] q,
    // VM writes (S face)
    input  wire [7:0]      vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire            w16_we,
    input  wire [23:0]     w16_addr,
    input  wire [511:0]    w16_data,
    input  wire            w1_we,
    input  wire [23:0]     w1_addr,
    input  wire [31:0]     w1_data,
    output reg             fault
);
    integer l, b, s, k, lc;   // lc: clocked-block loop only (no shared loop variable between processes)
    genvar gl, gb, gs, gk, bk;
    reg rl0, rl1;
    generate if (MIF == 0) begin : g_legacy_reset
        always @(posedge ck or negedge rst_n) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end
    end else begin : g_timed_reset
        // Timed reset input of the physical MIF1 profile; release depth stays2.
        always @(posedge ck) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end
    end endgenerate
    // ---------------------------------------------------------------- input pin registers
    reg [7:0] pa_re; reg [8*24-1:0] pa_addr;
    always @(posedge ck) begin pa_re <= re; pa_addr <= addr; end
    reg [8*24-1:0] pvm_waddr; reg [8*32-1:0] pvm_wdata;
    reg pw16_we, pw1_we; reg [23:0] pw16_addr, pw1_addr; reg [511:0] pw16_data; reg [31:0] pw1_data;
    always @(posedge ck) begin
        pvm_waddr <= vm_waddr; pvm_wdata <= vm_wdata;
        pw16_we <= w16_we; pw16_addr <= w16_addr; pw16_data <= w16_data;
        pw1_we <= w1_we; pw1_addr <= w1_addr; pw1_data <= w1_data;
    end
    // ---------------------------------------------------------------- VM write decode (vm8 copy; kept window copies)
    wire [9:0] pwin [0:5];
    wire [5:0] su_any_k;
    generate for (gk = 0; gk < 6; gk = gk + 1) begin : g_pwin
        qfd_dv_s8x_kff #(.W(10), .ID(8000 + gk)) u (.ck(ck), .d({vm_we, vm_waddr[23:22]}), .q(pwin[gk]));
        assign su_any_k[gk] = (|pwin[gk][9:2]) && pwin[gk][1:0] == 2'b00;
    end endgenerate
    wire su_any_r = su_any_k[4];
    wire [7:0] su_we_r, su_we_c;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_swe
        assign su_we_r[gl] = su_any_k[gl / 2] && pwin[gl / 2][2 + gl];
        assign su_we_c[gl] = su_any_k[5] && pwin[5][2 + gl];
    end endgenerate
    wire su_bank_r = pvm_waddr[3];
    wire w1_bank_r = pw1_addr[3];
    reg [7:0] off_oh [0:7];
    reg [7:0] hitS [0:7], winS [0:7];
    reg [7:0] anyS;
    reg [7:0] gw1_r [0:1], gmx_r [0:1];
    wire [1:0] sub_r;
    assign sub_r[0] = !pw16_we && su_any_r && !su_bank_r;
    assign sub_r[1] = !pw16_we && su_any_r && su_bank_r;
    wire [1:0] w1b_r;
    assign w1b_r[0] = !pw16_we && pw1_we && !w1_bank_r && !(su_any_r && !su_bank_r);
    assign w1b_r[1] = !pw16_we && pw1_we && w1_bank_r && !(su_any_r && su_bank_r);
    always @(*) begin
        for (l = 0; l < 8; l = l + 1) off_oh[l] = 8'd1 << pvm_waddr[24*l +: 3];
        for (s = 0; s < 8; s = s + 1) begin
            for (l = 0; l < 8; l = l + 1) hitS[s][l] = su_we_r[l] && off_oh[l][s];
            anyS[s] = |hitS[s];
            for (l = 0; l < 8; l = l + 1) begin
                winS[s][l] = hitS[s][l];
`ifdef OT_S8_MUT_WPRI
                for (k = 0; k < l; k = k + 1) if (hitS[s][k]) winS[s][l] = 1'b0;   // bench mutant: EARLIER lane wins
`else
                for (k = l + 1; k < 8; k = k + 1) if (hitS[s][k]) winS[s][l] = 1'b0;
`endif
            end
        end
        for (b = 0; b < 2; b = b + 1)
            for (s = 0; s < 8; s = s + 1) begin
                gw1_r[b][s] = w1b_r[b] && pw1_addr[2:0] == s[2:0];
                gmx_r[b][s] = (sub_r[b] && anyS[s]) || gw1_r[b][s];
            end
    end
    wire [1:0] ssu_r = {su_any_r && su_bank_r, su_any_r && !su_bank_r};
    wire [1:0] sw1_r = {pw1_we && w1_bank_r, pw1_we && !w1_bank_r};
    reg w_coll_r, w_bad_r;
    always @(*) begin
        w_coll_r = 1'b0; w_bad_r = 1'b0;
        if (pw1_we && pw1_addr[23:14] != 10'd0) w_bad_r = 1'b1;
        if (su_any_k[5]) begin
            for (l = 0; l < 8; l = l + 1)
                if (su_we_c[l] && (pvm_waddr[24*l+3 +: 21] != pvm_waddr[3 +: 21] || !su_we_c[0])) w_bad_r = 1'b1;
            if (pvm_waddr[23:14] != 10'd0) w_bad_r = 1'b1;
            if (pw1_we && w1_bank_r == su_bank_r) w_coll_r = 1'b1;
        end
        if (pw16_we) begin
            if (pw16_addr[3:0] != 4'd0 || pw16_addr[23:14] != 10'd0) w_bad_r = 1'b1;
            if (pw1_we || su_any_r) w_coll_r = 1'b1;
        end
    end
    reg  [255:0] l_sud;
    reg  [511:0] l_w16d;
    reg  [31:0]  l_w1d;
    reg  [9:0]   l_r16, l_rsu, l_rw1;
    reg          l_wbad, l_wbad2, l_wbad3;
    always @(posedge ck) begin
        l_sud <= pvm_wdata; l_w16d <= pw16_data; l_w1d <= pw1_data;
        l_r16 <= pw16_addr[13:4]; l_rsu <= pvm_waddr[13:4]; l_rw1 <= pw1_addr[13:4];
        l_wbad <= w_bad_r || w_coll_r; l_wbad2 <= l_wbad; l_wbad3 <= l_wbad2;
    end
    wire [1:0] l_r16w, l_m16, l_ssu, l_sw1;
    qfd_dv_s8x_kff #(.W(2), .ID(900)) u_r16 (.ck(ck), .d({2{pw16_we}}), .q(l_r16w));
    qfd_dv_s8x_kff #(.W(2), .ID(901)) u_ssu (.ck(ck), .d(ssu_r), .q(l_ssu));
    qfd_dv_s8x_kff #(.W(2), .ID(902)) u_sw1 (.ck(ck), .d(sw1_r), .q(l_sw1));
    qfd_dv_s8x_kff #(.W(2), .ID(903)) u_m16 (.ck(ck), .d({2{pw16_we}}), .q(l_m16));
    wire [1:0] l_we = l_r16w | l_ssu | l_sw1;
    wire [9:0] l_row [0:1];
    assign l_row[0] = l_r16w[0] ? l_r16 : l_ssu[0] ? l_rsu : l_rw1;
    assign l_row[1] = l_r16w[1] ? l_r16 : l_ssu[1] ? l_rsu : l_rw1;
    wire [255:0] dS;
    generate for (gs = 0; gs < 8; gs = gs + 1) begin : g_ws
        wire [7:0] lw;
        qfd_dv_s8x_kff #(.W(8), .ID(1000 + gs)) u_win (.ck(ck), .d(winS[gs]), .q(lw));
        reg [31:0] e;
        always @(*) begin
            e = 32'd0;
            for (l = 0; l < 8; l = l + 1) e = e | ({32{lw[l]}} & l_sud[32*l +: 32]);
        end
        assign dS[32*gs +: 32] = e;
    end endgenerate
    wire [255:0] wb_d [0:1];
    wire [7:0]   wb_ms [0:1];
    generate for (gb = 0; gb < 2; gb = gb + 1) begin : g_wb
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_s
            wire l16, lsu, lw1, lmx;
            qfd_dv_s8x_kff #(.W(1), .ID(1100 + 16*gb + gs)) u_16 (.ck(ck), .d(pw16_we), .q(l16));
            qfd_dv_s8x_kff #(.W(1), .ID(1150 + 16*gb + gs)) u_su (.ck(ck), .d(sub_r[gb]), .q(lsu));
            qfd_dv_s8x_kff #(.W(1), .ID(1200 + 16*gb + gs)) u_w1 (.ck(ck), .d(gw1_r[gb][gs]), .q(lw1));
            qfd_dv_s8x_kff #(.W(1), .ID(1300 + 16*gb + gs)) u_m (.ck(ck), .d(gmx_r[gb][gs]), .q(lmx));
            assign wb_d[gb][32*gs +: 32] = ({32{l16}} & l_w16d[256*gb + 32*gs +: 32]) | ({32{lsu}} & dS[32*gs +: 32]) |
                                           ({32{lw1}} & l_w1d);
            assign wb_ms[gb][gs] = l_m16[gb] | lmx;
        end
    end endgenerate
    // ---------------------------------------------------------------- registered write stage per bank (at the macros)
    wire [255:0] mwd [0:1];
    wire [9:0]   mrow [0:1];
    wire         mwe [0:1];
    wire [7:0]   mms [0:1];
    wire [255:0] rwd [0:1];   // landing D: MIF=0 the write decode; MIF=1 the relay stage (= the MIF=0 landing, one cycle early)
    wire [9:0]   rrow [0:1];
    wire         rwe [0:1];
    wire [7:0]   rms [0:1];
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_wr
        if (MIF == 0) begin : g_d
            assign rwd[bk] = wb_d[bk]; assign rrow[bk] = l_row[bk]; assign rwe[bk] = l_we[bk]; assign rms[bk] = wb_ms[bk];
        end else begin : g_r
            qfd_dv_s8x_kff #(.W(256), .ID(6400 + bk)) u_d (.ck(ck), .d(wb_d[bk]), .q(rwd[bk]));
            qfd_dv_s8x_kff #(.W(10), .ID(6410 + bk)) u_r (.ck(ck), .d(l_row[bk]), .q(rrow[bk]));
            qfd_dv_s8x_kff #(.W(1), .ID(6420 + bk)) u_e (.ck(ck), .d(l_we[bk]), .q(rwe[bk]));
            qfd_dv_s8x_kff #(.W(8), .ID(6430 + bk)) u_m (.ck(ck), .d(wb_ms[bk]), .q(rms[bk]));
        end
    end endgenerate
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_mw
        qfd_dv_s8x_kff #(.W(256), .ID(6000 + bk)) u_d (.ck(ck), .d(rwd[bk]), .q(mwd[bk]));
        qfd_dv_s8x_kff #(.W(10), .ID(6100 + bk)) u_r (.ck(ck), .d(rrow[bk]), .q(mrow[bk]));
        qfd_dv_s8x_kff #(.W(1), .ID(6200 + bk)) u_e (.ck(ck), .d(rwe[bk]), .q(mwe[bk]));
        qfd_dv_s8x_kff #(.W(8), .ID(6300 + bk)) u_m (.ck(ck), .d(rms[bk]), .q(mms[bk]));
    end endgenerate
    // ---------------------------------------------------------------- reads: 2 banks
    wire [511:0] vm_rd;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_bank
        // MIF=1: the collision compare runs one cycle early against the relay stage (rwe/rrow = next mwe/mrow)
        wire coll = MIF == 0 ? (mwe[bk] && mrow[bk] == pa_addr[4 +: 10]) : (rwe[bk] && rrow[bk] == pa_addr[4 +: 10]);
`ifdef OT_S8_MUT_COLL
        wire coll_u = 1'b0;                     // bench mutant: read of the row being written NOT suppressed
`else
        wire coll_u = coll;
`endif
        wire [255:0] wm;
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_m assign wm[32*gs +: 32] = {32{mms[bk][gs]}}; end
        wire m_rce; wire [9:0] m_ra;
        if (MIF == 0) begin : g_rd
            assign m_rce = pa_re[0] && pa_addr[3] == bk[0] && !coll_u; assign m_ra = pa_addr[4 +: 10];
        end else begin : g_rr
            qfd_dv_s8x_kff #(.W(1), .ID(6500 + bk)) u_rce (.ck(ck), .d(pa_re[0] && pa_addr[3] == bk[0] && !coll_u), .q(m_rce));
            qfd_dv_s8x_kff #(.W(10), .ID(6510 + bk)) u_ra (.ck(ck), .d(pa_addr[4 +: 10]), .q(m_ra));
        end
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck),
            .r_ce_in(m_rce),
            .r_addr_in(m_ra),
            .rd_out(vm_rd[bk*256 +: 256]),
            .w_ce_in(mwe[bk]), .w_addr_in(mrow[bk]), .wd_in(mwd[bk]), .w_mask_in(wm),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // bank / lane offsets of the read the SRAMs latch this edge (MIF=1: one cycle later, from a delayed copy)
    wire [24:0] rsel_n;
    assign rsel_n[0] = pa_addr[3];
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_rsel assign rsel_n[1 + 3*gl +: 3] = pa_addr[24*gl +: 3]; end endgenerate
    wire [24:0] rsel;
    generate if (MIF == 0) begin : g_rs0
        assign rsel = rsel_n;
    end else begin : g_rs1
        qfd_dv_s8x_kff #(.W(25), .ID(6520)) u_rs (.ck(ck), .d(rsel_n), .q(rsel));
    end endgenerate
    reg s1_bank; reg [23:0] s1_off; reg [511:0] cap;
    always @(posedge ck) begin
        s1_bank <= rsel[0];
        s1_off <= rsel[24:1];
        cap <= vm_rd;
    end
    wire [255:0] wsel;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_bk
        wire bq;
        qfd_dv_s8x_kff #(.W(1), .ID(2000 + gk)) u (.ck(ck), .d(s1_bank), .q(bq));
        assign wsel[16*gk +: 16] = bq ? cap[256 + 16*gk +: 16] : cap[16*gk +: 16];
    end endgenerate
    wire [8*32-1:0] q_n;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_l
        wire [7:0] dec = 8'd1 << s1_off[3*gl +: 3];
        wire [7:0] oh0, oh1;
        qfd_dv_s8x_kff #(.W(8), .ID(2100 + 2*gl)) u0 (.ck(ck), .d(dec), .q(oh0));
        qfd_dv_s8x_kff #(.W(8), .ID(2101 + 2*gl)) u1 (.ck(ck), .d(dec), .q(oh1));
        reg [31:0] e;
        always @(*) begin
            e = 32'd0;
            for (s = 0; s < 8; s = s + 1)
                e = e | {({16{oh1[s]}} & wsel[32*s + 16 +: 16]), ({16{oh0[s]}} & wsel[32*s +: 16])};
        end
        assign q_n[32*gl +: 32] = e;
    end endgenerate
    always @(posedge ck) q <= q_n;
    // ---------------------------------------------------------------- faults (read range of this replica, write checks)
    function automatic bad_vec(input [7:0] re_, input [8*24-1:0] ad);
        integer kk;
        begin
            bad_vec = 1'b0;
            for (kk = 0; kk < 8; kk = kk + 1)
                if (re_[kk] && (ad[24*kk+4 +: 20] != ad[4 +: 20])) bad_vec = 1'b1;
            for (kk = 0; kk < 8; kk = kk + 1)
                if (re_[kk] && (ad[24*kk+3] != ad[3])) bad_vec = 1'b1;
            if (re_[0] && (ad[23:14] != 10'd0)) bad_vec = 1'b1;
            if (re_ != 8'd0 && !re_[0]) bad_vec = 1'b1;
        end
    endfunction
    reg rd_bad_q;
    always @(posedge ck) rd_bad_q <= bad_vec(pa_re, pa_addr);
    always @(posedge ck or negedge rl1)
        if (!rl1) fault <= 1'b0;
        else fault <= fault | rd_bad_q | l_wbad3;
endmodule
