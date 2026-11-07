`timescale 1ns/1ps
// DIE-KV-70/ING 11-04, DIE-KV-73/ING 11-05 RE-FORM of qkd_host_native_engine at the production parameters of qkd_hr_ingest_eng
// (AW 32, HDMAX 128, KVHMAX 2, DQ 4, QKV 1, QPIPE 2, NATIVE_ROWS 1).  Function and descriptor format: see the source
// engine rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv.  Why: kit failed GRT 128244 overflow with TT -972 from
// RTL depth (st_d -> w_addr 59 levels, granule walk 35, quantiser 30).  Classes:
//  Exact     same value on every reachable state, no cycle change.
//  Contract  exact for what qkd_host_native_qm_debt passes: a QKV descriptor has n1 = 7 (HD128), n4 in 1..2 and rmw 0
//            (bad_native / bad_rmw fail closed before d_v), the read path never returns (e_rrdy 0 at QPIPE 2, rd_v 0).
//  V/R safe  more edges behind a valid/ready face, same write and done order, no value change.
//  Credit    same credit bound as the source sum, a counter instead of an adder.
// Cuts and removals:
//  1 Contract  RMW preload gone: pr_*, pt_*, s_pre, pr_out; r_v, r_addr constant 0 in the wrapper; rd_v, rd_data unused.
//  2 Contract  granule walk: at HD128 all granules of a beat sit in one head, only the state after the beat can cross.
//              Four chained 16-bit add/compare steps become one 3-bit add and one small head step (35 levels -> ~8).
//  3 Exact     K drain bytes e1_kb and the K branch of sec gone: e1_isv was always 1 at NATIVE_ROWS (the source flop was the
//              LEC X-fold class).  Lane flags e1_lane / s*_lane gone: a sector in the pipeline is in lane by s1_v.
//  4 V/R safe  shared input register in_q: free-running, one load on each in_data pin.  QKV I0 = in_q (+0).  Stream writes
//              ra from in_q (+1 edge), in_rdy low on that edge: one beat per 2 edges = the 32-byte-a-cycle drain rate.
//  5 V/R safe  quantiser cut in two, stage q1 (+1 edge beat to bank write).
//  6 Contract  one write data / address register per K/V bank pair: a beat is all K or all V (cut 2), so no bank pair is
//              written twice in one edge.  Bank select registered one-hot at I1.
//  7 Exact     read select: per-quadrant AND-OR register as the e1 stage (same edges as e1), local K/V pick from a per-bank
//              flag; 4096 macro capture bits reach 8 x 128 quadrant bits instead of a central 32:1 pair of muxes.
//  8 Credit    qp_room from a counter instead of a 5-term sum.
//  9 V/R safe  stream address = source APIPE 3 plus a stage after each product (stack x stride, local x pitch): five bubble edges a ROWS / IKEY row; n_sectors from a registered write fire,
//              done one edge later (the source's APIPE 2 rule).  ap_* with reset and without hold enable (they settle before
//              ap_ok, hold was not needed).
// 10 V/R safe  ROWS / IKEY half rate: step condition, take, row end, address and shifted head registered with one bubble
//              after each step.  RAW keeps 1 sector a cycle on the word mux (ra_rp[4:0] = 0 in RAW).
// 11 Exact     fq_a / s*_a without the constant bits 31:24 and 15 (nt[13]); w_addr gets them back on read (LEC X class by construction).
//    Exact     busy also covers done_r, done_q, wf_q (cut 9 must not let a marker pass a pending done).
// TOK-VERIFY cycle list: QKV beat -> bank write +1 (cut 5); drain, FIFO +0; done / n_sectors +1 (cut 9); RAW, ROWS, IKEY write
//  +1 (cut 4); ROWS / IKEY +5 a row and half rate (cuts 9, 10).  Sustained QKV (1 beat a cycle) and RAW (1 sector a cycle) unchanged.
// DIE-KV-73/ING 11-05 r2 cuts on the ING1 form (census of the routed ING1 build):
// 12 Exact     FIFO read: fq_rp replaced by one-hot read pointers, one kept copy per w_data byte, 2 for address, 1 for tag; each rotates itself on fq_pop.
//              qk_wv registered (fq_n != 0), a kept copy per slice selects FIFO vs stream.  No edge added.
// 13 V/R safe  I1B: one copy of the code beat per macro quadrant ({gb[3], gb[1]}); a code bit drives 4 flops, a quadrant copy 4 banks.  +1 edge beat to bank write.
// 14 V/R safe  stream read: word registers wq0, wq1 after the 8:1 word mux, kept per-byte copies of the word pointer (next state, no edge) and of the byte offset.
//              RAW: wq0 is a valid-qualified read stage (rawq_v), ra advances on its load, 1 sector a cycle kept, +1 edge beat to write.
//              ROWS / IKEY: second bubble (ok0) after each step and after new data: one step per 3 edges instead of 2.
// TOK-VERIFY cycle list on top of ING1: QKV beat -> bank write +1 (cut 13), drain, FIFO +0; RAW write +1 (cut 14), rate kept; ROWS / IKEY 1 step per 3 edges (was 2).  Ports unchanged.
// KV-ING-1 11-05 r3 (version B, safe by construction) on r2:
// 15 V/R safe  I1H: i1_code -> 2 kept half copies ih_all -> 4 quadrant copies ib_all; a bit drives 2 flops per stage.  +1 edge beat to bank write.
// 16 V/R safe  input faces registered: in_* and d_* land in 2-entry FIFOs at the pins; in_rdy / d_rdy are flops.  +1 edge port -> engine.
// 17 V/R safe  busy is a flop (engine busy | FIFO non-empty now or next | push this edge); falls 1 edge later.
// 18 Exact     n_sectors in two 16-bit halves; the high half steps on a registered low-all-ones flag (vA routed path wf_q -> n_sectors[31] was a 32-bit carry chain, -61 ps).
// TOK-VERIFY on top of r2: QKV beat -> bank write +1 (15), port -> engine +1 for beats and descriptors (16), busy fall +1 (17); rates kept.
// KV-ING-5 11-06 vF cut 19 (exact, 0 cycles, no new state): st_wa_r took ap_kcode + st_ph / ap_kscal + (st_ph == 4) through one
//   ripple carry chain that started at st_ph (vE_ff TT -13.65 ps, 10-deep OR chain st_ph[1] -> st_wa_r[30]).  Now carry-select:
//   the 3 low bits add st_ph, the 29 high bits +1 are formed from the registers alone, and the low carry only selects.
// KV-ING-8 11-07 vH2 (conservative) on r3 + cut 19, faces live in the wrapper qkd_hr_ingest_eng:
// 20 V/R safe  p_in_* / p_d_* come from free-running face flops.  in FIFO 3 entries, rdy next state = count + rdy <= 2 (no pin in the cone); dq written directly, rdy = count + rdy <= 3.
// 21 V/R safe  e_rdy copies: er_m (FIFO, credit), er_s (per slice one-hot read pointer), er_st (stream step), all from er_n, which has no w_rdy in its cone.
// 22 V/R safe  e_last, e_tag: fenced last sector's done travels with its write.  Stream done: sd_pend until face_idle, blocks dispatch.  done_r/done_q/wf_q/n_sectors move to the wrapper.
// 23 Exact     per-slice sl_raw, sl_sc, sl_p0, mb_q from next state.
// 24 Exact     RAW address ra_lo/ra_hi counter.
// 25 Exact     st_row = {row_hi, row_lo}, registered low-all-ones flag; st_left 24 bits.
// 26 V/R safe  sec_q, e2_*: read registers -> mid stage -> output FIFO (distance budget: macro block at the top edge, FIFO at the w pins at the bottom).  +1 edge QKV read to FIFO.
// TOK-VERIFY on top of r3: QKV read -> FIFO +1, port -> engine +1 (in, d), engine -> w port +1, done/n_sectors +1 more, stream done after the face drains; rates kept.
`define ROW_STEP begin row_lo <= row_lo + 16'd1; row_lf <= row_lo == 16'hfffe; if (row_lf) row_hi <= row_hi + 16'd1; st_left <= st_left - 24'd1; end
module qkd_host_native_engine_ing4 (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         p_d_v,                 // face flop: a descriptor was accepted at the port on the previous edge
    output wire         p_d_rdy,
    input  wire [255:0] p_d_data,
    input  wire         p_in_v,
    output wire         p_in_rdy,
    input  wire [511:0] p_in_data,
    output wire         e_wv,
    input  wire         er_n,                  // next state of the write-face ready
    output wire [31:0]  w_addr,
    output wire [255:0] w_data,
    output wire         e_last,
    output wire [7:0]   e_tag,
    input  wire         face_idle,
    output wire         sd_fire,
    output wire [7:0]   sd_tag,
    output wire         p_busy
);
    localparam [3:0] M_RAW = 4'd0, M_QKV = 4'd1, M_ROWS = 4'd2, M_IKEY = 4'd3;

    // -- input FIFO behind the face flops (cut 20) ------------------------------------------------------------------------
    wire         in_v, in_rdy, busy;
    wire [511:0] in_data;
    reg  [511:0] fi_d0, fi_d1, fi_d2;
    reg  [1:0]   fi_n;
    reg  [2:0]   fi_rp, fi_wp;                 // one-hot
    reg          fi_rdy;
    wire         fi_push = p_in_v, fi_pop = in_v && in_rdy;
    wire [1:0]   fi_n_n = fi_n + {1'b0, fi_push} - {1'b0, fi_pop};
    assign p_in_rdy = fi_rdy;
    assign in_v = fi_n != 2'd0;
    assign in_data = ({512{fi_rp[0]}} & fi_d0) | ({512{fi_rp[1]}} & fi_d1) | ({512{fi_rp[2]}} & fi_d2);
    assign p_busy = busy || fi_n != 2'd0 || fi_n_n != 2'd0;
    always @(posedge clk) begin
        if (fi_push && fi_wp[0]) fi_d0 <= p_in_data;
        if (fi_push && fi_wp[1]) fi_d1 <= p_in_data;
        if (fi_push && fi_wp[2]) fi_d2 <= p_in_data;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            fi_n <= 2'd0; fi_rp <= 3'b001; fi_wp <= 3'b001; fi_rdy <= 1'b0;
        end else begin
            fi_n <= fi_n_n; fi_rdy <= {1'b0, fi_n_n} + {2'd0, fi_rdy} <= 3'd2;
            if (fi_push) fi_wp <= {fi_wp[1:0], fi_wp[2]};
            if (fi_pop) fi_rp <= {fi_rp[1:0], fi_rp[2]};
        end
    // write-face ready copies (cut 21): identical flops, each with its own loads
    (* keep = 1 *) reg er_m;
    (* keep = 1 *) reg er_st;
    (* keep = 1 *) reg [34:0] er_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin er_m <= 1'b0; er_st <= 1'b0; er_s <= 35'd0; end
        else begin er_m <= er_n; er_st <= er_n; er_s <= {35{er_n}}; end

    // -- descriptor queue ---------------------------------------------------------------------------------------------
    reg  [255:0] dq [0:3];
    reg  [2:0]   dq_n;
    reg  [1:0]   dq_rd, dq_wr;
    wire [255:0] dh = dq[dq_rd];
    wire         dh_v = dq_n != 3'd0;
    wire [3:0]   dh_mode = dh[3:0];
    reg          dq_rdy;
    wire         d_pop;
    wire [2:0]   dq_n_n = dq_n + {2'd0, p_d_v} - {2'd0, d_pop};
    assign p_d_rdy = dq_rdy;

    // -- QKV input: walk on the input edge --------------------------------------------------------------------------
    reg  [255:0] sd0, sd1;
    reg  [1:0]   s_full, s_fill;
    reg          qi_act, qi_slot, qi_v, qi_g;
    reg  [4:0]   qi_t;
    reg  [2:0]   qi_dg;                        // d / 16
    reg  [1:0]   qf_fmt;
    reg          qf_k2;                        // n4 == 2
    reg  [4:0]   qf_tlo, qf_thi;
    wire         gp1 = qf_fmt == 2'd0, gp2 = qf_fmt == 2'd1;
    wire         q_beat = qi_act && in_v;
    wire         hd_end = gp1 ? (qi_dg == 3'd7) : gp2 ? (qi_dg[2:1] == 2'd3) : qi_dg[2];
    wire [2:0]   dg_n = qi_dg + (gp1 ? 3'd1 : gp2 ? 3'd2 : 3'd4);
    wire         g_end = !qf_k2 || qi_g;
    wire [4:0]   t_p1 = qi_t + 5'd1;
    wire         t_end = t_p1 >= qf_thi;
    wire         q_last = hd_end && g_end && t_end && qi_v;
    wire         qi_empty = qi_act && qf_tlo >= qf_thi;

    // shared input register (cut 4)
    reg  [511:0] in_q;
    always @(posedge clk) in_q <= in_data;

    // -- I0: walk result beside in_q ------------------------------------------------------------------------------------
    reg          i0_v, i0_slot, i0_last, i0_isv;
    reg  [1:0]   i0_fmt;
    reg  [3:0]   i0_t, i0_b;                   // lane, bank of granule 0 = 9 lane + {g, d / 16}
    always @(posedge clk or negedge rst_n) if (!rst_n) i0_v <= 1'b0; else i0_v <= q_beat;
    always @(posedge clk) begin
        i0_slot <= qi_slot; i0_last <= q_last; i0_isv <= qi_v; i0_fmt <= qf_fmt; i0_t <= qi_t[3:0];
        i0_b <= 4'd9 * qi_t[3:0] + {qi_g, qi_dg};
    end
    // -- q1: first half of the quantisers (cut 5); a raw FP8 byte shares the low bits --------------------------------------
    reg  [383:0] q1_p;                          // 32 x 12
    reg  [255:0] q1_r;                          // bytes 32 .. 63 of an FP8 beat
    wire         i0_fp32 = i0_fmt == 2'd0, i0_bf16 = i0_fmt == 2'd1;
    genvar ge;
    generate
        for (ge = 0; ge < 32; ge = ge + 1) begin : g_s1
            wire [11:0] pbf, p32;
            ot_hdc_ingest_fp8q_s1 u_bf (.f({in_q[ge*16 +: 16], 16'd0}), .p(pbf));
            if (ge < 16) begin : g32
                ot_hdc_ingest_fp8q_s1 u_32 (.f(in_q[ge*32 +: 32]), .p(p32));
            end else begin : g32z
                assign p32 = pbf;                  // an FP32 beat has one granule: bytes 16 and up are not written
            end
            always @(posedge clk)
                q1_p[ge*12 +: 12] <= i0_fp32 ? p32 : i0_bf16 ? pbf : {4'd0, in_q[ge*8 +: 8]};
        end
        for (ge = 32; ge < 64; ge = ge + 1) begin : g_r1
            always @(posedge clk) q1_r[(ge-32)*8 +: 8] <= in_q[ge*8 +: 8];
        end
    endgenerate
    reg          q1_v, q1_slot, q1_last, q1_isv, q1_raw;
    reg  [3:0]   q1_t, q1_b;
    reg  [3:1]   q1_use;
    always @(posedge clk or negedge rst_n) if (!rst_n) q1_v <= 1'b0; else q1_v <= i0_v;
    always @(posedge clk) begin
        q1_slot <= i0_slot; q1_last <= i0_last; q1_isv <= i0_isv; q1_t <= i0_t; q1_b <= i0_b;
        q1_raw <= !(i0_fp32 || i0_bf16);
        q1_use <= {!(i0_fp32 || i0_bf16), !(i0_fp32 || i0_bf16), !i0_fp32};   // granules a beat: 1 / 2 / 4
    end
    // -- I1: codes, one-hot bank select ------------------------------------------------------------------------------------
    reg  [511:0] i1_code;
    reg  [15:0]  i1_sel0, i1_sel1, i1_sel2, i1_sel3;
    reg          i1_v, i1_slot, i1_last, i1_isv;
    reg  [4:0]   i1_a;
    generate
        for (ge = 0; ge < 64; ge = ge + 1) begin : g_s2
            if (ge < 32) begin : gq
                wire [7:0] q2;
                ot_hdc_ingest_fp8q_s2 u_s2 (.p(q1_p[ge*12 +: 12]), .q(q2));
                always @(posedge clk) i1_code[ge*8 +: 8] <= q1_raw ? q1_p[ge*12 +: 8] : q2;
            end else begin : gr
                always @(posedge clk) i1_code[ge*8 +: 8] <= q1_r[(ge-32)*8 +: 8];
            end
        end
    endgenerate
    wire [3:0] sb0 = q1_b, sb1 = q1_b + 4'd1, sb2 = q1_b + 4'd2, sb3 = q1_b + 4'd3;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            i1_v <= 1'b0; i1_sel0 <= 16'd0; i1_sel1 <= 16'd0; i1_sel2 <= 16'd0; i1_sel3 <= 16'd0;
        end else begin
            i1_v <= q1_v;
            i1_sel0 <= q1_v              ? (16'd1 << sb0) : 16'd0;
            i1_sel1 <= q1_v && q1_use[1] ? (16'd1 << sb1) : 16'd0;
            i1_sel2 <= q1_v && q1_use[2] ? (16'd1 << sb2) : 16'd0;
            i1_sel3 <= q1_v && q1_use[3] ? (16'd1 << sb3) : 16'd0;
        end
    always @(posedge clk) begin i1_slot <= q1_slot; i1_last <= q1_last; i1_isv <= q1_isv; i1_a <= {q1_slot, q1_t}; end
    // -- I1B: per-quadrant copy of the beat (cut 13) ---------------------------------------------------------------------
    // flat kept vectors: a generate-scope reg behind an alias wire lost its keep in the face-port emission (ib_code[n] became the reg name) and folded to one bank
    (* keep = 1 *) reg [2047:0] ib_all;
    reg  [15:0]  ib_sel0, ib_sel1, ib_sel2, ib_sel3;
    reg          ib_v, ib_slot, ib_last, ib_isv;
    reg  [4:0]   ib_a;
    // I1H (cut 15): two kept half copies; quadrants 0, 1 (banks 0..7) read half 0, quadrants 2, 3 (banks 8..15) half 1
    (* keep = 1 *) reg [1023:0] ih_all;
    reg  [15:0]  ih_sel0, ih_sel1, ih_sel2, ih_sel3;
    reg          ih_v, ih_slot, ih_last, ih_isv;
    reg  [4:0]   ih_a;
    always @(posedge clk) ih_all <= {2{i1_code}};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ih_v <= 1'b0; ih_sel0 <= 16'd0; ih_sel1 <= 16'd0; ih_sel2 <= 16'd0; ih_sel3 <= 16'd0; end
        else begin ih_v <= i1_v; ih_sel0 <= i1_sel0; ih_sel1 <= i1_sel1; ih_sel2 <= i1_sel2; ih_sel3 <= i1_sel3; end
    always @(posedge clk) begin ih_slot <= i1_slot; ih_last <= i1_last; ih_isv <= i1_isv; ih_a <= i1_a; end
    always @(posedge clk) ib_all <= {ih_all[1023:512], ih_all[1023:512], ih_all[511:0], ih_all[511:0]};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ib_v <= 1'b0; ib_sel0 <= 16'd0; ib_sel1 <= 16'd0; ib_sel2 <= 16'd0; ib_sel3 <= 16'd0; end
        else begin ib_v <= ih_v; ib_sel0 <= ih_sel0; ib_sel1 <= ih_sel1; ib_sel2 <= ih_sel2; ib_sel3 <= ih_sel3; end
    always @(posedge clk) begin ib_slot <= ih_slot; ib_last <= ih_last; ib_isv <= ih_isv; ib_a <= ih_a; end

    // -- drain fields, loaded at drain start ---------------------------------------------------------------------------
    reg          qo_act, qo_slot, qo_v, qo_g;
    reg  [5:0]   qo_s;
    wire [255:0] sd_n = qo_slot ? sd0 : sd1;   // the slot the drain moves to
    reg          od_fence, od_k2;
    reg  [7:0]   od_tag;
    reg  [5:0]   od_lay;
    reg  [8:0]   od_tb;
    reg  [4:0]   od_tlo, od_thi, od_thim1;
    wire [3:0]   t0 = qo_s[5:2];
    wire [4:0]   t5 = {1'b0, t0};
    wire         in_lane = (t5 >= od_tlo) && (t5 < od_thi);
    reg  [3:0]   cred;                          // sectors issued, not yet off the FIFO (cut 8)
    wire         q_iss = qo_act && !cred[3];
    wire         q_hlast = qo_s == 6'd63;
    wire         o_g_end = !od_k2 || qo_g;
    wire         q_wlast = qo_v && o_g_end && q_hlast;
    wire         native_last = qo_v && o_g_end && qo_s[1:0] == 2'd3 && t5 == od_thim1;
    wire [12:0]  nt = {od_tb, t0};
    wire [22:0]  o_a = {od_lay, qo_v, qo_g, nt[6], nt[12:9], nt[5:3], nt[8:7], qo_s[1:0], nt[2:0]};   // 8'd0 and nt[13] = 0 left out
    wire [3:0]   rb0 = 4'd9 * t0 + {qo_g, qo_s[1:0], 1'b0};

    // -- banks, generate names kept: macro sites u_eng.g_qp.g_bm.g_mb[n].u_mk / u_mv -------------------------------------
    reg          kr, vr;
    reg  [4:0]   r_a, w_a;
    reg          s1_v, s2_v, s3_v, e1_v, s1_isv, s2_isv, s1_last, s2_last, s3_last, e1_last;
    reg  [7:0]   s1_tag, s2_tag, s3_tag, e1_tag;
    reg  [22:0]  s1_a, s2_a, s3_a, e1_a;
    reg  [3:0]   s1_b0, s2_b0;
    wire [3:0]   s2_b1 = s2_b0 + 4'd1;
    reg  [15:0]  bank_v, sel0, sel1;
    reg          fset_r, fslot_r, i2_v;
    wire [127:0] bq [0:15];
    genvar gb;
    generate if (1) begin : g_qp if (1) begin : g_bm
        for (gb = 0; gb < 16; gb = gb + 1) begin : g_mb
            reg          wk_v, wv_v;
            localparam integer QB = (gb / 8) * 2 + ((gb / 2) % 2);
            wire [511:0] w_code = ib_all[QB*512 +: 512];
            reg  [127:0] w_d;
            wire [127:0] mko, mvo;
            reg  [127:0] ck_q, cv_q;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin wk_v <= 1'b0; wv_v <= 1'b0; end
                else begin
                    wk_v <= !ib_isv && (ib_sel0[gb] || ib_sel1[gb] || ib_sel2[gb] || ib_sel3[gb]);
                    wv_v <=  ib_isv && (ib_sel0[gb] || ib_sel1[gb] || ib_sel2[gb] || ib_sel3[gb]);
                end
            always @(posedge clk)
                w_d <= ({128{ib_sel0[gb]}} & w_code[127:0])   | ({128{ib_sel1[gb]}} & w_code[255:128]) |
                       ({128{ib_sel2[gb]}} & w_code[383:256]) | ({128{ib_sel3[gb]}} & w_code[511:384]);
            ot_sram_1r1w_32x128_m1 u_mk (.clk(clk), .r_ce_in(kr), .r_addr_in(r_a), .rd_out(mko),
                .w_ce_in(wk_v), .w_addr_in(w_a), .wd_in(w_d), .w_mask_in({128{1'b1}}));
            ot_sram_1r1w_32x128_m1 u_mv (.clk(clk), .r_ce_in(vr), .r_addr_in(r_a), .rd_out(mvo),
                .w_ce_in(wv_v), .w_addr_in(w_a), .wd_in(w_d), .w_mask_in({128{1'b1}}));
            always @(posedge clk) begin ck_q <= mko; cv_q <= mvo; end      // capture flops on every macro output
            assign bq[gb] = bank_v[gb] ? cv_q : ck_q;
        end
    end end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            kr <= 1'b0; vr <= 1'b0; s1_v <= 1'b0; s2_v <= 1'b0; s3_v <= 1'b0; e1_v <= 1'b0; fset_r <= 1'b0; i2_v <= 1'b0;
            bank_v <= 16'd0; sel0 <= 16'd0; sel1 <= 16'd0;
        end else begin
            kr <= q_iss && !qo_v; vr <= q_iss && qo_v;
            s1_v <= q_iss && in_lane; s2_v <= s1_v; s3_v <= s2_v; e1_v <= s3_v;
            fset_r <= ib_v && ib_last; i2_v <= ib_v;
            bank_v <= s2_isv ? ((16'd1 << s2_b0) | (16'd1 << s2_b1)) : 16'd0;
            sel0   <= s2_v ? (16'd1 << s2_b0) : 16'd0;
            sel1   <= s2_v ? (16'd1 << s2_b1) : 16'd0;
        end
    always @(posedge clk) begin
        w_a <= ib_a; fslot_r <= ib_slot; r_a <= {qo_slot, t0};
        s1_isv <= qo_v; s1_last <= native_last && od_fence; s1_tag <= od_tag; s1_a <= o_a; s1_b0 <= rb0;
        s2_isv <= s1_isv; s2_last <= s1_last; s2_tag <= s1_tag; s2_a <= s1_a; s2_b0 <= s1_b0;
        s3_last <= s2_last; s3_tag <= s2_tag; s3_a <= s2_a;
        e1_last <= s3_last; e1_tag <= s3_tag; e1_a <= s3_a;
    end
    // quadrant read registers (cut 7): quadrants {0,1,4,5} {2,3,6,7} {8,9,12,13} {10,11,14,15} follow the macro plan
    reg  [511:0] qr0, qr1;
    genvar qd;
    generate
        for (qd = 0; qd < 4; qd = qd + 1) begin : g_qd
            localparam integer B0 = (qd == 0) ? 0 : (qd == 1) ? 2 : (qd == 2) ? 8 : 10;
            always @(posedge clk) begin
                qr0[qd*128 +: 128] <= ({128{sel0[B0]}} & bq[B0]) | ({128{sel0[B0+1]}} & bq[B0+1]) |
                           ({128{sel0[B0+4]}} & bq[B0+4]) | ({128{sel0[B0+5]}} & bq[B0+5]);
                qr1[qd*128 +: 128] <= ({128{sel1[B0]}} & bq[B0]) | ({128{sel1[B0+1]}} & bq[B0+1]) |
                           ({128{sel1[B0+4]}} & bq[B0+4]) | ({128{sel1[B0+5]}} & bq[B0+5]);
            end
        end
    endgenerate
    wire [255:0] sec = {qr1[127:0] | qr1[255:128] | qr1[383:256] | qr1[511:384],
                        qr0[127:0] | qr0[255:128] | qr0[383:256] | qr0[511:384]};
    // output FIFO: 8 entries, one sector a cycle
    reg  [255:0] fq_d [0:7];
    reg  [22:0]  fq_a [0:7];
    reg  [8:0]   fq_t [0:7];                    // {fenced last, tag}
    reg  [2:0]   fq_wp;
    reg  [3:0]   fq_n;
    reg          qk_wv;                         // fq_n != 0 (cut 12)
    wire         fq_pop = qk_wv && er_m;
    reg          e2_v, e2_last;
    reg  [7:0]   e2_tag;
    reg  [22:0]  e2_a;
    reg  [255:0] sec_q;
    wire [3:0]   fq_n_n = fq_n + (e2_v ? 4'd1 : 4'd0) - (fq_pop ? 4'd1 : 4'd0);
    wire         fq_ne_n = fq_n_n != 4'd0;
    wire [2047:0] fd_all = {fq_d[7], fq_d[6], fq_d[5], fq_d[4], fq_d[3], fq_d[2], fq_d[1], fq_d[0]};
    wire [183:0] fa_all = {fq_a[7], fq_a[6], fq_a[5], fq_a[4], fq_a[3], fq_a[2], fq_a[1], fq_a[0]};
    wire [71:0]  ft_all = {fq_t[7], fq_t[6], fq_t[5], fq_t[4], fq_t[3], fq_t[2], fq_t[1], fq_t[0]};
    (* keep = 1 *) reg [34:0] qk_s;             // per-slice qk_wv
    wire [255:0] qp_wd;
    wire [22:0]  fa;
    wire [8:0]   ft;
    genvar gs, gk;
    generate for (gs = 0; gs < 35; gs = gs + 1) begin : g_rs
        localparam integer W = (gs < 32) ? 8 : (gs == 32) ? 12 : (gs == 33) ? 11 : 9;
        (* keep = 1 *) reg [7:0] oh;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) oh <= 8'd1;
            else if (qk_s[gs] && er_s[gs]) oh <= {oh[6:0], oh[7]};
        wire [W-1:0] t_or [0:8];
        assign t_or[0] = {W{1'b0}};
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_k
            wire [W-1:0] w_k;
            if (gs < 32) begin : gd assign w_k = fd_all[gk*256 + gs*8 +: 8]; end
            else if (gs == 32) begin : ga0 assign w_k = fa_all[gk*23 +: 12]; end
            else if (gs == 33) begin : ga1 assign w_k = fa_all[gk*23 + 12 +: 11]; end
            else begin : gt assign w_k = ft_all[gk*9 +: 9]; end
            assign t_or[gk+1] = t_or[gk] | ({W{oh[gk]}} & w_k);
        end
        if (gs < 32) begin : gd assign qp_wd[gs*8 +: 8] = t_or[8]; end
        else if (gs == 32) begin : ga0 assign fa[11:0] = t_or[8]; end
        else if (gs == 33) begin : ga1 assign fa[22:12] = t_or[8]; end
        else begin : gt assign ft = t_or[8]; end
    end endgenerate
    wire [31:0]  qp_wa = {8'd0, fa[22:14], 1'b0, fa[13:0]};
    assign       e_last = qk_s[34] && ft[8];
    assign       e_tag = ft[7:0];
    always @(posedge clk) begin sec_q <= sec; e2_a <= e1_a; e2_last <= e1_last; e2_tag <= e1_tag; end
    always @(posedge clk) if (e2_v) begin fq_d[fq_wp] <= sec_q; fq_a[fq_wp] <= e2_a; fq_t[fq_wp] <= {e2_last, e2_tag}; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fq_wp <= 3'd0; fq_n <= 4'd0; qk_wv <= 1'b0; qk_s <= 35'd0; cred <= 4'd0; e2_v <= 1'b0; end
        else begin
            e2_v <= e1_v;
            if (e2_v) fq_wp <= fq_wp + 3'd1;
            fq_n <= fq_n_n; qk_wv <= fq_ne_n; qk_s <= {35{fq_ne_n}};
            cred <= cred + ((q_iss && in_lane) ? 4'd1 : 4'd0) - (fq_pop ? 4'd1 : 4'd0);
        end
    wire qp_busy = i0_v || q1_v || i1_v || ih_v || ib_v || i2_v || fset_r || cred != 4'd0 || s_fill != 2'b00;

    // -- stream path ---------------------------------------------------------------------------------------------------
    wire         q_disp, s_disp;
    reg  [255:0] ra [0:7];
    reg  [8:0]   ra_n;
    reg  [7:0]   ra_rp;
    reg  [2:0]   ra_wp;
    wire [2:0]   ra_wq = ra_wp + 3'd1;
    wire [2047:0] ra_all = {ra[7], ra[6], ra[5], ra[4], ra[3], ra[2], ra[1], ra[0]};
    wire [7:0]   ra_rp_n;                       // ra_rp next state
    wire [2:0]   ra_w1_n;                       // w1 next state, late-select form: no adder after ra_adv
    reg  [255:0] wq0, wq1;                      // word registers (cut 14)
    wire [255:0] ra_word, ra_wnext;
    wire [255:0] ra_sh;
    wire [511:0] wq_all = {wq1, wq0};
    genvar gy;
    generate for (gy = 0; gy < 32; gy = gy + 1) begin : g_ry
        (* keep = 1 *) reg [2:0] w0, w1;
        (* keep = 1 *) reg [4:0] off;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin w0 <= 3'd0; w1 <= 3'd1; end
            else begin w0 <= ra_rp_n[7:5]; w1 <= ra_w1_n; end
        always @(posedge clk) off <= ra_rp[4:0];
        wire [63:0] by0, by1;
        assign ra_word[gy*8 +: 8]  = ra_all[{w0, 8'd0} + gy*8 +: 8];
        assign ra_wnext[gy*8 +: 8] = ra_all[{w1, 8'd0} + gy*8 +: 8];
        wire [255:0] win = wq_all[gy*8 +: 256];
        assign ra_sh[gy*8 +: 8] = win[{off, 3'b000} +: 8];
    end endgenerate
    reg  [255:0] sh_r;                          // the next 32 bytes, ROWS / IKEY (cut 10)
    always @(posedge clk) sh_r <= ra_sh[255:0];
    reg          push_q;
    reg          st_act, st_pad;
    reg  [3:0]   st_mode;
    reg  [255:0] st_d;
    reg  [15:0]  row_lo, row_hi;
    reg          row_lf;                       // row_lo == 16'hffff (cut 25)
    wire [31:0]  st_row = {row_hi, row_lo};
    reg  [23:0]  st_left;
    reg  [15:0]  ra_lo, ra_hi;                 // RAW write address (cut 24)
    reg          ra_lf;
    reg  [15:0]  st_rem;
    reg  [4:0]   st_sec;
    reg  [2:0]   st_ph;
    reg  [15:0]  st_beats;
    reg  [255:0] sc0, sc1;
    wire         is_raw = st_mode == M_RAW, is_rows = st_mode == M_ROWS, is_ikey = st_mode == M_IKEY;
    // address terms: three registered stages (cut 9)
    wire [1:0]   s_ldie = st_d[217:216];
    wire [7:0]   s_die  = st_d[231:224];
    wire [1:0]   s_lns  = st_d[233:232];
    wire [31:0]  s_grp  = st_row >> 4;
    wire         s_mine = (s_ldie == 2'd0) || ((s_grp & ((32'd1 << s_ldie) - 32'd1)) == {24'd0, s_die});
    wire [31:0]  s_gd   = s_grp >> s_ldie;
    wire [2:0]   s_stk  = s_gd[2:0] & ((3'd1 << s_lns) - 3'd1);
    wire [31:0]  s_gs   = s_gd >> s_lns;
    wire [31:0]  s_ring = st_d[143:112];
    wire [31:0]  s_local = (s_ring != 0) ? (st_row & (s_ring - 32'd1)) : ((s_gs << 4) | (st_row & 32'd15));
    wire [15:0]  s_rb = st_d[183:168];
    wire [4:0]   s_pitch = st_d[84:80];
    reg          ap_ok, ap_ok0, ap_ok0m, ap_ok1, ap_ok1m;
    reg  [31:0]  ap0m_base, ap0m_prod, ap0m_local, ap0m_gs, ap0m_row;
    reg  [4:0]   ap0m_pitch;
    reg          ap0m_mine;
    reg  [31:0]  ap1m_rbase, ap1m_p0, ap1m_p1, ap1m_gs, ap1m_row;
    reg          ap1m_mine;
    reg  [31:0]  ap0_base, ap0_stride, ap0_local, ap0_gs, ap0_row;
    reg  [2:0]   ap0_stk;
    reg  [4:0]   ap0_pitch;
    reg          ap0_mine, ap0_ringz;
    reg  [31:0]  ap1_rbase, ap1_local, ap1_gs, ap1_row;
    reg  [4:0]   ap1_pitch;
    reg          ap1_mine;
    reg  [31:0]  ap_raddr, ap_kcode, ap_kscal;
    reg          ap_mine;
    wire [31:0]  a2_sb    = ap1m_gs >> 6;
    wire [5:0]   a2_q     = ap1m_gs[5:0];
    wire [31:0]  a2_blk   = ap1m_rbase + (a2_sb << 11) + (a2_sb << 7);
    wire [31:0]  a2_raddr = ap1m_rbase + ap1m_p0 + ap1m_p1;   // local x pitch in two partial products
    wire [31:0]  a2_kcode = a2_blk + ((32'd1 + {28'd0, a2_q[5:2]}) << 7) + ({30'd0, a2_q[1:0]} << 5) + ((ap1m_row & 32'd15) << 1);
    wire [31:0]  a2_kscal = a2_blk + ({26'd0, a2_q} << 1);
    wire         ap_go = ap_ok;
    // one step: RAW direct, ROWS / IKEY from registers loaded one edge after the previous step (cut 10)
    reg          st_ok_r, st_end_r;
    reg  [5:0]   take_r;
    reg  [31:0]  st_wa_r;
    wire         st_run = st_act && !st_pad;
    wire         raw_have = st_run && is_raw && ra_n[8:5] != 4'd0;
    reg          rawq_v;                        // wq0 holds the next RAW word (cut 14)
    reg          ok0;                           // second bubble (cut 14)
    wire         raw_ok = st_run && is_raw && rawq_v;
    wire [5:0]   k_take = (st_rem > 16'd32) ? 6'd32 : st_rem[5:0];
    wire         ik_sc  = st_ph >= 3'd3;
    wire         ik_low = st_ph < 3'd2;
    wire         st_adv = raw_ok || st_ok_r;
    wire         st_wv  = raw_ok || (st_ok_r && ap_mine && (is_rows || (is_ikey && st_ph != 3'd2)));
    wire         st_go  = st_adv && (!st_wv || er_st);
    wire         raw_load = raw_have && (!rawq_v || st_go);
    wire         ra_adv = is_raw ? raw_load : st_go;
    always @(posedge clk) begin
        if (!is_raw || raw_load) wq0 <= ra_word;
        wq1 <= ra_wnext;
    end
    wire         need_ok = is_rows ? (ra_n >= {3'd0, k_take}) : is_ikey ? (ik_sc ? 1'b1 : ik_low ? ra_n[8:5] != 4'd0 : ra_n >= 9'd4) : 1'b0;
    wire [5:0]   st_pop = is_raw ? 6'd32 : take_r;
    wire         st_row_end = st_end_r;
    genvar mb;
    // cut 23: next states of the select inputs, one registered copy per slice
    wire [3:0]   st_mode_n = s_disp ? dh_mode : st_mode;
    wire [2:0]   st_ph_n = (st_go && is_ikey) ? (st_ph == 3'd2 ? (st_row[3:0] == 4'd15 ? 3'd3 : 3'd0) : st_ph == 3'd4 ? 3'd0 : st_ph + 3'd1) : s_disp ? 3'd0 : st_ph;
    wire [5:0]   take_n = (st_run && !is_raw) ? (is_rows ? k_take : ik_low ? 6'd32 : st_ph == 3'd2 ? 6'd4 : 6'd0) : take_r;
    wire         raw_n = st_mode_n == M_RAW, sc_n = st_mode_n == M_IKEY && st_ph_n >= 3'd3;
    wire [255:0] st_wd;
    wire [31:0]  st_wa;
    (* keep = 1 *) reg [33:0] sl_raw;
    (* keep = 1 *) reg [31:0] sl_sc, sl_p0;
    (* keep = 1 *) reg [31:0] mb_q;
    always @(posedge clk) begin sl_raw <= {34{raw_n}}; sl_sc <= {32{sc_n}}; sl_p0 <= {32{st_ph_n[0]}}; end
    generate for (mb = 0; mb < 32; mb = mb + 1) begin : g_sw
        always @(posedge clk) mb_q[mb] <= take_n[5] || (5'(mb) < take_n[4:0]);
        assign st_wd[mb*8 +: 8] = sl_raw[mb] ? wq0[mb*8 +: 8] : sl_sc[mb] ? (sl_p0[mb] ? sc0[mb*8 +: 8] : sc1[mb*8 +: 8]) : (sh_r[mb*8 +: 8] & {8{mb_q[mb]}});
    end endgenerate
    assign st_wa = {sl_raw[33] ? {ra_hi, ra_lo[15:14]} : st_wa_r[31:14], sl_raw[32] ? ra_lo[13:0] : st_wa_r[13:0]};
    // cut 19 (KV-ING-5 vF): carry-select sums for st_wa_r, exact identities kc_sum == ap_kcode + st_ph, ks_sum == ap_kscal + (st_ph == 4)
    wire [3:0]   kc_lo  = {1'b0, ap_kcode[2:0]} + {1'b0, st_ph};
    wire [28:0]  kc_hi1 = ap_kcode[31:3] + 29'd1;
    wire [31:0]  kc_sum = {kc_lo[3] ? kc_hi1 : ap_kcode[31:3], kc_lo[2:0]};
    wire [3:0]   ks_lo  = {1'b0, ap_kscal[2:0]} + {3'd0, st_ph == 3'd4};
    wire [28:0]  ks_hi1 = ap_kscal[31:3] + 29'd1;
    wire [31:0]  ks_sum = {ks_lo[3] ? ks_hi1 : ap_kscal[31:3], ks_lo[2:0]};

    // -- ports ---------------------------------------------------------------------------------------------------------
    assign e_wv   = qk_wv || st_wv;
    assign w_addr = {qk_s[33] ? qp_wa[31:14] : st_wa[31:14], qk_s[32] ? qp_wa[13:0] : st_wa[13:0]};
    genvar gw;
    generate for (gw = 0; gw < 32; gw = gw + 1) begin : g_wd
        assign w_data[gw*8 +: 8] = qk_s[gw] ? qp_wd[gw*8 +: 8] : st_wd[gw*8 +: 8];
    end endgenerate
    wire [7:0]   ra_rp_a = ra_rp + {2'd0, st_pop};
    assign ra_rp_n = st_pad ? 8'd0 : ra_adv ? ra_rp_a : ra_rp;
    assign ra_w1_n = st_pad ? 3'd1 : ra_adv ? ra_rp_a[7:5] + 3'd1 : ra_rp[7:5] + 3'd1;
    reg    sd_pend;                             // a stream descriptor's done, waits for the face to drain (cut 22)
    assign sd_fire = sd_pend && face_idle;
    assign sd_tag = st_d[15:8];
    wire   ra_room = ra_n <= 9'd192;
    wire   beats_nz = st_beats != 16'd0;
    wire   ra_push = st_run && in_v && ra_room && beats_nz && !push_q;
    wire   pad_take = st_act && st_pad && in_v && beats_nz;
    assign in_rdy = qi_act || (st_act && (st_pad ? beats_nz : (ra_room && beats_nz && !push_q)));
    assign busy = dh_v || qi_act || qo_act || st_act || s_full != 2'b00 || qp_busy || sd_pend;

    // -- dispatch --------------------------------------------------------------------------------------------------------
    wire nslot = ~qi_slot;
    wire nfull = nslot ? s_full[1] : s_full[0];
    wire nfill = nslot ? s_fill[1] : s_fill[0];
    assign q_disp = dh_v && !sd_pend && dh_mode == M_QKV && !qi_act && !st_act && !nfull && !(qo_act && qo_slot == nslot) && !nfill;
    assign s_disp = dh_v && !sd_pend && dh_mode != M_QKV && !qi_act && !st_act && !qo_act && s_full == 2'b00 && !qp_busy;
    assign d_pop = q_disp || s_disp;
    wire o_next_full = qo_slot ? s_full[0] : s_full[1];
    integer j, sci;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dq_n <= 3'd0; dq_rd <= 2'd0; dq_wr <= 2'd0; dq_rdy <= 1'b0;
            s_full <= 2'b00; s_fill <= 2'b00; qi_act <= 1'b0; qi_slot <= 1'b0; qo_act <= 1'b0; qo_slot <= 1'b0;
            st_act <= 1'b0; st_pad <= 1'b0; ra_n <= 9'd0; ra_rp <= 8'd0; ra_wp <= 3'd0; push_q <= 1'b0; rawq_v <= 1'b0; ok0 <= 1'b0;
            sd_pend <= 1'b0;
            qi_t <= 5'd0; qi_g <= 1'b0; qi_dg <= 3'd0; qi_v <= 1'b0; qo_v <= 1'b0; qo_g <= 1'b0; qo_s <= 6'd0;
            st_ph <= 3'd0; st_beats <= 16'd0; row_lo <= 16'd0; row_hi <= 16'd0; row_lf <= 1'b0; st_left <= 24'd0; st_rem <= 16'd0; st_sec <= 5'd0;
            st_ok_r <= 1'b0;
        end else begin
            if (sd_fire) sd_pend <= 1'b0;
            dq_rdy <= {1'b0, dq_n_n} + {3'd0, dq_rdy} <= 4'd3;
            if (p_d_v) dq_wr <= dq_wr + 2'd1;
            if (d_pop) dq_rd <= dq_rd + 2'd1;
            dq_n <= dq_n_n;

            if (q_disp) begin
                qi_slot <= nslot; qi_act <= 1'b1;
                qi_t <= dh[228:224]; qi_g <= 1'b0; qi_dg <= 3'd0; qi_v <= 1'b0;
                if (nslot) s_fill[1] <= 1'b1; else s_fill[0] <= 1'b1;
            end
            if (s_disp) begin
                st_act <= 1'b1; st_pad <= 1'b0;
                row_lo <= (dh_mode == M_RAW) ? 16'd0 : dh[159:144];
                row_hi <= (dh_mode == M_RAW) ? 16'd0 : {8'd0, dh[167:160]};
                row_lf <= (dh_mode != M_RAW) && dh[159:144] == 16'hffff;
                st_left <= (dh_mode == M_RAW) ? dh[167:144] : {8'd0, dh[199:184]};
                st_rem <= dh[183:168]; st_sec <= 5'd0; st_ph <= 3'd0; st_beats <= dh[255:240];
            end
            // QKV input
            if (q_beat) begin
                qi_dg <= dg_n;
                if (hd_end) begin
                    if (g_end) begin
                        qi_g <= 1'b0;
                        if (t_end) begin qi_t <= qf_tlo; qi_v <= 1'b1; end else qi_t <= t_p1;
                    end else qi_g <= 1'b1;
                end
                if (q_last) qi_act <= 1'b0;
            end
            for (j = 0; j < 2; j = j + 1) begin
                if (qi_empty && qi_slot == (j == 1)) begin qi_act <= 1'b0; s_full[j] <= 1'b1; s_fill[j] <= 1'b0; end
                if (fset_r && fslot_r == (j == 1)) begin s_full[j] <= 1'b1; s_fill[j] <= 1'b0; end
                if (q_iss && q_wlast && qo_slot == (j == 1)) s_full[j] <= 1'b0;
            end
            // QKV drain
            if (!qo_act && o_next_full) begin
                qo_act <= 1'b1; qo_slot <= ~qo_slot; qo_v <= 1'b0; qo_g <= 1'b0; qo_s <= 6'd0;
            end
            if (q_iss) begin
                if (q_hlast) begin
                    qo_s <= 6'd0;
                    if (o_g_end) begin qo_g <= 1'b0; qo_v <= 1'b1; end else qo_g <= 1'b1;
                end else qo_s <= qo_s + 6'd1;
                if (q_wlast) qo_act <= 1'b0;
            end
            // stream
            push_q <= ra_push;
            if (push_q) ra_wp <= ra_wp + 3'd2;
            if (ra_push || pad_take) st_beats <= st_beats - 16'd1;
            if (st_pad) begin
                ra_n <= 9'd0; ra_rp <= 8'd0; ra_wp <= 3'd0; rawq_v <= 1'b0;
                if (!beats_nz || (pad_take && st_beats == 16'd1)) begin
                    st_act <= 1'b0; st_pad <= 1'b0;
                    if (st_d[7]) sd_pend <= 1'b1;
                end
            end else begin
                ra_n <= ra_n + (push_q ? 9'd64 : 9'd0) - (ra_adv ? {3'd0, st_pop} : 9'd0);
                ra_rp <= ra_rp_n;
                rawq_v <= raw_load || (rawq_v && !st_go);
            end
            ok0 <= st_run && !is_raw && ap_go && !st_go && need_ok;
            st_ok_r <= ok0 && st_run && !is_raw && ap_go && !st_go && need_ok;
            if (st_go) begin
                if (is_raw) begin
                    `ROW_STEP
                    if (st_left == 24'd1) st_pad <= 1'b1;
                end else if (is_rows) begin
                    st_rem <= st_rem - {10'd0, take_r};
                    if (!st_row_end) begin
                        if (ap_mine) st_sec <= st_sec + 5'd1;
                    end else begin
                        st_sec <= 5'd0; st_rem <= s_rb; `ROW_STEP
                        if (st_left == 24'd1) st_pad <= 1'b1;
                    end
                end else if (is_ikey) begin
                    if (st_ph == 3'd2) begin
                        if (st_row[3:0] == 4'd15) st_ph <= 3'd3;
                        else begin st_ph <= 3'd0; `ROW_STEP end
                    end else if (st_ph == 3'd4) begin
                        st_ph <= 3'd0; `ROW_STEP
                        if (st_left == 24'd1) st_pad <= 1'b1;
                    end else st_ph <= st_ph + 3'd1;
                end
            end
            if (st_run && st_left == 24'd0 && !s_disp) st_pad <= 1'b1;
        end
    end
    // data registers without reset; a write is valid-qualified
    always @(posedge clk) begin
        if (p_d_v) dq[dq_wr] <= p_d_data;
        if (q_disp) begin
            if (nslot) sd1 <= dh; else sd0 <= dh;
            qf_fmt <= dh[5:4]; qf_k2 <= dh[217]; qf_tlo <= dh[228:224]; qf_thi <= dh[236:232];
        end
        if (s_disp) begin st_mode <= dh_mode; st_d <= dh; ra_lo <= dh[31:16]; ra_hi <= dh[47:32]; ra_lf <= dh[31:16] == 16'hffff; end
        if (st_go && is_raw) begin ra_lo <= ra_lo + 16'd1; ra_lf <= ra_lo == 16'hfffe; if (ra_lf) ra_hi <= ra_hi + 16'd1; end
        if (!qo_act && o_next_full) begin
            od_fence <= sd_n[7]; od_tag <= sd_n[15:8]; od_k2 <= sd_n[217];
            od_lay <= sd_n[217] ? sd_n[37:32] : sd_n[36:31]; od_tb <= sd_n[30:22];
            od_tlo <= sd_n[228:224]; od_thi <= sd_n[236:232]; od_thim1 <= sd_n[236:232] - 5'd1;
        end
        if (push_q) begin ra[ra_wp] <= in_q[255:0]; ra[ra_wq] <= in_q[511:256]; end
        if (st_run && !is_raw) begin
            take_r <= take_n;
            st_end_r <= ap_mine ? (st_sec + 5'd1 >= s_pitch) : (st_rem <= 16'd32);
            st_wa_r <= is_rows ? (ap_raddr + {27'd0, st_sec}) : ik_sc ? ks_sum : kc_sum;
        end
        if (st_go && is_ikey && st_ph == 3'd2) begin
            for (sci = 0; sci < 8; sci = sci + 1) begin
                if (st_row[3:0] == sci)     sc0[sci*32 +: 32] <= sh_r[31:0];
                if (st_row[3:0] == sci + 8) sc1[sci*32 +: 32] <= sh_r[31:0];
            end
        end
    end
    wire ap_inval = s_disp || (st_go && (is_rows ? st_row_end : is_ikey ? ((st_ph == 3'd2 && st_row[3:0] != 4'd15) || st_ph == 3'd4) : 1'b0));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ap_ok0 <= 1'b0; ap_ok0m <= 1'b0; ap_ok1 <= 1'b0; ap_ok1m <= 1'b0; ap_ok <= 1'b0;
            ap0m_base <= 32'd0; ap0m_prod <= 32'd0; ap0m_local <= 32'd0; ap0m_gs <= 32'd0; ap0m_row <= 32'd0; ap0m_pitch <= 5'd0; ap0m_mine <= 1'b0;
            ap1m_rbase <= 32'd0; ap1m_p0 <= 32'd0; ap1m_p1 <= 32'd0; ap1m_gs <= 32'd0; ap1m_row <= 32'd0; ap1m_mine <= 1'b0;
            ap0_base <= 32'd0; ap0_stride <= 32'd0; ap0_local <= 32'd0; ap0_gs <= 32'd0; ap0_row <= 32'd0; ap0_stk <= 3'd0;
            ap0_pitch <= 5'd0; ap0_mine <= 1'b0; ap0_ringz <= 1'b0;
            ap1_rbase <= 32'd0; ap1_local <= 32'd0; ap1_gs <= 32'd0; ap1_row <= 32'd0; ap1_pitch <= 5'd0; ap1_mine <= 1'b0;
            ap_raddr <= 32'd0; ap_kcode <= 32'd0; ap_kscal <= 32'd0; ap_mine <= 1'b0;
        end else begin
            ap_ok0 <= !ap_inval && st_act;
            ap_ok0m <= !ap_inval && st_act && ap_ok0;
            ap_ok1 <= !ap_inval && st_act && ap_ok0m;
            ap_ok1m <= !ap_inval && st_act && ap_ok1;
            ap_ok  <= !ap_inval && st_act && ap_ok1m;
            ap0_base <= st_d[47:16]; ap0_stride <= st_d[79:48]; ap0_ringz <= s_ring == 32'd0; ap0_stk <= s_stk;
            ap0_local <= s_local; ap0_gs <= s_gs; ap0_row <= st_row; ap0_pitch <= s_pitch; ap0_mine <= s_mine;
            ap0m_base <= ap0_base; ap0m_prod <= ap0_ringz ? ap0_stk * ap0_stride : 32'd0; ap0m_local <= ap0_local; ap0m_gs <= ap0_gs;
            ap0m_row <= ap0_row; ap0m_pitch <= ap0_pitch; ap0m_mine <= ap0_mine;
            ap1_rbase <= ap0m_base + ap0m_prod; ap1_local <= ap0m_local; ap1_gs <= ap0m_gs;
            ap1_row <= ap0m_row; ap1_pitch <= ap0m_pitch; ap1_mine <= ap0m_mine;
            ap1m_rbase <= ap1_rbase; ap1m_p0 <= ap1_local * ap1_pitch[2:0]; ap1m_p1 <= (ap1_local * ap1_pitch[4:3]) << 3; ap1m_gs <= ap1_gs; ap1m_row <= ap1_row; ap1m_mine <= ap1_mine;
            ap_raddr <= a2_raddr; ap_kcode <= a2_kcode; ap_kscal <= a2_kscal; ap_mine <= ap1m_mine;
        end
    end
endmodule
