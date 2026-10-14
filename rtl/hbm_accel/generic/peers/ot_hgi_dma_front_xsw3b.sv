`timescale 1ns/1ps
`default_nettype none
// el1011-hbm-dmafs 2026-10-12: ot_hgi_dma_front as the two-level split (ports and behaviour of ot_hgi_dma_front XP=1 XQ=1
// AP=0, X path one cycle longer): CORE tile + NB/8 replicated crossbar SLICE tiles, pure wiring (the die assembles the
// tiles; this module is the bench target). This candidate further extracts all lanes into independent roots.
// It is not qualified for routing: outstanding-grant and output-mux seam repair remains required.
module ot_hgi_dma_front_xsw3b #(
    parameter integer NS = 4,
    parameter integer NL = 8,
    parameter integer SBIT = 35,          // stack select = HBM byte address [SBIT+1:SBIT] (ot_hbm_loader_kport_address)
    parameter [35:0] STACK_BYTES = 36'd22500000000,   // a run must end inside its stack's capacity
    parameter integer NB = 32,            // VM wide lanes = VM banks (power of 2): lane p carries a sector of bank p
    parameter integer LD = 16,            // lane buffer depth = the svc's initial credit a lane (power of 2); must cover the
                                          // credit round trip (svc lane reg -> die hops -> pin flop -> land -> pop -> credit
                                          // reg -> die hops -> svc pin flop): 4 + 2 x hops + svc cycles; 4 caps a lane at 4 / RTT
    parameter integer AP = 0,             // hgi-1010 b: 1 = the HC weight APERTURE (VM words >= 2^18): the VM lane grows an ap
                                          //   bit {v, ap, sector 15, data, mask} (ap = the 18-bit VM sector >= 32,768; sector =
                                          //   that minus 32,768); a sector past the two slots (>= 40,960) faults; bank b picks
                                          //   only while wl_rdy[b] (the VM unit's aperture queue stop, pin-flopped here)
    parameter integer XP = 1,             // hbm-fq/dma textbook rebuild (10-11, audit classes 5): 1 = X1 from per-lane registered bank
                                          //   request vectors and a two-level (4 x 8) rotating pick; X2 split into the AND-OR rung
                                          //   (registered) and the conversion rung; tag beat counts and the done count in
                                          //   registered rungs (match matrix -> popcount -> update).  +1 cycle out, +2 on tag free.
    parameter integer XQ = 1,             // hbm-fq/mvf (route n2b-a2fb5da71 post-CTS -471 ps x2s -> wl_d: lane subtract -> quarter
                                          //   select -> int8 / e4m3 conversion in one cycle; wl_d -> wl pin 462 ps of wire): 1 (needs
                                          //   XP) = a SELECT rung (lane offset, the quarter / half of the sector, s18 registered), the
                                          //   CONVERSION rung on the pre-selected bits, and a pure output register at the VM-lane pins.
                                          //   +2 cycles out.
    parameter integer QID = 0, MUT_B2 = 0, B2=1,
    parameter integer MUT = 0
) (
    input  wire                  clk,
    input  wire [NL-1:0]         lane_clk,
    input  wire [NB/8-1:0]       slice_clk,
    input  wire                  rst_n,
    input  wire                  mv_v,
    output wire                  mv_rdy,
    input  wire [226:0]          mv,
    output reg                   mv_done,
    output reg                   mv_fault,
    // indexed row stream command + id list
    input  wire                  ix_v,
    output wire                  ix_rdy,
    input  wire [175:0]          ix_cmd,
    input  wire                  id_v,
    output wire                  id_rdy,
    input  wire [31:0]           id,
    // requests per stack {v, tag 4, nsec 9, addr 37}
    output reg  [NS*51-1:0]      dq,
    input  wire [NS-1:0]         dq_rdy,
    // data per stack x lane {v, fault, tag 4, idx 8, data 256}
    input  wire [NS*NL*270-1:0]  dd,
    output wire [NS*NL-1:0]      dd_cr,
    // VM wide write port, NB lanes {v, sector 15, wdata 256, word mask 8}
    output wire [NB*(280+AP)-1:0] wl,
    input  wire [NB-1:0]         wl_done,
    input  wire [NB-1:0]         wl_rdy
);
    localparam integer NIN = 2*NL;
    wire [NB*NIN-1:0] xs_oh; wire [NIN*277-1:0] xs_ls; wire [NB-1:0] xs_v; wire [NB*279-1:0] wd;
    ot_hgi_dma_front_core3b #(.NS(NS), .NL(NL), .SBIT(SBIT), .STACK_BYTES(STACK_BYTES), .NB(NB), .LD(LD), .AP(AP), .XP(XP), .XQ(XQ),
        .MUT(MUT),.QID(QID),.MUT_B2(MUT_B2)) u_core (.clk(clk), .lane_clk(lane_clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault),
        .ix_v(ix_v), .ix_rdy(ix_rdy), .ix_cmd(ix_cmd), .id_v(id_v), .id_rdy(id_rdy), .id(id), .dq(dq), .dq_rdy(dq_rdy), .dd(dd),
        .dd_cr(dd_cr), .xs_oh(xs_oh), .xs_ls(xs_ls), .xs_v(xs_v), .wl_done(wl_done), .wl_rdy(wl_rdy));
    genvar s, b;
    generate for (s = 0; s < NB / 8; s = s + 1) begin : xs
        ot_hgi_dma_front_xs #(.NIN(NIN), .NBS(8), .MUT(MUT)) u_xs (.clk(slice_clk[s]), .xo(xs_oh[s*8*NIN +: 8*NIN]), .ls(xs_ls),
            .wd(wd[s*8*279 +: 8*279]));
    end endgenerate
    generate for (b = 0; b < NB; b = b + 1) begin : wg
        assign wl[b*(280+AP) +: 280+AP] = (280+AP)'({xs_v[b], wd[b*279 +: 279]});
    end endgenerate
`ifndef SYNTHESIS
    initial if (XP != 1 || XQ != 1 || AP != 0 || NB % 8 != 0) $fatal(1, "ot_hgi_dma_front_xsw: XP=1 XQ=1 AP=0, NB multiple of 8 only");
`endif
endmodule
`default_nettype wire
