`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA FRONT (hgi-takeover 2026-10-10; coordinator: the svc-side DMA stream feeds the VM wide port at up to 1 KB a
// cycle, hbm-forks builds the svc side, hgi-takeover the front and the VM side).  Interface spec: hgi-takeover.log
// "SPEC for hbm-forks" (03:40 PT).
//
// Takes a DMA LOAD (move word of ot_hgi_dma_mover, 227 b) whose shape is eligible:
//   src HBM, dst VM, istride 1 both sides, source row base and row stride 32 B aligned, n x esize a multiple of 32 B,
//   destination row base and row stride multiples of 8 words, formats FP32 / U32 / BF16 / FP8E4M3 / INT8 -> VM words;
// (the DMA unit sends every other move to the sector / serial mover), and
//   R  splits it into per-stack requests {tag, nsec <= 256, addr}, one a cycle: rows in windows of 4, chunk by chunk
//      round robin over the window's rows (a chunk = up to 256 sectors); the stack = address bits [SBIT+1:SBIT]); the tag remembers the run's first VM sector;
//   L  pin-flops the NS x NL data lanes, computes each beat's VM sector (tag base + idx x K) and lands it in an LD-entry
//      lane FIFO (source sector in a 128 x 256 SRAM macro a lane, VM sector in flops; credit LD a lane = the svc's initial
//      credit; the credit returns when the entry's read issues); a tag is free again once all its beats landed; the read
//      (macro output register) fills a 3-entry skid, issued on registered occupancy only;
//   C  per lane two out buffers {VM sector, source sector}: the skid head loads the idle one once every destination slot
//      (K = 4 / esize: FP32 / U32 1, BF16 2, FP8 / INT8 4) of the active one was picked;
//   X  X1 per bank a rotating-priority pick among the lanes' active buffers (each lane's K slots sit in K consecutive
//      banks), registered; X2 per bank the AND-OR mux of the picked lane's buffer (the one active in X1's cycle), decoded
//      for its slot exactly as the mover (BF16 << 16, E4M3 exact, NaN -> 0x7FC00000, INT8 exact), registered into the VM
//      wide lane = the bank (NB destination sectors a cycle);
//   done when every destination sector's wide write is acknowledged.
//   Fault (sticky until reset): a request run crossing a stack or ending beyond STACK_BYTES, an svc fault beat, a beat without a credit.
// Rate: NS x NL source sectors a cycle in (the svc lane rate), NB destination sectors a cycle out (the VM port).
// INDEXED ROW STREAM (spec 3.3, hgi-1010/c 2026-10-10; ROW_GATHER's list-order load, Engram rows, verify embeddings):
//   ix_cmd {rebase 1, cnt 20, dstride 32, dbase 32, n 21, dyn_mul 27, abase 40, fmt 3} (176 b: fmt [2:0], abase [42:3],
//   dyn_mul [69:43], n [90:70], dbase [122:91], dstride [154:123], cnt [174:155], rebase [175]) + the id list on id_v /
//   id_rdy / id 32.  rebase 1: abase is the CP's EFFECTIVE base, which already holds id_0 x dyn_mul (spec 3.3 with
//   X = U32(VM[I + L])), so row e reads abase + (id_e - id_0) x dyn_mul
//   (list order, exactly cnt ids; the DMA unit reads them from the I table).  Row e = the A row of id_e: source byte address
//   abase + id_e x dyn_mul (n elements of fmt, whole sectors), lands at VM word dbase + e x dstride.  The id pipeline: id
//   pin flop -> two 16 x 27 partial products (registered) -> address add (registered, alignment / 37-bit range check) -> a
//   4-row queue; the request generator issues each row as runs of <= 256 sectors on the row's own stack (rows of one list
//   spread over all stacks by their ids), one request a cycle, exactly as the strided form; landing / convert / crossbar
//   are shared.  Faults: a misaligned row (abase or dyn_mul not 32 B multiples), an address beyond 37 bits, a run
//   crossing a stack.  Eligibility of n / dbase / dstride as for the strided form (the DMA unit checks; the front faults
//   a non-sector n).
// MUT (bench): 1 BF16 halves mirrored within the sector: must FAIL; 2 a tag freed 8 beats early: must FAIL;
//   3 the id's high partial product dropped (ids >= 2^16 alias): must FAIL; 4 the destination row pointer advances on
//   every second row only: must FAIL; 5 the rebase (id_0 x dyn_mul) not removed: must FAIL.
//   AP (hgi-1010 b): 6 the VM's per-bank stop ignored, 7 the ap bit never set (the slot load lands in VM): must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
// el1011-hbm-dmafs 2026-10-12: CORE tile of the two-level split of ot_hgi_dma_front (XP=1 XQ=1 AP=0 only): everything but
// the X2 crossbar, which lives in 4 replicated slice tiles (ot_hgi_dma_front_xs, 8 banks each); ot_hgi_dma_front_xsw
// composes them with the ports of ot_hgi_dma_front.  Seams (all registered here): xs_oh = the registered X1 pick per bank,
// xs_ls = each lane's previously active out buffer {fmt 3, sector 18, source 256} (the move format travels WITH the data:
// every bank decodes its own registered copy, no shared format net), xs_v = the VM lane valids (aligned with the slices'
// output registers: one more valid rung x4b_v for the slices' input pin flops).
module ot_hgi_dma_front_core10 #(
    parameter integer SOURCE_CAP=16,REQ_IDLE=0,
    parameter integer NS = 4,
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
    parameter integer QID = 0, MUT_B2 = 0,
    parameter integer MUT = 0
) (
    input wire lease_grant,output wire lease_busy,
    input wire [NB-1:0] wl_credit,
    output wire [NB*281-1:0] vm_packet,output wire [NB-1:0] vm_bad,
    output wire [NB-1:0] issue_v,
    input  wire                  clk,
    input  wire [NL-1:0]         lane_clk,
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
    output wire [NB*(2*NIN)-1:0]     xs_oh,          // seam -> slices: registered X1 pick per bank (one-hot over lanes)
    output wire [2*NIN*277-1:0]    xs_ls,          // seam -> slices: lane buffers {fmt 3, sector 18, source 256}
    output wire [NB-1:0]         xs_v,           // the VM lane valids (wl[b] = {xs_v[b], slice wd[b]})
    input  wire [NB-1:0]         wl_done,
    input  wire [NB-1:0]         wl_rdy
);
    localparam integer NIN=NL;
    localparam integer QS=(MUT_B2==1)?(QID+1)%4:QID, LQ=(MUT_B2==2)?(QID+1)%4:QID;
    wire [50:0] local_dq;
    for (genvar s=0;s<NS;s=s+1) assign dq[s*51+:51] = s==LQ ? local_dq : 51'd0;
    for (genvar g=0;g<NS*NL;g=g+1) if (g/NL != LQ) assign dd_cr[g]=1'b0;
    wire [NIN-1:0] dv_w, lflt_w; wire [2*NIN-1:0] lane_epoch, ack_epoch;
    wire [NIN*4-1:0] dtag_w;
    wire [2*NIN*NB-1:0] rqv_w;
    // Reuse the actual CLOSED NB32 lane master unchanged. Four request quadrants
    // fold into the native eight-bank owner geometry; sectors and epoch stay exact.
    wire [2*NIN*32-1:0] closed_rqv;
    for(genvar i=0;i<2*NIN;i++)for(genvar b=0;b<8;b++)
      assign rqv_w[i*8+b]=closed_rqv[i*32+b]|closed_rqv[i*32+8+b]|closed_rqv[i*32+16+b]|closed_rqv[i*32+24+b];
    wire [287:0] tag_sectors; wire [1:0] cfg_ks; wire [2:0] cfg_sf;
    ot_hgi_dma_front_main10 #(.SOURCE_CAP(SOURCE_CAP),.REQ_IDLE(REQ_IDLE),.NS(1),.NL(NL),.SBIT(SBIT),.STACK_BYTES(STACK_BYTES),.NB(NB),.LD(LD),.AP(AP),.XP(XP),.XQ(XQ),.MUT(MUT)) u_main (
      .lease_grant(lease_grant),.lease_busy(lease_busy),.wl_credit(wl_credit),.issue_v(issue_v),.stack_id(2'(QS)),.clk(clk),.rst_n(rst_n),.mv_v(mv_v),.mv_rdy(mv_rdy),.mv(mv),.mv_done(mv_done),.mv_fault(mv_fault),
      .ix_v(ix_v),.ix_rdy(ix_rdy),.ix_cmd(ix_cmd),.id_v(id_v),.id_rdy(id_rdy),.id(id),
      .dq(local_dq),.dq_rdy(dq_rdy[LQ]),.wl_done(wl_done),.wl_rdy(wl_rdy),
      .dv_w(dv_w),.lflt_w(lflt_w),.lane_epoch(lane_epoch),.dtag_w(dtag_w),.rqv_w(rqv_w),
      .tag_sectors(tag_sectors),.cfg_ks(cfg_ks),.cfg_sf(cfg_sf),.ack_epoch(ack_epoch),.ls_a(xs_ls[0+:NIN*277]),.ls_b(xs_ls[NIN*277+:NIN*277]),.vm_packet(vm_packet),.vm_bad(vm_bad));
    for (genvar g=0;g<NIN;g=g+1) begin: lg
      ot_hgi_dma_front_lane2 #(.NB(32),.LD(16)) u_lane (
        .clk(lane_clk[g]),.rst_n(rst_n),.dd(dd[(LQ*NL+g)*270+:270]),.tag_sectors(tag_sectors),.ks(cfg_ks),.sf(cfg_sf),
        .ack_epoch(ack_epoch[g*2+:2]),.epoch(lane_epoch[g*2+:2]),.beat_valid(dv_w[g]),.beat_tag(dtag_w[g*4+:4]),
        .lane_fault(lflt_w[g]),.lane_sector(xs_ls[g*554+:554]),
        .credit(dd_cr[LQ*NL+g]),.request_banks(closed_rqv[g*64+:64]));
    end
endmodule
`default_nettype wire
