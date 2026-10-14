`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM B2 hyper-connection residual engine (el1013-hbm-hc, 2026-10-13): FUSED.HC_POST / HC_PRE_NORM at D 5,120 on the
// B2 quarter map (results/arch/hbm_b2_1012/SPEC.md: 4 clusters, a LOCAL VM slice each, no central VM, no barrier).
//
//   quarter q (ot_hgi_hc_qst_b2, one a cluster): 8 x ot_hgi_hc_lane_b2 (LOCAL8: D 1,280, 8 banks of the quarter's slice,
//     local sector stride 8; the ot_hgi_hc_lane_ll arithmetic unchanged), a chunk concentrator (ot_hgi_hc_cat_b2) and
//     the quarter's status / scalar-sector return.  Element range [1280 q, 1280 (q + 1)) of every vector operand sits in
//     slice q at the SAME local base (SPEC rule F2, partition alignment); a row is 160 local sectors.
//   centre (ot_hgi_hc_ctl_b2): job decode, scalar fetch through the scalar-home quarter, the relayed command broadcast,
//     the golden-order chunk collector (ot_hgi_hc_coll_b2), ss / D, + eps, rsqrt, the r broadcast, retirement.
//
// HC_PRE_NORM reduction (golden: hdc_golden_v41 chunk8, ot_dsrom_su_norm): 640 chunk sums (8 sequential squares each,
//   in the lanes) -> 20 blocks of 32 chunks by a 5-level pairwise tree (left = even chunk) -> the padded 20-block heap.
//   A lane tags every chunk QID * 160 + local sector = its GLOBAL sector index; block = tag[9:5], leaf = tag[4:0].
//   The collector stores a chunk at its tag, fires a block the cycle its 32 leaves are present (any block order: the
//   heap leaf is the block index), so arrival order, lane order and quarter order never reach the arithmetic.
//
// Chunk link, quarter -> centre: P = 2 slots of {v, epoch 2, tag 10, FP32 32} (45 b a slot), a credit pulse back a
//   slot.  A slot holds CD credits = the depth of its ingress queue at the collector (D-B2-12 convention: 4 + 2 x relay
//   stages); a credit returns when the collector takes the packet out of the queue.  No barrier, no ready wire.  The
//   store has a place for every tag, so the queue drains every cycle; the credit bounds the link whatever the relay
//   depth.  JOB stamps a new epoch and flushes the concentrator; a packet of an older epoch still in flight is dropped
//   at the collector (credited, counted, never stored).  Fail closed: a duplicate tag, a tag outside its quarter's
//   range, a queue overrun or an adder fault faults the record.
//
// Job word (ot_hgi_hc_eng's 149 b) with the B2 allocation rule: n = D; A / B / O are LOCAL word bases, the same in every
//   slice, at one bank phase (sector mod 8); job[38:37] = the scalar-home quarter (C is a local word base there); the
//   packed gain is refused (FP32 gain only).  A refused job faults with no lane activity.
// MUT (bench negatives, must FAIL): lanes 2 / 5 / 6 / 7 / 8 / 13 (ot_hgi_hc_lane_b2); 4 retire before the write dones;
//   9 the block tree pairs leaf c with c + 1 rotated (a non-golden association); 10 the concentrator sends without
//   credit; 11 the collector ignores the epoch; 12 the collector does not check a duplicate tag.
// ---------------------------------------------------------------------------------------------------------------------

// ---- chunk concentrator: NL lane chunk streams -> P credit-gated slots (lane l uses slot l mod P)
module ot_hgi_hc_cat_b2 #(
    parameter integer NL  = 8,
    parameter integer P   = 2,
    parameter integer QD  = 32,              // per-lane queue: a whole row of the lane (20 chunks) fits, the lane never waits
    parameter integer CD  = 16,              // credits a slot
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              flush,          // JOB: drop everything queued (the epoch moves with it)
    input  wire [1:0]        ep,
    input  wire [NL-1:0]     ch_v,
    input  wire [NL*42-1:0]  ch,             // per lane {tag 10, d 32}
    output reg  [P-1:0]      ck_v,
    output reg  [P*44-1:0]   ck,             // per slot {ep 2, tag 10, d 32}
    input  wire [P-1:0]      ck_cr,
    output reg               ovf
);
    localparam integer QB = $clog2(QD), NS = NL / P, SB = (NS > 1) ? $clog2(NS) : 1, CB = $clog2(CD + 1);
    generate if (NL % P != 0 || (QD & (QD - 1)) != 0) begin : g_bad
        ot_hgi_hc_cat_b2_NL_multiple_of_P_QD_power_of_two u_trap ();
    end endgenerate
    reg [41:0] q [0:NL-1][0:QD-1];
    reg [QB:0] wp [0:NL-1], rp [0:NL-1];
    reg [SB-1:0] rr [0:P-1]; reg [CB-1:0] crd [0:P-1]; reg [P-1:0] cr_q;
    reg [P-1:0] snd; reg [SB-1:0] pick [0:P-1];
    integer l, p, s;
    always @* begin
        for (p = 0; p < P; p = p + 1) begin
            snd[p] = 1'b0; pick[p] = rr[p];
            for (s = NS - 1; s >= 0; s = s - 1) begin : g_s
                reg [SB:0] k; integer ln;
                k = (SB+1)'(rr[p]) + (SB+1)'(s); if (k >= (SB+1)'(NS)) k = k - (SB+1)'(NS);
                ln = integer'(k) * P + p;
                if (wp[ln] != rp[ln]) begin snd[p] = 1'b1; pick[p] = k[SB-1:0]; end
            end
            if (crd[p] == '0 && MUT != 10) snd[p] = 1'b0;
        end
    end
    always @(posedge clk) begin
        for (l = 0; l < NL; l = l + 1) if (ch_v[l]) q[l][wp[l][QB-1:0]] <= ch[l*42 +: 42];
        for (p = 0; p < P; p = p + 1) ck[p*44 +: 44] <= {ep, q[integer'(pick[p]) * P + p][rp[integer'(pick[p]) * P + p][QB-1:0]]};
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (l = 0; l < NL; l = l + 1) begin wp[l] <= '0; rp[l] <= '0; end
            for (p = 0; p < P; p = p + 1) begin rr[p] <= '0; crd[p] <= CB'(CD); end
            ck_v <= '0; cr_q <= '0; ovf <= 1'b0;
        end else begin
            cr_q <= ck_cr;
            ck_v <= flush ? '0 : snd;
            for (l = 0; l < NL; l = l + 1) begin
                if (flush) begin wp[l] <= '0; rp[l] <= '0; end
                else if (ch_v[l]) begin
                    wp[l] <= wp[l] + 1'b1;
                    if (wp[l][QB-1:0] == rp[l][QB-1:0] && wp[l][QB] != rp[l][QB]) ovf <= 1'b1;
                end
            end
            for (p = 0; p < P; p = p + 1) begin
                if (snd[p] && !flush) begin
                    rp[integer'(pick[p]) * P + p] <= rp[integer'(pick[p]) * P + p] + 1'b1;
                    rr[p] <= (pick[p] == SB'(NS - 1)) ? '0 : pick[p] + 1'b1;
                end
                // a credit leaves with a packet and comes home with its pulse (a flushed packet was never sent)
                if (snd[p] && !flush && !cr_q[p]) crd[p] <= crd[p] - 1'b1;
                else if (!(snd[p] && !flush) && cr_q[p]) crd[p] <= crd[p] + 1'b1;
            end
            if (flush) ovf <= 1'b0;
        end
    end
endmodule

// ---- the finite central golden-order collector: NQ x P tagged chunk slots -> ss (the row's sum of squares)
module ot_hgi_hc_coll_b2 #(
    parameter integer STORELEAF=0, CLOCKED=0,
    parameter integer NQ  = 4,
    parameter integer P   = 2,
    parameter integer NB  = 20,              // 32-chunk blocks a row (D / 256)
    parameter integer CD  = 16,              // ingress queue depth a slot = the credits the slot's sender holds
    parameter integer LA  = 6,
    parameter integer MUT = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input wire[NB-1:0] clk_store,input wire[NQ*8-1:0] clk_scan,
    input wire[30:0] clk_block_add,clk_heap_add,
    input  wire               clr,           // a new row: every chunk, block and heap node forgotten
    input  wire [1:0]         ep,            // the row's epoch (stable from clr)
    input  wire [NQ*P-1:0]    pk_v,
    input  wire [NQ*P*44-1:0] pk,            // per slot {ep 2, tag 10, d 32}
    output reg  [NQ*P-1:0]    pk_cr,         // one credit back a packet taken
    output wire               ss_v,          // pulse: ss holds the golden sum
    output wire [31:0]        ss,
    output reg                flt,           // sticky to clr: duplicate / out-of-range tag, queue overrun, adder fault
    output reg  [15:0]        n_stale        // packets of another epoch dropped (since reset)
);
    localparam integer NS = NQ * P, NC = NB * 32, QC = NC / NQ;      // slots, chunks a row, chunks a quarter
    localparam integer NBP = (NB <= 1) ? 1 : (1 << $clog2(NB));
    localparam integer CDP = 1 << $clog2(CD), CB = $clog2(CDP);
    localparam integer BB = (NB > 1) ? $clog2(NB) : 1;
    // ---- ingress: pin flops, a CD-deep queue a slot, drained one packet a cycle into the store
    reg [NS-1:0] iv; reg [43:0] id [0:NS-1];
    reg [43:0] iq [0:NS-1][0:CDP-1]; reg [CB:0] iw [0:NS-1], ir [0:NS-1];
    reg [NC-1:0] vld; reg [31:0] st [0:NC-1];
    reg [NS-1:0] tk, bad, wr; reg [43:0] hd [0:NS-1]; reg [9:0] tg [0:NS-1];
    integer s, t, b;
    always @* begin
        for (s = 0; s < NS; s = s + 1) begin
            hd[s] = iq[s][ir[s][CB-1:0]]; tg[s] = hd[s][41:32];
            tk[s] = (iw[s] != ir[s]) && !clr;
            wr[s] = tk[s] && (hd[s][43:42] == ep || MUT == 11);
            bad[s] = 1'b0;
            if (wr[s]) begin
                if (tg[s] >= 10'(NC) || (integer'(tg[s]) / QC) != (s / P)) begin bad[s] = 1'b1; wr[s] = 1'b0; end
                else if (vld[tg[s]] && MUT != 12) bad[s] = 1'b1;
                for (t = 0; t < s; t = t + 1) if (tk[t] && hd[t][43:42] == ep && hd[t][41:32] == tg[s] && MUT != 12) bad[s] = 1'b1;
            end
        end
    end
    always @(posedge clk) begin
        for (s = 0; s < NS; s = s + 1) begin
            id[s] <= pk[s*44 +: 44];
            if (iv[s]) iq[s][iw[s][CB-1:0]] <= id[s];

        end
    end
    // ---- blocks: a block fires once, the cycle after its 32 leaves are all present
    reg [NB-1:0] full, fired; reg b0_v; reg [1023:0] b0; reg [5:0] b0_i;
    reg fb_v; reg [BB-1:0] fb;
    always @* begin
        fb_v = 1'b0; fb = '0;
        for (b = NB - 1; b >= 0; b = b - 1) if (full[b] && !fired[b]) begin fb_v = 1'b1; fb = BB'(b); end
    end
    wire[NB-1:0]store_full,store_fault,scan_valid;
    wire[NB*256-1:0]scan_data;
    wire[NQ-1:0]hub_v,hub_fault;wire[NQ*256-1:0]hub_data;wire[NQ*7-1:0]hub_meta;
    wire[6:0]land_tag;
    reg scan_active;reg[1:0]scan_group;reg[4:0]scan_block;
    reg[6:0]meta0,meta1;reg[3:0]scan_flush;
    generate if(STORELEAF)begin:g_stores
      initial if(NB!=20||NQ!=4||P!=2)$fatal(1,"HC local blockstore needs20blocks/4quarters/2slots");
      for(genvar bs=0;bs<NB;bs++)begin:g_store
        localparam integer Q=bs/5;
        wire[1:0]wv={wr[Q*2+1]&&(tg[Q*2+1]>>5)==bs,wr[Q*2]&&(tg[Q*2]>>5)==bs};
        ot_hgi_hc_chunk_store32 #(.MUT(MUT==12?2:0))u_store(
          .clk(CLOCKED?clk_store[bs]:clk),.rst_n(rst_n),.clr(clr),.wr_v(wv),
          .wr_tag({tg[Q*2+1][4:0],tg[Q*2][4:0]}),.wr_data({hd[Q*2+1][31:0],hd[Q*2][31:0]}),
          .scan_v(scan_active&&scan_block==bs&&scan_flush==0),.scan_group(scan_group),
          .scan_o_v(scan_valid[bs]),.scan_data(scan_data[bs*256+:256]),
          .full(store_full[bs]),.fault(store_fault[bs]));
      end
      for(genvar q=0;q<NQ;q++)begin:g_hub
        ot_hgi_hc_chunk_scan5 #(.CLOCKED(CLOCKED),.MUT(MUT==14?1:0))u_hub(.clk(clk),.clk_leaf(clk_scan[q*8+:8]),.rst_n(rst_n),.clr(clr),
          .in_v(scan_valid[q*5+:5]),.in_data(scan_data[q*5*256+:5*256]),.in_meta(meta1),
          .out_v(hub_v[q]),.out_data(hub_data[q*256+:256]),.out_meta(hub_meta[q*7+:7]),.fault(hub_fault[q]));
      end
      always @(posedge clk)begin meta0<={scan_block,scan_group};meta1<=meta0;end
      reg[255:0]land_data;reg[6:0]land_meta;
      always @*begin
        land_data=0;land_meta=0;
        for(integer q=0;q<NQ;q++)begin
          land_data=land_data|(hub_data[q*256+:256]&{256{hub_v[q]}});
          land_meta=land_meta|(hub_meta[q*7+:7]&{7{hub_v[q]}});
        end
      end
      assign land_tag=land_meta;
      // Four registered eight-chunk packets form the SAME32-leaf tree input.
      // Only the final packet publishes b0; the golden association is unchanged.
      for(genvar g=0;g<4;g++)begin:g_land
        always @(posedge clk)if((|hub_v)&&land_meta[1:0]==g&&!clr&&scan_flush==0)
          b0[g*256+:256]<=land_data;
      end
      always @(posedge clk)if((|hub_v)&&land_meta[1:0]==3&&!clr&&scan_flush==0)b0_i<={1'b0,land_meta[6:2]};
      always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin scan_active<=0;scan_group<=0;scan_block<=0;scan_flush<=0;end
        else if(clr)begin scan_active<=0;scan_group<=0;scan_flush<=12;end
        else begin
          if(scan_flush!=0)scan_flush<=scan_flush-1;
          if(!scan_active&&fb_v&&scan_flush==0)begin scan_active<=1;scan_group<=0;scan_block<=5'(fb);end
          else if(scan_active)begin scan_group<=scan_group+1'b1;if(scan_group==3)scan_active<=0;end
        end
      end
    end else begin:g_legacy_store
      assign land_tag=0;assign store_full=0;assign store_fault=0;assign hub_v=0;assign hub_fault=0;assign hub_data=0;assign hub_meta=0;
      always @(posedge clk)for(integer ws=0;ws<NS;ws++)if(wr[ws])st[tg[ws]]<=hd[ws][31:0];
      always @(posedge clk)if(fb_v)begin
        for(integer cc=0;cc<32;cc++)b0[32*cc+:32]<=st[32*integer'(fb)+cc];
        b0_i<=6'(fb);
      end
    end endgenerate
    wire [31:0] tv [0:5][0:31]; wire [5:0] tf;
    localparam integer DTB = 5 * LA;
    wire [DTB:0] tvl;
    ot_hdc_vline #(.D(DTB)) u_tvl (.clk(clk), .rst_n(rst_n), .v(b0_v), .vd(tvl));
    wire [5:0] tbi;
    ot_hdc_delay #(.W(6), .D(DTB)) u_tbi (.clk(clk), .rst_n(rst_n), .d(b0_i), .q(tbi));
    genvar c, kt, n;
    generate
        for (c = 0; c < 32; c = c + 1) begin : g_t0
            assign tv[0][c] = (MUT == 9) ? b0[32*((c + 1) % 32) +: 32] : b0[32*c +: 32];
        end
        assign tf[0] = 1'b0;
        for (kt = 1; kt <= 5; kt = kt + 1) begin : g_tl
            wire [(32 >> kt)-1:0] f;
            for (c = 0; c < (32 >> kt); c = c + 1) begin : g_tn
                ot_dsrom_qadd #(.LAT(LA)) u_a (CLOCKED?clk_block_add[32-(32>>(kt-1))+c]:clk, rst_n, tvl[LA * (kt - 1)], tv[kt - 1][2 * c], tv[kt - 1][2 * c + 1],
                                               tv[kt][c], f[c]);
            end
            for (c = (32 >> kt); c < 32; c = c + 1) begin : g_tz assign tv[kt][c] = 32'd0; end
            assign tf[kt] = |f;
        end
    endgenerate
    // a row cleared while a block is in the tree: its sum is dropped at the heap (kill line as long as the tree)
    reg [DTB:0] kl;
    wire vsum_v = tvl[DTB] && !kl[DTB] && !clr; wire [31:0] vsum = tv[5][0];
    // block heap (ot_dsrom_su_norm's vector levels): leaves NBP + b, padding right subtrees pass their left value
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    wire [31:0] nv [1:2*NBP-1]; wire nd [1:2*NBP-1]; wire np [1:2*NBP-1]; wire [NBP:0] nf;
    assign nf[0] = 1'b0; assign nf[NBP] = 1'b0;
    generate
        for (n = NBP; n < 2 * NBP; n = n + 1) begin : g_leaf
            reg [31:0] val; reg vd;
            wire hit = vsum_v && tbi == 6'(n - NBP);
            always @(posedge clk or negedge rst_n)
                if (!rst_n) vd <= 1'b0; else if (clr) vd <= 1'b0; else if (hit) vd <= 1'b1;
            always @(posedge clk) if (hit) val <= vsum;
            assign np[n] = hit; assign nd[n] = vd || hit; assign nv[n] = vd ? val : vsum;
        end
        for (n = 1; n < NBP; n = n + 1) begin : g_vn
            localparam integer H = $clog2(NBP) - ($clog2(n + 1) - 1);
            if ((((2 * n + 1) << (H - 1)) - NBP) < NB) begin : g_add
                reg stt, vd, kn; reg [31:0] val; wire [LAV:0] av; wire [31:0] sm;
                wire fire = nd[2 * n] && nd[2 * n + 1] && !stt && !clr;
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rst_n), .v(fire), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (CLOCKED?clk_heap_add[n-1]:clk, rst_n, fire, nv[2 * n], nv[2 * n + 1], sm, nf[n]);
                wire land = av[LAV] && !kn && !clr;          // kn: the add in flight belongs to a cleared row
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) begin stt <= 1'b0; vd <= 1'b0; kn <= 1'b0; end
                    else begin
                        if (av[LAV]) kn <= 1'b0;
                        if (clr) begin stt <= 1'b0; vd <= 1'b0; if (|av[LAV-1:0] || fire) kn <= 1'b1; end
                        else begin if (fire) stt <= 1'b1; if (land) vd <= 1'b1; end
                    end
                always @(posedge clk) if (land) val <= sm;
                assign np[n] = land; assign nd[n] = vd || land; assign nv[n] = vd ? val : sm;
            end else begin : g_pass
                assign nv[n] = nv[2 * n]; assign nd[n] = nd[2 * n]; assign np[n] = np[2 * n]; assign nf[n] = 1'b0;
            end
        end
    endgenerate
    assign ss_v = np[1] && !clr; assign ss = nv[1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            iv <= '0; pk_cr <= '0; vld <= '0; full <= '0; fired <= '0; b0_v <= 1'b0; flt <= 1'b0; n_stale <= '0; kl <= '0;
            for (s = 0; s < NS; s = s + 1) begin iw[s] <= '0; ir[s] <= '0; end
        end else begin
            iv <= pk_v; pk_cr <= tk;
            if(STORELEAF)b0_v <= (|hub_v)&&land_tag[1:0]==3&&!clr&&scan_flush==0;
            else b0_v <= fb_v&&!clr;
            kl <= {kl[DTB-1:0], 1'b0};
            for (s = 0; s < NS; s = s + 1) begin
                if (iv[s]) begin
                    iw[s] <= iw[s] + 1'b1;
                    if ((iw[s] - ir[s]) >= (CB+1)'(CD)) flt <= 1'b1;                  // the sender overran its credits
                end
                if (tk[s]) ir[s] <= ir[s] + 1'b1;
                if (wr[s]) vld[tg[s]] <= 1'b1;
                if (bad[s]) flt <= 1'b1;
                if (tk[s] && hd[s][43:42] != ep) n_stale <= n_stale + 1'b1;
            end
            for (b = 0; b < NB; b = b + 1) full[b] <= STORELEAF?store_full[b]:&vld[32*b +: 32];
            if (fb_v&&(!STORELEAF||(!scan_active&&scan_flush==0))) fired[fb] <= 1'b1;
            if ((|tf) || (|nf[NBP-1:1]) || (STORELEAF&&scan_flush==0&&((|store_fault)||(|hub_fault)))) flt <= 1'b1;
            if (clr) begin
                vld <= '0; full <= '0; fired <= '0; flt <= 1'b0;
                kl <= {(DTB+1){1'b1}};       // everything in the block tree now is of the cleared row
            end
        end
    end
endmodule

// ---- one quarter: 8 LOCAL8 lanes on the quarter's VM slice, the chunk concentrator, scalar return, status
module ot_hgi_hc_qst_b2 #(
    parameter integer QID = 0,
    parameter integer CLOCKED = 0, COEFFLEAF=0,
    parameter integer LQ  = 32,
    parameter integer FD  = 64,
    parameter integer HSL = 1,
    parameter integer RLL = 2,               // relay flops station <-> lane (each way)
    parameter integer CD  = 16,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire [63:0] clk_sl,
    input wire [55:0] clk_chunk,
    input wire [7:0]clk_coeff,
    input wire [7:0]clk_lane,input wire clk_cat,
    output wire [8*16-1:0]   wrq,
    input  wire [7:0]        wrq_cr,
    input  wire [8*257-1:0]  wrr,
    output wire [8*280-1:0]  wwq,
    input  wire [7:0]        wwq_cr,
    input  wire [7:0]        wwq_done,
    input  wire              dn_v,           // command from the centre {op 3, x 8, d 128}
    input  wire [138:0]      dn,
    output wire [1:0]        ck_v,           // chunk slots to the centre
    output wire [2*44-1:0]   ck,
    input  wire [1:0]        ck_cr,
    output reg               sc_v,           // a scalar sector to the centre {slot 2, d 256}
    output reg  [257:0]      sc,
    output reg  [5:0]        stat            // {write dones this cycle 4, fin, flt}
);
    // pin flops; SCRD goes to the lanes of the scalar-home quarter only
    reg dv; reg [138:0] dd; reg [1:0] ep;
    wire c_job = dv && dd[138:136] == 3'd0;
    wire dvl = dv && !(dd[138:136] == 3'd2 && dd[16:15] != 2'(QID));
    always @(posedge clk or negedge rst_n) if (!rst_n) dv <= 1'b0; else dv <= dn_v;
    always @(posedge clk) begin dd <= dn; if (c_job) ep <= dd[48:47]; end
    wire [7:0] l_uv, l_ut, l_wd, l_fin, l_flt; wire [8*10-1:0] l_ux; wire [8*256-1:0] l_ud;
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_ln
        wire lv; wire [138:0] ld;
        ot_hgi_hc_rly #(.W(139), .N(RLL)) u_dn (.clk(clk), .rst_n(rst_n), .v(dvl), .d(dd), .vq(lv), .q(ld));
        wire uv, ut, wd, fn, fl; wire [9:0] ux; wire [255:0] ud;
        ot_hgi_hc_lane_b2 #(.QID(QID), .CLOCKED(CLOCKED), .COEFFLEAF(COEFFLEAF), .LQ(LQ), .FD(FD), .HSL(HSL),
            .MUT((MUT == 2 || (MUT >= 4 && MUT <= 8) || MUT == 13 || MUT == 15) ? MUT : 0)) u_l (.clk(CLOCKED?clk_lane[gl]:clk), .rst_n(rst_n),
            .clk_sl(clk_sl[gl*8+:8]), .clk_chunk(clk_chunk[gl*7+:7]), .clk_coeff(clk_coeff[gl]), .lid(5'(gl)), .wrq(wrq[gl*16 +: 16]), .wrq_cr(wrq_cr[gl]), .wrr(wrr[gl*257 +: 257]), .wwq(wwq[gl*280 +: 280]),
            .wwq_cr(wwq_cr[gl]), .wwq_done(wwq_done[gl]), .dn_v(lv), .dn_op(ld[138:136]), .dn_x(ld[135:128]),
            .dn_d(ld[127:0]), .up_v(uv), .up_t(ut), .up_x(ux), .up_d(ud), .wdone(wd), .fin(fn), .flt(fl));
        wire [2:0] sq;
        ot_hdc_delay #(.W(3), .D(RLL), .RESET(1)) u_st (.clk(clk), .rst_n(rst_n), .d({wd, fn, fl}), .q(sq));
        wire uq; wire [266:0] uqd;
        ot_hgi_hc_rly #(.W(267), .N(RLL)) u_up (.clk(clk), .rst_n(rst_n), .v(uv), .d({ut, ux, ud}), .vq(uq), .q(uqd));
        assign l_uv[gl] = uq; assign l_ut[gl] = uqd[266]; assign l_ux[gl*10 +: 10] = uqd[265:256];
        assign l_ud[gl*256 +: 256] = uqd[255:0];
        assign l_wd[gl] = sq[2]; assign l_fin[gl] = sq[1]; assign l_flt[gl] = sq[0];
    end endgenerate
    // chunks
    wire [7:0] ch_v = l_uv & l_ut; wire [8*42-1:0] ch; wire c_ovf;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_ch
        assign ch[gl*42 +: 42] = {l_ux[gl*10 +: 10], l_ud[gl*256 +: 32]};
    end endgenerate
    ot_hgi_hc_cat_b2 #(.NL(8), .P(2), .QD(32), .CD(CD), .MUT(MUT)) u_cat (.clk(CLOCKED?clk_cat:clk), .rst_n(rst_n), .flush(c_job), .ep(ep),
        .ch_v(ch_v), .ch(ch), .ck_v(ck_v), .ck(ck), .ck_cr(ck_cr), .ovf(c_ovf));
    // scalar sectors: up to 4 slots land in any cycle; one a cycle goes up
    reg [255:0] sb [0:3]; reg [3:0] sp;
    integer w, k;
    always @(posedge clk) begin
        for (w = 0; w < 8; w = w + 1) if (l_uv[w] && !l_ut[w]) sb[l_ux[w*10 +: 2]] <= l_ud[w*256 +: 256];
        sc <= sp[0] ? {2'd0, sb[0]} : sp[1] ? {2'd1, sb[1]} : sp[2] ? {2'd2, sb[2]} : {2'd3, sb[3]};
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sp <= '0; sc_v <= 1'b0; stat <= '0; end
        else begin
            sc_v <= |sp;
            if (sp[0]) sp[0] <= 1'b0; else if (sp[1]) sp[1] <= 1'b0; else if (sp[2]) sp[2] <= 1'b0; else sp[3] <= 1'b0;
            for (w = 0; w < 8; w = w + 1) if (l_uv[w] && !l_ut[w]) sp[l_ux[w*10 +: 2]] <= 1'b1;
            if (c_job) sp <= '0;
            begin : b_pc
                reg [3:0] n; n = '0;
                for (k = 0; k < 8; k = k + 1) n = n + 4'(l_wd[k]);
                stat <= {n, &l_fin, (|l_flt) || c_ovf};
            end
        end
    end
endmodule

// ---- the centre
module ot_hgi_hc_ctl_b2 #(
    parameter integer STORELEAF=0,CLOCKED=0,
    parameter integer D   = 5120,
    parameter integer RLQ = 6,               // relay flops centre <-> quarter (each way)
    parameter integer CD  = 16,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire clk_coll,
    input wire[19:0]clk_store,input wire[31:0]clk_scan,
    input wire[30:0]clk_block_add,clk_heap_add,
    input  wire              job_v_i,
    output wire              job_rdy,
    input  wire [148:0]      job_i,
    input  wire              g_rdy_i,
    output reg               done,
    output reg               fault,
    output wire              idle,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt,
    // per quarter (at the quarter's pins)
    output wire [3:0]        q_dn_v,
    output wire [4*139-1:0]  q_dn,
    input  wire [4*2-1:0]    q_ck_v,
    input  wire [4*88-1:0]   q_ck,
    output wire [4*2-1:0]    q_ck_cr,
    input  wire [3:0]        q_sc_v,
    input  wire [4*258-1:0]  q_sc,
    input  wire [4*6-1:0]    q_stat
);
    localparam integer SD = D / 8, NB = D / 256;
    localparam integer LM = 5, LA = 6;
    function automatic integer tz(input integer x);
        integer t;
        begin t = 0; while (t < 31 && ((x >> t) & 1) == 0) t = t + 1; tz = t; end
    endfunction
    localparam integer DK = tz(D), DF = D >> DK;
    generate if (D != 5120 || RLQ < 1) begin : g_bad
        ot_hgi_hc_eng_b2_requires_D5120_RLQ_ge_1 u_trap ();
    end endgenerate
    // ---- pin flops
    reg job_v, g_rdy; reg [148:0] job; reg rg_q, wg_q;
    localparam [2:0] S_IDLE = 0, S_GRP = 1, S_SC = 2, S_SCW = 3, S_WG = 4, S_RUN = 5, S_FIN = 6;
    reg [2:0] st;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin job_v <= 1'b0; g_rdy <= 1'b0; rg_q <= 1'b0; wg_q <= 1'b0; end
        else begin job_v <= job_v_i && (st == S_IDLE) && !job_v; g_rdy <= g_rdy_i; rg_q <= rg_gnt && rg_req;
                   wg_q <= wg_gnt && wg_req; end
    always @(posedge clk) job <= job_i;
    assign job_rdy = (st == S_IDLE);
    assign idle = (st == S_IDLE);
    wire j_post = (job[148:147] == 2'd1);
    wire [14:0] ja = job[17:3], jb = job[35:21], jo = job[93:79];
    wire job_ok = (job[114:94] == 21'(D)) && (job[2:0] == 3'd0) && (job[20:18] == 3'd0) && (job[78:76] == 3'd0) &&
                  (ja[2:0] == jb[2:0]) && (ja[2:0] == jo[2:0]) && !job[36] && (job[148:147] <= 2'd1);

    // ---- command bus and the quarters' returns (RLQ relay flops each way)
    reg cv; reg [2:0] cop; reg [7:0] cx; reg [127:0] cd;
    wire [7:0] k_v; wire [4*88-1:0] k_d; wire [7:0] k_cr;
    wire [3:0] s_v; wire [4*258-1:0] s_d; wire [4*6-1:0] s_st;
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
        ot_hgi_hc_rly #(.W(139), .N(RLQ)) u_dn (.clk(clk), .rst_n(rst_n), .v(cv), .d({cop, cx, cd}), .vq(q_dn_v[gq]),
            .q(q_dn[gq*139 +: 139]));
        ot_hgi_hc_rly #(.W(44), .N(RLQ)) u_k0 (.clk(clk), .rst_n(rst_n), .v(q_ck_v[2*gq]), .d(q_ck[gq*88 +: 44]),
            .vq(k_v[2*gq]), .q(k_d[gq*88 +: 44]));
        ot_hgi_hc_rly #(.W(44), .N(RLQ)) u_k1 (.clk(clk), .rst_n(rst_n), .v(q_ck_v[2*gq + 1]), .d(q_ck[gq*88 + 44 +: 44]),
            .vq(k_v[2*gq + 1]), .q(k_d[gq*88 + 44 +: 44]));
        ot_hdc_delay #(.W(2), .D(RLQ), .RESET(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(k_cr[2*gq +: 2]), .q(q_ck_cr[2*gq +: 2]));
        ot_hgi_hc_rly #(.W(258), .N(RLQ)) u_sc (.clk(clk), .rst_n(rst_n), .v(q_sc_v[gq]), .d(q_sc[gq*258 +: 258]),
            .vq(s_v[gq]), .q(s_d[gq*258 +: 258]));
        ot_hdc_delay #(.W(6), .D(RLQ), .RESET(1)) u_st (.clk(clk), .rst_n(rst_n), .d(q_stat[gq*6 +: 6]), .q(s_st[gq*6 +: 6]));
    end endgenerate

    // ---- scalars
    reg [2:0] nsc, scs, scl; reg [255:0] scb [0:3]; reg [17:0] c_b; reg [1:0] cq;
    wire [1023:0] scw = {scb[3], scb[2], scb[1], scb[0]};
    wire [639:0] scx = scw[{c_b[2:0], 5'd0} +: 640];
    integer w;
    always @(posedge clk)
        for (w = 0; w < 4; w = w + 1) if (s_v[w]) scb[s_d[w*258 + 256 +: 2]] <= s_d[w*258 +: 256];

    // ---- done count, lane status
    reg [5:0] pc2; reg [12:0] ndone, nexp; reg fin_all, flt_any;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pc2 <= '0; fin_all <= 1'b0; flt_any <= 1'b0; end
        else begin
            pc2 <= 6'(s_st[2 +: 4]) + 6'(s_st[8 +: 4]) + 6'(s_st[14 +: 4]) + 6'(s_st[20 +: 4]);
            fin_all <= s_st[1] && s_st[7] && s_st[13] && s_st[19];
            flt_any <= s_st[0] || s_st[6] || s_st[12] || s_st[18];
        end

    // ---- the collector and the scalar tail: / D, + eps, rsqrt
    reg go_r; reg [1:0] ep;
    wire ss_v, c_flt; wire [31:0] ss; wire [15:0] c_stale;
    ot_hgi_hc_coll_b2 #(.STORELEAF(STORELEAF),.CLOCKED(CLOCKED),.NQ(4), .P(2), .NB(NB), .CD(CD), .LA(LA), .MUT(MUT)) u_coll (.clk(CLOCKED?clk_coll:clk), .rst_n(rst_n), .clr(go_r),
        .ep(ep), .clk_store(clk_store),.clk_scan(clk_scan),.clk_block_add(clk_block_add),.clk_heap_add(clk_heap_add),.pk_v(k_v), .pk(k_d), .pk_cr(k_cr), .ss_v(ss_v), .ss(ss), .flt(c_flt), .n_stale(c_stale));
    reg [31:0] eps_r;
    reg ssv_q; reg [31:0] ss_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) ssv_q <= 1'b0; else ssv_q <= ss_v;
    always @(posedge clk) ss_q <= ss;
    wire [31:0] mq, me, rr; wire mq_v, rr_v, f_div, f_eps, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rst_n), .v(ssv_q), .x(ss_q), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rst_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rst_n, mq_v, mq, eps_r, me, f_eps);
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(ve[LA]), .x(me), .y(rr), .vo(rr_v), .fault(f_rsq));
    reg r_pend; reg [31:0] r_hold;

    // ---- sequencer (ot_hgi_hc_ctl_ll's)
    reg post; reg gsent, gpend; reg [2:0] wb; reg sfault;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; rg_req <= 1'b0; wg_req <= 1'b0; cv <= 1'b0; cop <= '0; cx <= '0;
            cd <= '0; nsc <= '0; scs <= '0; scl <= '0; c_b <= '0; cq <= '0; ndone <= '0; nexp <= '0;
            go_r <= 1'b0; ep <= '0; eps_r <= '0; r_pend <= 1'b0; r_hold <= '0; post <= 1'b0; gsent <= 1'b0;
            gpend <= 1'b0; wb <= '0; sfault <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cv <= 1'b0; go_r <= 1'b0;
            ndone <= ndone + 13'(pc2);
            scl <= scl + 3'(s_v[0]) + 3'(s_v[1]) + 3'(s_v[2]) + 3'(s_v[3]);
            if (g_rdy && st != S_IDLE) gpend <= 1'b1;
            if (!post && gpend && st == S_RUN) wg_req <= 1'b1;
            if (rr_v) begin r_pend <= 1'b1; r_hold <= rr; end
            if (f_div || f_eps || f_rsq || (c_flt && !go_r && st != S_IDLE)) sfault <= 1'b1;
            case (st)
                S_IDLE: if (job_v) begin
                    if (!job_ok) fault <= 1'b1;
                    else begin
                        st <= S_GRP; rg_req <= 1'b1; wg_req <= j_post; post <= j_post; c_b <= job[75:58]; cq <= job[38:37];
                        eps_r <= job[146:115]; nexp <= j_post ? 13'(4 * SD) : 13'(SD);
                        gsent <= 1'b0; gpend <= 1'b0; r_pend <= 1'b0; sfault <= 1'b0; go_r <= 1'b1; ep <= ep + 2'd1;
                    end
                end
                S_GRP: if (rg_q && (wg_q || !post)) begin
                    st <= S_SC; scs <= '0; scl <= '0; ndone <= '0;
                    nsc <= 3'(({3'd0, c_b[2:0]} + (post ? 6'd20 : 6'd4) + 6'd7) >> 3);
                    cv <= 1'b1; cop <= 3'd0; cx <= '0; cd <= {79'd0, ep, 1'b0, post, jo, jb, ja};               // JOB
                end
                S_SC: begin                                                    // one scalar read a cycle
                    cv <= 1'b1; cop <= 3'd2; cx <= 8'(scs); cd <= {111'd0, cq, c_b[17:3] + 15'(scs)};
                    if (scs + 3'd1 == nsc) st <= S_SCW;
                    scs <= scs + 3'd1;
                end
                S_SCW: if (scl == nsc) begin st <= S_WG; wb <= '0; end
                S_WG: begin
                    cv <= 1'b1; cop <= 3'd1; cx <= 8'(wb); cd <= scx[128*wb +: 128];
                    if (wb == (post ? 3'd4 : 3'd0)) st <= S_RUN; else wb <= wb + 3'd1;
                end
                S_RUN: begin
                    if (!cv && cop == 3'd1) begin cv <= 1'b1; cop <= 3'd3; end                   // GO after the weights
                    else if (!post && gpend && !gsent && wg_q && cop != 3'd1) begin cv <= 1'b1; cop <= 3'd4; gsent <= 1'b1; end
                    else if (!post && r_pend && gsent && cop != 3'd1) begin
                        cv <= 1'b1; cop <= 3'd5; cd <= {96'd0, r_hold}; r_pend <= 1'b0;
                    end
                    if (ndone == nexp && fin_all && cop != 3'd1) st <= S_FIN;
                    if (MUT == 4 && cv && (post ? cop == 3'd3 : cop == 3'd5)) st <= S_FIN;
                end
                S_FIN: begin
                    rg_req <= 1'b0; wg_req <= 1'b0; st <= S_IDLE;
                    if (sfault || flt_any) fault <= 1'b1; else done <= 1'b1;
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule

// ---- the B2 engine: VM lanes quarter-major (lane 8 q + b = bank b of slice q)
module ot_hgi_hc_eng_b2 #(
    parameter integer D   = 5120,
    parameter integer CLOCKED = 0, COEFFLEAF=0,
    parameter integer STORELEAF = 0,
    parameter integer LQ  = 32,
    parameter integer FD  = 64,
    parameter integer HSL = 1,
    parameter integer RLQ = 6,
    parameter integer RLL = 2,
    parameter integer CD  = 16,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire [255:0] clk_sl,
    input wire [223:0] clk_chunk,
    input wire [31:0]clk_coeff,
    input wire [31:0]clk_lane,input wire [3:0]clk_qst,clk_cat,
    input wire clk_ctl,clk_coll,
    input wire[19:0]clk_store,input wire[31:0]clk_scan,
    input wire[30:0]clk_block_add,clk_heap_add,
    input  wire              job_v,
    output wire              job_rdy,
    input  wire [148:0]      job,
    input  wire              g_rdy,
    output wire              done,
    output wire              fault,
    output wire              idle,
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    wire [3:0] q_dn_v; wire [4*139-1:0] q_dn; wire [7:0] q_ck_v, q_ck_cr; wire [4*88-1:0] q_ck;
    wire [3:0] q_sc_v; wire [4*258-1:0] q_sc; wire [4*6-1:0] q_stat;
    ot_hgi_hc_ctl_b2 #(.STORELEAF(STORELEAF),.CLOCKED(CLOCKED),.D(D), .RLQ(RLQ), .CD(CD), .MUT(MUT)) u_ctl (.clk(CLOCKED?clk_ctl:clk), .rst_n(rst_n), .clk_coll(clk_coll), .clk_store(clk_store),.clk_scan(clk_scan),.clk_block_add(clk_block_add),.clk_heap_add(clk_heap_add),.job_v_i(job_v),
        .job_rdy(job_rdy), .job_i(job), .g_rdy_i(g_rdy), .done(done), .fault(fault), .idle(idle), .rg_req(rg_req),
        .rg_gnt(rg_gnt), .wg_req(wg_req), .wg_gnt(wg_gnt), .q_dn_v(q_dn_v), .q_dn(q_dn), .q_ck_v(q_ck_v), .q_ck(q_ck),
        .q_ck_cr(q_ck_cr), .q_sc_v(q_sc_v), .q_sc(q_sc), .q_stat(q_stat));
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
        ot_hgi_hc_qst_b2 #(.QID(gq), .CLOCKED(CLOCKED), .COEFFLEAF(COEFFLEAF), .LQ(LQ), .FD(FD), .HSL(HSL), .RLL(RLL), .CD(CD), .MUT(MUT)) u_q (.clk(CLOCKED?clk_qst[gq]:clk),
            .rst_n(rst_n), .clk_sl(clk_sl[gq*64+:64]), .clk_chunk(clk_chunk[gq*56+:56]), .clk_coeff(clk_coeff[gq*8+:8]), .clk_lane(clk_lane[gq*8+:8]), .clk_cat(clk_cat[gq]), .wrq(wrq[gq*128 +: 128]), .wrq_cr(wrq_cr[gq*8 +: 8]), .wrr(wrr[gq*2056 +: 2056]),
            .wwq(wwq[gq*2240 +: 2240]), .wwq_cr(wwq_cr[gq*8 +: 8]), .wwq_done(wwq_done[gq*8 +: 8]),
            .dn_v(q_dn_v[gq]), .dn(q_dn[gq*139 +: 139]), .ck_v(q_ck_v[2*gq +: 2]), .ck(q_ck[gq*88 +: 88]),
            .ck_cr(q_ck_cr[2*gq +: 2]), .sc_v(q_sc_v[gq]), .sc(q_sc[gq*258 +: 258]), .stat(q_stat[gq*6 +: 6]));
    end endgenerate
endmodule
`default_nettype wire
