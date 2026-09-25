`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MBIST / repair verification top (driven by rtl/test/mbist_harness.cpp,
// scenarios from tools/rtl_mbist_campaign.py).
//
// One shared ot_mbist_ctrl tests two compiled SRAM macros of different port
// styles and geometries and one compiled ROM:
//   m0  ot_sram_1rw_256x64_m4_r2c2   (1RW,  64 rows x 264 columns + 2 spare rows)
//   m1  ot_sram_1r1w_512x128_m4_r2c2 (1R1W, 128 rows x 520 columns + 2 spare rows)
//   m2  ot_rom_1024x72_m8            (via map from +OT_ROM_DIR, instance trom_r0_c0)
// compiled with +define+OT_MEM_FAULTS.  +FAULTS=<file> lists injected faults,
// one per line: "macro kind row col aggr_row aggr_col value" (physical indices,
// kinds as in tools/mem_compiler/behav.py).  +ROMSIG=<hex> is the expected ROM
// signature (tools/mem_compiler/rom_gen.py personalise).  +HOLD stalls the
// controller on a pseudo-random pattern.  +TRACE prints every failure event
// the BIRA records.
//
// After BIST: every SRAM is written and read back through the FUNCTIONAL
// port (repair active) and the repair registers are rotated once around the
// fuse scan chain (m0 -> m1 -> m0) and must come back unchanged.
// ---------------------------------------------------------------------------
module tb_mbist (input wire clk);
    localparam integer AMAX = 10, DMAX = 128, RMAX = 7, CMAX = 7;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    reg hold = 1'b0;
    integer cyc = 0;

    // ---- controller ------------------------------------------------------------
    wire busy, done, pass;
    wire [3:0] sram_status;
    wire [1:0] rom_status;
    wire [1:0] t_sel, rep_clear, rep_load;
    wire t_req, t_we, t_pol;
    wire [AMAX-1:0] t_addr;
    wire [1:0] t_bg;
    wire c0_fail, c1_fail;
    wire [DMAX-1:0] c0_vec, c1_vec;
    wire [RMAX-1:0] c0_row, c1_row;
    wire [1:0] rr_en, cr_en;
    wire [2*RMAX-1:0] rr_addr;
    wire [2*CMAX-1:0] cr_sel;
    wire [0:0] rom_sel, rom_match;
    wire rom_clear, rom_req;
    wire [AMAX-1:0] rom_addr;
    wire [7:0] dbg_ev, dbg_must;
    wire dbg_ovf;
    reg [31:0] exp_sig;
    reg cfg_we = 1'b0;
    reg [3:0] cfg_addr = 4'd0;
    reg [15:0] cfg_wdata = 16'd0;
    wire [15:0] cfg_rdata;
    // +ALG<k>=hex reprograms March element k, +BG=hex the background enables
    reg [15:0] alg_prog [0:8];
    reg [8:0] alg_set = 9'd0;
    integer ai;
    initial begin
        if ($value$plusargs("ALG0=%h", alg_prog[0])) alg_set[0] = 1'b1;
        if ($value$plusargs("ALG1=%h", alg_prog[1])) alg_set[1] = 1'b1;
        if ($value$plusargs("ALG2=%h", alg_prog[2])) alg_set[2] = 1'b1;
        if ($value$plusargs("ALG3=%h", alg_prog[3])) alg_set[3] = 1'b1;
        if ($value$plusargs("ALG4=%h", alg_prog[4])) alg_set[4] = 1'b1;
        if ($value$plusargs("ALG5=%h", alg_prog[5])) alg_set[5] = 1'b1;
        if ($value$plusargs("ALG6=%h", alg_prog[6])) alg_set[6] = 1'b1;
        if ($value$plusargs("ALG7=%h", alg_prog[7])) alg_set[7] = 1'b1;
        if ($value$plusargs("BG=%h", alg_prog[8])) alg_set[8] = 1'b1;
    end

    ot_mbist_ctrl #(.N_SRAM(2), .N_ROM(1), .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX),
                    .NSR(2), .NSC(2), .E(6), .SRAM_WORDS({32'd512, 32'd256}), .ROM_WORDS(32'd1024)) u_ctrl (
        .clk(clk), .rst_n(rst_n), .start(start), .hold(hold), .busy(busy), .done(done), .pass(pass),
        .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_wdata(cfg_wdata), .cfg_rdata(cfg_rdata),
        .sram_status(sram_status), .rom_status(rom_status),
        .t_sel(t_sel), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail({c1_fail, c0_fail}), .c_failvec({c1_vec, c0_vec}), .c_row({c1_row, c0_row}),
        .rep_clear(rep_clear), .rep_load(rep_load), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
        .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
        .rom_sel(rom_sel), .rom_clear(rom_clear), .rom_req(rom_req), .rom_addr(rom_addr),
        .rom_match(rom_match), .dbg_bira_events(dbg_ev), .dbg_bira_must_cols(dbg_must),
        .dbg_bira_overflow(dbg_ovf));

    // ---- functional drivers (idle during BIST) ----------------------------------
    reg f0_r, f0_w, f1_r, f1_w;
    reg [7:0] f0_addr;
    reg [8:0] f1_addr;
    reg [63:0] f0_wd;
    reg [127:0] f1_wd;
    wire [63:0] f0_rd;
    wire [127:0] f1_rd;
    reg rep_shift = 1'b0;
    wire so0, so1;

    // ---- m0: 1RW 256 x 64 --------------------------------------------------------
    wire m0_ce, m0_we; wire [7:0] m0_addr; wire [63:0] m0_wd, m0_wm, m0_rd;
    wire [1:0] m0_rr_en, m0_cr_en; wire [11:0] m0_rr_addr, m0_cr_sel;
    wire [27:0] m0_rep;
    ot_mbist_sram_collar #(.PORTS(0), .WORDS(256), .DW(64), .MUX(4), .NSR(2), .NSC(2), .AMAX(AMAX),
                           .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX), .NSRB(2), .NSCB(2)) u_c0 (
        .clk(clk), .rst_n(rst_n),
        .f_r_ce(f0_r), .f_r_addr(f0_addr), .f_rd(f0_rd), .f_w_ce(f0_w), .f_w_addr(f0_addr),
        .f_wd(f0_wd), .f_wmask({64{1'b1}}),
        .m_ce(m0_ce), .m_we(m0_we), .m_addr(m0_addr), .m_r_ce(), .m_r_addr(), .m_w_ce(), .m_w_addr(),
        .m_wd(m0_wd), .m_wmask(m0_wm), .m_rd(m0_rd),
        .m_rr_en(m0_rr_en), .m_rr_addr(m0_rr_addr), .m_cr_en(m0_cr_en), .m_cr_sel(m0_cr_sel),
        .t_en(t_sel[0]), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail(c0_fail), .c_failvec(c0_vec), .c_row(c0_row),
        .rep_clear(rep_clear[0]), .rep_load(rep_load[0]), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
        .rep_cr_en(cr_en), .rep_cr_sel(cr_sel), .rep_shift_en(rep_shift), .rep_si(so1), .rep_so(so0),
        .rep_q(m0_rep));
    ot_sram_1rw_256x64_m4_r2c2 u_m0 (
        .clk(clk), .ce_in(m0_ce), .we_in(m0_we), .addr_in(m0_addr), .wd_in(m0_wd), .w_mask_in(m0_wm),
        .rd_out(m0_rd), .rr_en(m0_rr_en), .rr_addr(m0_rr_addr), .cr_en(m0_cr_en), .cr_sel(m0_cr_sel));

    // ---- m1: 1R1W 512 x 128 ------------------------------------------------------
    wire m1_rce, m1_wce; wire [8:0] m1_raddr, m1_waddr; wire [127:0] m1_wd, m1_wm, m1_rd;
    wire [1:0] m1_rr_en, m1_cr_en; wire [13:0] m1_rr_addr, m1_cr_sel;
    wire [31:0] m1_rep;
    ot_mbist_sram_collar #(.PORTS(1), .WORDS(512), .DW(128), .MUX(4), .NSR(2), .NSC(2), .AMAX(AMAX),
                           .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX), .NSRB(2), .NSCB(2)) u_c1 (
        .clk(clk), .rst_n(rst_n),
        .f_r_ce(f1_r), .f_r_addr(f1_addr), .f_rd(f1_rd), .f_w_ce(f1_w), .f_w_addr(f1_addr),
        .f_wd(f1_wd), .f_wmask({128{1'b1}}),
        .m_ce(), .m_we(), .m_addr(), .m_r_ce(m1_rce), .m_r_addr(m1_raddr), .m_w_ce(m1_wce),
        .m_w_addr(m1_waddr), .m_wd(m1_wd), .m_wmask(m1_wm), .m_rd(m1_rd),
        .m_rr_en(m1_rr_en), .m_rr_addr(m1_rr_addr), .m_cr_en(m1_cr_en), .m_cr_sel(m1_cr_sel),
        .t_en(t_sel[1]), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail(c1_fail), .c_failvec(c1_vec), .c_row(c1_row),
        .rep_clear(rep_clear[1]), .rep_load(rep_load[1]), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
        .rep_cr_en(cr_en), .rep_cr_sel(cr_sel), .rep_shift_en(rep_shift), .rep_si(so0), .rep_so(so1),
        .rep_q(m1_rep));
    ot_sram_1r1w_512x128_m4_r2c2 u_m1 (
        .clk(clk), .r_ce_in(m1_rce), .r_addr_in(m1_raddr), .rd_out(m1_rd), .w_ce_in(m1_wce),
        .w_addr_in(m1_waddr), .wd_in(m1_wd), .w_mask_in(m1_wm),
        .rr_en(m1_rr_en), .rr_addr(m1_rr_addr), .cr_en(m1_cr_en), .cr_sel(m1_cr_sel));

    // ---- m2: ROM 1024 x 72 -------------------------------------------------------
    wire r_ce; wire [9:0] r_addr; wire [71:0] r_rd;
    wire [31:0] rom_sig;
    ot_mbist_rom_collar #(.WORDS(1024), .DW(72), .AMAX(AMAX)) u_r0 (
        .clk(clk), .rst_n(rst_n), .f_ce(1'b0), .f_addr(10'd0), .f_rd(),
        .m_ce(r_ce), .m_addr(r_addr), .m_rd(r_rd),
        .t_en(rom_sel[0]), .t_clear(rom_clear), .t_req(rom_req), .t_addr(rom_addr), .exp_sig(exp_sig),
        .sig(rom_sig), .sig_match(rom_match[0]), .sig_busy());
    ot_rom_1024x72_m8 #(.INSTANCE("trom_r0_c0")) u_m2 (.clk(clk), .ce_in(r_ce), .addr_in(r_addr), .rd_out(r_rd));

    // ---- fault injection ---------------------------------------------------------
    reg [8*512-1:0] fname;
    integer fd, n, fm, fk, fr, fc, far, fac, fv, nf = 0;
    integer slot0 = 0, slot1 = 0, slot2 = 0;
    integer fl_m [0:23], fl_k [0:23], fl_r [0:23], fl_c [0:23], fl_ar [0:23], fl_ac [0:23], fl_v [0:23];
    reg hold_mode = 1'b0, trace = 1'b0;
    initial begin
        if (!$value$plusargs("ROMSIG=%h", exp_sig)) exp_sig = 32'h0;
        if ($test$plusargs("HOLD")) hold_mode = 1'b1;
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if ($value$plusargs("FAULTS=%s", fname)) begin
            fd = $fopen(fname, "r");
            while (fd != 0 && !$feof(fd) && nf < 24) begin
                n = $fscanf(fd, "%d %d %d %d %d %d %d\n", fm, fk, fr, fc, far, fac, fv);
                if (n == 7) begin
                    fl_m[nf] = fm; fl_k[nf] = fk; fl_r[nf] = fr; fl_c[nf] = fc;
                    fl_ar[nf] = far; fl_ac[nf] = fac; fl_v[nf] = fv; nf = nf + 1;
                end
            end
            if (fd != 0) $fclose(fd);
        end
    end
    integer fi;
    always @(posedge clk) if (cyc == 2) begin
        for (fi = 0; fi < nf; fi = fi + 1) begin
            if (fl_m[fi] == 0) begin
                u_m0.f_kind[slot0] = fl_k[fi][3:0]; u_m0.f_r[slot0] = fl_r[fi]; u_m0.f_c[slot0] = fl_c[fi];
                u_m0.f_ar[slot0] = fl_ar[fi]; u_m0.f_ac[slot0] = fl_ac[fi]; u_m0.f_v[slot0] = fl_v[fi][1:0];
                slot0 = slot0 + 1;
            end else if (fl_m[fi] == 1) begin
                u_m1.f_kind[slot1] = fl_k[fi][3:0]; u_m1.f_r[slot1] = fl_r[fi]; u_m1.f_c[slot1] = fl_c[fi];
                u_m1.f_ar[slot1] = fl_ar[fi]; u_m1.f_ac[slot1] = fl_ac[fi]; u_m1.f_v[slot1] = fl_v[fi][1:0];
                slot1 = slot1 + 1;
            end else begin
                u_m2.f_kind[slot2] = fl_k[fi][3:0]; u_m2.f_r[slot2] = fl_r[fi]; u_m2.f_c[slot2] = fl_c[fi];
                u_m2.f_ar[slot2] = fl_ar[fi]; u_m2.f_ac[slot2] = fl_ac[fi]; u_m2.f_v[slot2] = fl_v[fi][1:0];
                slot2 = slot2 + 1;
            end
        end
        $display("FAULTS injected=%0d", nf);
    end

    // ---- observation ---------------------------------------------------------------
    reg [31:0] lfsr = 32'hACE1ACE1;
    always @(posedge clk) begin
        lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
        hold <= hold_mode && busy && (lfsr[2:0] == 3'd0);
        if (trace && u_ctrl.bira_rec && u_ctrl.ev_fail)
            $display("FAILEV m=%0d row=%0d vec=%h", u_ctrl.msel, u_ctrl.ev_row, u_ctrl.ev_vec);
        if (u_ctrl.st == 4'd6 && u_ctrl.bira_done)
            $display("ANA m=%0d ok=%0d unrep=%0d events=%0d must_cols=%0d rr_en=%b rr_addr=%h cr_en=%b cr_sel=%h",
                     u_ctrl.msel, u_ctrl.bira_ok, dbg_ovf, dbg_ev, dbg_must, rr_en, rr_addr, cr_en, cr_sel);
    end

    // ---- sequence --------------------------------------------------------------------
    localparam [3:0] P_RESET = 0, P_BIST = 1, P_F0W = 2, P_F0R = 3, P_F1W = 4, P_F1R = 5, P_FUSE = 6, P_END = 7;
    reg [3:0] ph = P_RESET;
    integer i = 0, bad0 = 0, bad1 = 0, bist_cycles = 0, shifts = 0;
    reg [27:0] rep0_before;
    reg [31:0] rep1_before;
    reg rd_pend = 1'b0, rd_pend2 = 1'b0, rd_m = 1'b0, rd_m2 = 1'b0;
    reg [9:0] rd_i, rd_i2;
    function automatic [127:0] fpat(input integer a, input integer m);
        fpat = {4{a[7:0] ^ 8'h5A, 8'hC3 ^ m[7:0], a[7:0], 8'h96}};
    endfunction
    function automatic [63:0] fpat64(input integer a);
        reg [127:0] w;
        begin w = fpat(a, 0); fpat64 = w[63:0]; end
    endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        start <= 1'b0;
        f0_r <= 1'b0; f0_w <= 1'b0; f1_r <= 1'b0; f1_w <= 1'b0; rep_shift <= 1'b0;
        rd_pend <= 1'b0;
        rd_pend2 <= rd_pend; rd_i2 <= rd_i; rd_m2 <= rd_m;
        if (cyc == 5) rst_n <= 1'b1;
        case (ph)
            P_RESET: begin
                cfg_we <= 1'b0;
                if (cyc >= 6 && cyc < 15 && alg_set[cyc - 6]) begin
                    cfg_we <= 1'b1; cfg_addr <= cyc[3:0] - 4'd6; cfg_wdata <= alg_prog[cyc - 6];
                end
                if (cyc == 16) begin start <= 1'b1; ph <= P_BIST; end
            end
            P_BIST: begin
                bist_cycles <= bist_cycles + 1;
                if (done) begin
                    $display("SRAM m=0 status=%0d rep=%h", sram_status[1:0], m0_rep);
                    $display("SRAM m=1 status=%0d rep=%h", sram_status[3:2], m1_rep);
                    $display("ROM m=0 status=%0d sig=%h exp=%h", rom_status[1:0], rom_sig, exp_sig);
                    $display("BIST pass=%0d cycles=%0d", pass, bist_cycles);
                    ph <= P_F0W; i <= 0;
                end
            end
            // functional write/read of every address, repair active
            P_F0W: begin
                f0_w <= 1'b1; f0_addr <= i[7:0]; f0_wd <= fpat64(i);
                if (i == 255) begin i <= 0; ph <= P_F0R; end else i <= i + 1;
            end
            P_F0R: begin
                if (i <= 255) begin f0_r <= 1'b1; f0_addr <= i[7:0]; rd_pend <= 1'b1; rd_m <= 1'b0; rd_i <= i[9:0]; i <= i + 1; end
                else if (!rd_pend && !rd_pend2) begin i <= 0; ph <= P_F1W; end
            end
            P_F1W: begin
                f1_w <= 1'b1; f1_addr <= i[8:0]; f1_wd <= fpat(i, 1);
                if (i == 511) begin i <= 0; ph <= P_F1R; end else i <= i + 1;
            end
            P_F1R: begin
                if (i <= 511) begin f1_r <= 1'b1; f1_addr <= i[8:0]; rd_pend <= 1'b1; rd_m <= 1'b1; rd_i <= i[9:0]; i <= i + 1; end
                else if (!rd_pend && !rd_pend2) begin
                    rep0_before <= m0_rep; rep1_before <= m1_rep; shifts <= 0; ph <= P_FUSE;
                end
            end
            P_FUSE: begin
                if (shifts < 60) begin rep_shift <= 1'b1; shifts <= shifts + 1; end
                else ph <= P_END;
            end
            default: begin
                $display("FUNC m=0 mismatches=%0d", bad0);
                $display("FUNC m=1 mismatches=%0d", bad1);
                $display("FUSE rotate_ok=%0d m0=%h m1=%h", (m0_rep == rep0_before) && (m1_rep == rep1_before),
                         m0_rep, m1_rep);
                $finish;
            end
        endcase
        if (rd_pend2 && !rd_m2 && f0_rd !== fpat64(rd_i2)) bad0 <= bad0 + 1;
        if (rd_pend2 && rd_m2 && f1_rd !== fpat(rd_i2, 1)) bad1 <= bad1 + 1;
        if (cyc > 400000) begin $display("TIMEOUT st=%0d", u_ctrl.st); $finish; end
    end
endmodule
