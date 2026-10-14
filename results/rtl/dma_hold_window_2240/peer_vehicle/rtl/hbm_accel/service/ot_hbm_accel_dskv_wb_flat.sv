`timescale 1ps/1fs
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
// r1 (2026-10-04, 1.2 GHz closure; cycle-identical to r0 sha256 baeca01c...): the key shadow is one 4352-bit word
// per slot (8 keys x 544 bits; key n of the block is bits 544n, so the merge is a chunk write) instead of a
// byte array (Yosys 0.68 asserts on r0's two-dimensional array); the emitting key block is copied into `dat` at
// S_MAP, so every emitted sector is dat[256 * idx] with idx a registered counter (t, or the key's sector
// within its block); the sector address S = s0 + t is a registered counter.
module ot_hbm_accel_dskv_wb_flat #(
  parameter integer ENABLE = 0,
  parameter integer STACK = 0,
  parameter integer WIN_ROW0 = 2000, parameter integer CKV_ROW0 = 3000, parameter integer KEY_ROW0 = 4000,
  parameter integer SLOT_ROWS = 2
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
  generate if (!ENABLE) begin : off
    assign row_r = 0; assign wq_v = 0; assign wq_pc = 0; assign wq_bank = 0; assign wq_row = 0; assign wq_col = 0;
    assign wq_data = 0; assign issued = 0; assign acked = 0; assign fence_ok = 0;
  end else begin : on
    localparam [1:0] S_IDLE = 0, S_MAP = 1, S_EMIT = 2;
    reg [1:0] st;
    reg [1:0] kind; reg [5:0] slot; reg r2; reg [4351:0] dat;
    // r1: the key block's slot as a registered one-hot, duplicated per 256-bit sector of dat (17 copies, kept
    // apart) so the 8:1 shadow -> dat copy at S_MAP is an AND-OR with a local select, not one high-fanout net
    (* keep *) reg [7:0] ssel [0:16];
    reg [4351:0] shsel;
    always @* begin
      shsel = 0;
      for (integer c = 0; c < 17; c = c + 1)
        for (integer z = 0; z < 8; z = z + 1)
          shsel[256*c +: 256] = shsel[256*c +: 256] | ({256{ssel[c][z]}} & shadow[4352*z + 256*c +: 256]);
    end
    // Packed per-row shadow: row z remains exactly bits [4352*z +: 4352].
    // This removes the Yosys unpacked-memory width failure, without new state.
    reg [8*4352-1:0] shadow;
    reg [19:0] n; reg [16:0] b; reg [13:0] k; reg own;
    reg [20:0] s0;            // first die-local sector (window: PC index with j = t)
    reg [4:0] ns, t;          // sectors in this row, current
    reg [16:0] kb_s;          // key: first sector of k's block (17 (k >> 3))
    reg [20:0] sr;            // r1: s0 + t (registered)
    reg [4:0]  idx;           // r1: sector of dat to emit (t; for a key, the sector within its block)
    reg [15:0] iss, ack;
    // ---- address map of sector t (combinational from registered state) ----
    wire [20:0] S = (kind == 2'd0) ? 21'(pos[6:0]) : sr;
    wire [6:0]  pcg = S[6:0];
    wire [13:0] jj = (kind == 2'd0) ? 14'(t) : 14'(S >> 7);
    wire [18:0] rbase = (kind == 2'd0) ? 19'(WIN_ROW0) : (kind == 2'd1) ? 19'(CKV_ROW0) : 19'(KEY_ROW0);
    wire [18:0] wrow_a = rbase + 19'(slot) * 19'(SLOT_ROWS) + 19'(jj >> 10);
    wire [255:0] sdat = dat[256 * idx +: 256];
    wire on_stack = (pcg[6:5] == 2'(STACK));
    wire emit = (st == S_EMIT) && on_stack;
    assign wq_v = emit; assign wq_pc = pcg[4:0]; assign wq_bank = {jj[9:7], jj[1:0]}; assign wq_row = wrow_a;
    assign wq_col = jj[6:2]; assign wq_data = sdat;
    assign row_r = (st == S_IDLE) && !sh_v;
    assign issued = iss; assign acked = ack;
    assign fence_ok = (st == S_IDLE) && !row_v && iss == ack;
    // b / 96 = (b >> 5) / 3
    wire [19:0] n_in = row_r2 ? {1'b0, pos[19:1]} : pos;
    wire [16:0] b_in = n_in[19:3];
    wire [11:0] x_in = b_in[16:5];
    wire [10:0] q_in = 11'((25'(x_in) * 25'd2731) >> 13);
    wire [16:0] own_in = b_in - 17'(q_in) * 17'd96;
    wire [13:0] k_in = {q_in, n_in[2:0]};
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        for (integer c = 0; c < 17; c = c + 1) ssel[c] <= 8'b1;
        st <= S_IDLE; kind <= 0; slot <= 0; r2 <= 0; dat <= 0; n <= 0; b <= 0; k <= 0; own <= 0; s0 <= 0;
        ns <= 0; t <= 0; kb_s <= 0; iss <= 0; ack <= 0; sr <= 0; idx <= 0;
      end else begin
        ack <= ack + 16'(ack_n);
        if (wq_v && wq_r) iss <= iss + 1'b1;
        case (st)
          S_IDLE: begin
            if (sh_v) shadow[4352*sh_slot +: 4352] <= sh_data;
            else if (row_v) begin
              kind <= row_kind; slot <= row_slot; r2 <= row_r2; dat <= row_data;
              for (integer c = 0; c < 17; c = c + 1) ssel[c] <= 8'b1 << row_slot[2:0];
              n <= n_in; b <= b_in; k <= k_in; own <= (own_in[6:0] == die);
              if (row_kind == 2'd2)          // merge the new key into the open block's shadow (chunk n_in[2:0])
                for (integer c = 0; c < 8; c = c + 1)
                  if (n_in[2:0] == 3'(c)) shadow[4352*row_slot[2:0] + 544*c +: 544] <= row_data[543:0];
              st <= S_MAP;
            end
          end
          S_MAP: begin
            t <= 0;
            kb_s <= 17'(k >> 3) * 17'd17;
            if (kind == 2'd2) dat <= shsel;              // = shadow[slot[2:0]]
            // idx: t (window, compressed row); for a key the sector within its block, (68 k >> 5) - 17 (k >> 3)
            idx <= (kind == 2'd2) ? 5'(((21'(k) * 21'd68) >> 5) - 21'(17'(k >> 3) * 17'd17)) : 5'd0;
            case (kind)
              2'd0: begin s0 <= 0; sr <= 0; ns <= 5'd17; st <= S_EMIT; end
              2'd1: begin s0 <= 21'(k) * 21'd9; sr <= 21'(k) * 21'd9; ns <= 5'd9; st <= own ? S_EMIT : S_IDLE; end
              default: begin
                s0 <= (21'(k) * 21'd68) >> 5; sr <= (21'(k) * 21'd68) >> 5;
                ns <= 5'((((21'(k) * 21'd68) + 21'd67) >> 5) - ((21'(k) * 21'd68) >> 5) + 21'd1);
                st <= own ? S_EMIT : S_IDLE;
              end
            endcase
          end
          default: begin                       // S_EMIT: one sector a cycle (off-stack sectors skip)
            if (!on_stack || wq_r) begin
              if (t == ns - 5'd1) st <= S_IDLE;
              t <= t + 1'b1; sr <= sr + 1'b1; idx <= idx + 1'b1;
            end
          end
        endcase
      end
  end endgenerate
endmodule
