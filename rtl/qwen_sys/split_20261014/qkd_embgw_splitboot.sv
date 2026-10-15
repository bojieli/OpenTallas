`timescale 1ns/1ps
// Embedding gateway in the hub (emb-hbm 2026-10-08): the die face the SU's embedding requester talks to, now that the
// table sits in each die's attached HBM instead of the on-die ROM.  The SU face is the r21f embedding ROM's, unchanged
// (ot_qfd_su_embed_pf / ot_qfd_io_embedding_rom): one request word {kind, 24-b address} with credits (the SU starts
// with RQD credits, ea_cr returns one a request retired), one 512-b response word a request, in request order.
//   kind 0: code word a = t * 64 + w (the 64 bytes 64 w .. 64 w + 63 of row t), kind 1: the BF16 scale of row t.
// The SU fetches a row as 64 code words in order then the scale (a token already buffered is not fetched again), so:
//   * code word 0 of row t opens a FETCH: one EMB-class FETCH word {t, sequence} broadcast on the four stack links
//     (only once the boot load is complete and checked: emb_ready; until then the request waits = the first-token
//     gate); every stack returns its 16 code words in order (code words 16 k .. 16 k + 15 from stack k) and the stack
//     holding the scale returns it after them;
//   * the requests are answered in order from the link receive FIFOs: code word w from link w[5:4], the scale from
//     link (t >> 9) & 3.  No row buffer: the hub's per-link receive buffers hold the words (the link credits cover
//     them); a one-word slot a link (e_take loads it) keeps the FIFO read off the decision path.
//   * boot: the loader's RAW sector stream reaches the strips as EMB BOOT_WR words through the existing x3 path; the
//     BOOT_END word that closes it carries the expected count / checksum (bend_*, snooped by the hub at send).  The four
//     strips answer with STATUS words {count, checksum}; their sums must match: emb_ready (sticky), else fault.
// Fail closed: a request out of sequence or out of range, a link word of the wrong kind / sequence, a POISONED word
// (uncorrectable ECC in HBM) or a failed boot check latches fault and nothing more is answered.
// MUT = 4 (bench mutant, must FAIL): the boot gate is ignored (a fetch before the load is complete).
module ot_qfd_emb_gw_splitboot #(
    parameter integer RQD = 32,
    parameter integer MUT = 0
) (
    input  wire              ck,
    input  wire              rn,
    // SU face (registered at the hub pins by the caller)
    input  wire              ea_v,
    input  wire              ea_kind,
    input  wire [23:0]       ea_addr,
    output reg               ea_cr,
    output reg               eq_v,
    output reg  [511:0]      eq_d,
    // link receive heads, EMB class (the caller pops with e_take)
    input  wire [3:0]        e_v,
    input  wire [4*523-1:0]  e_d,
    output wire [3:0]        e_take,
    // command words to the links (broadcast FETCH)
    output reg               g_v,
    output reg  [10:0]       g_tag,
    output reg  [511:0]      g_d,
    input  wire              g_rdy,
    // the BOOT_END word as the hub sends it (expected sectors [31:0], checksum [63:32])
    input  wire              bend_v,
    input  wire [63:0]       bend_d,
    output reg               emb_ready,
    output wire              fault,
    output reg  [7:0]        fault_code,
    output reg  [31:0]       fetches
);
    
  localparam integer VOCAB = 151936;
  localparam integer NSEC  = 128;                  // code sectors a row
  localparam integer E_SCALE = VOCAB * NSEC;       // 19,447,808: first scale sector
  localparam integer NSCALE = VOCAB / 16;          // 9,496 scale sectors
  localparam integer E_END = E_SCALE + NSCALE;     // 19,457,304 logical sectors
  localparam integer ROWS = 149;                   // row indices a copy
  localparam integer SCALE_P0 = 384;               // first PC-local index of the scale sectors (row ROW0 + 148)

  // EMB link class (link word tag [10:0]): [10] = 1, [9:8] kind, [7] poison, [3:0] sequence
  localparam [1:0] K_FETCH = 2'd0, K_BOOT_WR = 2'd1, K_BOOT_END = 2'd2;   // hub -> strip
  localparam [1:0] K_CODE = 2'd0, K_SCALE = 2'd1, K_STATUS = 2'd2;        // strip -> hub

  // physical location of a logical sector: {valid, stack[1:0], pc[4:0], bank[4:0], col[4:0], row_off[7:0]}
  function automatic [25:0] emb_loc(input [24:0] e);
    reg [24:0] s; reg [17:0] t; reg [6:0] i; reg [9:0] p; reg [7:0] ro; reg [1:0] k; reg [4:0] q;
    begin
      if (e < 25'(E_SCALE)) begin
        t = 18'(e >> 7); i = e[6:0]; k = i[6:5]; q = i[4:0]; p = t[9:0]; ro = 8'(t >> 10);
      end else begin
        s = e - 25'(E_SCALE); k = s[6:5]; q = s[4:0]; p = 10'(SCALE_P0) + 10'(s[13:7]); ro = 8'(ROWS - 1);
      end
      emb_loc = {e < 25'(E_END), k, q, p[9:7], p[1:0], p[6:2], ro};
    end
  endfunction

  // the bank / column / row offset of token t's code sectors (the same in every PC)
  function automatic [17:0] code_bcr(input [17:0] t);   // {bank[4:0], col[4:0], row_off[7:0]}
    code_bcr = {t[9:7], t[1:0], t[6:2], 8'(t >> 10)};
  endfunction
  // token t's scale: {stack[1:0] [28:27], pc[4:0] [26:22], bank[4:0] [21:17], col[4:0] [16:12], row_off[7:0] [11:4],
  // lane[3:0] [3:0]}
  function automatic [28:0] scale_loc(input [17:0] t);
    reg [13:0] s; reg [9:0] p;
    begin
      s = 14'(t >> 4); p = 10'(SCALE_P0) + 10'(s[13:7]);
      scale_loc = {s[6:5], s[4:0], p[9:7], p[1:0], p[6:2], 8'(ROWS - 1), t[3:0]};
    end
  endfunction
  // the stack that holds logical sector e
  function automatic [1:0] stack_of(input [24:0] e);
    reg [24:0] s;
    begin
      s = e - 25'(E_SCALE);
      stack_of = (e < 25'(E_SCALE)) ? e[6:5] : s[6:5];
    end
  endfunction

  // ---- SECDED(72,64): ot_gpu_w6_secded_pkg layout (Hamming positions 1..71, check bits at 2^k, overall parity bit 71)
  function automatic [71:0] enc64(input [63:0] data);
    reg [71:0] c; integer p, k, j;
    begin
      c = '0; j = 0;
      for (p = 1; p <= 71; p = p + 1)
        if ((p & (p - 1)) != 0) begin c[p-1] = data[j]; j = j + 1; end
      for (k = 0; k < 7; k = k + 1)
        for (p = 1; p <= 71; p = p + 1)
          if ((p & (1 << k)) != 0 && p != (1 << k)) c[(1<<k)-1] = c[(1<<k)-1] ^ c[p-1];
      c[71] = ^c[70:0]; enc64 = c;
    end
  endfunction
  function automatic [287:0] enc256(input [255:0] d);
    enc256 = {enc64(d[255:192]), enc64(d[191:128]), enc64(d[127:64]), enc64(d[63:0])};
  endfunction
  // decode stage A: {syndrome[6:0], overall parity}
  function automatic [7:0] syn64(input [71:0] code);
    reg [6:0] sy; integer p, k;
    begin
      sy = '0;
      for (k = 0; k < 7; k = k + 1)
        for (p = 1; p <= 71; p = p + 1)
          if ((p & (1 << k)) != 0) sy[k] = sy[k] ^ code[p-1];
      syn64 = {sy, ^code};
    end
  endfunction
  // decode stage B: {ue, corrected, data[63:0]} from the code and its stage-A syndrome
  function automatic [65:0] cor64(input [71:0] code, input [7:0] so);
    reg [71:0] c; reg [6:0] sy; reg ov, ue, ce; reg [63:0] d; integer p, j;
    begin
      c = code; sy = so[7:1]; ov = so[0]; ue = 1'b0; ce = 1'b0;
      if (sy != 0) begin
        if (ov && sy <= 71) begin c[sy-1] = ~c[sy-1]; ce = 1'b1; end
        else ue = 1'b1;
      end else if (ov) begin c[71] = ~c[71]; ce = 1'b1; end
      d = '0; j = 0;
      for (p = 1; p <= 71; p = p + 1)
        if ((p & (p - 1)) != 0) begin d[j] = c[p-1]; j = j + 1; end
      cor64 = {ue, ce, d};
    end
  endfunction

  // ---- boot checksum: zlib.crc32 of {E (4 B LE), data (32 B LE)}, LSB first
  function automatic [31:0] crc_sector(input [24:0] e, input [255:0] d);
    reg [287:0] m; reg [31:0] c; integer i;
    begin
      m = {d, 7'd0, e}; c = 32'hffffffff;
      for (i = 0; i < 288; i = i + 1) c = (c >> 1) ^ ((c[0] ^ m[i]) ? 32'hedb88320 : 32'h0);
      crc_sector = ~c;
    end
  endfunction

    localparam integer RA = $clog2(RQD);
    // ---- request FIFO ------------------------------------------------------------------------------------------------
    reg [24:0] rq [0:RQD-1];
    reg [RA:0] rw, rr;
    wire r_ne = rw != rr;
    wire r_full = (rw[RA-1:0] == rr[RA-1:0]) && (rw[RA] != rr[RA]);
    wire [24:0] rh = rq[rr[RA-1:0]];
    wire hk = rh[24];
    wire [23:0] ha = rh[23:0];
    always @(posedge ck) if (ea_v) rq[rw[RA-1:0]] <= {ea_kind, ea_addr};
    // ---- per-link one-word slots -------------------------------------------------------------------------------------
    reg [3:0] sv;
    reg [522:0] sd [0:3];
    assign e_take = e_v & ~sv;
    // ---- row state -------------------------------------------------------------------------------------------------
    localparam [1:0] S_IDLE = 0, S_ISSUE = 1, S_ROW = 2, S_DEAD = 3;
    reg [1:0] st;
    reg [17:0] ct; reg [3:0] seq; reg [6:0] w;
    wire [1:0] lk = (w == 7'd64) ? ct[10:9] : w[5:4];
    wire [522:0] sl = sd[lk];
    wire sl_ok = sl[522] && sl[521:520] == ((w == 7'd64) ? K_SCALE : K_CODE) && sl[515:512] == seq && !sl[519];
    wire hd_ok = (w == 7'd64) ? (hk && ha == {6'd0, ct}) : (!hk && ha == {ct, w[5:0]});
    wire serve = st == S_ROW && r_ne && sv[lk] && hd_ok && sl_ok;
    // ---- boot status ---------------------------------------------------------------------------------------------
    reg bend; reg [31:0] x_cnt, x_csum, a_cnt, a_csum; reg [2:0] nst;
    reg [3:0] stv;                               // slots holding a STATUS word
    integer i;
    always @(*) for (i = 0; i < 4; i = i + 1) stv[i] = sv[i] && sd[i][522] && sd[i][521:520] == K_STATUS;
    wire [1:0] sp = stv[0] ? 2'd0 : stv[1] ? 2'd1 : stv[2] ? 2'd2 : 2'd3;
    reg f_q;
    assign fault = f_q;
    always @(posedge ck) for (i = 0; i < 4; i = i + 1) if (e_take[i]) sd[i] <= e_d[i*523 +: 523];
    always @(posedge ck or negedge rn)
        if (!rn) begin
            rw <= 0; rr <= 0; sv <= 0; st <= S_IDLE; ct <= 0; seq <= 0; w <= 0; ea_cr <= 1'b0; eq_v <= 1'b0; g_v <= 1'b0;
            bend <= 1'b0; x_cnt <= 0; x_csum <= 0; a_cnt <= 0; a_csum <= 0; nst <= 0; emb_ready <= 1'b0;
            f_q <= 1'b0; fault_code <= 0; fetches <= 0;
        end else begin
            ea_cr <= 1'b0; eq_v <= 1'b0;
            if (ea_v) begin rw <= rw + 1'b1; if (r_full) begin f_q <= 1'b1; fault_code[0] <= 1'b1; end end
            // slots: load / free
            for (i = 0; i < 4; i = i + 1) if (e_take[i]) sv[i] <= 1'b1;
            // boot status words (one a cycle)
            if (|stv) begin
                sv[sp] <= 1'b0;
                if (!bend) begin f_q <= 1'b1; fault_code[6] <= 1'b1; end
                a_cnt <= a_cnt + sd[sp][31:0]; a_csum <= a_csum + sd[sp][63:32]; nst <= nst + 1'b1;
            end
            if (bend_v) begin if(MUT!=6)emb_ready <= 1'b0; bend <= 1'b1; x_cnt <= bend_d[31:0]; x_csum <= bend_d[63:32]; a_cnt <= 0; a_csum <= 0; nst <= 0; end
            if (bend && nst == 3'd4) begin
                bend <= 1'b0;
                if (a_cnt == x_cnt && a_csum == x_csum) emb_ready <= 1'b1;
                else begin f_q <= 1'b1; fault_code[5] <= 1'b1; end
            end
            case (st)
                S_IDLE: if (r_ne) begin
                    if (hk || ha[5:0] != 6'd0) begin f_q <= 1'b1; fault_code[1] <= 1'b1; st <= S_DEAD; end
                    else if (ha[23:6] >= 18'(VOCAB)) begin f_q <= 1'b1; fault_code[2] <= 1'b1; st <= S_DEAD; end
                    else if (emb_ready || MUT == 4) begin
                        ct <= ha[23:6]; seq <= seq + 1'b1; w <= 0; st <= S_ISSUE;
                        g_v <= 1'b1; g_tag <= {1'b1, K_FETCH, 1'b0, 3'd0, 4'(seq + 1'b1)}; g_d <= {494'd0, ha[23:6]};
                    end
                end
                S_ISSUE: if (g_rdy) begin g_v <= 1'b0; st <= S_ROW; fetches <= fetches + 1'b1; end
                S_ROW: if (r_ne) begin
                    if (!hd_ok) begin f_q <= 1'b1; fault_code[1] <= 1'b1; st <= S_DEAD; end
                    else if (sv[lk] && !(sd[lk][521:520] == K_STATUS)) begin
                        if (sl[519]) begin f_q <= 1'b1; fault_code[4] <= 1'b1; st <= S_DEAD; end
                        else if (!sl_ok) begin f_q <= 1'b1; fault_code[3] <= 1'b1; st <= S_DEAD; end
                        else begin
                            eq_v <= 1'b1; eq_d <= (w == 7'd64) ? {496'd0, sl[15:0]} : sl[511:0];
                            sv[lk] <= 1'b0; rr <= rr + 1'b1; ea_cr <= 1'b1;
                            w <= w + 1'b1;
                            if (w == 7'd64) st <= S_IDLE;
                        end
                    end
                end
                default: ;
            endcase
            if (f_q) st <= S_DEAD;
        end
endmodule
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
module ot_qkvd_embgw_splitboot #(
    parameter integer RQD = 32,
    parameter integer OD  = 4,
    parameter integer TXC = 4,
    parameter integer BD  = 4,
    parameter integer MUT = 0
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
    ot_qfd_emb_gw_splitboot #(.RQD(RQD), .MUT((MUT == 4) ? 4 : 0)) u_gw (.ck(ck), .rn(rs),
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

// Qwen ROM TP8 die (track B, KV merged): slot cells of the KV-centre masters qkd_embgw (embedding gateway) and qkd_host
// (host / control port), contract results/arch/hier_contract_1012/qwen_rom_tp8.json (v4b), el1013-qwen-embgw-host
// 2026-10-13.  Each cell is WIRING ONLY around its body: no logic and no flop is added or removed here.
// Packing tables are LSB-FIRST (the first field is bit 0).  A bundle with a bit against the flow is two ports on the
// same face: x (with the flow) + x_cr (the credit, against it).  Bits of a contract bundle that have no body port are
// NOT ports of the cell and are NOT tied off: they are posted as contract questions (el1011-qwen-tp8.log).
//
// ---- qkd_embgw: body ot_qkvd_embgw_m (the unchanged gateway ot_qfd_emb_gw + its merged-die link side) -------------
//   r_ea[25:0]      in   { ea_v, ea_kind, ea_addr[23:0] }                       SU embedding request (W, M5)
//   t_ecr           out  { ea_cr }                                              one credit a request retired
//   t_eq[512:0]     out  { eq_v, eq_d[511:0] }                                  one 512-b response word a request
//   emr_<q>[519:0]  in   { v, data[511:0], sequence[3:0], poison, kind[1:0] }   strip q -> gateway word
//   emr_<q>_cr      in   { strip q consumed one gateway word }                  (travels WITH emr: the strip's i_cr)
//   emf_<q>[287:0]  out  { v, data[280:0], sequence[3:0], kind[1:0] }           gateway -> strip q word
//   emf_<q>_cr      out  { the gateway took one emr_<q> word }                  (travels WITH emf: the strip's o_cr)
//   hb[282:0]       in   { v, end, E[24:0], data[255:0] }                       boot words from qkd_host (NEW bundle)
//   hb_cr           out  { one boot word sent on }                              credit, against hb
//   est[12:0]       out  { emb_ready, fault, cause[10:0] }                      status to qkd_host (NEW bundle)
//   <q> = WS, WN, ES, EN = stack 0, 1, 2, 3 (tools/qwen_kv_die/kv_die.py STACKS order; the landing strip's stack strap
//   st[1:0] must be the same index).  kind: emr 0 CODE / 1 SCALE / 2 STATUS; emf 0 FETCH / 1 BOOT_WR / 2 BOOT_END.
//   Against the landing leaf as built (qkd_land_emb, branch el1013-qwen-kvstrips: emf / emr [529:0] = {credit, 5'b0,
//   {tag 11, data 512}, v}): v = bit 0 and data[j] = bit 1 + j on both sides; sequence = land [516:513]; emr poison =
//   land emr[520]; kind = land [522:521]; credit = land [529].  Land bits [528:524] (always 0), [523] (the link class
//   bit: constant 1, class = queue on this hop), [519:517] (always 0) and emf [512:282] (data[511:281], zero in every
//   gateway word) have no body port on this side.
//   Contract bundles with NO body port (questions posted): gq[529:0], gr[529:0] (the EMBQ / EMBD classes through the
//   sequencer: the SU face ends here directly), t_eq[1023:513] (the 1,024-b ingress: the body answers 512 b a word).
// OT_QKD_SLOT_MUT (bench mutant only, never synthesized): t_eq data bits 100 and 101 swapped (a packing fault).
module qkd_embgw_splitboot (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [25:0]   r_ea,
    output wire          t_ecr,
    output wire [512:0]  t_eq,
    input  wire [519:0]  emr_WS,
    input  wire          emr_WS_cr,
    output wire [287:0]  emf_WS,
    output wire          emf_WS_cr,
    input  wire [519:0]  emr_WN,
    input  wire          emr_WN_cr,
    output wire [287:0]  emf_WN,
    output wire          emf_WN_cr,
    input  wire [519:0]  emr_ES,
    input  wire          emr_ES_cr,
    output wire [287:0]  emf_ES,
    output wire          emf_ES_cr,
    input  wire [519:0]  emr_EN,
    input  wire          emr_EN_cr,
    output wire [287:0]  emf_EN,
    output wire          emf_EN_cr,
    input  wire [282:0]  hb,
    output wire          hb_cr,
    output wire [12:0]   est
);
    wire [519:0] emr [0:3];
    wire [287:0] emf [0:3];
    assign emr[0] = emr_WS; assign emr[1] = emr_WN; assign emr[2] = emr_ES; assign emr[3] = emr_EN;
    assign emf_WS = emf[0]; assign emf_WN = emf[1]; assign emf_ES = emf[2]; assign emf_EN = emf[3];
    wire [3:0]       lr_v, lr_p, lt_v, lt_cr;
    wire [7:0]       lr_k, lt_k;
    wire [15:0]      lr_s, lt_s;
    wire [4*512-1:0] lr_d;
    wire [4*281-1:0] lt_d;
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_lk
        assign lr_v[q]             = emr[q][0];
        assign lr_d[512*q +: 512]  = emr[q][512:1];
        assign lr_s[4*q +: 4]      = emr[q][516:513];
        assign lr_p[q]             = emr[q][517];
        assign lr_k[2*q +: 2]      = emr[q][519:518];
        assign emf[q]              = {lt_k[2*q +: 2], lt_s[4*q +: 4], lt_d[281*q +: 281], lt_v[q]};
    end endgenerate
    wire         eq_v;
    wire [511:0] eq_d;
    wire [12:0]  st;
    ot_qkvd_embgw_splitboot #(.RQD(32), .OD(4), .TXC(4), .BD(4), .MUT(0)) u_body (
        .ck(ck), .rst_n(rst_n),
        .ea_v(r_ea[0]), .ea_kind(r_ea[1]), .ea_addr(r_ea[25:2]), .ea_cr(t_ecr), .eq_v(eq_v), .eq_d(eq_d),
        .lr_v(lr_v), .lr_k(lr_k), .lr_p(lr_p), .lr_s(lr_s), .lr_d(lr_d),
        .lr_cr({emr_EN_cr, emr_ES_cr, emr_WN_cr, emr_WS_cr}),
        .lt_v(lt_v), .lt_k(lt_k), .lt_s(lt_s), .lt_d(lt_d),
        .lt_cr({emf_EN_cr, emf_ES_cr, emf_WN_cr, emf_WS_cr}),
        .hb_v(hb[0]), .hb_end(hb[1]), .hb_e(hb[26:2]), .hb_d(hb[282:27]), .hb_cr(hb_cr),
        .st(st));
`ifdef OT_QKD_SLOT_MUT
    assign t_eq = {eq_d[511:102], eq_d[100], eq_d[101], eq_d[99:0], eq_v};
`else
    assign t_eq = {eq_d, eq_v};
`endif
    assign est = {st[12:2], st[1], st[0]};
endmodule
