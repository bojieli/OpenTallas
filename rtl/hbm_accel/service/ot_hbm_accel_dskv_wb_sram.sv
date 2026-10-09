`timescale 1ps/1fs
// UNQUALIFIED OPT-IN SRAM successor: sh_v must handshake sh_r; key preload required.
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
//     shadow and writes the whole sectors covering the new key (3 sectors for each 68-byte key), the bytes of the block's earlier
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
module ot_hbm_accel_dskv_wb_sram #(
  parameter integer ENABLE = 0,
  parameter integer MUT_MERGE = 0, // bench-only negative control; production always0
  parameter integer STACK = 0,
  parameter integer KEY_CONTIGUOUS = 0,      // opt-in indexer quarter placement: 342 whole blocks/stack
  parameter integer ALL_STACKS = 0,           // 1 (hfd hub write-back unit, 2026-10-08): emit every stack's sectors, wq_stk says which
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
  output wire sh_r, output wire fault,
  output wire          wq_v, output wire [4:0] wq_pc, output wire [4:0] wq_bank, output wire [18:0] wq_row,
  output wire [4:0]    wq_col, output wire [255:0] wq_data, input wire wq_r,
  output wire [1:0]    wq_stk,
  input  wire [5:0]    ack_n,
  output wire [15:0]   issued, output wire [15:0] acked, output wire fence_ok
);
  generate if (!ENABLE) begin : off
    assign row_r = 0; assign wq_v = 0; assign wq_stk = 0; assign wq_pc = 0; assign wq_bank = 0; assign wq_row = 0; assign wq_col = 0;
    assign sh_r=0; assign fault=0;
    assign wq_data = 0; assign issued = 0; assign acked = 0; assign fence_ok = 0;
  end else begin : on
    localparam [3:0] S_IDLE=0,S_MAP=1,S_EMIT=2,S_PRE_REQ=3,S_PRE_RSP=4,
      S_KEY_REQ=5,S_KEY_RSP=6,S_KEY_WRITE=7,S_KEY_WACK=8,S_KEY_EMIT=9;
    reg [3:0] st, st_n; reg ctl_fault;
    wire state_bad=(st != ~st_n) || (st>S_KEY_EMIT);
    reg [1:0] kind; reg [5:0] slot; reg r2; reg [4351:0] dat;
    reg [2:0] preload_slot;
    reg [4:0] preload_sector;
    reg [255:0] merged;
    wire mem_req_r,mem_rsp_v,mem_rsp_poison,mem_fault;
    wire [255:0] mem_rsp_data;
    wire preload = st==S_PRE_REQ || st==S_PRE_RSP;
    wire mem_write = st==S_PRE_REQ || st==S_KEY_WRITE;
    wire mem_req_v=(st==S_PRE_REQ || st==S_KEY_REQ || st==S_KEY_WRITE)&&!state_bad&&!ctl_fault;
    wire mem_rsp_r=st==S_PRE_RSP || st==S_KEY_RSP || st==S_KEY_WACK;
    ot_hbm_accel_dskv_shadow_sram #(.ENABLE(1)) shadow_store(
      .clk(clk),.rst_n(rst_n),.req_v(mem_req_v),.req_r(mem_req_r),.req_write(mem_write),
      .req_slot(preload?preload_slot:slot[2:0]),.req_sector(preload?preload_sector:ksec),
      .req_data(preload?dat[256*preload_sector+:256]:merged),
      .rsp_v(mem_rsp_v),.rsp_r(mem_rsp_r),.rsp_data(mem_rsp_data),.rsp_poison(mem_rsp_poison),.fault(mem_fault));
    assign sh_r=(st==S_IDLE)&&!mem_fault&&!ctl_fault&&!state_bad;
    assign fault=mem_fault||ctl_fault||state_bad;
    reg [255:0] merge_calc;
    always @* begin
      merge_calc=mem_rsp_data;
      for(integer y=0;y<32;y=y+1)
        if((32*int'(ksec)+y >= 68*int'(n[2:0])) &&
           (32*int'(ksec)+y < 68*int'(n[2:0])+68))
          merge_calc[8*y+:8]=dat[8*((32*int'(ksec)+y-68*int'(n[2:0])+MUT_MERGE)%68)+:8];
    end
    reg [19:0] position; reg [19:0] n; reg [16:0] b; reg [13:0] k; reg own;
    reg [20:0] s0;            // first die-local sector (window: PC index with j = t)
    reg [4:0] ns, t;          // sectors in this row, current
    reg [16:0] kb_s;          // key: first sector of k's block (17 (k >> 3))
    reg [15:0] iss, ack;
    // ---- address map of sector t (combinational from registered state) ----
    wire [20:0] S = (kind == 2'd0) ? 21'(position[6:0]) : s0 + 21'(t);
    // Preserve the shadow's die-global S/ksec; remap only the physical destination.
    wire contig_key = (KEY_CONTIGUOUS != 0) && (kind == 2'd2);
    wire [1:0] key_stack = (k[13:3] >= 11'd1026) ? 2'd3 :
                            (k[13:3] >= 11'd684) ? 2'd2 :
                            (k[13:3] >= 11'd342) ? 2'd1 : 2'd0;
    wire [20:0] key_sector = S - 21'(key_stack) * 21'd5814;
    wire [6:0] pcg = contig_key ? {key_stack, key_sector[4:0]} : S[6:0];
    wire [13:0] jj = (kind == 2'd0) ? 14'(t) : contig_key ? 14'(key_sector >> 5) : 14'(S >> 7);
    wire [18:0] rbase = (kind == 2'd0) ? 19'(WIN_ROW0) : (kind == 2'd1) ? 19'(CKV_ROW0) : 19'(KEY_ROW0);
    wire [18:0] wrow_a = rbase + 19'(slot) * 19'(SLOT_ROWS) + 19'(jj >> 10);
    wire [4:0]  ksec = 5'(S - 21'(kb_s));           // key: sector within the block (0..16)
    reg [255:0] sdat;
    always @* begin
      sdat = 0;
      if (kind == 2'd2) begin
        sdat = merged;
      end else sdat = dat[256 * t +: 256];
    end
    wire on_stack = ALL_STACKS ? 1'b1 : (pcg[6:5] == 2'(STACK));
    assign wq_stk = pcg[6:5];
    wire emit = ((st==S_EMIT)||(st==S_KEY_EMIT)) && on_stack && !mem_fault&&!ctl_fault&&!state_bad;
    assign wq_v = emit; assign wq_pc = pcg[4:0]; assign wq_bank = {jj[9:7], jj[1:0]}; assign wq_row = wrow_a;
    assign wq_col = jj[6:2]; assign wq_data = sdat;
    assign row_r = (st == S_IDLE) && !sh_v && !mem_fault&&!ctl_fault&&!state_bad;
    assign issued = iss; assign acked = ack;
    assign fence_ok = (st == S_IDLE) && !row_v && !sh_v && iss == ack && !mem_fault&&!ctl_fault&&!state_bad;
    // b / 96 = (b >> 5) / 3
    wire [19:0] n_in = row_r2 ? {1'b0, pos[19:1]} : pos;
    wire [16:0] b_in = n_in[19:3];
    wire [11:0] x_in = b_in[16:5];
    wire [10:0] q_in = 11'((25'(x_in) * 25'd2731) >> 13);
    wire [16:0] own_in = b_in - 17'(q_in) * 17'd96;
    wire [13:0] k_in = {q_in, n_in[2:0]};
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        st <= S_IDLE; st_n<=~S_IDLE; kind <= 0; slot <= 0; r2 <= 0; dat <= 0; position<=0; n <= 0; b <= 0; k <= 0; own <= 0; s0 <= 0;
        ns <= 0; t <= 0; kb_s <= 0; iss <= 0; ack <= 0; ctl_fault<=0; preload_slot<=0; preload_sector<=0; merged<=0;
      end else begin
        if(state_bad)ctl_fault<=1;
        ack <= ack + 16'(ack_n);
        if (wq_v && wq_r) iss <= iss + 1'b1;
        case (st)
          S_IDLE: begin
            if (sh_v && sh_r) begin dat<=sh_data; preload_slot<=sh_slot; preload_sector<=0; st<=S_PRE_REQ; st_n<=~S_PRE_REQ; end
            else if (row_v && row_r) begin
              kind <= row_kind; slot <= row_slot; r2 <= row_r2; dat <= row_data;
              position<=pos; n <= n_in; b <= b_in; k <= k_in; own <= (own_in[6:0] == die);
              st <= S_MAP; st_n<=~S_MAP;
            end
          end
          S_MAP: begin
            t <= 0;
            kb_s <= 17'(k >> 3) * 17'd17;
            case (kind)
              2'd0: begin s0 <= 0; ns <= 5'd17; st <= S_EMIT; st_n<=~S_EMIT; end
              2'd1: begin s0 <= 21'(k) * 21'd9; ns <= 5'd9; st<=own?S_EMIT:S_IDLE; st_n<=~(own?S_EMIT:S_IDLE); end
              default: begin
                s0 <= (21'(k) * 21'd68) >> 5;
                ns <= 5'((((21'(k) * 21'd68) + 21'd67) >> 5) - ((21'(k) * 21'd68) >> 5) + 21'd1);
                st<=own?S_KEY_REQ:S_IDLE; st_n<=~(own?S_KEY_REQ:S_IDLE);
              end
            endcase
          end
          S_PRE_REQ:if(mem_req_r)begin st<=S_PRE_RSP; st_n<=~S_PRE_RSP; end
          S_PRE_RSP:if(mem_rsp_v)begin
            if(preload_sector==16)begin st<=S_IDLE; st_n<=~S_IDLE; end
            else begin preload_sector<=preload_sector+1;st<=S_PRE_REQ; st_n<=~S_PRE_REQ;end
          end
          S_KEY_REQ:if(mem_req_r)begin st<=S_KEY_RSP; st_n<=~S_KEY_RSP; end
          S_KEY_RSP:if(mem_rsp_v)begin merged<=merge_calc;st<=S_KEY_WRITE; st_n<=~S_KEY_WRITE;end
          S_KEY_WRITE:if(mem_req_r)begin st<=S_KEY_WACK; st_n<=~S_KEY_WACK; end
          S_KEY_WACK:if(mem_rsp_v)begin st<=S_KEY_EMIT; st_n<=~S_KEY_EMIT; end
          S_KEY_EMIT:if(!on_stack||wq_r)begin
            if(t==ns-1)begin st<=S_IDLE; st_n<=~S_IDLE; end else begin st<=S_KEY_REQ; st_n<=~S_KEY_REQ; end
            t<=t+1;
          end
          S_EMIT: begin                       // S_EMIT: one sector a cycle (off-stack sectors skip)
            if (!on_stack || wq_r) begin
              if (t == ns - 5'd1) begin st <= S_IDLE; st_n<=~S_IDLE; end
              t <= t + 1'b1;
            end
          end
          default: begin ctl_fault<=1; st<=S_IDLE; st_n<=~S_IDLE; end
        endcase
      end
  end endgenerate
endmodule
