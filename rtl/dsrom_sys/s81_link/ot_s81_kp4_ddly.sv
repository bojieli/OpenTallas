`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_ddly (S81-KP4 2026-10-17): received-word delay hard tile of the S81 KP4 decoder cluster ot_s81_kp4_dec:
// one 64 x 546 1R1W SRAM (ot_sram_1r1w2c_64x546_m1, both ports on clk) written and read every cycle at a fixed
// distance DD = 55 (a free-running pointer: no enables, no flow control).  Word k of a frame enters at T + k (pure RTL
// time base) and leaves the macro read port at T + 56 + k.  The words and the corrections reach ot_s81_kp4_dout over
// the same number of tile seams (dsyn -> ddly -> dout, dsyn -> dchn -> dout), so DD does not depend on the seam
// latency.  The tile's pin registers register w_d and r_d; r_d is the macro read port itself.
// ---------------------------------------------------------------------------------------------------------------
// S81-RCK-10 vJ: the syndrome tile's k_* results come 2 rck later (ot_s81_kp4_dsyn SYN_LOCAL): words wait 2 more.
// S81-TYPES-9-RCK 11-08: OT_S81_RCK_RX_SPCYC (RX-SYN +1 pin cycle on sc_q -> sp, k_* one rck later): words wait 1 more.
`ifdef OT_S81_KP4_SYN_LOCAL
`ifdef SYNL_MUT_DD
`define OT_S81_KP4_DD_DEFAULT 56
`elsif OT_S81_RCK_RX_SPCYC
`ifdef RCKRF_MUT_DDSP
`define OT_S81_KP4_DD_DEFAULT 57
`else
`define OT_S81_KP4_DD_DEFAULT 58
`endif
`else
`define OT_S81_KP4_DD_DEFAULT 57
`endif
`else
// FABLE-FIX-HEAD-SD9F 11-18: the BASE form (no OT_S81_KP4_SYN_LOCAL) under OT_S81_RCK_RX_SPCYC kept DD 55 while k_* came one
// rck later: tb_s81_pdie_link got=5002 bad=5002.  Words wait 1 more, as in the SYN_LOCAL branch.
`ifdef OT_S81_RCK_RX_SPCYC
`define OT_S81_KP4_DD_DEFAULT 56
`else
`define OT_S81_KP4_DD_DEFAULT 55
`endif
`endif
// RQ (opt-in, default 0; S81-TYPES-9-RCK 11-08 RX-BACK vE): a read-data register right at the macro read port.  The macro
// is read one word EARLIER (address ptr - (DD - RQ)) and r_d is that read registered, so r_d carries the same word on the
// same cycle (DD >= 2 + RQ: the word was written before the earlier read and is not overwritten for 64 - DD cycles):
// ZERO added cycles.  It cuts the macro clk->q + 546-bit wire to the landing ring banks into two register hops.
// S81-RESIGN-DEEP 11-15 (FABLE-TRIAGE-HEADKV M6): ot_s81_kp4_dchn registers its 320 inputs inside the tile under
// OT_S81_DCHN_FACE (+1 cycle), so the received words wait one more cycle.
`ifdef OT_S81_DCHN_FACE
`define OT_S81_KP4_DD_FACE 1
`else
`define OT_S81_KP4_DD_FACE 0
`endif
// DDX (HEAD-SERDES-O 11-16, default 0 = unchanged): extra word delay asked by the parent ot_s81_kp4_dec when it registers
// the k_* seam in front of u_chn (DKREG): corrections come DDX cycles later, so the words wait DDX more.
// XPIPE1 moves one word-delay edge into the dsyn output wire. The SRAM
// address distance shrinks by one; complete receiver mission latency is unchanged.
`ifdef OT_S81_RCK_XPIPE1
`ifdef RCKRF_MUT_XPIPE_DD
`define OT_S81_KP4_DD_XPIPE 0
`else
`define OT_S81_KP4_DD_XPIPE 1
`endif
`else
`define OT_S81_KP4_DD_XPIPE 0
`endif
module ot_s81_kp4_ddly #(parameter integer DDX = 0,
    parameter integer DD = `OT_S81_KP4_DD_DEFAULT + `OT_S81_KP4_DD_FACE + DDX - `OT_S81_KP4_DD_XPIPE, parameter integer RQ = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [543:0]  w_d,
    output wire [543:0]  r_d
);
    wire [0:0] rs_n;
    ot_s81_kp4_rst #(.NL(1)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
    reg  [5:0] ptr;
    always @(posedge clk) if (!rs_n[0]) ptr <= 6'd0; else ptr <= ptr + 6'd1;
`ifdef RCKRF_MUT_DQREG
    wire [5:0] rd_d = ptr - DD[5:0];             // bench mutant: register added without the earlier read (+1 word late)
`else
    wire [5:0] rd_d = ptr - DD[5:0] + RQ[5:0];
`endif
    wire [545:0] d_rd;
    ot_sram_1r1w2c_64x546_m1 u_dmem (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in(rd_d), .rd_out(d_rd),
        .w_ce_in(1'b1), .w_addr_in(ptr), .wd_in({2'b00, w_d}), .w_mask_in({546{1'b1}}));
    generate if (RQ != 0) begin : g_rq
        (* keep = 1, dont_touch = 1 *) reg [543:0] rq_d;
        always @(posedge clk) rq_d <= d_rd[543:0];
        assign r_d = rq_d;
    end else begin : g_rd
        assign r_d = d_rd[543:0];
    end endgenerate
endmodule
