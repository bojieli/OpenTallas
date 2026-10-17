`timescale 1ns/1ps
// Per-pseudo-channel embedding port (emb-hbm 2026-10-08), in the controller band beside qfd_ctrl_emb_<pc>, HBM
// controller clock, between the controller / PHY and the PC's core-clock crossing (qfd_cdc).  It owns the ECC of the
// stored copy: every embedding sector is 256 data + 32 check bits = four SECDED(72,64) words in the HBM3E ECC side-band
// (ot_qfd_emb_pkg enc256: the KV path's / near-HBM row client's SECDED72 bit layout).
//   * class: the PHY returns a PC's read data in RD issue order, so every RD the controller issues (col_v && !col_we,
//     registered outputs of ot_qwen_ctrl_pc_emb) pushes its class (col_sr: static = embedding, else the KV stream)
//     into an RQD-entry in-order FIFO and every returned beat (r_v, 288 b) pops it;
//   * KV beats leave unchanged on the KV landing path (kv_v / kv_d, from flops);
//   * embedding beats are decoded in two registered stages (SECDED72 syndromes, then correction) and leave toward the
//     strip engine as {ue, ce, data 256} (em_v / em_d): ce = a single-bit error corrected, ue = uncorrectable;
//   * static WRITE data (the boot load, 256 b) arrives from the strip engine with its command (w_v / w_d), is encoded
//     (enc256) into a WQD-entry FIFO whose head is the PHY write data of the next static WR (col_v && col_we && col_sr).
// Faults (sticky): a beat with no RD outstanding, class FIFO overflow, a static WR with no data, write FIFO overflow.
// MUT = 3 (bench mutant, must FAIL): the correction is skipped (the raw data bits pass, nothing flagged).
// KVW = 1 (sys-takeover 2026-10-09, opt-in; registry qfd_hbm_ecc_provider): the ECC provider for the MUTABLE KV payload.
//   KV write data (kw_v / kw_d, 256 b, with its KV WR command, same credit discipline as w_v) is encoded here into the
//   HBM3E ECC side-band (enc256: 32 check bits per 256, the layout ot_qfd_kv_landing_ecc decodes) into a KWQD FIFO whose
//   head is the PHY write data of the next KV WR (col_v && col_we && !col_sr); wd = col_sr ? static head : KV head.
//   KV reads already leave as the full 288-b codeword (kv_d) and are corrected by ot_qfd_kv_landing_ecc.  No in-band
//   cost: 0 cycles, +KWQD x 288 flops.  Faults: KV WR with no data, KV write FIFO overflow.
// KVW = 2 (sys-takeover 2026-10-09, the die's actual KV write timing): the per-PC STREAM4 CDC (ot_qwen_stream4_cdc_pc)
//   hands the KV write data over at its WR COLUMN (h_wcon = col_v && col_we && !col_sr) and presents it ONE edge later
//   (h_cv / h_cdata) -- it cannot be pushed ahead of the column as KVW 1 assumes (a KVW 1 port faults "KV WR with no
//   data" on every die write).  KVW 2: kw_v / kw_d = h_cv / h_cdata, encoded (enc256) into a register; EVERY WR's PHY
//   write data (static and KV) is presented on wd two edges after its WR column (static head captured at the column).
//   Faults: KV data with no KV WR column on the previous edge, a KV WR column with no data on the next edge.  0 cycles
//   on the token path (write data latency +2 hclk inside the PHY's programmable write latency).
// MUT = 4 / 5 (bench mutants): KV write check column 0 wrong / KV write side-band dropped (check bits 0).
module ot_qfd_emb_pcport #(
    parameter integer RQD = 32,
    parameter integer WQD = 4,
    parameter integer MUT = 0,
    parameter integer KVW = 0,
    parameter integer KWQD = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         col_v,
    input  wire         col_we,
    input  wire         col_sr,
    input  wire         w_v,
    input  wire [255:0] w_d,
    output wire [287:0] wd,               // the PHY write data of the next static WR (FIFO head); KVW: of the next WR
    input  wire         kw_v,             // KVW: KV write data (256 b), one per KV WR command
    input  wire [255:0] kw_d,
    input  wire         r_v,
    input  wire [287:0] r_d,
    output reg          kv_v,
    output reg  [287:0] kv_d,
    output reg          em_v,
    output reg  [257:0] em_d,             // {ue, ce, data}
    output reg          fault
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
    localparam integer WA = (WQD > 1) ? $clog2(WQD) : 1;
    reg [RQD-1:0] kq;
    reg [RA:0] kw, kr;
    reg [287:0] wq [0:WQD-1];
    reg [WA:0] ww, wr;
    wire rd_issue = col_v && !col_we;
    wire wr_static = col_v && col_we && col_sr;
    wire k_empty = kw == kr;
    wire k_full = (kw[RA-1:0] == kr[RA-1:0]) && (kw[RA] != kr[RA]);
    wire w_empty = ww == wr;
    wire w_full = (ww[WA-1:0] == wr[WA-1:0]) && (ww[WA] != wr[WA]);
    wire cls = kq[kr[RA-1:0]];
    localparam integer KA = (KWQD > 1) ? $clog2(KWQD) : 1;
    reg [287:0] kq_w [0:KWQD-1];
    reg [KA:0] kww, kwr;
    wire wr_kv = col_v && col_we && !col_sr;
    wire kw_empty = kww == kwr;
    wire kw_full = (kww[KA-1:0] == kwr[KA-1:0]) && (kww[KA] != kwr[KA]);
    // KVW 2: wd two edges after every WR column (s2_wd); KVW 1 / 0: combinational heads at the column (unchanged)
    reg wc1_kv, wc1_st; reg [287:0] st1_wd, s2_wd;
    assign wd = (KVW == 2) ? s2_wd : (KVW != 0 && !col_sr) ? kq_w[kwr[KA-1:0]] : wq[wr[WA-1:0]];
    function automatic [287:0] kenc(input [255:0] x);
        reg [287:0] c;
        begin
            c = enc256(x);
            if (MUT == 4) c[0] = ~c[0];          // check column 0 of word 0 wrong
            if (MUT == 5) begin c[0] = 1'b0; c[1] = 1'b0; c[3] = 1'b0; c[7] = 1'b0; c[15] = 1'b0; c[31] = 1'b0; c[63] = 1'b0; c[71] = 1'b0; end
            kenc = c;
        end
    endfunction
    always @(posedge clk) if (KVW == 1 && kw_v) kq_w[kww[KA-1:0]] <= kenc(kw_d);
    always @(posedge clk) if (KVW == 2) begin
        if (wr_static) st1_wd <= wq[wr[WA-1:0]];
        if (wc1_kv) s2_wd <= kenc(kw_d); else if (wc1_st) s2_wd <= st1_wd;
    end
    // decode pipe: stage 1 raw + syndromes, stage 2 corrected
    reg v1; reg [287:0] c1; reg [31:0] y1;
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            kw <= 0; kr <= 0; ww <= 0; wr <= 0; kww <= 0; kwr <= 0; kv_v <= 1'b0; em_v <= 1'b0; v1 <= 1'b0; fault <= 1'b0;
            wc1_kv <= 1'b0; wc1_st <= 1'b0;
        end else begin
            if (rd_issue) begin kw <= kw + 1'b1; if (k_full) fault <= 1'b1; end
            if (r_v) begin kr <= kr + 1'b1; if (k_empty) fault <= 1'b1; end
            kv_v <= r_v && !cls;
            v1 <= r_v && cls;
            em_v <= v1;
            if (w_v) begin ww <= ww + 1'b1; if (w_full) fault <= 1'b1; end
            if (wr_static) begin wr <= wr + 1'b1; if (w_empty) fault <= 1'b1; end
            if (KVW == 1 && kw_v) begin kww <= kww + 1'b1; if (kw_full) fault <= 1'b1; end
            if (KVW == 1 && wr_kv) begin kwr <= kwr + 1'b1; if (kw_empty) fault <= 1'b1; end
            if (KVW == 2) begin
                wc1_kv <= wr_kv; wc1_st <= wr_static;
                if (kw_v != wc1_kv) fault <= 1'b1;      // KV data exactly one edge after its KV WR column
            end
        end
    always @(posedge clk) begin : dp
        reg [65:0] dc; reg ue, ce; reg [255:0] d;
        if (rd_issue) kq[kw[RA-1:0]] <= col_sr;
        if (w_v) wq[ww[WA-1:0]] <= enc256(w_d);
        if (r_v) begin
            kv_d <= r_d; c1 <= r_d;
            for (i = 0; i < 4; i = i + 1) y1[i*8 +: 8] <= syn64(r_d[i*72 +: 72]);
        end
        ue = 1'b0; ce = 1'b0;
        for (i = 0; i < 4; i = i + 1) begin
            dc = cor64(c1[i*72 +: 72], (MUT == 3) ? 8'd0 : y1[i*8 +: 8]);
            d[i*64 +: 64] = dc[63:0]; ue = ue | dc[65]; ce = ce | dc[64];
        end
        if (v1) em_d <= {ue, ce, d};
    end
endmodule
