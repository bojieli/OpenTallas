`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_cfg7_seq: per-pair configuration sequencer of the DS-ROM S81 die (CLAUDE S81-DIE, 2026-10-06).
//
// The S81 die gives every field pair NROM = 7 real cfg ROMs (ot_rom_4096x72_m8): 2^PHW = 1,024 phases x CW = 25 words
// = 25,600 words per pair (results/uarch/dsrom_c_w4_20261003/s82_inputs/inventory.json, words_per_pair_by_stage).
// The pinned single-macro loader (ot_v41_pair_pq_ld_cfgrom) stops at one 4,096-row macro ($fatal for PHW 10), so the
// die needs this sequencer: the loader of ot_v41_pair_pq_ld_frontend (PQ = 0, the pinned load-at-broadcast loader)
// with its linear word address split into a macro select (a[AW-1:12]) and a row (a[11:0]):
//   * one shared 12-bit row address to all NROM macros, one chip enable per macro (only the addressed macro reads);
//   * the 48-bit payload (rd_out[47:0]; rd_out[71:48] are spare macro columns) taken from the macro that was read on
//     the previous edge (bank select registered with the read), so the configuration word reaches c_d on exactly the
//     edge the combinational-read reference loader captures it (same-edge address lookahead, as ot_v41_pair_cfgrom_context).
// Ports: lc = {cfg_np[2:0], cfg_ph[PHW-1:0], cfg_go, go} from the slot station; cfg = {c_v, c_d[47:0], c_a[4:0]} in the
// q element's cfg pin order (cfg_a, cfg_d, cfg_v); go_e gates the element's go (W17 class-valid gate); st = {fault,
// ld_busy}.  fault is the reference loader's (constant 0 at PQ = 0: the q element exposes no shadow-free signals, so the
// die runs the pinned PQ = 0 loader).
// PQ = 1 (s81-die-2 2026-10-08, tie-off audit TA-10: the adopted PQ q element ot_v41_rom_elem_q_qxpq_w10 had go_tag /
// bank_free / sh_free floating on the die): the loader of ot_v41_pair_pq_ld_frontend PQ = 1 -- a broadcast that finds
// the element's configuration shadow full or the output-tag bank it would write still draining (ef = {bank_free,
// sh_free}) is held (pending) and loaded when both clear; a second broadcast before the load, or a go before the load
// finished, is a FAULT.  go_tag = the op tag of ot_v41_spine_pq_w17w10 (bt_tag = ist, which advances by one on every
// go broadcast, from 0 at reset): a 2-bit count of the broadcast gos this pair has seen (lc[0], before the class gate),
// so no tag wires leave the hub.  PQ = 0: go_tag = 0, ef ignored, cycle-identical to the pinned loader.
// Exact gate: rtl/v41die/test/tb_ot_s81_cfg7_seq.sv (cycle lockstep against ot_v41_pair_pq_ld_frontend PHW 10, PQ 0 and 1).
// ---------------------------------------------------------------------------
module ot_s81_cfg7_seq #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer PQ = 0,
    parameter integer CW = 3 * NSEG + 1,
    parameter integer AW = $clog2(CW << PHW)
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [47:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    input  wire [1:0]          ef,          // PQ: {bank_free, sh_free} of the element
    output wire [1:0]          go_tag       // PQ: the op tag that rides with go
);
    initial begin
        if (NROM != 7) $fatal(1, "ot_s81_cfg7_seq: the port list is written for NROM = 7");
        if ((CW << PHW) > NROM * 4096) $fatal(1, "ot_s81_cfg7_seq: CW x 2^PHW words exceed NROM 4096-row macros");
        if (CW > 32 || AW < 12) $fatal(1, "ot_s81_cfg7_seq: CW <= 32 and AW >= 12 required");
    end
    wire           go      = lc[0];
    wire           cfg_go  = lc[1];
    wire [PHW-1:0] cfg_ph  = lc[PHW+1:2];
    wire [2:0]     cfg_np  = lc[PHW+4:PHW+2];
    reg         ld_run;
    reg [4:0]   ld_k;
    reg [AW-1:0] ld_a;
    reg [2:0]   ld_np;
    reg         c_v;
    reg [4:0]   c_a;
    reg [47:0]  c_d;
    reg         fault;
    reg         pend;
    reg [PHW-1:0] pend_ph;
    reg [2:0]   pend_np;
    reg [1:0]   tag;
    wire        ld_ok = (PQ == 0) || (ef[0] && ef[1]);
    wire        ld_start = (cfg_go && ld_ok) || (PQ != 0 && pend && !cfg_go && ld_ok);
    // same-edge lookahead of the reference's combinational cm_a = ld_a: read ld_a's word one edge early
    wire [AW-1:0] ra = ld_start ? AW'(cfg_go ? cfg_ph : pend_ph) * AW'(CW) : ld_a + 1'b1;
    wire          rce = rst_n[0] && (ld_start || (ld_run && ld_k < 5'(CW - 1)));
    wire [AW-13:0] rbank = ra[AW-1:12];
    reg  [AW-13:0] bank_q;
    assign a = ra[11:0];
    assign ce0 = rce && rbank == 0;
    assign ce1 = rce && rbank == 1;
    assign ce2 = rce && rbank == 2;
    assign ce3 = rce && rbank == 3;
    assign ce4 = rce && rbank == 4;
    assign ce5 = rce && rbank == 5;
    assign ce6 = rce && rbank == 6;
    always @(posedge clk[0]) if (rce) bank_q <= rbank;
`ifdef OT_S81_CFG7_MUT_BANK
    wire [AW-13:0] sel = rbank;          // negative control: select by the current (not the read) address
`else
    wire [AW-13:0] sel = bank_q;
`endif
    reg [47:0] cm_q;
    always @(*) begin
        case (sel)
            0: cm_q = q0;
            1: cm_q = q1;
            2: cm_q = q2;
            3: cm_q = q3;
            4: cm_q = q4;
            5: cm_q = q5;
            default: cm_q = q6;
        endcase
    end
    always @(posedge clk[0] or negedge rst_n[0]) begin
        if (!rst_n[0]) begin
            ld_run <= 1'b0; ld_k <= 5'd0; c_v <= 1'b0; fault <= 1'b0; pend <= 1'b0; tag <= 2'd0;
        end else begin
            fault <= fault;
            pend <= pend;
            c_v <= ld_run;
            if (PQ != 0) begin
                if (cfg_go && !ld_ok) begin pend <= 1'b1; pend_ph <= cfg_ph; pend_np <= cfg_np; end
                else if (ld_start) pend <= 1'b0;
`ifndef OT_S81_CFG7_MUT_NOFAULT
                if (cfg_go && (pend || ld_run)) fault <= 1'b1;               // a second broadcast before the load
`endif
                if (go && (pend || ld_run || c_v || cfg_go)) fault <= 1'b1;  // go before the load finished
                if (go) tag <= tag + 2'd1;
            end
            if (ld_start) begin
                ld_run <= 1'b1; ld_k <= 5'd0;
`ifdef OT_S81_CFG7_MUT_STRIDE
                ld_a <= AW'(cfg_ph) * AW'(CW + 1);   // negative control: wrong phase stride
`else
                ld_a <= AW'(cfg_go ? cfg_ph : pend_ph) * AW'(CW);
`endif
                ld_np <= cfg_go ? cfg_np : pend_np;
            end else if (ld_run) begin
                ld_k <= ld_k + 5'd1;
                ld_a <= ld_a + 1'b1;
                if (ld_k == 5'(CW - 1)) ld_run <= 1'b0;
            end
        end
    end
    reg act;
    always @(posedge clk[0] or negedge rst_n[0]) begin
        if (!rst_n[0]) act <= 1'b0;
        else if (cfg_go || ld_start) act <= 1'b0;
        else if (c_v && c_a >= 5'(NSEG) && c_a < 5'(2 * NSEG) && c_d[0]) act <= 1'b1;
    end
    always @(posedge clk[0]) begin
        c_a <= ld_k;
        if (ld_run) c_d <= (ld_k == 5'(2 * NSEG)) ? (cm_q | {42'd0, ld_np, 3'd0}) : cm_q;
    end
    assign go_e = go && act;
    assign cfg = {c_v, c_d, c_a};
`ifdef OT_S81_CFG7_MUT_NOHOLD
    wire ld_busy = ld_run || c_v;              // negative control: pending load not reported busy
`else
    wire ld_busy = ld_run || c_v || pend;
`endif
    assign st = {fault, ld_busy};
`ifdef OT_S81_CFG7_MUT_TAG
    assign go_tag = (PQ != 0) ? tag + 2'd1 : 2'd0;   // negative control: tag one op ahead
`else
    assign go_tag = (PQ != 0) ? tag : 2'd0;
`endif
endmodule
