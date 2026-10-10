`timescale 1ns/1ps
`default_nettype none
// Two physical 1R1W macros, 256 protected sectors. No cache payload flops.
// Registered macro pins; payload then sidecar, independent read/write ports.
// Four reserved publication slots permit read II=2 despite decoder latency.
module hbm_svc_dma_sram_bank_wide #(parameter integer ECC_MUT = 0, parameter integer BANK_MUT = 0) (
  input wire clk, input wire rst_n,
  input wire wr_v, output wire wr_rdy, input wire [7:0] wr_addr,
  input wire [255:0] wr_data, input wire wr_fault,
  input wire rd_v, output wire rd_rdy, input wire [7:0] rd_addr,
  output wire out_v, input wire out_rdy,
  output wire [255:0] out_data, output wire out_fault
);
  reg [255:0] valid_map;
  reg [1:0] wp;
  reg [7:0] wa, ra, commit_addr;
  reg wf, commit;
  reg [31:0] parity_hold;
  reg rp;
  reg rce, wce;
  reg [7:0] raddr, waddr;
  reg [255:0] wd;
  wire [255:0] mq;
  wire [255:0] mq0, mq1;
  reg rsel, wsel, return_sel;
  assign mq = return_sel ? mq1 : mq0;
  wire w_take = wr_v && wr_rdy;
  wire r_take = rd_v && rd_rdy;
  reg [2:0] reserved;
  // A read already launched owns its group until both macro edges finish.
  wire read_conflict = (rp && wr_addr == ra) ||
                       (rce && wr_addr == {rsel, raddr[6:0]});
  assign wr_rdy = rst_n && (wp != 1) && !read_conflict;
  // Writes win a same-group simultaneous admission. Reads of absent groups
  // are accepted as poisoned transactions, never as uninitialized payload.
  assign rd_rdy = rst_n && !rp && reserved < 4 &&
                  !(wp != 0 && rd_addr == wa) &&
                  !(commit && rd_addr == commit_addr) &&
                  !(wr_v && rd_addr == wr_addr);

  wire [71:0] encoded [0:3];
  genvar g;
  integer j;
  generate for (g=0; g<4; g=g+1) begin: ecc
    ot_secded_enc #(.K(64), .R(8), .MUT(ECC_MUT)) enc (
      .clk(clk), .d(wr_data[g*64 +: 64]), .q(encoded[g]));
  end endgenerate

  // Data pins have no reset; locally reset enable/control prevents use.
  always @(posedge clk) begin
    if (w_take) begin wa <= wr_addr; wf <= wr_fault; end
    if (wp == 1) begin
      waddr <= {1'b0, wa[6:0]}; wsel <= wa[7];
      for (j=0; j<4; j=j+1) begin
        wd[j*64 +: 64] <= encoded[j][63:0];
        parity_hold[j*8 +: 8] <= encoded[j][71:64];
      end
    end
    if (wp == 2) begin
      waddr <= {1'b1, wa[6:0]}; wsel <= wa[7];
      wd <= {204'b0, ~wa, wa, 1'b0, 1'b1, ~wf, wf, parity_hold};
      commit_addr <= wa;
    end
    if (r_take) begin ra <= rd_addr; raddr <= {1'b0, rd_addr[6:0]}; rsel <= rd_addr[7]; end
    if (rp) begin raddr <= {1'b1, ra[6:0]}; rsel <= ra[7]; end
    if (rce) return_sel <= rsel;
  end
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin wp <= 0; rp <= 0; wce <= 0; rce <= 0;
      commit <= 0; valid_map <= 0;
    end else begin
      wce <= (wp != 0);
      commit <= (wp == 2);
      if (commit) valid_map[commit_addr] <= 1;
      if (w_take) valid_map[wr_addr] <= 0;
      case (wp)
        0: if (w_take) wp <= 1;
        1: wp <= 2;
        2: wp <= w_take ? 1 : 0;
        default: wp <= 0;
      endcase
      rce <= r_take || rp;
      rp <= r_take;
    end
  end
  ot_sram_1r1w_256x256_m2_r2c2 mem0 (
    .clk(clk), .r_ce_in(rce && !rsel), .r_addr_in(raddr), .rd_out(mq0),
    .w_ce_in(wce && !(wsel ^ (BANK_MUT != 0))), .w_addr_in(waddr), .wd_in(wd),
    .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'b0),
    .cr_en(2'b00), .cr_sel(16'b0));
  ot_sram_1r1w_256x256_m2_r2c2 mem1 (
    .clk(clk), .r_ce_in(rce && rsel), .r_addr_in(raddr), .rd_out(mq1),
    .w_ce_in(wce && (wsel ^ (BANK_MUT != 0))), .w_addr_in(waddr), .wd_in(wd),
    .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'b0),
    .cr_en(2'b00), .cr_sel(16'b0));

  reg payload_return, sidecar_return;
  reg [7:0] return_addr;
  reg [255:0] payload;
  reg present, bad1, bad2;
  always @(posedge clk) begin
    if (rce && !raddr[7]) begin
      return_addr <= {rsel,raddr[6:0]}; present <= valid_map[{rsel,raddr[6:0]}];
    end
    if (payload_return) payload <= mq;
    // The markers also reject a torn write and corrupted fault metadata.
    bad1 <= !present || mq[33] != ~mq[32] || mq[35:34] != 2'b01 ||
            mq[43:36] != return_addr || mq[51:44] != ~return_addr || mq[32];
    bad2 <= bad1;
  end
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin payload_return <= 0; sidecar_return <= 0; end
    else begin payload_return <= rce && !raddr[7];
               sidecar_return <= rce && raddr[7]; end
  wire [255:0] corrected;
  wire [3:0] dv, ce, ue;
  generate for (g=0; g<4; g=g+1) begin: decode
    ot_secded_dec #(.K(64), .R(8)) dec (
      .clk(clk), .rst_n(rst_n), .v(sidecar_return),
      .w({mq[g*8 +: 8], payload[g*64 +: 64]}),
      .ov(dv[g]), .d(corrected[g*64 +: 64]), .ce(ce[g]), .ue(ue[g]),
      .n_ce(), .n_ue());
  end endgenerate
  reg [256:0] pub [0:3];
  reg [3:0] occupied;
  reg [1:0] head, tail;
  wire poison = bad2 || (|ue);
  assign out_v = rst_n && occupied[head];
  assign out_data = out_v ? pub[head][255:0] : 256'b0;
  assign out_fault = out_v && pub[head][256];
  wire pop = out_v && out_rdy;
  always @(posedge clk) if (dv[0])
    pub[tail] <= {poison, poison ? 256'b0 : corrected};
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin head <= 0; tail <= 0; occupied <= 0; reserved <= 0; end
    else begin
      case ({r_take,pop})
        2'b10: reserved <= reserved + 1'b1;
        2'b01: reserved <= reserved - 1'b1;
        default: reserved <= reserved;
      endcase
      if (pop) begin occupied[head] <= 0; head <= head + 1'b1; end
      if (dv[0]) begin occupied[tail] <= 1; tail <= tail + 1'b1; end
    end
  end
endmodule
`default_nettype wire
