`timescale 1ps/1fs
// ot_hbm_accel_dskv_wb_spec: MTP-exact successor of ot_hbm_accel_dskv_wb (stream mtp-rollback, 2026-10-08).
// Identical except the WINDOW ring: ring slot w = pos mod WIN_SLOTS (as built: pos mod 128).  Under DSpark MTP a
// verify pass writes positions n .. n+g (g <= 5) before the commit, and a rejected position's window row at slot
// pos mod 128 overwrites committed row pos-128, which the next query (q+2+a) still reads whenever g >= a+2 (the
// coverage-T3 finding: ot_dshbm_spec_state sizes its window ring WR = 136 but this unit and the read stream used
// pos mod 128).  Exact rollback needs a ring of >= W + PMAX slots; WIN_SLOTS = 256 keeps the slot a power of two,
// so the writer, the read stream (ot_hbm_accel_dswin_rd) and the spec-state address generator (WR = 256) compute
// the same slot with no divider.  Slot w lives on die-local PC w[6:0] (every 128 consecutive positions still hit
// 128 distinct PCs: the read spread is unchanged) at PC-local window sectors 17*w[7] .. 17*w[7]+16.  HBM cost:
// 2x the window region (+128 x 544 B a layer a user; 40 layers + 3 DSpark stages = +2.99 MB a user a die).
// The DSpark stage window rows (golden state["dsk"]) are window rows of layer slots NL .. NL+2 (row_slot 40..42).
// WIN_SLOTS = 128 reproduces the as-built unit (the bench mutant).
// MR-6 (APPROVED 2026-10-09): the index-key open-block SHADOW loads only at bring-up / ingest.  SH_LOCK = 1 (default)
// ignores sh_v once the first key row has been accepted since reset (decode has begun): a reload at a block opening
// under MTP would let a REJECTED key opening block b+1 replace the shadow, and the next committed key of block b
// would rewrite its neighbours' bytes from it.  Ingest (dsfd_host / prefill) loads the shadow before the first key
// write, then a reset or the next user's bring-up re-arms it.  SH_LOCK = 0 = the as-built policy (bench mutant).
// DS-V4.1 HBM accelerator: per-token KV + index-key WRITE-BACK of one HBM3E stack, 1M-addressable (2026-10-04).
// ENABLE = 0 (default) ties every output to zero; nothing pinned instantiates it.
//
// What a die writes per token at position `pos` (20 bits, 0 .. 1,048,575), W19 TP-96 layout
// (tools/w19_hbm_tp96_isa.py: window rows replicated on every die; compressed rows and index keys SHARDED BY
// SEQUENCE POSITION, group n on die (n / 8) mod 96, blocks of KEY_BLOCK 8):
//   kind 0 WINDOW row of layer `slot` (0..39), every die: 528 B (512 FP8 E4M3 + 16 UE8M0) padded to 17 sectors
//     (544 B).  Ring slot w = pos mod 128 lives whole on die-local PC w (stack w[6:5], PC w[4:0]), PC-local
//     sectors 0..16 of the layer's window row: the HBM-resident window of a layer is 128 rows x 17 sectors,
//     one row a PC (the audit's 17 sectors a PC a layer).
//   kind 1 COMPRESSED-KV row of index-source slot `slot` (0..7), owner die only: 288 B (256 B E2M1 + 32 E4M3) =
//     9 sectors.  Group n = r2 ? pos >> 1 : pos (ratio 2 / ratio 1), block b = n >> 3, owner b mod 96,
//     die-local row k = (b / 96) * 8 + n[2:0]; die-local sectors 9k .. 9k+8, sector S on PC S[6:0], PC-local
//     sector S >> 7 (the gather layout: one row over 9 PCs).
//   kind 2 INDEX KEY of slot `slot`, owner die only: 68 B (64 B E2M1 + 4 UE8M0) packed back to back: key k at
//     die-local bytes 68k .. 68k+67; a KEY_BLOCK of 8 keys is 544 B = 17 whole sectors, so the block is sector
//     aligned.  HBM3 has no write data mask, so the unit keeps the owner's OPEN key block (<= 544 B a slot) in a
//     shadow and writes the whole sectors covering the new key (2-3 sectors), the bytes of the block's earlier
//     keys taken from the shadow.  The shadow is loaded (sh_v) when a block opens or at bring-up from HBM.
// PC-local sector j -> stream-PC address: bank {j[9:7], j[1:0]}, column j[6:2], row ROW0(kind) + slot *
// SLOT_ROWS + (j >> 10); the read stream (ot_hbm_accel_expert_stream_pc / ot_hbm_r14_stream_pc) reads the same
// j order, so a written row is read back by the next token's stream at the same addresses.
// Only sectors on this instance's STACK are emitted; four instances (or one with the stack field) make a die.
//
// Posted writes leave on wq_* (one sector a cycle, to the stack's PCs through the write-request network);
// `issued` counts handshaken sectors, `acked` counts posted-write ACKs returned (ack_n a cycle).  fence_ok =
// nothing pending and every issued write ACKed: the visibility fence the next token's reads of a written region
// wait for.  b / 96 = ((b >> 5) * 2731) >> 13 (exact for b >> 5 < 4096, i.e. any 20-bit position).
module ot_hbm_accel_dskv_wb_spec #(
  parameter integer ENABLE = 0,
  parameter integer WIN_SLOTS = 256,             // power of two, <= 256 (as built: 128)
  parameter integer SH_LOCK = 1,                 // MR-6: shadow loads only before the first key write
  parameter integer STACK = 0,
  parameter integer WIN_ROW0 = 2000, parameter integer CKV_ROW0 = 3000, parameter integer KEY_ROW0 = 4000,
  parameter integer SLOT_ROWS = 2,
  parameter integer PIPE = 0                      // mtp-lead 2026-10-09: 1 = the ownership divide (pos -> q = b/96 -> own, k)
                                                 // in its own state S_OWN after the row capture (+1 cycle a row); 0 = as built
)(
  input  wire          clk, rst_n,
  input  wire [6:0]    die,
  input  wire [19:0]   pos,
  input  wire          row_v, input wire [1:0] row_kind, input wire [5:0] row_slot, input wire row_r2,
  input  wire [4351:0] row_data,                  // 544 B, byte i = row_data[8i +: 8]
  output wire          row_r,
  input  wire          sh_v, input wire [2:0] sh_slot, input wire [4351:0] sh_data,
  output wire          wq_v, output wire [4:0] wq_pc, output wire [4:0] wq_bank, output wire [18:0] wq_row,
  output wire [4:0]    wq_col, output wire [255:0] wq_data, input wire wq_r,
  input  wire [5:0]    ack_n,
  output wire [15:0]   issued, output wire [15:0] acked, output wire fence_ok
);
`ifndef SYNTHESIS
  initial if (WIN_SLOTS < 1 || WIN_SLOTS > 256 || (WIN_SLOTS & (WIN_SLOTS - 1)) != 0)
    $fatal(1, "ot_hbm_accel_dskv_wb_spec: WIN_SLOTS must be a power of two <= 256");
`endif
  generate if (!ENABLE) begin : off
    assign row_r = 0; assign wq_v = 0; assign wq_pc = 0; assign wq_bank = 0; assign wq_row = 0; assign wq_col = 0;
    assign wq_data = 0; assign issued = 0; assign acked = 0; assign fence_ok = 0;
  end else begin : on
    localparam [1:0] S_IDLE = 0, S_MAP = 1, S_EMIT = 2, S_OWN = 3;
    reg [1:0] st;
    reg [1:0] kind; reg [5:0] slot; reg r2; reg [4351:0] dat;
    // mtp-lead 2026-10-09: the key shadow as 8 slot rows of 544 B (4,352 b), written and read with CONSTANT part
    // selects (a 544-bit key field write chosen by a case on n, a 17-way sector read).  Bit-identical to the original
    // byte array shadow[slot][byte] (byte y of a row = bits [8y +: 8]); the byte loops with computed indices
    // (68 n + y, 32 ksec + y) made yosys 0.68 run > 4 h / fail (mtprb-dskvwb_spec-a/b).  No cycle change.
    reg [4351:0] shadow [0:7];
    reg [19:0] n; reg [16:0] b; reg [13:0] k; reg own;
    reg [20:0] s0;            // first die-local sector (window: PC index with j = t)
    reg [4:0] ns, t;          // sectors in this row, current
    reg [16:0] kb_s;          // key: first sector of k's block (17 (k >> 3))
    reg [15:0] iss, ack;
    reg sh_locked;
    wire sh_go = sh_v && !(SH_LOCK != 0 && sh_locked);
    // ---- address map of sector t (combinational from registered state) ----
    reg  [19:0] pos_q;          // PIPE: the row's position held for its emit (a pin FIFO moves on after the pop)
    wire [19:0] pos_w = (PIPE != 0) ? pos_q : pos;
    wire [7:0]  wslot = 8'(pos_w & 20'(WIN_SLOTS - 1));
    wire [20:0] S = (kind == 2'd0) ? 21'(wslot[6:0]) : s0 + 21'(t);
    wire [6:0]  pcg = S[6:0];
    wire [13:0] jj = (kind == 2'd0) ? 14'(t) + 14'(wslot[7] ? 17 : 0) : 14'(S >> 7);
    wire [18:0] rbase = (kind == 2'd0) ? 19'(WIN_ROW0) : (kind == 2'd1) ? 19'(CKV_ROW0) : 19'(KEY_ROW0);
    wire [18:0] wrow_a = rbase + 19'(slot) * 19'(SLOT_ROWS) + 19'(jj >> 10);
    wire [4:0]  ksec = 5'(S - 21'(kb_s));           // key: sector within the block (0..16)
    wire [4351:0] sh_row = shadow[slot[2:0]];
    reg [255:0] sh_sec, dat_sec;
    always @* begin
      case (ksec)
        5'd0: sh_sec = sh_row[255:0];
        5'd1: sh_sec = sh_row[511:256];
        5'd2: sh_sec = sh_row[767:512];
        5'd3: sh_sec = sh_row[1023:768];
        5'd4: sh_sec = sh_row[1279:1024];
        5'd5: sh_sec = sh_row[1535:1280];
        5'd6: sh_sec = sh_row[1791:1536];
        5'd7: sh_sec = sh_row[2047:1792];
        5'd8: sh_sec = sh_row[2303:2048];
        5'd9: sh_sec = sh_row[2559:2304];
        5'd10: sh_sec = sh_row[2815:2560];
        5'd11: sh_sec = sh_row[3071:2816];
        5'd12: sh_sec = sh_row[3327:3072];
        5'd13: sh_sec = sh_row[3583:3328];
        5'd14: sh_sec = sh_row[3839:3584];
        5'd15: sh_sec = sh_row[4095:3840];
        5'd16: sh_sec = sh_row[4351:4096];
        default: sh_sec = 256'd0;
      endcase
      case (t)
        5'd0: dat_sec = dat[255:0];
        5'd1: dat_sec = dat[511:256];
        5'd2: dat_sec = dat[767:512];
        5'd3: dat_sec = dat[1023:768];
        5'd4: dat_sec = dat[1279:1024];
        5'd5: dat_sec = dat[1535:1280];
        5'd6: dat_sec = dat[1791:1536];
        5'd7: dat_sec = dat[2047:1792];
        5'd8: dat_sec = dat[2303:2048];
        5'd9: dat_sec = dat[2559:2304];
        5'd10: dat_sec = dat[2815:2560];
        5'd11: dat_sec = dat[3071:2816];
        5'd12: dat_sec = dat[3327:3072];
        5'd13: dat_sec = dat[3583:3328];
        5'd14: dat_sec = dat[3839:3584];
        5'd15: dat_sec = dat[4095:3840];
        5'd16: dat_sec = dat[4351:4096];
        default: dat_sec = 256'd0;
      endcase
    end
    reg [255:0] sdat;
    always @* begin
      sdat = 0;
      if (kind == 2'd2) sdat = sh_sec;
      else sdat = dat_sec;
    end
    wire on_stack = (pcg[6:5] == 2'(STACK));
    wire emit = (st == S_EMIT) && on_stack;
    assign wq_v = emit; assign wq_pc = pcg[4:0]; assign wq_bank = {jj[9:7], jj[1:0]}; assign wq_row = wrow_a;
    assign wq_col = jj[6:2]; assign wq_data = sdat;
    assign row_r = (st == S_IDLE) && !sh_go;
    assign issued = iss; assign acked = ack;
    assign fence_ok = (st == S_IDLE) && !row_v && iss == ack;
    // b / 96 = (b >> 5) / 3
    wire [19:0] n_in = row_r2 ? {1'b0, pos[19:1]} : pos;
    wire [16:0] b_in = n_in[19:3];
    wire [11:0] x_in = b_in[16:5];
    wire [10:0] q_in = 11'((25'(x_in) * 25'd2731) >> 13);
    wire [16:0] own_in = b_in - 17'(q_in) * 17'd96;
    wire [13:0] k_in = {q_in, n_in[2:0]};
    wire [11:0] x_b = b[16:5];
    wire [10:0] q_b = 11'((25'(x_b) * 25'd2731) >> 13);
    wire [16:0] own_b = b - 17'(q_b) * 17'd96;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        st <= S_IDLE; kind <= 0; slot <= 0; r2 <= 0; dat <= 0; n <= 0; b <= 0; k <= 0; own <= 0; s0 <= 0;
        ns <= 0; t <= 0; kb_s <= 0; pos_q <= 0; iss <= 0; ack <= 0; sh_locked <= 0;
      end else begin
        ack <= ack + 16'(ack_n);
        if (wq_v && wq_r) iss <= iss + 1'b1;
        case (st)
          S_IDLE: begin
            if (sh_go) ;                       // shadow load: see the shadow block below
            else if (row_v) begin
              kind <= row_kind; slot <= row_slot; r2 <= row_r2; dat <= row_data;
              n <= n_in; b <= b_in; pos_q <= pos;
              if (PIPE == 0) begin k <= k_in; own <= (own_in[6:0] == die); end
              if (row_kind == 2'd2) sh_locked <= 1'b1;
              st <= (PIPE != 0) ? S_OWN : S_MAP;
            end
          end
          S_OWN: begin                       // PIPE: the same divide on the registered b / n
            k <= {q_b, n[2:0]}; own <= (own_b[6:0] == die); st <= S_MAP;
          end
          S_MAP: begin
            t <= 0;
            kb_s <= 17'(k >> 3) * 17'd17;
            case (kind)
              2'd0: begin s0 <= 0; ns <= 5'd17; st <= S_EMIT; end
              2'd1: begin s0 <= 21'(k) * 21'd9; ns <= 5'd9; st <= own ? S_EMIT : S_IDLE; end
              default: begin
                s0 <= (21'(k) * 21'd68) >> 5;
                ns <= 5'((((21'(k) * 21'd68) + 21'd67) >> 5) - ((21'(k) * 21'd68) >> 5) + 21'd1);
                st <= own ? S_EMIT : S_IDLE;
              end
            endcase
          end
          default: begin                       // S_EMIT: one sector a cycle (off-stack sectors skip)
            if (!on_stack || wq_r) begin
              if (t == ns - 5'd1) st <= S_IDLE;
              t <= t + 1'b1;
            end
          end
        endcase
      end
    // shadow writes (no reset, as the original array): a bring-up load of a whole slot row, else the new key's
    // 68 B merged at byte 68 n of the open block's row (only in S_IDLE, as in the original)
    always @(posedge clk)
      if (rst_n && st == S_IDLE) begin
        if (sh_go) shadow[sh_slot] <= sh_data;
        else if (row_v && row_kind == 2'd2)
          case (n_in[2:0])
            3'd0: shadow[row_slot[2:0]][543:0] <= row_data[543:0];
            3'd1: shadow[row_slot[2:0]][1087:544] <= row_data[543:0];
            3'd2: shadow[row_slot[2:0]][1631:1088] <= row_data[543:0];
            3'd3: shadow[row_slot[2:0]][2175:1632] <= row_data[543:0];
            3'd4: shadow[row_slot[2:0]][2719:2176] <= row_data[543:0];
            3'd5: shadow[row_slot[2:0]][3263:2720] <= row_data[543:0];
            3'd6: shadow[row_slot[2:0]][3807:3264] <= row_data[543:0];
            3'd7: shadow[row_slot[2:0]][4351:3808] <= row_data[543:0];
          endcase
      end
  end endgenerate
endmodule
