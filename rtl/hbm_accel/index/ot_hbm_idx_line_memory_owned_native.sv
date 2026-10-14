// Distinct memory+capture clock interface; no old clock ABI alias.
module ot_hbm_idx_line_memory_owned_native #(parameter integer W = 8, parameter integer AW = 4, parameter integer MEMV = 0, parameter integer READLAT = 1) (
  input wire ck, input wire [((W+255)/256)-1:0] clk_mem, input wire we, input wire [AW-1:0] wa, input wire [W-1:0] wd,
  input wire re, input wire [AW-1:0] ra, output wire [W-1:0] rd
);
  wire [W-1:0] raw_rd;
  generate if (READLAT == 2) begin : capture
    reg [W-1:0] captured;
    always @(posedge ck) captured <= raw_rd;
    assign rd = captured;
  end else begin : direct
    assign rd = raw_rd;
  end endgenerate
  generate if (MEMV == 0) begin : beh
    reg [W-1:0] m [0:(1<<AW)-1];
    reg [W-1:0] r;
    always @(posedge ck) begin
      if (we) m[wa] <= wd;
      if (re) r <= m[ra];
    end
    assign raw_rd = r;
  end else begin : mac
    localparam integer NM = (W + 255) / 256;
    wire [NM*256-1:0] wdx = {{(NM*256-W){1'b0}}, wd};
    wire [NM*256-1:0] rdx;
    genvar i;
    for (i = 0; i < NM; i = i + 1) begin : m
      if (AW == 8) begin : d256
        ot_sram_1r1w_256x256_m2_r2c2 u (.clk(clk_mem[i]), .r_ce_in(re), .r_addr_in(ra), .rd_out(rdx[i*256 +: 256]),
          .w_ce_in(we), .w_addr_in(wa), .wd_in(wdx[i*256 +: 256]), .w_mask_in({256{1'b1}}), .rr_en(2'b00),
          .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
      end else begin : d1024
        ot_sram_1r1w_1024x256_m2_r2c2 u (.clk(clk_mem[i]), .r_ce_in(re), .r_addr_in(ra), .rd_out(rdx[i*256 +: 256]),
          .w_ce_in(we), .w_addr_in(wa), .wd_in(wdx[i*256 +: 256]), .w_mask_in({256{1'b1}}), .rr_en(2'b00),
          .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
      end
    end
    assign raw_rd = rdx[W-1:0];
  end endgenerate
endmodule
`default_nettype wire
