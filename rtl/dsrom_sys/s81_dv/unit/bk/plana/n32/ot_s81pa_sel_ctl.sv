// Opt-in; generated from exact selected pipeline state transitions.
module ot_s81pa_sel_ctl #(
    parameter integer Q  = 4,
    parameter integer K  = 512,
    parameter integer KW = $clog2(K + 1),
    parameter integer CB = KW + 1,
    // CLAUDE S81-PH tiles (defaults = the native unit): XD extra edges each way between the control and the slices
    // (the waits and holdoffs grow by the round trip), PERM 1: slice i serves quarter qs[2i +: 2] (tie quotas in
    // quarter order)
    parameter integer XD   = 0,
    parameter integer PERM = 0,
    parameter integer RQPIPE = 0,                   // 1: tie quotas from registered prefix sums (C_R2, +1 edge)
    parameter integer SLAT = 0                      // extra edges of slice status latency (waits / holds only)
) (
    input  wire                    clk,
    input wire[32:0]rst_n_profile,
    input  wire [KW-1:0]           k_in,
    input  wire                    k_ld,
    input  wire [2*Q-1:0]          qs,
    input  wire [Q*16*(CB+4)-1:0]  s_gc,
    input  wire [Q*16*(CB+4)-1:0]  s_gf,
    input  wire [Q*16*CB-1:0]      s_bc,
    input  wire [Q*16*CB-1:0]      s_bf,
    input  wire [Q-1:0]            s_last,
    input  wire [Q-1:0]            s_hfin,
    input  wire [Q-1:0]            s_stopped,
    input  wire [Q-1:0]            s_done2,
    input  wire [Q-1:0]            s_emitted,
    input  wire [Q-1:0]            s_ovf,
    output reg  [15:0]             c_T,
    output reg  [7:0]              c_Bt,
    output reg                     c_fclr,
    output wire [3:0]              c_cg,
    output wire [3:0]              c_fg,
    output reg                     c_ing,
    output reg                     c_stop,
    output reg                     c_p2,
    output reg                     c_p3,
    output reg                     c_rep,
    output reg  [15:0]             c_st,
    output reg  [Q*(KW+1)-1:0]     c_rem,
    output reg                     c_hclr,
    output reg                     rep_req,
    output reg                     ovf,
    output wire                    busy
);
    localparam integer XW   = CB + 10;              // search sums
    localparam integer QC   = KW + 1;               // coarse quota width
    localparam integer XR   = 2 * XD;               // round trip added by the tile hops
    localparam integer WAIT = 20 + XR + SLAT;       // search latency after the counts settle
    localparam integer HOLD = 40 + 2 * XR + 2 * SLAT; // fine results ignored after a bucket change
    localparam integer HC0  = 27 + 2 * XR + 2 * SLAT, HF0 = 50 + 2 * XR + 2 * SLAT, CLRW = 27 + 2 * XR + 2 * SLAT;
    localparam integer TW   = (XD == 0 && SLAT == 0) ? 6 : 8;    // wait / hold counter width
    localparam integer KI   = K;
    localparam [QC-1:0] KQ  = KI[QC-1:0];
    localparam [XW-1:0] QINV = {XW{1'b1}};          // a quota no count reaches
    localparam [2:0] C_ING = 3'd0, C_FL = 3'd1, C_P2 = 3'd2, C_W2 = 3'd3, C_R = 3'd4, C_P3 = 3'd5, C_CLR = 3'd6, C_R2 = 3'd7;

    wire rst_n=rst_n_profile[0]; // status group only,24 FF
    // status inputs, registered
    reg [Q-1:0] st_last, st_hfin, st_stopped, st_done2, st_emitted, st_ovf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin st_last <= 0; st_hfin <= 0; st_stopped <= 0; st_done2 <= 0; st_emitted <= 0; st_ovf <= 0; end
        else begin
            st_last <= s_last; st_hfin <= s_hfin; st_stopped <= s_stopped; st_done2 <= s_done2;
            st_emitted <= s_emitted; st_ovf <= s_ovf;
        end
    end

    // the two searches
    reg  [QC-1:0] kq;
    reg  [XW-1:0] qf;
    wire [7:0]    cres_b, fres_b;
    wire [XW-1:0] cres_above, fres_above;
    wire          cres_ok, fres_ok;
    wire [Q*CB-1:0] cres_eq, fres_eq;
    ot_s81pa_sel_su #(.Q(Q), .CB(CB), .QW(QC), .XR(XR)) u_cs (
        .clk(clk), .gs(s_gc), .bs(s_bc), .q(kq), .g_out(c_cg),
        .res_b(cres_b), .res_above(cres_above), .res_ok(cres_ok), .res_eq(cres_eq));
    ot_s81pa_sel_su #(.Q(Q), .CB(CB), .QW(XW), .XR(XR)) u_fs (
        .clk(clk), .gs(s_gf), .bs(s_bf), .q(qf), .g_out(c_fg),
        .res_b(fres_b), .res_above(fres_above), .res_ok(fres_ok), .res_eq(fres_eq));

    reg  [2:0]    st;
    reg  [TW-1:0] wcnt, hold_c, hold_f;
    reg           kseen, hf_seen, bs_done;
    reg  [7:0]    bs, ls;
    reg  [QC-1:0] m, t;
    reg  [Q*CB-1:0] eq;
`ifdef S81PH_MUT_THRESHOLD
    wire [15:0] tc = 16'hffff;
`else
    wire [15:0] tc = {cres_b, 8'h00};
`endif
    wire [15:0]   tf = {c_Bt, fres_b};
    wire [QC-1:0] kin_c = ({1'b0, k_in} > KQ) ? KQ : {1'b0, k_in};
    wire [XW-1:0] cab = cres_above;

    // tie quotas: t_q = max(0, t - ties in quarters below q)
    reg  [Q*QC-1:0] rem_d;
    reg  [CB+2:0]   pre;
    integer i;
    integer j;
    // RQPIPE: the prefix sums of the tie counts, registered in C_R (rem_r from them in C_R2)
    reg  [Q*(CB+3)-1:0] pre_d, pre_r;
    reg  [Q*QC-1:0]     rem_r;
    reg  [CB+2:0]       prq;
    integer ri, rj;
    always @(*) begin
        for (ri = 0; ri < Q; ri = ri + 1) begin
            prq = 0;
            for (rj = 0; rj < Q; rj = rj + 1)
                if ((PERM == 0) ? (rj < ri) : (qs[2*rj +: 2] < qs[2*ri +: 2])) prq = prq + {3'b000, eq[CB*rj +: CB]};
            pre_d[(CB+3)*ri +: CB+3] = prq;
        end
        for (ri = 0; ri < Q; ri = ri + 1)
            rem_r[QC*ri +: QC] = ({{(CB+3-QC){1'b0}}, t} > pre_r[(CB+3)*ri +: CB+3]) ? t - pre_r[(CB+3)*ri +: QC] : {QC{1'b0}};
    end
    always @(posedge clk) pre_r <= pre_d;
    generate if (PERM == 0) begin : g_rq
        always @(*) begin
            pre = 0;
            for (i = 0; i < Q; i = i + 1) begin
                rem_d[QC*i +: QC] = ({{(CB+3-QC){1'b0}}, t} > pre) ? t - pre[QC-1:0] : {QC{1'b0}};
                pre = pre + {3'b000, eq[CB*i +: CB]};
            end
        end
    end else begin : g_rqp
        // ties of the slices serving lower quarters
        always @(*) begin
            for (i = 0; i < Q; i = i + 1) begin
                pre = 0;
                for (j = 0; j < Q; j = j + 1)
                    if (qs[2*j +: 2] < qs[2*i +: 2]) pre = pre + {3'b000, eq[CB*j +: CB]};
                rem_d[QC*i +: QC] = ({{(CB+3-QC){1'b0}}, t} > pre) ? t - pre[QC-1:0] : {QC{1'b0}};
            end
        end
    end endgenerate

    // [ELEM-BKG] 20 same-edge next-state copies, one per register chunk group; copy0 = original st + 1-bit flags
    localparam integer NXK=20, NXW=237;
    wire[NXK*NXW-1:0]nx_bus;
    wire[3*NXK-1:0]st_k;
    assign st_k[2:0]=st;
    generate for(genvar k=0;k<NXK;k=k+1)begin:g_nx
    wire[2:0]stc=st_k[3*k+:3];
    wire          use_c = (stc == C_ING) && kseen && (hold_c == 0) && cres_ok;
    wire          use_f = (stc == C_ING) && kseen && (hold_c == 0) && (hold_f == 0) && fres_ok;
    reg[2:0]st_d;
    reg[7:0]wcnt_d;
    reg[7:0]hold_c_d;
    reg[7:0]hold_f_d;
    reg[0:0]kseen_d;
    reg[0:0]hf_seen_d;
    reg[0:0]bs_done_d;
    reg[7:0]bs_d;
    reg[7:0]ls_d;
    reg[10:0]m_d;
    reg[10:0]t_d;
    reg[43:0]eq_d;
    reg[15:0]c_T_d;
    reg[7:0]c_Bt_d;
    reg[0:0]c_fclr_d;
    reg[0:0]c_ing_d;
    reg[0:0]c_stop_d;
    reg[0:0]c_p2_d;
    reg[0:0]c_p3_d;
    reg[0:0]c_rep_d;
    reg[15:0]c_st_d;
    reg[43:0]c_rem_d;
    reg[0:0]c_hclr_d;
    reg[0:0]rep_req_d;
    reg[0:0]ovf_d;
    reg[10:0]kq_d;
    reg[20:0]qf_d;
    always @* begin
      st_d=stc;
      wcnt_d=wcnt;
      hold_c_d=hold_c;
      hold_f_d=hold_f;
      kseen_d=kseen;
      hf_seen_d=hf_seen;
      bs_done_d=bs_done;
      bs_d=bs;
      ls_d=ls;
      m_d=m;
      t_d=t;
      eq_d=eq;
      c_T_d=c_T;
      c_Bt_d=c_Bt;
      c_fclr_d=c_fclr;
      c_ing_d=c_ing;
      c_stop_d=c_stop;
      c_p2_d=c_p2;
      c_p3_d=c_p3;
      c_rep_d=c_rep;
      c_st_d=c_st;
      c_rem_d=c_rem;
      c_hclr_d=c_hclr;
      rep_req_d=rep_req;
      ovf_d=ovf;
      kq_d=kq;
      qf_d=qf;
            c_fclr_d = 1'b0; c_p2_d = 1'b0; c_p3_d = 1'b0; c_hclr_d = 1'b0; rep_req_d = 1'b0;
            if (hold_c != 0) hold_c_d = hold_c - 1'b1;
            if (hold_f != 0) hold_f_d = hold_f - 1'b1;
            if (wcnt != 0) wcnt_d = wcnt - 1'b1;
            case (stc)
                C_ING: begin
                    if (k_ld && !kseen) begin
                        kseen_d = 1'b1; kq_d = kin_c; hold_c_d = HC0[TW-1:0]; hold_f_d = HF0[TW-1:0];
                    end
                    // the running bound
                    if (use_c) begin
                        if (cres_b > c_Bt) begin
                            c_Bt_d = cres_b; c_fclr_d = 1'b1; hold_f_d = HOLD[TW-1:0]; qf_d = QINV;
                        end else if (cres_b == c_Bt)
                            qf_d = {{(XW-QC){1'b0}}, kq} - cab;
                    end
                    if (use_c && use_f)          c_T_d = (tc > c_T) ? ((tc > tf) ? tc : tf) : ((tf > c_T) ? tf : c_T);
                    else if (use_c && tc > c_T)  c_T_d = tc;
                    else if (use_f && tf > c_T)  c_T_d = tf;
                    if (&st_last) begin st_d = C_FL; c_ing_d = 1'b0; c_stop_d = 1'b1; hf_seen_d = 1'b0; bs_done_d = 1'b0; end
                end
                C_FL: begin
                    if ((&st_hfin) && !hf_seen) begin hf_seen_d = 1'b1; wcnt_d = WAIT[TW-1:0]; end
                    if (hf_seen && wcnt == 0 && !bs_done) begin
                        bs_done_d = 1'b1; bs_d = cres_b; m_d = kq - cab[QC-1:0];
                    end
                    if (bs_done && (&st_stopped)) begin
                        st_d = C_P2; c_rep_d = |st_ovf; ovf_d = |st_ovf; rep_req_d = |st_ovf;
`ifdef S81PH_MUT_REPLAY
                        rep_req_d = 1'b0;
`endif
                        c_st_d = {bs, 8'h00}; c_p2_d = 1'b1; qf_d = {{(XW-QC){1'b0}}, m};
                    end
                end
                C_P2: begin
                    if (&st_done2) begin st_d = C_W2; wcnt_d = WAIT[TW-1:0] + 1'b1; end   // + res_eq's edge
                end
                C_W2: begin
                    if (wcnt == 0) begin
                        st_d = C_R; ls_d = fres_b; t_d = m - fres_above[QC-1:0]; eq_d = fres_eq;
                    end
                end
                C_R: begin
                    if (RQPIPE != 0) st_d = C_R2;     // pre_r captures the prefix sums on this edge
                    else begin st_d = C_P3; c_rem_d = rem_d; c_st_d = {bs, ls}; c_p3_d = 1'b1; rep_req_d = c_rep; end
                end
                C_R2: begin
                    st_d = C_P3; c_rem_d = rem_r; c_st_d = {bs, ls}; c_p3_d = 1'b1; rep_req_d = c_rep;
                end
                C_P3: begin
                    if (&st_emitted) begin st_d = C_CLR; c_hclr_d = 1'b1; wcnt_d = CLRW[TW-1:0]; end
                end
                default: begin                     // C_CLR: the slices clear; stale search results drain
                    c_T_d = 0; c_Bt_d = 0; qf_d = QINV; kseen_d = 1'b0; c_rep_d = 1'b0; c_stop_d = 1'b0; ovf_d = 1'b0;
                    if (wcnt == 0) begin st_d = C_ING; c_ing_d = 1'b1; end
                end
            endcase
    end
    assign nx_bus[NXW*k+:NXW]={qf_d,kq_d,ovf_d,rep_req_d,c_hclr_d,c_rem_d,c_st_d,c_rep_d,c_p3_d,c_p2_d,c_stop_d,c_ing_d,c_fclr_d,c_Bt_d,c_T_d,eq_d,t_d,m_d,ls_d,bs_d,bs_done_d,hf_seen_d,kseen_d,hold_f_d,hold_c_d,wcnt_d,st_d};
    end endgenerate
    localparam[2:0]N32_INIT_st=C_CLR;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_st
      localparam integer LO=c*16,SW=(3-LO<16)?3-LO:16;
      always @(posedge clk or negedge rst_n_profile[1+c])
        if(!rst_n_profile[1+c])st[LO+:SW]<=N32_INIT_st[LO+:SW];
        else st[LO+:SW]<=nx_bus[NXW*(0+c*0)+0+LO+:SW];
    end endgenerate
    localparam[7:0]N32_INIT_wcnt=CLRW[TW-1:0];
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_wcnt
      localparam integer LO=c*16,SW=(8-LO<16)?8-LO:16;
      always @(posedge clk or negedge rst_n_profile[2+c])
        if(!rst_n_profile[2+c])wcnt[LO+:SW]<=N32_INIT_wcnt[LO+:SW];
        else wcnt[LO+:SW]<=nx_bus[NXW*(1+c*1)+3+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(1+c))u_stk(.clk(clk),.rst_n(rst_n_profile[2+c]),.d(nx_bus[0+:3]),.q(st_k[3*(1+c)+:3]));
    end endgenerate
    localparam[7:0]N32_INIT_hold_c=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_hold_c
      localparam integer LO=c*16,SW=(8-LO<16)?8-LO:16;
      always @(posedge clk or negedge rst_n_profile[3+c])
        if(!rst_n_profile[3+c])hold_c[LO+:SW]<=N32_INIT_hold_c[LO+:SW];
        else hold_c[LO+:SW]<=nx_bus[NXW*(2+c*1)+11+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(2+c))u_stk(.clk(clk),.rst_n(rst_n_profile[3+c]),.d(nx_bus[0+:3]),.q(st_k[3*(2+c)+:3]));
    end endgenerate
    localparam[7:0]N32_INIT_hold_f=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_hold_f
      localparam integer LO=c*16,SW=(8-LO<16)?8-LO:16;
      always @(posedge clk or negedge rst_n_profile[4+c])
        if(!rst_n_profile[4+c])hold_f[LO+:SW]<=N32_INIT_hold_f[LO+:SW];
        else hold_f[LO+:SW]<=nx_bus[NXW*(3+c*1)+19+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(3+c))u_stk(.clk(clk),.rst_n(rst_n_profile[4+c]),.d(nx_bus[0+:3]),.q(st_k[3*(3+c)+:3]));
    end endgenerate
    localparam[0:0]N32_INIT_kseen=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_kseen
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[5+c])
        if(!rst_n_profile[5+c])kseen<=N32_INIT_kseen;
        else kseen<=nx_bus[NXW*(0+c*0)+27];
    end endgenerate
    localparam[0:0]N32_INIT_hf_seen=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_hf_seen
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[6+c])
        if(!rst_n_profile[6+c])hf_seen<=N32_INIT_hf_seen;
        else hf_seen<=nx_bus[NXW*(0+c*0)+28];
    end endgenerate
    localparam[0:0]N32_INIT_bs_done=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_bs_done
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[7+c])
        if(!rst_n_profile[7+c])bs_done<=N32_INIT_bs_done;
        else bs_done<=nx_bus[NXW*(0+c*0)+29];
    end endgenerate
    localparam[7:0]N32_INIT_bs=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_bs
      localparam integer LO=c*16,SW=(8-LO<16)?8-LO:16;
      always @(posedge clk or negedge rst_n_profile[8+c])
        if(!rst_n_profile[8+c])bs[LO+:SW]<=N32_INIT_bs[LO+:SW];
        else bs[LO+:SW]<=nx_bus[NXW*(4+c*1)+30+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(4+c))u_stk(.clk(clk),.rst_n(rst_n_profile[8+c]),.d(nx_bus[0+:3]),.q(st_k[3*(4+c)+:3]));
    end endgenerate
    localparam[7:0]N32_INIT_ls=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_ls
      localparam integer LO=c*16,SW=(8-LO<16)?8-LO:16;
      always @(posedge clk or negedge rst_n_profile[9+c])
        if(!rst_n_profile[9+c])ls[LO+:SW]<=N32_INIT_ls[LO+:SW];
        else ls[LO+:SW]<=nx_bus[NXW*(5+c*1)+38+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(5+c))u_stk(.clk(clk),.rst_n(rst_n_profile[9+c]),.d(nx_bus[0+:3]),.q(st_k[3*(5+c)+:3]));
    end endgenerate
    localparam[10:0]N32_INIT_m=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_m
      localparam integer LO=c*16,SW=(11-LO<16)?11-LO:16;
      always @(posedge clk or negedge rst_n_profile[10+c])
        if(!rst_n_profile[10+c])m[LO+:SW]<=N32_INIT_m[LO+:SW];
        else m[LO+:SW]<=nx_bus[NXW*(6+c*1)+46+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(6+c))u_stk(.clk(clk),.rst_n(rst_n_profile[10+c]),.d(nx_bus[0+:3]),.q(st_k[3*(6+c)+:3]));
    end endgenerate
    localparam[10:0]N32_INIT_t=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_t
      localparam integer LO=c*16,SW=(11-LO<16)?11-LO:16;
      always @(posedge clk or negedge rst_n_profile[11+c])
        if(!rst_n_profile[11+c])t[LO+:SW]<=N32_INIT_t[LO+:SW];
        else t[LO+:SW]<=nx_bus[NXW*(7+c*1)+57+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(7+c))u_stk(.clk(clk),.rst_n(rst_n_profile[11+c]),.d(nx_bus[0+:3]),.q(st_k[3*(7+c)+:3]));
    end endgenerate
    localparam[43:0]N32_INIT_eq=0;
    generate for(genvar c=0;c<3;c=c+1)begin:g_n32_eq
      localparam integer LO=c*16,SW=(44-LO<16)?44-LO:16;
      always @(posedge clk or negedge rst_n_profile[12+c])
        if(!rst_n_profile[12+c])eq[LO+:SW]<=N32_INIT_eq[LO+:SW];
        else eq[LO+:SW]<=nx_bus[NXW*(8+c*1)+68+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(8+c))u_stk(.clk(clk),.rst_n(rst_n_profile[12+c]),.d(nx_bus[0+:3]),.q(st_k[3*(8+c)+:3]));
    end endgenerate
    localparam[15:0]N32_INIT_c_T=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_T
      localparam integer LO=c*16,SW=(16-LO<16)?16-LO:16;
      always @(posedge clk or negedge rst_n_profile[15+c])
        if(!rst_n_profile[15+c])c_T[LO+:SW]<=N32_INIT_c_T[LO+:SW];
        else c_T[LO+:SW]<=nx_bus[NXW*(11+c*1)+112+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(11+c))u_stk(.clk(clk),.rst_n(rst_n_profile[15+c]),.d(nx_bus[0+:3]),.q(st_k[3*(11+c)+:3]));
    end endgenerate
    localparam[7:0]N32_INIT_c_Bt=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_Bt
      localparam integer LO=c*16,SW=(8-LO<16)?8-LO:16;
      always @(posedge clk or negedge rst_n_profile[16+c])
        if(!rst_n_profile[16+c])c_Bt[LO+:SW]<=N32_INIT_c_Bt[LO+:SW];
        else c_Bt[LO+:SW]<=nx_bus[NXW*(12+c*1)+128+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(12+c))u_stk(.clk(clk),.rst_n(rst_n_profile[16+c]),.d(nx_bus[0+:3]),.q(st_k[3*(12+c)+:3]));
    end endgenerate
    localparam[0:0]N32_INIT_c_fclr=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_fclr
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[17+c])
        if(!rst_n_profile[17+c])c_fclr<=N32_INIT_c_fclr;
        else c_fclr<=nx_bus[NXW*(0+c*0)+136];
    end endgenerate
    localparam[0:0]N32_INIT_c_ing=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_ing
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[18+c])
        if(!rst_n_profile[18+c])c_ing<=N32_INIT_c_ing;
        else c_ing<=nx_bus[NXW*(0+c*0)+137];
    end endgenerate
    localparam[0:0]N32_INIT_c_stop=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_stop
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[19+c])
        if(!rst_n_profile[19+c])c_stop<=N32_INIT_c_stop;
        else c_stop<=nx_bus[NXW*(0+c*0)+138];
    end endgenerate
    localparam[0:0]N32_INIT_c_p2=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_p2
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[20+c])
        if(!rst_n_profile[20+c])c_p2<=N32_INIT_c_p2;
        else c_p2<=nx_bus[NXW*(0+c*0)+139];
    end endgenerate
    localparam[0:0]N32_INIT_c_p3=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_p3
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[21+c])
        if(!rst_n_profile[21+c])c_p3<=N32_INIT_c_p3;
        else c_p3<=nx_bus[NXW*(0+c*0)+140];
    end endgenerate
    localparam[0:0]N32_INIT_c_rep=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_rep
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[22+c])
        if(!rst_n_profile[22+c])c_rep<=N32_INIT_c_rep;
        else c_rep<=nx_bus[NXW*(0+c*0)+141];
    end endgenerate
    localparam[15:0]N32_INIT_c_st=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_st
      localparam integer LO=c*16,SW=(16-LO<16)?16-LO:16;
      always @(posedge clk or negedge rst_n_profile[23+c])
        if(!rst_n_profile[23+c])c_st[LO+:SW]<=N32_INIT_c_st[LO+:SW];
        else c_st[LO+:SW]<=nx_bus[NXW*(13+c*1)+142+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(13+c))u_stk(.clk(clk),.rst_n(rst_n_profile[23+c]),.d(nx_bus[0+:3]),.q(st_k[3*(13+c)+:3]));
    end endgenerate
    localparam[43:0]N32_INIT_c_rem=0;
    generate for(genvar c=0;c<3;c=c+1)begin:g_n32_c_rem
      localparam integer LO=c*16,SW=(44-LO<16)?44-LO:16;
      always @(posedge clk or negedge rst_n_profile[24+c])
        if(!rst_n_profile[24+c])c_rem[LO+:SW]<=N32_INIT_c_rem[LO+:SW];
        else c_rem[LO+:SW]<=nx_bus[NXW*(14+c*1)+158+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(14+c))u_stk(.clk(clk),.rst_n(rst_n_profile[24+c]),.d(nx_bus[0+:3]),.q(st_k[3*(14+c)+:3]));
    end endgenerate
    localparam[0:0]N32_INIT_c_hclr=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_c_hclr
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[27+c])
        if(!rst_n_profile[27+c])c_hclr<=N32_INIT_c_hclr;
        else c_hclr<=nx_bus[NXW*(0+c*0)+202];
    end endgenerate
    localparam[0:0]N32_INIT_rep_req=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_rep_req
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[28+c])
        if(!rst_n_profile[28+c])rep_req<=N32_INIT_rep_req;
        else rep_req<=nx_bus[NXW*(0+c*0)+203];
    end endgenerate
    localparam[0:0]N32_INIT_ovf=1'b0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_ovf
      localparam integer LO=c*16,SW=(1-LO<16)?1-LO:16;
      always @(posedge clk or negedge rst_n_profile[29+c])
        if(!rst_n_profile[29+c])ovf<=N32_INIT_ovf;
        else ovf<=nx_bus[NXW*(0+c*0)+204];
    end endgenerate
    localparam[10:0]N32_INIT_kq=0;
    generate for(genvar c=0;c<1;c=c+1)begin:g_n32_kq
      localparam integer LO=c*16,SW=(11-LO<16)?11-LO:16;
      always @(posedge clk or negedge rst_n_profile[30+c])
        if(!rst_n_profile[30+c])kq[LO+:SW]<=N32_INIT_kq[LO+:SW];
        else kq[LO+:SW]<=nx_bus[NXW*(17+c*1)+205+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(17+c))u_stk(.clk(clk),.rst_n(rst_n_profile[30+c]),.d(nx_bus[0+:3]),.q(st_k[3*(17+c)+:3]));
    end endgenerate
    localparam[20:0]N32_INIT_qf=QINV;
    generate for(genvar c=0;c<2;c=c+1)begin:g_n32_qf
      localparam integer LO=c*16,SW=(21-LO<16)?21-LO:16;
      always @(posedge clk or negedge rst_n_profile[31+c])
        if(!rst_n_profile[31+c])qf[LO+:SW]<=N32_INIT_qf[LO+:SW];
        else qf[LO+:SW]<=nx_bus[NXW*(18+c*1)+216+LO+:SW];
      ot_s81pa_rcopy #(.W(3),.INIT(C_CLR),.ID(18+c))u_stk(.clk(clk),.rst_n(rst_n_profile[31+c]),.d(nx_bus[0+:3]),.q(st_k[3*(18+c)+:3]));
    end endgenerate
    initial if(Q!=4||K!=512||KW!=10||CB!=11||XD!=17||PERM!=1||RQPIPE!=1||SLAT!=4)$fatal(1,"fixed selected n32 control shape");
    assign busy = (st != C_ING) || kseen;
endmodule
