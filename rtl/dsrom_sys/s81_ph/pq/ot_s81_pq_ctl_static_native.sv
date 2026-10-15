`timescale 1ns/1ps
// Compiler calendar successor. No response/availability/completion signal
// controls the event timeline. Arithmetic and native ROM word decoding are
// copied from the pinned PQ datapath; all launches/consumes/retirements are fixed.
module ot_s81_pq_ctl_static_native (
 input wire clk,
 input wire rst_n,
 output wire q_consume,
 output wire b_consume,
 output wire aq_vin,
 input wire [1:0] aqf,
 output wire [9:0] aqi_o,
 output wire ba_v_o,
 output reg [1:0] ba_wv_o,
 output wire [7:0] ba_blk_o,
 output wire [47:0] hw_o,
 output wire [35:0] h_hi_o,
 output wire [15:0] h_b0_o,
 output wire [15:0] h_b1_o,
 output wire [457:0] mdr_o,
 input wire [11:0] q2f_i,
 input wire [191:0] ga_i,
 output wire [608:0] bc_hr_o,
 input wire calendar_v,input wire[71:0] calendar_action,
 input wire go,
 input wire [8:0] i_ph,
 input wire [2:0] i_np,
 input wire [18:0] i_xbase,
 input wire [18:0] i_xps,
 input wire [18:0] i_obase,
 input wire [18:0] i_ops,
 input wire [1:0] i_fmt,
 output wire ready,
 output wire idle,
 output reg x_re,
 output reg [18:0] x_addr,
 input wire x_rv,
 input wire f_fault,
 output reg fault,
 output reg [31:0] phase_cycles,
 output reg ev_go,
 output reg ev_end,
 output reg stream_end_v,output reg[1:0] stream_end_tag,
 output reg [1:0] ev_tag,
 output wire [9:0] rom_pa0,
 output wire [9:0] rom_pa1,
 input wire [63:0] rom_pq0,
 input wire [63:0] rom_pq1,
 output wire [10:0] rom_sa,
 input wire [47:0] rom_sq
);
 localparam integer PHW=9,SAW=11,R=128,VAW=19,VRD=64,KMAX=6144,RG=11;
 localparam integer NBLK=192,BAW=8,NGR=12,NWB=192,WBW=8,BW=1633;
 wire[0:0] rst_cv;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr
 (.clk(clk),.rst_n_in(rst_n),.rst_n(rst_cv));
 wire rst_c=rst_cv[0];
 wire[71:0] action=calendar_v ? calendar_action : 72'd0;
 wire[1:0] accept_tag=action[1:0];
 wire rq_v=action[22];wire[13:0] rq_k=action[36:23];
 wire rq_par=action[37],rq_fam=action[38];
 `ifdef OT_S81_PQ_STATIC_MUT_TAG
 wire[1:0] config_tag=action[61:60]^2'd1,launch_tag=action[64:63];
`else
 wire[1:0] config_tag=action[61:60],launch_tag=action[64:63];
`endif
 reg sv[0:3],sr[0:3],si[0:3];
 reg[8:0] s_ph[0:3];reg[18:0] s_xb[0:3],s_ob[0:3],s_xps[0:3],s_ops[0:3];
 reg[1:0] s_fm[0:3];reg[63:0] s_pw[0:3];reg[15:0] s_rs[0:3];
 reg[2:0] s_np[0:3];reg[3:0] s_np1[0:3];
 reg[18:0] s_tot[0:3],s_tm0[0:3],s_tm1[0:3],s_tq[0:3][0:3];
 wire[18:0] s_tm0n[0:3],s_tm1n[0:3],s_totn[0:3];
 reg[18:0] rows_seen[0:3];
 reg[1:0] iss_tag;
 wire any_v=sv[0]|sv[1]|sv[2]|sv[3];
 assign ready=1'b1;assign idle=!any_v;
 reg[31:0] cyc;
    genvar gst;
    generate for (gst = 0; gst < 4; gst = gst + 1) begin : g_st
        ot_v41_ksadd #(.W(19)) u_a0 (.a(s_tq[gst][0]), .b(s_tq[gst][1]), .cin(1'b0), .s(s_tm0n[gst]), .cout());
        ot_v41_ksadd #(.W(19)) u_a1 (.a(s_tq[gst][2]), .b(s_tq[gst][3]), .cin(1'b0), .s(s_tm1n[gst]), .cout());
        ot_v41_ksadd #(.W(19)) u_at (.a(s_tm0[gst]), .b(s_tm1[gst]), .cin(1'b0), .s(s_totn[gst]), .cout());
    end endgenerate
    reg           a_v, a_v2;
    reg [1:0]     a_tag, a_tag2;
    reg [PHW-1:0] a_ph;
    // Calendar-assigned tag; input fields use the native one-edge capture relay.
    reg [VAW-1:0] a_xb, a_ob, a_xps, a_ops;
    reg [1:0]     a_fm;
    reg [2:0]     a_np;
    wire [3:0]    a_oh_d = go ? (4'b0001 << accept_tag) : 4'b0000;
    wire [7:0]    a_oh;
    ot_v41_kreg #(.W(4), .AR(1)) u_aoh0 (.clk(clk), .arst_n(rst_c), .d(a_oh_d), .q(a_oh[3:0]));
    ot_v41_kreg #(.W(4), .AR(1)) u_aoh1 (.clk(clk), .arst_n(rst_c), .d(a_oh_d), .q(a_oh[7:4]));
    always @(posedge clk) begin
        a_xb <= i_xbase; a_ob <= i_obase; a_xps <= i_xps; a_ops <= i_ops; a_fm <= i_fmt; a_np <= i_np;
    end
    integer ka;
    always @(posedge clk)
        for (ka = 0; ka < 4; ka = ka + 1) begin
            if (a_oh[ka]) begin s_xb[ka] <= a_xb; s_ob[ka] <= a_ob; s_xps[ka] <= a_xps; s_ops[ka] <= a_ops; end
            if (a_oh[4 + ka]) begin s_ph[ka] <= a_ph; s_fm[ka] <= a_fm; s_np[ka] <= a_np; s_np1[ka] <= 4'(a_np) + 4'd1; end
        end
    wire [63:0] ph_q0, ph_q1;

    // macro ports: the NEXT address (a_ph registers it at accept); the macro registers it itself
    wire [PHW-1:0] a_ph_n = go ? i_ph : a_ph;
    assign rom_pa0 = {a_ph_n, 1'b0}; assign rom_pa1 = {a_ph_n, 1'b1};
    assign ph_q0 = rom_pq0; assign ph_q1 = rom_pq1;           // two-cycle synchronous macro: valid with a_v2

    // v15: the two quantisers are T_AQ tiles (ot_dsrom_aq12t) in the spine wrapper
    localparam integer AQL = 29;
    wire [1:0] aq_f = aqf;
`ifdef OT_PQ_AQ_PIN_LAUNCH
    // Move AQ's first validity flop into the controller's launch pin owner.
    // AQ removes exactly that validity stage locally, keeping every data epoch.
    // Distinct async-reset owner avoids synthesis merging this pin launch
    // with u_aqi's first metadata flop (that flop resets from rst_c).
    reg aq_v_pin;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) aq_v_pin <= 0;
        else aq_v_pin <= rst_c && rq_v && !rq_fam;
    assign aq_vin = aq_v_pin;
`else
    assign aq_vin = rq_v && !rq_fam;
`endif
    // Quantizer metadata follows the actual fixed AQ datapath latency.
    localparam integer NQR = 2 * NBLK;                  // qb rows
    wire           aq_v_n = rq_v && !rq_fam;
    wire [BAW+1:0] aqi_d;                               // {v, block, parity} at AQL - 2
    ot_hdc_delay #(.W(BAW + 2), .D(AQL - 2), .RESET(1)) u_aqi (.clk(clk), .rst_n(rst_c),
        .d({aq_v_n, rq_k[BAW+4:5], rq_par}), .q(aqi_d));
    assign aqi_o = aqi_d;

 reg ba_v,ba_par;reg[13:0] ba_k;
 reg[7:0] ba_blk;
 wire[7:0] bw_blk_n=8'(((rq_par ? KMAX : 0)+32'(rq_k))/VRD);
 assign ba_v_o=ba_v;assign ba_blk_o=ba_blk;
 always @(posedge clk) ba_blk<=bw_blk_n;
    // R0: registered ROM address + the word's attributes; RA: the macro's own pipeline register; R1: the ROM word
    reg           r0_v, r0_lp, r0_lo, r0_fam;
    reg [1:0]     r0_tag;
    reg [2:0]     r0_pos;
    reg [SAW-1:0] r0_a;
    reg           ra_v, ra_lp, ra_lo, ra_fam;
    reg [1:0]     ra_tag;
    reg [2:0]     ra_pos;
    wire [47:0] st_q;

    // macro port: the NEXT address (rd_a, which r0_a registers every cycle); the macro is a two-cycle synchronous ROM
    // (address register, internal pipeline register) and returns the word of r0_a two cycles later, as below
    assign rom_sa = action[50:40]; assign st_q = rom_sq;

    reg           r1_v, r1_lp, r1_lo, r1_fam;
    reg [1:0]     r1_tag;
    reg [2:0]     r1_pos;
    reg [47:0]    r1_w;
    // R2: derived fields
    wire          r1_spar = r1_tag[0] ^ r1_pos[0];
    wire [7:0]    r1_u  = r1_w[8:1];
    wire [2:0]    r1_b  = r1_w[11:9];
    wire [1:0]    r1_sv = r1_w[13:12];
    // max over the byte lanes whose bit is set (0 if none): a balanced tree, the same value as the pinned serial scan
    wire [7:0]    r1_g0 = r1_w[4] ? r1_w[15:8]  : 8'd0;
    wire [7:0]    r1_g1 = r1_w[5] ? r1_w[23:16] : 8'd0;
    wire [7:0]    r1_g2 = r1_w[6] ? r1_w[31:24] : 8'd0;
    wire [7:0]    r1_g3 = r1_w[7] ? r1_w[39:32] : 8'd0;
    wire [7:0]    r1_m01 = (r1_g1 > r1_g0) ? r1_g1 : r1_g0;
    wire [7:0]    r1_m23 = (r1_g3 > r1_g2) ? r1_g3 : r1_g2;
    // Last max level retains the native balanced reduction and register edge.
    // need_q = ({u, sv[1], b, 5'd0} + 32) mod 2^15, need_b = ({umax, 7'd0} + 128) mod 2^15 (the pinned formulas);
    // need_q is formed in R2, need_b's increment at the push
    wire [9:0]  r1_nq;
    ot_v41_inc #(.W(10)) u_nq (.a({r1_u[5:0], r1_sv[1], r1_b}), .inc(1'b1), .y(r1_nq), .co());
    wire [15:0] r1_blk0 = (r1_spar ? 16'(NBLK) : 16'd0) + {5'd0, r1_u, 1'b0, r1_b};
    wire [15:0] r1_blk1 = (r1_spar ? 16'(NBLK) : 16'd0) + {5'd0, r1_u, 1'b1, r1_b};
    reg           r2_v, r2_lp, r2_lo, r2_fam, r2_spar;
    reg [1:0]     r2_tag;
    reg [2:0]     r2_pos;
    reg [47:0]    r2_w;
    reg [9:0]     r2_nq;
    reg [7:0]     r2_m01, r2_m23;
    reg [15:0]    r2_b0, r2_b1;
    reg [35:0]    r2_hi;
    // R3: the last max level; need_b's increment at the push
    reg           r3_v, r3_lp, r3_lo, r3_fam, r3_spar;
    reg [1:0]     r3_tag;
    reg [2:0]     r3_pos;
    reg [47:0]    r3_w;
    reg [9:0]     r3_nq;
    reg [7:0]     r3_umax;
    reg [15:0]    r3_b0, r3_b1;
    reg [35:0]    r3_hi;
    wire [7:0]    r3_nb;
    ot_v41_inc #(.W(8)) u_nb (.a(r3_umax), .inc(1'b1), .y(r3_nb), .co());
    // an entry: {w 48, need 15, spar, lp, lo, fam, tag 2, pos 3, b0 16, b1 16, hi 36}
    localparam integer EW = 48 + 15 + 4 + 2 + 3 + 16 + 16 + 36;
    wire [EW-1:0] r3_e = {r3_w, r3_fam ? {r3_nb, 7'd0} : {r3_nq, 5'd0}, r3_spar, r3_lp, r3_lo, r3_fam, r3_tag, r3_pos,
                          r3_b0, r3_b1, r3_hi};

 reg[EW-1:0] he;reg hv;
 wire[47:0] hw=he[EW-1 -:48];
 wire h_fam=he[EW-67];wire[1:0] h_tag=he[EW-68 -:2];
 wire[2:0] h_pos=he[EW-70 -:3];
 wire[15:0] h_b0=he[EW-73 -:16],h_b1=he[EW-89 -:16];
 wire[35:0] h_hi=he[35:0];
 wire h_lastop=he[EW-66];
 assign q_consume=hv&&hw[0]&&!h_fam;
 assign b_consume=hv&&hw[0]&&h_fam;
 assign hw_o=hw;assign h_hi_o=h_hi;assign h_b0_o=h_b0;assign h_b1_o=h_b1;
    reg         p1_xs_v, p1_xb_v, p1_go, p1_gobf, p1_cfg;
    reg [7:0]   p1_p;
    reg [2:0]   p1_b, p1_pos, p1_np;
    reg [1:0]   p1_sv, p1_tag;
    reg [3:0]   p1_bsv;
    reg [31:0]  p1_u;
    reg [PHW-1:0] p1_ph;
    // stage 2: the broadcast registers
    reg         bt_xs_v, bt_xb_v;
    reg [7:0]   bt_p;
    reg [2:0]   bt_b;
    reg [1:0]   bt_sv;
    wire [255:0] bt_q0 = '0, bt_q1 = '0;  // T_QB (its registered fields are spliced into bc by the wrapper)
    wire [9:0]   bt_e0 = '0, bt_e1 = '0;
    reg [3:0]   bt_bsv;
    reg [31:0]  bt_u;
    reg         bt_go, bt_gobf, bt_cfg;
    reg [1:0]   bt_tag;
    reg [2:0]   bt_np, bt_pos;
    reg [PHW-1:0] bt_ph;
    always @(posedge clk) begin
`ifdef OT_PQC_MUT_CTL
        p1_p <= hw[8:1]; p1_b <= h_fam ? hw[11:9] : hw[3:1];          // mutant: block field of the wrong family
`else
        p1_p <= hw[8:1]; p1_b <= h_fam ? hw[3:1] : hw[11:9];
`endif p1_sv <= hw[13:12]; p1_pos <= h_pos;
        p1_bsv <= hw[7:4]; p1_u <= hw[39:8];
        // stage 2
        bt_p <= p1_p; bt_b <= p1_b; bt_sv <= p1_sv; bt_pos <= p1_pos; bt_bsv <= p1_bsv; bt_u <= p1_u;
    end
    // ------------------------------------------------------------------ broadcast wire stages
    wire [BW-1025:0] bc_h = {bt_cfg, bt_ph, bt_np, bt_go, bt_gobf, bt_tag, bt_xs_v, bt_p, bt_b, bt_sv, bt_q0, bt_e0, bt_q1,
                             bt_e1, bt_pos, bt_pos, bt_xb_v, bt_b, bt_bsv, bt_u};
    // v15: bc_hr's valid / configuration bits reset (top PHW + 9 bits and xb_v at 39), its data does not; the BST +
    // RPT wire stages are T_BC relay tiles in the wrapper
    localparam integer BRT = PHW + 9;
    reg  [BW-1025:0] bc_hd;
    reg  [BRT:0]     bc_hc;
    always @(posedge clk) bc_hd <= bc_h;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) bc_hc <= '0; else bc_hc <= {bc_h[BW-1025 -: BRT], bc_h[39]};
    reg  [BW-1025:0] bc_hr;
    always @* begin bc_hr = bc_hd; bc_hr[BW-1025 -: BRT] = bc_hc[BRT:1]; bc_hr[39] = bc_hc[0]; end
    assign bc_hr_o = bc_hr;

    // per-group replicas of the per-tag return configuration (one-cycle copies of the masters, kept)
    // per tag: {ob, 7 ops, 5 ops, 3 ops, ops, rs, pw63, pw62, fmt == 0, fmt == 1} (CFW bits)
    localparam integer CFW = 5 * VAW + 18;
    localparam integer GRW = 4 * CFW + 4 + 2;               // one group's replica word (+ the issued op's tag)
    wire [GRW-1:0] g_md;                                    // the masters, packed
    genvar gt, gg;
    generate for (gt = 0; gt < 4; gt = gt + 1) begin : g_mt
        wire [VAW-1:0] o1 = s_ops[gt];
        wire [VAW-1:0] o3, o5, o7;
        ot_v41_ksadd #(.W(VAW)) u_o3 (.a(o1), .b({o1[VAW-2:0], 1'b0}), .cin(1'b0), .s(o3), .cout());
        ot_v41_ksadd #(.W(VAW)) u_o5 (.a(o1), .b({o1[VAW-3:0], 2'b0}), .cin(1'b0), .s(o5), .cout());
        ot_v41_ksadd #(.W(VAW)) u_o7 (.a({o1[VAW-4:0], 3'b0}), .b(~o1), .cin(1'b1), .s(o7), .cout());
        assign g_md[CFW*gt +: CFW] = {s_ob[gt], o7, o5, o3, o1, s_rs[gt][13:0],
                                      s_pw[gt][63], s_pw[gt][62], s_fm[gt] == 2'd0, s_fm[gt] == 2'd1};
        assign g_md[4*CFW + gt] = sv[gt] && si[gt];
    end endgenerate
    assign g_md[4*CFW + 4 +: 2] = iss_tag;
    // v11: the masters (slot registers -> stride adders -> packing) are registered once at the spine before the group
    // replicas, so the replicas' D is a wire from one register (v9 R = 128: s_ops -> o3/o5/o7 -> 16 replicas across
    // the die was an SS class, -21.1 ps; +1 cycle on the configuration's way to the return stage)
    reg  [GRW-1:0]     g_mdr, g_mdr2;
    // v13 (margin-first): a second master stage, so the die-crossing replica nets start from a register placed
    // between the slot logic and the groups (+1 cycle on the configuration's way to the return stage)
    always @(posedge clk) begin g_mdr <= g_md; g_mdr2 <= g_mdr; end
    assign mdr_o = g_mdr2;
    wire [NGR-1:0] q2_f = q2f_i;
    integer kg, kt, kr, kq, kc;

    // ------------------------------------------------------------------ row counts from the registered root tags
    // stage A: per group of 8 regions and per tag, a popcount; stage B: groups of four summed; stage C: total
    // v13: stage C is two stages (C1 pairs of B summed, C2 total; gb -> rc was +46 ps at 833), so a row is counted
    // one cycle later -- the same cycle its write leaves (+1 row-write stage), keeping idle >= the last row write
    // The return leaves expose NGR counters, regardless of their region
    // partition. A fixed 8-region assumption reads beyond ga_i for RG=11.
    localparam integer NCA = NGR;
    localparam integer NCB = (NCA + 3) / 4;
    localparam integer NCP = (NCB + 1) / 2;
    reg [7:0] gp [0:NCP-1][0:3];
    wire [3:0] ga [0:NCA-1][0:3];
    genvar gga, ggt;
    generate for (gga = 0; gga < NCA; gga = gga + 1) begin : g_ga
        for (ggt = 0; ggt < 4; ggt = ggt + 1) begin : g_t
            assign ga[gga][ggt] = ga_i[16*gga + 4*ggt +: 4];
        end
    end endgenerate
    reg [7:0] gb [0:NCB-1][0:3];
    // v15: stage B as a Kogge-Stone tree over the four group popcounts (the seam from the T_RET tiles is register ->
    // two prefix adds -> register; the same sum, mod 256, as the serial accumulation)
    wire [7:0] gbn [0:NCB-1][0:3];
    genvar gqb, gtb;
    generate for (gqb = 0; gqb < NCB; gqb = gqb + 1) begin : g_gb
        for (gtb = 0; gtb < 4; gtb = gtb + 1) begin : g_t
            wire [7:0] t0 = (4*gqb + 0 < NCA) ? 8'(ga[4*gqb + 0][gtb]) : 8'd0;
            wire [7:0] t1 = (4*gqb + 1 < NCA) ? 8'(ga[(4*gqb + 1 < NCA) ? 4*gqb + 1 : 0][gtb]) : 8'd0;
            wire [7:0] t2 = (4*gqb + 2 < NCA) ? 8'(ga[(4*gqb + 2 < NCA) ? 4*gqb + 2 : 0][gtb]) : 8'd0;
            wire [7:0] t3 = (4*gqb + 3 < NCA) ? 8'(ga[(4*gqb + 3 < NCA) ? 4*gqb + 3 : 0][gtb]) : 8'd0;
            wire [7:0] s01, s23, s;
            ot_v41_ksadd #(.W(8)) u_a (.a(t0), .b(t1), .cin(1'b0), .s(s01), .cout());
            ot_v41_ksadd #(.W(8)) u_b (.a(t2), .b(t3), .cin(1'b0), .s(s23), .cout());
            ot_v41_ksadd #(.W(8)) u_c (.a(s01), .b(s23), .cin(1'b0), .s(s), .cout());
            assign gbn[gqb][gtb] = s;
        end
    end endgenerate
    reg [7:0] rc [0:3];
    reg [7:0] gm;
    reg [7:0] racc;
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin
            for (kt = 0; kt < 4; kt = kt + 1) begin
                rc[kt] <= 8'd0;
                for (kq = 0; kq < NCB; kq = kq + 1) gb[kq][kt] <= 8'd0;
                for (kq = 0; kq < NCP; kq = kq + 1) gp[kq][kt] <= 8'd0;
            end
        end else begin
            for (kt = 0; kt < 4; kt = kt + 1) begin
                for (kq = 0; kq < NCB; kq = kq + 1) gb[kq][kt] <= gbn[kq][kt];
                for (kq = 0; kq < NCP; kq = kq + 1)
                    gp[kq][kt] <= gb[2 * kq][kt] + ((2 * kq + 1 < NCB) ? gb[2 * kq + 1][kt] : 8'd0);
                racc = 8'd0;
                for (kq = 0; kq < NCP; kq = kq + 1) racc = racc + gp[kq][kt];
                rc[kt] <= racc;
            end
        end
    end

 integer ks;
 always @(posedge clk or negedge rst_c) begin
  if(!rst_c) begin
   fault<=0;cyc<=0;phase_cycles<=0;ev_go<=0;ev_end<=0;ev_tag<=0;stream_end_v<=0;stream_end_tag<=0;
   a_v<=0;a_v2<=0;a_tag<=0;a_tag2<=0;a_ph<=0;
   x_re<=0;ba_v<=0;ba_wv_o<=0;
   r0_v<=0;ra_v<=0;r1_v<=0;r2_v<=0;r3_v<=0;hv<=0;
   p1_xs_v<=0;p1_xb_v<=0;p1_go<=0;p1_gobf<=0;p1_cfg<=0;p1_tag<=0;p1_ph<=0;p1_np<=0;
   bt_xs_v<=0;bt_xb_v<=0;bt_go<=0;bt_gobf<=0;bt_cfg<=0;bt_tag<=0;bt_ph<=0;bt_np<=0;iss_tag<=0;
   for(ks=0;ks<4;ks=ks+1) begin sv[ks]<=0;sr[ks]<=0;si[ks]<=0;rows_seen[ks]<=0;end
  end else begin
   cyc<=any_v ? cyc+1'b1 : 0;
   ev_go<=action[62];ev_end<=|action[68:65];
   stream_end_v<=hv&&h_lastop;
   if(hv&&h_lastop)stream_end_tag<=h_tag;
   if(action[62])ev_tag<=launch_tag;
   if(|action[68:65])ev_tag<={action[68]|action[67],action[68]|action[66]};
   if((action[68:65]&(action[68:65]-4'd1))!=0)fault<=1;
   // Faults diagnose violated compiler contracts; they never gate events.
   if(f_fault||(|aqf)||(|q2f_i)||x_rv!=rq_v||(|action[71:70]))fault<=1;
   if(go&&sv[accept_tag])fault<=1;
   if(go&&!calendar_v)fault<=1;
   a_v<=go;a_tag<=accept_tag;a_v2<=a_v;a_tag2<=a_tag;
   if(go)begin sv[accept_tag]<=1;sr[accept_tag]<=0;si[accept_tag]<=0;a_ph<=i_ph;end
   if(a_v2)begin s_pw[a_tag2]<=ph_q0;s_rs[a_tag2]<=ph_q1[15:0];sr[a_tag2]<=1;end
   for(ks=0;ks<4;ks=ks+1)begin
    s_tq[ks][0]<={3'd0,s_pw[ks][61:46]}&{19{s_np1[ks][0]}};
    s_tq[ks][1]<={2'd0,s_pw[ks][61:46],1'b0}&{19{s_np1[ks][1]}};
    s_tq[ks][2]<={1'd0,s_pw[ks][61:46],2'b0}&{19{s_np1[ks][2]}};
    s_tq[ks][3]<={s_pw[ks][61:46],3'b0}&{19{s_np1[ks][3]}};
    s_tm0[ks]<=s_tm0n[ks];s_tm1[ks]<=s_tm1n[ks];s_tot[ks]<=s_totn[ks];
    rows_seen[ks]<=rows_seen[ks]+19'(rc[ks]);
    if(action[65+ks])begin
     // Retirement is fixed even on a count mismatch. No runtime drain wait.
     sv[ks]<=0;sr[ks]<=0;si[ks]<=0;rows_seen[ks]<=0;
     if(!sv[ks]||rows_seen[ks]+19'(rc[ks])!=s_tot[ks])fault<=1;
    end
   end
   if(action[69])phase_cycles<=cyc+1'b1;
   // All three issue strobes and their tags come only from the calendar.
   p1_cfg<=action[59];p1_go<=action[62];
   if(action[59])begin
    p1_ph<=s_ph[config_tag];p1_np<=s_np[config_tag];si[config_tag]<=1;iss_tag<=config_tag;
    if(!sv[config_tag]||!sr[config_tag])fault<=1;
   end
   if(action[62])begin
    p1_gobf<=s_pw[launch_tag][0];p1_tag<=launch_tag;
    if(!sv[launch_tag]||!sr[launch_tag]||!si[launch_tag])fault<=1;
   end
   x_re<=action[2];x_addr<=action[21:3];
   ba_v<=rq_v&&rq_fam;ba_par<=rq_par;ba_k<=rq_k;
   ba_wv_o<={2{rq_v&&rq_fam}}&{bw_blk_n[0],~bw_blk_n[0]};
   r0_v<=action[39];r0_a<=action[50:40];r0_tag<=action[52:51];r0_pos<=action[55:53];
   r0_fam<=action[56];r0_lp<=action[57];r0_lo<=action[58];
   ra_v<=r0_v;ra_tag<=r0_tag;ra_pos<=r0_pos;ra_fam<=r0_fam;ra_lp<=r0_lp;ra_lo<=r0_lo;
   r1_v<=ra_v;r1_w<=st_q;r1_tag<=ra_tag;r1_pos<=ra_pos;r1_fam<=ra_fam;r1_lp<=ra_lp;r1_lo<=ra_lo;
   r2_v<=r1_v;r2_w<=r1_w;r2_tag<=r1_tag;r2_pos<=r1_pos;r2_fam<=r1_fam;r2_lp<=r1_lp;r2_lo<=r1_lo;
   r2_spar<=r1_spar;r2_nq<=r1_nq;r2_m01<=r1_m01;r2_m23<=r1_m23;r2_b0<=r1_blk0;r2_b1<=r1_blk1;
   for(kc=0;kc<4;kc=kc+1)r2_hi[9*kc+:9]<=(r1_spar ? 9'(KMAX/128):9'd0)+{1'b0,r1_w[8+8*kc+:8]};
   r3_v<=r2_v;r3_w<=r2_w;r3_tag<=r2_tag;r3_pos<=r2_pos;r3_fam<=r2_fam;r3_lp<=r2_lp;r3_lo<=r2_lo;
   r3_spar<=r2_spar;r3_nq<=r2_nq;r3_umax<=r2_m23>r2_m01?r2_m23:r2_m01;
   r3_b0<=r2_b0;r3_b1<=r2_b1;r3_hi<=r2_hi;
   he<=r3_e;hv<=r3_v;
   p1_xs_v<=hv&&hw[0]&&!h_fam;p1_xb_v<=hv&&hw[0]&&h_fam;
   bt_xs_v<=p1_xs_v;bt_xb_v<=p1_xb_v;
   bt_go<=p1_go;bt_gobf<=p1_gobf;bt_cfg<=p1_cfg;bt_tag<=p1_tag;bt_ph<=p1_ph;bt_np<=p1_np;
  end
 end
endmodule
