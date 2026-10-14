`timescale 1ns/1ps
`default_nettype none
// Fused source-clock leaf candidate: internal registered pick plus three XS captures.
module ot_hgi_dma_front_main10 #(
    parameter integer SOURCE_CAP=16, REQ_IDLE=0,
    parameter integer NS = 1,
    parameter integer NL = 8,
    parameter integer SBIT = 35,          // stack select = HBM byte address [SBIT+1:SBIT] (ot_hbm_loader_kport_address)
    parameter [35:0] STACK_BYTES = 36'd22500000000,   // a run must end inside its stack's capacity
    parameter integer NB = 8,            // VM wide lanes = VM banks (power of 2): lane p carries a sector of bank p
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
    parameter integer MUT = 0
) (
    input wire lease_grant,output reg lease_busy,
    input wire [NB-1:0] wl_credit,
    output wire [NB-1:0] issue_v,
    input wire [1:0] stack_id,
    input  wire                  clk,
    input wire [NS*NL-1:0] dv_w, lflt_w,
    input wire [2*NS*NL-1:0] lane_epoch,
    input wire [NS*NL*4-1:0] dtag_w,
    input wire [2*NS*NL*NB-1:0] rqv_w,
    output wire [287:0] tag_sectors,
    output wire [1:0] cfg_ks,
    output wire [2:0] cfg_sf,
    output reg [2*NS*NL-1:0] ack_epoch,
    input  wire                  rst_n,
    input  wire                  mv_v,
    output reg                   mv_rdy,
    input  wire [226:0]          mv,
    output reg                   mv_done,
    output reg                   mv_fault,
    // indexed row stream command + id list
    input  wire                  ix_v,
    output reg                   ix_rdy,
    input  wire [175:0]          ix_cmd,
    input  wire                  id_v,
    output reg                   id_rdy,
    input  wire [31:0]           id,
    // requests per stack {v, tag 4, nsec 9, addr 37}
    output reg  [NS*51-1:0]      dq,
    input  wire [NS-1:0]         dq_rdy,
    // data per stack x lane {v, fault, tag 4, idx 8, data 256}

    // VM wide write port, NB lanes {v, sector 15, wdata 256, word mask 8}
    input  wire [NB-1:0]         wl_done,
    input  wire [NB-1:0]         wl_rdy,
    input wire [NS*NL*277-1:0] ls_a,ls_b,
    output wire [NB*281-1:0] vm_packet,output wire [NB-1:0] vm_bad
);
 wire [NB*(2*NS*NL)-1:0] xs_oh;wire [NB-1:0] xs_v;
 wire [NB*280-1:0] wd;wire [NB-1:0] valid;
 ot_hgi_dma_front_ctrl7b #(.SOURCE_CAP(SOURCE_CAP),.REQ_IDLE(REQ_IDLE),.NS(NS),.NL(NL),.SBIT(SBIT),.STACK_BYTES(STACK_BYTES),.NB(NB),.LD(LD),.AP(AP),.XP(XP),.XQ(XQ),.MUT(MUT)) u_ctrl(
.lease_grant(lease_grant),.lease_busy(lease_busy),.wl_credit(wl_credit),.issue_v(issue_v),.stack_id(stack_id),.clk(clk),.dv_w(dv_w),.lflt_w(lflt_w),.lane_epoch(lane_epoch),.dtag_w(dtag_w),.rqv_w(rqv_w),.tag_sectors(tag_sectors),.cfg_ks(cfg_ks),.cfg_sf(cfg_sf),.ack_epoch(ack_epoch),.rst_n(rst_n),.mv_v(mv_v),.mv_rdy(mv_rdy),.mv(mv),.mv_done(mv_done),.mv_fault(mv_fault),.ix_v(ix_v),.ix_rdy(ix_rdy),.ix_cmd(ix_cmd),.id_v(id_v),.id_rdy(id_rdy),.id(id),.dq(dq),.dq_rdy(dq_rdy),.xs_oh(xs_oh),.xs_v(xs_v),.wl_done(wl_done),.wl_rdy(wl_rdy),.fmt_bad(vm_bad));
 ot_hgi_dma_front_xs_vm3 #(.NIN(2*NS*NL),.NBS(NB),.MUT(MUT)) formatter(.clk(clk),.xo(xs_oh),.ls_a(ls_a),.ls_b(ls_b),.wd(wd),.v_o(valid),.bad_o(vm_bad));
 for(genvar b=0;b<NB;b++)assign vm_packet[b*281+:281]={valid[b],wd[b*280+:280]};
endmodule
`default_nettype wire
