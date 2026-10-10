`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// redesign-qwen 2026-10-09: the SU-LOCAL CONSTANT BUFFER (owner: local controllers / buffers at each consumer).
//
// r22k puts the constant ROM (ot_qfd_crom, 48 macros) 1,002.5 um from the stream unit: 3 + 3 relay stages on crom_a /
// crom_q, so the SU lanes run at ML 10 instead of the VM's 7 (+48 cycles a layer measured).  This block sits BESIDE the
// SU and answers the SU's constant port exactly as ot_qfd_crom does (same port, same banking contract, same 5-edge
// answer: CRX = 4, so the lanes run at ML = max(4 + IS + OS, VL 7) = 7), from local per-lane banks that a prefetcher
// fills from the far ROM ahead of use:
//   narrow banks A / B   the layer-local constants of stages of even / odd parity (QK 20 + OSC 64 + DSC 64 = 148 rows)
//   narrow bank F        the HEAD stage's final norm (64 rows)
//   rope entries 0 / 1   the cos / sin row of a token position (wide, 64 b a lane), tagged with the row
//   QSCALE / ZERO        hardwired, as the ROM
// Prefetch policy: at a token start (tok_start, position tpos) stage 0 + rope(tpos) are filled if absent; while the SU is
// in stage s the next stage (s + 1, HEAD after 35, stage 0 + rope(tpos + 1) during HEAD) is filled into the bank it does
// not use.  The far ROM may answer FL edges after its strobe (relays included); the prefetcher never stalls the SU: it
// reports per-stage readiness (st_rdy: the bank of `stage` holds `stage`, filled), which the SU-side controller waits for
// at a stage start (a local dependency, normally long true: a stage lasts ~5,500 cycles, a fill 148 + FL).
// A read the buffer cannot serve (stage not resident, rope row not resident) raises a sticky fault (code 1) and leaves
// the output station unchanged -- never a silent wrong value without a fault; the far ROM's own faults are forwarded (code 2).
// Storage: 64 lanes x (2 x 148 + 64) x 32 b + 2 x 64 x 64 b = 745 Kb (SRAM-able: per 8-lane group, 360 x 256 b).
// MUT (negative controls, must FAIL): 1 = the narrow row of OSC off by one; 2 = a stage fill written into the other
// parity's bank (the bank the SU may still be reading).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_crom_lbuf #(
    parameter integer SW = 64,
    parameter integer AW = 24,
    parameter integer LW = 6,
    parameter integer QK0 = 4096,
    parameter integer POST0 = 5376,
    parameter integer QSCALE = 9472,
    parameter integer ROPE0 = 9473,
    parameter integer OSC0 = 533761,
    parameter integer DSC0 = 537857,
    parameter integer END = 541953,
    parameter integer HEAD = 36,
    parameter integer HEAD_N = 4096,
    parameter integer QKR = 20,
    parameter integer NWIN = 148,              // narrow rows a stage
    parameter integer NHD = 64,                // narrow rows of the HEAD stage
    parameter integer NW = 18,
    parameter integer FLP = 5,                 // far ROM: strobe -> answer edges at this block (ot_qfd_crom 5 + 2 x relays)
    parameter [63:0] QSCALE_WORD = 64'h3db504f3_00000000,
    parameter integer MUT = 0,
    // SRAM = 1: the narrow banks are one ot_sram_1r1w_1024x256 per 8-lane group (rows: bank 0 at 0, bank 1 at 256, HEAD at
    // 512; the banking contract makes every lane of a group read one row, as the ROM's narrow macro columns), rope rows
    // in flops.  Same answers, same edges (the macro's read register is the e3 stage).  0 = behavioural flop arrays.
    parameter integer SRAM = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    // the SU's constant port (ot_qfd_crom's)
    input  wire [SW-1:0]     crom_re,
    input  wire [SW*AW-1:0]  crom_addr,
    input  wire [LW-1:0]     crom_stage,
    output wire [SW*64-1:0]  crom_q,
    // stage / token context (from the SU-side controller)
    input  wire [LW-1:0]     stage,           // the stage the SU is in (or about to start)
    input  wire              tok_start,       // a token starts at position tpos
    input  wire [NW-1:0]     tpos,
    input  wire [AW-1:0]     lane_base,       // global index of lane 0 (a lane-group tile's strap; 0 for the full block)
    output wire              st_rdy,          // the bank of `stage` is resident (and rope(tpos) for stage 0 starts)
    // the far constant ROM (ot_qfd_crom), FL edges strobe -> answer
    output reg  [SW-1:0]     f_re,
    output reg  [SW*AW-1:0]  f_addr,
    output reg  [LW-1:0]     f_stage,
    input  wire [SW*64-1:0]  f_q,
    input  wire              f_fault,
    output reg               fault,
    output reg  [1:0]        fault_code
);
    localparam integer RB = 8;                 // local row bits (>= 148)
    localparam [2:0] K_ZERO = 3'd0, K_QSC = 3'd1, K_WIDE = 3'd2, K_NARROW = 3'd3, K_BAD = 3'd4;
    localparam [LW-1:0] S_HEAD = HEAD;
    localparam [AW-1:0] A_QK0 = QK0, A_POST0 = POST0, A_QSC = QSCALE, A_ROPE0 = ROPE0, A_OSC0 = OSC0, A_DSC0 = DSC0,
                        A_END = END, A_HN = HEAD_N;

    // ---- residency ----------------------------------------------------------------------------------------------
    reg [LW-1:0]   tag_n [0:1];                // stage held by narrow bank 0 / 1
    reg [1:0]      val_n;
    reg            val_f;                      // bank F holds HEAD
    reg [NW-1:0]   tag_r [0:1];                // rope rows held
    reg [1:0]      val_r;
    function automatic [0:0] par(input [LW-1:0] s);
        par = s[0];
    endfunction
    wire res_stage = (stage == S_HEAD) ? val_f : (val_n[par(stage)] && tag_n[par(stage)] == stage);
    wire res_rope  = (val_r[0] && tag_r[0] == tpos) || (val_r[1] && tag_r[1] == tpos);
    assign st_rdy = res_stage && (stage != 0 || res_rope);

    // ---- prefetcher: one fill at a time (a stage's narrow rows, the HEAD rows, or one rope row) -------------------
    localparam [1:0] F_NONE = 2'd0, F_STAGE = 2'd1, F_HEADB = 2'd2, F_ROPE = 2'd3;
    reg  [1:0]     f_kind;
    reg  [LW-1:0]  f_st;                       // stage being filled
    reg  [NW-1:0]  f_pos;                      // rope row being filled
    reg            f_slot;                     // rope slot being filled
    reg  [RB-1:0]  f_r;                        // next row to request
    reg  [RB-1:0]  f_n;                        // rows to request
    reg  [RB:0]    f_out;                      // requests in flight
    reg            busy;
    reg            pend_rope;                  // a stage-0 fill wants rope(rp_pos) after it
    reg  [NW-1:0]  rp_pos;
    wire [LW-1:0]  nxt = (stage == S_HEAD) ? {LW{1'b0}} : (stage == HEAD - 1) ? S_HEAD : stage + 1'b1;
    wire nxt_res = (nxt == S_HEAD) ? val_f : (val_n[par(nxt)] && tag_n[par(nxt)] == nxt);
    wire nxt_rope_res = (val_r[0] && tag_r[0] == tpos + 1'b1) || (val_r[1] && tag_r[1] == tpos + 1'b1);
    reg  tok_pend;
    // the request row's layer-local address (lane l adds l)
    function automatic [AW-1:0] row_addr(input [1:0] k, input [RB-1:0] r, input [NW-1:0] p);
        if (k == F_HEADB) row_addr = {r, 6'd0};
        else if (k == F_ROPE) row_addr = A_ROPE0 + {p, 6'd0};
        else if (r < QKR) row_addr = A_QK0 + {r, 6'd0};
        else if (r < QKR + 64) row_addr = A_OSC0 + {r - QKR[RB-1:0], 6'd0};
        else row_addr = A_DSC0 + {r - QKR[RB-1:0] - 8'd64, 6'd0};
    endfunction
    // answer side of the far ROM: the request's {kind, bank / slot, row} rides a tag line with the strobe
    wire issue = busy && (f_r < f_n);
    wire rv_done;
    wire [1:0] rt_kind; wire rt_sel; wire [RB-1:0] rt_row;
    ot_hdc_delay #(.W(1), .D(FLP + 1), .RESET(1)) u_rv (.clk(clk), .rst_n(rst_n), .d(issue), .q(rv_done));
    ot_hdc_delay #(.W(3 + RB), .D(FLP + 1)) u_rt (.clk(clk), .rst_n(rst_n),
        .d({f_kind, (f_kind == F_ROPE) ? f_slot : (par(f_st) ^ ((MUT == 2) ? 1'b1 : 1'b0)), f_r}), .q({rt_kind, rt_sel, rt_row}));
    integer la, lw, ld, lr, lo;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; f_kind <= F_NONE; f_re <= 0; val_n <= 2'b00; val_f <= 1'b0; val_r <= 2'b00; f_out <= 0;
            pend_rope <= 1'b0; tok_pend <= 1'b0;
        end else begin
            f_re <= {SW{issue}};
            if (tok_start) tok_pend <= 1'b1;
            if (issue) f_r <= f_r + 1'b1;
            f_out <= f_out + (issue ? 1'b1 : 1'b0) - (rv_done ? 1'b1 : 1'b0);
            // a fill completes when every row was requested and answered
            if (busy && f_r == f_n && f_out == 0 && !issue) begin
                busy <= 1'b0;
                case (f_kind)
                    F_STAGE: val_n[par(f_st)] <= 1'b1;
                    F_HEADB: val_f <= 1'b1;
                    F_ROPE:  val_r[f_slot] <= 1'b1;
                    default: ;
                endcase
            end else if (!busy) begin
                // choose the next fill: the token's own stage 0 / rope first, then the next stage, then the next rope
                if (tok_pend && !(val_n[par(0)] && tag_n[par(0)] == 0)) begin
                    busy <= 1'b1; f_kind <= F_STAGE; f_st <= 0; f_r <= 0; f_n <= NWIN;
                    val_n[par(0)] <= 1'b0; tag_n[par(0)] <= 0;
                end else if (tok_pend && !res_rope) begin
                    busy <= 1'b1; f_kind <= F_ROPE; f_pos <= tpos; f_r <= 0; f_n <= 1;
                    f_slot <= (val_r[0] && tag_r[0] != tpos) ? 1'b1 : 1'b0;      // keep the other row
                    val_r[(val_r[0] && tag_r[0] != tpos) ? 1 : 0] <= 1'b0;
                    tag_r[(val_r[0] && tag_r[0] != tpos) ? 1 : 0] <= tpos;
                end else if (!nxt_res) begin
                    tok_pend <= 1'b0;
                    busy <= 1'b1; f_st <= nxt; f_r <= 0;
                    if (nxt == S_HEAD) begin f_kind <= F_HEADB; f_n <= NHD; val_f <= 1'b0; end
                    else begin f_kind <= F_STAGE; f_n <= NWIN; val_n[par(nxt)] <= 1'b0; tag_n[par(nxt)] <= nxt; end
                end else if (stage == S_HEAD && !nxt_rope_res) begin
                    tok_pend <= 1'b0;
                    busy <= 1'b1; f_kind <= F_ROPE; f_pos <= tpos + 1'b1; f_r <= 0; f_n <= 1;
                    // replace the rope row that is not the current token's
                    f_slot <= (val_r[0] && tag_r[0] == tpos) ? 1'b1 : 1'b0;
                    val_r[(val_r[0] && tag_r[0] == tpos) ? 1 : 0] <= 1'b0;
                    tag_r[(val_r[0] && tag_r[0] == tpos) ? 1 : 0] <= tpos + 1'b1;
                end else tok_pend <= 1'b0;
            end
        end
    end
    always @(posedge clk) if (issue) begin
        f_stage <= (f_kind == F_HEADB) ? S_HEAD : (f_kind == F_ROPE) ? {LW{1'b0}} : f_st;
        for (la = 0; la < SW; la = la + 1) f_addr[la*AW +: AW] <= row_addr(f_kind, f_r, f_pos) + lane_base + la;
    end
    // ---- local banks -----------------------------------------------------------------------------------------------
    reg [31:0] bn0 [0:SW*NWIN-1];
    reg [31:0] bn1 [0:SW*NWIN-1];
    reg [31:0] bf  [0:SW*NHD-1];
    reg [63:0] br0 [0:SW-1];
    reg [63:0] br1 [0:SW-1];
    // ---- the SU's port: e1 IS, e2 decode, e3 bank read, e4 capture, e5 OS (ot_qfd_crom's timing) ---------------------
    wire [SW-1:0]    re1;
    wire [SW*AW-1:0] a1;
    wire [LW-1:0]    st1;
    ot_hdc_delay #(.W(SW), .D(1), .RESET(1)) u_is_re (.clk(clk), .rst_n(rst_n), .d(crom_re), .q(re1));
    ot_hdc_delay #(.W(SW*AW + LW), .D(1)) u_is_a (.clk(clk), .rst_n(rst_n), .d({crom_addr, crom_stage}), .q({a1, st1}));
    reg [SW-1:0]    t_v, t_miss;
    reg [SW*3-1:0]  t_kind;
    reg [SW*RB-1:0] t_row;
    reg [SW*2-1:0]  t_bank;                    // 0 / 1 narrow, 2 F, 3 rope (t_row[0] = rope slot)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin t_v <= 0; t_miss <= 0; end
        else begin
            for (ld = 0; ld < SW; ld = ld + 1) begin : g_dec
                reg [AW-1:0] a, off;
                reg [2:0] k;
                reg [RB-1:0] r;
                reg [1:0] bk;
                reg ms;
                a = a1[ld*AW +: AW];
                off = 0; r = 0; bk = 0; ms = 1'b0;
                if (st1 == S_HEAD) begin
                    if (a < A_HN) begin k = K_NARROW; r = a[6 +: RB]; bk = 2'd2; ms = !val_f; end
                    else k = K_BAD;
                end else if (st1 > S_HEAD) k = K_BAD;
                else if (a < A_QK0 || (a >= A_POST0 && a < A_QSC)) k = K_ZERO;
                else if (a < A_POST0) begin
                    k = K_NARROW; off = a - A_QK0; r = off[6 +: RB]; bk = {1'b0, par(st1)};
                    ms = !(val_n[par(st1)] && tag_n[par(st1)] == st1);
                end else if (a == A_QSC) k = K_QSC;
                else if (a < A_OSC0) begin
                    k = K_WIDE; off = a - A_ROPE0; bk = 2'd3;
                    if (val_r[0] && tag_r[0] == off[6 +: NW]) r = 0;
                    else if (val_r[1] && tag_r[1] == off[6 +: NW]) r = 1;
                    else ms = 1'b1;
                end else if (a < A_DSC0) begin
                    k = K_NARROW; off = a - A_OSC0; r = QKR + off[6 +: RB] + ((MUT == 1) ? 1 : 0); bk = {1'b0, par(st1)};
                    ms = !(val_n[par(st1)] && tag_n[par(st1)] == st1);
                end else if (a < A_END) begin
                    k = K_NARROW; off = a - A_DSC0; r = QKR + 64 + off[6 +: RB]; bk = {1'b0, par(st1)};
                    ms = !(val_n[par(st1)] && tag_n[par(st1)] == st1);
                end else k = K_BAD;
                t_v[ld] <= re1[ld];
                t_kind[ld*3 +: 3] <= k;
                t_row[ld*RB +: RB] <= r;
                t_bank[ld*2 +: 2] <= bk;
                t_miss[ld] <= re1[ld] && (ms || k == K_BAD);
            end
        end
    end
    reg [SW-1:0]   m_v, c_v;
    reg [SW*3-1:0] m_kind, c_kind;
    reg [SW*64-1:0] m_w, c_w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin m_v <= 0; c_v <= 0; end
        else begin m_v <= t_v & ~t_miss; c_v <= m_v; end
    end
    reg grp_dis;                               // SRAM: lanes of one group disagree on the row (contract violation)
    generate if (SRAM == 0) begin : g_flop
        always @(posedge clk) begin
            m_kind <= t_kind; c_kind <= m_kind; c_w <= m_w;
            for (lr = 0; lr < SW; lr = lr + 1) begin : g_rd
                reg [RB-1:0] r;
                r = t_row[lr*RB +: RB];
                case (t_bank[lr*2 +: 2])
                    2'd0: m_w[lr*64 +: 64] <= {32'd0, bn0[lr*NWIN + r]};
                    2'd1: m_w[lr*64 +: 64] <= {32'd0, bn1[lr*NWIN + r]};
                    2'd2: m_w[lr*64 +: 64] <= {32'd0, bf[lr*NHD + r]};
                    default: m_w[lr*64 +: 64] <= r[0] ? br1[lr] : br0[lr];
                endcase
            end
        end
        always @(posedge clk) grp_dis <= 1'b0;
    end else begin : g_sram
        localparam integer NG = SW / 8;
        wire [NG*256-1:0] rd;
        wire [NG-1:0] gdis;
        reg  [SW-1:0] m_nar;                   // lane's answer comes from its group macro
        genvar gg;
        for (gg = 0; gg < NG; gg = gg + 1) begin : g_grp
            reg ce; reg [9:0] ra; reg dis;
            integer j;
            always @(*) begin
                ce = 1'b0; ra = 10'd0; dis = 1'b0;
                for (j = 7; j >= 0; j = j - 1)
                    if (t_v[gg*8 + j] && !t_miss[gg*8 + j] && t_bank[(gg*8 + j)*2 +: 2] != 2'd3 && t_kind[(gg*8 + j)*3 +: 3] == K_NARROW) begin
                        ce = 1'b1;
                        ra = {t_bank[(gg*8 + j)*2 +: 2], t_row[(gg*8 + j)*RB +: RB]};
                    end
                for (j = 0; j < 8; j = j + 1)
                    if (t_v[gg*8 + j] && !t_miss[gg*8 + j] && t_kind[(gg*8 + j)*3 +: 3] == K_NARROW &&
                        {t_bank[(gg*8 + j)*2 +: 2], t_row[(gg*8 + j)*RB +: RB]} != ra) dis = 1'b1;
            end
            assign gdis[gg] = dis;
            reg [255:0] wd; reg [9:0] wa; reg wce;
            integer k;
            always @(*) begin
                wce = rv_done && (rt_kind == F_STAGE || rt_kind == F_HEADB);
                wa = (rt_kind == F_HEADB) ? {2'b10, rt_row} : {1'b0, rt_sel, rt_row};
                for (k = 0; k < 8; k = k + 1) wd[k*32 +: 32] = f_q[(gg*8 + k)*64 +: 32];
            end
            ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(ce), .r_addr_in(ra), .rd_out(rd[gg*256 +: 256]),
                .w_ce_in(wce), .w_addr_in(wa), .wd_in(wd), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
        always @(posedge clk) begin
            m_kind <= t_kind; c_kind <= m_kind;
            grp_dis <= |gdis;
            for (lr = 0; lr < SW; lr = lr + 1) begin : g_rr
                m_nar[lr] <= (t_bank[lr*2 +: 2] != 2'd3);
                m_w[lr*64 +: 64] <= t_row[lr*RB] ? br1[lr] : br0[lr];      // rope lanes (row bit 0 = slot)
            end
            for (lr = 0; lr < SW; lr = lr + 1) begin : g_cw
                c_w[lr*64 +: 64] <= m_nar[lr] ? {32'd0, rd[(lr / 8)*256 + (lr % 8)*32 +: 32]} : m_w[lr*64 +: 64];
            end
        end
    end endgenerate
    reg [SW*64-1:0] q_r;
    always @(posedge clk) begin
        for (lo = 0; lo < SW; lo = lo + 1) begin : g_out
            reg [63:0] w;
            case (c_kind[lo*3 +: 3])
                K_WIDE, K_NARROW: w = c_w[lo*64 +: 64];
                K_QSC:            w = QSCALE_WORD;
                default:          w = 64'd0;
            endcase
            if (c_v[lo]) q_r[lo*64 +: 64] <= w;
        end
    end
    assign crom_q = q_r;
    // ---- fill writes: the far answer FLP edges after the strobe ------------------------------------------------------
    always @(posedge clk) if (rv_done) begin
        for (lw = 0; lw < SW; lw = lw + 1) begin : g_fw
            case (rt_kind)
                F_STAGE: if (SRAM != 0) ; else if (rt_sel) bn1[lw*NWIN + rt_row] <= f_q[lw*64 +: 32]; else bn0[lw*NWIN + rt_row] <= f_q[lw*64 +: 32];
                F_HEADB: if (SRAM == 0) bf[lw*NHD + rt_row] <= f_q[lw*64 +: 32];
                F_ROPE:  if (rt_sel) br1[lw] <= f_q[lw*64 +: 64]; else br0[lw] <= f_q[lw*64 +: 64];
                default: ;
            endcase
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; fault_code <= 2'd0; end
        else if (!fault && ((|t_miss) || f_fault || grp_dis)) begin fault <= 1'b1; fault_code <= (|t_miss) ? 2'd1 : f_fault ? 2'd2 : 2'd3; end
    end
endmodule

// Die master qfd_su_cbuf: ot_qfd_crom_lbuf SRAM 1, far latency 11 (crom 5 + 3 + 3 relays), no top parameters (yosys 0.68
// asserts on a re-processed parameterised top).
module ot_qfd_su_cbuf (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [63:0]       crom_re,
    input  wire [64*24-1:0]  crom_addr,
    input  wire [5:0]        crom_stage,
    output wire [64*64-1:0]  crom_q,
    input  wire [5:0]        stage,
    input  wire              tok_start,
    input  wire [17:0]       tpos,
    output wire              st_rdy,
    output wire [63:0]       f_re,
    output wire [64*24-1:0]  f_addr,
    output wire [5:0]        f_stage,
    input  wire [64*64-1:0]  f_q,
    input  wire              f_fault,
    output wire              fault,
    output wire [1:0]        fault_code
);
    ot_qfd_crom_lbuf #(.SRAM(1), .FLP(11)) u_b (.clk(clk), .rst_n(rst_n), .crom_re(crom_re), .crom_addr(crom_addr),
        .crom_stage(crom_stage), .crom_q(crom_q), .stage(stage), .tok_start(tok_start), .tpos(tpos), .st_rdy(st_rdy),
        .f_re(f_re), .f_addr(f_addr), .f_stage(f_stage), .f_q(f_q), .f_fault(f_fault), .fault(fault), .fault_code(fault_code),
        .lane_base(24'd0));
endmodule


// Die master qfd_su_cbuf_g (owner rule: one hardened element, replicated): ONE 8-lane group of the constant buffer -- its
// SRAM, its lanes' answer pipeline and its own copy of the (deterministic) prefetcher, strapped with its lane base.
// 8 instances side by side form the SU's constant buffer; every copy sees the same stage / token inputs, so the copies
// fill in lockstep (st_rdy of any copy stands for all).  No top parameters.
module ot_qfd_su_cbuf_g (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        crom_re,
    input  wire [8*24-1:0]   crom_addr,
    input  wire [5:0]        crom_stage,
    output wire [8*64-1:0]   crom_q,
    input  wire [5:0]        stage,
    input  wire              tok_start,
    input  wire [17:0]       tpos,
    input  wire [2:0]        grp,              // strap: lanes 8 grp .. 8 grp + 7
    output wire              st_rdy,
    output wire [7:0]        f_re,
    output wire [8*24-1:0]   f_addr,
    output wire [5:0]        f_stage,
    input  wire [8*64-1:0]   f_q,
    input  wire              f_fault,
    output wire              fault,
    output wire [1:0]        fault_code
);
    ot_qfd_crom_lbuf #(.SW(8), .SRAM(1), .FLP(11)) u_b (.clk(clk), .rst_n(rst_n), .crom_re(crom_re), .crom_addr(crom_addr),
        .crom_stage(crom_stage), .crom_q(crom_q), .stage(stage), .tok_start(tok_start), .tpos(tpos),
        .lane_base({18'd0, grp, 3'd0}), .st_rdy(st_rdy), .f_re(f_re), .f_addr(f_addr), .f_stage(f_stage), .f_q(f_q),
        .f_fault(f_fault), .fault(fault), .fault_code(fault_code));
endmodule
