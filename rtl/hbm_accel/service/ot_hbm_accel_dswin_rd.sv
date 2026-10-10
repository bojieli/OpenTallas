`timescale 1ps/1fs
// DS-V4.1 HBM accelerator: WINDOW-row read address stream (stream mtp-rollback, 2026-10-08).
// The read side of ot_hbm_accel_dskv_wb_spec's window layout, driven by the spec-state address generator
// (ot_dshbm_spec_state WIN_RD / DSK_RD answers, WR = WIN_SLOTS): an answer address a = layer_slot * WR + w
// (A_WIN = 0; the DSpark stage rings follow the NL layers, A_DSK = NL * WR, so stage s is layer slot NL + s).
// For each row it emits the row's 17 PC-local sectors in order t = 0 .. 16:
//   stack w[6:5], PC w[4:0], PC-local sector j = t + 17 * w[7], bank {j[9:7], j[1:0]}, column j[6:2],
//   row WIN_ROW0 + layer_slot * SLOT_ROWS + (j >> 10)          -- the writer's map, byte for byte.
// WIN_SLOTS = 128 reproduces the as-built read stream (slot = pos mod 128; the bench mutant).
// One row request at a time (rq_r), one sector address a cycle, registered.
module ot_hbm_accel_dswin_rd #(
  parameter integer WIN_SLOTS = 256,
  parameter integer WR = 256,                    // the spec-state ring the answer addresses use
  parameter integer WIN_ROW0 = 2000, parameter integer SLOT_ROWS = 2,
  parameter integer AW = 32
)(
  input  wire          clk, rst_n,
  input  wire          rq_v,
  input  wire [AW-1:0] rq_addr,                  // spec-state answer address
  output wire          rq_r,
  output reg           sa_v,
  output reg  [1:0]    sa_stack,
  output reg  [4:0]    sa_pc, sa_bank, sa_col,
  output reg  [18:0]   sa_row,
  output reg  [4:0]    sa_t,
  output reg           sa_last
);
  localparam integer WB = $clog2(WR);
`ifndef SYNTHESIS
  initial if ((1 << WB) != WR || WIN_SLOTS > 256 || (WIN_SLOTS & (WIN_SLOTS - 1)) != 0)
    $fatal(1, "ot_hbm_accel_dswin_rd: WR and WIN_SLOTS must be powers of two (WIN_SLOTS <= 256)");
`endif
  reg busy; reg [5:0] ls; reg [7:0] w; reg [4:0] t;
  assign rq_r = !busy;
  wire [13:0] j = 14'(t) + 14'(w[7] ? 17 : 0);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      busy <= 0; ls <= 0; w <= 0; t <= 0; sa_v <= 0; sa_stack <= 0; sa_pc <= 0; sa_bank <= 0; sa_col <= 0;
      sa_row <= 0; sa_t <= 0; sa_last <= 0;
    end else begin
      sa_v <= 0; sa_last <= 0;
      if (!busy && rq_v) begin
        busy <= 1; t <= 0;
        ls <= 6'(rq_addr >> WB);
        w <= 8'(rq_addr & AW'(WR - 1) & AW'(WIN_SLOTS - 1));
      end else if (busy) begin
        sa_v <= 1; sa_stack <= w[6:5]; sa_pc <= w[4:0]; sa_bank <= {j[9:7], j[1:0]}; sa_col <= j[6:2];
        sa_row <= 19'(WIN_ROW0) + 19'(ls) * 19'(SLOT_ROWS) + 19'(j >> 10); sa_t <= t;
        if (t == 5'd16) begin busy <= 0; sa_last <= 1; end
        t <= t + 1'b1;
      end
    end
endmodule
