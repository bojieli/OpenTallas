`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): vq = the act-quant sub-leaf of one BEAT of a DV vector slice (x5 per slice, own
// clock root).  It takes the beat's normed y from vn (8 lanes a cycle, sub-beats j = 0..7), assembles the two golden
// 32-element act-quant blocks (block 0 = sub-beats 0..3, block 1 = 4..7: blocks are aligned to the slice's 320-element
// ownership, so no amax crosses a beat) and runs them through ot_dsrom_aq12 (tools/hdc_golden_v41.quant_fp8 bit for bit,
// latency 18).  Output = ring-format x beats of this leaf (SLICE_CONTRACT section 3), sent as 4 x 276-b FRAGMENTS (the V
// rung format: fragment 0 = bits [275:0] with the header, then [551:276], [827:552], [1103:828]) on xf with xf_v (fragment
// valid) and xf_s (fragment 0); header: v, kind, hops 1, src sid, idx = the global beat 5 sid + k (straps, captured):
//   XQ  the q family of the beat, payload {e1 10, q1 256, e0 10, q0 256} (dsfd_pq_lx x0 / x1 fields)
//   XB  the BF16 family: the 64 normed y as BF16 (lane l at payload [16 l +: 16]) for BF16 field phases
// The gather mode (m_q / m_b, set per norm by vp) selects the families.  The beats leave STAGGERED by the leaf strap k
// with stride 4 (one V rung beat = 4 x 276-b fragments): XQ at q + 4k, XB at q + 20 + 4k (q = the quantiser output
// edge), so the 5 leaves' beats reach the ring stop one every 4 cycles (equal-latency glue paths) and are injected on
// the tier line and sent over the V rung without any staging.
// Every input lands in a flop; every output leaves a flop.  Static schedule: a y beat index out of order is a fault.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_vq #(
    // 0: the shared ot_dsrom_aq12 with its 1024 x 11 flop wait line (reference).
    // 2 (the kit's setting, S81-TILES2 10-17): the wait line is rebuilt from the 256-b sub-beat stream: every sub-beat
    // sd_ is written to ONE ot_sram_1r1w_128x256_m1_r2c2 ring (free-running 4-bit pointer, read 11 rows behind) and
    // replayed 12 cycles later, with its (valid, slot) control from a 3-b x 12 flop line, into a 1024-b re-assembly
    // register xr; blk changes only on those events, so xr(c) = blk(c - 12) = aq12's flop-line xg(c) on every cycle.
    // The quantiser is then the vq-only fork ot_s81sl_aq12x (xd port, no u_x line; S81-TILES3 10-17): the shared
    // ot_dsrom_aq12 stays byte-identical with main.  (The former AQ_XMEM = 1, a 4-macro ring inside aq12, is dropped.)
    parameter integer AQ_XMEM = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          y_v,          // normed y from vn
    input  wire [2:0]    y_i,
    input  wire [127:0]  y,             // packed BF16 from vn (OWNER DECISION 8 (2026-10-24, S81-KITS-RTLA):): unpacked at the input flop
    input  wire          u_v,          // SU results to quantise from vs (SW act, QB z): same 8-lane sub-beat stream
    input  wire [2:0]    u_i,
    input  wire [255:0]  u,
    input  wire [3:0]    sid,        // straps: slice id, leaf index
    input  wire [2:0]    k,
    input  wire          m_v,        // gather mode for the next 64-element vector (vp: NORM): families q / BF16, global beat
    input  wire          m_q,        // index of the vector's 64 elements (the x-buffer index; 5 sid + k for h vectors)
    input  wire          m_b,
    input  wire [7:0]    m_i,
    input  wire          um_v,       // the same for a vs stream
    input  wire          um_q,
    input  wire          um_b,
    input  wire [7:0]    um_i,
    output reg           xf_v,
    output reg           xf_s,
    output reg  [275:0]  xf,
    (* keep *) output reg fault          // keep: never merged with its internal copy fault_s
);
    wire [1:0] rsv;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_q = rsv[1];
    reg yv_c, uv_c; reg [2:0] yi_c, ui_c; reg [255:0] y_c, u_c; reg [3:0] sid_c; reg [2:0] k_c; reg mq, mb, mcol; reg [7:0] mi;
    always @(posedge clk or negedge rs_c) if (!rs_c) begin yv_c <= 1'b0; uv_c <= 1'b0; end else begin yv_c <= y_v; uv_c <= u_v; end
    always @(posedge clk) begin yi_c <= y_i; y_c <= {y[127:112], 16'd0, y[111:96], 16'd0, y[95:80], 16'd0, y[79:64], 16'd0, y[63:48], 16'd0, y[47:32], 16'd0, y[31:16], 16'd0, y[15:0], 16'd0}; ui_c <= u_i; u_c <= u; sid_c <= sid; k_c <= k; end
    // S81-NATIVE3 (10-17, NATIVE-2 audit: um_v 229.0 / m_v 228.9 / y_v 192.0 ps capture): the mode command lands in
    // pin flops (mv_c/umv_c + their q/b/i fields) and the mode-register mux and the collision check read only flops.
    // The mode registers load one edge later than in the closed view (b6d9d4515); every read of mq/mb/mi happens while
    // a vector is sent (run), >= 18 + 8 edges after the command (quantiser latency + sub-beats), so xf is cycle-identical
    // (tools/s81_slice/vq_pinreg_eq.sh vs the closed RTL).  fault also ORs the collision of the pin flops directly, so a
    // collision reaches fault on the same edge as before (mcol keeps it sticky).
    reg mv_c, umv_c, mq_c, mb_c, umq_c, umb_c; reg [7:0] mi_c, umi_c;
    always @(posedge clk or negedge rs_c) if (!rs_c) begin mv_c <= 1'b0; umv_c <= 1'b0; end else begin mv_c <= m_v; umv_c <= um_v; end
`ifdef OT_VQ_MUT_PINREG
    always @(posedge clk) begin mq_c <= um_q; mb_c <= m_b; mi_c <= m_i; umq_c <= um_q; umb_c <= um_b; umi_c <= um_i; end   // mutant: m_q crossed with um_q
`else
    always @(posedge clk) begin mq_c <= m_q; mb_c <= m_b; mi_c <= m_i; umq_c <= um_q; umb_c <= um_b; umi_c <= um_i; end
`endif
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin mq <= 1'b1; mb <= 1'b0; mi <= 8'd0; mcol <= 1'b0; end
        else begin
            if (mv_c) begin mq <= mq_c; mb <= mb_c; mi <= mi_c; end
            else if (umv_c) begin mq <= umq_c; mb <= umb_c; mi <= umi_c; end
            mcol <= mcol | (mv_c && umv_c) | (yv_c && uv_c);
        end
    // one stream: vn's y or vs's u (never both in a cycle: compiler slots; both = fault)
    wire sv_ = yv_c | uv_c; wire [2:0] si_ = yv_c ? yi_c : ui_c; wire [255:0] sd_ = yv_c ? y_c : u_c;
    // block assembly: 4 sub-beats of 8 FP32 words -> 32 words; BF16 copy of all 64
    reg [1023:0] blk; reg bv, bbk; reg [2:0] nexp; reg ord_f;
    integer l, j;
    reg [1023:0] bf;
    // S81-CORES2/RV (2026-10-25, GEOM PASS-COND 04:45; f5b TT -58.8/298 = yv_c -> bf load-enable broadcast over the
    // whole 1024-flop bf array): the bf load is registered once more, from the pin flops: 8 per-group load enables
    // bf_en[j] = (sv_ && si_ == j) (distinct functions, one 128-flop group each, placed with its group) and the BF16 half
    // of sd_ (bf_d, 128 b), so no pin flop fans out into bf and each enable flop drives 128 loads.  bf is loaded one edge
    // later than in the closed RTL; it is read only while the vector's XB beat is sent (>= 18 + 20 edges after the last
    // sub-beat, the next vector's sub-beats come after that send), so xf / fault are cycle-identical
    // (tools/s81_slice/vq_pinreg_eq.sh vs b6d9d4515; mutant OT_VQ_MUT_BFQ must FAIL).  Pin flops keep one load per pin.
    reg [7:0] bf_en; reg [127:0] bf_d; integer jb, lb, jw;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) bf_en <= 8'd0;
        else for (jb = 0; jb < 8; jb = jb + 1)
`ifdef OT_VQ_MUT_BFQ
            bf_en[jb] <= sv_ && si_ == (jb ^ 1);      // mutant: groups steered to the wrong slot (must FAIL)
`else
            bf_en[jb] <= sv_ && si_ == jb;
`endif
    always @(posedge clk) for (lb = 0; lb < 8; lb = lb + 1) bf_d[lb * 16 +: 16] <= sd_[lb * 32 + 16 +: 16];
    always @(posedge clk)
        for (jw = 0; jw < 8; jw = jw + 1) if (bf_en[jw]) bf[128 * jw +: 128] <= bf_d;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin bv <= 1'b0; nexp <= 3'd0; ord_f <= 1'b0; end
        else begin
            bv <= sv_ && si_[1:0] == 2'd3;
            if (sv_) begin nexp <= si_ + 3'd1; if (si_ != nexp) ord_f <= 1'b1; end
        end
    always @(posedge clk) bbk <= si_[2];
    // S81-CORES3/RT (2026-10-25, vq_bfq GRT-RC TT estimate -219.9 on yv_c -> si_ decode -> load enable of 256 blk flops x 4,
    // the same broadcast class as bf): the blk write is staged once, from the pin flops: 4 per-quarter write enables
    // blk_en[j] = (sv_ && si_[1:0] == j) and the sub-beat blk_d = sd_, and blk takes the staged write one edge later.
    // Every reader sees blk_x = blk with the staged write forwarded (blk_en[j] ? blk_d : blk quarter j), which equals the
    // closed RTL's blk on every cycle: 0 cycles (tools/s81_slice/vq_pinreg_eq.sh; mutant OT_VQ_MUT_BLKF drops the forward
    // and must FAIL).  The pin flops now load 4 + 256 flops instead of 1024 enables.
    reg [3:0] blk_en; (* keep *) reg [255:0] blk_d; integer jq;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) blk_en <= 4'd0;
        else for (jq = 0; jq < 4; jq = jq + 1) blk_en[jq] <= sv_ && si_[1:0] == jq;
    always @(posedge clk) blk_d <= sd_;
    always @(posedge clk)
        for (j = 0; j < 4; j = j + 1) if (blk_en[j]) blk[256 * j +: 256] <= blk_d;
    wire [1023:0] blk_x;
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_blkx
`ifdef OT_VQ_MUT_BLKF
        assign blk_x[256 * gq +: 256] = blk[256 * gq +: 256];                          // mutant: no forward (must FAIL)
`else
        assign blk_x[256 * gq +: 256] = blk_en[gq] ? blk_d : blk[256 * gq +: 256];
`endif
    end endgenerate
    // the quantiser registers x itself (aq12 S0): blk feeds it directly; bv is high in the cycle after the block's last
    // sub-beat was written, so aq12 samples the complete block (the next sub-beat lands on the same edge)
    wire vo, af; wire [255:0] q; wire signed [9:0] e; wire [511:0] qy;
    wire [1023:0] xr_w;
    generate
        if (AQ_XMEM == 2) begin : g_xr
            // event t (sv_, slot si_[1:0], data sd_) is written at the end of cycle t to row wp(t); the read address of
            // cycle t + 11 is wp(t + 11) - 11 = wp(t) (registered read: rd_out in cycle t + 12; rows 11 apart, never
            // the row being written); the control rides a 12-deep flop line, so xr loads blk's update of cycle t at
            // the end of cycle t + 12.
            // S81-VQFIX (2026-10-25): the macro's write port and both addresses land in flops AT the macro (kit route
            // ot_s81sl_vq_lfp NOT SIGNED TT -55.87: yv_c -> sd_ mux -> wd_in was 2 x ~120 ps wires + 384 ps slew at the
            // macro pin).  Event t is written one edge later, at the end of cycle t + 1 (wd_m = sd_(t), wa_m = wp(t)),
            // and the read address is registered too (ra_m in cycle c = wp(c - 1) - 10 = wp(c) - 11): the row read in
            // cycle t + 11 is still wp(t), written 10 cycles before and 6 cycles before it is overwritten (t + 17), and
            // never the row being written (wa_m = wp - 1, ra_m = wp - 11).  rd_out, ce and xr are unchanged: 0 cycles.
            reg  [3:0] wp, wa_m, ra_m;
            reg  [255:0] wd_m;
            always @(posedge clk or negedge rs_q)
                if (!rs_q) begin wp <= 4'd0; wa_m <= 4'd15; ra_m <= 4'd5; end
                else begin
                    wp <= wp + 4'd1;
`ifdef OT_VQ_MUT_WREG
                    wa_m <= wp + 4'd1;      // mutant: write address not aligned with the registered data (must FAIL)
`else
                    wa_m <= wp;
`endif
`ifdef OT_VQ_MUT_XPTR
                    ra_m <= wp - 4'd9;      // mutant: one cycle short (the bench must catch it)
`else
                    ra_m <= wp - 4'd10;
`endif
                end
            always @(posedge clk) wd_m <= sd_;
            wire [255:0] rd;
            ot_sram_1r1w_128x256_m1_r2c2 u_xm (.clk(clk), .r_ce_in(1'b1), .r_addr_in({3'd0, ra_m}), .rd_out(rd),
                .w_ce_in(1'b1), .w_addr_in({3'd0, wa_m}), .wd_in(wd_m), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            wire [2:0] ce;
            ot_hdc_delay #(.W(3), .D(12), .RESET(1)) u_xc (.clk(clk), .rst_n(rs_q), .d({sv_, si_[1:0]}), .q(ce));
            reg [1023:0] xr;
            integer jr;
            always @(posedge clk)
                if (ce[2]) for (jr = 0; jr < 4; jr = jr + 1) if (ce[1:0] == jr) xr[256 * jr +: 256] <= rd;
            assign xr_w = xr;
        end else begin : g_xnr
            assign xr_w = {1024{1'b0}};
        end
    endgenerate
    generate
        if (AQ_XMEM == 2) begin : g_aqx
            ot_s81sl_aq12x u_aq (.clk(clk), .rst_n(rs_q), .v(bv), .x(blk_x), .vo(vo), .q(q), .e(e), .y(qy), .fault(af), .xd(xr_w));
        end else begin : g_aq
            ot_dsrom_aq12 u_aq (.clk(clk), .rst_n(rs_q), .v(bv), .x(blk_x), .vo(vo), .q(q), .e(e), .y(qy), .fault(af));
        end
    endgenerate
    // block index rides the quantiser latency
    wire blo;
    ot_hdc_delay #(.W(1), .D(18)) u_bi (.clk(clk), .rst_n(rs_q), .d(bbk), .q(blo));
    reg [255:0] q0; reg [9:0] e0; reg [531:0] xqd;   // the BF16 family is read from bf (stable until the next norm)
    // stagger: a step counter from the quantiser output; XQ leaves at step 4k, XB at step 20 + 4k
    reg [5:0] st; reg run;
    wire [1103:0] xb_full;
    wire [7:0] gidx = mi;                                            // the vector's global beat index (command)
    // the beat being sent: header {idx, src sid, hops 1, kind, v} + payload
    assign xb_full = (st >= 6'd20) ? {59'd0, bf, gidx, sid_c, 5'd1, 3'd2, 1'b1} : {551'd0, xqd, gidx, sid_c, 5'd1, 3'd1, 1'b1};
    // S81-CORES2/RV: the sticky term feeds back from an internal copy (fault_s), so the fault output flop drives only
    // its port (face_guard: one load per output pin flop); same value every edge.
    (* keep *) reg fault_s;
    wire fault_n = fault_s | (vo && af) | ord_f | mcol | (mv_c && umv_c) | (yv_c && uv_c) | (vo && blo && run);
    always @(posedge clk or negedge rs_q)
        if (!rs_q) begin run <= 1'b0; st <= 6'd0; xf_v <= 1'b0; xf_s <= 1'b0; fault <= 1'b0; fault_s <= 1'b0; end
        else begin
            if (vo && blo) begin run <= 1'b1; st <= 6'd0; end
            else if (run) begin st <= st + 6'd1; if (st == 6'd39) run <= 1'b0; end
            xf_v <= run && ((mq && st[5:2] == {1'b0, k_c}) || (mb && st[5:2] == 4'd5 + {1'b0, k_c}));
            xf_s <= run && ((mq && st == {1'b0, k_c, 2'b00}) || (mb && st == 6'd20 + {1'b0, k_c, 2'b00}));
            fault <= fault_n; fault_s <= fault_n;
        end
    always @(posedge clk) begin
        if (vo && !blo) begin q0 <= q; e0 <= e; end
        if (vo && blo) xqd <= {e, q, e0, q0};
        case (st[1:0])
            2'd0: xf <= xb_full[275:0];
            2'd1: xf <= xb_full[551:276];
            2'd2: xf <= xb_full[827:552];
            default: xf <= xb_full[1103:828];
        endcase
    end
endmodule
