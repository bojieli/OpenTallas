`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Physical characterisation top for the V4.1 attention ENGINE CONTROLLER
// (rtl/hdc/v41x/ot_hdc_v41x_attn.sv, unchanged): the engine is instantiated at
// H16 / TD32 / NL4 / TROWS640 / PWORDS2 / ILV1 with D = 64.  D = 64 keeps the
// full-shape schedule (DPT = D/NT = 8, 16 words per 32-row block, R = 2,
// FILLC = 8, GUARD_P 18, GUARD_Q 20, NBANK 5, the same counters and the same
// bank allocator), with NT = 8 tiles instead of 64, so the stationary-operand
// and issue broadcasts fan out to 8 tile boundaries, not 64 (the 64-tile
// broadcast tree is a separate item).
//
// Stubbed here (this file only; used by no simulation):
//   ot_hdc_v41x_attn_tile     registered sink of every input (the real tile's
//                             R0 boundary), outputs a registered fold
//   ot_hdc_v41x_attn_staging  registered address/data sink with a registered
//                             read port (the SRAM macro boundary)
//   ot_hdc_qadd               one register stage (merge and lane-tree adders)
//   ot_hdc_v41x_dly / _vdly   copies of the real delay lines
// The transposers, merge rings, lane-tree structure and the whole controller
// are the engine's own RTL.
//
// Wide data buses (q_w, kv_w, p_w) come from internal registers loaded 64 bits
// per cycle from pins; wide results (sc_y, pv_y) leave through registered XOR
// folds.  Every handshake (valid/ready/credit) is a real top-level port, so
// the engine's combinational p_v -> q_ready path is an in-to-out path here.
// ---------------------------------------------------------------------------
// BREG = 1: every control input and ready/issue output passes a boundary register here, so each
// engine port path is flop-to-flop (the die-internal neighbours are registered); the reported
// fmax is then register-to-register.  REPL = 1 selects the engine's per-tile index copies.
module ot_v41_attn_eng_ctl_phys #(
    parameter integer BREG = 0,
    parameter integer REPL = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        job_v,
    input  wire [15:0] job_t,
    output wire        job_ready,
    input  wire        q_v,
    output wire        q_ready,
    input  wire        kv_v,
    input  wire [3:0]  kv_m,
    output wire        kv_ready,
    input  wire        p_v,
    output wire        p_ready,
    input  wire        sc_cr,
    input  wire        pv_cr,
    input  wire        ld_en,           // shift the data registers
    input  wire [1:0]  ld_sel,          // 0 q, 1 kv, 2 p
    input  wire [63:0] ld_d,
    output reg         sc_v_o,
    output reg  [15:0] sc_row_o,
    output reg  [31:0] sc_fold,
    output reg         pv_v_o,
    output reg  [7:0]  pv_c_o,
    output reg  [31:0] pv_fold,
    output wire        qk_iss,
    output wire        pv_iss
);
    localparam integer H = 16, D = 64, TD = 32, NL = 4, TROWS = 640, PWORDS = 2;
    localparam integer QW = D * 16, KW = NL * (D / 32) * 265, PW = PWORDS * TD * 16;
    localparam integer NT = NL * (D / TD);
    reg [QW-1:0] q_w;
    reg [KW-1:0] kv_w;
    reg [PW-1:0] p_w;
    always @(posedge clk) if (ld_en) begin
        if (ld_sel == 2'd0) q_w <= {q_w[QW-65:0], ld_d};
        if (ld_sel == 2'd1) kv_w <= {kv_w[KW-65:0], ld_d};
        if (ld_sel == 2'd2) p_w <= {p_w[PW-65:0], ld_d};
    end
    wire e_job_v, e_q_v, e_kv_v, e_p_v, e_sc_cr, e_pv_cr, e_job_ready, e_q_ready, e_kv_ready, e_p_ready, e_qk_iss, e_pv_iss;
    wire [15:0] e_job_t; wire [3:0] e_kv_m;
    generate if (BREG != 0) begin : g_breg
        reg ri_job_v, ri_q_v, ri_kv_v, ri_p_v, ri_sc_cr, ri_pv_cr, ro_job_ready, ro_q_ready, ro_kv_ready, ro_p_ready, ro_qk, ro_pv;
        reg [15:0] ri_job_t; reg [3:0] ri_kv_m;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                ri_job_v <= 1'b0; ri_q_v <= 1'b0; ri_kv_v <= 1'b0; ri_p_v <= 1'b0; ri_sc_cr <= 1'b0; ri_pv_cr <= 1'b0;
                ro_job_ready <= 1'b0; ro_q_ready <= 1'b0; ro_kv_ready <= 1'b0; ro_p_ready <= 1'b0; ro_qk <= 1'b0; ro_pv <= 1'b0;
            end else begin
                ri_job_v <= job_v; ri_q_v <= q_v; ri_kv_v <= kv_v; ri_p_v <= p_v; ri_sc_cr <= sc_cr; ri_pv_cr <= pv_cr;
                ro_job_ready <= e_job_ready; ro_q_ready <= e_q_ready; ro_kv_ready <= e_kv_ready; ro_p_ready <= e_p_ready;
                ro_qk <= e_qk_iss; ro_pv <= e_pv_iss;
            end
        end
        always @(posedge clk) begin ri_job_t <= job_t; ri_kv_m <= kv_m; end
        assign e_job_v = ri_job_v; assign e_q_v = ri_q_v; assign e_kv_v = ri_kv_v; assign e_p_v = ri_p_v;
        assign e_sc_cr = ri_sc_cr; assign e_pv_cr = ri_pv_cr; assign e_job_t = ri_job_t; assign e_kv_m = ri_kv_m;
        assign job_ready = ro_job_ready; assign q_ready = ro_q_ready; assign kv_ready = ro_kv_ready;
        assign p_ready = ro_p_ready; assign qk_iss = ro_qk; assign pv_iss = ro_pv;
    end else begin : g_nobreg
        assign e_job_v = job_v; assign e_q_v = q_v; assign e_kv_v = kv_v; assign e_p_v = p_v;
        assign e_sc_cr = sc_cr; assign e_pv_cr = pv_cr; assign e_job_t = job_t; assign e_kv_m = kv_m;
        assign job_ready = e_job_ready; assign q_ready = e_q_ready; assign kv_ready = e_kv_ready;
        assign p_ready = e_p_ready; assign qk_iss = e_qk_iss; assign pv_iss = e_pv_iss;
    end endgenerate
    wire sc_v; wire [15:0] sc_row; wire [NL-1:0] sc_m; wire [NL*H*32-1:0] sc_y; wire [NL*H-1:0] sc_f;
    wire pv_v; wire [7:0] pv_c; wire [NT*H*32-1:0] pv_y; wire [NT*H-1:0] pv_f;
    ot_hdc_v41x_attn #(.H(H), .D(D), .TD(TD), .NL(NL), .TROWS(TROWS), .PWORDS(PWORDS), .ILV(1), .REPL(REPL)) u_eng (
        .clk(clk), .rst_n(rst_n), .job_v(e_job_v), .job_t(e_job_t), .job_ready(e_job_ready),
        .q_v(e_q_v), .q_w(q_w), .q_ready(e_q_ready), .kv_v(e_kv_v), .kv_m(e_kv_m), .kv_w(kv_w), .kv_ready(e_kv_ready),
        .sc_v(sc_v), .sc_row(sc_row), .sc_m(sc_m), .sc_y(sc_y), .sc_f(sc_f), .sc_cr(e_sc_cr),
        .p_v(e_p_v), .p_w(p_w), .p_ready(e_p_ready), .pv_v(pv_v), .pv_c(pv_c), .pv_y(pv_y), .pv_f(pv_f),
        .pv_cr(e_pv_cr), .qk_iss(e_qk_iss), .pv_iss(e_pv_iss));
    function automatic [31:0] fold(input [NT*H*32-1:0] x, input integer n);
        integer i;
        begin
            fold = 32'd0;
            for (i = 0; i < n; i = i + 1) fold = fold ^ x[i*32 +: 32];
        end
    endfunction
    always @(posedge clk) begin
        sc_v_o <= sc_v; sc_row_o <= sc_row; sc_fold <= fold({{(NT-NL)*H*32{1'b0}}, sc_y}, NL * H) ^ {sc_m, sc_f[27:0]};
        pv_v_o <= pv_v; pv_c_o <= pv_c; pv_fold <= fold(pv_y, NT * H) ^ pv_f[31:0];
    end
endmodule

// ---- stubs (characterisation only) ----
module ot_hdc_v41x_attn_tile #(
    parameter integer H = 16, parameter integer TD = 64, parameter integer NBANK = 3,
    parameter integer BW = 2, parameter integer PWORDS = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [PWORDS*TD*16-1:0] ld_w,
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    output reg               ov,
    output reg  [H*32-1:0]   oy,
    output reg  [H-1:0]      oflt
);
    reg r_ld_v, r_ld_mode, r_ld_w2v, r_iv;
    reg [BW-1:0] r_ld_bank, r_ibank;
    reg [7:0] r_ld_grp;
    reg [PWORDS*TD*16-1:0] r_ld_w;
    reg [TD*18-1:0] r_ib;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r_ld_v <= 1'b0; r_iv <= 1'b0; ov <= 1'b0; end
        else begin r_ld_v <= ld_v; r_iv <= iv; ov <= r_iv; end
    end
    always @(posedge clk) begin
        r_ld_mode <= ld_mode; r_ld_bank <= ld_bank; r_ld_grp <= ld_grp; r_ld_w <= ld_w; r_ld_w2v <= ld_w2v;
        r_ibank <= ibank; r_ib <= ib;
    end
    integer i;
    reg [H*32-1:0] f;
    always @* begin
        f = {H*32{1'b0}};
        for (i = 0; i < PWORDS*TD*16; i = i + 1) f[i % (H*32)] = f[i % (H*32)] ^ r_ld_w[i];
        for (i = 0; i < TD*18; i = i + 1) f[(i * 7) % (H*32)] = f[(i * 7) % (H*32)] ^ r_ib[i];
    end
    always @(posedge clk) begin
        oy <= f ^ {{(H*32-12){1'b0}}, r_ld_v, r_ld_mode, r_ld_w2v, r_ld_grp, r_ld_bank[0]};
        oflt <= {H{r_ibank[0]}};
    end
endmodule

module ot_hdc_v41x_attn_staging #(
    parameter integer D = 512, parameter integer NL = 4, parameter integer TROWS = 640, parameter bit SRAM_MACRO = 0
) (
    input  wire clk,
    input  wire [NL-1:0] wr_en,
    input  wire [$clog2((TROWS+NL-1)/NL)-1:0] wr_addr,
    input  wire [NL*(D/32)*265-1:0] wr_data,
    input  wire [$clog2((TROWS+NL-1)/NL)-1:0] rd_addr,
    output reg  [NL*(D/32)*265-1:0] rd_data
);
    localparam integer AW = $clog2((TROWS+NL-1)/NL);
    reg [NL-1:0] r_we;
    reg [AW-1:0] r_wa, r_ra;
    reg [NL*(D/32)*265-1:0] r_wd;
    always @(posedge clk) begin
        r_we <= wr_en; r_wa <= wr_addr; r_ra <= rd_addr; r_wd <= wr_data;
        rd_data <= r_wd ^ {(NL*(D/32)*265/AW + 1){r_ra ^ r_wa}} ^ {(NL*(D/32)*265/NL + 1){r_we}};
    end
endmodule

module ot_hdc_qadd (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg         fault
);
    always @(posedge clk) begin y <= a ^ b; fault <= v & a[31] & b[31]; end
endmodule

module ot_hdc_v41x_dly #(parameter integer W = 1, parameter integer D = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else begin : g_reg
            reg [W-1:0] r [0:D-1];
            integer i;
            always @(posedge clk) begin
                r[0] <= d;
                for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
            end
            assign q = r[D-1];
        end
    endgenerate
endmodule

module ot_hdc_v41x_vdly #(parameter integer D = 1) (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output wire q
);
    reg [D:0] r;
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r[D:1] <= {D{1'b0}};
        else for (i = 1; i <= D; i = i + 1) r[i] <= (i == 1) ? d : r[i-1];
    end
    assign q = r[D];
endmodule
