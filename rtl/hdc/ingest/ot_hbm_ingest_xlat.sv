`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_ingest_xlat (stream ingest 2026-10-08): the HBM accelerator die's KV-ingest address translator.  It turns the
// linear sector words of ot_rom_host_ingest (die face, ck) into the DS-V4.1 DECODE KV LAYOUT that the per-token
// write-back unit ot_hbm_accel_dskv_wb writes and the stream PCs read (W19 TP-96; tools/hbm_accel_dskv_wb.py is the
// independent golden of the map), as write requests on the same stack write-request port format (wq_*):
//   ingest address o_addr = {kind[1:0], slot[5:0], S[23:0]} (the runtime puts {kind, slot} in the descriptor base):
//   kind 0 WINDOW  (descriptor ROWS, pitch 17, RING 128, slot = layer 0..39): S = 17 w + t -> ring slot w on die-local
//                  PC w (stack w[6:5], PC w[4:0]), PC-local sector j = t (0..16).  w = (S * 3856) >> 16 = S / 17 exactly
//                  for S < 4096.
//   kind 1 COMPRESSED KV (ROWS, pitch 9, NDIE 1: the host sends the die's own groups in die-local row order k; slot =
//                  index-source slot 0..7): S = 9 k + t, PC = S[6:0], j = S >> 7.
//   kind 2 INDEX KEYS (RAW: the die's keys packed 68 B back to back in whole 8-key blocks of 17 sectors, the host pads
//                  the last block): S = die-local sector, PC = S[6:0], j = S >> 7.
//   kind 3 reserved: fault (sticky), the word is dropped.
//   PC-local sector j -> bank {j[9:7], j[1:0]}, column j[6:2], row ROW0(kind) + slot * SLOT_ROWS + (j >> 10): the
//   dskv_wb / stream-PC order, so the ingested image is read by the next token's streams exactly as a decoded one.
// Flow: IQ-entry input FIFO (the host block's die-face credits: o_cr one per entry popped, OCRED = IQ), two register
// stages (divide, then the address), output valid / ready from a 4-entry FIFO (head from flops).
// Writes only (the HBM die's host block is RMW_EN 0); a read word (o_we 0) is a fault.  The BOOT_END marker (o_addr all
// ones) passes as eop_v (a level pulse, no write) for the loader / boot checker.
// ---------------------------------------------------------------------------
module ot_hbm_ingest_xlat #(
    parameter integer WIN_ROW0 = 2000, parameter integer CKV_ROW0 = 3000, parameter integer KEY_ROW0 = 4000,
    parameter integer SLOT_ROWS = 2,
    parameter integer IQ = 4,
    // XPIPE = 1 (sys-takeover 2026-10-10, hing_pipec_a TT -114: qr -> head mux -> S * 3856 -> w1 24 lv, w1 -> w17 ->
    // t -> row -> w2 28 lv): four register stages (latch; divide; window offset / j; row) and an 8-entry output FIFO so
    // the admission rule still sustains a word an edge.  +2 ck edges per word latency, same order / values.
    parameter integer XPIPE = 0
) (
    input  wire          ck, rst_n,
    input  wire          o_v, input wire o_we, input wire [31:0] o_addr, input wire [255:0] o_d,
    output reg           o_cr,
    output wire          wq_v, output wire [1:0] wq_stack, output wire [4:0] wq_pc, output wire [4:0] wq_bank,
    output wire [18:0]   wq_row, output wire [4:0] wq_col, output wire [255:0] wq_data, input wire wq_r,
    output reg           eop_v, output reg [63:0] eop_d,
    output reg           fault
);
    localparam integer LQ = $clog2(IQ);
    // input FIFO {we, addr, data}
    reg [288:0] q [0:IQ-1];
    reg [LQ:0]  qw, qr;
    wire        q_ne = qw != qr;
    wire [288:0] qh = q[qr[LQ-1:0]];
    wire        hwe = qh[288];
    wire [31:0] ha = qh[287:256];
    wire [255:0] hd = qh[255:0];
    always @(posedge ck) if (o_v) q[qw[LQ-1:0]] <= {o_we, o_addr, o_d};
    // stage 1 (divide by 17), stage 2 (address), then a 4-entry output FIFO; a word is admitted only when the output
    // FIFO can hold it and everything ahead of it (no stage ever stalls)
    reg         v1, v2;
    reg  [1:0]  k1;  reg [5:0] sl1; reg [23:0] S1; reg [11:0] w1; reg [255:0] d1;
    reg  [291:0] w2;
    localparam integer OQN = (XPIPE != 0) ? 8 : 4;
    localparam integer LO = (XPIPE != 0) ? 3 : 2;
    reg  [291:0] oq [0:OQN-1];
    reg  [3:0]  ow, orp;
    wire [3:0]  on = ow - orp;
    wire        pop = wq_v && wq_r;
    reg         va, vb;                                          // XPIPE stages
    wire        adv = q_ne && ((XPIPE != 0) ? ({1'b0, on} + v1 + va + vb + v2 < 5'd8) : ({1'b0, on} + v1 + v2 < 5'd4));
    wire [23:0] wdiv_p = {12'd0, (XPIPE != 0) ? S1[11:0] : ha[11:0]} * 24'd3856;
    wire [11:0] wdiv = wdiv_p[23:16];
    wire [11:0] w17 = (w1 << 4) + w1;
    wire [11:0] tw = S1[11:0] - w17;
    wire [6:0]  pcg = (k1 == 2'd0) ? w1[6:0] : S1[6:0];
    wire [13:0] j   = (k1 == 2'd0) ? {2'd0, tw} : S1[20:7];
    wire [18:0] rb  = (k1 == 2'd0) ? WIN_ROW0 : (k1 == 2'd1) ? CKV_ROW0 : KEY_ROW0;
    wire [18:0] row = rb + sl1 * SLOT_ROWS + (j >> 10);
    // XPIPE datapath: stage a (divide), stage b (window offset / j / pc), stage 2 (row)
    reg  [1:0]  ka, kb; reg [5:0] sla, slb; reg [23:0] Sa; reg [11:0] wa; reg [255:0] da, db; reg [6:0] pcb; reg [13:0] jb;
    wire [11:0] wa17 = (wa << 4) + wa;
`ifdef OT_XLAT_MUT_XSTAGE
    wire [11:0] twa  = S1[11:0] - wa17;                          // mutant: stage b takes S from the wrong stage
`else
    wire [11:0] twa  = Sa[11:0] - wa17;
`endif
    wire [6:0]  pca  = (ka == 2'd0) ? wa[6:0] : Sa[6:0];
    wire [13:0] ja   = (ka == 2'd0) ? {2'd0, twa} : Sa[20:7];
    wire [18:0] rbb  = (kb == 2'd0) ? WIN_ROW0 : (kb == 2'd1) ? CKV_ROW0 : KEY_ROW0;
    wire [18:0] rowb = rbb + slb * SLOT_ROWS + (jb >> 10);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin va <= 1'b0; vb <= 1'b0; end
        else begin va <= (XPIPE != 0) && v1; vb <= va; end
    always @(posedge ck) begin
        if (v1) begin ka <= k1; sla <= sl1; Sa <= S1; wa <= wdiv; da <= d1; end
        if (va) begin kb <= ka; slb <= sla; pcb <= pca; jb <= ja; db <= da; end
    end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            qw <= 0; qr <= 0; v1 <= 0; v2 <= 0; o_cr <= 0; ow <= 0; orp <= 0; fault <= 0; eop_v <= 0; eop_d <= 0;
        end else begin
            if (o_v) qw <= qw + 1'b1;
            o_cr <= 1'b0; eop_v <= 1'b0; v1 <= 1'b0;
            if (adv) begin
                qr <= qr + 1'b1; o_cr <= 1'b1;
                if (ha == 32'hFFFFFFFF) begin eop_v <= 1'b1; eop_d <= hd[63:0]; end
                else if (!hwe || ha[31:30] == 2'd3 || (ha[31:30] == 2'd0 && ha[23:12] != 12'd0)) fault <= 1'b1;
                else begin v1 <= 1'b1; k1 <= ha[31:30]; sl1 <= ha[29:24]; S1 <= ha[23:0]; w1 <= (XPIPE != 0) ? 12'd0 : wdiv; d1 <= hd; end
            end
            v2 <= (XPIPE != 0) ? vb : v1;
            if (XPIPE != 0) begin if (vb) w2 <= {pcb[6:5], pcb[4:0], jb[9:7], jb[1:0], rowb, jb[6:2], db}; end
            else if (v1) w2 <= {pcg[6:5], pcg[4:0], j[9:7], j[1:0], row, j[6:2], d1};
            if (v2) begin oq[ow[LO-1:0]] <= w2; ow <= ow + 1'b1; end
            if (pop) orp <= orp + 1'b1;
        end
    end
    wire [291:0] oh = oq[orp[LO-1:0]];
    assign wq_v = on != 4'd0;
    assign {wq_stack, wq_pc, wq_bank, wq_row, wq_col} = oh[291:256];
    assign wq_data = oh[255:0];
endmodule
