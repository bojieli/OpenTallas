`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Memory subsystem of the hardwired decode core (ot_hdc_core) built from the
// ASAP7 compiled macros in physical/asap7_memory_macros (tools/mem_compiler).
//
// It presents exactly the synchronous-read ports the core expects (one cycle
// from an enabled read to the data, data held while the read enable is low)
// and replaces the behavioural arrays of rtl/test/tb_hdc_core.sv:
//
//   program ROM   4,096 x 1,024  4 x ot_rom_4096x266_m8   (256 data + 10 SECDED each)
//   constant ROM  4,096 x 64     1 x ot_rom_4096x72_m8    (64 + 8 SECDED)
//   weight ROM    WROM_ROWS*8,192 x G*256
//                                WROM_ROWS x 4G ot_rom_8192x266_m8 (256 + 10 SECDED)
//   KV SRAM       1,024 x 512, G read ports, one 32-bit element write port
//                                G replicas x 2 x ot_sram_1r1w_1024x256_m2_r2c2
//                                (one replica per read port; every write goes to all
//                                replicas; read-before-write; spare rows/columns)
//   vector memory 4,096 x 32, G+3 read and G+2 write ports per cycle
//                                a standard-cell register file (below):
//                                measured on the campaign it has up to 7 reads and
//                                4 writes in one cycle and 128 same-bank write pairs
//                                under 4-way banking, so no 1R1W/2RW macro organisation
//                                keeps the schedule; it is covered by scan, not MBIST.
//
// ROM content is not in this RTL: each ROM instance loads the via map
// <OT_ROM_DIR>/<instance>.viamap.hex produced by
// tools/mem_compiler/rom_gen.py personalise, and SECDED corrects a single bad
// via per word on the read path (combinational, after the macro's output
// register, so the core sees the same cycle).  ecc_corrected / ecc_uncorrectable
// count what the decoders saw.
//
// Self-test and repair: every KV macro sits behind an ot_mbist_sram_collar and
// every ROM macro behind an ot_mbist_rom_collar, all driven by ONE shared
// ot_mbist_ctrl (rtl/dft): March C- with BIRA and spare row/column repair on the
// KV SRAM, CRC-32 signature on every ROM against bist_exp_sig (the per-instance
// signatures rom_gen.py personalise computed from the via maps).  The repair
// registers form one scan chain (rep_scan_*) for fuse read-out and boot load.
// The collars are combinational pass-through while not selected, so the core
// sees the same cycles.
//
// Test access (tst_*): the debug port in front of the collars' functional side.
// While tst_kv_en is high the KV macros take word-wide writes from tst_kv_*
// (to every replica) and replica 0 reads back tst_kv_raddr; this is also how a
// test bench preloads the golden KV cache and dumps it after a token.
// ---------------------------------------------------------------------------
module ot_hdc_memsys #(
    parameter integer INSTR_BITS = 1024,
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer AW = 24,
    parameter integer PAW = 12,
    parameter integer WROM_ROWS = 6,
    parameter integer N_ROM = INSTR_BITS / 256 + 1 + WROM_ROWS * (G * W * 16 / 256),
    parameter integer N_KV  = G * (W * 32 / 256)
) (
    input  wire              clk,
    input  wire              rst_n,
    // memory BIST
    input  wire              bist_start,
    output wire              bist_busy,
    output wire              bist_done,
    output wire              bist_pass,
    output wire [2*N_KV-1:0] bist_sram_status,
    output wire [2*N_ROM-1:0] bist_rom_status,
    input  wire [32*N_ROM-1:0] bist_exp_sig,
    input  wire              rep_scan_en,
    input  wire              rep_scan_in,
    output wire              rep_scan_out,
    // program ROM
    input  wire              prog_re,
    input  wire [PAW-1:0]    prog_addr,
    output wire [INSTR_BITS-1:0] prog_q,
    // weight ROM
    input  wire              wrom_re,
    input  wire [AW-1:0]     wrom_addr,
    output wire [G*W*16-1:0] wrom_q,
    // constant ROM
    input  wire              crom_re,
    input  wire [AW-1:0]     crom_addr,
    output wire [63:0]       crom_q,
    // KV SRAM
    input  wire              kv_re,
    input  wire [G*AW-1:0]   kv_raddr,
    output wire [G*W*32-1:0] kv_q,
    input  wire              kv_we,
    input  wire [AW-1:0]     kv_waddr,
    input  wire [31:0]       kv_wdata,
    // vector memory
    input  wire [G-1:0]      vx_re,
    input  wire [G*AW-1:0]   vx_addr,
    output reg  [G*32-1:0]   vx_q,
    input  wire              va_re,
    input  wire [AW-1:0]     va_addr,
    output reg  [31:0]       va_q,
    input  wire              vb_re,
    input  wire [AW-1:0]     vb_addr,
    output reg  [31:0]       vb_q,
    input  wire              vc_re,
    input  wire [AW-1:0]     vc_addr,
    output reg  [31:0]       vc_q,
    input  wire [G-1:0]      vw_me_we,
    input  wire [G*AW-1:0]   vw_me_addr,
    input  wire [G*W-1:0]    vw_me_mask,
    input  wire [G*W*32-1:0] vw_me_data,
    input  wire              vw_su_we,
    input  wire [AW-1:0]     vw_su_addr,
    input  wire [31:0]       vw_su_data,
    input  wire              vw_rd_we,
    input  wire [AW-1:0]     vw_rd_addr,
    input  wire [31:0]       vw_rd_data,
    // test / debug access
    input  wire              tst_kv_en,
    input  wire              tst_kv_we,
    input  wire [9:0]        tst_kv_waddr,
    input  wire [W*32-1:0]   tst_kv_wdata,
    input  wire              tst_kv_re,
    input  wire [9:0]        tst_kv_raddr,
    output wire [W*32-1:0]   tst_kv_q,
    input  wire [11:0]       tst_vm_addr,
    output wire [31:0]       tst_vm_q,
    // ROM SECDED event counters
    output reg  [31:0]       ecc_corrected,
    output reg  [31:0]       ecc_uncorrectable
);
    localparam integer KVW = W * 32;          // 512: one KV word
    localparam integer KVT = KVW / 256;       // KV column tiles per replica
    localparam integer WT  = G * W * 16 / 256; // weight ROM column tiles
    localparam integer PT  = INSTR_BITS / 256; // program ROM column tiles
    localparam integer AMAX = 13, DMAX = 256, RMAX = 10, CMAX = 8;

    // ---------------- shared BIST controller ----------------
    wire [N_KV-1:0] t_sel, rep_clear, rep_load, c_fail;
    wire [N_KV*DMAX-1:0] c_failvec;
    wire [N_KV*RMAX-1:0] c_row;
    wire t_req, t_we, t_pol;
    wire [1:0] t_bg;
    wire [AMAX-1:0] t_addr, rom_addr;
    wire [1:0] rr_en, cr_en;
    wire [2*RMAX-1:0] rr_addr;
    wire [2*CMAX-1:0] cr_sel;
    wire [N_ROM-1:0] rom_sel, rom_match;
    wire rom_clear, rom_req;
    wire [N_KV:0] scan;
    assign scan[0] = rep_scan_in;
    assign rep_scan_out = scan[N_KV];
    ot_mbist_ctrl #(.N_SRAM(N_KV), .N_ROM(N_ROM), .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX),
                    .NSR(2), .NSC(2), .E(6), .SRAM_WORDS({N_KV{32'd1024}}),
                    .ROM_WORDS({{(WROM_ROWS * WT){32'd8192}}, 32'd4096, {PT{32'd4096}}})) u_bist (
        .clk(clk), .rst_n(rst_n), .start(bist_start), .hold(1'b0),
        .busy(bist_busy), .done(bist_done), .pass(bist_pass),
        .cfg_we(1'b0), .cfg_addr(4'd0), .cfg_wdata(16'd0), .cfg_rdata(),
        .sram_status(bist_sram_status), .rom_status(bist_rom_status),
        .t_sel(t_sel), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail(c_fail), .c_failvec(c_failvec), .c_row(c_row),
        .rep_clear(rep_clear), .rep_load(rep_load), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
        .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
        .rom_sel(rom_sel), .rom_clear(rom_clear), .rom_req(rom_req), .rom_addr(rom_addr),
        .rom_match(rom_match),
        .dbg_bira_events(), .dbg_bira_must_cols(), .dbg_bira_overflow());

    // ---------------- program ROM ----------------
    wire [PT-1:0] p_cor, p_unc;
    genvar t, r, q;
    generate
        for (t = 0; t < PT; t = t + 1) begin : g_prog
            wire [265:0] cw, m_rd;
            wire m_ce;
            wire [11:0] m_addr;
            ot_mbist_rom_collar #(.WORDS(4096), .DW(266), .AMAX(AMAX)) u_col (
                .clk(clk), .rst_n(rst_n), .f_ce(prog_re), .f_addr(prog_addr[11:0]), .f_rd(cw),
                .m_ce(m_ce), .m_addr(m_addr), .m_rd(m_rd),
                .t_en(rom_sel[t]), .t_clear(rom_clear), .t_req(rom_req), .t_addr(rom_addr),
                .exp_sig(bist_exp_sig[32*t +: 32]), .sig(), .sig_match(rom_match[t]), .sig_busy());
            ot_rom_4096x266_m8 #(.INSTANCE($sformatf("prog_r0_c%0d", t))) u_rom (
                .clk(clk), .ce_in(m_ce), .addr_in(m_addr), .rd_out(m_rd));
            ot_rom_secded_dec #(.K(256)) u_dec (.cw(cw), .data(prog_q[t*256 +: 256]),
                                               .corrected(p_cor[t]), .uncorrectable(p_unc[t]));
        end
    endgenerate

    // ---------------- constant ROM ----------------
    wire [71:0] c_cw, c_mrd;
    wire c_cor, c_unc, c_mce;
    wire [11:0] c_maddr;
    ot_mbist_rom_collar #(.WORDS(4096), .DW(72), .AMAX(AMAX)) u_crom_col (
        .clk(clk), .rst_n(rst_n), .f_ce(crom_re), .f_addr(crom_addr[11:0]), .f_rd(c_cw),
        .m_ce(c_mce), .m_addr(c_maddr), .m_rd(c_mrd),
        .t_en(rom_sel[PT]), .t_clear(rom_clear), .t_req(rom_req), .t_addr(rom_addr),
        .exp_sig(bist_exp_sig[32*PT +: 32]), .sig(), .sig_match(rom_match[PT]), .sig_busy());
    ot_rom_4096x72_m8 #(.INSTANCE("crom_r0_c0")) u_crom (
        .clk(clk), .ce_in(c_mce), .addr_in(c_maddr), .rd_out(c_mrd));
    ot_rom_secded_dec #(.K(64)) u_crom_dec (.cw(c_cw), .data(crom_q), .corrected(c_cor), .uncorrectable(c_unc));

    // ---------------- weight ROM ----------------
    // Row tile r holds words [r*8192, (r+1)*8192); only the addressed row tile is
    // enabled, and the row select is captured with the read so the output stays
    // on the last-read tile while wrom_re is low, as the behavioural array did.
    reg  [3:0] w_sel;
    reg        w_valid;
    wire [WT-1:0] w_cor, w_unc;
    wire [G*W*16-1:0] w_row_data [0:WROM_ROWS-1];
    wire [WT-1:0] w_row_cor [0:WROM_ROWS-1];
    wire [WT-1:0] w_row_unc [0:WROM_ROWS-1];
    generate
        for (r = 0; r < WROM_ROWS; r = r + 1) begin : g_wrow
            wire ce = wrom_re && (wrom_addr[16:13] == r);
            for (t = 0; t < WT; t = t + 1) begin : g_wcol
                localparam integer RI = PT + 1 + r * WT + t;
                wire [265:0] cw, m_rd;
                wire m_ce;
                wire [12:0] m_addr;
                ot_mbist_rom_collar #(.WORDS(8192), .DW(266), .AMAX(AMAX)) u_col (
                    .clk(clk), .rst_n(rst_n), .f_ce(ce), .f_addr(wrom_addr[12:0]), .f_rd(cw),
                    .m_ce(m_ce), .m_addr(m_addr), .m_rd(m_rd),
                    .t_en(rom_sel[RI]), .t_clear(rom_clear), .t_req(rom_req), .t_addr(rom_addr),
                    .exp_sig(bist_exp_sig[32*RI +: 32]), .sig(), .sig_match(rom_match[RI]), .sig_busy());
                ot_rom_8192x266_m8 #(.INSTANCE($sformatf("wrom_r%0d_c%0d", r, t))) u_rom (
                    .clk(clk), .ce_in(m_ce), .addr_in(m_addr), .rd_out(m_rd));
                ot_rom_secded_dec #(.K(256)) u_dec (.cw(cw), .data(w_row_data[r][t*256 +: 256]),
                                                   .corrected(w_row_cor[r][t]), .uncorrectable(w_row_unc[r][t]));
            end
        end
    endgenerate
    always @(posedge clk)
        if (wrom_re) begin
            w_sel <= wrom_addr[16:13];
            w_valid <= (wrom_addr[16:13] < WROM_ROWS);
        end
    assign wrom_q = w_valid ? w_row_data[w_sel] : {(G*W*16){1'b0}};
    assign w_cor = w_valid ? w_row_cor[w_sel] : {WT{1'b0}};
    assign w_unc = w_valid ? w_row_unc[w_sel] : {WT{1'b0}};

    // ---------------- KV SRAM ----------------
    wire [KVW-1:0] kv_rep_q [0:G-1];
    generate
        for (q = 0; q < G; q = q + 1) begin : g_kvrep
            for (t = 0; t < KVT; t = t + 1) begin : g_kvcol
                // functional element write: this tile holds elements [t*8, t*8+8)
                wire f_hit = kv_we && (kv_waddr[3] == t);
                wire [255:0] f_mask = {224'd0, 32'hFFFF_FFFF} << (32 * kv_waddr[2:0]);
                wire         w_ce  = tst_kv_en ? tst_kv_we : f_hit;
                wire [9:0]   w_a   = tst_kv_en ? tst_kv_waddr : kv_waddr[13:4];
                wire [255:0] w_d   = tst_kv_en ? tst_kv_wdata[t*256 +: 256] : {8{kv_wdata}};
                wire [255:0] w_m   = tst_kv_en ? {256{1'b1}} : f_mask;
                wire         r_ce  = tst_kv_en ? (tst_kv_re && q == 0) : kv_re;
                wire [9:0]   r_a   = tst_kv_en ? tst_kv_raddr : kv_raddr[q*AW +: 10];
                localparam integer KI = q * KVT + t;
                wire m_r_ce, m_w_ce;
                wire [9:0] m_r_addr, m_w_addr;
                wire [255:0] m_wd, m_wmask, m_rd;
                wire [1:0] m_rr_en, m_cr_en;
                wire [17:0] m_rr_addr;
                wire [15:0] m_cr_sel;
                ot_mbist_sram_collar #(.PORTS(1), .WORDS(1024), .DW(256), .MUX(2), .NSR(2), .NSC(2),
                                       .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX),
                                       .NSRB(2), .NSCB(2)) u_col (
                    .clk(clk), .rst_n(rst_n),
                    .f_r_ce(r_ce), .f_r_addr(r_a), .f_rd(kv_rep_q[q][t*256 +: 256]),
                    .f_w_ce(w_ce), .f_w_addr(w_a), .f_wd(w_d), .f_wmask(w_m),
                    .m_ce(), .m_we(), .m_addr(), .m_r_ce(m_r_ce), .m_r_addr(m_r_addr),
                    .m_w_ce(m_w_ce), .m_w_addr(m_w_addr), .m_wd(m_wd), .m_wmask(m_wmask), .m_rd(m_rd),
                    .m_rr_en(m_rr_en), .m_rr_addr(m_rr_addr), .m_cr_en(m_cr_en), .m_cr_sel(m_cr_sel),
                    .t_en(t_sel[KI]), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
                    .c_fail(c_fail[KI]), .c_failvec(c_failvec[KI*DMAX +: DMAX]), .c_row(c_row[KI*RMAX +: RMAX]),
                    .rep_clear(rep_clear[KI]), .rep_load(rep_load[KI]), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
                    .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
                    .rep_shift_en(rep_scan_en), .rep_si(scan[KI]), .rep_so(scan[KI + 1]), .rep_q());
                ot_sram_1r1w_1024x256_m2_r2c2 u_sram (
                    .clk(clk), .r_ce_in(m_r_ce), .r_addr_in(m_r_addr), .rd_out(m_rd),
                    .w_ce_in(m_w_ce), .w_addr_in(m_w_addr), .wd_in(m_wd), .w_mask_in(m_wmask),
                    .rr_en(m_rr_en), .rr_addr(m_rr_addr), .cr_en(m_cr_en), .cr_sel(m_cr_sel));
            end
            assign kv_q[q*KVW +: KVW] = kv_rep_q[q];
        end
    endgenerate
    assign tst_kv_q = kv_rep_q[0];

    // ---------------- vector memory: register file ----------------
    reg [31:0] vm [0:4095];
    integer i, l, g;
    initial for (i = 0; i < 4096; i = i + 1) vm[i] = 32'd0;
    always @(posedge clk) begin
        for (g = 0; g < G; g = g + 1)
            if (vx_re[g]) vx_q[32*g +: 32] <= vm[vx_addr[g*AW +: 12]];
        if (va_re) va_q <= vm[va_addr[11:0]];
        if (vb_re) vb_q <= vm[vb_addr[11:0]];
        if (vc_re) vc_q <= vm[vc_addr[11:0]];
        for (g = 0; g < G; g = g + 1)
            if (vw_me_we[g])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[g*W + l]) vm[{vw_me_addr[g*AW +: 8], 4'b0} + l] <= vw_me_data[32*(g*W + l) +: 32];
        if (vw_su_we) vm[vw_su_addr[11:0]] <= vw_su_data;
        if (vw_rd_we) vm[vw_rd_addr[11:0]] <= vw_rd_data;
    end
    assign tst_vm_q = vm[tst_vm_addr];

    // ---------------- SECDED event counters ----------------
    // a decoder's flags are valid in the cycle after its macro was read
    reg p_rd, c_rd, w_rd;
    integer n;
    reg [31:0] cor_n, unc_n;
    initial begin ecc_corrected = 0; ecc_uncorrectable = 0; end
    always @(posedge clk) begin
        p_rd <= prog_re; c_rd <= crom_re; w_rd <= wrom_re;
        cor_n = 0; unc_n = 0;
        if (p_rd) for (n = 0; n < PT; n = n + 1) begin cor_n = cor_n + p_cor[n]; unc_n = unc_n + p_unc[n]; end
        if (c_rd) begin cor_n = cor_n + c_cor; unc_n = unc_n + c_unc; end
        if (w_rd) for (n = 0; n < WT; n = n + 1) begin cor_n = cor_n + w_cor[n]; unc_n = unc_n + w_unc[n]; end
        ecc_corrected <= ecc_corrected + cor_n;
        ecc_uncorrectable <= ecc_uncorrectable + unc_n;
    end
endmodule
