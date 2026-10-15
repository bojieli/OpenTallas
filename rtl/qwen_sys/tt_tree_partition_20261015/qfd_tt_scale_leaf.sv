`timescale 1ns/1ps
module ot_qwen_tt_scale_body (
    input wire clk, input wire rst_n,
    input wire [166:0] s3_tag, input wire s3_v, input wire [17:0] s3_t,
    output reg scale_re, output reg [23:0] scale_gre,
    output reg [575:0] scale_addr
);
    localparam integer W=16, IL=8, AW=24, NW=18, GT=3072, TCUT=7,
      SMIN=7, SMAX=11, XD=105, RX=5, ACC_LAT=7, TREE_LAT=7,
      MUL_LAT=6, SCALE_LOCAL=0, SPRE=2, SC=1, BANDF=1, RDMEM=1;
    localparam integer GOUT=GT>>SMIN, NPG=GOUT, LW=$clog2(W), LG=$clog2(GT),
      SD=MUL_LAT+ACC_LAT, TL=TREE_LAT+1, OD=TL*LG, XDD=XD,
      TW=1+1+1+1+1+4+AW+AW+3*(NW+1)+1+3+1+AW+AW;
    wire [31:0] gb=0;
    // -- post-scale: the scale requests, ONE CYCLE EARLIER than the monolithic engine's ---------------------
    //: pre = s3 + (SD - 2 + OD + XDD) in ot_qwen_w12_matvec_part; here s3 + (SD - 3 + OD + XDD); the port element
    //: registers scale_q once before its multiplier, so the multiplier sees the same word on the same edge
    localparam integer PD = SD - 3 + OD + XDD + RX;
    localparam integer PDX = (SPRE >= 2) ? PD - 2 : (SPRE != 0) ? PD - 1 : PD;   // SPRE: request registered 1 (2) edges before use
    wire [TW-1:0] pre_tag;
    wire [PD:0]   pre_vline;
    //: SC (a): the pre-scale compare starts from flops -- the line one edge shorter, then a register (the SRAM bank mux
    //: and capture now have a cycle of their own); the two differences nout - nb / nout - lb (kept KS) are formed in
    //: that register's stage, so the per-group test in the a_act stage is one kept compare against pgi * K.
    localparam integer SCA = ((SC & 1) != 0 && BANDF != 0 && PDX >= 6 && W == (1 << LW) && IL == (1 << $clog2(IL))) ? 1 : 0;
    localparam integer DW = NW + 3;                 // signed difference of two (NW+1)-b counts
    localparam integer CWD = ((DW > LW + $clog2(IL) + 16) ? DW : LW + $clog2(IL) + 16) + 2;   // pgi < 2^16 (BANDF): d - c - 1 fits signed
    wire [DW-1:0] sca_d;                            // registered (mmode ? nout - lb : nout - nb), with pre_tag
    generate if (SCA != 0) begin : g_sca
        wire [TW-1:0] pre_tag_e;
        ot_qwen_me_rdelay_w12 #(.W(TW), .D(PDX - 1), .TREE(SPRE), .MEM(RDMEM)) u_pretag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(pre_tag_e));
        wire e_last, e_oen, e_amax, e_wsrc, e_mmode, e_rmax, e_opend;
        wire [3:0] e_split;
        wire [AW-1:0] e_oa, e_ots, e_mbase, e_sbase;
        wire [NW:0] e_nb, e_lb, e_nout;
        wire [2:0] e_j;
        assign {e_last, e_oen, e_amax, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_nout,
                e_rmax, e_j, e_opend, e_mbase, e_sbase} = pre_tag_e;
        wire [DW-1:0] dn_s, dl_s; wire dn_c, dl_c;
        ot_hdc_ksadd_k #(.W(DW)) u_dn (.a({2'b00, e_nout}), .b(~{2'b00, e_nb}), .cin(1'b1), .s(dn_s), .cout(dn_c));
        ot_hdc_ksadd_k #(.W(DW)) u_dl (.a({2'b00, e_nout}), .b(~{2'b00, e_lb}), .cin(1'b1), .s(dl_s), .cout(dl_c));
        reg [TW-1:0] pre_tag_r;
        reg [DW-1:0] d_r;
        always @(posedge clk) begin pre_tag_r <= pre_tag_e; d_r <= e_mmode ? dl_s : dn_s; end
        assign pre_tag = pre_tag_r;
        assign sca_d = d_r;
    end else begin : g_nsca
        ot_qwen_me_rdelay_w12 #(.W(TW), .D(PDX), .TREE(SPRE), .MEM(RDMEM)) u_pretag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(pre_tag));
        assign sca_d = '0;
    end endgenerate
    ot_hdc_vline #(.D(PD)) u_prev (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(pre_vline));
    wire [NW-1:0] pre_t;
    generate if (SCALE_LOCAL != 0) begin : g_pret
        ot_qwen_me_rdelay_w12 #(.W(NW), .D(PDX), .TREE(SPRE)) u_pret (.clk(clk), .rst_n(rst_n), .d(s3_t), .q(pre_t));
    end else begin : g_nopret
        assign pre_t = {NW{1'b0}};
    end endgenerate
    wire pre_last, pre_oen, pre_amax, pre_wsrc, pre_mmode, pre_rmax, pre_opend;
    wire [3:0] pre_split;
    wire [AW-1:0] pre_oa, pre_ots, pre_mbase, pre_sbase;
    wire [NW:0] pre_nb, pre_lb, pre_nout;
    wire [2:0] pre_j;
    assign {pre_last, pre_oen, pre_amax, pre_wsrc, pre_mmode, pre_split, pre_oa, pre_ots, pre_nb, pre_lb, pre_nout,
            pre_rmax, pre_j, pre_opend, pre_mbase, pre_sbase} = pre_tag;
    wire [GOUT-1:0] pre_scale_active;
    //: BANDF: the group each result-port position holds at the op's split (ot_qfd_band_lanes frame)
    localparam integer TB = TCUT + 3;
    function automatic [16:0] bframe(input [3:0] sp, input integer p);   // {in range, group}
        integer bb, kk, gg;
        reg ok;
        reg [15:0] g16;
        begin
            bb = p >> 3; kk = p & 7;
            if (sp <= TB) begin ok = ((kk >> (TB - sp)) == 0); gg = (bb << (TB - sp)) + kk; end
            else          begin ok = (bb == 0) && (kk < (GT >> sp)); gg = kk; end
            g16 = gg;
            bframe = {ok, g16};
        end
    endfunction
    wire [NPG*32-1:0] pgi;
    wire [NPG-1:0]    pgok;
    genvar pg;
    generate
        for (pg = 0; pg < NPG; pg = pg + 1) begin : g_scale_request_mask
            if (BANDF != 0) begin : g_bf
                wire [16:0] fr = bframe(pre_split, pg);
                assign pgi[pg*32 +: 32] = {16'd0, fr[15:0]};
                assign pgok[pg] = fr[16];
            end else begin : g_lin
                assign pgi[pg*32 +: 32] = gb + pg;
                assign pgok[pg] = ((gb + pg) < (GT >> pre_split));
            end
            wire sca_gt;
            if (SCA != 0) begin : g_scg
                //: nb + pgi*K < nout  <=>  d = nout - nb > c = pgi*K  <=>  sign of d + ~c (= d - c - 1) clear (kept KS)
                wire [CWD-1:0] c = {{(CWD-16){1'b0}}, pgi[pg*32 +: 16]} << (pre_mmode ? LW : LW + $clog2(IL));
                wire [CWD-1:0] gs; wire gco;
                ot_hdc_ksadd_k #(.W(CWD)) u_g (.a({{(CWD-DW){sca_d[DW-1]}}, sca_d}), .b(~c), .cin(((SC & 4) != 0) ? 1'b1 : 1'b0),
                    .s(gs), .cout(gco));
                assign sca_gt = !gs[CWD-1];
`ifdef OT_SC_COV
                integer cov_eq = 0, cov_on = 0;
                always @(posedge clk) if (pre_vline[PDX] && pre_last && !pre_wsrc && pgok[pg]) begin
                    if (gs == {CWD{1'b1}}) cov_eq = cov_eq + 1;      // d == c (the > / >= boundary)
                    if (sca_gt) cov_on = cov_on + 1;
                end
                final if (pg == 0 || pg == 1 || pg == 9) $display("SC_COV a pg=%0d: tested_on=%0d boundary=%0d", pg, cov_on, cov_eq);
`endif
            end else begin : g_scn
                assign sca_gt = 1'b0;
            end
            assign pre_scale_active[pg] = pre_vline[PDX] && pre_last && !pre_wsrc && pgok[pg] &&
                ((SCA != 0) ? sca_gt :
                (pre_mmode ? (pre_lb + pgi[pg*32 +: 32]*W < pre_nout) :
                             (pre_nb + pgi[pg*32 +: 32]*(W*IL) < pre_nout)));
        end
    endgenerate
    integer sg;
    //: SPRE: one registered stage of the request (active mask, base, row offset, group index); else wires
    wire [GOUT-1:0] sq_act;
    wire [AW-1:0]   sq_sbase;
    wire [NW-1:0]   sq_t;
    wire [2:0]      sq_j;
    wire [NW:0]     sq_nbs;
    wire [NPG*32-1:0] sq_pgi;
    wire [NPG*AW-1:0] bq_sbase;     // SPRE 2: per-group copies
    wire [NPG*NW-1:0] bq_t;
    wire [NPG*3-1:0]  bq_j;
    wire [NPG*(NW+1)-1:0] bq_nbs;
    wire [NPG*AW-1:0] bq_off;       // SC (c): per-group row offset (SPRE 2)
    generate if (SPRE >= 2) begin : g_spre2
        //: SPRE 2 (redesign-qwen): a shared registered stage A, then one registered copy PER SCALE GROUP (B, kept: placed by
        //: the group's scale_addr / scale_gre outputs), then the per-group add -- the 24-b base no longer fans out to 48
        //: adders across the tile in the add's own cycle.
        reg [GOUT-1:0] a_act;
        reg [AW-1:0]   a_sbase;
        reg [NW-1:0]   a_t;
        reg [2:0]      a_j;
        reg [NW:0]     a_nbs;
        reg [NPG*32-1:0] a_pgi;
        always @(posedge clk or negedge rst_n) if (!rst_n) a_act <= 0; else a_act <= pre_scale_active;
        always @(posedge clk) begin a_sbase <= pre_sbase; a_t <= pre_t; a_j <= pre_j; a_nbs <= pre_nb >> LW; a_pgi <= pgi; end
        genvar sgb;
        for (sgb = 0; sgb < NPG; sgb = sgb + 1) begin : g_b
            (* keep *) reg          b_act;
            (* keep *) reg [AW-1:0] b_sbase;
            (* keep *) reg [NW-1:0] b_t;
            (* keep *) reg [2:0]    b_j;
            (* keep *) reg [NW:0]   b_nbs;
            (* keep *) reg [31:0]   b_pgi;
            always @(posedge clk or negedge rst_n) if (!rst_n) b_act <= 1'b0; else b_act <= a_act[sgb];
            always @(posedge clk) begin b_sbase <= a_sbase; b_t <= a_t; b_j <= a_j; b_nbs <= a_nbs; b_pgi <= a_pgi[sgb*32 +: 32]; end
            //: SC (c): the row offset of the scale address added in the A -> B stage (scale_addr = b_sbase + b_off, a
            //: 2-operand add; mod 2^AW as the 3-operand sum)
            (* keep *) reg [AW-1:0] b_off;
            always @(posedge clk)
                b_off <= (SCALE_LOCAL != 0) ? a_t * IL + a_j :
                         ((SC & 8) != 0) ? a_pgi[sgb*32 +: 32] * IL : a_nbs + a_pgi[sgb*32 +: 32] * IL;
            assign bq_off[sgb*AW +: AW] = b_off;
            assign sq_act[sgb] = b_act;
            assign sq_pgi[sgb*32 +: 32] = b_pgi;
            assign bq_sbase[sgb*AW +: AW] = b_sbase; assign bq_t[sgb*NW +: NW] = b_t; assign bq_j[sgb*3 +: 3] = b_j;
            assign bq_nbs[sgb*(NW+1) +: NW+1] = b_nbs;
        end
        assign sq_sbase = bq_sbase[AW-1:0]; assign sq_t = bq_t[NW-1:0]; assign sq_j = bq_j[2:0]; assign sq_nbs = bq_nbs[NW:0];
    end else if (SPRE != 0) begin : g_spre
        assign bq_sbase = '0; assign bq_t = '0; assign bq_j = '0; assign bq_nbs = '0; assign bq_off = '0;
        reg [GOUT-1:0] r_act;
        reg [AW-1:0]   r_sbase;
        reg [NW-1:0]   r_t;
        reg [2:0]      r_j;
        reg [NW:0]     r_nbs;
        reg [NPG*32-1:0] r_pgi;
        always @(posedge clk or negedge rst_n) if (!rst_n) r_act <= 0; else r_act <= pre_scale_active;
        always @(posedge clk) begin r_sbase <= pre_sbase; r_t <= pre_t; r_j <= pre_j; r_nbs <= pre_nb >> LW; r_pgi <= pgi; end
        assign sq_act = r_act; assign sq_sbase = r_sbase; assign sq_t = r_t; assign sq_j = r_j; assign sq_nbs = r_nbs;
        assign sq_pgi = r_pgi;
    end else begin : g_nospre
        assign bq_sbase = '0; assign bq_t = '0; assign bq_j = '0; assign bq_nbs = '0; assign bq_off = '0;
        assign sq_act = pre_scale_active; assign sq_sbase = pre_sbase; assign sq_t = pre_t; assign sq_j = pre_j;
        assign sq_nbs = pre_nb >> LW; assign sq_pgi = pgi;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin scale_re <= 1'b0; scale_gre <= 0; end
        else begin scale_re <= |sq_act; scale_gre <= sq_act; end
    end
    generate if (SPRE < 2) begin : g_sadd1
    always @(posedge clk) begin
        for (sg = 0; sg < NPG; sg = sg + 1)
            scale_addr[sg*AW +: AW] <= !sq_act[sg] ? sq_sbase :
                (SCALE_LOCAL != 0) ? sq_sbase + sq_t * IL + sq_j :
                                     sq_sbase + sq_nbs + sq_pgi[sg*32 +: 32] * IL;
    end
    end else begin : g_sadd
        genvar sga;
        for (sga = 0; sga < NPG; sga = sga + 1) begin : g_a
            if ((SC & 1) != 0) begin : g_sc
                wire [AW-1:0] sa; wire sco;
                ot_hdc_ksadd_k #(.W(AW)) u_sa (.a(bq_sbase[sga*AW +: AW]), .b(bq_off[sga*AW +: AW]), .cin(1'b0), .s(sa), .cout(sco));
                always @(posedge clk)
                    scale_addr[sga*AW +: AW] <= !sq_act[sga] ? bq_sbase[sga*AW +: AW] : sa;
            end else begin : g_n
            always @(posedge clk)
                scale_addr[sga*AW +: AW] <= !sq_act[sga] ? bq_sbase[sga*AW +: AW] :
                    (SCALE_LOCAL != 0) ? bq_sbase[sga*AW +: AW] + bq_t[sga*NW +: NW] * IL + bq_j[sga*3 +: 3] :
                    bq_sbase[sga*AW +: AW] + bq_nbs[sga*(NW+1) +: NW+1] + sq_pgi[sga*32 +: 32] * IL;
            end
        end
    end endgenerate


endmodule

module qfd_tt_scale_leaf (
    input wire clk, input wire rst_n,
    input wire [166:0] s3_tag, input wire s3_v, input wire [17:0] s3_t,
    output reg scale_re, output reg [23:0] scale_gre,
    output reg [575:0] scale_addr
);
    wire raw_re; wire [23:0]raw_gre; wire [575:0]raw_addr;
    ot_qwen_tt_scale_body u_scale(.clk(clk),.rst_n(rst_n),.s3_tag(s3_tag),
      .s3_v(s3_v),.s3_t(s3_t),.scale_re(raw_re),.scale_gre(raw_gre),.scale_addr(raw_addr));
    always @(posedge clk or negedge rst_n)
      if(!rst_n)begin scale_re<=0;scale_gre<=0;end
      else begin scale_re<=raw_re;scale_gre<=raw_gre;end
    always @(posedge clk)scale_addr<=raw_addr;
endmodule
