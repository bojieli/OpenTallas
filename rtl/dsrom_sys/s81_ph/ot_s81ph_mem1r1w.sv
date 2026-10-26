`timescale 1ns/1ps
// ot_s81ph_mem1r1w (CLAUDE S81-PH collective, 2026-10-06): a 1R1W array with a REGISTERED read port
// (q <= mem[ra] when re; q holds otherwise; a same-cycle write to ra returns the OLD word -- callers forward).
// SRAM = 0: flops.  SRAM = 1: ceil(W/128) x ot_sram_1r1w_512x128_m4_r2c2 (DEPTH <= 512; the macro's read data is
// registered inside the macro and holds while r_ce is low, so both builds have the same cycle behaviour).
// WREG = 1 (ds-1010/coll-tu 2026-10-11, opt-in): REGISTERED WRITE PORT.  {we, wa, wd} are captured in flops beside the
// array and written one edge later, so every array write pin (SRAM w_ce_in / w_addr_in / wd_in) is driven by a flop
// that drives nothing else (lane lcrpi EF_HOLD: w_addr_in = the EP's nxt_i, a setup-critical register that hold repair
// could not buffer -- hold stuck -68 ps at u_rb w_addr_in[8] for 8,570 iterations).  A read in the cycle right after a
// write to the same address is forwarded from the write register, so the caller-visible behaviour is unchanged
// (registered read; a same-cycle write still returns the OLD word; q holds while re is low).  Needs rst_n.
module ot_s81ph_mem1r1w #(
    parameter integer W = 64,
    parameter integer DEPTH = 16,
    parameter integer SRAM = 0,
    parameter integer WREG = 0,
    parameter integer AW = (DEPTH > 1) ? $clog2(DEPTH) : 1
) (
    input  wire          clk,
    input  wire          rst_n,      // used only with WREG = 1
    input  wire          we,
    input  wire [AW-1:0] wa,
    input  wire [W-1:0]  wd,
    input  wire          re,
    input  wire [AW-1:0] ra,
    output wire [W-1:0]  q
);
    // array-side write port (WREG = 0: the caller's)
    wire          we_m;
    wire [AW-1:0] wa_m;
    wire [W-1:0]  wd_m;
    wire [W-1:0]  q_m;
    generate if (WREG != 0) begin : g_wreg
        reg          wv_q, sel_r;
        reg [AW-1:0] wa_q;
        reg [W-1:0]  wd_q, fd_r;
`ifdef OT_S81PH_MEM_WREG_MUT
        wire hit = 1'b0;                 // bench mutant: no read-after-write forwarding
`else
        wire hit = wv_q && (ra == wa_q); // the word written last cycle has not reached the array yet
`endif
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin wv_q <= 1'b0; sel_r <= 1'b0; end
            else begin wv_q <= we; if (re) sel_r <= hit; end
        always @(posedge clk) begin
            wa_q <= wa; wd_q <= wd;
            if (re && hit) fd_r <= wd_q;
        end
        assign we_m = wv_q; assign wa_m = wa_q; assign wd_m = wd_q;
        assign q = sel_r ? fd_r : q_m;
    end else begin : g_wdir
        assign we_m = we; assign wa_m = wa; assign wd_m = wd;
        assign q = q_m;
    end endgenerate
    generate if (SRAM == 0) begin : g_ff
        reg [W-1:0] mem [0:DEPTH-1];
        reg [W-1:0] q_r;
        always @(posedge clk) begin
            if (we_m) mem[wa_m] <= wd_m;
            if (re) q_r <= mem[ra];
        end
        assign q_m = q_r;
    end else begin : g_sram
        localparam integer NT = (W + 127) / 128;
        wire [NT*128-1:0] wdp = {{(NT*128-W){1'b0}}, wd_m};
        wire [NT*128-1:0] qp;
        wire [8:0] wa9 = {{(9-AW){1'b0}}, wa_m};
        wire [8:0] ra9 = {{(9-AW){1'b0}}, ra};
        genvar t;
        for (t = 0; t < NT; t = t + 1) begin : g_t
            ot_sram_1r1w_512x128_m4_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra9), .rd_out(qp[t*128 +: 128]),
                .w_ce_in(we_m), .w_addr_in(wa9), .wd_in(wdp[t*128 +: 128]), .w_mask_in({128{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
        end
        assign q_m = qp[W-1:0];
`ifndef SYNTHESIS
        initial if (DEPTH > 512) $fatal(1, "ot_s81ph_mem1r1w: SRAM depth %0d > 512", DEPTH);
`endif
    end endgenerate
endmodule
