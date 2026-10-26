`timescale 1ns/1ps
import ot_hdc_engram_tables_shipped_pkg::*;
module ot_ra640_inactive_miter #(
    parameter integer RETURN_AGE = 0,
    parameter integer ROWSTRIPE = 0, // opt-in nine contiguous atoms per PC row
    parameter integer NR    = 4,           // TP ranks
    parameter integer CPR   = 6,           // columns per rank (ENG_COLS / NR)
    parameter integer NSLOT = 2,           // prefetch slots in every sink
    parameter integer ABW   = 36,          // HBM byte address bits (2 stacks, 45 GB)
    parameter [ABW-1:0] BASE = {ABW{1'b0}},// region base (32-B aligned)
    parameter integer PIPE  = 0,           // 1: one-hot replicated atom select (+1 stage), linear-split CRC
    // CRCMAT (sys-takeover 2026-10-09, opt-in; define OT_ENGRAM_CRCMAT or the parameter): every CRC term as an explicit
    // GF(2) matrix (per output bit a reduction XOR of a constant-masked vector -> balanced XOR trees, depth log2 256 = 8)
    // instead of 32 chained crc_byte calls (engram-lkp-B/C PREROUTE -2144 ps: e2_d -> g_crc1.ga, a ~100-level XOR chain).
    // crc_beat(c, d) = crc_beat(c, 0) ^ crc_beat(0, d) and crc_byte(c, b) = crc_byte(c, 0) ^ crc_byte(0, b) (linear,
    // no constant term): identical values, 0 cycles.
`ifdef OT_ENGRAM_CRCMAT
    parameter integer CRCMAT = 1,
`else
    parameter integer CRCMAT = 0,
`endif
    parameter integer SLW   = (NSLOT > 1) ? $clog2(NSLOT) : 1
) (
    input  wire                     clk,        // front root: window ids / win_n, hash capture res_c, straps
    // st10 (S81-TILES2 10-17): three more phase-0 1:1 regional roots of the same source as clk (each only re-roots
    // registers; no logic, cycle or edge changes; in simulation all four carry the same clock):
    input  wire                     clk_ctl,    // control: FSM / issue / address / age-seen / write path / emit control / qn
    input  wire                     clk_rd,     // read select: the three row SRAM macros, r_* and E1
    input  wire                     clk_em,     // emit tail: E2, CRC, E3, transport / od, status
    input  wire                     clk_seed,
    input  wire [5:0]               clk_hash,
    input  wire                     rst_n,
`ifdef OT_S81ENG_RR_N32
    input wire[15:0] rst_regions,
`endif
    // static straps (die-level ties): one hardened element serves all 8 home dies
    input  wire                     cfg_layer,       // Engram layer index (0: layer 1, 1: layer 14)
    input  wire [1:0]               cfg_rank,        // TP rank of this die
    // window (lead flit)
    input  wire                     win_valid,
    input  wire [SLW-1:0]           win_slot,
    input  wire [4*ENG_ID_W-1:0]    win_ids,
    // sink slot releases, one pulse per release, per rank

    // HBM controller request port
    input wire                      hq_valid,

    input wire  [ABW-6:0]           hq_atom,
    input wire [3:0]               hq_len,
    input wire  [2:0]               hq_tag,
    // HBM controller response port (32-B atoms)
    input  wire                     hr_valid,
    input  wire [SLW-1:0]           hr_slot,
    input  wire [2:0]               hr_tag,
    input  wire [2:0]               hr_tag_w,       // n32: second pin-flop copy of hr_tag (seen write decode, wbank)
    input  wire [3:0]               hr_idx,
    // ELEM-ENG2 n32 (native census 10-21): kept pin-flop copies (same pins, same edges) for the per-bank / per-group
    // acceptance and seen consumers: win_valid_c[4:0] -> accept_ids group g, [7:5] -> accept_seen banks 2k,2k+1;
    // hr_idx_w[4b +: 4] -> accept_seen bank b (write decode + local read)
    input  wire [7:0]               win_valid_c,
    input  wire [4*CPR-1:0]         hr_idx_w,
    input  wire [255:0]             hr_data,
    // row beats to the all-gather and the local sink
    input wire                     o_valid,

    input wire [4:0]               o_col,
    input wire [2:0]               o_beat,
    input wire [SLW-1:0]           o_slot,
    input wire [263:0]             o_data,
    // integrity
    input wire                      st_valid,        // one status per emitted row
    input wire  [SLW-1:0]           st_slot,
    input wire                      st_bad,          // CRC mismatch on that row
    input wire                      fault
);
integer mutate=0; longint checks=0, inactive=0; initial void'($value$plusargs("LOOKUP_MUT=%d", mutate));
wire  ref_hq_valid;
wire [ABW-6:0] ref_hq_atom;
wire [3:0] ref_hq_len;
wire [2:0] ref_hq_tag;
wire  ref_o_valid;
wire [4:0] ref_o_col;
wire [2:0] ref_o_beat;
wire [SLW-1:0] ref_o_slot;
wire [263:0] ref_o_data;
wire  ref_st_valid;
wire [SLW-1:0] ref_st_slot;
wire  ref_st_bad;
wire  ref_fault;
ot_ra640_inactive_ref #(.RETURN_AGE(RETURN_AGE),.ROWSTRIPE(ROWSTRIPE),.NR(NR),.CPR(CPR),.NSLOT(NSLOT),.ABW(ABW),.BASE(BASE),.PIPE(PIPE),.CRCMAT(CRCMAT),.SLW(SLW)) u_ref (.clk(clk),.clk_ctl(clk_ctl),.clk_rd(clk_rd),.clk_em(clk_em),.clk_seed(clk_seed),.clk_hash(clk_hash),.rst_n(rst_n),.rst_regions(rst_regions),.cfg_layer(cfg_layer),.cfg_rank(cfg_rank),.win_valid(win_valid),.win_slot(win_slot),.win_ids(win_ids),.hq_valid(ref_hq_valid),.hq_atom(ref_hq_atom),.hq_len(ref_hq_len),.hq_tag(ref_hq_tag),.hr_valid(hr_valid),.hr_slot(hr_slot),.hr_tag(hr_tag),.hr_tag_w(hr_tag_w),.hr_idx(hr_idx),.win_valid_c(win_valid_c),.hr_idx_w(hr_idx_w),.hr_data(hr_data ^ ((mutate != 0 && hr_valid) ? 256'd1 : 256'd0)),.o_valid(ref_o_valid),.o_col(ref_o_col),.o_beat(ref_o_beat),.o_slot(ref_o_slot),.o_data(ref_o_data),.st_valid(ref_st_valid),.st_slot(ref_st_slot),.st_bad(ref_st_bad),.fault(ref_fault));
always @(negedge clk) if (rst_n) begin
 checks <= checks+1;
 if ({hq_valid,hq_atom,hq_len,hq_tag,o_valid,o_col,o_beat,o_slot,o_data,st_valid,st_slot,st_bad,fault} !== {ref_hq_valid,ref_hq_atom,ref_hq_len,ref_hq_tag,ref_o_valid,ref_o_col,ref_o_beat,ref_o_slot,ref_o_data,ref_st_valid,ref_st_slot,ref_st_bad,ref_fault})
  $fatal(1,"RA640_INACTIVE_MITER mismatch cycle %0d mutant %0d",checks,mutate);
end
final begin if(checks==0) $error("RA640_INACTIVE_MITER no checks"); else $display("RA640_INACTIVE_MITER PASS cycles %0d mutant %0d",checks,mutate); end
endmodule
bind ot_s81_engram_lookup_ra640 ot_ra640_inactive_miter #(.RETURN_AGE(RETURN_AGE),.ROWSTRIPE(ROWSTRIPE),.NR(NR),.CPR(CPR),.NSLOT(NSLOT),.ABW(ABW),.BASE(BASE),.PIPE(PIPE),.CRCMAT(CRCMAT),.SLW(SLW)) check_inactive (.clk(clk),.clk_ctl(clk_ctl),.clk_rd(clk_rd),.clk_em(clk_em),.clk_seed(clk_seed),.clk_hash(clk_hash),.rst_n(rst_n),.rst_regions(rst_regions),.cfg_layer(cfg_layer),.cfg_rank(cfg_rank),.win_valid(win_valid),.win_slot(win_slot),.win_ids(win_ids),.hq_valid(hq_valid),.hq_atom(hq_atom),.hq_len(hq_len),.hq_tag(hq_tag),.hr_valid(hr_valid),.hr_slot(hr_slot),.hr_tag(hr_tag),.hr_tag_w(hr_tag_w),.hr_idx(hr_idx),.win_valid_c(win_valid_c),.hr_idx_w(hr_idx_w),.hr_data(hr_data),.o_valid(o_valid),.o_col(o_col),.o_beat(o_beat),.o_slot(o_slot),.o_data(o_data),.st_valid(st_valid),.st_slot(st_slot),.st_bad(st_bad),.fault(fault));
