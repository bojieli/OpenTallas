`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, RTL-BUILD-KV/BOOT 2026-10-18 (results/arch/qwen_kv_boot_path_1018/note.md): the embedding gateway for
// the STATIC KV die, successor of qkd_embgw_boot.  The legacy gateway sent BOOT_WR / BOOT_END over four credit links
// (emf_<q> / emr_<q>) to the per-stack embedding strips (ot_qfd_emb_strip in qkd_land) and took {count, checksum}
// STATUS back; the static die removed the strips, so those links have no far end.  This cell does the strips' boot
// job itself, at the gateway:
//   hb {v, end, E 25, data 256} (host boot words, BD-word skid, hb_cr = one credit a word taken: the HOST boot
//   boundary, owner rule 10-14: credits stay at the boot / off-die boundaries)
//   BOOT_WR  -> map E (ot_qfd_emb_pkg.emb_loc, the strip's map, unchanged) -> ONE registered boot word a send edge
//               bw = {data 256, address 29 = {bank, col, row}, pc 5, stack 2, v} to the writer-side chain root
//               (qkd_kv_es_fan_root2_b), which carries it on the existing static PC chain to the home PC's station
//               (qkd_kv_pc_chain_station_b) -> that PC's HOST slice land_es (the slice's landing source, unchanged
//               qkd_host_pc_slice_die) -> the slice's boot-qualified static arbiter -> es merge _b -> the controller.
//               count + checksum (sum of crc_sector(E, data) mod 2^32, the strip's definition, cumulative from
//               reset as the strips' were) are taken on the words as sent.
//   BOOT_END -> expected {count [31:0], checksum [63:32]} (the HOST dispatcher sends it only after every boot write's
//               REAL controller completion has retired on its commit-order ledger); emb_ready drops, and HOLD edges
//               later rises iff the sums match (else fault code bit 5).  HOLD keeps the not-ready phase the HOST
//               boot barrier (qkd_host_emb_boot_barrier, require_fresh) must observe; the legacy STATUS round trip
//               gave the same window.
//   Re-load: a BOOT_WR at the skid head while emb_ready is high first drops emb_ready and holds the stream HOLD edges
//               (REOPEN), so every PC's es merge _b has handed its controller face back to the HOST slice before the
//               first new word can reach it (the est trunk is shorter than HOLD edges).  The HOST stops the static
//               programme before a re-load (boot is the exceptional phase).
//   est = {cause 11, fault, emb_ready}: cause [7:0] fault code ([0] BOOT_WR sector out of range, [5] sum mismatch),
//   [8] 0 (no strip link), [9] boot skid overrun, [10] 0 (no strip link credits).
// Pacing: one send every GAP edges (GAP >= 1).  A PC receives one word per 128 consecutive sectors of an ascending
// image; the slice's 4-word landing queue and the controller's static queue absorb the HBM side (credits inside the
// slice); an over-full slice queue is a fault there, never a stall here (boot contract, note.md).
// MUT (bench only): 1 = BOOT_WR mapped to pc ^ 1; 2 = BOOT_END checks the count only; 3 = no REOPEN (emb_ready stays
// high while a re-load is written).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_embgw_boot_s #(
    parameter integer BD   = 4,
    parameter integer GAP  = 1,
    parameter integer HOLD = 64,
    parameter integer ROW0 = 24427,
    parameter integer MUT  = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [282:0]  hb,
    output reg           hb_cr,
    output wire [12:0]   est,
    output reg  [292:0]  bw
);

  localparam integer VOCAB = 151936;
  localparam integer NSEC  = 128;                  // code sectors a row
  localparam integer E_SCALE = VOCAB * NSEC;       // 19,447,808: first scale sector
  localparam integer NSCALE = VOCAB / 16;          // 9,496 scale sectors
  localparam integer E_END = E_SCALE + NSCALE;     // 19,457,304 logical sectors
  localparam integer E_ROPE = E_END;
  localparam integer E_ROPE_END = E_ROPE + 1024*128;
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
      end else if(e >= 25'(E_ROPE))begin
        s=e-25'(E_ROPE);t=18'(s>>7);i=s[6:0];k=i[6:5];q=i[4:0];p=t[9:0];ro=8'd149;
      end else begin
        s = e - 25'(E_SCALE); k = s[6:5]; q = s[4:0]; p = 10'(SCALE_P0) + 10'(s[13:7]); ro = 8'(ROWS - 1);
      end
      emb_loc = {e < 25'(E_ROPE_END), k, q, p[9:7], p[1:0], p[6:2], ro};
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
      if(e>=25'(E_ROPE))begin s=e-25'(E_ROPE);stack_of=s[6:5];end
      else stack_of = (e < 25'(E_SCALE)) ? e[6:5] : s[6:5];
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

    localparam integer BA = (BD <= 2) ? 1 : $clog2(BD);
    localparam integer GW = (GAP <= 1) ? 1 : $clog2(GAP + 1);
    localparam integer HW = $clog2(HOLD + 2);
    // ---- reset: asynchronous assert, synchronous release (as qkd_embgw_boot) ----
    reg rs0, rs;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin rs0 <= 1'b0; rs <= 1'b0; end else begin rs0 <= 1'b1; rs <= rs0; end
    // ---- hb pin capture ----
    reg          hbv_p, hbe_p;
    reg [24:0]   hbs_p;
    reg [255:0]  hbd_p;
    always @(posedge ck or negedge rs) if (!rs) hbv_p <= 1'b0; else hbv_p <= hb[0];
    always @(posedge ck) begin hbe_p <= hb[1]; hbs_p <= hb[26:2]; hbd_p <= hb[282:27]; end
    // ---- boot skid ----
    reg  [281:0] bq [0:BD-1];
    reg  [BA:0]  bwp, brp;
    wire         bne    = (bwp != brp);
    wire         bfull  = (bwp[BA-1:0] == brp[BA-1:0]) && (bwp[BA] != brp[BA]);
    wire [281:0] bh     = bq[brp[BA-1:0]];
    wire         bh_end = bh[281];
    wire [24:0]  bh_e   = bh[280:256];
    wire [255:0] bh_d   = bh[255:0];
    always @(posedge ck) if (hbv_p && !bfull) bq[bwp[BA-1:0]] <= {hbe_p, hbs_p, hbd_p};
    // ---- pacing / REOPEN ----
    reg  [GW-1:0] gc;
    reg  [HW-1:0] wc, hold;
    reg           emb_ready, pend, f_bq, ck_v;
    wire          reopen = bne && !bh_end && emb_ready && MUT != 3;
    wire          go     = bne && (gc == 0) && (wc == 0) && !reopen;
    wire [25:0]   loc    = emb_loc(bh_e);             // {valid, stack, pc, bank, col, row_off}
    wire [4:0]    mpc    = (MUT == 1) ? (loc[22:18] ^ 5'd1) : loc[22:18];
    wire [18:0]   mrow   = 19'(ROW0) + 19'(loc[7:0]);
    // ---- checksum stage (registered: the sums are compared HOLD edges after BOOT_END) ----
    reg  [31:0]   ck_c, a_cnt, a_csum, x_cnt, x_csum;
    reg  [7:0]    fc;
    always @(posedge ck) ck_c <= crc_sector(bh_e, bh_d);
    always @(posedge ck) if (go && !bh_end) bw[292:1] <= {bh_d, loc[17:13], loc[12:8], mrow, mpc, loc[24:23]};
    always @(posedge ck or negedge rs)
        if (!rs) begin
            bwp <= 0; brp <= 0; gc <= 0; wc <= 0; hb_cr <= 1'b0; bw[0] <= 1'b0; ck_v <= 1'b0; f_bq <= 1'b0;
            a_cnt <= 0; a_csum <= 0; x_cnt <= 0; x_csum <= 0; pend <= 1'b0; emb_ready <= 1'b0; hold <= 0; fc <= 8'd0;
        end else begin
            hb_cr <= go;
            bw[0] <= go && !bh_end && loc[25];
            ck_v  <= go && !bh_end && loc[25];
            if (hbv_p) begin if (bfull) f_bq <= 1'b1; else bwp <= bwp + 1'b1; end
            if (go) begin brp <= brp + 1'b1; gc <= GW'(GAP - 1); end
            else if (gc != 0) gc <= gc - 1'b1;
            if (reopen) begin emb_ready <= 1'b0; wc <= HW'(HOLD); end
            else if (wc != 0) wc <= wc - 1'b1;
            if (go && !bh_end && !loc[25]) fc[0] <= 1'b1;   // out-of-range sector: never written
            if (ck_v) begin a_cnt <= a_cnt + 1'b1; a_csum <= a_csum + ck_c; end
            if (go && bh_end) begin
                x_cnt <= bh_d[31:0]; x_csum <= bh_d[63:32];
                emb_ready <= 1'b0; pend <= 1'b1; hold <= HW'(HOLD);
            end else if (pend) begin
                if (hold != 0) hold <= hold - 1'b1;
                else begin
                    pend <= 1'b0;
                    if (a_cnt == x_cnt && (MUT == 2 || a_csum == x_csum)) emb_ready <= 1'b1;
                    else fc[5] <= 1'b1;
                end
            end
        end
    // ---- status (flops at the pins) ----
    reg  [12:0] st_q;
    wire        any_f = (|fc) | f_bq;
    always @(posedge ck or negedge rs)
        if (!rs) st_q <= 13'd0;
        else st_q <= {1'b0, f_bq, 1'b0, fc, any_f, emb_ready && !any_f};
    assign est = st_q;
endmodule
