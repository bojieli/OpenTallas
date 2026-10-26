`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qkvd_emb_strip_c -- el1013-qwen-kvstrips 2026-10-13: the strip embedding engine with the 32 pseudo-channels reached
// through a registered CHAIN (die master qkd_land_emb at the N end of a KV landing strip; the per-PC ends are in the 32
// qkd_land_pc leaves).  Derived from rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_strip.sv (the function-inline
// synthesis source): the link protocol, the command FSM, the credits, the packer's word format, the transmit FIFO and
// the faults are that file's text UNCHANGED.  What differs:
//   * the static command leaves as one down-chain word a cycle, dn = {w_d 256, row 19, col 5, bank 5, w_v, s_we,
//     side, pc 5, bc, kind, v} with a 2-b word tag on top (dn[297:296]): kind 0 = a static command for PC pc (bc:
//     every PC), kind 1 = POP of PC pc's oldest returned beat (side 0 / 1 = the a / b sector of the word);
//   * the 32 x PFD x 258-b return FIFOs (33,024 of the 39,613 flops of ot_qfd_emb_strip) are NOT here: each PC's FIFO
//     sits in its qkd_land_pc leaf.  The packer asks for the two beats of word m (PCs 2m, 2m + 1; the scale: its PC)
//     with POP words and waits for them on the up chain, up = {beat 258, tag 2, side, v} (a PC answers a POP when its
//     beat is there, so no status travels); the pair then enters the unchanged stage 1 / stage 2.  The POPs of the next
//     FOUR words are sent ahead (tag = word number mod 4; the beats of a word wait in slot tag until the packer takes
//     them in order), so the chain round trip (<= 2 x 32 hops + 4 cycles) is shared by four words.
//   * the boot checksum is a registered XOR tree added to csum one cycle later (see crc_mask);
//   * s_cr is the credit vector of the PCs as it arrives on the strip's credit chain (later than the monolith's: the
//     credit rule only becomes more conservative).
// A beat on the up chain that was not asked for sets fault code bit 2 (the monolith's return-FIFO overrun bit; the
// FIFO overrun itself is reported by the PC leaf on the strip's fault chain).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_emb_strip_c #(
    parameter integer STK = 0,
    parameter integer NPC = 32,
    parameter integer SQD = 4,
    parameter integer PFD = 4,
    parameter integer TXQ = 4,
    parameter integer OCR = 4,               // transmit credits (the endpoint's transmit queue)
    parameter integer ROW0 = 24427,          // first row of the embedding region
    parameter integer TWIN = 0,
    parameter integer TWIN_ROFF = 0,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    // link, EMB class
    input  wire              i_v,
    input  wire [522:0]      i_d,
    output reg               i_cr,
    output reg               o_v,
    output reg  [522:0]      o_d,
    input  wire              o_cr,
    // static commands to the pseudo-channels (registered broadcast)
    output reg  [297:0]      dn,              // down chain (static commands and POPs)
    input  wire [NPC-1:0]    s_cr,
    input  wire [261:0]      up,              // up chain {beat 258 = {ue, ce, data}, tag 2, side, v}
    input  wire [1:0]        stk,             // the stack (strap; replaces the parameter STK of the monolith)
    output wire              fault,
    output wire [7:0]        fault_code,
    output reg  [31:0]       ce_cnt,
    output reg  [31:0]       ue_info          // {valid, token[17:0], word m [3:0], ...} of the first uncorrectable word
);
    // the monolith's static-command outputs, now internal (they leave on dn)
    reg  [NPC-1:0]    s_m;
    reg               s_we;
    reg  [4:0]        s_bank;
    reg  [4:0]        s_col;
    reg  [18:0]       s_row;
    reg  [NPC-1:0]    w_m;
    reg  [255:0]      w_d;
    
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

  // ---- boot checksum: zlib.crc32 of {E (4 B LE), data (32 B LE)}, LSB first.  The monolith evaluates the 288-step
  // bit-serial recurrence in one cycle (93 logic levels in the first gate of this leaf).  The CRC is affine in the
  // message, so bit k = parity(m & MASK_k) ^ CONST_k: a balanced XOR tree, registered (crc_q), added to csum one
  // cycle later (the STATUS word that carries csum cannot leave before every write's credit is home).
  // crc_mask(k) = {CONST_k, MASK_k}: walk the recurrence backwards from output bit k (v = the state bits that reach it).
  function automatic [288:0] crc_mask(input integer k);
    reg [31:0] v; reg t; integer i;
    begin
      v = 32'd1 << k;
      for (i = 287; i >= 0; i = i - 1) begin
        t = ^(v & 32'hedb88320);
        crc_mask[i] = t;
        v = {v[30:0], t};
      end
      crc_mask[288] = ~(^v);                     // the all-ones initial state and the final inversion
    end
  endfunction

    localparam integer PA = $clog2(PFD);
    localparam integer CQ = $clog2(SQD + 1) + 1;
    // ---- input FIFO (4 words: the credits the endpoint holds) ---------------------------------------------------
    reg [522:0] iq [0:3];
    reg [2:0] iw, ir;
    wire i_ne = iw != ir;
    wire [522:0] ih = iq[ir[1:0]];
    wire [1:0] ik = ih[521:520];
    reg fa; reg [7:0] fca;                       // command-side faults
    reg fb; reg [7:0] fcb;                       // return-side faults
    assign fault = fa | fb; assign fault_code = fca | fcb;
    // the packer / transmit state the command side reads (declared here)
    reg v1, v2;
    reg [3:0] tx_res;                            // words reserved in the transmit FIFO (packer in flight + queued)
    reg stat_v;                                  // a STATUS word waits for the transmit FIFO
    wire room = tx_res < 4'(TXQ);
    wire stat_send = stat_v && room && !v1 && !v2;   // STATUS goes in when the packer pipe is empty
    always @(posedge clk) if (i_v) iq[iw[1:0]] <= i_d;
    // ---- per-PC credits -------------------------------------------------------------------------------------------
    reg [CQ-1:0] cred [0:NPC-1];
    reg all1, allf;                              // every PC has >= 1 credit / every PC idle (registered)
    reg [NPC-1:0] ge2;                           // a PC has >= 2 credits (registered)
    // ---- the token queue (packer order) -----------------------------------------------------------------------------
    reg [17:0] tq_t [0:3]; reg [3:0] tq_seq [0:3]; reg tq_sh [0:3]; reg [4:0] tq_spc [0:3];
    reg [2:0] tw, tr;
    wire tq_full = (tw[1:0] == tr[1:0]) && (tw[2] != tr[2]);
    // ---- command FSM ------------------------------------------------------------------------------------------------
    // FETCH: F0 code reads (all PCs) [+ F1 scale read]; BOOT_WR: B0 register + map, B1 issue [+ B2 twin]; BOOT_END: wait
    localparam [2:0] IDLE = 0, F1 = 1, B1 = 2, B2 = 3, E1 = 4;
    reg [2:0] st;
    reg [28:0] sl_q;                             // scale_loc of the fetched token
    reg [24:0] be; reg [255:0] bd; reg [25:0] bl;
    reg [31:0] csum, wcnt;
    wire [287:0] crc_m = {bd, 7'd0, be};
    wire [31:0]  crc_lin;
    genvar gk;
    generate for (gk = 0; gk < 32; gk = gk + 1) begin : g_crc
        localparam [288:0] MK = crc_mask(gk);
        assign crc_lin[gk] = (^(crc_m & MK[287:0])) ^ MK[288];
    end endgenerate
    reg [31:0] crc_q; reg cv;
    reg b1p, b_bad, b_ok; reg [NPC-1:0] b_oh;   // B1's registered pre-step
    always @(posedge clk) crc_q <= crc_lin;
    wire [17:0] ft = ih[17:0];
    wire [28:0] fsl = scale_loc(ft);
    wire [17:0] fbcr = code_bcr(ft);
    wire f_here = fsl[28:27] == stk;
    integer p;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            iw <= 0; ir <= 0; i_cr <= 1'b0; st <= IDLE; tw <= 0; s_m <= 0; w_m <= 0; s_we <= 1'b0;
            csum <= 0; wcnt <= 0; cv <= 1'b0; b1p <= 1'b0; stat_v <= 1'b0; fa <= 1'b0; fca <= 0;
            for (p = 0; p < NPC; p = p + 1) cred[p] <= CQ'(SQD);
            all1 <= 1'b1; allf <= 1'b1; ge2 <= {NPC{1'b1}};
        end else begin : fsm
            reg [NPC-1:0] dec, dec2;
            dec = 0; dec2 = 0;
            s_m <= 0; w_m <= 0; i_cr <= 1'b0; cv <= 1'b0;
            if (cv) csum <= csum + crc_q;
            if (i_v) iw <= iw + 1'b1;
            case (st)
                IDLE: if (i_ne) begin
                    if (ih[522] != 1'b1 || ik == 2'd3) begin
                        fa <= 1'b1; fca[0] <= 1'b1; ir <= ir + 1'b1; i_cr <= 1'b1;
                    end else if (ik == K_FETCH) begin
                        if (all1 && !tq_full && (!f_here || ge2[fsl[26:22]])) begin
                            s_m <= {NPC{1'b1}}; s_we <= 1'b0; s_bank <= fbcr[17:13]; s_col <= fbcr[12:8];
                            s_row <= 19'(ROW0) + 19'(fbcr[7:0]) + ((MUT == 1) ? 19'd1 : 19'd0);
                            dec = {NPC{1'b1}};
                            tq_t[tw[1:0]] <= ft; tq_seq[tw[1:0]] <= ih[515:512]; tq_sh[tw[1:0]] <= f_here;
                            tq_spc[tw[1:0]] <= fsl[26:22];
                            tw <= tw + 1'b1;
                            sl_q <= fsl;
                            if (f_here) st <= F1; else begin ir <= ir + 1'b1; i_cr <= 1'b1; end
                        end
                    end else if (ik == K_BOOT_WR) begin
                        be <= ih[24:0]; bd <= ih[280:25]; bl <= emb_loc(ih[24:0]);
                        st <= B1;
                    end else begin   // BOOT_END: once every static entry has issued (all credits home)
                        if (allf && !stat_v) begin stat_v <= 1'b1; ir <= ir + 1'b1; i_cr <= 1'b1; end
                    end
                end
                F1: begin
                    s_m <= {{(NPC-1){1'b0}}, 1'b1} << sl_q[26:22]; s_we <= 1'b0; s_bank <= sl_q[21:17];
                    s_col <= sl_q[16:12]; s_row <= 19'(ROW0) + 19'(sl_q[11:4]);
                    dec[sl_q[26:22]] = 1'b1;
                    ir <= ir + 1'b1; i_cr <= 1'b1; st <= IDLE;
                end
                B1: if (!b1p) begin
                    // el1013-qwen-kvstrips: the address check, the PC's credit and its one-hot are registered first
                    // (the first gate's worst stage ran from the sector register through the credit update to allf)
                    b1p <= 1'b1; b_bad <= !bl[25] || bl[24:23] != stk; b_oh <= {{(NPC-1){1'b0}}, 1'b1} << bl[22:18];
                    b_ok <= (TWIN != 0) ? ge2[bl[22:18]] : (cred[bl[22:18]] != 0);
                end else begin
                    if (b_bad) begin
                        fa <= 1'b1; fca[1] <= 1'b1; ir <= ir + 1'b1; i_cr <= 1'b1; st <= IDLE; b1p <= 1'b0;
                    end else if (b_ok) begin
                        s_m <= b_oh; w_m <= b_oh;
                        s_we <= 1'b1; s_bank <= bl[17:13]; s_col <= bl[12:8]; s_row <= 19'(ROW0) + 19'(bl[7:0]);
                        w_d <= bd;
                        dec = b_oh;
                        cv <= 1'b1; wcnt <= wcnt + 1'b1; b1p <= 1'b0;
                        if (TWIN != 0) st <= B2; else begin ir <= ir + 1'b1; i_cr <= 1'b1; st <= IDLE; end
                    end else b_ok <= (TWIN != 0) ? ge2[bl[22:18]] : (cred[bl[22:18]] != 0);   // a credit only comes back
                end
                B2: begin   // the twin copy: bank ^ 2 (other bank-group pair), TWIN_ROFF rows away
                    s_m <= b_oh; w_m <= b_oh;
                    s_we <= 1'b1; s_bank <= bl[17:13] ^ 5'd2; s_col <= bl[12:8]; s_row <= 19'(19'(ROW0) + 19'(bl[7:0]) + 19'(TWIN_ROFF));
                    dec = b_oh;
                    ir <= ir + 1'b1; i_cr <= 1'b1; st <= IDLE;
                end
                default: st <= IDLE;
            endcase
            // credits (decrement on issue, increment on return); the registered summaries follow
            for (p = 0; p < NPC; p = p + 1) begin : cr
                reg [CQ-1:0] cn;
                cn = cred[p] - (dec[p] ? 1'b1 : 1'b0) + (s_cr[p] ? 1'b1 : 1'b0);
                cred[p] <= cn;
                if (s_cr[p] && cred[p] == CQ'(SQD)) begin fa <= 1'b1; fca[4] <= 1'b1; end
                ge2[p] <= cn >= 2;
            end
            begin : sm
                reg a1, af; reg [CQ-1:0] cn2;
                a1 = 1'b1; af = 1'b1;
                for (p = 0; p < NPC; p = p + 1) begin
                    cn2 = cred[p] - (dec[p] ? 1'b1 : 1'b0) + (s_cr[p] ? 1'b1 : 1'b0);
                    a1 = a1 && cn2 != 0; af = af && cn2 == CQ'(SQD);
                end
                all1 <= a1; allf <= af;
            end
            if (stat_send) stat_v <= 1'b0;
        end
    // ---- return FIFOs ({ue, ce, data} a beat) -------------------------------------------------------------------
    // chain version: the beats of the next WIN = 4 words, asked for with POP words (tag = word number mod 4) ahead of
    // the packer; xw / xp count the words asked for / packed, (xt, xm, xs, xb) walk the token queue ahead of (tr, pm, pscale)
    reg [3:0]   ga_v, gb_v;
    reg [257:0] ga [0:3];
    reg [257:0] gb [0:3];
    reg [2:0]   xw, xp, xt;
    reg [3:0]   xm;
    reg         xs, xb;
    wire        i_ok = (xt != tw) && (3'(xw - xp) < 3'd4);
    // ---- packer ------------------------------------------------------------------------------------------------------
    reg [3:0] pm; reg pscale;                    // the next word of the head token / its scale phase
    wire t_ne = tw != tr;
    wire [17:0] ht = tq_t[tr[1:0]];
    wire [4:0] hspc = tq_spc[tr[1:0]];
    wire [4:0] pa = {pm, 1'b0}, pb = {pm, 1'b1};
    wire pop_code = t_ne && !pscale && ga_v[xp[1:0]] && gb_v[xp[1:0]] && room;
    wire pop_scale = t_ne && pscale && ga_v[xp[1:0]] && room;
    function automatic [4:0] onehot_pc(input [NPC-1:0] m);
        integer k;
        begin onehot_pc = 5'd0; for (k = 0; k < NPC; k = k + 1) if (m[k]) onehot_pc = onehot_pc | 5'(k); end
    endfunction
    // stage 1: the popped beats + header; stage 2 (v2): the link word into the transmit FIFO
    reg k1; reg [515:0] r1; reg [17:0] t1; reg [3:0] q1, m1;
    reg [522:0] txq [0:TXQ-1];
    reg [3:0] txw, txr;
    reg [3:0] ocr;
    wire tx_ne = txw != txr;
    wire tx_send = tx_ne && ocr != 0;
    integer q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            ga_v <= 4'd0; gb_v <= 4'd0; xw <= 3'd0; xp <= 3'd0; xt <= 3'd0; xm <= 4'd0; xs <= 1'b0; xb <= 1'b0; dn[8:0] <= 9'd0; dn[297:296] <= 2'd0;
            tr <= 0; pm <= 0; pscale <= 1'b0; v1 <= 1'b0; v2 <= 1'b0; txw <= 0; txr <= 0; ocr <= 4'(OCR); o_v <= 1'b0;
            tx_res <= 0; ce_cnt <= 0; ue_info <= 0; fb <= 1'b0; fcb <= 0;
        end else begin : pk
            reg [511:0] dd; reg ue_n; reg [1:0] ce_n;
            // down chain: a static command of the FSM first, else the POP the packer still owes
            dn[0] <= 1'b0; dn[297:296] <= xw[1:0];
            if (|s_m) begin
                dn[8:0] <= {1'b0, onehot_pc(s_m), &s_m, 1'b0, 1'b1};
            end else if (i_ok && !xb) begin                    // POP a (or the scale beat) of word xw
                dn[8:0] <= {1'b0, xs ? tq_spc[xt[1:0]] : {xm, 1'b0}, 1'b0, 1'b1, 1'b1};
                if (xs) begin xs <= 1'b0; xt <= xt + 3'd1; xw <= xw + 3'd1; end
                else xb <= 1'b1;
            end else if (xb) begin                             // POP b of word xw
                dn[8:0] <= {1'b1, {xm, 1'b1}, 1'b0, 1'b1, 1'b1};
                xb <= 1'b0; xw <= xw + 3'd1; xm <= xm + 4'd1;
                if (xm == 4'd15) begin if (tq_sh[xt[1:0]]) xs <= 1'b1; else xt <= xt + 3'd1; end
            end
            if (pop_code || pop_scale) begin ga_v[xp[1:0]] <= 1'b0; gb_v[xp[1:0]] <= 1'b0; xp <= xp + 3'd1; end
            if (up[0]) begin
                if (up[1] ? gb_v[up[3:2]] : ga_v[up[3:2]]) begin fb <= 1'b1; fcb[2] <= 1'b1; end
                if (up[1]) gb_v[up[3:2]] <= 1'b1; else ga_v[up[3:2]] <= 1'b1;
            end
            // stage 1: pop
            v1 <= pop_code || pop_scale;
            if (pop_code) begin
                k1 <= 1'b0; m1 <= pm; t1 <= ht; q1 <= tq_seq[tr[1:0]];
                pm <= pm + 1'b1;
                if (pm == 4'd15) begin if (tq_sh[tr[1:0]]) pscale <= 1'b1; else tr <= tr + 1'b1; end
            end else if (pop_scale) begin
                k1 <= 1'b1; m1 <= 4'd0; t1 <= ht; q1 <= tq_seq[tr[1:0]];
                pscale <= 1'b0; tr <= tr + 1'b1;
            end
            // stage 2: the link word
            v2 <= 1'b0;
            if (v1) begin
                // r1 = {ue_b, ce_b, data_b, ue_a, ce_a, data_a} (b = sector 2m + 1; a scale word has only a)
                ue_n = r1[257] | (!k1 && r1[515]);
                ce_n = {1'b0, r1[256]} + ((!k1 && r1[514]) ? 2'd1 : 2'd0);
                dd = k1 ? {496'd0, r1[16 * ((MUT == 2) ? (t1[3:0] + 4'd1) : t1[3:0]) +: 16]} : {r1[513:258], r1[255:0]};
                txq[txw[1:0]] <= {1'b1, k1 ? K_SCALE : K_CODE, ue_n, 3'd0, q1, dd};
                txw <= txw + 1'b1;
                ce_cnt <= ce_cnt + ce_n;
                if (ue_n) begin
                    fb <= 1'b1; fcb[5] <= 1'b1;
                    if (!ue_info[31]) ue_info <= {1'b1, t1, m1, k1, 8'd0};
                end
            end else if (stat_send) begin
                txq[txw[1:0]] <= {1'b1, K_STATUS, 1'b0, 3'd0, 4'd0, 416'd0, ce_cnt, csum, wcnt};
                txw <= txw + 1'b1;
            end
            // transmit: one word a cycle against the endpoint's credits
            o_v <= tx_send;
            if (tx_send) begin o_d <= txq[txr[1:0]]; txr <= txr + 1'b1; end
            ocr <= ocr - (tx_send ? 1'b1 : 1'b0) + (o_cr ? 1'b1 : 1'b0);
            if (o_cr && ocr == 4'(OCR)) begin fb <= 1'b1; fcb[6] <= 1'b1; end
            tx_res <= tx_res + ((pop_code || pop_scale || stat_send) ? 1'b1 : 1'b0) - (tx_send ? 1'b1 : 1'b0);
        end
    always @(posedge clk) begin
        dn[295:9] <= {w_d, s_row, s_col, s_bank, |w_m, s_we};
        if (up[0]) begin if (up[1]) gb[up[3:2]] <= up[261:4]; else ga[up[3:2]] <= up[261:4]; end
        if (pop_code) r1 <= {gb[xp[1:0]], ga[xp[1:0]]};
        else if (pop_scale) r1 <= {258'd0, ga[xp[1:0]]};
    end
endmodule
