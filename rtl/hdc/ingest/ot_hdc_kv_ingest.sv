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
module ot_hdc_kv_ingest #(
    parameter integer AW     = 32,        // sector address bits
    parameter integer HDMAX  = 128,       // largest head_dim (QKV), a power of two >= 16
    parameter integer KVHMAX = 8,         // most KV heads per block (QKV), a power of two <= 16
    parameter integer DQ     = 4          // descriptor queue depth (a power of two)
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
    output reg               done_v,
    output reg  [7:0]        done_tag,
    output wire              busy,
    output reg  [31:0]       n_sectors,
    output reg  [31:0]       n_beats
);
    localparam [3:0] M_RAW = 4'd0, M_QKV = 4'd1, M_ROWS = 4'd2, M_IKEY = 4'd3;
    localparam integer BB  = KVHMAX * HDMAX;       // bytes per position lane per slot
    localparam integer WPL = BB / 16;              // 16-byte words per lane per slot (a power of two)
    localparam integer LWP = (WPL > 1) ? $clog2(WPL) : 1;
    localparam integer NBW = 2 * 16 * WPL;         // words per bank (2 slots x 16 lanes)

    // -- descriptor queue ---------------------------------------------------------
    localparam integer LDQ = $clog2(DQ);
    reg [255:0] dq [0:DQ-1];
    reg [LDQ:0] dq_n;
    reg [LDQ-1:0] dq_rd, dq_wr;
    wire [255:0] dh = dq[dq_rd];
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
    wire [1:0]  q_fmt = qd[5:4];
    wire [3:0]  q_lhd = qd[171:168];
    wire [15:0] q_hd  = 16'd1 << q_lhd;
    wire [7:0]  q_kvh = {4'd0, qd[219:216]};
    wire [4:0]  q_tlo = qd[228:224];
    wire [4:0]  q_thi = qd[236:232];
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
    wire [255:0] od = sd[qo_slot];
    wire [3:0]  o_lhd = od[171:168];
    wire [15:0] o_hd  = 16'd1 << o_lhd;
    wire [7:0]  o_kvh = {4'd0, od[219:216]};
    wire [4:0]  o_tlo = od[228:224];
    wire [4:0]  o_thi = od[236:232];
    wire        o_rmw = od[6];
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
    wire [511:0] ra_pair = {ra[ra_w0 + 3'd1], ra[ra_w0]};
    wire [511:0] ra_sh = ra_pair >> {ra_rp[4:0], 3'b000};
    wire [255:0] ra_head = ra_sh[255:0];      // the next 32 bytes
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
    // this cycle's stream step
    reg  [5:0]  st_pop;
    reg         st_wv, st_adv;
    reg  [255:0] st_wd;
    reg  [AW-1:0] st_wa;
    wire [5:0]  k_take = (st_rem > 16'd32) ? 6'd32 : st_rem[5:0];
    always @* begin
        st_pop = 6'd0; st_wv = 1'b0; st_wd = 256'd0; st_wa = {AW{1'b0}}; st_adv = 1'b0;
        if (st_act && !st_pad) begin
            case (st_mode)
                M_RAW: if (ra_n >= 9'd32) begin
                    st_pop = 6'd32; st_wv = 1'b1; st_wd = ra_head; st_wa = st_d[47:16] + st_row; st_adv = 1'b1;
                end
                M_ROWS: if (ra_n >= {3'd0, k_take}) begin
                    st_pop = k_take; st_adv = 1'b1; st_wv = s_mine;
                    st_wd = (k_take == 6'd32) ? ra_head : (ra_head & ~({256{1'b1}} << {k_take[4:0], 3'b000}));
                    st_wa = s_raddr + st_sec;
                end
                M_IKEY: begin
                    if (st_ph < 3'd2) begin
                        if (ra_n >= 9'd32) begin
                            st_pop = 6'd32; st_adv = 1'b1; st_wv = s_mine; st_wd = ra_head; st_wa = k_code + st_ph;
                        end
                    end else if (st_ph == 3'd2) begin
                        if (ra_n >= 9'd4) begin st_pop = 6'd4; st_adv = 1'b1; end
                    end else begin
                        st_adv = 1'b1; st_wv = s_mine; st_wd = sc_acc[st_ph[0] ? 0 : 1];
                        st_wa = k_scal + (st_ph == 3'd4 ? 1 : 0);
                    end
                end
                default: ;
            endcase
        end
    end
    wire st_go = st_adv && (!st_wv || w_rdy);
    // ROWS: the row ends with its last output sector (this die) or its last bytes (dropped)
    wire st_row_end = s_mine ? (st_sec + 5'd1 >= s_pitch) : (st_rem <= 16'd32);

    // =============================================================================
    // Ports
    // =============================================================================
    // the stream path runs only while the QKV path is idle, so they never contend
    assign w_v    = q_wv || st_wv;
    assign w_addr = q_wv ? (qo_hb + qo_s) : st_wa;
    assign w_data = q_wv ? q_sec : st_wd;
    wire w_fire = w_v && w_rdy;
    wire ra_push = st_act && !st_pad && in_v && (ra_n <= 9'd192) && (st_beats != 0);
    wire pad_take = st_act && st_pad && in_v && (st_beats != 0);
    assign in_rdy = qi_act || (st_act && (st_pad ? (st_beats != 0) : ((ra_n <= 9'd192) && (st_beats != 0))));
    assign busy = dh_v || qi_act || qo_act || pr_act || (s_pre != 0) || st_act || (s_full != 0);

    // dispatch: a QKV descriptor takes the other slot once it is drained (and an
    // RMW descriptor waits for any preload in flight); a stream descriptor starts
    // when the QKV path is idle
    wire nslot = ~qi_slot;
    wire q_disp = dh_v && dh_mode == M_QKV && !qi_act && !st_act && !s_full[nslot] && !s_pre[nslot]
                  && !(qo_act && qo_slot == nslot) && (!dh[6] || (!pr_act && pr_out == 0 && s_pre == 2'b00));
    wire s_disp = dh_v && dh_mode != M_QKV && !qi_act && !st_act && !qo_act && s_full == 2'b00 && !pr_act
                  && s_pre == 2'b00;
    wire d_pop = q_disp || s_disp;

    // -- sequential ---------------------------------------------------------------
    integer bi;
    reg [127:0] g_word, r_word;
    reg [31:0]  r_idx;
    reg [15:0]  r_by;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dq_n <= 0; dq_rd <= 0; dq_wr <= 0;
            s_full <= 2'b00; s_pre <= 2'b00; qi_act <= 1'b0; qi_slot <= 1'b0; qo_act <= 1'b0; qo_slot <= 1'b0;
            pr_act <= 1'b0; pr_out <= 0; st_act <= 1'b0; st_pad <= 1'b0; ra_n <= 0; ra_rp <= 0; ra_wp <= 0;
            done_v <= 1'b0; done_tag <= 0; n_sectors <= 0; n_beats <= 0;
            qi_t <= 0; qi_g <= 0; qi_d <= 0; qi_v <= 1'b0; qo_v <= 1'b0; qo_g <= 0; qo_s <= 0; qo_hb <= 0;
            pr_v <= 1'b0; pr_g <= 0; pr_s <= 0; pr_hb <= 0; pr_slot <= 1'b0;
            pt_v <= 1'b0; pt_g <= 0; pt_s <= 0; st_ph <= 0; st_beats <= 0; st_row <= 0; st_left <= 0;
            st_rem <= 0; st_sec <= 0;
        end else begin
            done_v <= 1'b0;
            if (w_fire) n_sectors <= n_sectors + 1;
            if (q_beat || ra_push || pad_take) n_beats <= n_beats + 1;
            // descriptor queue
            if (d_v && d_rdy) begin dq[dq_wr] <= d_data; dq_wr <= dq_wr + 1'b1; end
            if (d_pop) dq_rd <= dq_rd + 1'b1;
            dq_n <= dq_n + ((d_v && d_rdy) ? 1 : 0) - (d_pop ? 1 : 0);

            if (q_disp) begin
                qi_slot <= nslot; sd[nslot] <= dh; qi_act <= 1'b1;
                qi_t <= dh[228:224]; qi_g <= 0; qi_d <= 0; qi_v <= 1'b0;
                if (dh[6] && dh[228:224] != 5'd0) begin
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
            if (q_beat) begin
                for (gi = 0; gi < 4; gi = gi + 1)
                    if (g_use[gi]) begin
                        for (bi = 0; bi < 16; bi = bi + 1) g_word[bi*8 +: 8] = cv[gi*16 + bi];
                        if (!gw_v[gi]) bk[bw_idx(qi_slot, gw_t[gi][3:0], hw_word(gw_g[gi], q_lhd, gw_d[gi]))] <= g_word;
                        else           bv[bw_idx(qi_slot, gw_t[gi][3:0], hw_word(gw_g[gi], q_lhd, gw_d[gi]))] <= g_word;
                    end
                qi_t <= gw_t[q_gpb]; qi_g <= gw_g[q_gpb]; qi_d <= gw_d[q_gpb]; qi_v <= gw_v[q_gpb];
                if (q_last) begin qi_act <= 1'b0; s_full[qi_slot] <= 1'b1; end
            end
            if (qi_act && q_tlo >= q_thi) begin qi_act <= 1'b0; s_full[qi_slot] <= 1'b1; end   // empty payload

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
                qo_hb <= sd[~qo_slot][47:16];
            end
            if (q_wv && w_rdy) begin
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
                    if (od[7]) begin done_v <= 1'b1; done_tag <= od[15:8]; end
                end
            end

            // ---- stream path
            if (ra_push) begin
                ra[ra_wp] <= in_data[255:0]; ra[ra_wp + 3'd1] <= in_data[511:256]; ra_wp <= ra_wp + 3'd2;
            end
            if (ra_push || pad_take) st_beats <= st_beats - 16'd1;
            if (st_pad) begin
                // the segment's last-beat padding (and any extra padding beats) is dropped
                ra_n <= 0; ra_rp <= 0; ra_wp <= 0;
                if (st_beats == 0 || (pad_take && st_beats == 16'd1)) begin
                    st_act <= 1'b0; st_pad <= 1'b0;
                    if (st_d[7]) begin done_v <= 1'b1; done_tag <= st_d[15:8]; end
                end
            end else begin
                ra_n <= ra_n + (ra_push ? 9'd64 : 9'd0) - (st_go ? {3'd0, st_pop} : 9'd0);
                if (st_go) ra_rp <= ra_rp + {2'd0, st_pop};
            end
            if (st_go) begin
                case (st_mode)
                    M_RAW: begin
                        st_row <= st_row + 1; st_left <= st_left - 1;
                        if (st_left == 32'd1) st_pad <= 1'b1;
                    end
                    M_ROWS: begin
                        st_rem <= st_rem - {10'd0, k_take};
                        if (!st_row_end) begin
                            if (s_mine) st_sec <= st_sec + 5'd1;
                        end else begin
                            st_sec <= 0; st_rem <= s_rb; st_row <= st_row + 1; st_left <= st_left - 1;
                            if (st_left == 32'd1) st_pad <= 1'b1;
                        end
                    end
                    M_IKEY: begin
                        if (st_ph == 3'd2) begin
                            if (st_row[3]) sc_acc[1][st_row[2:0] * 32 +: 32] <= ra_head[31:0];
                            else           sc_acc[0][st_row[2:0] * 32 +: 32] <= ra_head[31:0];
                            if (st_row[3:0] == 4'd15) st_ph <= 3'd3;
                            else begin st_ph <= 3'd0; st_row <= st_row + 1; st_left <= st_left - 1; end
                        end else if (st_ph == 3'd4) begin
                            st_ph <= 3'd0; st_row <= st_row + 1; st_left <= st_left - 1;
                            if (st_left == 32'd1) st_pad <= 1'b1;
                        end else st_ph <= st_ph + 3'd1;
                    end
                    default: ;
                endcase
            end
            if (st_act && !st_pad && st_left == 0 && !s_disp) st_pad <= 1'b1;   // an empty segment
        end
    end
endmodule
