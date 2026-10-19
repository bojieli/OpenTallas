`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// KV ingest engine: GPU-prefilled KV -> the decode die's HBM KV layout.
//
// Spec: docs/ARCH_SPEC_PREFILL.md section 6.  Prefill runs on GPUs; their KV
// arrives over RDMA (NIC -> PCIe peer-to-peer write into this engine's window,
// no host-memory bounce) as a stream of 512-bit beats, and is placed in HBM
// exactly where the decode core reads it.  The host posts one 256-bit
// DESCRIPTOR per segment; the payload beats of the segments follow in
// descriptor order, each segment starting on a beat boundary.
//
// QKV (Qwen3-8B; tools/hdc_program.py Layout.k_elem / v_elem at FP8, one byte
//   per element, HBM byte = element index): one descriptor = one layer's
//   16-position block (one K tile per KV head).  Payload: the block's K then
//   its V in the serving engine's page order [t][head][d] (vLLM FlashAttention
//   NHD, block_size 16), positions t_lo .. t_hi-1 only, as FP32, BF16 or FP8
//   E4M3 elements (16 / 32 / 64 per beat).  FP32 / BF16 are rounded by the
//   golden's to_fp8 (ot_hdc_ingest_fp8q); FP8 passes through.  K is
//   CORNER-TURNED into position tiles (word d of a head's tile holds positions
//   t = 0 .. 15 of dimension d; sector s = words 2s, 2s+1); V rows stay
//   position-major per head.  RMW: lanes t < t_lo are resident (a turn appended
//   mid-tile) and are read back from HBM first; other lanes outside
//   [t_lo, t_hi) are written as 0.  Two block slots: block n+1's payload fills
//   one while block n drains, so a BF16 stream runs at one beat a cycle.
// ROWS (V4.1 compressed KV rows 288 B, window rows 528 B in 17-sector slots,
//   any row stream): row r of RB bytes -> PITCH sectors, zero padded.  Rows go
//   in groups of 16: group g belongs to this die when g mod NDIE = DIE (the
//   tensor group's split); the die's groups interleave over its NS stacks
//   (stack gd mod NS, gd = g / NDIE) and each stack packs its groups densely
//   (local row 16 (gd / NS) + r mod 16).  RING > 0 (window rows): row r ->
//   slot r mod RING, every die (no split, no stacks).
// IKEY (V4.1 index keys, 68 B on the wire: 64 B of E2M1 codes then 4 UE8M0
//   scales): the index-key stream's lossless super-block layout
//   (rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv): per stack, 1,024-key super-blocks
//   of 17 x 4 KB blocks -- block 0 the keys' scales (4 B each), blocks 1..16 the
//   codes of 64 keys each; the die / stack split in 16-key groups as ROWS.
//   Keys come in whole 16-key groups (the sender pads the last).
// RAW: N sectors to consecutive addresses (compressor tail state, anything).
//
// Descriptor (256 bits):
//   [3:0] mode  [5:4] fmt (QKV: 0 FP32, 1 BF16, 2 FP8)  [6] rmw  [7] fence
//   [15:8] tag  a0 [47:16]  a1 [79:48]  a2 [111:80]  a3 [143:112]
//   n0 [167:144]  n1 [183:168]  n2 [199:184]  n4 [219:216]  n5 [231:224]
//   n6 [236:232]  nb [255:240] (stream modes: payload beats of the segment)
//   QKV : a0 K base, a1 V base, a2 K head stride, a3 V head stride (sectors);
//         n1 log2 head_dim (4 .. log2 HDMAX), n4 KV heads, n5 t_lo, n6 t_hi
//   ROWS: a0 base, a1 stack stride, a2 row pitch (sectors, <= 31), a3 RING;
//         n0 first global row, n1 row bytes, n2 rows, n4 log2 NDIE, n5 DIE,
//         n6 log2 NS
//   IKEY: a0 base, a1 stack stride; n0 first key, n2 keys, n4 / n5 / n6 as ROWS
//   RAW : a0 base; n0 sectors
//
// Write port: one 32-B sector a cycle (valid/ready); the in-order read port
// serves the RMW preload.  `done_v` pulses with the tag once a fenced
// descriptor's last sector has been accepted.  Flow control against the decode
// streams is the arbiter's (ot_hdc_ingest_arb); this engine back-pressures its
// payload only when its buffers are full.  The block banks are flops here and
// SRAM macros on silicon (per slot 16 lanes x KVHMAX x HDMAX bytes, K and V).
// ---------------------------------------------------------------------------
`ifdef OT_S81_SH_S10B
`define OT_SR_INC st_row_inc
`define OT_SL_DEC st_left_dec
`else
`define OT_SR_INC st_row + 1
`define OT_SL_DEC st_left - 1
`endif
module ot_hdc_kv_ingest #(
    parameter integer AW     = 32,        // sector address bits
    parameter integer HDMAX  = 128,       // largest head_dim (QKV), a power of two >= 16
    parameter integer KVHMAX = 8,         // most KV heads per block (QKV), a power of two <= 16
    parameter integer DQ     = 4,         // descriptor queue depth (a power of two)
    // sys-takeover 2026-10-09 (dsfd_host_native / hfd_host_ingest TT -194: qi_slot -> sd[qi_slot] -> granule walk ->
    // bk / bv write decode, 43-45 levels; st_d -> stream address arithmetic -> request FIFO, 42 levels).  Both opt-in,
    // defaults = the original:
    //   QKV   = 0: the QKV path is absent (a QKV descriptor is never dispatched; the host wrappers with QKV_EN = 0
    //           already fail it closed before the engine), so the QKV walk / banks / drain synthesise away.
    //   APIPE = 1: the stream path's per-row address terms (ROWS row address, ownership, IKEY code / scale bases) are
    //           registered: one bubble edge after every row / key / segment start before its first sector.
    //   APIPE = 2 (sys-takeover 2026-10-09, hostnative_pipe_a-25ce04993 TT -47: st_d -> address arithmetic -> ap_* still
    //           41-42 levels; w_fire -> n_sectors 33 levels): the address terms in TWO registered stages (ownership /
    //           group / stack / local / base first, then the pitch product and the IKEY sums: two bubble edges a row);
    //           n_sectors counts a REGISTERED write fire and done_v / done_tag leave one edge later, so every done word
    //           still carries the count that includes its own last sector.
    //   APIPE = 3 (sys-takeover 2026-10-10, hing_pipec_a TT -114: st_d -> s_stk * stride -> ap1_rbase 31 levels): one
    //           more stage in front (ap0_*: group / die / stack / local decomposition and the descriptor fields), then
    //           ap1_rbase = base + stack * stride, then the pitch product / IKEY sums: three bubble edges a row.
    //   APIPE = 4 (S81U-SEQ3 2026-10-17, dsdv_sh_lk gate 8940e10e9: ap1_local -> ap1_local * ap1_pitch -> ap_raddr 26
    //           levels ~922 ps): as 3, with the local * pitch product registered in stage A1 (ap1_lp, captured with
    //           ap1_local / ap1_pitch under the same enable, so ap1_lp == ap1_local * ap1_pitch whenever read) and stage B
    //           = ap1_rbase + ap1_lp.  Same three bubble edges a row and the same values as APIPE 3, edge for edge.
    //   APIPE = 5 (S81U-SEQ4 2026-10-17, dsdv_sh_lk gate4 df8031f2c: ap0_stk * ap0_stride + base -> ap1_rbase TT -70 ps):
    //           as 4, with the stack x stride partial products formed in stage A0 (ap0_pp{0,1,2} = stride << k when
    //           stack bit k is set and the segment is unringed, captured with the other ap0 fields), so stage A1 is a
    //           four-operand add ap1_rbase = base + pp0 + pp1 + pp2 (= base + stk * stride mod 2^32, stk < 8).  Same
    //           bubble edges and values as APIPE 4, edge for edge.
    //   APIPE = 8 (S81-SAFE-FIX/SH 2026-10-19, dsdv_sh_lk route lint: ap1_gs -> a2_blk + IKEY offsets -> ap_kcode 22
    //           levels / 775-787 ps, over the 600-ps stage rule): as 7 with stage B split in two.  B0 (apb_*) registers
    //           the block base a2_blk = rbase + sb * 2176, the IKEY code / scale offsets (bit-disjoint fields: no carry
    //           chain) and a2_raddr; B adds them (two-operand adds).  One more bubble edge a row (four), same values.
    //   APIPE = 10 (S81-SHLK s10 2026-10-19, dsdv_sh_lk_sr9 gate TT -252/-271 ps, all worst paths ra_rpc -> 8 full
    //           512-b realigner copies (~1,000 loads a pointer bit) -> sc_acc / ox write data; textbook ap0_pitch ->
    //           ap1_lp 26 levels 884 ps): as 9 plus (a) STREAM PIPE: the realigner head is no longer formed in the pop
    //           cycle.  Stage P (registered at the pop edge) captures the 40-byte window of the 256-byte ring that holds
    //           the head (32:1 select of 8-byte ring granules by the pointer's granule index, 10 kept pointer copies,
    //           32 output bits a copy) with the fine byte offset, write address and data kind; stage O forms the head by
    //           an 8:1 byte select (8 kept fine-offset copies), masks / substitutes the IKEY scales, writes sc_acc and
    //           enters a 4-entry output FIFO that drives the write port (registered head).  Pops are credit-issued
    //           against the FIFO (no w_rdy in the pop cone).  Every stream sector reaches the write port 2 edges later;
    //           rate 1 sector/edge unchanged.  A fenced segment's done enters a completion queue 2 edges after its
    //           APIPE 2 done edge, with the cumulative count of stream writes issued up to it, and leaves when that
    //           many sectors have been accepted at the write port (so without write-port stalls done is uniformly +2
    //           edges, and its count is the segment's exact cumulative count even when the fabric stalls).  busy
    //           covers the pipe; the next segment dispatches as before (the pipe keeps order).  (b) ap1_lp = local *
    //           pitch[2:0] and ap1_lph = local * pitch[4:3] (two short products), summed with rbase in stage X
    //           (three-operand add): no edge change.  Requires QKV = 0 (stream-only engine).
    parameter integer QKV    = 1,
    parameter integer APIPE  = 0,
    // QPIPE = 1 (qwen-1010/c 2026-10-10; 0 = unchanged): qfd_io_host preroute -1.2 .. -2.3 ns at clk_i (135 k of 139 k
    // endpoints): the QKV banks bk / bv (2 x 512 x 128 b of flops) were written through four computed-index 512-entry
    // decodes and read through 512:1 x 128 b muxes, behind sd[slot] field muxes and the beat's FP8 quantisers in the same
    // cycle.  QPIPE 1 restructures the QKV path (write-only: an rmw descriptor must be failed closed upstream; the
    // preload path is absent):
    //   * the slot's descriptor fields are decoded into registers at dispatch (input side) / drain start (drain side);
    //   * input: beat + granule walk registered (I0), FP8 codes + lane / word indices registered (I1), bank write (I2):
    //     +2 edges, one beat a cycle (the walk recurrence reads registered fields only);
    //   * banks per position lane (16 x 2 slots x WPL words): the write decode is 32 entries a lane;
    //   * drain: per-lane 32:1 reads registered (E1; K keeps the two addressed bytes a lane), then the 16:1 lane select /
    //     sector assembly registered into a 4-entry output FIFO (E2): +2 edges, credit-issued, one sector a cycle.
    //   Completion (done) leaves with the last sector at the write port, as before.  QMUT (bench mutants, must FAIL):
    //   1 = K granules written to lane t ^ 1; 2 = the drain loads the OTHER slot's (stale) descriptor fields.
    parameter integer NATIVE_ROWS=0, // Qwen merged native token-row K/V map, QPIPE2 only
    parameter integer QPIPE  = 0,
    parameter integer QMUT   = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              d_v,
    output wire              d_rdy,
    input  wire [255:0]      d_data,
    input  wire              in_v,
    output wire              in_rdy,
    input  wire [511:0]      in_data,
    output wire              w_v,
    input  wire              w_rdy,
    output wire [AW-1:0]     w_addr,
    output wire [255:0]      w_data,
    output wire              r_v,
    input  wire              r_rdy,
    output wire [AW-1:0]     r_addr,
    input  wire              rd_v,
    input  wire [255:0]      rd_data,
    output wire              done_v,
    output wire [7:0]        done_tag,
    output wire              busy,
    output wire [31:0]       n_sectors,
    output reg  [31:0]       n_beats
);
    localparam [3:0] M_RAW = 4'd0, M_QKV = 4'd1, M_ROWS = 4'd2, M_IKEY = 4'd3;
    localparam integer BB  = KVHMAX * HDMAX;       // bytes per position lane per slot
    localparam integer WPL = BB / 16;              // 16-byte words per lane per slot (a power of two)
    localparam integer LWP = (WPL > 1) ? $clog2(WPL) : 1;
    localparam integer NBW = 2 * 16 * WPL;         // words per bank (2 slots x 16 lanes)
    // QPIPE 2 macro corner-turn applies at the Qwen die geometry (16 words a lane per slot); other geometries keep QPIPE 1
    initial if(NATIVE_ROWS&&(QPIPE<2||HDMAX!=128||KVHMAX!=2))
        $fatal(1,"native ingest requires full32-macro QPIPE2 provider; descriptor may use1/2heads");
    localparam integer QP2 = (QPIPE >= 2 && BB == 256) ? 1 : 0;

    // -- descriptor queue ---------------------------------------------------------
    localparam integer LDQ = $clog2(DQ);
    reg [255:0] dq [0:DQ-1];
    reg [LDQ:0] dq_n;
    reg [LDQ-1:0] dq_rd, dq_wr;
`ifdef OT_S81_SH_S10B
    // S81-SHLK s10b (2026-10-19, s10 mapped netlist: dq_rd[0] drove 794 read-mux loads into st_d / st_left / st_row):
    // DQC kept copies of the read pointer, loaded with dq_rd on the same edge; copy k selects head bits 8k .. 8k+7
    // (~24 mux loads a copy bit).  Same head, same edge.
    localparam integer DQC = 32;
    (* keep *) reg [LDQ*DQC-1:0] dq_rdc;
    wire [255:0] dh;
    genvar dqs;
    for (dqs = 0; dqs < DQC; dqs = dqs + 1) begin : g_dqc
        wire [255:0] dqrow = dq[dq_rdc[LDQ*dqs +: LDQ]];
        assign dh[8*dqs +: 8] = dqrow[8*dqs +: 8];
    end
`else
    wire [255:0] dh = dq[dq_rd];
`endif
    wire dh_v = dq_n != 0;
    wire [3:0] dh_mode = dh[3:0];
    assign d_rdy = dq_n < DQ;

    // =============================================================================
    // QKV path: two block slots; per slot 16 lanes (positions) of WPL 16-byte words
    // for K and V.  Word w of lane t holds bytes 16 w .. 16 w + 15 of that
    // position's [head][d] row, so a granule (16 consecutive d of one head) is one
    // word write and every read is whole words: the banks map onto SRAM macros.
    // =============================================================================
    reg [127:0] bk [0:NBW-1];
    reg [127:0] bv [0:NBW-1];
    function automatic [31:0] bw_idx(input slot, input [3:0] lane, input [15:0] word);
        bw_idx = ((slot ? 32'd16 : 32'd0) + lane) * WPL + (word & (WPL - 1));
    endfunction
    // word of (head g, dimension d) for head_dim 2^lhd (lhd >= 4)
    function automatic [15:0] hw_word(input [7:0] g, input [3:0] lhd, input [15:0] d);
        hw_word = ({8'd0, g} << (lhd - 4'd4)) + (d >> 4);
    endfunction
    reg [255:0] sd [0:1];                  // each slot's descriptor
    reg [1:0]   s_full;                    // payload complete, not yet drained
    reg [1:0]   s_pre;                     // RMW preload outstanding
    // ---- input side
    reg         qi_act, qi_slot;
    reg         qi_v;                      // 0: K payload, 1: V payload
    reg  [4:0]  qi_t;
    reg  [7:0]  qi_g;
    reg  [15:0] qi_d;
    wire [255:0] qd = sd[qi_slot];
    reg  [1:0]  qf_fmt; reg [3:0] qf_lhd; reg [15:0] qf_hd; reg [7:0] qf_kvh; reg [4:0] qf_tlo, qf_thi;   // QPIPE
    wire [1:0]  q_fmt = (QPIPE != 0) ? qf_fmt : qd[5:4];
    wire [3:0]  q_lhd = (QPIPE != 0) ? qf_lhd : qd[171:168];
    wire [15:0] q_hd  = (QPIPE != 0) ? qf_hd : 16'd1 << q_lhd;
    wire [7:0]  q_kvh = (QPIPE != 0) ? qf_kvh : {4'd0, qd[219:216]};
    wire [4:0]  q_tlo = (QPIPE != 0) ? qf_tlo : qd[228:224];
    wire [4:0]  q_thi = (QPIPE != 0) ? qf_thi : qd[236:232];
    wire [2:0]  q_gpb = (q_fmt == 2'd0) ? 3'd1 : (q_fmt == 2'd1) ? 3'd2 : 3'd4;   // granules / beat
    // the beat's FP8 codes (FP32: 16, BF16: 32, FP8: 64 elements)
    wire [7:0] cv [0:63];
    genvar ge;
    generate
        for (ge = 0; ge < 64; ge = ge + 1) begin : g_cv
            wire [7:0] c32, cbf;
            if (ge < 16) begin : g32
                ot_hdc_ingest_fp8q u_q32 (.f(in_data[ge*32 +: 32]), .q(c32));
            end else begin : g32z
                assign c32 = 8'd0;
            end
            if (ge < 32) begin : gbf
                ot_hdc_ingest_fp8q u_qbf (.f({in_data[ge*16 +: 16], 16'd0}), .q(cbf));
            end else begin : gbfz
                assign cbf = 8'd0;
            end
            assign cv[ge] = (q_fmt == 2'd0) ? c32 : (q_fmt == 2'd1) ? cbf : in_data[ge*8 +: 8];
        end
    endgenerate
    // the granule walk: granule i of this beat is (t, g, d) = the walk + i granules
    reg  [4:0]  gw_t [0:4];
    reg  [7:0]  gw_g [0:4];
    reg  [15:0] gw_d [0:4];
    reg         gw_v [0:4];
    reg         gw_end [0:4];
    integer gi;
    always @* begin
        gw_t[0] = qi_t; gw_g[0] = qi_g; gw_d[0] = qi_d; gw_v[0] = qi_v; gw_end[0] = 1'b0;
        for (gi = 0; gi < 4; gi = gi + 1) begin
            gw_t[gi+1] = gw_t[gi]; gw_g[gi+1] = gw_g[gi]; gw_d[gi+1] = gw_d[gi] + 16'd16;
            gw_v[gi+1] = gw_v[gi]; gw_end[gi+1] = gw_end[gi];
            if (gw_d[gi] + 16'd16 >= q_hd) begin
                gw_d[gi+1] = 16'd0;
                gw_g[gi+1] = gw_g[gi] + 8'd1;
                if (gw_g[gi] + 8'd1 >= q_kvh) begin
                    gw_g[gi+1] = 8'd0;
                    gw_t[gi+1] = gw_t[gi] + 5'd1;
                    if (gw_t[gi] + 5'd1 >= q_thi) begin
                        gw_t[gi+1] = q_tlo;
                        if (gw_v[gi]) gw_end[gi+1] = 1'b1;
                        gw_v[gi+1] = 1'b1;
                    end
                end
            end
        end
    end
    wire [3:0] g_use = {q_gpb[2] && !gw_end[3], q_gpb[2] && !gw_end[2], !q_gpb[0] && !gw_end[1], !gw_end[0]};
    wire q_beat = qi_act && in_v;                 // the QKV input takes a beat (in_rdy = qi_act)
    wire q_last = gw_end[q_gpb];

    // ---- drain side
    reg         qo_act, qo_slot, qo_v;
    reg  [7:0]  qo_g;
    reg  [15:0] qo_s;
    reg  [AW-1:0] qo_hb;                     // this head's tile / V block base
    wire [255:0] od_s = sd[qo_slot];
    reg  [255:0] of_d;                       // QPIPE: the draining slot's descriptor, registered at drain start
    wire [255:0] od = (QPIPE != 0) ? of_d : od_s;
    wire [3:0]  o_lhd = od[171:168];
    wire [15:0] o_hd  = 16'd1 << o_lhd;
    wire [7:0]  o_kvh = {4'd0, od[219:216]};
    wire [4:0]  o_tlo = od[228:224];
    wire [4:0]  o_thi = od[236:232];
    wire        o_rmw = (QPIPE != 0) ? 1'b0 : od[6];
    wire [15:0] o_spb = o_hd >> 1;           // sectors per head: 16 x hd bytes / 32
    wire [15:0] o_lane;
    genvar gl;
    generate
        for (gl = 0; gl < 16; gl = gl + 1) begin : g_lane
            assign o_lane[gl] = (gl >= o_tlo && gl < o_thi) || (o_rmw && gl < o_tlo);
        end
    endgenerate
    reg [255:0] q_sec;
    reg [127:0] o_w;
    reg [15:0]  o_by;
    reg [3:0]   o_t, o_b;
    integer ob, oh;
    always @* begin
        q_sec = 256'd0; o_w = 128'd0; o_by = 0; o_t = 0; o_b = 0;
        if (!qo_v) begin
            // K tile sector s: words d = 2s, 2s+1; lane l = position l.  Every lane
            // reads its word holding d = 2s, 2s+1 and gives two bytes
            o_b = {qo_s[2:0], 1'b0};
            for (ob = 0; ob < 16; ob = ob + 1) begin
                o_w = bk[bw_idx(qo_slot, ob[3:0], hw_word(qo_g, o_lhd, {qo_s[14:0], 1'b0}))];
                q_sec[ob*8 +: 8] = o_lane[ob] ? o_w[o_b*8 +: 8] : 8'd0;
                q_sec[(16+ob)*8 +: 8] = o_lane[ob] ? o_w[(o_b+1)*8 +: 8] : 8'd0;
            end
        end else begin
            // V block sector j: bytes 32 j .. 32 j + 31 of [t][d]: two 16-byte words
            for (oh = 0; oh < 2; oh = oh + 1) begin
                o_by = {qo_s[10:0], 5'd0} + oh * 16;
                o_t = o_by >> o_lhd;
                o_w = bv[bw_idx(qo_slot, o_t, hw_word(qo_g, o_lhd, o_by & (o_hd - 16'd1)))];
                q_sec[oh*128 +: 128] = o_lane[o_t] ? o_w : 128'd0;
            end
        end
    end
    wire q_wv = qo_act && !s_pre[qo_slot];
    wire qp_room;                            // QPIPE: an output-FIFO credit for a sector issued now
    wire q_iss = (QPIPE != 0) ? (qo_act && qp_room) : (q_wv && w_rdy);
    wire q_hlast = qo_s + 16'd1 >= o_spb;
    wire q_wlast = qo_v && (qo_g + 8'd1 >= o_kvh) && q_hlast;

    // ---- RMW preload: issue one read per sector of the slot's K tiles and V
    // blocks; scatter the returns' resident lanes (t < t_lo)
    reg         pr_act, pr_slot, pr_v;
    reg  [7:0]  pr_g;
    reg  [15:0] pr_s;
    reg  [AW-1:0] pr_hb;
    reg  [15:0] pr_out;                       // reads issued, not yet returned
    reg         pt_v;
    reg  [7:0]  pt_g;
    reg  [15:0] pt_s;
    wire [255:0] pd = sd[pr_slot];
    wire [3:0]  p_lhd = pd[171:168];
    wire [15:0] p_spb = (16'd1 << p_lhd) >> 1;
    wire [7:0]  p_kvh = {4'd0, pd[219:216]};
    wire [4:0]  p_tlo = pd[228:224];
    assign r_v = pr_act;
    assign r_addr = pr_hb + pr_s;
    wire pr_hlast = pr_s + 16'd1 >= p_spb;
    wire pr_last = pr_v && (pr_g + 8'd1 >= p_kvh) && pr_hlast;
    wire pt_hlast = pt_s + 16'd1 >= p_spb;

    // =============================================================================
    // Stream path (RAW / ROWS / IKEY): byte realigner + row walk
    // =============================================================================
    reg [255:0] ra [0:7];                      // 8 words of 32 B; a beat fills 2
    reg [8:0]   ra_n;                          // bytes held, 0 .. 256
    reg [7:0]   ra_rp;                         // head byte (mod 256)
    reg [2:0]   ra_wp;
    wire [2:0]  ra_w0 = ra_rp[7:5];
    wire [2:0]  ra_w1 = ra_w0 + 3'd1;          // mod 8 (a named 3-b net: some simulators widen an index sum)
    wire [2:0]  ra_wq = ra_wp + 3'd1;
    wire [255:0] ra_head;                      // the next 32 bytes
    // APIPE >= 7 (S81-SHLK 2026-10-18, dsdv_sh_lk route ef442ffba: u_eng.ra_rp[5] -> word select + byte shift of all 512
    // bits -> ox_w_q / sc_acc TT -22.4, 11 endpoints): RAC = 8 kept copies of ra_rp, loaded with it on every edge; copy
    // s drives the select / shift of head bits [32 s +: 32] only.  Same value, same edge: no cycle or value change.
    localparam integer SP  = (APIPE >= 10) ? 1 : 0;   // APIPE 10: stream pipe (see the parameter note)
    localparam integer RAC = (APIPE >= 10) ? 10 : (APIPE >= 7) ? 8 : 1;
    (* keep *) reg [8*RAC-1:0] ra_rpc;           // RAC = 1: unused (the original single-pointer realigner below)
    if (SP != 0) begin : g_ra0
        assign ra_head = 256'd0;                // APIPE 10: the head is formed in stage O (g_sp)
    end else if (RAC > 1) begin : g_rac
        genvar ras;
        for (ras = 0; ras < 8; ras = ras + 1) begin : g_rah
            wire [7:0]   rp = ra_rpc[8 * ras +: 8];
            wire [2:0]   w0 = rp[7:5];
            wire [2:0]   w1 = w0 + 3'd1;
            wire [511:0] pr = {ra[w1], ra[w0]};
            wire [511:0] sh = pr >> {rp[4:0], 3'b000};
            assign ra_head[32 * ras +: 32] = sh[32 * ras +: 32];
        end
    end else begin : g_ra1
        wire [511:0] ra_pair = {ra[ra_w1], ra[ra_w0]};
        wire [511:0] ra_sh = ra_pair >> {ra_rp[4:0], 3'b000};
        assign ra_head = ra_sh[255:0];
    end
    reg         st_act, st_pad;
    reg  [3:0]  st_mode;
    reg  [255:0] st_d;
    reg  [31:0] st_row;                         // global row / key; RAW: sector
    reg  [31:0] st_left;                        // rows / keys / sectors left
    reg  [15:0] st_rem;                         // bytes of the current row not yet consumed
    reg  [4:0]  st_sec;                         // output sector within the row
    reg  [2:0]  st_ph;                          // IKEY: 0, 1 code sectors, 2 scales, 3, 4 scale sectors
    reg  [15:0] st_beats;                       // payload beats not yet taken
    reg  [255:0] sc_acc [0:1];                  // IKEY: the 16-key group's scales
`ifdef OT_S81_SH_S10B
    // S81-SHLK s10b (2026-10-19, s10 textbook: st_row[0] -> st_row[31] 32-b ripple increment, 19 levels ~690 ps):
    // st_row / st_left step as lo 4 + hi 28 bits.  The lo nibble steps in the cycle; the hi word takes a REGISTERED
    // hi +- 1 (sr_hp1 / sl_hm1).  Those are loaded with the segment (s_disp) and otherwise refreshed by a two-edge
    // pipe (stage a: 14-b halves +- 1 and the half carry; stage b: combine) from the current hi.  A hi step needs
    // 16 lo steps, so after any hi change the refresh (2 edges) lands long before the next carry; after a load the
    // refresh holds one edge (sr_hold) so a carry on the 2nd edge still sees the loaded value.  Same values, same
    // edges as st_row + 1 / st_left - 1 (exact for all 32 bits, wrap included).
    reg  [27:0] sr_hp1, sl_hm1;
    reg  [13:0] sr_alo, sr_ahi, sl_alo, sl_ahi, sr_asrc, sl_asrc;
    reg         sr_ac, sl_ac, sr_hold;
    wire [31:0] st_row_inc  = {(st_row[3:0]  == 4'hf) ? sr_hp1 : st_row[31:4],  st_row[3:0]  + 4'd1};
    wire [31:0] st_left_dec = {(st_left[3:0] == 4'h0) ? sl_hm1 : st_left[31:4], st_left[3:0] - 4'd1};
`endif
    wire [1:0]  s_ldie = st_d[217:216];
    wire [7:0]  s_die  = st_d[231:224];
    wire [1:0]  s_lns  = st_d[233:232];
    wire [31:0] s_grp  = st_row >> 4;
    wire        s_mine = (s_ldie == 2'd0) || ((s_grp & ((32'd1 << s_ldie) - 32'd1)) == {24'd0, s_die});
    wire [31:0] s_gd   = s_grp >> s_ldie;
    wire [2:0]  s_stk  = s_gd[2:0] & ((3'd1 << s_lns) - 3'd1);
    wire [31:0] s_gs   = s_gd >> s_lns;
    wire [31:0] s_ring = st_d[143:112];
    wire [31:0] s_local = (s_ring != 0) ? (st_row & (s_ring - 32'd1)) : ((s_gs << 4) | (st_row & 32'd15));
    wire [31:0] s_rbase = st_d[47:16] + ((s_ring != 0) ? 32'd0 : s_stk * st_d[79:48]);
    wire [15:0] s_rb = st_d[183:168];
    wire [4:0]  s_pitch = st_d[84:80];
    wire [31:0] s_raddr = s_rbase + s_local * s_pitch;          // pitch <= 31: shifts and adds
    // IKEY: super-block sb = gs / 64 (17 x 128 sectors), group q = gs mod 64
    wire [31:0] k_sb = s_gs >> 6;
    wire [5:0]  k_q = s_gs[5:0];
    wire [31:0] k_blk = s_rbase + (k_sb << 11) + (k_sb << 7);
    wire [31:0] k_code = k_blk + ((32'd1 + {28'd0, k_q[5:2]}) << 7) + ({30'd0, k_q[1:0]} << 5) + ((st_row & 32'd15) << 1);
    wire [31:0] k_scal = k_blk + ({26'd0, k_q} << 1);
    // APIPE: per-row address terms registered (ap_ok = valid for the current st_row / segment)
    reg         ap_ok;
    reg  [31:0] ap_raddr, ap_kcode, ap_kscal;
    reg         ap_mine;
    wire [31:0] u_raddr = (APIPE != 0) ? ap_raddr : s_raddr;
    wire [31:0] u_kcode = (APIPE != 0) ? ap_kcode : k_code;
    wire [31:0] u_kscal = (APIPE != 0) ? ap_kscal : k_scal;
    wire        u_mine  = (APIPE != 0) ? ap_mine  : s_mine;
    wire        ap_go   = (APIPE == 0) || ap_ok || st_mode == M_RAW;
    // this cycle's stream step
    reg  [5:0]  st_pop;
    reg  [1:0]  st_kind;                        // APIPE 10: 0 head, 1 head masked to k_take bytes, 2 / 3 sc_acc[0 / 1]
    reg         st_wv, st_adv;
    reg  [255:0] st_wd;
    reg  [AW-1:0] st_wa;
`ifdef OT_S81_SH_S10C
    // S81-SHLK s10c (2026-10-19, s10b gate: st_ph -> p_wa 810 ps / 23 levels = mode/phase mux + 32-b add in one stage):
    // the stream address is carried into stage P as base + offset (both muxed here, no adder); stage O adds them
    // (p_wa = p_wb + p_wo) in parallel with the 8:1 head-byte select, before the output FIFO write.  Same value, same
    // edge as st_wa (no added cycle).  st_wa itself is still formed for the SP = 0 build.
    reg  [AW-1:0] st_wb, st_wo;
`endif
    wire [5:0]  k_take = (st_rem > 16'd32) ? 6'd32 : st_rem[5:0];
    always @* begin
        st_pop = 6'd0; st_wv = 1'b0; st_wd = 256'd0; st_wa = {AW{1'b0}}; st_adv = 1'b0; st_kind = 2'd0;
`ifdef OT_S81_SH_S10C
        st_wb = {AW{1'b0}}; st_wo = {AW{1'b0}};
        case (st_mode)
            M_RAW:  begin st_wb = st_d[47:16]; st_wo = st_row; end
            M_ROWS: begin st_wb = u_raddr; st_wo = {{(AW-5){1'b0}}, st_sec}; end
            M_IKEY: if (st_ph < 3'd2) begin st_wb = u_kcode; st_wo = {{(AW-3){1'b0}}, st_ph}; end
                    else begin st_wb = u_kscal; st_wo = {{(AW-1){1'b0}}, (st_ph == 3'd4)}; end
            default: ;
        endcase
`endif
        if (st_act && !st_pad && ap_go) begin
            case (st_mode)
                M_RAW: if (ra_n >= 9'd32) begin
                    st_pop = 6'd32; st_wv = 1'b1; st_wd = ra_head; st_wa = st_d[47:16] + st_row; st_adv = 1'b1;
                end
                M_ROWS: if (ra_n >= {3'd0, k_take}) begin
                    st_pop = k_take; st_adv = 1'b1; st_wv = u_mine;
                    st_wd = (k_take == 6'd32) ? ra_head : (ra_head & ~({256{1'b1}} << {k_take[4:0], 3'b000}));
                    st_kind = (k_take == 6'd32) ? 2'd0 : 2'd1;
                    st_wa = u_raddr + st_sec;
                end
                M_IKEY: begin
                    if (st_ph < 3'd2) begin
                        if (ra_n >= 9'd32) begin
                            st_pop = 6'd32; st_adv = 1'b1; st_wv = u_mine; st_wd = ra_head; st_wa = u_kcode + st_ph;
                        end
                    end else if (st_ph == 3'd2) begin
                        if (ra_n >= 9'd4) begin st_pop = 6'd4; st_adv = 1'b1; end
                    end else begin
                        st_adv = 1'b1; st_wv = u_mine; st_wd = sc_acc[st_ph[0] ? 0 : 1]; st_kind = st_ph[0] ? 2'd2 : 2'd3;
                        st_wa = u_kscal + (st_ph == 3'd4 ? 1 : 0);
                    end
                end
                default: ;
            endcase
        end
    end
    wire sp_room;                               // APIPE 10: output FIFO credit (g_sp); 1 otherwise
    wire st_go = st_adv && (!st_wv || ((SP != 0) ? sp_room : w_rdy));
    // ROWS: the row ends with its last output sector (this die) or its last bytes (dropped)
    wire st_row_end = u_mine ? (st_sec + 5'd1 >= s_pitch) : (st_rem <= 16'd32);

    // =============================================================================
    // Ports
    // =============================================================================
    // the stream path runs only while the QKV path is idle, so they never contend
    wire          qp_wv;                     // QPIPE output FIFO head
    wire [AW-1:0] qp_wa;
    wire [255:0]  qp_wd;
    wire          qp_busy;                   // QPIPE: a beat / sector still in the input or drain pipeline
    wire          qk_wv = (QPIPE != 0) ? qp_wv : q_wv;
    wire          sp_wv;                     // APIPE 10: stream output FIFO head (g_sp)
    wire [AW-1:0] sp_wa;
    wire [255:0]  sp_wd;
    wire          sp_busy;                   // APIPE 10: a sector still in stage P or the output FIFO
    assign w_v    = qk_wv || ((SP != 0) ? sp_wv : st_wv);
    assign w_addr = qk_wv ? ((QPIPE != 0) ? qp_wa : (qo_hb + qo_s)) : ((SP != 0) ? sp_wa : st_wa);
    assign w_data = qk_wv ? ((QPIPE != 0) ? qp_wd : q_sec) : ((SP != 0) ? sp_wd : st_wd);
    wire w_fire = w_v && w_rdy;
    // done / sector-count outputs (APIPE 2: registered write fire, done one edge later)
    reg         done_r, done_q, wf_q;
    reg  [7:0]  dtag_r, dtag_q;
    reg  [31:0] nsec_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin done_q <= 1'b0; dtag_q <= 0; wf_q <= 1'b0; end
`ifdef OT_ING_MUT_NSECLAG
        else begin done_q <= done_r; dtag_q <= dtag_r; wf_q <= w_fire; end   // (mutant applied below: done not delayed)
`else
        else begin done_q <= done_r; dtag_q <= dtag_r; wf_q <= w_fire; end
`endif
`ifdef OT_ING_MUT_NSECLAG
    assign done_v = done_r; assign done_tag = dtag_r;                       // mutant: done leaves before its last count
`else
    // APIPE 10: done (with its sector count) from the stream pipe's completion queue (g_sp)
    wire        sp_done_v;
    wire [7:0]  sp_done_tag;
    wire [31:0] sp_done_cnt;
    assign done_v = (SP != 0) ? sp_done_v : (APIPE >= 2) ? done_q : done_r;
    assign done_tag = (SP != 0) ? sp_done_tag : (APIPE >= 2) ? dtag_q : dtag_r;
`endif
    assign n_sectors = (SP != 0) ? sp_done_cnt : nsec_r;   // read with done_v (the completion word's count)
    wire ra_push = st_act && !st_pad && in_v && (ra_n <= 9'd192) && (st_beats != 0);
    wire pad_take = st_act && st_pad && in_v && (st_beats != 0);
    assign in_rdy = qi_act || (st_act && (st_pad ? (st_beats != 0) : ((ra_n <= 9'd192) && (st_beats != 0))));
    assign busy = dh_v || qi_act || qo_act || pr_act || (s_pre != 0) || st_act || (s_full != 0) || qp_busy || sp_busy;

    // dispatch: a QKV descriptor takes the other slot once it is drained (and an
    // RMW descriptor waits for any preload in flight); a stream descriptor starts
    // when the QKV path is idle
    wire nslot = ~qi_slot;
    reg  [1:0] s_fill;                     // QPIPE: slot dispatched, its last bank write not yet landed
    wire q_disp = (QKV != 0) && dh_v && dh_mode == M_QKV && !qi_act && !st_act && !s_full[nslot] && !s_pre[nslot]
                  && !(qo_act && qo_slot == nslot) && (!dh[6] || (!pr_act && pr_out == 0 && s_pre == 2'b00))
                  && !((QPIPE != 0) && s_fill[nslot]);
    wire s_disp = dh_v && dh_mode != M_QKV && !qi_act && !st_act && !qo_act && s_full == 2'b00 && !pr_act
                  && s_pre == 2'b00 && !qp_busy;
    wire       qp_fset;                    // QPIPE: the slot's last bank write lands (s_full)
    wire       qp_fslot;
    wire       qp_dv;                      // QPIPE: a fenced block's last sector left the write port
    wire [7:0] qp_dtag;
    wire d_pop = q_disp || s_disp;

    // -- sequential ---------------------------------------------------------------
    integer bi;
    reg [127:0] g_word, r_word;
    reg [31:0]  r_idx;
    reg [15:0]  r_by;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dq_n <= 0; dq_rd <= 0; dq_wr <= 0;
`ifdef OT_S81_SH_S10B
            dq_rdc <= '0;
`endif
            s_full <= 2'b00; s_pre <= 2'b00; s_fill <= 2'b00; qi_act <= 1'b0; qi_slot <= 1'b0; qo_act <= 1'b0; qo_slot <= 1'b0;
            pr_act <= 1'b0; pr_out <= 0; st_act <= 1'b0; st_pad <= 1'b0; ra_n <= 0; ra_rp <= 0; if (RAC > 1) ra_rpc <= 0; ra_wp <= 0;
            done_r <= 1'b0; dtag_r <= 0; nsec_r <= 0; n_beats <= 0;
            qi_t <= 0; qi_g <= 0; qi_d <= 0; qi_v <= 1'b0; qo_v <= 1'b0; qo_g <= 0; qo_s <= 0; qo_hb <= 0;
            pr_v <= 1'b0; pr_g <= 0; pr_s <= 0; pr_hb <= 0; pr_slot <= 1'b0;
            pt_v <= 1'b0; pt_g <= 0; pt_s <= 0; st_ph <= 0; st_beats <= 0; st_row <= 0; st_left <= 0;
            st_rem <= 0; st_sec <= 0;
        end else begin
            done_r <= 1'b0;
            if (QPIPE != 0 && qp_dv) begin done_r <= 1'b1; dtag_r <= qp_dtag; end
            if ((APIPE >= 2) ? wf_q : w_fire) nsec_r <= nsec_r + 1;
            if (q_beat || ra_push || pad_take) n_beats <= n_beats + 1;
            // descriptor queue
            if (d_v && d_rdy) begin dq[dq_wr] <= d_data; dq_wr <= dq_wr + 1'b1; end
            if (d_pop) dq_rd <= dq_rd + 1'b1;
`ifdef OT_S81_SH_S10B
`ifdef OT_ING_MUT_DQC
            if (d_pop) for (int k = 1; k < DQC; k++) dq_rdc[LDQ*k +: LDQ] <= dq_rd + 1'b1;   // mutant: copy 0 stalls
`else
            if (d_pop) for (int k = 0; k < DQC; k++) dq_rdc[LDQ*k +: LDQ] <= dq_rd + 1'b1;
`endif
`endif
            dq_n <= dq_n + ((d_v && d_rdy) ? 1 : 0) - (d_pop ? 1 : 0);

            if (q_disp) begin
                qi_slot <= nslot; sd[nslot] <= dh; qi_act <= 1'b1;
                qi_t <= dh[228:224]; qi_g <= 0; qi_d <= 0; qi_v <= 1'b0;
                qf_fmt <= dh[5:4]; qf_lhd <= dh[171:168]; qf_hd <= 16'd1 << dh[171:168]; qf_kvh <= {4'd0, dh[219:216]};
                qf_tlo <= dh[228:224]; qf_thi <= dh[236:232];
                if (QPIPE != 0) s_fill[nslot] <= 1'b1;
                if (QPIPE == 0 && dh[6] && dh[228:224] != 5'd0) begin
                    s_pre[nslot] <= 1'b1;
                    pr_act <= 1'b1; pr_slot <= nslot; pr_v <= 1'b0; pr_g <= 0; pr_s <= 0; pr_hb <= dh[47:16];
                    pt_v <= 1'b0; pt_g <= 0; pt_s <= 0;
                end
            end
            if (s_disp) begin
                st_act <= 1'b1; st_pad <= 1'b0; st_mode <= dh_mode; st_d <= dh;
                st_row <= (dh_mode == M_RAW) ? 32'd0 : {8'd0, dh[167:144]};
                st_left <= (dh_mode == M_RAW) ? {8'd0, dh[167:144]} : {16'd0, dh[199:184]};
                st_rem <= dh[183:168]; st_sec <= 0; st_ph <= 0; st_beats <= dh[255:240];
            end

            // ---- QKV input: the beat's granules into the slot's lane banks
            if (q_beat && QPIPE == 0) begin
                for (gi = 0; gi < 4; gi = gi + 1)
                    if (g_use[gi]) begin
                        for (bi = 0; bi < 16; bi = bi + 1) g_word[bi*8 +: 8] = cv[gi*16 + bi];
                        if (!gw_v[gi]) bk[bw_idx(qi_slot, gw_t[gi][3:0], hw_word(gw_g[gi], q_lhd, gw_d[gi]))] <= g_word;
                        else           bv[bw_idx(qi_slot, gw_t[gi][3:0], hw_word(gw_g[gi], q_lhd, gw_d[gi]))] <= g_word;
                    end
            end
            if (q_beat) begin
                qi_t <= gw_t[q_gpb]; qi_g <= gw_g[q_gpb]; qi_d <= gw_d[q_gpb]; qi_v <= gw_v[q_gpb];
                if (q_last) begin qi_act <= 1'b0; if (QPIPE == 0) s_full[qi_slot] <= 1'b1; end
            end
            if (qi_act && q_tlo >= q_thi) begin                                                  // empty payload
                qi_act <= 1'b0; s_full[qi_slot] <= 1'b1; if (QPIPE != 0) s_fill[qi_slot] <= 1'b0;
            end
            if (QPIPE != 0 && qp_fset) begin s_full[qp_fslot] <= 1'b1; s_fill[qp_fslot] <= 1'b0; end

            // ---- RMW preload: issue, then scatter the returns
            if (pr_act && r_rdy) begin
                if (pr_hlast) begin
                    pr_s <= 0;
                    if (pr_g + 8'd1 >= p_kvh) begin
                        pr_g <= 0; pr_v <= 1'b1; pr_hb <= pd[79:48];
                    end else begin
                        pr_g <= pr_g + 8'd1; pr_hb <= pr_hb + (pr_v ? pd[143:112] : pd[111:80]);
                    end
                end else pr_s <= pr_s + 16'd1;
                if (pr_last) pr_act <= 1'b0;
            end
            pr_out <= pr_out + ((pr_act && r_rdy) ? 16'd1 : 16'd0) - (rd_v ? 16'd1 : 16'd0);
            if (rd_v) begin
                if (!pt_v) begin
                    // K: lane l's word holding d = 2s, 2s+1 takes sector bytes l and 16 + l
                    for (bi = 0; bi < 16; bi = bi + 1)
                        if (bi < p_tlo) begin
                            r_idx = bw_idx(pr_slot, bi[3:0], hw_word(pt_g, p_lhd, {pt_s[14:0], 1'b0}));
                            r_word = bk[r_idx];
                            r_word[{pt_s[2:0], 1'b0}*8 +: 8] = rd_data[bi*8 +: 8];
                            r_word[({pt_s[2:0], 1'b0}+1)*8 +: 8] = rd_data[(16+bi)*8 +: 8];
                            bk[r_idx] <= r_word;
                        end
                end else begin
                    // V: the sector's two 16-byte halves are two whole words
                    for (bi = 0; bi < 2; bi = bi + 1) begin
                        r_by = {pt_s[10:0], 5'd0} + bi * 16;
                        if ((r_by >> p_lhd) < p_tlo)
                            bv[bw_idx(pr_slot, r_by >> p_lhd, hw_word(pt_g, p_lhd, r_by & ((16'd1 << p_lhd) - 16'd1)))]
                                <= rd_data[bi*128 +: 128];
                    end
                end
                if (pt_hlast) begin
                    pt_s <= 0;
                    if (pt_g + 8'd1 >= p_kvh) begin
                        pt_g <= 0;
                        if (pt_v) s_pre[pr_slot] <= 1'b0;
                        pt_v <= 1'b1;
                    end else pt_g <= pt_g + 8'd1;
                end else pt_s <= pt_s + 16'd1;
            end

            // ---- QKV drain, in fill order
            if (!qo_act && s_full[~qo_slot]) begin
                qo_act <= 1'b1; qo_slot <= ~qo_slot; qo_v <= 1'b0; qo_g <= 0; qo_s <= 0;
                qo_hb <= sd[(QMUT == 2) ? qo_slot : ~qo_slot][47:16];
                of_d <= sd[(QMUT == 2) ? qo_slot : ~qo_slot];
            end
            if (q_iss) begin
                if (q_hlast) begin
                    qo_s <= 0;
                    if (qo_g + 8'd1 >= o_kvh) begin
                        qo_g <= 0; qo_v <= 1'b1; qo_hb <= od[79:48];
                    end else begin
                        qo_g <= qo_g + 8'd1; qo_hb <= qo_hb + (qo_v ? od[143:112] : od[111:80]);
                    end
                end else qo_s <= qo_s + 16'd1;
                if (q_wlast) begin
                    qo_act <= 1'b0; s_full[qo_slot] <= 1'b0;
                    if (QPIPE == 0 && od[7]) begin done_r <= 1'b1; dtag_r <= od[15:8]; end
                end
            end

            // ---- stream path
            if (ra_push) begin
                ra[ra_wp] <= in_data[255:0]; ra[ra_wq] <= in_data[511:256]; ra_wp <= ra_wp + 3'd2;
            end
            if (ra_push || pad_take) st_beats <= st_beats - 16'd1;
            if (st_pad) begin
                // the segment's last-beat padding (and any extra padding beats) is dropped
                ra_n <= 0; ra_rp <= 0; if (RAC > 1) ra_rpc <= 0; ra_wp <= 0;
                if (st_beats == 0 || (pad_take && st_beats == 16'd1)) begin
                    st_act <= 1'b0; st_pad <= 1'b0;
                    if (st_d[7]) begin done_r <= 1'b1; dtag_r <= st_d[15:8]; end
                end
            end else begin
                ra_n <= ra_n + (ra_push ? 9'd64 : 9'd0) - (st_go ? {3'd0, st_pop} : 9'd0);
                if (st_go) ra_rp <= ra_rp + {2'd0, st_pop};
`ifdef OT_ING_MUT_RAC
                if (st_go && RAC > 1) for (int k = 1; k < RAC; k++) ra_rpc[8 * k +: 8] <= ra_rp + {2'd0, st_pop};   // mutant: copy 0 stalls
`else
                if (st_go && RAC > 1) for (int k = 0; k < RAC; k++) ra_rpc[8 * k +: 8] <= ra_rp + {2'd0, st_pop};
`endif
            end
            if (st_go) begin
                case (st_mode)
                    M_RAW: begin
                        st_row <= `OT_SR_INC; st_left <= `OT_SL_DEC;
                        if (st_left == 32'd1) st_pad <= 1'b1;
                    end
                    M_ROWS: begin
                        st_rem <= st_rem - {10'd0, k_take};
                        if (!st_row_end) begin
                            if (u_mine) st_sec <= st_sec + 5'd1;
                        end else begin
                            st_sec <= 0; st_rem <= s_rb; st_row <= `OT_SR_INC; st_left <= `OT_SL_DEC;
                            if (st_left == 32'd1) st_pad <= 1'b1;
                        end
                    end
                    M_IKEY: begin
                        if (st_ph == 3'd2) begin
                            if (st_row[3:0] == 4'd15) st_ph <= 3'd3;
                            else begin st_ph <= 3'd0; st_row <= `OT_SR_INC; st_left <= `OT_SL_DEC; end
                        end else if (st_ph == 3'd4) begin
                            st_ph <= 3'd0; st_row <= `OT_SR_INC; st_left <= `OT_SL_DEC;
                            if (st_left == 32'd1) st_pad <= 1'b1;
                        end else st_ph <= st_ph + 3'd1;
                    end
                    default: ;
                endcase
            end
            if (st_act && !st_pad && st_left == 0 && !s_disp) st_pad <= 1'b1;   // an empty segment
        end
    end
`ifdef OT_S81_SH_S10B
    wire [31:0] st_row_ld  = (dh_mode == M_RAW) ? 32'd0 : {8'd0, dh[167:144]};
    wire [31:0] st_left_ld = (dh_mode == M_RAW) ? {8'd0, dh[167:144]} : {16'd0, dh[199:184]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sr_hp1 <= 28'd1; sl_hm1 <= {28{1'b1}}; sr_hold <= 1'b0;
            sr_alo <= 14'd1; sr_ahi <= 14'd1; sr_asrc <= 14'd0; sr_ac <= 1'b0;
            sl_alo <= {14{1'b1}}; sl_ahi <= {14{1'b1}}; sl_asrc <= 14'd0; sl_ac <= 1'b1;
        end else begin
            // stage a: halves of the current hi
            sr_alo <= st_row[17:4] + 14'd1;  sr_ac <= &st_row[17:4];        sr_ahi <= st_row[31:18] + 14'd1;  sr_asrc <= st_row[31:18];
            sl_alo <= st_left[17:4] - 14'd1; sl_ac <= (st_left[17:4] == 14'd0); sl_ahi <= st_left[31:18] - 14'd1; sl_asrc <= st_left[31:18];
            sr_hold <= s_disp;
            if (s_disp) begin
                sr_hp1 <= st_row_ld[31:4] + 28'd1;
                sl_hm1 <= st_left_ld[31:4] - 28'd1;
`ifdef OT_ING_MUT_HPHOLD
            end else begin                                              // mutant: the refresh overwrites a fresh load
`elsif OT_ING_MUT_HPREF
            end else if (1'b0) begin                                    // mutant: hi +- 1 only loaded, never refreshed
`else
            end else if (!sr_hold) begin
`endif
                sr_hp1 <= {sr_ac ? sr_ahi : sr_asrc, sr_alo};
                sl_hm1 <= {sl_ac ? sl_ahi : sl_asrc, sl_alo};
            end
        end
    end
`endif
    // IKEY scales (APIPE 10: written from stage O, one edge after the pop; read by stage O of the phase 3 / 4 pops,
    // which come at least one edge after the last scale pop, so the read always sees the group's 16 scales)
    wire        sc_we;
    wire [3:0]  sc_row;
    wire [31:0] sc_wd;
    always @(posedge clk)
        if (sc_we) begin
            if (sc_row[3]) sc_acc[1][sc_row[2:0] * 32 +: 32] <= sc_wd;
            else           sc_acc[0][sc_row[2:0] * 32 +: 32] <= sc_wd;
        end
    // APIPE: the address terms of the current row; invalidated whenever st_row / the segment can change
    wire ap_inval = s_disp || (st_go && (st_mode == M_ROWS ? st_row_end :
                                         st_mode == M_IKEY ? ((st_ph == 3'd2 && st_row[3:0] != 4'd15) || st_ph == 3'd4) : 1'b0));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ap_ok <= 1'b0;
`ifdef OT_ING_MUT_APSTALE
        else if (s_disp) ap_ok <= 1'b0;                    // mutant: stale row address kept across rows
`else
        else if (ap_inval) ap_ok <= 1'b0;
`endif
`ifdef OT_ING_MUT_APBSKIP
        else ap_ok <= (APIPE >= 2) ? (st_act && ap_ok1) : st_act;               // mutant: APIPE 8 stage B0 not waited for
`else
        else ap_ok <= (APIPE >= 8) ? (st_act && ap_okb) : (APIPE >= 2) ? (st_act && ap_ok1) : st_act;
`endif
    end
    // APIPE 2: stage A (ap1_*) registers the per-row decomposition, stage B (ap_*) the products / sums from it
    reg         ap_ok1;
    reg  [31:0] ap1_rbase, ap1_local, ap1_gs, ap1_row;
    reg  [4:0]  ap1_pitch;
    reg         ap1_mine;
    wire [31:0] a2_sb    = ap1_gs >> 6;
    wire [5:0]  a2_q     = ap1_gs[5:0];
    wire [31:0] a2_blk   = ap1_rbase + (a2_sb << 11) + (a2_sb << 7);
    reg  [31:0] ap1_lp, ap1_lph;
    wire [31:0] a2_raddr = (APIPE >= 10) ? ap1_rbase + ap1_lp + (ap1_lph << 3)
                         : (APIPE >= 4) ? ap1_rbase + ap1_lp : ap1_rbase + ap1_local * ap1_pitch;
    wire [31:0] a2_kcode = a2_blk + ((32'd1 + {28'd0, a2_q[5:2]}) << 7) + ({30'd0, a2_q[1:0]} << 5) + ((ap1_row & 32'd15) << 1);
    wire [31:0] a2_kscal = a2_blk + ({26'd0, a2_q} << 1);
    // APIPE 3: stage A0 (ap0_*) = the decomposition and descriptor fields; ap1_rbase = base + stack * stride from it
    reg         ap_ok0;
    reg  [31:0] ap0_base, ap0_stride, ap0_local, ap0_gs, ap0_row;
    reg  [2:0]  ap0_stk;
    reg  [4:0]  ap0_pitch;
    reg         ap0_mine, ap0_ringz;
    reg  [31:0] ap0_pp0, ap0_pp1, ap0_pp2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ap_ok0 <= 1'b0;
        else if (ap_inval) ap_ok0 <= 1'b0;
        else ap_ok0 <= st_act;
    end
    always @(posedge clk) if (!ap_ok0) begin
        ap0_base <= st_d[47:16]; ap0_stride <= st_d[79:48]; ap0_ringz <= (s_ring == 0); ap0_stk <= s_stk;
        ap0_local <= s_local; ap0_gs <= s_gs; ap0_row <= st_row; ap0_pitch <= s_pitch; ap0_mine <= s_mine;
        if (APIPE >= 5) begin
            ap0_pp0 <= (s_ring == 0 && s_stk[0]) ? st_d[79:48]        : 32'd0;
            ap0_pp1 <= (s_ring == 0 && s_stk[1]) ? st_d[79:48] << 1   : 32'd0;
            ap0_pp2 <= (s_ring == 0 && s_stk[2]) ? st_d[79:48] << 2   : 32'd0;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ap_ok1 <= 1'b0;
        else if (ap_inval) ap_ok1 <= 1'b0;
`ifdef OT_ING_MUT_AP0SKIP
        else ap_ok1 <= st_act;                                                     // mutant: stage A0 not waited for
`else
        else ap_ok1 <= (APIPE >= 3) ? (st_act && ap_ok0) : st_act;
`endif
    end
    always @(posedge clk) if (!ap_ok1) begin
        if (APIPE >= 3) begin
            ap1_rbase <= (APIPE >= 5) ? ap0_base + ap0_pp0 + ap0_pp1 + ap0_pp2
                                      : ap0_base + (ap0_ringz ? ap0_stk * ap0_stride : 32'd0); ap1_local <= ap0_local; ap1_gs <= ap0_gs;
            ap1_row <= ap0_row; ap1_pitch <= ap0_pitch; ap1_mine <= ap0_mine;
            if (APIPE >= 10) begin ap1_lp <= ap0_local * {29'd0, ap0_pitch[2:0]}; ap1_lph <= ap0_local * {30'd0, ap0_pitch[4:3]}; end
            else if (APIPE >= 4) ap1_lp <= ap0_local * ap0_pitch;
        end else begin
            ap1_rbase <= s_rbase; ap1_local <= s_local; ap1_gs <= s_gs; ap1_row <= st_row; ap1_pitch <= s_pitch; ap1_mine <= s_mine;
        end
    end
    // APIPE 9: split sb*2176 from the base addition. Each stage has one
    // two-operand add; the old ap1_gs -> apb_blk cone had two serial adds.
    // Same modulo32-bit addresses; one additional row-start bubble.
    reg ap_okx, apx_mine;
    reg [31:0] apx_stride, apx_base, apx_koff, apx_soff, apx_raddr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ap_okx <= 1'b0;
        else if (ap_inval) ap_okx <= 1'b0;
        else ap_okx <= st_act && ap_ok1;
    end
    always @(posedge clk) if (!ap_okx) begin
        apx_stride <= (a2_sb << 11) + (a2_sb << 7);
        apx_base <= ap1_rbase;
        apx_koff <= ((32'd1 + {28'd0, a2_q[5:2]}) << 7) + ({30'd0, a2_q[1:0]} << 5) + ((ap1_row & 32'd15) << 1);
        apx_soff <= {26'd0, a2_q} << 1;
        apx_raddr <= a2_raddr; apx_mine <= ap1_mine;
    end
    // APIPE 8: stage B0 (apb_*) = block base, IKEY offsets, row address; stage B = two-operand sums
    reg         ap_okb, apb_mine;
    reg  [31:0] apb_blk, apb_koff, apb_soff, apb_raddr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ap_okb <= 1'b0;
        else if (ap_inval) ap_okb <= 1'b0;
`ifdef OT_ING_MUT_APXSKIP
        else ap_okb <= st_act && ap_ok1;
`else
        else ap_okb <= st_act && ((APIPE >= 9) ? ap_okx : ap_ok1);
`endif
    end
    always @(posedge clk) if (!ap_okb) begin
        apb_blk  <= (APIPE >= 9) ? apx_base + apx_stride : a2_blk;
        apb_koff <= (APIPE >= 9) ? apx_koff : ((32'd1 + {28'd0, a2_q[5:2]}) << 7) + ({30'd0, a2_q[1:0]} << 5) + ((ap1_row & 32'd15) << 1);
        apb_soff <= (APIPE >= 9) ? apx_soff : ({26'd0, a2_q} << 1);
        apb_raddr <= (APIPE >= 9) ? apx_raddr : a2_raddr; apb_mine <= (APIPE >= 9) ? apx_mine : ap1_mine;
    end
    always @(posedge clk) if (!ap_ok) begin
        if (APIPE >= 8) begin ap_raddr <= apb_raddr; ap_kcode <= apb_blk + apb_koff; ap_kscal <= apb_blk + apb_soff; ap_mine <= apb_mine; end
        else if (APIPE >= 2) begin ap_raddr <= a2_raddr; ap_kcode <= a2_kcode; ap_kscal <= a2_kscal; ap_mine <= ap1_mine; end
        else begin ap_raddr <= s_raddr; ap_kcode <= k_code; ap_kscal <= k_scal; ap_mine <= s_mine; end
    end
    // =============================================================================
    // QPIPE QKV path (see the parameter): input I0 / I1 / bank write, per-lane banks, drain E1 / E2 into an output FIFO
    // =============================================================================
    localparam integer LBW = LWP + 1;                       // per-lane bank index {slot, word}
    // =============================================================================
    // APIPE 10 stream pipe (see the parameter note): stage P (pop edge) -> stage O -> 4-entry output FIFO
    // =============================================================================
    generate if (SP != 0) begin : g_sp
`ifndef SYNTHESIS
        initial if (QKV != 0 || QPIPE != 0 || AW != 32) $error("ot_hdc_kv_ingest: APIPE 10 stream pipe requires QKV = 0, QPIPE = 0, AW = 32");
`endif
        reg           p_wv, p_sc;
        reg  [1:0]    p_kind;
        reg  [5:0]    p_kt;
        reg  [3:0]    p_row;
`ifdef OT_S81_SH_S10C
        reg  [AW-1:0] p_wb, p_wo;
`ifdef OT_ING_MUT_S10CWA
        wire [AW-1:0] p_wa = p_wb | p_wo;      // mutant: base and offset OR-ed, not added
`else
        wire [AW-1:0] p_wa = p_wb + p_wo;      // stage O add (s10c)
`endif
`else
        reg  [AW-1:0] p_wa;
`endif
        reg  [319:0]  p_win;                   // ring bytes 8 * rp[7:3] .. + 39 (the head and its fine offset)
        (* keep *) reg [23:0] p_fo;            // 8 kept copies of the fine byte offset rp[2:0], 4 head bytes each
        // window granule g = ring granule (rp[7:3] + g) mod 32; ring granule k = ra[k / 4][64 (k mod 4) +: 64].
        // 10 slices of 32 window bits; slice s reads pointer copy s (32 one-hot select loads a copy).
        wire [319:0]  win;
        genvar gs, gb;
        for (gs = 0; gs < 10; gs = gs + 1) begin : g_ws
            localparam integer G = gs / 2;
            localparam integer H = gs % 2;
            wire [4:0] gi = ra_rpc[8 * gs + 3 +: 5];
            reg  [31:0] v;
            integer k;
            always @* begin
                v = 32'd0;
                for (k = 0; k < 32; k = k + 1)
                    if (gi == ((k + 32 - G) % 32)) v = v | ra[k / 4][64 * (k % 4) + 32 * H +: 32];
            end
            assign win[32 * gs +: 32] = v;
        end
        always @(posedge clk)
            if (st_go) begin
                p_win <= win; p_fo <= {8{ra_rpc[2:0]}}; p_kind <= st_kind; p_kt <= k_take; p_row <= st_row[3:0];
`ifdef OT_S81_SH_S10C
                p_wb <= st_wb; p_wo <= st_wo;
`else
                p_wa <= st_wa;
`endif
            end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin p_wv <= 1'b0; p_sc <= 1'b0; end
            else begin
                p_wv <= st_go && st_wv;
                p_sc <= st_go && st_mode == M_IKEY && st_ph == 3'd2;
            end
        // stage O: head byte b = window byte b + fine offset (8:1, fine-offset copy b / 4)
        wire [255:0] head;
        for (gb = 0; gb < 32; gb = gb + 1) begin : g_hb
            wire [2:0] fo = p_fo[3 * (gb / 4) +: 3];
            reg  [7:0] hb;
            integer j;
            always @* begin
                hb = 8'd0;
                for (j = 0; j < 8; j = j + 1) if (fo == j) hb = hb | p_win[8 * (gb + j) +: 8];
            end
            assign head[8 * gb +: 8] = hb;
        end
        wire [255:0] o_mask = ~({256{1'b1}} << {p_kt[4:0], 3'b000});
`ifdef OT_ING_MUT_SPKIND
        wire [255:0] o_d = (p_kind == 2'd0) ? head : (p_kind == 2'd1) ? head                       // mutant: tail not masked
`else
        wire [255:0] o_d = (p_kind == 2'd0) ? head : (p_kind == 2'd1) ? (head & o_mask)
`endif
                         : (p_kind == 2'd2) ? sc_acc[0] : sc_acc[1];
        assign sc_we = p_sc; assign sc_row = p_row; assign sc_wd = head[31:0];
        // output FIFO: 4 x {addr, data}; read through 9 kept one-hot read-pointer copies (32 output bits a copy)
        reg  [AW+255:0] fq [0:3];
        reg  [1:0]      fq_wr;
        reg  [2:0]      fq_n;
        (* keep *) reg [35:0] fq_rh;
        wire            fq_pop = (fq_n != 0) && w_rdy;
        always @(posedge clk) if (p_wv) fq[fq_wr] <= {p_wa, o_d};
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin fq_wr <= 2'd0; fq_n <= 3'd0; fq_rh <= {9{4'b0001}}; end
            else begin
                if (p_wv) fq_wr <= fq_wr + 2'd1;
`ifdef OT_ING_MUT_SPRH
                if (fq_pop) for (int c = 0; c < 8; c++) fq_rh[4 * c +: 4] <= {fq_rh[4 * c +: 3], fq_rh[4 * c + 3]};  // mutant: address copy 8 stalls
`else
                if (fq_pop) for (int c = 0; c < 9; c++) fq_rh[4 * c +: 4] <= {fq_rh[4 * c +: 3], fq_rh[4 * c + 3]};
`endif
                fq_n <= fq_n + (p_wv ? 3'd1 : 3'd0) - (fq_pop ? 3'd1 : 3'd0);
            end
        wire [AW+255:0] fq_h;
        for (gb = 0; gb < 9; gb = gb + 1) begin : g_fr
            wire [3:0] oh = fq_rh[4 * gb +: 4];
            assign fq_h[32 * gb +: 32] = ({32{oh[0]}} & fq[0][32 * gb +: 32]) | ({32{oh[1]}} & fq[1][32 * gb +: 32])
                                       | ({32{oh[2]}} & fq[2][32 * gb +: 32]) | ({32{oh[3]}} & fq[3][32 * gb +: 32]);
        end
        assign sp_wv = (fq_n != 0);
        assign sp_wa = fq_h[AW+255:256];
        assign sp_wd = fq_h[255:0];
        assign sp_room = (fq_n + (p_wv ? 3'd1 : 3'd0)) <= 3'd3;
        assign sp_busy = p_wv || p_sc || (fq_n != 0);
        // completion queue: entries {tag, issued count}; head leaves when the accepted count reaches it
        reg  [31:0] sp_iss, sp_acc;
        reg         dq_e1, dq_e2;
        reg  [7:0]  dq_t1, dq_t2;
        reg  [31:0] dq_c1, dq_c2;
        reg  [39:0] cq [0:7];
        reg  [2:0]  cq_wr, cq_rd;
        reg  [3:0]  cq_n;
        wire [39:0] cq_h = cq[cq_rd];
        wire        cq_go = (cq_n != 0) && (sp_acc >= cq_h[31:0]);
        always @(posedge clk) begin
`ifdef OT_S81_SH_S10C
            // s10c: sp_iss counts the registered issue (p_wv), one edge after st_go && st_wv, so sp_iss after edge
            // t + 1 equals the s10b count after edge t: dq_c2 takes it directly (= the s10b dq_c1 one edge later).
            dq_t1 <= dtag_r; dq_c1 <= sp_iss; dq_t2 <= dq_t1; dq_c2 <= sp_iss;
`else
            dq_t1 <= dtag_r; dq_c1 <= sp_iss; dq_t2 <= dq_t1; dq_c2 <= dq_c1;
`endif
            if (dq_e2) cq[cq_wr] <= {dq_t2, dq_c2};
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin sp_iss <= 0; sp_acc <= 0; dq_e1 <= 1'b0; dq_e2 <= 1'b0; cq_wr <= 0; cq_rd <= 0; cq_n <= 0; end
            else begin
`ifdef OT_S81_SH_S10C
`ifdef OT_ING_MUT_S10CISS
                if (p_wv || p_sc) sp_iss <= sp_iss + 1;  // mutant: counts every stage-P step incl. the IKEY scale capture
`else
                if (p_wv) sp_iss <= sp_iss + 1;      // registered enable (s10b: st_go && st_wv cone + 32-b increment)
`endif
`else
                if (st_go && st_wv) sp_iss <= sp_iss + 1;
`endif
                if (fq_pop) sp_acc <= sp_acc + 1;
                dq_e1 <= done_r; dq_e2 <= dq_e1;
                if (dq_e2) cq_wr <= cq_wr + 3'd1;
                if (cq_go) cq_rd <= cq_rd + 3'd1;
                cq_n <= cq_n + (dq_e2 ? 4'd1 : 4'd0) - (cq_go ? 4'd1 : 4'd0);
            end
`ifndef SYNTHESIS
        always @(posedge clk) if (rst_n && dq_e2 && cq_n == 4'd8 && !cq_go) $fatal(1, "ot_hdc_kv_ingest: APIPE 10 completion queue overflow");
`endif
        assign sp_done_v = cq_go; assign sp_done_tag = cq_h[39:32]; assign sp_done_cnt = cq_h[31:0];
    end else begin : g_sp0
        assign sp_done_v = 1'b0; assign sp_done_tag = 8'd0; assign sp_done_cnt = 32'd0;
        assign sp_wv = 1'b0; assign sp_wa = {AW{1'b0}}; assign sp_wd = 256'd0; assign sp_room = 1'b1; assign sp_busy = 1'b0;
        assign sc_we = st_go && st_mode == M_IKEY && st_ph == 3'd2; assign sc_row = st_row[3:0]; assign sc_wd = ra_head[31:0];
    end endgenerate

    generate if (QPIPE != 0) begin : g_qp
        // ---- I0: the beat and its granule walk
        reg          i0_v, i0_slot, i0_last;
        reg  [511:0] i0_d;
        reg  [1:0]   i0_fmt;
        reg  [3:0]   i0_lhd;
        reg  [3:0]   i0_use, i0_isv;
        reg  [3:0]   i0_t [0:3];
        reg  [7:0]   i0_g [0:3];
        reg  [15:0]  i0_dd [0:3];
        integer k;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) i0_v <= 1'b0; else i0_v <= q_beat;
        always @(posedge clk) if (q_beat) begin
            i0_slot <= qi_slot; i0_last <= q_last; i0_d <= in_data; i0_fmt <= q_fmt; i0_lhd <= q_lhd;
            i0_use <= g_use;
            for (k = 0; k < 4; k = k + 1) begin
                i0_t[k] <= gw_t[k][3:0]; i0_g[k] <= gw_g[k]; i0_dd[k] <= gw_d[k]; i0_isv[k] <= gw_v[k];
            end
        end
        // ---- I1: FP8 codes, lane and word of each granule
        wire [7:0] cq [0:63];
        genvar ge2;
        for (ge2 = 0; ge2 < 64; ge2 = ge2 + 1) begin : g_cq
            wire [7:0] c32, cbf;
            if (ge2 < 16) begin : g32
                ot_hdc_ingest_fp8q u_q32 (.f(i0_d[ge2*32 +: 32]), .q(c32));
            end else begin : g32z
                assign c32 = 8'd0;
            end
            if (ge2 < 32) begin : gbf
                ot_hdc_ingest_fp8q u_qbf (.f({i0_d[ge2*16 +: 16], 16'd0}), .q(cbf));
            end else begin : gbfz
                assign cbf = 8'd0;
            end
            assign cq[ge2] = (i0_fmt == 2'd0) ? c32 : (i0_fmt == 2'd1) ? cbf : i0_d[ge2*8 +: 8];
        end
        reg          i1_v, i1_slot, i1_last;
        reg  [3:0]   i1_use, i1_isv;
        reg  [3:0]   i1_lane [0:3];
        reg  [LWP-1:0] i1_word [0:3];
        reg  [127:0] i1_code [0:3];
        reg  [15:0]  hw;
        integer b;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) i1_v <= 1'b0; else i1_v <= i0_v;
        always @(posedge clk) if (i0_v) begin
            i1_slot <= i0_slot; i1_last <= i0_last; i1_use <= i0_use; i1_isv <= i0_isv;
            for (k = 0; k < 4; k = k + 1) begin
                hw = hw_word(i0_g[k], i0_lhd, i0_dd[k]);
                i1_word[k] <= hw[LWP-1:0];
                i1_lane[k] <= (QMUT == 1 && !i0_isv[k]) ? (i0_t[k] ^ 4'd1) : i0_t[k];
                for (b = 0; b < 16; b = b + 1) i1_code[k][b*8 +: 8] <= cq[k*16 + b];
            end
        end
        // QPIPE 2 (QP2) state seen by the shared output-FIFO / completion logic; tied off (continuous assigns) otherwise
        wire [127:0] e1_vs0, e1_vs1;               // the two selected V words (sector halves)
        wire         s1_v, s2_v;                   // drain read stages in flight (credit accounting)
        wire         fset_d, fslot_d;              // slot-full flag one edge after its last staged write
        wire [15:0]  wk_any_q, wv_any_q;           // per-bank staged write enables (busy accounting)
        assign qp_fset = (QP2 != 0) ? fset_d : (i1_v && i1_last);
        assign qp_fslot = (QP2 != 0) ? fslot_d : i1_slot;
        // ---- per-lane banks: write at I2, drain reads E1
        reg          e1_v, e1_isv, e1_last;
        reg  [AW-1:0] e1_a;
        reg  [7:0]   e1_tag;
        reg  [15:0]  e1_lane;
        reg  [3:0]   e1_t0, e1_t1;
        reg  [15:0]  e1_kb [0:15];
        reg  [127:0] e1_v0 [0:15];
        reg  [127:0] e1_v1 [0:15];
        // drain addresses from the registered counters / fields
        wire [15:0]  kw = hw_word(qo_g, o_lhd, {qo_s[14:0], 1'b0});
        wire [15:0]  by0 = {qo_s[10:0], 5'd0};
        wire [15:0]  by1 = {qo_s[10:0], 5'd0} + 16'd16;
        wire [15:0]  vw0 = hw_word(qo_g, o_lhd, by0 & (o_hd - 16'd1));
        wire [15:0]  vw1 = hw_word(qo_g, o_lhd, by1 & (o_hd - 16'd1));
        wire [15:0]  t0w = by0 >> o_lhd;
        wire [15:0]  t1w = by1 >> o_lhd;
        wire [3:0] kob = {qo_s[2:0],1'b0};
        // Original production descriptors use CTX8192,HD128,1/2 heads.
        // a0 retains original K linear base: L*KVH*32768 + block*64.
        wire[5:0] native_layer=(o_kvh==1)?od[36:31]:od[37:32];
        wire[13:0] native_t={1'b0,od[30:22],4'd0}+14'(t0w[3:0]);
        wire[31:0] native_addr={8'd0,native_layer,qo_v,qo_g[0],native_t[6],native_t[13:9],native_t[5:3],
                             native_t[8:7],qo_s[1:0],native_t[2:0]};
        wire native_last=qo_v&&(qo_g+8'd1>=o_kvh)&&(qo_s[1:0]==3)&&(t0w==o_thi-1'b1);

        if (QP2 != 0) begin : g_bm
            reg  [127:0] e1_vs0_r, e1_vs1_r;
            reg          s1_v_r, s2_v_r, fset_r, fslot_r;
            wire [15:0]  wk_any, wv_any;
            assign e1_vs0 = e1_vs0_r; assign e1_vs1 = e1_vs1_r; assign s1_v = s1_v_r; assign s2_v = s2_v_r;
            assign fset_d = fset_r; assign fslot_d = fslot_r; assign wk_any_q = wk_any; assign wv_any_q = wv_any;
            // ---- QPIPE 2 (el1011-q-coll 2026-10-11, textbook class 1: the per-lane mk / mv flop banks were ~131k of
            // 155,943 clk_i sinks).  Corner-turn in 2 x 16 single-clock 1R1W macros (ot_sram_1r1w_32x128_m1), skewed
            // bank map  bank = (9 lane + word) mod 16, entry = {slot, lane}:
            //   * a K drain reads one word of all 16 lanes: 9 is odd, so 9 lane mod 16 is a permutation -> 16 banks;
            //   * a beat writes 4 consecutive granules (one lane's consecutive words, or a lane crossing with 1 / 2 / 4 /
            //     8 / 16 words a lane): distinct banks for multiplier 9; a K -> V switch writes the other array;
            //   * a V sector reads two adjacent words of a lane (hd >= 32: banks differ by 1) or the same word of two
            //     adjacent lanes (hd = 16: differ by 9).
            // Write: I1 -> per-bank registered {we, entry, code} (I2) -> macro write (I3); the slot-full flag is delayed
            // one edge so a drain read never samples a slot in the edge its last word lands.  Read: macros sample at
            // q_iss; capture flops on every macro output (no logic before them); then byte-select / lane-rotate / V
            // select into the e1 registers (+2 drain edges; the output FIFO is 8 deep and counts the read stages).
            genvar gb;
            reg  [3:0] wbank [0:3];
            integer wq;
            always @* for (wq = 0; wq < 4; wq = wq + 1) wbank[wq] = (4'd9 * i1_lane[wq] + i1_word[wq][3:0]);
            // read addressing (combinational from the drain registers, sampled by the macros at q_iss)
            wire [3:0] rkw  = kw[3:0];
            wire [3:0] rbv0 = 4'd9 * t0w[3:0] + vw0[3:0];
            wire [3:0] rbv1 = 4'd9 * t1w[3:0] + vw1[3:0];
            wire [127:0] mko [0:15];
            wire [127:0] mvo [0:15];
            reg  [127:0] ck_q [0:15];
            reg  [127:0] cv_q [0:15];
            for (gb = 0; gb < 16; gb = gb + 1) begin : g_mb
                localparam [3:0] GB = gb;
                reg          wk_v, wv_v;
                reg  [4:0]   wk_a, wv_a;
                reg  [127:0] wk_d, wv_d;
                integer w2;
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) begin wk_v <= 1'b0; wv_v <= 1'b0; end
                    else begin
                        wk_v <= 1'b0; wv_v <= 1'b0;
                        if (i1_v) for (w2 = 0; w2 < 4; w2 = w2 + 1)
                            if (i1_use[w2] && wbank[w2] == GB) begin
                                if (!i1_isv[w2]) wk_v <= 1'b1; else wv_v <= 1'b1;
                            end
                    end
                always @(posedge clk) if (i1_v)
                    for (w2 = 0; w2 < 4; w2 = w2 + 1)
                        if (i1_use[w2] && wbank[w2] == GB) begin
                            if (!i1_isv[w2]) begin wk_a <= {i1_slot, i1_lane[w2]}; wk_d <= i1_code[w2]; end
                            else             begin wv_a <= {i1_slot, i1_lane[w2]}; wv_d <= i1_code[w2]; end
                        end
                assign wk_any[gb] = wk_v; assign wv_any[gb] = wv_v;
                // K: bank gb holds lane 9 (gb - kw) mod 16 of the drained word (9 is its own inverse mod 16)
                wire[3:0]rvl=(rbv0==GB)?t0w[3:0]:t1w[3:0];
                wire[3:0]rkl=NATIVE_ROWS?rvl:4'd9*(GB-rkw);
                ot_sram_1r1w_32x128_m1 u_mk (.clk(clk), .r_ce_in(q_iss && !qo_v), .r_addr_in({qo_slot, rkl}), .rd_out(mko[gb]),
                    .w_ce_in(wk_v), .w_addr_in(wk_a), .wd_in(wk_d), .w_mask_in({128{1'b1}}));
                ot_sram_1r1w_32x128_m1 u_mv (.clk(clk), .r_ce_in(q_iss && qo_v), .r_addr_in({qo_slot, rvl}), .rd_out(mvo[gb]),
                    .w_ce_in(wv_v), .w_addr_in(wv_a), .wd_in(wv_d), .w_mask_in({128{1'b1}}));
                always @(posedge clk) begin ck_q[gb] <= mko[gb]; cv_q[gb] <= mvo[gb]; end   // capture flops
            end
            // drain side info through the two read stages
            reg          s1_isv, s1_last, s2_isv, s2_last;
            reg  [7:0]   s1_tag, s2_tag;
            reg  [AW-1:0] s1_a, s2_a;
            reg  [15:0]  s1_lane, s2_lane;
            reg  [3:0]   s1_t0, s1_t1, s2_t0, s2_t1, s1_kw, s2_kw, s1_kob, s2_kob, s1_b0, s1_b1, s2_b0, s2_b1;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin s1_v_r <= 1'b0; s2_v_r <= 1'b0; e1_v <= 1'b0; fset_r <= 1'b0; end
                else begin s1_v_r <= q_iss&&(!NATIVE_ROWS||o_lane[t0w[3:0]]); s2_v_r <= s1_v_r; e1_v <= s2_v_r; fset_r <= i1_v && i1_last; end
            always @(posedge clk) fslot_r <= i1_slot;
            always @(posedge clk) if (q_iss) begin
                s1_isv <= qo_v; s1_last <= (NATIVE_ROWS?native_last:q_wlast)&&od[7]; s1_tag <= od[15:8]; s1_a <= NATIVE_ROWS?native_addr:qo_hb+qo_s;
                s1_lane <= o_lane; s1_t0 <= t0w[3:0]; s1_t1 <= t1w[3:0]; s1_kw <= rkw; s1_kob <= kob; s1_b0 <= rbv0; s1_b1 <= rbv1;
            end
            always @(posedge clk) begin
                s2_isv <= s1_isv; s2_last <= s1_last; s2_tag <= s1_tag; s2_a <= s1_a; s2_lane <= s1_lane;
                s2_t0 <= s1_t0; s2_t1 <= s1_t1; s2_kw <= s1_kw; s2_kob <= s1_kob; s2_b0 <= s1_b0; s2_b1 <= s1_b1;
            end
            integer lq;
            reg [3:0] kb;
            always @(posedge clk) if (s2_v_r) begin
                for (lq = 0; lq < 16; lq = lq + 1) begin
                    kb = 4'd9 * lq + s2_kw;
                    e1_kb[lq] <= {ck_q[kb][(s2_kob+1)*8 +: 8], ck_q[kb][s2_kob*8 +: 8]};
                end
                e1_vs0_r <= (NATIVE_ROWS&&!s2_isv)?ck_q[s2_b0]:cv_q[s2_b0]; e1_vs1_r <= (NATIVE_ROWS&&!s2_isv)?ck_q[s2_b1]:cv_q[s2_b1];
                e1_isv <= NATIVE_ROWS||s2_isv; e1_last <= s2_last; e1_tag <= s2_tag; e1_a <= s2_a;
                e1_lane <= s2_lane; e1_t0 <= s2_t0; e1_t1 <= s2_t1;
            end
        end else begin : g_b1
            assign s1_v = 1'b0; assign s2_v = 1'b0; assign fset_d = 1'b0; assign fslot_d = 1'b0;
            assign wk_any_q = 16'd0; assign wv_any_q = 16'd0; assign e1_vs0 = 128'd0; assign e1_vs1 = 128'd0;
        genvar gl2;
            for (gl2 = 0; gl2 < 16; gl2 = gl2 + 1) begin : g_bank
                reg [127:0] mk [0:2*WPL-1];
                reg [127:0] mv [0:2*WPL-1];
                integer w;
                always @(posedge clk) if (i1_v)
                    for (w = 0; w < 4; w = w + 1)
                        if (i1_use[w] && i1_lane[w] == gl2) begin
                            if (!i1_isv[w]) mk[{i1_slot, i1_word[w]}] <= i1_code[w];
                            else            mv[{i1_slot, i1_word[w]}] <= i1_code[w];
                        end
                wire [127:0] rk = mk[{qo_slot, kw[LWP-1:0]}];
                always @(posedge clk) if (q_iss) begin
                    e1_kb[gl2] <= {rk[(kob+1)*8 +: 8], rk[kob*8 +: 8]};
                    e1_v0[gl2] <= mv[{qo_slot, vw0[LWP-1:0]}];
                    e1_v1[gl2] <= mv[{qo_slot, vw1[LWP-1:0]}];
                end
            end
            always @(posedge clk or negedge rst_n)
                if (!rst_n) e1_v <= 1'b0; else e1_v <= q_iss;
            always @(posedge clk) if (q_iss) begin
                e1_isv <= qo_v; e1_last <= q_wlast && od[7]; e1_tag <= od[15:8]; e1_a <= qo_hb + qo_s;
                e1_lane <= o_lane; e1_t0 <= t0w[3:0]; e1_t1 <= t1w[3:0];
            end
        end
        // ---- E2: sector assembly into the output FIFO (4 entries; credit-issued)
        reg  [255:0]  sec;
        integer l;
        always @* begin
            sec = 256'd0;
            if (!e1_isv) begin
                for (l = 0; l < 16; l = l + 1) begin
                    sec[l*8 +: 8]      = e1_lane[l] ? e1_kb[l][7:0]  : 8'd0;
                    sec[(16+l)*8 +: 8] = e1_lane[l] ? e1_kb[l][15:8] : 8'd0;
                end
            end else begin
                sec[127:0]   = e1_lane[e1_t0] ? ((QP2 != 0) ? e1_vs0 : e1_v0[e1_t0]) : 128'd0;
                sec[255:128] = e1_lane[e1_t1] ? ((QP2 != 0) ? e1_vs1 : e1_v1[e1_t1]) : 128'd0;
            end
        end
        localparam integer FQD = (QP2 != 0) ? 8 : 4;    // QPIPE 2: +2 drain edges in flight -> 8 entries
        localparam integer FQA = (QP2 != 0) ? 3 : 2;
        reg  [255:0]  fq_d [0:FQD-1];
        reg  [AW-1:0] fq_a [0:FQD-1];
        reg  [8:0]    fq_t [0:FQD-1];          // {fenced last, tag}
        reg  [FQA-1:0] fq_wp, fq_rp;
        reg  [FQA:0]   fq_n;
        wire          fq_pop = qp_wv && w_rdy;
        assign qp_wv = fq_n != 0;
        assign qp_wa = fq_a[fq_rp];
        assign qp_wd = fq_d[fq_rp];
        assign qp_dv = fq_pop && fq_t[fq_rp][8];
        assign qp_dtag = fq_t[fq_rp][7:0];
        assign qp_room = ({2'b0, fq_n} + (e1_v ? 5'd1 : 5'd0) + (s1_v ? 5'd1 : 5'd0) + (s2_v ? 5'd1 : 5'd0)) < FQD;
        assign qp_busy = i0_v || i1_v || e1_v || s1_v || s2_v || fset_d || (|wk_any_q) || (|wv_any_q) || fq_n != 0 || s_fill != 2'b00;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin fq_wp <= 0; fq_rp <= 0; fq_n <= 0; end
            else begin
                if (e1_v) fq_wp <= fq_wp + 1'b1;
                if (fq_pop) fq_rp <= fq_rp + 1'b1;
                fq_n <= fq_n + (e1_v ? 1'b1 : 1'b0) - (fq_pop ? 1'b1 : 1'b0);
            end
        always @(posedge clk) if (e1_v) begin
            fq_d[fq_wp] <= sec; fq_a[fq_wp] <= e1_a; fq_t[fq_wp] <= {e1_last, e1_tag};
        end
    end else begin : g_qn
        assign qp_room = 1'b0; assign qp_wv = 1'b0; assign qp_wa = {AW{1'b0}}; assign qp_wd = 256'd0;
        assign qp_busy = 1'b0; assign qp_fset = 1'b0; assign qp_fslot = 1'b0; assign qp_dv = 1'b0; assign qp_dtag = 8'd0;
    end endgenerate
endmodule
`undef OT_SR_INC
`undef OT_SL_DEC
