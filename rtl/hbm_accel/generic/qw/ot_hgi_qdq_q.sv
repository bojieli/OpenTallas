`timescale 1ns/1ps
`default_nettype none
// FUSED.QDQ_* B2 QUARTER (el1011-qdqtput, 2026-10-12): one QDQ engine per HBM B2 cluster, its wide VM read / write on the
// cluster's LOCAL VM slice 8-lane group (results/arch/hbm_b2_1012/SPEC.md sec 2a: lane b <-> local bank b = sector[2:0];
// the lanestation client protocol of ot_hgi_vm_lanechain: rq {v, sector 15} / rq_cr / rr {v, data 256} in order per lane,
// wq {v, sector 15, data 256, wmask 8} / wq_cr / wq_done, burst grant rg_req / rg_gnt, wg_req / wg_gnt).
// Throughput fix (AGENTS throughput gate: the packet unit ran 13.7x its price ceil(n/32)+8, the 32-lane wide engines
// 2.7-4.4x because every record waited for the previous one to drain):
//   * rate: one 32-FP32 beat (4 sectors on 4 consecutive local banks) a cycle into ONE decode core (ot_hgi_qw_dec3 = dxl/dbq/daq, or ot_hgi_qw_dec; the
//     closed hardened decode tile: same arithmetic as ot_hgi_quant_wide / the transport -> word-identical O);
//   * record OVERLAP: an RQ-deep record queue; the read walk of record k+1 is loaded on the cycle record k issues its last
//     beat (no drain between records); the header rides with each beat into the decode (the decode is per-beat clean);
//     in-order retire on per-lane write counters (a record retires when every lane's done counter passed the snapshot
//     taken at its last write) -> one done a record, in record order;
//   * hazards: at enqueue each record gets a dependency mask over the older in-flight records whose A / O word ranges
//     intersect its O / A / O ranges (RAW, WAR, WAW); its read walk starts only when those retired.  A record's own
//     in-place A == O is legal (a beat is read before it is written);
//   * shape class: the fast-path shapes of ot_hgi_quant_wide (QDQ header legal, A / O VM FP32 descriptors, inner stride
//     1, 8-word aligned bases / n / row strides, ends inside VM, A / O disjoint or identical).  Any other record FAULTS
//     (fail closed, retired in order with {fault, done}): the B2 compiler emits only this class (the packet transport,
//     its second decode core and the VM packet client are not part of the quarter).
// Front: face flops (pure) -> record binding (ot_hgi_quant_record) -> S1 capture -> S2 spans / flags -> S3 eligibility +
// ranges -> enqueue (dependency compares against the queue's registered ranges).  ret = {fault, done, ready}; ready is
// high while at most RQ - 4 records are accepted and not retired (4 = the records that can arrive before a lowered ready
// is seen through the face flops).
// MUT (bench): 1 = assembly takes sector j from lane j ^ 1 (lane-to-sector map; must FAIL); 2 = hazard masks ignored.
module ot_hgi_qdq_q #(
    parameter integer LQ  = 10,     // lane credits a lane (= the slice bank's wide-lane queue depth, 4 + 2 x 3 relay stages,
                                    // B2 SPEC v0.8 D-B2-12; 4 credits at 3 relays measured 1.29x)
    parameter integer LD  = 16,     // per-lane response FIFO (read round trip at 0.5 sector / lane / cycle; >= LQ)
    parameter integer NB  = 32,     // issued-beat FIFO (>= read round trip in beats; 16 caps S=3 at 18 cyc a 16-beat record)
    parameter integer OD  = 64,     // result FIFO beats (>= decode latency 26 + write round trip at S=3)
    parameter integer RQ  = 16,     // record queue
    parameter integer DEC3 = 1,     // decoder: 1 = ot_hgi_qw_dec3 (track B: dxl / dbq / daq tiles), 0 = ot_hgi_qw_dec (one tile)
    parameter integer SPANPIPE = 0, // opt-in: six local span stages (+5 edges), exact 52-bit product
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [682:0]      rec,          // {n_O, n_A, desc_O, desc_A, header, valid} (hgi_die_dispatch 'quant')
    output reg  [2:0]        ret,          // {fault, done, ready}
    output reg  [8*16-1:0]   wrq,
    input  wire [7:0]        wrq_cr,
    input  wire [8*257-1:0]  wrr,
    output reg  [8*280-1:0]  wwq,
    input  wire [7:0]        wwq_cr,
    input  wire [7:0]        wwq_done,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt
);
    localparam integer QW = $clog2(RQ), SW = $clog2(NB), OW = $clog2(OD), LW = $clog2(LD), CW = $clog2(LQ + 1);
    // ---------------------------------------------------------------- face flops (pure: no logic, reset or enable)
    // (the read responses wrr go straight to the lane-pair tiles' own pin flops, below)
    reg f_rst, f_rg, f_wg; reg [682:0] f_rec; reg [7:0] f_rcr, f_wcr, f_wdone;
    always @(posedge clk) begin
        f_rst <= rst_n; f_rec <= rec; f_rg <= rg_gnt; f_wg <= wg_gnt;
        f_rcr <= wrq_cr; f_wcr <= wwq_cr; f_wdone <= wwq_done;
    end
    wire [3:0] rr_n;                                  // 0 front / queue, 1 walks / lanes, 2 decode tile
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    // ---------------------------------------------------------------- record binding + front S1..S3
    wire [1408:0] cmd; wire nfault;
    ot_hgi_quant_record u_rec (.clk(clk), .rst_n(rr_n[0]), .rec(f_rec), .cmd(cmd), .nfault(nfault));
    reg s1_v, s2_v, s3_v;
    reg [127:0] s1_h; reg [255:0] s1_a, s1_o;
    always @(posedge clk) begin s1_h <= cmd[128:1]; s1_a <= cmd[385 +: 256]; s1_o <= cmd[1153 +: 256]; end
    // S2: field / fast flags and spans (the multiplies are this stage's only arithmetic)
    wire [5:0] op1 = s1_h[123:118];
    wire [19:0] an1 = s1_a[67:48], am1 = s1_a[87:68], on1 = s1_o[67:48], om1 = s1_o[87:68];
    wire [31:0] ars1 = s1_a[119:88], ors1 = s1_o[119:88];
    wire [39:0] ab1 = s1_a[47:8], ob1 = s1_o[47:8];
    wire fld1 = s1_h[127:124] == 4 && op1 >= 4 && op1 <= 6 && s1_h[99:93] == 7'b0010001 && !s1_h[92] &&
                (op1 != 6 || s1_h[71:64] == 16) && s1_a[1:0] == 1 && s1_o[1:0] == 1 && s1_a[4:2] == 0 &&
                (s1_o[4:2] == 0 || s1_o[4:2] == 1) && !s1_o[5] && am1 != 0 && am1 == om1 && an1 != 0 && an1 == on1 &&
                (op1 == 6 ? an1[3:0] == 0 : an1[4:0] == 0);
    wire fast1 = !s1_a[5] && s1_a[135:120] <= 16'd1 && s1_o[135:120] <= 16'd1 && ab1[2:0] == 0 && ob1[2:0] == 0 &&
                 an1[2:0] == 0 && (am1 == 20'd1 || (ars1[2:0] == 0 && ors1[2:0] == 0 && ars1 >= {12'd0, an1} && ors1 >= {12'd0, on1}));
    reg fld2, fast2, same2; reg [63:0] aend2, oend2; reg [39:0] ab2, ob2; reg [19:0] n2, m2; reg [31:0] ars2, ors2;
    reg [17:0] hd2;                                   // {unit 4, op 6, block 8}: the decode's only header fields
    generate if (SPANPIPE == 0) begin : g_span_legacy
    always @(posedge clk) begin
        fld2 <= fld1; fast2 <= fast1; same2 <= ars1 == ors1; ab2 <= ab1; ob2 <= ob1; n2 <= an1; m2 <= am1;
        ars2 <= ars1; ors2 <= ors1; hd2 <= {s1_h[127:118], s1_h[71:64]};
        aend2 <= {24'd0, ab1} + (64'(am1) - 64'd1) * 64'(ars1) + 64'(an1) - 64'd1;
        oend2 <= {24'd0, ob1} + (64'(om1) - 64'd1) * 64'(ors1) + 64'(on1) - 64'd1;
    end
    end else begin : g_span_pipe
        // Physical stages: row decrement -> five 4x32 partial products -> adjacent pairs -> pair sum ->
        // final product -> one end-address add.  The maximum legal product is 52 bits (20x32), so no 64-bit
        // multiply or multiply-plus-add cone remains.  Invalid zero-row descriptors still fail fld1.
        reg [19:0] rows_a, rows_o;
        reg [31:0] stride_a, stride_o;
        reg [35:0] pa [0:4], po [0:4];
        reg [39:0] pair_a [0:1], pair_o [0:1]; reg [35:0] last_a, last_o;
        reg [47:0] sum_a, sum_o; reg [35:0] last_a2, last_o2;
        reg [51:0] prod_a, prod_o;
        reg [40:0] base_n_a, base_n_o, offset_a [0:4], offset_o [0:4];
        reg [2:0] flags [0:5]; reg [39:0] bases_a [0:5], bases_o [0:5];
        reg [19:0] ns [0:5], ms [0:5]; reg [31:0] rss_a [0:5], rss_o [0:5]; reg [17:0] headers [0:5];
        integer k;
        always @(posedge clk) begin
            rows_a <= am1 - 20'd1; rows_o <= om1 - 20'd1; stride_a <= ars1; stride_o <= ors1;
            base_n_a <= {1'b0, ab1} + 41'(an1); base_n_o <= {1'b0, ob1} + 41'(on1);
            offset_a[0] <= base_n_a - 41'd1; offset_o[0] <= base_n_o - 41'd1;
            for (k = 1; k < 5; k = k + 1) begin offset_a[k] <= offset_a[k-1]; offset_o[k] <= offset_o[k-1]; end
            for (k = 0; k < 5; k = k + 1) begin
                pa[k] <= rows_a[k*4 +: 4] * stride_a; po[k] <= rows_o[k*4 +: 4] * stride_o;
            end
            pair_a[0] <= 40'(pa[0]) + (40'(pa[1]) << 4); pair_o[0] <= 40'(po[0]) + (40'(po[1]) << 4);
            pair_a[1] <= 40'(pa[2]) + (40'(pa[3]) << 4); pair_o[1] <= 40'(po[2]) + (40'(po[3]) << 4);
            last_a <= pa[4]; last_o <= po[4];
            sum_a <= 48'(pair_a[0]) + (48'(pair_a[1]) << 8); sum_o <= 48'(pair_o[0]) + (48'(pair_o[1]) << 8);
            last_a2 <= last_a; last_o2 <= last_o;
            prod_a <= 52'(sum_a) + (52'(last_a2) << 16); prod_o <= 52'(sum_o) + (52'(last_o2) << 16);
            aend2 <= 64'(prod_a) + 64'(offset_a[3]); oend2 <= 64'(prod_o) + 64'(offset_o[3]);
            flags[0] <= {fld1, fast1, ars1 == ors1}; bases_a[0] <= ab1; bases_o[0] <= ob1;
            ns[0] <= an1; ms[0] <= am1; rss_a[0] <= ars1; rss_o[0] <= ors1; headers[0] <= {s1_h[127:118], s1_h[71:64]};
            for (k = 1; k < 6; k = k + 1) begin
                flags[k] <= flags[k-1]; bases_a[k] <= bases_a[k-1]; bases_o[k] <= bases_o[k-1];
                ns[k] <= ns[k-1]; ms[k] <= ms[k-1]; rss_a[k] <= rss_a[k-1]; rss_o[k] <= rss_o[k-1]; headers[k] <= headers[k-1];
            end
        end
        always @* begin
            {fld2, fast2, same2} = flags[5]; ab2 = bases_a[5]; ob2 = bases_o[5]; n2 = ns[5]; m2 = ms[5];
            ars2 = rss_a[5]; ors2 = rss_o[5]; hd2 = headers[5];
        end
    end endgenerate
    // S3: eligibility; everything an entry needs, narrowed to the slice address space
    reg el3; reg [17:0] alo3, ahi3, olo3, ohi3; reg [14:0] as3, os3, rs3, ws3; reg [15:0] bpr3; reg [2:0] nsl3;
    reg [19:0] m3; reg [17:0] hd3;
    always @(posedge clk) begin
        el3 <= fld2 && fast2 && aend2 < 64'd262144 && oend2 < 64'd262144 &&
               ((aend2 < {24'd0, ob2}) || (oend2 < {24'd0, ab2}) || (same2 && ab2 == ob2));
        alo3 <= ab2[17:0]; ahi3 <= aend2[17:0]; olo3 <= ob2[17:0]; ohi3 <= oend2[17:0];
        as3 <= ab2[17:3]; os3 <= ob2[17:3]; rs3 <= ars2[17:3]; ws3 <= ors2[17:3];
        bpr3 <= 16'((n2 + 20'd31) >> 5); nsl3 <= (n2[4:0] == 5'd0) ? 3'd4 : {1'b0, n2[4:3]};
        m3 <= m2; hd3 <= hd2;
    end
    generate if (SPANPIPE == 0) begin : g_valid_legacy
        always @(posedge clk or negedge rr_n[0])
            if (!rr_n[0]) begin s1_v <= 0; s2_v <= 0; s3_v <= 0; end
            else begin s1_v <= cmd[0]; s2_v <= s1_v; s3_v <= s2_v; end
    end else begin : g_valid_pipe
        reg [4:0] span_v;
        always @(posedge clk or negedge rr_n[0])
            if (!rr_n[0]) begin s1_v <= 0; span_v <= 0; s2_v <= 0; s3_v <= 0; end
            else begin s1_v <= cmd[0]; span_v <= {span_v[3:0], s1_v}; s2_v <= span_v[4]; s3_v <= s2_v; end
    end endgenerate
    // ---------------------------------------------------------------- record queue
    reg [RQ-1:0] q_v, q_rej, q_snv;
    reg [RQ-1:0] q_dep [0:RQ-1];
    reg [17:0] q_alo [0:RQ-1], q_ahi [0:RQ-1], q_olo [0:RQ-1], q_ohi [0:RQ-1];
    reg [14:0] q_as [0:RQ-1], q_os [0:RQ-1], q_rs [0:RQ-1], q_ws [0:RQ-1];
    reg [15:0] q_bpr [0:RQ-1]; reg [2:0] q_nsl [0:RQ-1]; reg [19:0] q_m [0:RQ-1]; reg [17:0] q_hd [0:RQ-1];
    reg [8*8-1:0] q_snap [0:RQ-1];                    // per-lane write count after the record's last write
    reg [QW-1:0] qt, rp, hd;                          // tail, next to start, retire head
    reg [QW:0] occ;                                   // accepted (bound) and not retired
    reg bad;
    // dependency of the S3 record on every valid entry (RAW: its A vs their O; WAR: its O vs their A; WAW: O vs O)
    reg [RQ-1:0] dep3; reg [RQ-1:0] ret_oh;
    always @* begin
        for (integer e = 0; e < RQ; e = e + 1)
            dep3[e] = q_v[e] && !ret_oh[e] && !q_rej[e] &&
                      ((alo3 <= q_ohi[e] && q_olo[e] <= ahi3) || (olo3 <= q_ahi[e] && q_alo[e] <= ohi3) ||
                       (olo3 <= q_ohi[e] && q_olo[e] <= ohi3));
    end
    // ---------------------------------------------------------------- read walk
    reg r_act; reg [QW-1:0] r_e; reg [19:0] r_row, r_m; reg [15:0] r_beat, r_bpr; reg [2:0] r_nsl;
    reg [14:0] r_rsec, r_osec, r_rs, r_ws;
    reg rg_ok, wg_ok;
    reg [CW-1:0] rcr [0:7], wcr [0:7];
    // lane response FIFOs: 4 hardened lane-pair tiles (ot_hgi_qdq_lq, LD 16 x 256 per lane, ~9.3k sinks each on their
    // own clock trees; textbook audit 10-12 class 1: the 8 x 16 x 256 flop array put 46k flops on the cluster root).
    // The centre keeps occupancy lf_n (from the tiles' registered e_push) and issued-not-popped lf_r, decides pops, and
    // sends registered per-lane pop strobes; the popped heads come back registered two cycles later (hq) and are placed
    // into beat positions here, three cycles after the pop decision (registered select pipeline s1..s3).
    reg [LW:0] lf_n [0:7], lf_r [0:7];
    reg [7:0] c_pop; wire [7:0] e_push; wire [3:0] e_ovf; wire [8*256-1:0] hq;
    genvar gp;
    generate for (gp = 0; gp < 4; gp = gp + 1) begin : g_lq
        ot_hgi_qdq_lq u_lq (.clk(clk), .rst_n(rr_n[1]), .wrr(wrr[gp*2*257 +: 2*257]), .c_pop(c_pop[gp*2 +: 2]),
            .hq(hq[gp*512 +: 512]), .e_push(e_push[gp*2 +: 2]), .e_ovf(e_ovf[gp]));
    end endgenerate
    reg [2:0] bq_l [0:NB-1], bq_n [0:NB-1]; reg [14:0] bq_o [0:NB-1]; reg [QW-1:0] bq_e [0:NB-1]; reg bq_z [0:NB-1];
    reg [SW-1:0] b_t, b_h; reg [SW:0] b_used;
    wire [14:0] r_sec0 = r_rsec + {r_beat[12:0], 2'd0};
    wire r_lastbeat = (r_beat + 16'd1 == r_bpr);
    wire r_lastrow = (r_row + 20'd1 == r_m);
    wire [2:0] r_nsec = r_lastbeat ? r_nsl : 3'd4;
    reg [7:0] r_hit; reg r_cr_ok;
    always @* begin
        r_cr_ok = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) begin
            r_hit[b] = 3'(b - r_sec0[2:0]) < r_nsec;
            if (r_hit[b] && (rcr[b] == 0 || lf_r[b] == LD[LW:0])) r_cr_ok = 1'b0;
        end
    end
    wire r_issue = r_act && rg_ok && !bad && b_used != NB[SW:0] && r_cr_ok;
    wire r_end = r_issue && r_lastbeat && r_lastrow;
    // the next entry may start: bound, eligible, its producers retired
    wire n_ok = q_v[rp] && !q_rej[rp] && ((q_dep[rp] & q_v) == '0 || MUT == 2) && !bad;
    wire n_load = n_ok && (!r_act || r_end);
    wire n_skip = q_v[rp] && q_rej[rp] && (!r_act || r_end) && !n_load;   // a rejected record holds no walk
    // ---------------------------------------------------------------- assembly -> decode
    wire [2:0] h_l = bq_l[b_h], h_n = bq_n[b_h];
    reg [7:0] h_hit; reg h_ok; reg [1023:0] h_x;
    // pop pipeline: s1 (with c_pop) -> s2 (tile i_pop) -> s3 (tile hq) -> d_x / d_v.  The 4 beat positions take a one-hot
    // AND-OR over the 8 popped lane heads, selects decoded from the registered s3 lane / count.
    reg s1_lv, s2_lv, s3_lv; reg [2:0] s1_l, s2_l, s3_l, s1_n, s2_n, s3_n; reg [17:0] s1_hd, s2_hd, s3_hd;
    always @* begin
        h_ok = b_used != 0; h_x = '0;
        for (integer b = 0; b < 8; b = b + 1) begin
            h_hit[b] = 3'(b - h_l) < h_n;
            if (h_hit[b] && lf_n[b] == 0) h_ok = 1'b0;
        end
        for (integer j = 0; j < 4; j = j + 1) begin
            reg [2:0] l; l = 3'(s3_l + ((MUT == 1) ? (j ^ 1) : j));
            for (integer b = 0; b < 8; b = b + 1)
                h_x[j*256 +: 256] = h_x[j*256 +: 256] | ({256{j < s3_n && l == 3'(b)}} & hq[b*256 +: 256]);
        end
    end
    reg [OW:0] resv, od_n;
    wire l_fire = h_ok && resv != OD[OW:0];
    reg d_v; reg [127:0] d_h; reg [1023:0] d_x;
    wire vo, qfault, dfault; wire [511:0] y;
    generate if (DEC3 != 0) begin : g_d3
        // track B (decoder of record, coordinator 10-12): three hardened tiles dxl / dbq / daq, same ports and timing
        ot_hgi_qw_dec3 u_dec (.clk(clk), .rst_n(rr_n[2]), .v(d_v), .header(d_h), .x(d_x), .vo(vo), .y(y), .fault(qfault),
            .decode_fault(dfault));
    end else begin : g_d1
        ot_hgi_qw_dec u_dec (.clk(clk), .rst_n(rr_n[2]), .v(d_v), .header(d_h), .x(d_x), .vo(vo), .y(y), .fault(qfault),
            .decode_fault(dfault));
    end endgenerate
    // ---------------------------------------------------------------- result FIFO + write
    reg [14:0] mq_o [0:OD-1]; reg [2:0] mq_n [0:OD-1]; reg [QW-1:0] mq_e [0:OD-1]; reg mq_z [0:OD-1];
    // result store (textbook audit 10-12, class 5/6: was a 64 x 512 flop array read 64:1 x 512 b in one cycle): one
    // ot_sram_1r1w_64x512_m1_r2c2 macro behind a 2-entry registered prefetch buffer (ot_fifo_sram_fwft: synchronous macro
    // read issued ahead into capture registers; an empty FIFO shows a push the next cycle, one pop a cycle sustained),
    // so the write issue sees a 2:1 register head instead of the array.  ESL 128: the buffer in 4 x 128-b slices with
    // their own control copies (one slice per sector of the write).  od_n keeps the pushed-not-written count (retire /
    // drain accounting); the write issues on the buffer's head valid.
    wire od_hv, od_ovf; wire [511:0] od_head;
    reg [OW-1:0] mq_t, mq_h;
    wire [14:0] w_sec0 = mq_o[mq_h]; wire [2:0] w_n = mq_n[mq_h];
    reg [7:0] w_hit; reg w_cr_ok;
    always @* begin
        w_cr_ok = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) begin
            w_hit[b] = 3'(b - w_sec0[2:0]) < w_n;
            if (w_hit[b] && wcr[b] == 0) w_cr_ok = 1'b0;
        end
    end
    wire w_fire = wg_ok && !bad && od_hv && w_cr_ok;
    ot_fifo_sram_fwft #(.W(512), .DEPTH(OD), .MACRO(0), .ESL(128)) u_od (.clk(clk), .rst_n(rr_n[1]), .push(vo),
        .wdata(y), .pop(w_fire), .hv(od_hv), .head(od_head), .ovf(od_ovf));
    reg [7:0] wcnt [0:7], dcnt [0:7];
    // ---------------------------------------------------------------- retire (in record order)
    reg r_ready; reg h_fin;
    always @* begin
        h_fin = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) if ($signed(dcnt[b] - q_snap[hd][b*8 +: 8]) < 0) h_fin = 1'b0;
    end
    // after a decode fault (terminal, as nfault): writes stop; every launched beat has come back -> retire the rest faulted
    wire drained = b_used == 0 && !d_v && resv == od_n;
    wire rt_ok = q_v[hd] && (q_rej[hd] || (q_snv[hd] && h_fin) || (bad && drained));
    wire rt_fault = q_rej[hd] || bad;
    always @* begin ret_oh = '0; if (rt_ok) ret_oh[hd] = 1'b1; end
    // ---------------------------------------------------------------- sequential control
    integer b, e, j;
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            q_v <= 0; q_rej <= 0; q_snv <= 0; qt <= 0; rp <= 0; hd <= 0; occ <= 0; bad <= 0; ret <= 0;
            rg_req <= 0; wg_req <= 0; rg_ok <= 0; wg_ok <= 0;

        end else begin
            rg_req <= q_v != 0; wg_req <= q_v != 0;
            rg_ok <= rg_req && f_rg; wg_ok <= wg_req && f_wg;
            // enqueue
            if (s3_v) begin
                q_v[qt] <= 1'b1; q_rej[qt] <= !el3; q_snv[qt] <= 1'b0; qt <= qt + 1'b1;
            end

            if (n_load || n_skip) rp <= rp + 1'b1;
            if (w_fire && mq_z[mq_h]) q_snv[mq_e[mq_h]] <= 1'b1;
            if (rt_ok) begin q_v[hd] <= 1'b0; hd <= hd + 1'b1; end
            if (vo && qfault) bad <= 1'b1;
            if (dfault || od_ovf || e_ovf != 0) bad <= 1'b1;   // e_ovf: lane FIFO overrun in a tile   // result-store overrun (bounded by resv; fail closed)
            occ <= occ + (QW+1)'(cmd[0]) - (QW+1)'(rt_ok);
            ret <= {rt_ok && rt_fault || nfault, rt_ok, (occ + (QW+1)'(cmd[0]) - (QW+1)'(rt_ok)) <= (QW+1)'(RQ - (SPANPIPE ? 9 : 4))};
        end
    end
    // Queue dependency masks have a separate, equally staged reset root (256 sinks at RQ16).
    always @(posedge clk or negedge rr_n[3]) begin
        if (!rr_n[3]) begin for (integer qe = 0; qe < RQ; qe = qe + 1) q_dep[qe] <= '0; end
        else begin
            if (s3_v) q_dep[qt] <= el3 ? dep3 : '0;
            for (integer qe = 0; qe < RQ; qe = qe + 1) if (rt_ok) q_dep[qe][hd] <= 1'b0;
            if (s3_v && rt_ok) q_dep[qt][hd] <= 1'b0;
        end
    end
    always @(posedge clk or negedge rr_n[1]) begin
        if (!rr_n[1]) begin
            r_act <= 0; r_e <= 0; r_row <= 0; r_m <= 0; r_beat <= 0; r_bpr <= 0; r_nsl <= 0; r_rsec <= 0; r_osec <= 0;
            r_rs <= 0; r_ws <= 0; b_t <= 0; b_h <= 0; b_used <= 0; resv <= 0; od_n <= 0; mq_h <= 0; mq_t <= 0;
            d_v <= 0; c_pop <= '0; s1_lv <= 0; s2_lv <= 0; s3_lv <= 0;
            for (b = 0; b < 8; b = b + 1) begin
                wrq[b*16 + 15] <= 1'b0; wwq[b*280 + 279] <= 1'b0;
                rcr[b] <= LQ[CW-1:0]; wcr[b] <= LQ[CW-1:0]; lf_n[b] <= 0; lf_r[b] <= 0;
                wcnt[b] <= 0; dcnt[b] <= 0;
            end
        end else begin
            wrq <= '0; wwq <= '0; s1_lv <= l_fire; s2_lv <= s1_lv; s3_lv <= s2_lv; d_v <= s3_lv;
            // ---- read walk: one beat (<= 4 sectors) a cycle; the next record loads on the last beat
            if (r_issue) begin
                for (b = 0; b < 8; b = b + 1) if (r_hit[b]) wrq[b*16 +: 16] <= {1'b1, 15'(r_sec0 + 15'(3'(b - r_sec0[2:0])))};
                b_t <= b_t + 1'b1;
                if (r_lastbeat) begin r_beat <= 0; r_row <= r_row + 1'b1; r_rsec <= r_rsec + r_rs; r_osec <= r_osec + r_ws; end
                else r_beat <= r_beat + 1'b1;
            end
            if (r_end && !n_load) r_act <= 1'b0;
            if (n_load) begin
                r_act <= 1'b1; r_e <= rp; r_row <= 0; r_beat <= 0; r_m <= q_m[rp]; r_bpr <= q_bpr[rp]; r_nsl <= q_nsl[rp];
                r_rsec <= q_as[rp]; r_osec <= q_os[rp]; r_rs <= q_rs[rp]; r_ws <= q_ws[rp];
            end
            // ---- lanes: credits, response FIFOs, issued / popped
            for (b = 0; b < 8; b = b + 1) begin : lanes
                reg push, pop, iss, wr;
                push = e_push[b]; pop = l_fire && h_hit[b]; iss = r_issue && r_hit[b]; wr = w_fire && w_hit[b];
                c_pop[b] <= pop;
                rcr[b] <= rcr[b] + CW'(f_rcr[b]) - CW'(iss);
                wcr[b] <= wcr[b] + CW'(f_wcr[b]) - CW'(wr);
                lf_n[b] <= lf_n[b] + (LW+1)'(push) - (LW+1)'(pop);
                lf_r[b] <= lf_r[b] + (LW+1)'(iss) - (LW+1)'(pop);
                wcnt[b] <= wcnt[b] + 8'(wr); dcnt[b] <= dcnt[b] + 8'(f_wdone[b]);
            end
            b_used <= b_used + (SW+1)'(r_issue) - (SW+1)'(l_fire);
            if (l_fire) begin b_h <= b_h + 1'b1; mq_t <= mq_t + 1'b1; end
            // ---- decode results -> result FIFO; write the head result on its 1..4 lanes
            od_n <= od_n + (OW+1)'(vo) - (OW+1)'(w_fire);
            resv <= resv + (OW+1)'(l_fire) - (OW+1)'(w_fire);
            if (w_fire) begin
                for (b = 0; b < 8; b = b + 1) if (w_hit[b]) begin : wr
                    reg [255:0] d; reg [1:0] s; reg [127:0] c; s = 2'(3'(b - w_sec0[2:0]));
                    // decoded constant-index sector select (one-hot AND-OR, no runtime part-select)
                    c = ({128{s == 2'd0}} & od_head[127:0]) | ({128{s == 2'd1}} & od_head[255:128]) |
                        ({128{s == 2'd2}} & od_head[383:256]) | ({128{s == 2'd3}} & od_head[511:384]);
                    for (integer k = 0; k < 8; k = k + 1) d[k*32 +: 32] = {c[k*16 +: 16], 16'd0};
                    wwq[b*280 +: 280] <= {1'b1, 15'(w_sec0 + 15'(s)), d, 8'hff};
                end
                mq_h <= mq_h + 1'b1;
            end
        end
    end
    // ---------------------------------------------------------------- storage (no reset)
    always @(posedge clk) begin
        if (s3_v) begin
            q_alo[qt] <= alo3; q_ahi[qt] <= ahi3; q_olo[qt] <= olo3; q_ohi[qt] <= ohi3; q_as[qt] <= as3; q_os[qt] <= os3;
            q_rs[qt] <= rs3; q_ws[qt] <= ws3; q_bpr[qt] <= bpr3; q_nsl[qt] <= nsl3; q_m[qt] <= m3; q_hd[qt] <= hd3;
        end
        if (r_issue) begin
            bq_l[b_t] <= r_sec0[2:0]; bq_n[b_t] <= r_nsec; bq_o[b_t] <= r_osec + {r_beat[12:0], 2'd0}; bq_e[b_t] <= r_e;
            bq_z[b_t] <= r_lastbeat && r_lastrow;
        end
        s1_l <= h_l; s1_n <= h_n; s1_hd <= q_hd[bq_e[b_h]];
        s2_l <= s1_l; s2_n <= s1_n; s2_hd <= s1_hd; s3_l <= s2_l; s3_n <= s2_n; s3_hd <= s2_hd;
        // Decoder consumes data only when d_v: no 2k-load data enable is needed.
        d_x <= h_x; d_h <= {s3_hd[17:8], 46'd0, s3_hd[7:0], 64'd0};
        if (l_fire) begin
            mq_o[mq_t] <= bq_o[b_h]; mq_n[mq_t] <= h_n; mq_e[mq_t] <= bq_e[b_h]; mq_z[mq_t] <= bq_z[b_h];
        end
        if (w_fire && mq_z[mq_h])
            for (integer q = 0; q < 8; q = q + 1) q_snap[mq_e[mq_h]][q*8 +: 8] <= wcnt[q] + 8'(w_hit[q]);
    end
    initial begin
        if ((RQ & (RQ - 1)) != 0 || RQ < 8) $fatal(1, "ot_hgi_qdq_q: RQ must be a power of two >= 8");
        if ((NB & (NB - 1)) != 0 || (OD & (OD - 1)) != 0 || (LD & (LD - 1)) != 0) $fatal(1, "ot_hgi_qdq_q: NB / OD / LD powers of two");
        if (OD < 32) $fatal(1, "ot_hgi_qdq_q: OD >= 32 (decode latency 26)");
        if (LD != 16) $fatal(1, "ot_hgi_qdq_q: LD = 16 (= the hardened ot_hgi_qdq_lq default)");
    end
endmodule
`default_nettype wire
