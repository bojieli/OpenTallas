module ot_dsrom_reindex_kgctl_parent #(
    parameter integer OPT_KC6 = 1,
    parameter integer OPT_KC7 = 1,
    parameter integer OPT_KC8 = 1,   // grouped registered room, replicated slot write enables
    parameter integer LIST_LAT = 6,
    parameter integer NPC  = 32,
    parameter integer WB   = 128,       // reorder slots (blocks), power of two
    parameter integer AW   = 28,        // sector address bits
    parameter integer HW   = 20,        // 4-KB block address bits
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer LBW  = 14,        // local block index bits
    parameter integer LMW  = 11,        // list entries = 2^LMW
    parameter integer DF   = 8          // request FIFO depth per channel and kind
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input wire memory_fault,
    output wire drain_accept,
    output wire [1:0] lr_mask,
    // candidate-list SRAM (two banks, even / odd entries), synchronous read: data of the
    // address presented with lr_re appears on lr_e / lr_o after the edge
    output wire                 lr_re,
    output wire [LMW-2:0]       lr_addr,
    input  wire [LBW-1:0]       lr_e,
    input  wire [LBW-1:0]       lr_o,
    input  wire                 cmd_v,
    input  wire [HW-1:0]        cmd_base,
    input  wire [9:0]           cmd_skip,   // ring head, keys (multiple of 8)
    input  wire [LMW:0]         cmd_n,      // candidate blocks of this stack
    output reg                  busy,
    output reg                  fault,      // cmd_skip not a multiple of 8
    output reg  [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output reg  [NPC*AW-1:0]    req_addr,
    output reg  [NPC*LENW-1:0]  req_len,
    output reg  [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    output reg  [1:0]           dr_v,
    output reg  [$clog2(WB)-1:0] dr_slot,   // block 0's slot (block 1: dr_slot + 1)
    output reg  [2*7-1:0]       dr_j,
    output reg  [2*5-1:0]       dr_fc,
    output reg  [2*5-1:0]       dr_f0,
    output reg  [2*LBW-1:0]     dr_blk,
    input  wire                 dr_ready    // room for this drain and two in flight
);
    localparam integer SW = $clog2(WB);
    localparam integer QW = LMW + 1;
    localparam integer FW = $clog2(DF);
    localparam integer ND = 5;              // decode stages (fixed latency, never stall)
    localparam integer PD = 16;              // decoded-pair FIFO depth
    localparam integer PW = $clog2(PD);
    localparam integer GS = 8;              // copies of the dispatch write stage
    localparam integer SG = WB / GS;        // slots fed by one slot-side copy
    localparam integer CG = NPC / GS;       // channels fed by one channel-side copy

    function automatic [4:0] fold(input [HW-1:0] b);
        fold = b[4:0] ^ b[9:5];
    endfunction
    function automatic [WB-1:0] onehot(input [SW-1:0] s);
        onehot = {{(WB-1){1'b0}}, 1'b1} << s;
    endfunction
    function automatic [WB-1:0] rotl(input [WB-1:0] v, input integer k);
        rotl = (v << k) | (v >> (WB - k));
    endfunction

    reg            run;
    reg [HW-1:0]   base;
    reg [6:0]      skip8;
    reg [QW-1:0]   n;
    reg [QW-1:0]   rd_seq;                  // next pair to read
    reg [QW-1:0]   d_seq;                   // drain head
    reg [QW-1:0]   d_left;                  // n - d_seq
    reg [4:0]      occ;                     // pairs read and not yet dispatched

    // -- list read and the decode pipe -----------------------------------------------------------
    wire           rd_go = run && !fault && !memory_fault && (rd_seq < n) && (occ < PD);
    assign lr_re = rd_go;
    assign lr_addr = rd_seq[LMW-1:1];
    assign lr_mask={(QW'(rd_seq+1)<n),1'b1};
    reg            c0_v;   reg [QW-1:0] c0_seq; reg [1:0] c0_m;
    reg            e1_v;   reg [QW-1:0] e1_seq; reg [1:0] e1_m;
    reg            e2_v;   reg [QW-1:0] e2_seq; reg [1:0] e2_m;
    reg            e3_v;   reg [QW-1:0] e3_seq; reg [1:0] e3_m;
    reg            e4_v;   reg [QW-1:0] e4_seq; reg [1:0] e4_m;
    reg            e5_v;   reg [QW-1:0] e5_seq; reg [1:0] e5_m;
    reg [LBW+6:0]  lk    [0:1];             // local key / 8 (e2 stage, combinational)
    reg [LBW-1:0]  e1_blk[0:1], e2_blk[0:1], e3_blk[0:1], e4_blk[0:1], e5_blk[0:1];
    reg [LBW+4:0]  e2_m17[0:1];             // 17 x super-block
    reg [6:0]      e2_j [0:1], e3_j [0:1], e4_j [0:1], e5_j [0:1];
    reg [HW-1:0]   e3_o0[0:1], e3_oc[0:1];  // offsets of the scale / code block
    reg [HW-1:0]   e4_b0[0:1], e4_bc[0:1], e5_b0[0:1], e5_bc[0:1];
    reg [4:0]      e5_f0[0:1], e5_fc[0:1];
    reg [NPC-1:0]  e5_cm[0:1], e5_sm[0:1];

    initial if(OPT_KC6!=1||OPT_KC7!=1||OPT_KC8!=1||LIST_LAT!=6) $fatal(1,"production parent uses its modeled fixed cuts");

    // -- decoded-pair FIFO, registered head ----------------------------------------------------------
    reg [QW-1:0]   pf_seq [0:PD-1];
    reg [1:0]      pf_m   [0:PD-1];
    reg [LBW-1:0]  pf_blk [0:2*PD-1];
    reg [6:0]      pf_j   [0:2*PD-1];
    reg [4:0]      pf_f0  [0:2*PD-1], pf_fc [0:2*PD-1];
    reg [HW-1:0]   pf_b0  [0:2*PD-1], pf_bc [0:2*PD-1];
    reg [NPC-1:0]  pf_cm  [0:2*PD-1], pf_sm [0:2*PD-1];
    reg [PW-1:0]   pf_wp, pf_rp;
    reg [PW:0]     pf_n;
    reg            hd_v;   reg [QW-1:0] hd_seq; reg [1:0] hd_m; reg [SW-1:0] hd_s1;
    reg [LBW-1:0]  hd_blk[0:1]; reg [6:0] hd_j[0:1]; reg [4:0] hd_f0[0:1], hd_fc[0:1];
    reg [HW-1:0]   hd_b0[0:1], hd_bc[0:1];
    reg [NPC-1:0]  hd_cm[0:1], hd_sm[0:1];

    // -- dispatch: decided on registers, written one cycle later -----------------------------------
    // both conditions registered: every request FIFO has >= 4 free entries (2 in flight + 2),
    // and the slots in use (dispatched pairs x 2 - drained) leave room for this pair and one
    // in flight (conservative: a FIFO filling anywhere pauses dispatch for a cycle)
    reg            room_all, rob_ok;
    reg [QW-1:0]   inuse;
    // OPT_KC8: the 64-FIFO room AND is retimed: each channel group (4 code + 4 scale FIFOs, beside its
    // channel copy) registers the AND of its own 8 room bits, and the dispatch ANDs the 8 group flags.
    // room_g(t+1)[g] = &rm_g(t), so &room_g == room_all every cycle: identical dispatch, zero latency.
    reg  [7:0]     room_g;
    wire           room_ok = (OPT_KC8 != 0) ? &room_g : room_all;
    wire           disp = run && !fault && !memory_fault && hd_v && rob_ok && room_ok;
    wire           hd_take = !hd_v || disp;
    reg            w_v;
    wire [WB-1:0]   w_oh0, w_oh1;            // the write stage's slots, one-hot (zero when nothing is written)
    // OPT_KC8: three kept copies of each one-hot (metadata / code-pending / scale-pending writes): a slot's
    // enable drove 95 mux selects (kc7: 512 post-route slew violations on those nets).  Same D as w_oh*.
    wire [WB-1:0]  w_oh0_d, w_oh1_d;
    wire [3*WB-1:0] w_oh0_c, w_oh1_c;
    // The write stage's operands, in GS kept copies (ot_hdc_v41x_kg_kreg_parent) loaded from the head every cycle
    // (used only on w_v / a one-hot slot): slot copy g feeds slots [g SG, (g+1) SG), channel copy g the request
    // FIFOs of channels [g CG, (g+1) CG); the channel copies' masks are gated by the dispatch (zero otherwise).
    localparam integer SLW = LBW + 7 + 5 + 5 + 2 * NPC;            // blk, j, f0, fc, cm, sm
    localparam integer CHW = 2 * HW + 5 + 7 + SW + 2 * CG;         // b0, bc, fc, j, rs, cm / sm of the group
    wire [GS*2*SLW-1:0] sl_q;               // copy g, lane l at [(2 g + l) SLW +: SLW]
    wire [GS*2*CHW-1:0] ch_q;
    // One priced edge splits the global head into two physical halves.
    // The word and its real dispatch enable move together; no ready bypass.
    localparam integer HCW=SLW+2*HW+SW+WB;
    localparam integer HCP=HCW+1;
    wire [4*HCP-1:0] half_q;
    wire [3:0] half_bad;
    generate for(genvar hh=0;hh<2;hh=hh+1)begin:g_half
        for(genvar hl=0;hl<2;hl=hl+1)begin:g_lane
            wire [SW-1:0] hs=hl?hd_s1:hd_seq[SW-1:0];
            wire [HCW-1:0] d={hl?w_oh1_d:w_oh0_d,hd_b0[hl],hd_bc[hl],hs,
                    hd_blk[hl],hd_j[hl],hd_f0[hl],hd_fc[hl],
                    disp?hd_cm[hl]:{NPC{1'b0}},disp?hd_sm[hl]:{NPC{1'b0}}};
            ot_hdc_v41x_kg_kreg_parent #(.W(HCP)) u_h(.clk(clk),.d({^d,d}),
                .q(half_q[(2*hh+hl)*HCP+:HCP]));
            assign half_bad[2*hh+hl]=^half_q[(2*hh+hl)*HCP+:HCP];
        end
    end endgenerate

    // -- per-channel request FIFOs: [0, NPC) code, [NPC, 2 NPC) scale ------------------------------
    reg [AW-1:0]   fq_addr [0:2*NPC*DF-1];
    reg [SW-1:0]   fq_slot [0:2*NPC*DF-1];
    reg [FW-1:0]   fq_rp   [0:2*NPC-1];
    reg [FW-1:0]   fq_wp   [0:2*NPC-1];
    reg [FW:0]     fq_n    [0:2*NPC-1];

    // -- slot state ------------------------------------------------------------------------------------
    reg [NPC-1:0]  pend_c [0:WB-1];
    reg [NPC-1:0]  pend_s [0:WB-1];
    reg [4:0]      cntc   [0:4*WB-1]; // four distinct beats per actual code channel plus check bit
    reg [WB-1:0]   adm;
    reg [WB-1:0]   adm_q;                   // adm, a cycle later (aligned with cpart)
    reg [7:0]      cpart [0:WB-1];          // nothing pending in each 8-channel group (code 0-3, scale 4-7)
    reg [WB-1:0]   cmp;                     // registered completion: adm_q && &cpart
    reg [6:0]      m_j   [0:WB-1];
    reg [4:0]      m_fc  [0:WB-1];
    reg [4:0]      m_f0  [0:WB-1];
    reg [LBW-1:0]  m_blk [0:WB-1];

    assign rsp_rdy = {NPC{1'b1}};           // every beat has its slot (allocated at dispatch)

    // -- drain: completion of head .. head+3 sampled a cycle earlier; adv_r = the step taken then ----
    reg [3:0]      rq;
    reg [1:0]      adv_r;
    reg [WB-1:0]   hoh;                     // the drain head's slot, one-hot (= d_seq mod WB)
    wire [SW-1:0]  h0 = d_seq[SW-1:0];
    wire           rq0 = (adv_r == 2'd0) ? rq[0] : (adv_r == 2'd1) ? rq[1] : rq[2];
    wire           rq1 = (adv_r == 2'd0) ? rq[1] : (adv_r == 2'd1) ? rq[2] : rq[3];
    wire           can0 = run && !fault && !memory_fault && (d_left != 0) && rq0 && dr_ready;
    wire           can1 = can0 && (d_left > 1) && rq1;
    wire drain_eligible = run && !fault && !memory_fault && (d_left != 0) && rq0;
    wire drain_two = (d_left > 1) && rq1;
    wire [WB-1:0] next_hoh;
    wire [WB-1:0] rotated_one = rotl(hoh, 1);
    wire [WB-1:0] rotated_two = rotl(hoh, 2);
    generate for (genvar hs=0; hs<GS; hs=hs+1) begin : g_head_local
        ot_dsrom_parent_ready_last #(.W(SG)) u_select (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(hoh[hs*SG +: SG]), .one_head(rotated_one[hs*SG +: SG]),
            .two_head(rotated_two[hs*SG +: SG]), .next_head(next_hoh[hs*SG +: SG]));
    end endgenerate
    // All arithmetic and rob comparisons are independent of actual ready.
    wire [QW-1:0] seq_one = d_seq + QW'(1), seq_two = d_seq + QW'(2);
    wire [QW-1:0] left_one = d_left - QW'(1), left_two = d_left - QW'(2);
    wire [QW-1:0] use_base = inuse + (disp ? QW'(2) : QW'(0));
    wire [QW-1:0] use_one = use_base - QW'(1), use_two = use_base - QW'(2);
    wire [QW-1:0] next_seq, next_left, next_use;
    wire next_rob_ok;
    generate for (genvar ds=0; ds<QW; ds=ds+4) begin : g_drain_ready_last
        localparam integer W = (QW-ds < 4) ? QW-ds : 4;
        ot_dsrom_parent_ready_last #(.W(W)) u_seq (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(d_seq[ds+:W]), .one_head(seq_one[ds+:W]),
            .two_head(seq_two[ds+:W]), .next_head(next_seq[ds+:W]));
        ot_dsrom_parent_ready_last #(.W(W)) u_left (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(d_left[ds+:W]), .one_head(left_one[ds+:W]),
            .two_head(left_two[ds+:W]), .next_head(next_left[ds+:W]));
        ot_dsrom_parent_ready_last #(.W(W)) u_use (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(use_base[ds+:W]), .one_head(use_one[ds+:W]),
            .two_head(use_two[ds+:W]), .next_head(next_use[ds+:W]));
    end endgenerate
    ot_dsrom_parent_ready_last #(.W(1)) u_rob (
        .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
        .old_head(use_base <= QW'(WB-6)), .one_head(use_one <= QW'(WB-6)),
        .two_head(use_two <= QW'(WB-6)), .next_head(next_rob_ok));
    reg            dq_v; reg [1:0] dq_m; reg [SW-1:0] dq_slot;    // drain decided: read metadata next
    reg [WB-1:0]   dq_oh;

    assign w_oh0_d = (rst_n && !(cmd_v && !busy) && run && disp && hd_m[0]) ? onehot(hd_seq[SW-1:0]) : {WB{1'b0}};
    assign w_oh1_d = (rst_n && !(cmd_v && !busy) && run && disp && hd_m[1]) ? onehot(hd_s1) : {WB{1'b0}};
    generate for (genvar wc = 0; wc < 3; wc = wc + 1) begin : g_woh
        if (OPT_KC8 != 0) begin : g_on
            ot_hdc_v41x_kg_kreg_parent #(.W(WB)) u_w0 (.clk(clk), .d(half_q[0*HCP+SLW+2*HW+SW+:WB]), .q(w_oh0_c[wc*WB +: WB]));
            ot_hdc_v41x_kg_kreg_parent #(.W(WB)) u_w1 (.clk(clk), .d(half_q[1*HCP+SLW+2*HW+SW+:WB]), .q(w_oh1_c[wc*WB +: WB]));
        end else begin : g_off
            assign w_oh0_c[wc*WB +: WB] = w_oh0;
            assign w_oh1_c[wc*WB +: WB] = w_oh1;
        end
    end endgenerate

    assign w_oh0=w_oh0_c[0+:WB];
    assign w_oh1=w_oh1_c[0+:WB];
    // per channel issue: the scale head first, else the code head
    reg [NPC-1:0]  iss, use_s;
    integer q;
    always @* begin
        for (q = 0; q < NPC; q = q + 1) begin
            use_s[q] = (fq_n[NPC + q] != 0);
            iss[q] = run && !fault && !memory_fault && ((fq_n[q] != 0) || use_s[q]) && (!req_v[q] || req_rdy[q]);
        end
    end

    // -- the write-stage copies ------------------------------------------------------------------------
    genvar gg, gl;
    generate for (gg = 0; gg < GS; gg = gg + 1) begin : g_cp
        for (gl = 0; gl < 2; gl = gl + 1) begin : g_l
            wire [HCW-1:0] h=half_q[(2*(gg/(GS/2))+gl)*HCP+:HCW];
            wire [SW-1:0] rs=h[SLW+:SW];
            wire [HW-1:0] bc=h[SLW+SW+:HW],b0=h[SLW+SW+HW+:HW];
            wire [4:0] fc=h[2*NPC+:5];
            wire [6:0] j=h[2*NPC+10+:7];
            wire [CG-1:0] cmg=h[NPC+gg*CG+:CG],smg=h[gg*CG+:CG];
            ot_hdc_v41x_kg_kreg_parent #(.W(SLW)) u_s (.clk(clk), .d(h[0+:SLW]),
                .q(sl_q[(2*gg+gl)*SLW+:SLW]));
            ot_hdc_v41x_kg_kreg_parent #(.W(CHW)) u_c (.clk(clk),.d({b0,bc,fc,j,rs,cmg,smg}),
                .q(ch_q[(2*gg+gl)*CHW+:CHW]));
        end
    end endgenerate

    integer p, l, e, c, k, g;
    reg [FW:0]     cnt;
    reg [FW-1:0]   wp;
    reg [NPC-1:0]  t;
    reg [2*NPC-1:0] rm;
    wire [FW:0] fq_nm1 [0:2*NPC-1];
    wire [FW:0] fq_np1 [0:2*NPC-1];
    wire [FW:0] fq_np2 [0:2*NPC-1];
    generate for (genvar fp = 0; fp < 2*NPC; fp = fp+1) begin : g_count_alternatives
        // Fixed-width modular arithmetic, before the ready-dependent pop.
        assign fq_nm1[fp] = fq_n[fp] - 1'b1;
        assign fq_np1[fp] = fq_n[fp] + 1'b1;
        assign fq_np2[fp] = fq_n[fp] + 2'd2;
    end endgenerate
    reg push_a, push_b, pop_now;
    reg [QW-1:0]   nu;
    reg            b0, b1;
    reg [HW-1:0]   cb0, cbc;
    reg [4:0]      cfc;
    reg [6:0]      cj;
    reg [SW-1:0]   crs;
    reg [SW-1:0]   x_rs [0:1];
    reg [AW-1:0]   x_ad [0:1];

    // Encoded responses are captured beside each 16-slot group. Full original
    // tag padding, kind, beat range, pending identity and checked sparse counts
    // are validated before any completion permission changes.
    localparam integer RW = SW+5;
    wire [GS*NPC*RW-1:0] rr_q;
    wire [WB-1:0] rr_oh[0:NPC-1];
    wire [NPC-1:0] rr_kind[0:GS-1];
    wire [NPC*2-1:0] rr_beat[0:GS-1];
    wire [NPC-1:0] rr_bad[0:GS-1];
    generate for(genvar rg=0;rg<GS;rg=rg+1)begin:g_rsp
        wire [NPC*RW-1:0] din;
        for(genvar rp=0;rp<NPC;rp=rp+1)begin:g_p
            wire v=rsp_v[rp]&&rst_n&&run;
            assign din[rp*RW+:RW]={^{v,rsp_tag[rp*TAGW+:SW+1],rsp_beat[rp*BEATW+:2]},v,
                rsp_beat[rp*BEATW+:2],rsp_tag[rp*TAGW+:SW+1]};
            wire [RW-1:0] z=rr_q[(rg*NPC+rp)*RW+:RW];
            assign rr_kind[rg][rp]=z[SW];
            assign rr_beat[rg][rp*2+:2]=z[SW+1+:2];
            assign rr_bad[rg][rp]=^z;
            for(genvar re=rg*SG;re<(rg+1)*SG;re=re+1)begin:g_e
                assign rr_oh[rp][re]=z[SW+3]&&(z[SW-1:0]==SW'(re));
            end
        end
        ot_hdc_v41x_kg_kreg_parent #(.W(NPC*RW)) u_r(.clk(clk),.d(din),.q(rr_q[rg*NPC*RW+:NPC*RW]));
    end endgenerate
    reg [LIST_LAT-2:0] list_v;
    reg [QW-1:0] list_seq[0:LIST_LAT-2];
    reg [1:0] list_m[0:LIST_LAT-2];
    integer li, ci;
    reg [3:0] next_beats;
    assign drain_accept=can0&&!fault&&!memory_fault;
    // ---- control (synchronously reset) ----------------------------------------------------------------
    always @(posedge clk) begin
        if (!rst_n) begin
            run <= 1'b0; busy <= 1'b0; fault <= 1'b0; req_v <= 0; dr_v <= 0; dq_v <= 1'b0;
            list_v<=0; c0_v <= 1'b0; e1_v <= 1'b0; e2_v <= 1'b0; e3_v <= 1'b0; e4_v <= 1'b0; e5_v <= 1'b0;
            hd_v <= 1'b0; w_v <= 1'b0; pf_n <= 0; pf_wp <= 0; pf_rp <= 0; occ <= 0;
            adm <= 0; adm_q <= 0; cmp <= 0; rq <= 0; adv_r <= 0; hoh <= {{(WB-1){1'b0}}, 1'b1};
            room_all <= 1'b1; room_g <= 8'hff; rob_ok <= 1'b1; inuse <= 0;
            list_v <= 0;
            for (p = 0; p < 2 * NPC; p = p + 1) begin fq_rp[p] <= 0; fq_wp[p] <= 0; fq_n[p] <= 0; end
            for (p = 0; p < 4 * WB; p = p + 1) cntc[p] <= 5'd0;   // empty distinct-beat mask
        end else begin
            if(memory_fault||(run&&(|half_bad)))fault<=1;
            // completion, two cycles late: per-group partials, then their AND (never early: adm_q is
            // registered alongside the partials)
            adm_q <= adm;
            for (e = 0; e < WB; e = e + 1) begin
                if (!OPT_KC6)
                    for (k = 0; k < 4; k = k + 1) begin
                        cpart[e][k]     <= ~|pend_c[e][8*k +: 8];
                        cpart[e][4 + k] <= ~|pend_s[e][8*k +: 8];
                    end
                cmp[e] <= adm_q[e] && &cpart[e];
            end
            for(p=0;p<NPC;p=p+1)begin
                if(rsp_v[p]&&((|rsp_tag[p*TAGW+SW+1+:TAGW-SW-1])||
                    (rsp_tag[p*TAGW+SW]?(rsp_beat[p*BEATW+:BEATW]!=0):(rsp_beat[p*BEATW+:BEATW]>=4))))fault<=1;
                for(e=0;e<WB;e=e+1)if(rr_oh[p][e])begin
                    ci=(p^m_fc[e])&3;
                    if(rr_bad[e/SG][p]||!adm[e]||
                       (rr_kind[e/SG][p]?!pend_s[e][p]:(!pend_c[e][p]||(^cntc[e*4+ci])||
                        cntc[e*4+ci][rr_beat[e/SG][p*2+:2]])))fault<=1;
                    else if(!rr_kind[e/SG][p])begin
                        next_beats=cntc[e*4+ci][3:0] | (4'b0001 << rr_beat[e/SG][p*2+:2]);
                        cntc[e*4+ci]<=(&next_beats)?5'd0:{^next_beats,next_beats};
                    end
                end
            end
            // dispatch write stage (decided last cycle): admitted slots
            adm <= adm | w_oh0 | w_oh1;
            // drain stage 2: retire the slots (after the dispatch write, as before)
            dr_v <= 2'b00;
            if (dq_v) begin
                adm <= (adm | w_oh0 | w_oh1) & ~(dq_oh | (dq_m[1] ? rotl(dq_oh, 1) : {WB{1'b0}}));
                dr_v <= dq_m;
                dr_slot <= dq_slot;
            end

            if (cmd_v && !busy) begin
                run <= 1'b1; busy <= 1'b1;
                base <= cmd_base; skip8 <= cmd_skip[9:3]; n <= cmd_n;
                fault <= (cmd_skip[2:0] != 3'd0);
                rd_seq <= 0; d_seq <= 0; d_left <= cmd_n; occ <= 0; inuse <= 0; rob_ok <= 1'b1;
                hoh <= {{(WB-1){1'b0}}, 1'b1};
                list_v<=0; c0_v <= 1'b0; e1_v <= 1'b0; e2_v <= 1'b0; e3_v <= 1'b0; e4_v <= 1'b0; e5_v <= 1'b0;
                hd_v <= 1'b0; w_v <= 1'b0; pf_n <= 0; pf_wp <= 0; pf_rp <= 0; rq <= 0; adv_r <= 0; dq_v <= 1'b0;
            end else if (run) begin
                // list read (SRAM output valid next cycle)
                list_v<={list_v[LIST_LAT-3:0],rd_go};
                c0_v<=list_v[LIST_LAT-2];c0_m<=list_m[LIST_LAT-2];
                if (rd_go) rd_seq <= rd_seq + 2;
                occ <= occ + (rd_go ? 5'd1 : 5'd0) - (disp ? 5'd1 : 5'd0);
                e1_v <= c0_v; e2_v <= e1_v; e3_v <= e2_v; e4_v <= e3_v; e5_v <= e4_v;
                if (e5_v) pf_wp <= pf_wp + 1'b1;
                if (hd_take) begin
                    hd_v <= (pf_n != 0);
                    if (pf_n != 0) pf_rp <= pf_rp + 1'b1;
                end
                pf_n <= pf_n + (e5_v ? 1'b1 : 1'b0) - ((hd_take && pf_n != 0) ? 1'b1 : 1'b0);
                // dispatch decision -> write stage
                w_v <= disp;
                // per-channel issue
                for (p = 0; p < NPC; p = p + 1) begin
                    if (req_v[p] && req_rdy[p]) req_v[p] <= 1'b0;
                    if (iss[p]) req_v[p] <= 1'b1;
                end
                // FIFO pushes (from the write stage; masks zero unless written) / pops, counts, room
                for (p = 0; p < 2 * NPC; p = p + 1) begin
                    g = (p % NPC) / CG;
                    c = (p % NPC) % CG;
                    cnt = fq_n[p];
                    wp = fq_wp[p];
                    for (l = 0; l < 2; l = l + 1)
                        if (ch_q[(2*g+l)*CHW + (p < NPC ? CG : 0) + c]) begin
                            wp = wp + 1'b1;
                            cnt = cnt + 1'b1;
                        end
                    fq_wp[p] <= wp;
                    // room counts the pushes but not this cycle's pop (conservative: keeps the request
                    // port's req_rdy out of the 64-FIFO room AND)
                    rm[p] = (cnt + 6 <= DF);
                    if (p < NPC ? (iss[p % NPC] && !use_s[p % NPC]) : (iss[p % NPC] && use_s[p % NPC])) begin
                        fq_rp[p] <= fq_rp[p] + 1'b1;
                        cnt = cnt - 1'b1;
                    end
                    if (OPT_KC6) begin
                        push_a = ch_q[(2*g+0)*CHW + (p < NPC ? CG : 0) + c];
                        push_b = ch_q[(2*g+1)*CHW + (p < NPC ? CG : 0) + c];
                        pop_now = p < NPC ? (iss[p % NPC] && !use_s[p % NPC])
                                          : (iss[p % NPC] && use_s[p % NPC]);
                        // Late pop selects precomputed counts; rm above still
                        // sees pushed count BEFORE pop, exactly as the donor.
                        case ({push_a, push_b})
                            2'b00: fq_n[p] <= pop_now ? fq_nm1[p] : fq_n[p];
                            2'b11: fq_n[p] <= pop_now ? fq_np1[p] : fq_np2[p];
                            default: fq_n[p] <= pop_now ? fq_n[p] : fq_np1[p];
                        endcase
                    end else fq_n[p] <= cnt;
                end
                room_all <= &rm;
                for (g = 0; g < GS; g = g + 1)
                    room_g[g] <= &{rm[NPC + g*CG +: CG], rm[g*CG +: CG]};
                // drain stage 1: head and next, in order
                for (k = 0; k < 4; k = k + 1) rq[k] <= |(cmp & rotl(hoh, k));
                adv_r <= can1 ? 2'd2 : (can0 ? 2'd1 : 2'd0);
                dq_v <= can0;
                dq_m <= {can1, 1'b1};
                dq_slot <= h0;
                dq_oh <= hoh;
                if (OPT_KC7) begin
                    d_seq <= next_seq;
                    d_left <= next_left;
                end else if (can0) begin
                    d_seq <= d_seq + (can1 ? 2 : 1);
                    d_left <= d_left - (can1 ? 2 : 1);
                end
                if (can0 && !OPT_KC6) hoh <= can1 ? rotl(hoh, 2) : rotl(hoh, 1);
                if (OPT_KC6) hoh <= next_hoh;
                nu = inuse + (disp ? QW'(2) : QW'(0)) - (can1 ? QW'(2) : (can0 ? QW'(1) : QW'(0)));
                inuse <= OPT_KC7 ? next_use : nu;
                rob_ok <= OPT_KC7 ? next_rob_ok : (nu <= QW'(WB - 4));
                if (d_left == 0 && !dq_v) run <= 1'b0;
            end else if (busy && dr_v == 2'b00 && !dq_v) busy <= 1'b0;
        end
    end

    localparam integer RQPW = AW + LENW + TAGW;
    wire [NPC*RQPW-1:0] next_payload;
    generate for (genvar pp=0; pp<NPC; pp=pp+1) begin : g_payload_ready_last
        wire [RQPW-1:0] code_payload = {fq_addr[pp*DF+fq_rp[pp]],
            LENW'(4), TAGW'({1'b0, fq_slot[pp*DF+fq_rp[pp]]})};
        wire [RQPW-1:0] scale_payload = {fq_addr[(NPC+pp)*DF+fq_rp[NPC+pp]],
            LENW'(1), TAGW'({1'b1, fq_slot[(NPC+pp)*DF+fq_rp[NPC+pp]]})};
        wire [RQPW-1:0] old_payload = {req_addr[pp*AW+:AW],
            req_len[pp*LENW+:LENW], req_tag[pp*TAGW+:TAGW]};
        for (genvar ps=0; ps<RQPW; ps=ps+8) begin : g_slice
            localparam integer W = (RQPW-ps < 8) ? RQPW-ps : 8;
            ot_dsrom_parent_payload_last #(.W(W)) u_select (
                .eligible(run && ((fq_n[pp] != 0) || use_s[pp])),
                .scale(use_s[pp]), .valid(req_v[pp]), .ready(req_rdy[pp]),
                .old_data(old_payload[ps+:W]), .code_data(code_payload[ps+:W]),
                .scale_data(scale_payload[ps+:W]), .next_data(next_payload[pp*RQPW+ps+:W]));
        end
    end endgenerate
    // ---- data (no reset: every word is written before it is read) ---------------------------------------
    integer p2, l2, e2, c2, g2;
    reg [6:0]      aj [0:1];
    reg [4:0]      afc [0:1], af0 [0:1];
    reg [LBW-1:0]  ablk [0:1];
    localparam integer MDW = 7 + 5 + 5 + LBW;
    reg [MDW-1:0]  mp;
    reg [MDW-1:0]  dpart [0:2*GS-1];
    always @(posedge clk) begin
        // Derived partials have no reset value; adm_q/cmp still reset-clear.
        // NBA reads the same pre-edge pending state as the donor.
        if (OPT_KC6)
            for (e2 = 0; e2 < WB; e2 = e2 + 1)
                for (c2 = 0; c2 < 4; c2 = c2 + 1) begin
                    cpart[e2][c2] <= ~|pend_c[e2][8*c2 +: 8];
                    cpart[e2][4+c2] <= ~|pend_s[e2][8*c2 +: 8];
                end
        // decode pipe
        list_seq[0]<=rd_seq;list_m[0]<={(QW'(rd_seq+1)<n),1'b1};
        for(li=1;li<LIST_LAT-1;li=li+1)begin list_seq[li]<=list_seq[li-1];list_m[li]<=list_m[li-1];end
        c0_seq <= list_seq[LIST_LAT-2];
        e1_seq <= c0_seq; e2_seq <= e1_seq; e3_seq <= e2_seq; e4_seq <= e3_seq; e5_seq <= e4_seq;
        e1_m <= c0_m; e2_m <= e1_m; e3_m <= e2_m; e4_m <= e3_m; e5_m <= e4_m;
        for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
            e1_blk[l2] <= l2 ? lr_o : lr_e;
            lk[l2] = {{LBW{1'b0}}, skip8} + {7'd0, e1_blk[l2]};
            e2_blk[l2] <= e1_blk[l2]; e2_j[l2] <= lk[l2][6:0];
            e2_m17[l2] <= {lk[l2][LBW+6:7], 4'd0} + {4'd0, lk[l2][LBW+6:7]};
            e3_blk[l2] <= e2_blk[l2]; e3_j[l2] <= e2_j[l2];
            e3_o0[l2] <= HW'(e2_m17[l2]);
            e3_oc[l2] <= HW'(e2_m17[l2]) + HW'(1) + HW'(e2_j[l2][6:3]);
            e4_blk[l2] <= e3_blk[l2]; e4_j[l2] <= e3_j[l2];
            e4_b0[l2] <= base + e3_o0[l2];
            e4_bc[l2] <= base + e3_oc[l2];
            e5_blk[l2] <= e4_blk[l2]; e5_j[l2] <= e4_j[l2]; e5_b0[l2] <= e4_b0[l2]; e5_bc[l2] <= e4_bc[l2];
            e5_f0[l2] <= fold(e4_b0[l2]); e5_fc[l2] <= fold(e4_bc[l2]);
            t = 0;
            for (c2 = 0; c2 < 4; c2 = c2 + 1) t[(5'({e4_j[l2][2:0], 2'b00}) + 5'(c2)) ^ fold(e4_bc[l2])] = 1'b1;
            e5_cm[l2] <= t;
            t = 0;
            t[e4_j[l2][6:2] ^ fold(e4_b0[l2])] = 1'b1;
            e5_sm[l2] <= t;
        end
        // pair FIFO: push from the pipe, pop into the head register
        if (run && e5_v) begin
            pf_seq[pf_wp] <= e5_seq; pf_m[pf_wp] <= e5_m;
            for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
                pf_blk[2*pf_wp+l2] <= e5_blk[l2]; pf_j[2*pf_wp+l2] <= e5_j[l2];
                pf_f0[2*pf_wp+l2] <= e5_f0[l2]; pf_fc[2*pf_wp+l2] <= e5_fc[l2];
                pf_b0[2*pf_wp+l2] <= e5_b0[l2]; pf_bc[2*pf_wp+l2] <= e5_bc[l2];
                pf_cm[2*pf_wp+l2] <= e5_m[l2] ? e5_cm[l2] : {NPC{1'b0}};
                pf_sm[2*pf_wp+l2] <= e5_m[l2] ? e5_sm[l2] : {NPC{1'b0}};
            end
        end
        if (run && hd_take && pf_n != 0) begin
            hd_seq <= pf_seq[pf_rp]; hd_m <= pf_m[pf_rp]; hd_s1 <= SW'(pf_seq[pf_rp]) + 1'b1;
            for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
                hd_blk[l2] <= pf_blk[2*pf_rp+l2]; hd_j[l2] <= pf_j[2*pf_rp+l2];
                hd_f0[l2] <= pf_f0[2*pf_rp+l2]; hd_fc[l2] <= pf_fc[2*pf_rp+l2];
                hd_b0[l2] <= pf_b0[2*pf_rp+l2]; hd_bc[l2] <= pf_bc[2*pf_rp+l2];
                hd_cm[l2] <= pf_cm[2*pf_rp+l2]; hd_sm[l2] <= pf_sm[2*pf_rp+l2];
            end
        end
        // responses clear pending bits; the dispatch write (one-hot slots, slot copies) then sets them
        for (p2 = 0; p2 < NPC; p2 = p2 + 1)
            for (e2 = 0; e2 < WB; e2 = e2 + 1)
                if (rr_oh[p2][e2] && !rr_bad[e2/SG][p2] && adm[e2] &&
                    (rr_kind[e2/SG][p2] ? pend_s[e2][p2] :
                     (pend_c[e2][p2] && !(^cntc[e2*4 + ((p2 ^ m_fc[e2]) & 3)]) &&
                      !cntc[e2*4 + ((p2 ^ m_fc[e2]) & 3)][rr_beat[e2/SG][p2*2+:2]]))) begin
                    if (rr_kind[e2/SG][p2]) pend_s[e2][p2] <= 1'b0;
                    else if (&(cntc[e2*4 + ((p2 ^ m_fc[e2]) & 3)][3:0] | (4'b0001 << rr_beat[e2/SG][p2*2+:2]))) pend_c[e2][p2] <= 1'b0;
                end
        for (e2 = 0; e2 < WB; e2 = e2 + 1)
            for (l2 = 0; l2 < 2; l2 = l2 + 1)
                begin
                    if (l2 ? w_oh1_c[e2] : w_oh0_c[e2])
                        {m_blk[e2], m_j[e2], m_f0[e2], m_fc[e2]} <= sl_q[(2*(e2/SG)+l2)*SLW + 2*NPC +: SLW - 2*NPC];
                    if (l2 ? w_oh1_c[WB + e2] : w_oh0_c[WB + e2])
                        pend_c[e2] <= sl_q[(2*(e2/SG)+l2)*SLW + NPC +: NPC];
                    if (l2 ? w_oh1_c[2*WB + e2] : w_oh0_c[2*WB + e2])
                        pend_s[e2] <= sl_q[(2*(e2/SG)+l2)*SLW +: NPC];
                end
        // request FIFO entries (lane 0 at the write pointer, lane 1 after it)
        for (p2 = 0; p2 < 2 * NPC; p2 = p2 + 1) begin
            g2 = (p2 % NPC) / CG;
            c2 = (p2 % NPC) % CG;
            b0 = ch_q[(2*g2+0)*CHW + (p2 < NPC ? CG : 0) + c2];
            b1 = ch_q[(2*g2+1)*CHW + (p2 < NPC ? CG : 0) + c2];
            for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
                {cb0, cbc, cfc, cj, crs} = ch_q[(2*g2+l2)*CHW + 2*CG +: CHW - 2*CG];
                x_rs[l2] = crs;
                // code: channel p serves column p ^ fold(Bc); scale: sector j of B0
                x_ad[l2] = (p2 < NPC) ? AW'({cbc, 5'(p2 % NPC) ^ cfc, 2'b00}) : AW'({cb0, cj});
            end
            if (b0) begin fq_slot[p2 * DF + fq_wp[p2]] <= x_rs[0]; fq_addr[p2 * DF + fq_wp[p2]] <= x_ad[0]; end
            if (b1) begin
                fq_slot[p2 * DF + FW'(fq_wp[p2] + (b0 ? 1 : 0))] <= x_rs[1];
                fq_addr[p2 * DF + FW'(fq_wp[p2] + (b0 ? 1 : 0))] <= x_ad[1];
            end
        end
        // per-channel issue data
        for (p2 = 0; p2 < NPC; p2 = p2 + 1)
            if (OPT_KC7) begin
                {req_addr[p2*AW+:AW], req_len[p2*LENW+:LENW], req_tag[p2*TAGW+:TAGW]}
                    <= next_payload[p2*RQPW+:RQPW];
            end else if (iss[p2]) begin
                if (use_s[p2]) begin
                    req_addr[p2*AW +: AW] <= fq_addr[(NPC + p2) * DF + fq_rp[NPC + p2]];
                    req_len[p2*LENW +: LENW] <= LENW'(1);
                    req_tag[p2*TAGW +: TAGW] <= TAGW'({1'b1, fq_slot[(NPC + p2) * DF + fq_rp[NPC + p2]]});
                end else begin
                    req_addr[p2*AW +: AW] <= fq_addr[p2 * DF + fq_rp[p2]];
                    req_len[p2*LENW +: LENW] <= LENW'(4);
                    req_tag[p2*TAGW +: TAGW] <= TAGW'({1'b0, fq_slot[p2 * DF + fq_rp[p2]]});
                end
            end
        // drain metadata: stage 1 registers per-16-slot partial AND-OR reads of the head and next slot
        // (both admitted and complete when taken, so their metadata cannot change before stage 2);
        // stage 2 ORs the GS partials
        for (g2 = 0; g2 < GS; g2 = g2 + 1)
            for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
                mp = 0;
                for (e2 = g2 * SG; e2 < (g2 + 1) * SG; e2 = e2 + 1)
                    mp = mp | ({m_j[e2], m_fc[e2], m_f0[e2], m_blk[e2]} & {MDW{hoh[(e2 + WB - l2) % WB]}});
                dpart[2*g2+l2] <= mp;
            end
        for (l2 = 0; l2 < 2; l2 = l2 + 1) begin
            mp = 0;
            for (g2 = 0; g2 < GS; g2 = g2 + 1) mp = mp | dpart[2*g2+l2];
            {aj[l2], afc[l2], af0[l2], ablk[l2]} = mp;
        end
        if (dq_v) begin
            dr_j <= {aj[1], aj[0]}; dr_fc <= {afc[1], afc[0]}; dr_f0 <= {af0[1], af0[0]};
            dr_blk <= {ablk[1], ablk[0]};
        end
    end
endmodule

// A W-bit register that synthesis keeps as its own instance: Yosys opt_merge merges flip-flops with identical
// inputs even under (* keep *), which would fold the write-stage copies back into one high-fanout register
// (same reasoning as rtl/v41rom/ot_v41_kreg.sv).
(* keep_hierarchy *)
module ot_hdc_v41x_kg_kreg_parent #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule


module ot_dsrom_parent_ready_last #(parameter integer W=16) (
    input wire eligible, two, ready,
    input wire [W-1:0] old_head, one_head, two_head,
    output wire [W-1:0] next_head
);
    (* keep = 1 *) wire [W-1:0] eligible_head = eligible ? (two ? two_head : one_head) : old_head;
    assign next_head = ready ? eligible_head : old_head;
endmodule

// Combinational partition only: no ready sample, state, or protocol edge.
(* keep_hierarchy = "yes" *)
module ot_dsrom_parent_payload_last #(parameter integer W=8) (
    input wire eligible, scale, valid, ready,
    input wire [W-1:0] old_data, code_data, scale_data,
    output wire [W-1:0] next_data
);
    (* keep = 1 *) wire [W-1:0] selected = scale ? scale_data : code_data;
    (* keep = 1 *) wire [W-1:0] available = eligible ? selected : old_data;
    assign next_data = (ready || !valid) ? available : old_data;
endmodule
