`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41x_idx_kdata_m -- the index-key stream's datapath (ROB + scale
// buffer + output queue) with the ROB in SRAM MACROS: the W11 hardened form of
// ot_hdc_v41x_idx_kdata (same ports and drain protocol; that module is left
// untouched).
//
// ROB: per pseudo-channel p one bank of WB = 128 blocks x 1,024 bits, stored as
// four ot_sram_1r1w_128x256_m1_r2c2 (one per 256-bit beat): a response beat is
// one macro write.  Every bank is read at the drain's slot (one read port each:
// a scale drain reads all 32 banks, a quarter drain 8 of them, never both in a
// cycle).  MACRO = 0 models the same macro timing behaviourally (1-cycle
// synchronous read) for fast simulation.
//
// Latency: the drain command visible in cycle t (stage 0) is read by the macros
// at edge t+1 (stage 1), the macro outputs are registered at edge t+2 (stage 2)
// and, XP = 2, the fold crossbar's output at edge t+3; the stage-L quarter
// (L = 1 + XP) is written into the output queue at the end of its cycle: L + 1
// edges from decision to queue (the legacy kdata: 1).  The queue is L + 2 deep
// and dr_ready admits a decision only while every in-flight quarter and the new
// one fit: occupancy + (stage L) - pop + (stages 0..L-1) + 1 <= L + 2.  At one
// pop a cycle the stream sustains one quarter a cycle.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_kdata_m #(
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer TAGW = 16,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer MACRO = 1,     // 1: ot_sram_1r1w_128x256_m1_r2c2 instances; 0: behavioural, same timing
    parameter integer XP   = 1       // 1: register the macro outputs; 2: also register the crossbar output
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [NPC-1:0]        rsp_v,
    input  wire [NPC-1:0]        rsp_rdy,
    input  wire [NPC*TAGW-1:0]   rsp_tag,
    input  wire [NPC*BEATW-1:0]  rsp_beat,
    input  wire [NPC*DW-1:0]     rsp_data,
    input  wire                  dr_scale,
    input  wire                  dr_quarter,
    input  wire [$clog2(WB)-1:0] dr_slot,
    input  wire [1:0]            dr_q,
    input  wire [4:0]            dr_fold,
    input  wire [5:0]            dr_sidx,
    input  wire [4:0]            dr_nkeys,
    output wire                  dr_ready,
    output wire                  o_valid,
    input  wire                  o_ready,
    output wire [15:0]           o_kv,
    output wire [16*544-1:0]     o_key,
    output wire                  busy        // a drain is in flight or the queue holds a quarter
);
    localparam integer L  = 1 + XP;
    localparam integer QD = L + 2;
    localparam integer SW = $clog2(WB);
    initial if (WB != 128 || DW != 256 || NPC != 32 || XP < 1 || XP > 2)
        $fatal(1, "ot_hdc_v41x_idx_kdata_m: NPC 32, WB 128, DW 256, XP 1..2");

    // ---- ROB banks ----------------------------------------------------------------------
    wire [NPC*4*DW-1:0] rd;              // bank p, 1,024 bits: the four beats' macro outputs
    genvar p, b;
    generate for (p = 0; p < NPC; p = p + 1) begin : g_bank
        wire          wv = rsp_v[p] && rsp_rdy[p];
        wire [SW-1:0] wa = SW'(rsp_tag[p*TAGW +: TAGW] % WB);
        wire [1:0]    wb = rsp_beat[p*BEATW +: 2];
        for (b = 0; b < 4; b = b + 1) begin : g_beat
            if (MACRO != 0) begin : g_m
                ot_sram_1r1w_128x256_m1_r2c2 u_mem (
                    .clk(clk), .r_ce_in(1'b1), .r_addr_in(dr_slot), .rd_out(rd[(4*p+b)*DW +: DW]),
                    .w_ce_in(wv && wb == b), .w_addr_in(wa), .wd_in(rsp_data[p*DW +: DW]),
                    .w_mask_in({DW{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
            end else begin : g_b
                reg [DW-1:0] mem [0:WB-1];
                reg [DW-1:0] q;
                always @(posedge clk) begin
                    q <= mem[dr_slot];
                    if (wv && wb == b) mem[wa] <= rsp_data[p*DW +: DW];
                end
                assign rd[(4*p+b)*DW +: DW] = q;
            end
        end
    end endgenerate

    // ---- control pipeline: stage 0 = the drain command (cycle t), stage k = t + k ------
    reg [L:1]  s_scale, s_quarter;
    reg [1:0]  s_q    [1:L];
    reg [4:0]  s_fold [1:L];
    reg [5:0]  s_sidx [1:L];
    reg [4:0]  s_nk   [1:L];
    integer k;
    always @(posedge clk) begin
        if (!rst_n) begin s_scale <= 0; s_quarter <= 0; end
        else begin
            s_scale[1] <= dr_scale; s_quarter[1] <= dr_quarter;
            for (k = 2; k <= L; k = k + 1) begin s_scale[k] <= s_scale[k-1]; s_quarter[k] <= s_quarter[k-1]; end
        end
        s_q[1] <= dr_q; s_fold[1] <= dr_fold; s_sidx[1] <= dr_sidx; s_nk[1] <= dr_nkeys;
        for (k = 2; k <= L; k = k + 1) begin
            s_q[k] <= s_q[k-1]; s_fold[k] <= s_fold[k-1]; s_sidx[k] <= s_sidx[k-1]; s_nk[k] <= s_nk[k-1];
        end
    end
    // macro outputs registered (stage 2: the read data of the stage-1 command)
    reg [NPC*4*DW-1:0] rq;
    always @(posedge clk) rq <= rd;

    // ---- scale buffer and the fold crossbar (stage 2 data, stage-2 control) ------------
    reg [511:0] sbuf [0:63];
    integer w, i, c;
    always @(posedge clk)
        if (s_scale[2])
            for (w = 0; w < 64; w = w + 1)
                sbuf[w] <= rq[((w >> 1) ^ s_fold[2]) * 1024 + 512 * (w & 1) +: 512];
    reg [511:0] sw;
    reg [16*544-1:0] nk;
    reg [15:0] nkv;
    always @* begin
        sw = sbuf[s_sidx[2]];
        for (i = 0; i < 16; i = i + 1) begin
            c = {s_q[2], i[3:1]};
            nk[544*i +: 544] = {sw[32*i +: 32], rq[(c ^ s_fold[2]) * 1024 + 512 * (i & 1) +: 512]};
            nkv[i] = (i < s_nk[2]);
        end
    end
    // stage L: the quarter entering the queue
    wire             in_v;
    wire [16*544+15:0] in_d;
    generate if (XP == 1) begin : g_x1
        assign in_v = s_quarter[2]; assign in_d = {nkv, nk};
    end else begin : g_x2
        reg [16*544+15:0] xd;
        always @(posedge clk) xd <= {nkv, nk};
        assign in_v = s_quarter[3]; assign in_d = xd;
    end endgenerate

    // ---- output queue (QD entries, head at rp) ---------------------------------------------
    reg [16*544+15:0] qd [0:QD-1];
    reg [$clog2(QD+1)-1:0] occ;
    reg [$clog2(QD)-1:0] rp, wp;
    assign o_valid = occ != 0;
    assign {o_kv, o_key} = qd[rp];
    wire pop = o_valid && o_ready;
    integer nif;
    always @* begin
        nif = dr_quarter ? 1 : 0;
        for (k = 1; k < L; k = k + 1) nif = nif + (s_quarter[k] ? 1 : 0);
    end
    // in flight after this edge: the stage-0..L-1 quarters that have not reached the queue
    assign dr_ready = (32'(occ) + 32'(in_v) - 32'(pop) + 32'(nif) + 1) <= QD;
    assign busy = o_valid || (|s_quarter) || (|s_scale);
    always @(posedge clk) begin
        if (!rst_n) begin occ <= 0; rp <= 0; wp <= 0; end
        else begin
            if (in_v) begin qd[wp] <= in_d; wp <= (wp == QD - 1) ? 0 : wp + 1'b1; end
            if (pop) rp <= (rp == QD - 1) ? 0 : rp + 1'b1;
            occ <= occ + (in_v ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
        end
    end
endmodule
