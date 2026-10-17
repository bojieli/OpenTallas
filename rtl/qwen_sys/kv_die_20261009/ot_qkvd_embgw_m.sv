`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B ROM TP8, track B (ONE die type: the KV die is merged into the ROM die), 2026-10-13: the merged-die embedding
// gateway (die master qkd_embgw).
//
// The embedding table is read from each die's attached HBM (owner decision; there is no embedding ROM on the die).  The
// gateway ot_qfd_emb_gw (emb-hbm 2026-10-08, UNCHANGED: the function-inlined synthesis copy
// rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_gw.sv) sat inside the r21c hub (ot_qwen_die_hub_emb), which gave it
// its link side: per-link receive FIFOs behind forwarded-clock CDC channels, the x3 skid for the loader's boot words and
// the Gray link credits.  On the merged die the gateway is its own cell and talks to the four landing strips' embedding
// engines (qkd_land_emb: ot_qkvd_emb_strip_c, the ot_qfd_emb_strip link protocol unchanged) over plain registered
// die words on ONE clock, so the link side is this file:
//
//   SU face     ea {v, kind, 24-b address} in, ea_cr out, eq {v, 512 b} out: the r21f embedding face, unchanged
//               (ot_qfd_su_embed_pf).  Captured / launched from flops (the gateway's own eq_* / ea_cr registers).
//   strip links (x4, stack k = code words 16 k .. 16 k + 15 of every row), credit flow, no ready:
//     lr_v / lr_k / lr_p / lr_s / lr_d   a strip word {kind 2 (CODE / SCALE / STATUS), poison, sequence 4, data 512};
//                 OD = 4 words buffered a link (the strip's transmit credits, ot_qfd_emb_strip OCR); lt_cr returns one
//                 credit a word the gateway takes (e_take).
//     lt_v / lt_k / lt_s / lt_d          a gateway word {kind 2 (FETCH / BOOT_WR / BOOT_END), sequence 4, data 281}
//                 sent only with a credit in hand (TXC = 4 = the strip's input FIFO; lr_cr returns one a word the strip
//                 consumed).  FETCH goes to all four strips at once (priority, every link credit in hand); BOOT_WR goes
//                 to the stack that holds the sector (stack_of(E), computed when the word enters the skid); BOOT_END
//                 goes to all four and is snooped for the gateway's boot check (bend_*), as in the hub.
//     The link class bit (tag[10] of the r21c link word) is not carried: on this hop every word is an EMB word (class
//     identity is queue identity, kv-die CONTRACT section 6); the gateway sees it as constant 1.  The upper data bits
//     of a gateway -> strip word (data[511:281]) are zero in all three kinds and are not carried either.
//   boot words  hb {v, end, E 25, data 256} from the host ingest router (qkd_host: the ingest engine's sector writes
//               with o_addr[31] = 1 and its BOOT END marker), BD-word skid, hb_cr returns one credit a word sent on.
//   status      st = {cause 11, fault, emb_ready}: emb_ready = the boot load is complete and its count / checksum match
//               (the first-token gate is inside the gateway: a request waits for it); fault is sticky.
//               cause[7:0] the gateway's fault_code, [8] a strip sent without a credit (receive buffer overrun),
//               [9] the host sent without a credit (boot skid overrun), [10] a strip returned more credits than taken.
//
// Every port is a flop at the boundary (input capture registers, registered outputs); reset is asynchronous assert,
// synchronous release (two flops).  The gateway's `fetches` counter is a debug output and is not a port here.
// MUT (bench only): 4 = the gateway's boot gate ignored (ot_qfd_emb_gw MUT 4); 5 = BOOT_WR sent to stack + 1.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_embgw_m #(
    parameter integer RQD = 32,
    parameter integer OD  = 4,
    parameter integer TXC = 4,
    parameter integer BD  = 4,
    parameter integer MUT = 0,
    parameter integer HEADQ = 0       // ot_qfd_emb_gw HEADQ (registered request-FIFO head; 0 = unchanged); MUT 6 = its mutant
) (
    input  wire              ck,
    input  wire              rst_n,
    // SU face
    input  wire              ea_v,
    input  wire              ea_kind,
    input  wire [23:0]       ea_addr,
    output wire              ea_cr,
    output wire              eq_v,
    output wire [511:0]      eq_d,
    // strip -> gateway words (per link) and the credit for the gateway's words
    input  wire [3:0]        lr_v,
    input  wire [4*2-1:0]    lr_k,
    input  wire [3:0]        lr_p,
    input  wire [4*4-1:0]    lr_s,
    input  wire [4*512-1:0]  lr_d,
    input  wire [3:0]        lr_cr,
    // gateway -> strip words (per link) and the credit for the strip's words
    output reg  [3:0]        lt_v,
    output reg  [4*2-1:0]    lt_k,
    output reg  [4*4-1:0]    lt_s,
    output reg  [4*281-1:0]  lt_d,
    output reg  [3:0]        lt_cr,
    // boot words from the host
    input  wire              hb_v,
    input  wire              hb_end,
    input  wire [24:0]       hb_e,
    input  wire [255:0]      hb_d,
    output reg               hb_cr,
    // status
    output wire [12:0]       st
);
    localparam [24:0] E_SCALE = 25'd19447808;      // ot_qfd_emb_pkg E_SCALE = VOCAB 151,936 x 128 code sectors
    localparam [1:0] K_FETCH = 2'd0, K_BOOT_WR = 2'd1, K_BOOT_END = 2'd2;
    localparam integer OA = $clog2(OD);
    localparam integer BA = (BD <= 2) ? 1 : $clog2(BD);
    localparam integer CW = $clog2(TXC + 1) + 1;
    localparam integer RW = 2 + 1 + 4 + 512;          // a stored strip word {kind, poison, sequence, data}
    integer i;
    genvar k;
    // ---- reset: asynchronous assert, synchronous release ----
    reg rs0, rs;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin rs0 <= 1'b0; rs <= 1'b0; end else begin rs0 <= 1'b1; rs <= rs0; end
    // ---- input capture ----
    reg          eav_p, eak_p, hbv_p, hbe_p;
    reg [23:0]   eaa_p;
    reg [24:0]   hbs_p;
    reg [255:0]  hbd_p;
    reg [3:0]    lrv_p, lrc_p;
    reg [RW-1:0] lrw_p [0:3];
    always @(posedge ck or negedge rs)
        if (!rs) begin eav_p <= 1'b0; hbv_p <= 1'b0; lrv_p <= 4'd0; lrc_p <= 4'd0; end
        else begin eav_p <= ea_v; hbv_p <= hb_v; lrv_p <= lr_v; lrc_p <= lr_cr; end
    always @(posedge ck) begin
        eak_p <= ea_kind; eaa_p <= ea_addr; hbe_p <= hb_end; hbs_p <= hb_e; hbd_p <= hb_d;
        for (i = 0; i < 4; i = i + 1) lrw_p[i] <= {lr_k[2*i +: 2], lr_p[i], lr_s[4*i +: 4], lr_d[512*i +: 512]};
    end
    // ---- per-link receive buffers (OD words: the strip's transmit credits) ----
    reg  [RW-1:0]    rf  [0:4*OD-1];
    reg  [OA:0]      rfw [0:3];
    reg  [OA:0]      rfr [0:3];
    reg  [3:0]       rne, rfull;
    reg  [4*523-1:0] e_d;
    wire [3:0]       e_take;
    reg  [RW-1:0]    rh;
    always @(*)
        for (i = 0; i < 4; i = i + 1) begin
            rne[i]   = (rfw[i] != rfr[i]);
            rfull[i] = (rfw[i][OA-1:0] == rfr[i][OA-1:0]) && (rfw[i][OA] != rfr[i][OA]);
            rh = rf[i*OD + rfr[i][OA-1:0]];
            // the gateway's 523-b link word {tag 11 = {class 1, kind 2, poison, 3'b0, sequence 4}, data 512}
            e_d[i*523 +: 523] = {1'b1, rh[RW-1 -: 2], rh[RW-3], 3'b000, rh[515:512], rh[511:0]};
        end
    always @(posedge ck) for (i = 0; i < 4; i = i + 1) if (lrv_p[i]) rf[i*OD + rfw[i][OA-1:0]] <= lrw_p[i];
    // ---- the gateway (unchanged) ----
    wire          g_v;
    wire [10:0]   g_tag;
    wire [511:0]  g_d;
    wire          gsend, bend_v;
    wire [63:0]   bend_d;
    wire          emb_ready, g_fault;
    wire [7:0]    g_fc;
    wire [31:0]   g_fetches;
    ot_qfd_emb_gw #(.RQD(RQD), .MUT((MUT == 4 || MUT == 6) ? MUT : 0), .HEADQ(HEADQ)) u_gw (.ck(ck), .rn(rs),
        .ea_v(eav_p), .ea_kind(eak_p), .ea_addr(eaa_p), .ea_cr(ea_cr), .eq_v(eq_v), .eq_d(eq_d),
        .e_v(rne), .e_d(e_d), .e_take(e_take),
        .g_v(g_v), .g_tag(g_tag), .g_d(g_d), .g_rdy(gsend), .bend_v(bend_v), .bend_d(bend_d),
        .emb_ready(emb_ready), .fault(g_fault), .fault_code(g_fc), .fetches(g_fetches));
    // ---- boot skid (BD words: the host router's credits) ----
    reg  [281:0]  bq   [0:BD-1];                 // {end, E 25, data 256}
    reg  [1:0]    bdst [0:BD-1];
    reg  [BA:0]   bw, br;
    wire          bne   = (bw != br);
    wire          bfull = (bw[BA-1:0] == br[BA-1:0]) && (bw[BA] != br[BA]);
    wire [281:0]  bh    = bq[br[BA-1:0]];
    wire          bh_end = bh[281];
    wire [1:0]    bh_dst = bdst[br[BA-1:0]];
    wire [24:0]   hbs_sc = hbs_p - E_SCALE;
    wire [1:0]    hb_stk = (hbs_p < E_SCALE) ? hbs_p[6:5] : hbs_sc[6:5];     // ot_qfd_emb_pkg stack_of(E)
    always @(posedge ck) if (hbv_p && !bfull) begin
        bq[bw[BA-1:0]]   <= {hbe_p, hbs_p, hbd_p};
        bdst[bw[BA-1:0]] <= (MUT == 5) ? (hb_stk + 2'd1) : hb_stk;
    end
    // ---- transmit: link credits, FETCH first, then the boot skid head ----
    reg  [CW-1:0] lc [0:3];
    reg  [3:0]    lcnz;
    always @(*) for (i = 0; i < 4; i = i + 1) lcnz[i] = (lc[i] != 0);
    assign gsend = g_v && (&lcnz);
    wire   bsend = !gsend && bne && (bh_end ? (&lcnz) : lcnz[bh_dst]);
    assign bend_v = bsend && bh_end;
    assign bend_d = bh[63:0];
    reg  [3:0]    tgt;
    always @(*) for (i = 0; i < 4; i = i + 1) tgt[i] = gsend || (bsend && (bh_end || bh_dst == i));
    wire [1:0]    t_k = gsend ? g_tag[9:8] : (bh_end ? K_BOOT_END : K_BOOT_WR);
    wire [3:0]    t_s = gsend ? g_tag[3:0] : 4'd0;
    wire [280:0]  t_d = gsend ? g_d[280:0] : (bh_end ? {217'd0, bh[63:0]} : {bh[255:0], bh[280:256]});
    reg           f_rx, f_bq, f_lc;
    always @(posedge ck) for (i = 0; i < 4; i = i + 1) if (tgt[i]) begin
        lt_k[2*i +: 2] <= t_k; lt_s[4*i +: 4] <= t_s; lt_d[281*i +: 281] <= t_d;
    end
    always @(posedge ck or negedge rs)
        if (!rs) begin
            bw <= 0; br <= 0; lt_v <= 4'd0; lt_cr <= 4'd0; hb_cr <= 1'b0; f_rx <= 1'b0; f_bq <= 1'b0; f_lc <= 1'b0;
            for (i = 0; i < 4; i = i + 1) begin rfw[i] <= 0; rfr[i] <= 0; lc[i] <= TXC[CW-1:0]; end
        end else begin
            for (i = 0; i < 4; i = i + 1) begin
                if (lrv_p[i]) begin if (rfull[i]) f_rx <= 1'b1; else rfw[i] <= rfw[i] + 1'b1; end
                if (e_take[i]) rfr[i] <= rfr[i] + 1'b1;
                lc[i] <= lc[i] - {{(CW-1){1'b0}}, tgt[i]} + {{(CW-1){1'b0}}, lrc_p[i]};
                if (lrc_p[i] && !tgt[i] && lc[i] == TXC[CW-1:0]) f_lc <= 1'b1;
            end
            lt_cr <= e_take;
            lt_v  <= tgt;
            if (hbv_p) begin if (bfull) f_bq <= 1'b1; else bw <= bw + 1'b1; end
            if (bsend) br <= br + 1'b1;
            hb_cr <= bsend;
        end
    // ---- status (flops at the pins) ----
    reg [12:0] st_q;
    always @(posedge ck or negedge rs)
        if (!rs) st_q <= 13'd0;
        else st_q <= {f_lc, f_bq, f_rx, g_fc, g_fault | f_rx | f_bq | f_lc, emb_ready};
    assign st = st_q;
endmodule
