`timescale 1ps/1fs
`default_nettype none
// UNQUALIFIED default-off SRAM successor; original source retained.
// hbm-system 2026-10-08 (T3 gap 3): the die's KV / compressed-KV / index-key WRITE-BACK unit, hub side.
//
// One per die, in the hub's stream domain (clk, 1.2 GHz).  It closes the gap "the r25 stream service has no write
// command; ot_hbm_accel_dskv_wb (exact 768/768) sits in no die master":
//   producer (KV/quant tail of the SU quarter) --row beats--> [beat FIFO, credit per beat]
//     -> row / shadow assembler -> ot_hbm_accel_dskv_wb (ENABLE 1, ALL_STACKS 1: one unit, every stack's sectors)
//     -> ot_hbm_kport_map (pc, bank, row, col -> K-port sector address) -> per-stack SECTOR LINK to that stack's
//        stream service (ot_hbm_svc_core WB=1), credit-flowed;
//   each service returns two Gray-coded running counts on its own clock: FIFO pops (credits) and posted-write
//   completions (PHY k_wr_done), synchronised here; the completion deltas are dskv_wb's ack_n, so fence_ok is the
//   real "every issued write is in DRAM" fence the next token's window / CKV / key reads wait on.
//
// Row input (ri_*): one 256-bit beat a cycle, valid only (the producer holds <= RI_DEPTH beats of credit; ri_cr
// returns one credit per beat popped).  A HEADER beat (ri_hdr = 1) carries
//   [1:0] kind (0 window row 528 B, 1 compressed-KV row 288 B, 2 index key 68 B), [7:2] slot, [8] r2,
//   [28:9] pos, [29] shadow (an open-key-block image of slot[2:0], 544 B, loaded into dskv_wb's shadow)
// then NB data beats, byte i of the row at bit 8*(i mod 32) of beat i/32: NB = 17 (window, shadow), 9 (CKV), 3 (key).
// Sector link to stack t (so_d[t], 292 b, launched on clk, forwarded with clk): {data256, addr30, pc5, v}.
// Return from stack t (si_g[t], 16 b, launched on the service clock): {ack_gray8, pop_gray8}.
// Every input lands in a flop; every output leaves a flop.  MUT (bench negative control): 1 flips sector bit 0.
module ot_hbm_kvwb_hub_sram #(
  parameter integer ENABLE=0,
  parameter integer WIN_ROW0 = 2000, parameter integer CKV_ROW0 = 3000, parameter integer KEY_ROW0 = 4000,
  parameter integer SLOT_ROWS = 2,
  parameter integer KEY_CONTIGUOUS = 0,
  parameter integer RI_AW = 5,            // row beat FIFO 2^RI_AW (credits held by the producer)
  parameter integer SO_DEPTH = 8,         // the service's sector FIFO depth (credits per stack)
  parameter integer MUT = 0
)(
  input  wire          clk, input wire rst_n,
  input  wire [6:0]    die,
  input  wire          ri_v, input wire ri_hdr, input wire [255:0] ri_d, output reg ri_cr,
  output wire [4*292-1:0] so_d,
  input  wire [4*16-1:0]  si_g,
  output wire          fence_ok, output wire [15:0] issued, output wire [15:0] acked, output reg map_fault
);
  generate if(!ENABLE) begin:off
    assign ri_cr=0;assign so_d=0;assign fence_ok=0;assign issued=0;assign acked=0;assign map_fault=0;
  end else begin:on
  // ---------------------------------------------------------------- row beats: pin flops + FIFO
  reg rv_q, rh_q; reg [255:0] rd_q;
  always @(posedge clk or negedge rst_n) if (!rst_n) begin rv_q <= 1'b0; rh_q <= 1'b0; end else begin rv_q <= ri_v; rh_q <= ri_hdr; end
  always @(posedge clk) rd_q <= ri_d;
  localparam integer RD = 1 << RI_AW;
  reg [256:0] rf [0:RD-1];
  reg [RI_AW:0] rwp, rrp;
  wire rne = (rwp != rrp);
  wire [256:0] rh = rf[rrp[RI_AW-1:0]];
  wire r_pop;
  always @(posedge clk) if (rv_q) rf[rwp[RI_AW-1:0]] <= {rh_q, rd_q};
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin rwp <= 0; rrp <= 0; ri_cr <= 1'b0; end
    else begin rwp <= rwp + (rv_q ? 1'b1 : 1'b0); rrp <= rrp + (r_pop ? 1'b1 : 1'b0); ri_cr <= r_pop; end

  // ---------------------------------------------------------------- assembler
  localparam [2:0] A_HDR=0,A_DAT=1,A_WAIT=2,A_GO=3,A_SH=4;
  reg [2:0] ast;
  reg [1:0] h_kind; reg [5:0] h_slot; reg h_r2, h_sh; reg [19:0] h_pos;
  reg [4:0] nb, bi;
  reg [4351:0] buf_;
  wire row_r,sh_r,wb_fault,wb_fence;
  assign fence_ok=wb_fence&&(ast==A_HDR)&&!rne&&!rv_q&&!ri_v&&!row_v&&!sh_v&&!map_fault;
  reg row_v, sh_v; reg [19:0] cur_pos;
  assign r_pop = rne && ((ast == A_HDR) || (ast == A_DAT));
  wire [4:0] nb_of = (rh[1:0] == 2'd1 && !rh[29]) ? 5'd9 : (rh[1:0] == 2'd2 && !rh[29]) ? 5'd3 : 5'd17;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin ast <= A_HDR; row_v <= 1'b0; sh_v <= 1'b0; nb <= 0; bi <= 0; cur_pos <= 0; end
    else begin
      case (ast)
        A_HDR: if (rne) begin
          if (rh[256]) begin
            h_kind <= rh[1:0]; h_slot <= rh[7:2]; h_r2 <= rh[8]; h_pos <= rh[28:9]; h_sh <= rh[29];
            nb <= nb_of; bi <= 0; ast <= A_DAT;
          end                                                    // a data beat without a header: dropped
        end
        A_DAT: if (rne) begin
          if (bi == nb - 5'd1) ast <= A_WAIT;
          bi <= bi + 5'd1;
        end
        A_WAIT: if (row_r && !row_v) begin                       // dskv_wb idle (and no row presented): go next cycle
          if (h_sh) begin sh_v <= 1'b1; ast <= A_SH; end
          else begin row_v <= 1'b1; cur_pos <= h_pos; ast <= A_GO; end
        end
        A_SH:if(sh_v&&sh_r)begin sh_v<=0;ast<=A_HDR;end
        default: if (row_v && row_r) begin row_v <= 1'b0; ast <= A_HDR; end   // A_GO: accepted
      endcase
    end
  always @(posedge clk)
    if (ast == A_HDR && rne && rh[256]) buf_ <= 4352'd0;
    else if (ast == A_DAT && rne) buf_[256 * bi +: 256] <= rh[255:0];

  // ---------------------------------------------------------------- the write-back unit (all stacks)
  wire wq_v; wire [4:0] wq_pc, wq_bank, wq_col; wire [18:0] wq_row; wire [255:0] wq_data; wire [1:0] wq_stk;
  reg [5:0] ack_n;
  wire wq_r;
  ot_hbm_accel_dskv_wb_sram #(.ENABLE(1), .STACK(0), .ALL_STACKS(1), .WIN_ROW0(WIN_ROW0), .CKV_ROW0(CKV_ROW0),
    .KEY_ROW0(KEY_ROW0), .SLOT_ROWS(SLOT_ROWS), .KEY_CONTIGUOUS(KEY_CONTIGUOUS)) u_wb (
    .clk(clk), .rst_n(rst_n), .die(die), .pos(cur_pos),
    .row_v(row_v), .row_kind(h_kind), .row_slot(h_slot), .row_r2(h_r2), .row_data(buf_), .row_r(row_r),
    .sh_r(sh_r),.fault(wb_fault),.sh_v(sh_v), .sh_slot(h_slot[2:0]), .sh_data(buf_),
    .wq_v(wq_v), .wq_pc(wq_pc), .wq_bank(wq_bank), .wq_row(wq_row), .wq_col(wq_col), .wq_data(wq_data), .wq_r(wq_r),
    .wq_stk(wq_stk), .ack_n(ack_n), .issued(issued), .acked(acked), .fence_ok(wb_fence));
  wire [29:0] s_addr; wire s_fault;
  ot_hbm_kport_map u_map (.pc(wq_pc), .bank(wq_bank), .row(wq_row), .col(wq_col), .s(s_addr), .fault(s_fault));

  // ---------------------------------------------------------------- per-stack links: credits, launch, return sync
  function automatic [7:0] g2b(input [7:0] g);
    for (integer i = 7; i >= 0; i = i - 1) g2b[i] = (i == 7) ? g[i] : g2b[i+1] ^ g[i];
  endfunction
  reg [7:0] sent [0:3];
  reg [3:0] cr_ok;                                               // registered: stack t has a free FIFO slot
  reg [3:0] so_v; reg [290:0] so_p [0:3];
  (* async_reg = "true" *) reg [15:0] g1 [0:3];
  (* async_reg = "true" *) reg [15:0] g2 [0:3];
  reg [7:0] ackb_q [0:3], popb_q [0:3];
  assign wq_r = cr_ok[wq_stk];
  wire take = wq_v && wq_r;
  genvar t;
  for (t = 0; t < 4; t = t + 1) begin : gs
    wire [7:0] popb = g2b(g2[t][7:0]), ackb = g2b(g2[t][15:8]);
    wire [7:0] sent_n = sent[t] + ((take && wq_stk == t) ? 8'd1 : 8'd0);
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin sent[t] <= 0; cr_ok[t] <= 1'b0; g1[t] <= 0; g2[t] <= 0; ackb_q[t] <= 0; popb_q[t] <= 0;
        so_v[t] <= 1'b0; end
      else begin
        g1[t] <= si_g[16*t +: 16]; g2[t] <= g1[t];
        ackb_q[t] <= ackb; popb_q[t] <= popb;
        sent[t] <= sent_n;
        // a slot is free when fewer than SO_DEPTH sectors are unpopped (popb is a lagging view: conservative)
        cr_ok[t] <= (8'(sent_n - popb) < 8'(SO_DEPTH));
        so_v[t] <= take && (wq_stk == t);
      end
    always @(posedge clk) if (take && wq_stk == t)
      so_p[t] <= {wq_data ^ ((MUT == 1) ? 256'd1 : 256'd0), s_addr, wq_pc};
    assign so_d[292*t +: 292] = {so_p[t], so_v[t]};
  end
  // completions: per-stack deltas of the synchronised Gray count (<= 1 per stack per service clock, which is slower)
  wire [7:0] d0 = g2b(g2[0][15:8]) - ackb_q[0], d1 = g2b(g2[1][15:8]) - ackb_q[1];
  wire [7:0] d2 = g2b(g2[2][15:8]) - ackb_q[2], d3 = g2b(g2[3][15:8]) - ackb_q[3];
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin ack_n <= 0; map_fault <= 1'b0; end
    else begin
      ack_n <= 6'(d0) + 6'(d1) + 6'(d2) + 6'(d3);
      if (wb_fault || (take && s_fault)) map_fault <= 1'b1;
    end
  end endgenerate
endmodule
`default_nettype wire
