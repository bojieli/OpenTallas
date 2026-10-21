// Opt-in; exact state transitions, SRAM queues, same-edge local output consumers.
module ot_s81pa_ctl #(
    parameter integer SEARCH_PIPE = 1,   // adopted 10-07 (selt_c cd3337221-b SS -541; bench selector/pipeline_r1)
    parameter integer DM   = 4,
    parameter integer PACE = 2,
    // CLAUDE s81-blocks 2026-10-07 (selt_c b6fcd9853 SS -308.9: qs/cq -> cnt, qs -> c_rem, qs -> lq): MRG_PIPE 1 =
    // the serving-tile select registered (ts_r, settles in the off-slot edge; needs PACE >= 2), each landing entry
    // carries its lane popcount (computed at the pin flop), the DONE count accumulates one edge after the take;
    // RQPIPE 1 = the control's tie quotas from registered prefix sums (+1 edge a segment); SLAT = extra slice status
    // latency (dsfd_selt_q PIPE2 tiles) added to the control's waits / holds
    parameter integer MRG_PIPE = 1,
    parameter integer RQPIPE = 1,
    parameter integer SLAT = 4,
    parameter integer XDX = 15                // extra control <-> quarter edges each way (QIO quarter tiles: 1)
) (
    input  wire [0:0]                ck,
    input wire[413-1:0]rst_profile,
    input  wire [4*`SELT_SB-1:0]     f_s,    // per quarter tile (lane 0 SW, 1 SE, 2 NW, 3 NE)
    output wire [4*`SELT_CB-1:0]     t_c,
    input  wire [4*`SELT_OB-1:0]     f_o,
    output wire [3:0]                t_cr,
    output wire [513:0]              vd,
    output wire [0:0]                vf
);
    localparam integer Q = 4, W = 16, IW = 20, K = 512, KW = 10, CB = 11, GW = CB + 4, SB = `SELT_SB, OB = `SELT_OB;
    localparam integer DW = OB - 1;          // landing entry {last, ninf, lv, idx}
    localparam integer CW = $clog2(DM + 1);
    wire[413-1:0]rst_local;
    generate for(genvar r=0;r<413;r=r+1)begin:g_rst
      ot_s81pa_rst_leaf #(.ID(r))u(.clk(ck[0]),.raw(rst_profile[r]),.q(rst_local[r]));
    end endgenerate
    wire rst_n=rst_local[0];
    // pin flops
    reg [Q*SB-1:0] sq; reg [Q*OB-1:0] oq;
    generate for(genvar c=0;c<(Q*SB+23)/24;c=c+1)begin:g_sq
      localparam integer LO=c*24,SW=(Q*SB-LO<24)?Q*SB-LO:24;
      always @(posedge ck[0] or negedge rst_local[1+c])
        if(!rst_local[1+c])sq[LO+:SW]<=0;else sq[LO+:SW]<=f_s[LO+:SW];
    end endgenerate
    always @(posedge ck[0]) oq <= f_o;
    // unpack
    wire [Q*16*GW-1:0] s_gc, s_gf; wire [Q*16*CB-1:0] s_bc, s_bf;
    wire [Q-1:0] s_last, s_hfin, s_stopped, s_done2, s_emitted, s_ovf, s_ready, s_acc, h_v, act;
    wire [Q*10-1:0] h_k; wire [Q*8-1:0] h_tag; wire [Q*2-1:0] act_q; wire [Q*3-1:0] lflt;
    genvar g;
    generate for (g = 0; g < Q; g = g + 1) begin : g_u
        wire [SB-1:0] x = sq[SB * g +: SB];
        assign s_gc[16*GW*g +: 16*GW] = x[239:0];
        assign s_gf[16*GW*g +: 16*GW] = x[479:240];
        assign s_bc[16*CB*g +: 16*CB] = x[655:480];
        assign s_bf[16*CB*g +: 16*CB] = x[831:656];
        assign {s_ovf[g], s_emitted[g], s_done2[g], s_stopped[g], s_hfin[g], s_last[g]} = x[837:832];
        assign s_ready[g] = x[838]; assign s_acc[g] = x[839]; assign h_v[g] = x[840];
        assign h_k[10*g +: 10] = x[850:841]; assign h_tag[8*g +: 8] = x[858:851];
        assign act[g] = x[859]; assign act_q[2*g +: 2] = x[861:860]; assign lflt[3*g +: 3] = x[864:862];
    end endgenerate
    // segment header state, faults
    reg        seg_open;
    reg [KW-1:0] seg_k, k_r;
    reg [7:0]  seg_tag;
    reg [4:0]  flt;
    reg        e_coll, e_kt, kld_r;
    reg [2*Q-1:0] qs;                        // the quarter each slice serves (from its lane's header)
    reg        coll_n;
    integer q, s;
    always @(*) begin
        coll_n = 1'b0;
        for (s = 0; s < Q; s = s + 1)
            for (q = s + 1; q < Q; q = q + 1)
                if (act[s] && act[q] && act_q[2*s +: 2] == act_q[2*q +: 2]) coll_n = 1'b1;
    end
    // ---- the select control (native, XD 2, PERM 1)
    wire [15:0] c_T, c_st; wire [7:0] c_Bt; wire [3:0] c_cg, c_fg;
    wire c_fclr, c_ing, c_stop, c_p2, c_p3, c_rep, c_hclr, rep_req, ovf, busy;
    wire [Q*(KW+1)-1:0] c_rem;
    ot_s81pa_sel_ctl #(.Q(Q),.K(K),.KW(KW),.CB(CB),.XD(2+XDX),.PERM(1),.RQPIPE(RQPIPE),.SLAT(SLAT))u_ctl(
      .clk(ck[0]),.rst_n_profile(rst_local[146+:33]),.k_in(k_r),.k_ld(kld_r),.qs(qs),
      .s_gc(s_gc),.s_gf(s_gf),.s_bc(s_bc),.s_bf(s_bf),.s_last(s_last),.s_hfin(s_hfin),.s_stopped(s_stopped),.s_done2(s_done2),.s_emitted(s_emitted),.s_ovf(s_ovf),
      .c_T(c_T),.c_Bt(c_Bt),.c_fclr(c_fclr),.c_cg(c_cg),.c_fg(c_fg),.c_ing(c_ing),.c_stop(c_stop),.c_p2(c_p2),.c_p3(c_p3),.c_rep(c_rep),.c_st(c_st),.c_rem(c_rem),.c_hclr(c_hclr),.rep_req(rep_req),.ovf(ovf),.busy(busy));
    // command bundles, one per tile, from flops at the pins
    reg [`SELT_CB-1:0] cmd [0:Q-1];
    wire[Q*`SELT_CB-1:0]cmd_next;
    generate for(g=0;g<Q;g=g+1)begin:g_c
      assign cmd_next[`SELT_CB*g+:`SELT_CB]={c_hclr,c_rem[(KW+1)*g+:KW+1],c_st,c_rep,c_p3,c_p2,c_stop,c_ing,c_fg,c_cg,c_fclr,c_Bt,c_T};
      for(genvar c=0;c<3;c=c+1)begin:g_chunk
        localparam integer LO=c*24,SW=(`SELT_CB-LO<24)?`SELT_CB-LO:24;
        always @(posedge ck[0] or negedge rst_local[179+g*3+c])
          if(!rst_local[179+g*3+c])cmd[g][LO+:SW]<=0;else cmd[g][LO+:SW]<=cmd_next[`SELT_CB*g+LO+:SW];
      end
      assign t_c[`SELT_CB*g+:`SELT_CB]=cmd[g];
    end endgenerate
    // ---- landing FIFOs (head at entry 0), credits
    function automatic [4:0] pop16(input [15:0] x);
        integer j; begin pop16 = 0; for (j = 0; j < 16; j = j + 1) pop16 = pop16 + x[j]; end
    endfunction
    wire[357:0]queue_head[0:3];wire[4*358-1:0]heads;
    wire[2:0]lc[0:3];wire[11:0]lc_next;
    reg[Q-1:0]lpop;wire[Q-1:0]lv;
    generate for(g=0;g<Q;g=g+1)begin:g_l
      assign lv[g]=(lc[g]!=0);
      assign lc_next[g*3+:3]=lc[g]+3'(oq[OB*g])-3'(lpop[g]);
      ot_s81pa_queue u_q(.clk(ck[0]),.rst_n(rst_local[191+23*g+:23]),.push(oq[OB*g]),.pop(lpop[g]),
        .data({pop16(oq[OB*g+1+320+:16]),oq[OB*g+1+:DW]}),.head(queue_head[g]),.count(lc[g]));
      assign heads[358*g+:358]=queue_head[g];
    end endgenerate
    reg [Q-1:0] crq;
    always @(posedge ck[0] or negedge rst_local[283]) if (!rst_local[283]) crq <= {Q{1'b0}}; else crq <= lpop;
    assign t_cr = crq;
    // ---- output merger: quarter cq is served by the tile whose lane header named it
    reg        ovf_seen;
    reg  [1:0] rep_pend;
    reg        rep_n;
    reg  [1:0] cq;
    reg        done_pend;
    reg  [9:0] cnt;
    reg  [4:0] cnt_add;                      // MRG_PIPE: the last take's lane count, added on the next edge
    reg  [4:0] flt_rep;
    reg  [$clog2(PACE+1)-1:0] pc;
    wire       slot = (pc == 0);
    wire [4:0] flt_new = flt & ~flt_rep;
    reg  [1:0] ts;                           // the tile serving quarter cq
    always @(*) begin
        ts = cq;
`ifndef OT_S81PH_MUT2
        for (s = 0; s < Q; s = s + 1) if (qs[2*s +: 2] == cq) ts = s[1:0];
`endif
    end
    reg  [1:0] ts_r;
    always @(posedge ck[0]) ts_r <= ts;
    wire [1:0] ts_u = (MRG_PIPE != 0) ? ts_r : ts;
`ifdef OT_S81PH_MUT3
    wire [1:0] tsel = ts_u ^ 2'd1;
`else
    wire [1:0] tsel = ts_u;
`endif
    wire [DW-1:0] hd = queue_head[tsel][0+:DW];
    wire take = slot && !(|flt_new) && rep_pend == 0 && !done_pend && lv[tsel];
    always @(*) begin lpop = {Q{1'b0}}; if (take) lpop[tsel] = 1'b1; end
    wire hd_last = hd[DW-1];
    wire [15:0] hd_ninf = hd[DW-2 -: 16];
    wire [15:0] hd_lv = hd[335:320];
    wire [319:0] hd_idx = hd[319:0];
    reg        o_v;
    wire [511:0] o_d;
    reg[0:0]seg_open_d;
    reg[9:0]seg_k_d;
    reg[7:0]seg_tag_d;
    reg[4:0]flt_d;
    reg[0:0]e_coll_d;
    reg[0:0]e_kt_d;
    reg[9:0]k_r_d;
    reg[0:0]kld_r_d;
    reg[7:0]qs_d;
    reg[0:0]ovf_seen_d;
    reg[1:0]rep_pend_d;
    reg[0:0]rep_n_d;
    reg[1:0]cq_d;
    reg[0:0]done_pend_d;
    reg[9:0]cnt_d;
    reg[4:0]cnt_add_d;
    reg[4:0]flt_rep_d;
    reg[1:0]pc_d;
    reg[0:0]o_v_d;
    always @* begin
      seg_open_d=seg_open;
      seg_k_d=seg_k;
      seg_tag_d=seg_tag;
      flt_d=flt;
      e_coll_d=e_coll;
      e_kt_d=e_kt;
      k_r_d=k_r;
      kld_r_d=kld_r;
      qs_d=qs;
      ovf_seen_d=ovf_seen;
      rep_pend_d=rep_pend;
      rep_n_d=rep_n;
      cq_d=cq;
      done_pend_d=done_pend;
      cnt_d=cnt;
      cnt_add_d=cnt_add;
      flt_rep_d=flt_rep;
      pc_d=pc;
      o_v_d=o_v;
            kld_r_d = |s_acc;
            if (|s_acc) k_r_d = seg_k;
            e_coll_d = coll_n;
            for (s = 0; s < Q; s = s + 1) if (h_v[s]) qs_d[2*s +: 2] = act_q[2*s +: 2];
            e_kt_d = 1'b0;
            begin : hdr
                integer t; reg op; reg [KW-1:0] kk; reg [7:0] tt;
                op = seg_open; kk = seg_k; tt = seg_tag;
                for (t = 0; t < Q; t = t + 1)
                    if (h_v[t]) begin
                        if (!op) begin op = 1'b1; kk = h_k[10*t +: 10]; tt = h_tag[8*t +: 8]; end
                        else if (h_k[10*t +: 10] != kk || h_tag[8*t +: 8] != tt) e_kt_d = 1'b1;
                    end
                seg_open_d = op; seg_k_d = kk; seg_tag_d = tt;
            end
            begin : fl
                reg [2:0] lf; lf = lflt[2:0] | lflt[5:3] | lflt[8:6] | lflt[11:9];
                flt_d = flt | {1'b0, lf[2], e_kt, lf[1] | e_coll, lf[0]};
            end
            if (ovf) ovf_seen_d = 1'b1;
            pc_d = (pc == PACE - 1) ? 0 : pc + 1'b1;
            o_v_d = 1'b0;
            if (MRG_PIPE != 0) begin cnt_d = cnt + {5'd0, cnt_add}; cnt_add_d = 5'd0; end
            if (rep_req) rep_pend_d = rep_pend + 1'b1;
            if (slot) begin
                if (|flt_new) begin
                    o_v_d = 1'b1;
                    flt_rep_d = flt;
                end else if (rep_pend != 0 && &s_ready) begin
                    o_v_d = 1'b1;
                    rep_n_d = ~rep_n;
                    rep_pend_d = rep_pend - 1'b1 + (rep_req ? 1'b1 : 1'b0);
                end else if (take) begin
                    o_v_d = 1'b1;

                    if (MRG_PIPE != 0) cnt_add_d = queue_head[tsel][DW+:5];
                    else cnt_d = cnt + pop16(hd_lv);
                    if (hd_last) begin
                        cq_d = cq + 1'b1;
                        if (cq == 2'd3) done_pend_d = 1'b1;
                    end
                end else if (done_pend && &s_ready) begin
                    o_v_d = 1'b1;
                    done_pend_d = 1'b0; cnt_d = 10'd0; ovf_seen_d = 1'b0; seg_open_d = 1'b0; rep_n_d = 1'b0;
                end
            end
    end
    // [ELEM-BKG] seg_tag header chain from kept same-edge copies of h_v (pin-flop bit x[840]: same D, same reset leaf)
    // and seg_open (same D seg_open_d, same leaf), halving the header-select fanout; identical first-valid rule.
    wire[Q-1:0]h_v_t;wire seg_open_t;
    generate for(genvar g2=0;g2<Q;g2=g2+1)begin:g_hvt
      localparam integer HB=SB*g2+840;
      ot_s81pa_rcopy #(.W(1),.INIT(1'b0),.ID(16384+g2))u_h(.clk(ck[0]),.rst_n(rst_local[1+HB/24]),.d(f_s[HB]),.q(h_v_t[g2]));
    end endgenerate
    ot_s81pa_rcopy #(.W(1),.INIT(1'b0),.ID(16400))u_so(.clk(ck[0]),.rst_n(rst_local[284]),.d(seg_open_d),.q(seg_open_t));
    reg[7:0]seg_tag_t;
    always @* begin : hdr_t
      integer t2; reg op2; op2=seg_open_t; seg_tag_t=seg_tag;
      for(t2=0;t2<Q;t2=t2+1) if(h_v_t[t2]&&!op2) begin op2=1'b1; seg_tag_t=h_tag[8*t2+:8]; end
    end
    localparam[0:0]N32_INIT_seg_open=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_seg_open
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge ck[0] or negedge rst_local[284+c])
        if(!rst_local[284+c])seg_open<=N32_INIT_seg_open;
        else seg_open<=seg_open_d;
    end endgenerate
    localparam[9:0]N32_INIT_seg_k={KW{1'b0}};
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_seg_k
      localparam integer LO=c*16,SW=(10-LO<16)?10-LO:16;
      always @(posedge ck[0] or negedge rst_local[285+c])
        if(!rst_local[285+c])seg_k[LO+:SW]<=N32_INIT_seg_k[LO+:SW];
        else seg_k[LO+:SW]<=seg_k_d[LO+:SW];
    end endgenerate
    localparam[7:0]N32_INIT_seg_tag=8'd0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_seg_tag
      localparam integer LO=c*16,SW=(8-LO<16)?8-LO:16;
      always @(posedge ck[0] or negedge rst_local[286+c])
        if(!rst_local[286+c])seg_tag[LO+:SW]<=N32_INIT_seg_tag[LO+:SW];
        else seg_tag[LO+:SW]<=seg_tag_t[LO+:SW];
    end endgenerate
    localparam[4:0]N32_INIT_flt=5'd0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_flt
      localparam integer LO=c*16,SW=(5-LO<16)?5-LO:16;
      always @(posedge ck[0] or negedge rst_local[287+c])
        if(!rst_local[287+c])flt[LO+:SW]<=N32_INIT_flt[LO+:SW];
        else flt[LO+:SW]<=flt_d[LO+:SW];
    end endgenerate
    localparam[0:0]N32_INIT_e_coll=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_e_coll
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge ck[0] or negedge rst_local[288+c])
        if(!rst_local[288+c])e_coll<=N32_INIT_e_coll;
        else e_coll<=e_coll_d;
    end endgenerate
    localparam[0:0]N32_INIT_e_kt=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_e_kt
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge ck[0] or negedge rst_local[289+c])
        if(!rst_local[289+c])e_kt<=N32_INIT_e_kt;
        else e_kt<=e_kt_d;
    end endgenerate
    localparam[9:0]N32_INIT_k_r={KW{1'b0}};
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_k_r
      localparam integer LO=c*16,SW=(10-LO<16)?10-LO:16;
      always @(posedge ck[0] or negedge rst_local[290+c])
        if(!rst_local[290+c])k_r[LO+:SW]<=N32_INIT_k_r[LO+:SW];
        else k_r[LO+:SW]<=k_r_d[LO+:SW];
    end endgenerate
    localparam[0:0]N32_INIT_kld_r=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_kld_r
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge ck[0] or negedge rst_local[291+c])
        if(!rst_local[291+c])kld_r<=N32_INIT_kld_r;
        else kld_r<=kld_r_d;
    end endgenerate
    localparam[7:0]N32_INIT_qs={2'd3, 2'd2, 2'd1, 2'd0};
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_qs
      localparam integer LO=c*16,SW=(8-LO<16)?8-LO:16;
      always @(posedge ck[0] or negedge rst_local[292+c])
        if(!rst_local[292+c])qs[LO+:SW]<=N32_INIT_qs[LO+:SW];
        else qs[LO+:SW]<=qs_d[LO+:SW];
    end endgenerate
    localparam[0:0]N32_INIT_ovf_seen=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_ovf_seen
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge ck[0] or negedge rst_local[293+c])
        if(!rst_local[293+c])ovf_seen<=N32_INIT_ovf_seen;
        else ovf_seen<=ovf_seen_d;
    end endgenerate
    localparam[1:0]N32_INIT_rep_pend=2'd0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_rep_pend
      localparam integer LO=c*16,SW=(2-LO<16)?2-LO:16;
      always @(posedge ck[0] or negedge rst_local[294+c])
        if(!rst_local[294+c])rep_pend[LO+:SW]<=N32_INIT_rep_pend[LO+:SW];
        else rep_pend[LO+:SW]<=rep_pend_d[LO+:SW];
    end endgenerate
    localparam[0:0]N32_INIT_rep_n=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_rep_n
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge ck[0] or negedge rst_local[295+c])
        if(!rst_local[295+c])rep_n<=N32_INIT_rep_n;
        else rep_n<=rep_n_d;
    end endgenerate
    localparam[1:0]N32_INIT_cq=2'd0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_cq
      localparam integer LO=c*16,SW=(2-LO<16)?2-LO:16;
      always @(posedge ck[0] or negedge rst_local[296+c])
        if(!rst_local[296+c])cq[LO+:SW]<=N32_INIT_cq[LO+:SW];
        else cq[LO+:SW]<=cq_d[LO+:SW];
    end endgenerate
    localparam[0:0]N32_INIT_done_pend=1'b1;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_done_pend
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge ck[0] or negedge rst_local[297+c])
        if(!rst_local[297+c])done_pend<=N32_INIT_done_pend;
        else done_pend<=done_pend_d;
    end endgenerate
    localparam[9:0]N32_INIT_cnt=10'd0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_cnt
      localparam integer LO=c*16,SW=(10-LO<16)?10-LO:16;
      always @(posedge ck[0] or negedge rst_local[298+c])
        if(!rst_local[298+c])cnt[LO+:SW]<=N32_INIT_cnt[LO+:SW];
        else cnt[LO+:SW]<=cnt_d[LO+:SW];
    end endgenerate
    localparam[4:0]N32_INIT_cnt_add=5'd0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_cnt_add
      localparam integer LO=c*16,SW=(5-LO<16)?5-LO:16;
      always @(posedge ck[0] or negedge rst_local[299+c])
        if(!rst_local[299+c])cnt_add[LO+:SW]<=N32_INIT_cnt_add[LO+:SW];
        else cnt_add[LO+:SW]<=cnt_add_d[LO+:SW];
    end endgenerate
    localparam[4:0]N32_INIT_flt_rep=5'd0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_flt_rep
      localparam integer LO=c*16,SW=(5-LO<16)?5-LO:16;
      always @(posedge ck[0] or negedge rst_local[300+c])
        if(!rst_local[300+c])flt_rep[LO+:SW]<=N32_INIT_flt_rep[LO+:SW];
        else flt_rep[LO+:SW]<=flt_rep_d[LO+:SW];
    end endgenerate
    localparam[1:0]N32_INIT_pc=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_pc
      localparam integer LO=c*16,SW=(2-LO<16)?2-LO:16;
      always @(posedge ck[0] or negedge rst_local[301+c])
        if(!rst_local[301+c])pc[LO+:SW]<=N32_INIT_pc[LO+:SW];
        else pc[LO+:SW]<=pc_d[LO+:SW];
    end endgenerate
    localparam[0:0]N32_INIT_o_v=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_o_v
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge ck[0] or negedge rst_local[302+c])
        if(!rst_local[302+c])o_v<=N32_INIT_o_v;
        else o_v<=o_v_d;
    end endgenerate
    wire[52:0]packet_next={{f_s[3*SB+838],f_s[2*SB+838],f_s[SB+838],f_s[838]},lc_next,seg_tag_t,flt_d,flt_rep_d,rep_pend_d,done_pend_d,pc_d,rep_n_d,cq_d,cnt_d,ovf_seen_d};
    // [ELEM-BKG] packet selector_next = ts from kept per-3-packet copies of the ts cone (same qs/cq registers, same
    // expression; was one 2-bit net into 22 packets x 8 tsel copies = 177 loads)
    wire[15:0]ts_k;
    // [ELEM-BKG] the ts cones read kept same-edge copies of qs/cq (D=qs_d/cq_d, same reset value and leaf), one set per two cones
    wire[31:0]qs_k;wire[7:0]cq_k;
    generate for(genvar j=0;j<4;j=j+1)begin:g_qsk
      ot_s81pa_rcopy #(.W(8),.INIT(8'b11100100),.ID(16416+j))u_qs(.clk(ck[0]),.rst_n(rst_local[(j<2)?292:296]),.d(qs_d),.q(qs_k[8*j+:8]));
      ot_s81pa_rcopy #(.W(2),.INIT(2'd0),.ID(16424+j))u_cq(.clk(ck[0]),.rst_n(rst_local[296]),.d(cq_d),.q(cq_k[2*j+:2]));
    end endgenerate
    generate for(genvar c=0;c<22;c=c+1)begin:g_packet
      localparam integer LO=c*24,SW=(512-LO<24)?512-LO:24;
      if(c%3==0)begin:g_tsn
        ot_s81pa_tsnext #(.ID(c/3))u_tsn(.qs(qs_k[8*(c/6)+:8]),.cq(cq_k[2*(c/6)+:2]),.ts(ts_k[2*(c/3)+:2]));
      end
      ot_s81pa_packet #(.LO(LO),.SW(SW),.ID(c))u(.clk(ck[0]),.rst_n(rst_local[303+5*c+:5]),.state_next(packet_next),.selector_next(ts_k[2*(c/3)+:2]),.heads(heads),.out(o_d[LO+:SW]));
    end endgenerate
    initial if(SEARCH_PIPE!=1||DM!=4||PACE!=2||MRG_PIPE!=1||RQPIPE!=1||SLAT!=4||XDX!=15)$fatal(1,"fixed selected n32 outer shape");
`ifndef SYNTHESIS
    initial if (MRG_PIPE != 0 && PACE < 2) $fatal(1, "dsfd_selt_c: MRG_PIPE needs PACE >= 2");
`endif
    reg [513:0] vd_q;
    always @(posedge ck[0]) vd_q <= {o_d, o_v & rst_n, rst_n};
    assign vd = vd_q;
    ot_fwd_clk_inv u_vf (.a(ck[0]), .y(vf[0]));
endmodule

// [ELEM-BKG] kept copy of the serving-quarter cone (identical to ot_s81pa_ctl ts); one per three packets
(* keep_hierarchy="yes" *)
module ot_s81pa_tsnext #(parameter integer ID=0)(input wire[7:0]qs,input wire[1:0]cq,output reg[1:0]ts);
 integer s;
 always @(*) begin
  ts=cq;
`ifndef OT_S81PH_MUT2
  for(s=0;s<4;s=s+1) if(qs[2*s+:2]==cq) ts=s[1:0];
`endif
 end
endmodule
