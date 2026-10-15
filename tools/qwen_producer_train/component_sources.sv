module qfd_res_ser_static #(
    parameter integer BAND = 0,
    parameter integer NB = 3,
    parameter integer D = 2,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          me_en,
    input  wire [4424:0] rq,
    output reg  [550:0]  rb,
    output reg           fault
);
    localparam integer SPAN = 8 * NB;                 // cycles of one burst on the shared result face
    localparam integer T0 = D + 8 * BAND;             // first emission slot of this band after the capture edge
    localparam integer CW = $clog2(SPAN + D + 8) + 1;
    localparam LAST = (BAND == NB - 1);
    wire cap = me_en && rq[4424];
    reg  [551:0] buf_s [0:1][0:7];
    reg  [7:0]   buf_we [0:1];
    reg  [1:0]   busy;                                // buffer holds a burst not yet fully emitted
    reg          wp;                                  // next capture buffer
    reg          rp;                                  // buffer being emitted
    reg  [CW-1:0] age;                                // cycles since the oldest un-emitted capture
    reg  [CW-1:0] since;                              // edges since the last capture minus one (saturating)
    reg          pend;                                // a capture is waiting / emitting
    reg  [CW-1:0] age2;                               // age of the second (younger) capture
    integer s;
    wire [CW-1:0] slot = age - T0[CW-1:0];
    wire in_win = pend && (age >= T0) && (age < T0 + 8);
    wire [2:0] j0 = slot[2:0];
    wire [2:0] j = (MUT != 0 && j0 < 3'd2) ? {2'b00, ~j0[0]} : j0;  // MUT: slots 0/1 swapped
    wire [551:0] w = buf_s[rp][j];
    wire row_beat = in_win && buf_we[rp][j];
    wire end_beat = in_win && LAST && (j0 == 3'd7);
    wire done = pend && (age == T0 + 7);
    reg bad_addr;
    always @(*) begin
        bad_addr = 1'b0;
        for (s = 0; s < 8; s = s + 1) if (rq[4416 + s] && |rq[552 * s + 548 +: 4]) bad_addr = 1'b1;
    end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 2'b00; wp <= 1'b0; rp <= 1'b0; pend <= 1'b0; age <= 0; age2 <= 0;
            since <= {CW{1'b1}}; fault <= 1'b0; rb <= 551'd0;
        end else begin
            // emission (a register at the output pin: the beat leaves one edge after its slot decode)
            rb <= {row_beat || end_beat, end_beat, end_beat && !buf_we[rp][j],
                   (row_beat ? w[547:528] : 20'd0), (row_beat ? w[527:512] : 16'd0), (row_beat ? w[511:0] : 512'd0)};
            // ages of pending captures
            if (pend) age <= age + 1'b1;
            if (busy == 2'b11) age2 <= age2 + 1'b1;
            if (done) begin
                busy[rp] <= 1'b0; rp <= ~rp;
                if (busy == 2'b11) begin age <= age2 + 1'b1; end else pend <= 1'b0;
            end
            since <= (since == {CW{1'b1}}) ? since : since + 1'b1;
            if (cap) begin
                if (since < SPAN - 1 || busy[wp] || bad_addr) fault <= 1'b1;
                for (s = 0; s < 8; s = s + 1) buf_s[wp][s] <= rq[552 * s +: 552];
                buf_we[wp] <= rq[4423:4416];
                busy[wp] <= 1'b1; wp <= ~wp; since <= 0;
                if (!pend || done && busy != 2'b11) begin pend <= 1'b1; age <= 0; end
                else age2 <= 0;
            end
        end
    end
endmodule
module ot_qwen_me_spport_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer GT = 80,
    parameter integer SMIN = 3,
    parameter integer PQ = 4,
    parameter integer TREE_LAT = 3,
    parameter integer SCALE_LAT = 5,      // 5: ot_hdc_fmul (the monolithic engine's); 6: ot_hdc_fp32_mul_lat #(6)
    // qwen-band-integrate 2026-10-08: BANDF 1 = the positions are band-local (ot_qfd_band_lanes frame, see
    // ot_qwen_me_spctl_w12 BANDF): position p holds group g(split, p), so the in-range test, row base, lane-vector
    // base and (g * ots) take g instead of p.  Default 0 = base.
    parameter integer BANDF = 0,
    parameter integer TCUT = 7,
    parameter integer HARD_MUL = 0
) (
    input wire [15:0] ck_mul,
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       pt_id,
    input  wire [PQ*W*32-1:0] lv_in,          // tree level LG-1 at positions pt_id*PQ.., word-major (position, lane)
    input  wire              a_v_e2,
    input  wire [1+1+1+1+4+AW+AW+3*(NW+1)-1:0] a_f_e2,
    input  wire [PQ*W*16-1:0] scale_q,
    output reg  [PQ-1:0]     o_we,
    output reg  [PQ*AW-1:0]  o_addr,
    output reg  [PQ*W-1:0]   o_mask,
    output reg  [PQ*W*32-1:0] o_data,
    output reg               o_ov,          // qwen-vm-me: the burst (op-output edge) marker, aligned with o_we
    output wire [1+32+NW-1:0] am,
    output reg               fault
);
    localparam integer TA = TREE_LAT;
    localparam integer NL = PQ * W;
    localparam integer LPT = $clog2(NL);
    localparam integer CW = 1 + 32 + NW;
    localparam integer FW = 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1);
    localparam integer BW = 32;
    // -- tree level LG: hold TA, then the level register ---------------------------------------------------
    wire [NL*32-1:0] held;
    reg  [NL*32-1:0] raw_res;
    ot_qwen_me_rdelay_w12 #(.W(NL*32), .D(TA)) u_hold (.clk(clk), .rst_n(rst_n), .d(lv_in), .q(held));
    always @(posedge clk) raw_res <= held;
    // -- stage E: the tags (a - 1) ------------------------------------------------------------------------------
    reg          e_v;
    reg [FW-1:0] e_f;
    always @(posedge clk or negedge rst_n) if (!rst_n) e_v <= 1'b0; else e_v <= a_v_e2;
    always @(posedge clk) e_f <= a_f_e2;
    wire          e_last, e_oen, e_wsrc, e_mmode;
    wire [3:0]    e_split;
    wire [AW-1:0] e_oa, e_ots;
    wire [NW:0]   e_nb, e_lb, e_nout;
    assign {e_last, e_oen, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_nout} = e_f;
    wire [31:0] q0 = {16'd0, pt_id} * PQ;
    wire [$clog2(GT):0] e_ports = GT >> e_split;
    localparam integer QB = 16;
    wire [PQ-1:0]     e_gok, e_pos, e_big;
    wire [PQ*4-1:0]   e_dlo;
    wire [PQ*BW-1:0]  e_rowb;
    wire [PQ*AW-1:0]  e_qots;
    localparam integer TB = TCUT + 3;
    function automatic [16:0] bframe(input [3:0] sp, input [31:0] p);   // {in range, group}
        reg [31:0] bb, kk, gg;
        reg ok;
        reg [15:0] g16;
        begin
            bb = p >> 3; kk = p & 7;
            if (sp <= TB) begin ok = ((kk >> (TB - sp)) == 0); gg = (bb << (TB - sp)) + kk; end
            else          begin ok = (bb == 0) && (kk < (GT >> sp)); gg = kk; end
            g16 = gg[15:0];
            bframe = {ok, g16};
        end
    endfunction
    genvar b, g, e;
    generate for (g = 0; g < PQ; g = g + 1) begin : g_e
        wire [31:0] qp = q0 + g;
        wire [16:0] fr = bframe(e_split, qp);
        wire [31:0] qg = (BANDF != 0) ? {16'd0, fr[15:0]} : qp;
        assign e_gok[g] = (BANDF != 0) ? fr[16] : (qg < e_ports);
        //: row base nb + qg*W*IL, lane-vector base lb + qg*W; the lane mask is base + lane < nout
        wire [BW-1:0] rowb, lvb, base, nd;
        ot_qwen_w12_kadd #(.W(BW)) u_rb (.a({{(BW-NW-1){1'b0}}, e_nb}), .b(qg * (W * IL)), .s(rowb));
        ot_qwen_w12_kadd #(.W(BW)) u_lb (.a({{(BW-NW-1){1'b0}}, e_lb}), .b(qg * W), .s(lvb));
        assign base = e_mmode ? lvb : rowb;
        //: nout - base (base <= nout - 1 iff the borrow is clear and the difference is non-zero)
        wire nd_c;
        ot_qwen_w12_ksa #(.W(BW)) u_nd (.a({{(BW-NW-1){1'b0}}, e_nout}), .b(~base), .cin(1'b1), .s(nd), .cout(nd_c));
        assign e_pos[g] = nd_c && (nd != 0);
        assign e_big[g] = (nd[BW-1:4] != 0);
        assign e_dlo[g*4 +: 4] = nd[3:0];
        assign e_rowb[g*BW +: BW] = rowb;
        //: (q0 + g) * ots
        wire [QB*AW-1:0] qrows;
        wire [AW-1:0] qs, qc;
        for (b = 0; b < QB; b = b + 1) begin : g_qr
            assign qrows[b*AW +: AW] = qg[b] ? (e_ots << b) : {AW{1'b0}};
        end
        ot_qwen_w12_csa_tree #(.W(AW), .N(QB)) u_qcs (.rows(qrows), .s(qs), .c(qc));
        ot_qwen_w12_kadd #(.W(AW)) u_qka (.a(qs), .b(qc), .s(e_qots[g*AW +: AW]));
    end endgenerate
    // -- stage A (the monolithic a_tag cycle) --------------------------------------------------------------------
    reg              raw_v, raw_last, raw_oen, raw_wsrc;
    reg  [AW-1:0]    raw_oa;
    reg  [PQ-1:0]    a_gok, a_pos, a_big;
    reg  [PQ*4-1:0]  a_dlo;
    reg  [PQ*BW-1:0] a_rowb;
    reg  [PQ*AW-1:0] a_qots;
    always @(posedge clk or negedge rst_n) if (!rst_n) raw_v <= 1'b0; else raw_v <= e_v;
    always @(posedge clk) begin
        raw_last <= e_last; raw_oen <= e_oen; raw_wsrc <= e_wsrc; raw_oa <= e_oa;
        a_gok <= e_gok; a_pos <= e_pos; a_big <= e_big; a_dlo <= e_dlo; a_rowb <= e_rowb; a_qots <= e_qots;
    end
    //: lane l of group g is active (an output row): (q0+g < GT >> split) && base + l < nout
    wire [NL-1:0]    act;
    wire [NL*NW-1:0] rows;
    generate for (e = 0; e < NL; e = e + 1) begin : g_act
        localparam integer EQ = e / W, EL = e % W;
        assign act[e] = a_gok[EQ] && a_pos[EQ] && (a_big[EQ] || (a_dlo[EQ*4 +: 4] > EL));
        wire [NW-1:0] r;
        ot_qwen_w12_kadd #(.W(NW)) u_row (.a(a_rowb[EQ*BW +: NW]), .b(EL[NW-1:0]), .s(r));
        assign rows[e*NW +: NW] = r;
    end endgenerate
    // -- post-scale ----------------------------------------------------------------------------------------------
    reg  [NL*16-1:0] sq;
    always @(posedge clk) sq <= scale_q;
    wire [NL*32-1:0] res;
    wire [NL-1:0]    sf;
    generate if (HARD_MUL != 0) begin:g_hard_mul
        initial if (W != 16 || NL > 64 || SCALE_LAT != 8)
            $fatal(1,"hard port needs W16 NL<=64 SCALE_LAT8");
        for(genvar q=0;q<NL/4;q=q+1) begin:g_mul
            wire [7:0] err;
            wire [3:0] vo;
            wire [3:0] vi = {4{raw_v && raw_last}} & act[4*q +: 4];
            ot_qwen_slab_pg_lanes u_ln (.clk(ck_mul[q]),.rs0(rst_n),
                .l_v(vi),.l_ws({4{raw_wsrc}}),.a(raw_res[128*q +: 128]),
                .s(sq[64*q +: 64]),.y(res[128*q +: 128]),.vo(vo),.err(err));
            for(genvar k=0;k<4;k=k+1) begin:g_error
                assign sf[4*q+k] = vo[k] && (err[2*k +: 2] != 0);
            end
        end
    end else begin:g_soft_mul
    for (e = 0; e < NL; e = e + 1) begin : g_scale
        if (SCALE_LAT == 5) begin : g_fmul
            ot_hdc_fmul u_mul (.clk(clk), .rst_n(rst_n), .v(raw_v && raw_last && act[e]),
                .a(raw_res[32*e +: 32]), .b({raw_wsrc ? 16'h3F80 : sq[16*e +: 16], 16'd0}),
                .y(res[32*e +: 32]), .fault(sf[e]));
        end else begin : g_lat
            //: bit-identical to ot_hdc_fmul (ot_hdc_fp32_mul_fast cut at SCALE_LAT stages; rtl/test/tb_hdc_fastfp_equiv.sv,
            //: rtl/test/tb_w11_fp32_mul_lat.cpp); routed alone at 0.833 ns SS +11.4 ps at LAT 6
            wire [1:0] err;
            wire vo;
            ot_hdc_fp32_mul_lat #(.LAT(SCALE_LAT)) u_mul (.clk(clk), .rst_n(rst_n), .valid_in(raw_v && raw_last && act[e]),
                .a(raw_res[32*e +: 32]), .b({raw_wsrc ? 16'h3F80 : sq[16*e +: 16], 16'd0}),
                .y(res[32*e +: 32]), .err(err), .valid_out(vo));
            assign sf[e] = vo && (err != 2'd0);
        end
    end
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= |sf;
    // -- result tag: a + SCALE_LAT, carrying the finished mask, rows and addresses -------------------------------
    localparam integer RW = 1 + 1 + PQ + AW + PQ*AW + NL + NL*NW;
    wire [PQ*AW-1:0] a_oaq;
    generate for (g = 0; g < PQ; g = g + 1) begin : g_oa
        ot_qwen_w12_kadd #(.W(AW)) u_a (.a(raw_oa), .b(a_qots[g*AW +: AW]), .s(a_oaq[g*AW +: AW]));
    end endgenerate
    wire [RW-1:0] rt;
    wire [SCALE_LAT:0] rv;
    ot_qwen_me_rdelay_w12 #(.W(RW), .D(SCALE_LAT)) u_rt (.clk(clk), .rst_n(rst_n),
        .d({raw_last, raw_oen, a_gok, raw_oa, a_oaq, act, rows}), .q(rt));
    ot_hdc_vline #(.D(SCALE_LAT)) u_rv (.clk(clk), .rst_n(rst_n), .v(raw_v), .vd(rv));
    wire          r_v = rv[SCALE_LAT];
    wire          r_last, r_oen;
    wire [PQ-1:0] r_gok;
    wire [AW-1:0] r_oa;
    wire [PQ*AW-1:0] r_oaq;
    wire [NL-1:0] r_mask;
    wire [NL*NW-1:0] r_rows;
    assign {r_last, r_oen, r_gok, r_oa, r_oaq, r_mask, r_rows} = rt;
    // -- the two result registers --------------------------------------------------------------------------------
    reg  [PQ-1:0]     o_we1;
    reg               o_ov1;
    reg  [PQ*AW-1:0]  o_addr1;
    reg  [PQ*W-1:0]   o_mask1;
    reg  [PQ*W*32-1:0] o_data1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_we1 <= 0; o_we <= 0; o_ov1 <= 1'b0; o_ov <= 1'b0; end
        else begin
            o_we1 <= {PQ{r_v && r_last && r_oen}} & r_gok;
            o_we <= o_we1;
            o_ov1 <= r_v && r_last;
            o_ov <= o_ov1;
        end
    end
    always @(posedge clk) begin
        o_addr1 <= r_oaq; o_mask1 <= r_mask; o_data1 <= res;
        o_mask <= o_mask1; o_data <= o_data1; o_addr <= o_addr1;
    end
    // -- argmax leaves and levels 1 .. LPT ------------------------------------------------------------------------
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    wire [(LPT+1)*CW*NL-1:0] alv;          // level al at [al*CW*NL +: CW*NL] (flat: Yosys 0.68 wire-array assert)
    genvar al;
    generate
        for (e = 0; e < NL; e = e + 1) begin : g_leaf
            reg [CW-1:0] c;
            always @(posedge clk) c <= {r_mask[e], okey(res[32*e +: 32]), r_rows[e*NW +: NW]};
            assign alv[CW*e +: CW] = c;
        end
        for (al = 1; al <= LPT; al = al + 1) begin : g_alvl
            for (e = 0; e < (NL >> al); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[(al-1)*CW*NL + CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[(al-1)*CW*NL + CW*(2*e+1) +: CW];
                //: key0 > key1, or equal keys and row0 < row1  <=>  {key0, ~row0} > {key1, ~row1}: one kept
                //: prefix carry (A > B <=> carry out of A + ~B), not Yosys's rippled > / == / <
                wire          gt, gt_c;
                wire [32+NW-1:0] gt_s;
                ot_qwen_w12_ksa #(.W(32 + NW)) u_gt (.a({x0[CW-2 -: 32], ~x0[NW-1:0]}), .b(~{x1[CW-2 -: 32], ~x1[NW-1:0]}),
                    .cin(1'b0), .s(gt_s), .cout(gt_c));
                assign gt = gt_c;
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || gt);
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[al*CW*NL + CW*e +: CW] = c;
            end
            assign alv[al*CW*NL + CW*NL-1 : al*CW*NL + CW*(NL >> al)] = 0;
        end
    endgenerate
    assign am = alv[LPT*CW*NL +: CW];
endmodule
module ot_qwen_w12_ksa #(parameter integer W = 8) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    // Index 0 of the prefix network is the carry-in; index i+1 is bit i.
    localparam integer L = $clog2(W + 1);
    genvar l, i;
    generate
        for (l = 0; l <= L; l = l + 1) begin : g_lv
            (* keep *) wire [W:0] g, p;
            if (l == 0) begin : g_init
                assign g = {a & b, cin};
                assign p = {a ^ b, 1'b0};
            end else begin : g_step
                for (i = 0; i <= W; i = i + 1) begin : g_bit
                    if (i >= (1 << (l - 1))) begin : g_op
                        assign g[i] = g_lv[l-1].g[i] | (g_lv[l-1].p[i] & g_lv[l-1].g[i - (1 << (l - 1))]);
                        assign p[i] = g_lv[l-1].p[i] & g_lv[l-1].p[i - (1 << (l - 1))];
                    end else begin : g_pass
                        assign g[i] = g_lv[l-1].g[i];
                        assign p[i] = g_lv[l-1].p[i];
                    end
                end
            end
        end
    endgenerate
    assign s = (a ^ b) ^ g_lv[L].g[W-1:0];
    assign cout = g_lv[L].g[W];
endmodule
module ot_hdc_vline #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end
    assign vd = {line, v};
endmodule
module ot_qwen_me_rdelay_w12 #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer SL = 64,
    parameter integer TREE = 0,         // redesign-qwen: 1 = the ring read as a balanced OR tree (same value)
    parameter integer MEM = 0           // el1011-q-seq: 1 = SRAM-backed when 4 <= D <= 130 (exact q(t) = d(t - D))
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    // el1011-q-seq MEM: input register -> 1r1w SRAM ring (write pointer wp, read address wp - (D - 3)) -> the macro's
    // registered read -> a capture flop next to each macro.  d of cycle c: registered at c+1, written at the end of c+1,
    // read in cycle c+D-2 (registered read out in c+D-1), captured -> q in cycle c+D.  The read never meets the write
    // address (D - 3 < ring depth).  ot_sram_1r1w_128x256 macros (2.65 k um2 each; the 64 x 512 is 13.3 k um2), NB banks
    // of 128 in depth (bank = address top bits; its select registered with the read, the mux after the capture flops).
    localparam integer NB = (D - 3 < 128) ? 1 : (D - 3 < 256) ? 2 : 4;
    localparam integer BB = (NB == 1) ? 1 : $clog2(NB);
    localparam integer MA = 7 + ((NB == 1) ? 0 : BB);
    localparam integer MW = 256;
    localparam integer NMM = (W + MW - 1) / MW;
    generate if (MEM != 0 && D >= 4 && D <= 514) begin : g_mem
        reg  [W-1:0] d_r;
        reg  [MA-1:0] wp;
        always @(posedge clk) d_r <= d;
        always @(posedge clk or negedge rst_n) if (!rst_n) wp <= {MA{1'b0}}; else wp <= wp + 1'b1;
        wire [MA-1:0] ra = wp - MA'((MEM == 2) ? D - 4 : D - 3);   // MEM 2: one edge short (negative control)
        wire [NMM*MW-1:0] wpad = {{(NMM*MW-W){1'b0}}, d_r};
        wire [NB*W-1:0] qb;
        genvar mm, bk;
        for (bk = 0; bk < NB; bk = bk + 1) begin : g_b
            wire [NMM*MW-1:0] rd;
            wire wsel = (NB == 1) ? 1'b1 : ((wp >> 7) == bk);
            for (mm = 0; mm < NMM; mm = mm + 1) begin : g_m
                ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(1'b1), .r_addr_in(ra[6:0]), .rd_out(rd[mm*MW +: MW]),
                    .w_ce_in(wsel), .w_addr_in(wp[6:0]), .wd_in(wpad[mm*MW +: MW]), .w_mask_in({MW{1'b1}}),
                    .rr_en(2'b0), .rr_addr('0), .cr_en(2'b0), .cr_sel('0));
            end
            reg [W-1:0] q_r;                     // capture flop next to the bank's macros (no logic before it)
            always @(posedge clk) q_r <= rd[W-1:0];
            assign qb[bk*W +: W] = q_r;
        end
        if (NB == 1) begin : g_one
            assign q = qb[W-1:0];
        end else begin : g_sel
            reg [BB-1:0] s1, s2;                 // the read's bank: with the registered read, then with the capture
            always @(posedge clk) begin s1 <= BB'(ra >> 7); s2 <= s1; end
            assign q = qb[s2*W +: W];
        end
    end else if (D <= 1) begin : g_short
        ot_hdc_delay #(.W(W), .D(D)) u_d (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
    end else begin : g_ring
        localparam integer NS = (W + SL - 1) / SL;
        genvar s, i;
        for (s = 0; s < NS; s = s + 1) begin : g_s
            localparam integer LO = s * SL;
            localparam integer SW = ((W - LO) < SL) ? (W - LO) : SL;
            reg [D-1:0] ptr;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) ptr <= {{(D-1){1'b0}}, 1'b1};
                else ptr <= {ptr[D-2:0], ptr[D-1]};
            reg  [D*SW-1:0] mem;            // flat (entry-major): Yosys 0.68 asserts on wire arrays under chparam
            wire [(D+1)*SW-1:0] sel;
            assign sel[SW-1:0] = {SW{1'b0}};
            for (i = 0; i < D; i = i + 1) begin : g_e
                always @(posedge clk) if (ptr[i]) mem[i*SW +: SW] <= d[LO +: SW];
                assign sel[(i+1)*SW +: SW] = sel[i*SW +: SW] | (mem[i*SW +: SW] & {SW{ptr[i]}});
            end
            if (TREE != 0) begin : g_tree
                wire [D*SW-1:0] tm;
                for (i = 0; i < D; i = i + 1) begin : g_m
                    assign tm[i*SW +: SW] = mem[i*SW +: SW] & {SW{ptr[i]}};
                end
                ot_qfd_or_tree #(.W(SW), .N(D)) u_or (.d(tm), .q(q[LO +: SW]));
            end else begin : g_chain
                assign q[LO +: SW] = sel[D*SW +: SW];
            end
        end
    end endgenerate
endmodule
module ot_qfd_or_tree #(parameter integer W = 1, parameter integer N = 2) (input wire [N*W-1:0] d, output wire [W-1:0] q);
    generate if (N == 1) begin : g_1
        assign q = d;
    end else begin : g_n
        localparam integer H = N / 2;
        wire [W-1:0] a, b;
        ot_qfd_or_tree #(.W(W), .N(H)) u_a (.d(d[H*W-1:0]), .q(a));
        ot_qfd_or_tree #(.W(W), .N(N - H)) u_b (.d(d[N*W-1:H*W]), .q(b));
        assign q = a | b;
    end endgenerate
endmodule
module ot_hdc_delay #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule
module ot_qwen_w12_kadd #(parameter integer W = 24) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] s
);
    wire c;
    ot_qwen_w12_ksa #(.W(W)) u (.a(a), .b(b), .cin(1'b0), .s(s), .cout(c));
endmodule
module ot_hdc_fp32_mul_lat #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bit k-1 = C<k> (LAT must be 3 + their count); -1: by LAT as above.
    // W11 serial domain: CUTS = 4'b0101 (C1 + C3, LAT 5) cuts the INPUT side, so an operand multiplexer in front
    // of the unit shares stage 1 with the decode / normalise instead of the partial-product rows
    parameter integer CUTS = -1,
    // KCP > 1 (margin m3, 2026-10-06): the C1 operand register is KCP kept copies (ot_hdc_mul_kcp48), each driving
    // 24/KCP partial products, so the 24-load operand broadcast to the partial-product rows is a local net.  Values
    // identical (every copy captures the same a_n / b_n); no added cycle.  Needs CUT1.
    parameter integer KCP = 1,
    // Opt-in: reset only valid bits at extra cuts; payload is ignored until valid.
    parameter integer DRST = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT1 = (CUTS >= 0) ? CUTS % 2       : (LAT >= 6) ? 1 : 0;
    localparam integer CUT2 = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 5) ? 1 : 0;
    localparam integer CUT3 = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT4 = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;
    localparam integer CUT5 = (CUTS >= 0) ? (CUTS / 16) % 2 : (LAT >= 8) ? 1 : 0;
    localparam integer CUT6 = (CUTS >= 0) ? (CUTS / 32) % 2 : (LAT >= 9) ? 1 : 0;
    localparam integer CUT7 = (CUTS >= 0) ? (CUTS / 64) % 2 : (LAT >= 10) ? 1 : 0;
    generate if (CUTS >= 0 && CUT1 + CUT2 + CUT3 + CUT4 + CUT5 + CUT6 + CUT7 + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_mul_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- S1a: decode, normalise --------------------------------------------------------------------
    // C7: field / zero / non-finite decode | LZC, power
    wire [68:0] c7;
    ot_hdc_w11_cut #(.W(69), .CUT(CUT7), .VB(DRST ? -1 : 69-1)) u_c7 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, a, b, (a[30:23] == 8'd0), (b[30:23] == 8'd0),
            (a[30:23] == 8'hff) || (b[30:23] == 8'hff), (a[30:0] == 31'd0) || (b[30:0] == 31'd0)}), .q(c7));
    wire        x_v, x_afz, x_bfz, nonfinite, zero;
    wire [31:0] x_a, x_b;
    assign {x_v, x_a, x_b, x_afz, x_bfz, nonfinite, zero} = c7;
    wire [7:0]  a_field = x_a[30:23];
    wire [7:0]  b_field = x_b[30:23];
    wire [23:0] a_raw = {!x_afz, x_a[22:0]};
    wire [23:0] b_raw = {!x_bfz, x_b[22:0]};
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32 u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32 u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    wire signed [11:0] a_power = x_afz ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = x_bfz ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    // C5: decode / LZC | normalise shift
    localparam integer W5 = 1 + 1 + 2 + 1 + 24 + 24 + 5 + 5 + 12 + 12;
    wire [W5-1:0] c5;
    ot_hdc_w11_cut #(.W(W5), .CUT(CUT5), .VB(DRST ? -1 : W5-1)) u_c5 (.clk(clk), .rst_n(rst_n),
        .d({x_v, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), x_a[31] ^ x_b[31], a_raw, b_raw, a_lz[4:0],
            b_lz[4:0], a_power, b_power}), .q(c5));
    wire        n_v, n_bz, n_sign;
    wire [1:0]  n_err;
    wire [23:0] n_ar, n_br;
    wire [4:0]  n_al, n_bl;
    wire [11:0] n_ap, n_bp;
    assign {n_v, n_bz, n_err, n_sign, n_ar, n_br, n_al, n_bl, n_ap, n_bp} = c5;
    wire [23:0] a_n = n_ar << n_al;
    wire [23:0] b_n = n_br << n_bl;
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] c1;
    ot_hdc_w11_cut #(.W(W1), .CUT(CUT1), .VB(DRST ? -1 : W1-1)) u_c1 (.clk(clk), .rst_n(rst_n),
        .d({n_v, n_bz, n_err, n_sign, a_n, b_n, n_ap, n_bp}),
        .q(c1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = c1;
    // ---- S1b: rows, exponent sum ------------------------------------------------------------------
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    generate if (KCP > 1 && CUT1 != 0) begin : g_kcp
        wire [KCP*24-1:0] ka, kb;
        genvar k;
        for (k = 0; k < KCP; k = k + 1) begin : g_c
            ot_hdc_mul_kcp48 u_k (.clk(clk), .rst_n(rst_n),
`ifdef NEGK
                .d({a_n ^ ((k == 1) ? 24'd1 : 24'd0), b_n}),   // bench negative control only
`else
                .d({a_n, b_n}),
`endif .q({ka[24*k +: 24], kb[24*k +: 24]}));
        end
        ot_hdc_mul24_rows_k #(.K(KCP)) u_rows (.a(ka), .b(kb), .rows(rows));
    end else begin : g_nokcp
        ot_hdc_mul24_rows u_rows (.a(p_a), .b(p_b), .rows(rows));
    end endgenerate

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= p_v;
    end
    always @(posedge clk) begin
        s1_byp <= p_byp; s1_err <= p_err; s1_sign <= p_sign; s1_rows <= rows; s1_power <= power;
    end

    // ---- S2a: compress to two rows; masks ----------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(s1_rows[144*i +: 48], s1_rows[144*i + 48 +: 48], s1_rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = s1_rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    localparam integer W2 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W2-1:0] c2;
    ot_hdc_w11_cut #(.W(W2), .CUT(CUT2), .VB(DRST ? -1 : W2-1)) u_c2 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_err, s1_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(c2));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = c2;
    // ---- S2b: the prefix add -----------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= q_v;
    end
    always @(posedge clk) begin
        s2_byp <= q_byp; s2_err <= q_err; s2_sign <= q_sign;
        s2_prod <= prod;
        s2_sub47 <= q_s47; s2_sub46 <= q_s46;
        s2_fl47 <= q_fl47; s2_fl46 <= q_fl46;
        s2_sh <= q_sh; s2_mr <= q_mr; s2_ms <= q_ms;
    end

    // ---- S3a: select, subnormal shift, round/sticky bits ------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    localparam integer W3 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W3-1:0] c3;
    ot_hdc_w11_cut #(.W(W3), .CUT(CUT3), .VB(DRST ? -1 : W3-1)) u_c3 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, fl, main, rb && (st || main[0])}), .q(c3));
    wire        r_v, r_byp, r_sign, r_sub, r_inc;
    wire [1:0]  r_err;
    wire [11:0] r_fl;
    wire [23:0] r_main;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_fl, r_main, r_inc} = c3;
    // ---- S3b: round ---------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k #(.W(24)) u_rnd (.a(r_main), .b(24'd0), .cin(r_inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer W4 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W4-1:0] c4;
    ot_hdc_w11_cut #(.W(W4), .CUT(CUT4), .VB(DRST ? -1 : W4-1)) u_c4 (.clk(clk), .rst_n(rst_n),
        .d({r_v, r_byp, r_err, r_sign, r_sub, r_fl, rnd_w, rnd_cw}), .q(c4));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c;
    wire [1:0]  o_err;
    wire signed [11:0] o_fl;
    wire [23:0] rnd;
    assign {o_v, o_byp, o_err, o_sign, o_sub, o_fl, rnd, rnd_c} = c4;
    // ---- S3c: encode --------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = o_fl + {11'd0, carry};
    wire over = !o_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    // C6: encode | refusals -> y
    localparam integer W6 = 1 + 1 + 2 + 1 + 32;
    wire [W6-1:0] c6;
    ot_hdc_w11_cut #(.W(W6), .CUT(CUT6), .VB(DRST ? -1 : W6-1)) u_c6 (.clk(clk), .rst_n(rst_n), .d({o_v, o_byp, o_err, over, code}), .q(c6));
    wire        e_v, e_byp, e_over;
    wire [1:0]  e_err;
    wire [31:0] e_code;
    assign {e_v, e_byp, e_err, e_over, e_code} = c6;
    generate if (DRST != 0) begin : g_output_reset
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= e_v;
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end
    end else begin : g_output_valid_reset
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= e_v;
        end
        always @(posedge clk) begin
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end endgenerate
endmodule
module ot_hdc_w11_cut #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv;
        reg [W-1:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : g_b
            assign q[i] = (i == VB) ? rv : rd[i];
        end
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule
module ot_hdc_ksadd_k #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    localparam integer L = $clog2(W + 1);
    // position 0 is the carry-in; bit i of the operands is position i + 1
    (* keep *) wire [W:0] g [0:L];
    (* keep *) wire [W:0] p [0:L];
    assign g[0] = {a & b, cin};
    assign p[0] = {a ^ b, 1'b0};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign g[l + 1][i] = g[l][i] | (p[l][i] & g[l][i - (1 << l)]);
                    assign p[l + 1][i] = p[l][i] & p[l][i - (1 << l)];
                end else begin : g_p
                    assign g[l + 1][i] = g[l][i];
                    assign p[l + 1][i] = p[l][i];
                end
            end
        end
    endgenerate
    // carry into operand bit i = the group generate of positions [0, i]
    assign s = (a ^ b) ^ g[L][W-1:0];
    assign cout = g[L][W];
endmodule
module ot_hdc_mul24_rows (
    input  wire [23:0]     a,
    input  wire [23:0]     b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;        // {carry, sum} of three rows
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a & {24{b[i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule
module ot_hdc_mul24_rows_k #(parameter integer K = 2) (
    input  wire [K*24-1:0] a,
    input  wire [K*24-1:0] b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a[24*(i*K/24) +: 24] & {24{b[24*(i*K/24) + i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule
module ot_hdc_mul_kcp48 (input wire clk, input wire rst_n, input wire [47:0] d, output reg [47:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 48'd0; else q <= d;
endmodule
module ot_hdc_lzc32 (
    input  wire [31:0] x,
    output wire [5:0]  n
);
    // Level L holds 32 >> L groups; group k covers bits [(k+1)*2^L-1 : k*2^L],
    // with a valid bit (any one) and the count of leading zeros below 2^L.
    reg [31:0]     v, vn;
    reg [32*5-1:0] c, cn;
    integer L, k;
    always @* begin
        v = x;
        c = {(32*5){1'b0}};
        vn = 32'd0;
        cn = {(32*5){1'b0}};
        for (L = 0; L < 5; L = L + 1) begin
            vn = 32'd0;
            cn = {(32*5){1'b0}};
            for (k = 0; k < (16 >> L); k = k + 1) begin
                vn[k] = v[2*k+1] | v[2*k];
                cn[5*k +: 5] = v[2*k+1] ? c[5*(2*k+1) +: 5] : (c[5*(2*k) +: 5] | (5'd1 << L));
            end
            v = vn;
            c = cn;
        end
    end
    assign n = v[0] ? {1'b0, c[4:0]} : 6'd32;
endmodule
module ot_hdc_fmul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    ot_hdc_fp32_mul_pipe u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b),
                            .y(y), .err(err), .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule
module ot_hdc_fp32_mul_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    integer k;

    // -- stage 1: decode, normalize subnormals, resolve zero and nonfinite ----
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire        s1_nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire        s1_zero = (a_raw == 24'd0) || (b_raw == 24'd0);

    //: A subnormal is shifted up until bit 23 is set, its exponent following it
    //: down -- exactly the authority's 23-iteration loop, as one shift.
    function automatic [4:0] lead_shift_24;
        input [23:0] value;
        reg [4:0] shift;
        integer bit_index;
        begin
            shift = 5'd23;
            for (bit_index = 0; bit_index <= 23; bit_index = bit_index + 1)
                if (value[bit_index]) shift = 5'd23 - bit_index[4:0];
            lead_shift_24 = shift;
        end
    endfunction
    wire [4:0] a_shift = lead_shift_24(a_raw);
    wire [4:0] b_shift = lead_shift_24(b_raw);
    //: The authority's powers: field - 150 for a normal, -149 for a subnormal,
    //: then one less for every normalizing shift.
    wire signed [11:0] a_power = (a_field == 8'd0)
        ? (-12'sd149 - {7'd0, a_shift})
        : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0)
        ? (-12'sd149 - {7'd0, b_shift})
        : ($signed({4'd0, b_field}) - 12'sd150);

    reg        s1_v, s1_byp;
    reg [1:0]  s1_err;
    reg        s1_sign;
    reg [23:0] s1_a, s1_b;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_v <= 1'b0; s1_byp <= 1'b0; s1_err <= E_NONE; s1_sign <= 1'b0;
            s1_a <= 24'd0; s1_b <= 24'd0; s1_power <= 12'sd0;
        end else begin
            s1_v <= valid_in;
            s1_byp <= s1_nonfinite || s1_zero;
            s1_err <= s1_nonfinite ? E_NONFINITE : E_NONE;
            s1_sign <= a[31] ^ b[31];
            s1_a <= a_raw << a_shift;
            s1_b <= b_raw << b_shift;
            s1_power <= a_power + b_power;
        end
    end

    // -- stage 2: three 24x8 partial products; both exponent decisions ---------
    //: 46 or 47, never anything else, because both significands carry bit 23;
    //: the decision for each case needs only the exponents, so both are ready
    //: before the product is.
    function automatic [24:0] decide;     // {is_sub, floor[11:0], shift[11:0]}
        input signed [11:0] power;
        input [5:0] msb;
        reg signed [11:0] fl, sh;
        reg sub;
        begin
            fl = power + $signed({6'd0, msb});
            sub = (fl < -12'sd126);
            //: The normal-result align, and the subnormal-result align in units
            //: of the binary32 subnormal LSB; the authority picks on floor >= -126.
            sh = sub ? -(power + 12'sd149) : ($signed({6'd0, msb}) - 12'sd23);
            decide = {sub, fl, sh};
        end
    endfunction

    reg        s2_v, s2_byp, s2_sign;
    reg [1:0]  s2_err;
    reg [31:0] s2_pp0, s2_pp1, s2_pp2;
    reg [24:0] s2_d47, s2_d46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s2_v <= 1'b0; s2_byp <= 1'b0; s2_sign <= 1'b0; s2_err <= E_NONE;
            s2_pp0 <= 32'd0; s2_pp1 <= 32'd0; s2_pp2 <= 32'd0; s2_d47 <= 25'd0; s2_d46 <= 25'd0;
        end else begin
            s2_v <= s1_v; s2_byp <= s1_byp; s2_sign <= s1_sign; s2_err <= s1_err;
            s2_pp0 <= {8'd0, s1_a} * {24'd0, s1_b[7:0]};
            s2_pp1 <= {8'd0, s1_a} * {24'd0, s1_b[15:8]};
            s2_pp2 <= {8'd0, s1_a} * {24'd0, s1_b[23:16]};
            s2_d47 <= decide(s1_power, 6'd47);
            s2_d46 <= decide(s1_power, 6'd46);
        end
    end

    // -- stage 3: the product, and the decision its top bit selects -----------
    wire [47:0] s3_prod = {16'd0, s2_pp0} + {8'd0, s2_pp1, 8'd0} + {s2_pp2, 16'd0};
    wire [24:0] s3_dec = s3_prod[47] ? s2_d47 : s2_d46;

    reg        s3_v, s3_byp, s3_sign, s3_is_sub_q;
    reg [1:0]  s3_err;
    reg [47:0] s3_product;
    reg signed [11:0] s3_floor_q, s3_shift_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s3_v <= 1'b0; s3_byp <= 1'b0; s3_sign <= 1'b0; s3_is_sub_q <= 1'b0;
            s3_err <= E_NONE; s3_product <= 48'd0;
            s3_floor_q <= 12'sd0; s3_shift_q <= 12'sd0;
        end else begin
            s3_v <= s2_v; s3_byp <= s2_byp; s3_sign <= s2_sign;
            s3_err <= s2_err; s3_product <= s3_prod;
            s3_is_sub_q <= s3_dec[24];
            s3_floor_q <= s3_dec[23:12];
            s3_shift_q <= s3_dec[11:0];
        end
    end

    // -- stage 4: align, extract round and sticky, round to nearest even ------
    //: The authority's shift_right_48_to_24: bits outside the product are zero,
    //: so a distance at or past 48 leaves nothing.
    function automatic [23:0] shift_48_to_24;
        input [47:0] value;
        input signed [11:0] distance;
        reg [23:0] taken;
        reg signed [11:0] source;
        integer bit_index;
        begin
            taken = 24'd0;
            for (bit_index = 0; bit_index < 24; bit_index = bit_index + 1) begin
                source = $signed({4'd0, bit_index[7:0]}) + distance;
                //: Narrowed to the product's own index width only where the
                //: guard has already put it in range.
                if ((source >= 12'sd0) && (source < 12'sd48))
                    taken[bit_index] = value[source[5:0]];
            end
            shift_48_to_24 = taken;
        end
    endfunction
    //: ``sticky`` is every bit strictly below the round bit.
    function automatic sticky_below;
        input [47:0] value;
        input signed [11:0] distance;
        reg found;
        integer bit_index;
        begin
            found = 1'b0;
            for (bit_index = 0; bit_index < 48; bit_index = bit_index + 1)
                if ($signed({4'd0, bit_index[7:0]}) < distance - 12'sd1)
                    found = found | value[bit_index];
            sticky_below = found;
        end
    endfunction

    wire [23:0] s4_main = (s3_is_sub_q && (s3_shift_q >= 12'sd48))
                        ? 24'd0
                        : shift_48_to_24(s3_product, s3_shift_q);
    //: Named so the index is narrowed once, inside the range the guard proves.
    wire signed [11:0] s4_round_index = s3_shift_q - 12'sd1;
    wire s4_round_in_range = (s3_shift_q > 12'sd0) && (s3_shift_q <= 12'sd48);
    wire s4_round_bit = s4_round_in_range &&
                        s3_product[s4_round_in_range ? s4_round_index[5:0]
                                                     : 6'd0];
    wire s4_sticky = sticky_below(s3_product, s3_shift_q);
    wire [24:0] s4_rounded =
        {1'b0, s4_main} +
        {24'd0, (s4_round_bit && (s4_sticky || s4_main[0]))};

    reg        s4_v, s4_byp, s4_sign, s4_is_sub;
    reg [1:0]  s4_err;
    reg [24:0] s4_mant;
    reg signed [11:0] s4_floor;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s4_v <= 1'b0; s4_byp <= 1'b0; s4_sign <= 1'b0; s4_is_sub <= 1'b0;
            s4_err <= E_NONE; s4_mant <= 25'd0; s4_floor <= 12'sd0;
        end else begin
            s4_v <= s3_v; s4_byp <= s3_byp; s4_sign <= s3_sign;
            s4_err <= s3_err; s4_is_sub <= s3_is_sub_q;
            s4_mant <= s4_rounded;
            s4_floor <= s3_floor_q;
        end
    end

    // -- stage 5: the post-round carry, the encoding, and the refusals --------
    //: A carry out of bit 24 moves the leading bit up one exponent.
    wire        s5_carry = !s4_is_sub && s4_mant[24];
    wire [23:0] s5_man = s5_carry ? s4_mant[24:1] : s4_mant[23:0];
    wire signed [11:0] s5_floor = s4_floor + $signed({11'd0, s5_carry});
    wire        s5_over = !s4_is_sub && (s5_floor > 12'sd127);
    wire [7:0]  s5_field = s5_floor[7:0] + 8'd127;
    //: The subnormal path rounds in LSB units, so a mantissa reaching 2**23 has
    //: rounded UP into the smallest normal and is encoded with field 1.
    wire        s5_sub_carry = s4_is_sub && (s4_mant >= 25'h080_0000);
    wire [31:0] s5_code =
        s4_is_sub ? (s5_sub_carry ? {s4_sign, 8'h01, 23'd0}
                                  : {s4_sign, 8'h00, s4_mant[22:0]})
                  : {s4_sign, s5_field, s5_man[22:0]};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y <= 32'd0; err <= E_NONE; valid_out <= 1'b0;
        end else begin
            valid_out <= s4_v;
            if (s4_byp) begin
                //: A zero operand gives +0 whatever the signs; nonfinite gives
                //: the refusal and a zero code, never an infinity.
                y <= 32'd0;
                err <= s4_err;
            end else if (s5_over) begin
                y <= 32'd0;
                err <= E_OVERFLOW;
            end else begin
                y <= (s5_code[30:0] == 31'd0) ? 32'd0 : s5_code;
                err <= E_NONE;
            end
        end
    end
endmodule
module ot_qwen_w12_csa_tree #(parameter integer W = 24, parameter integer N = 8) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s,
    output wire [W-1:0]   c
);
    function automatic integer nxt(input integer n);
        nxt = (n <= 2) ? n : 2 * (n / 3) + (n % 3);
    endfunction
    function automatic integer cnt(input integer l);
        integer i, n;
        begin n = N; for (i = 0; i < l; i = i + 1) n = nxt(n); cnt = n; end
    endfunction
    function automatic integer depth(input integer d);
        integer n, l;
        begin n = N; l = 0; while (n > 2) begin n = nxt(n); l = l + 1; end depth = l; end
    endfunction
    localparam integer L = depth(0);
    genvar l, i;
    generate
        for (l = 0; l <= L; l = l + 1) begin : g_l
            localparam integer NL = cnt(l);
            (* keep *) wire [((NL > 0) ? NL : 1)*W-1:0] r;
            if (l == 0) begin : g0
                assign r = rows;
            end else begin : gn
                localparam integer NP = cnt(l - 1);
                for (i = 0; i < NP / 3; i = i + 1) begin : g_c
                    wire [W-1:0] x = g_l[l-1].r[(3*i)*W +: W], y = g_l[l-1].r[(3*i+1)*W +: W],
                                 z = g_l[l-1].r[(3*i+2)*W +: W];
                    assign r[(2*i)*W +: W] = x ^ y ^ z;
                    assign r[(2*i+1)*W +: W] = ((x & y) | (x & z) | (y & z)) << 1;
                end
                for (i = 0; i < NP % 3; i = i + 1) begin : g_p
                    assign r[(2*(NP/3)+i)*W +: W] = g_l[l-1].r[(3*(NP/3)+i)*W +: W];
                end
            end
        end
    endgenerate
    assign s = g_l[L].r[0 +: W];
    assign c = (cnt(L) > 1) ? g_l[L].r[W +: W] : {W{1'b0}};
endmodule
module ot_qwen_me_spctl_w12 #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_SCALE_WCS_BASE = 1,
    parameter integer GT = 80,
    parameter integer TG = 4,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer TCUT = 3,
    parameter integer XD = 0,
    parameter integer XVM = 0,
    parameter integer ORD = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer PQ = 4,
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5,
    parameter integer SCALE_LAT = 5,
    parameter integer LANDED = 0,      // qwen-vm-me: progress / idle count LANDED result bursts (land_cnt), 0 = base
    // qwen-band-integrate 2026-10-08 (default 0 = base):
    //   RX    extra edges between the tree lanes' level-(LG-1) words and the port elements (the band-lane blocks'
    //         +5 + 2 LNK): the element tags (p_v_e2 / p_f_e2), the scale requests, the result valid, the argmax top
    //         and the argmax-accumulator clear move RX edges later, so every result-side output is the base's
    //         delayed RX edges (the per-level tree selects t_sel_e / t_tv_e are unchanged: the bands are lane-timed).
    //   BANDF 1: the result-port positions are BAND-LOCAL (ot_qfd_band_lanes frame): position p = 8b + k holds group
    //         g = b * 2^(TCUT+3-s) + k (k < 2^(TCUT+3-s)) at split s <= TCUT+3, else g = k on band 0 (k < GT >> s);
    //         the scale requests use g (rows, scale address, in-range test).  Needs GT = 48 << TCUT, SMIN >= TCUT.
    parameter integer RX = 0,
    //   RXA   the argmax-accumulator clear's delay (default RX): the result shift relative to the op's ISSUE, which is
    //         RX minus any reduction of XD (a caller that makes the tree selects early by lowering XD passes RXA itself)
    parameter integer RXA = RX,
    parameter integer BANDF = 0,
    // AMR = 1 (safe-qwen S-D1, 2026-10-08; 0 = unchanged): the argmax tree's top word {top_v, key, idx} and its valid /
    // rmax tag are registered AT the accumulator, and the accumulator clear moves with them, so the top-vs-best compare
    // (u_bgt) and the am_idx / best_key / am_val update are local (routed qfd_sp_tree_top_b: am_idx -> u_bgt -> am_idx
    // 2,228 ps, 6 logic + ~40 wire buffers).  The argmax result (am_any / am_idx / am_val) settles one edge later.
    parameter integer AMR = 0,
    // SPRE (redesign-qwen 2026-10-09; 0 = unchanged): the post-scale request path (pretag ring read -> per-group in-range
    // compare / multiply -> scale_active -> scale_addr add, tree-top TT -1,584 / -1,592) is cut by one register stage:
    // the tags are delayed PD - 1 (balanced-OR ring read), the per-group request is registered, and scale_re / gre / addr
    // are formed from it on the edge the base forms them.  0 cycles, same outputs every edge.
    parameter integer SPRE = 0,
    parameter integer XADDR = 1,         // el1011-q-seq: 0 = no per-port x_re / x_addr (callers on the descriptor form x_dv/x_dc/x_dcs;
                                         //   62.7 k flops + shared CSA rows of fan-out 2-4 k in ctlm_i, all unobserved)
    parameter integer RDMEM = 0,         // el1011-q-seq: 1 = the long tag delay lines (u_tag / u_pretag) in SRAM (rdelay MEM)
    parameter integer SC = 0,            // el1011-q-seq setup cuts (exact, 0 cycles; bit 0 on, bits 1-3 negative controls): fpapk-4e9afc303 classes
                                         //   (a) pre-scale compare from flops: u_pretag one edge shorter + a register, the two differences
                                         //   (nout - nb / nout - lb) as kept KS in that stage, the per-group test a kept compare against
                                         //   pgi*K (BANDF only; bit 2 mutant: >= for >); (b) mx write: lane rotate / slot select
                                         //   pre-decoded from the ring output and the slot maximum rk[t_j] / rseen[t_j] registered with
                                         //   write forwarding (bit 1 mutant: no forwarding); (c) scale_addr = b_sbase + b_off, the
                                         //   offset added one stage earlier (bit 3 mutant: offset without nbs)
    parameter integer AMI = 0,           // el1011-q-seq (coordinator 10-11 decision, +1 argmax-loop cycle): 1 = p_am pin register (the die
                                         //   word lands in a flop at the ctlm pin; textbook class 3, routed p_am -> argmax -58 ps), and every
                                         //   result-side argmax / mx timing (tree valid line tv, tag line u_ttag, accumulator clear RXA) one
                                         //   edge later to match: am_* / mx_* / idle settle one edge later, the result sequence is unchanged;
                                         //   2 = negative control (the register without the +1 compensation: MUST FAIL)
    parameter integer PK = 0             // el1011-q-seq (exact, 0 cycles): 1 = progress subtract as a kept Kogge-Stone (was a 16-b MAJ ripple behind the
                                         //   land_cnt pin flop) and the u_ttag line read from a register (ring D-1 + output flop: t_* straight from flops); 2 = negative control (KS carry-in dropped: progress one low)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [15:0]       land_cnt,  // LANDED: result bursts written into the vector memory since reset (ot_qfd_res_merge)
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [NW-1:0]     i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_ts,
    input  wire [AW-1:0]     i_ks,
    input  wire [AW-1:0]     i_js,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xks,
    input  wire [AW-1:0]     i_xjs,
    input  wire [AW-1:0]     i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire              i_amax,
    input  wire              i_rmax,
    input  wire [AW-1:0]     i_mbase,
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    output reg               kv_re,
    // scale requests (ONE CYCLE EARLIER than ot_qwen_me_spine_w12's)
    output reg               scale_re,
    output reg  [(GT >> SMIN)-1:0]    scale_gre,
    output reg  [(GT >> SMIN)*AW-1:0] scale_addr,
    // x reads and the x network's first (select) stage
    output reg  [(1<<SMAX)-1:0]    x_re,
    output reg  [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    output reg  [(1<<SMAX)*32-1:0] xl0,
    // the x read as a descriptor (qwen-rtl-finish 2026-10-07, die master qfd_sp_tree_top): x_re[c] = x_dv for every
    // enabled port, x_addr[c] = x_dc + (c mod 2^x_dsp) * x_dcs (mod 2^AW), the x network select stage's split = x_dsp
    // (op_split, before its 2 + XVM delay).  Equivalent to x_re / x_addr; a caller uses one or the other.
    output reg               x_dv,
    output reg  [AW-1:0]     x_dc,
    output reg  [AW-1:0]     x_dcs,
    output wire [3:0]        x_dsp,
    // tree elements: per level (index = level) the hold/sum select and the adder valid, one cycle early
    output wire [$clog2(GT):0] t_sel_e,
    output wire [$clog2(GT):0] t_tv_e,
    input  wire [W-1:0]        tr_fault,       // the tree elements' registered faults
    // port elements: the element tag fields and valid two cycles early; their argmax nodes and faults
    output wire              p_v_e2,
    output wire [1+1+1+1+4+AW+AW+3*(NW+1)-1:0] p_f_e2,
    input  wire [((GT >> SMIN) / PQ)*(1+32+NW)-1:0] p_am,
    input  wire [((GT >> SMIN) / PQ)-1:0]   p_fault,
    input  wire              fab_fault,
    output wire              ov,
    output reg  [NW-1:0]     am_idx,
    output reg  [31:0]       am_val,
    output reg               am_any,
    output reg               mx_we,
    output reg  [AW-1:0]     mx_addr,
    output reg  [W-1:0]      mx_mask,
    output reg  [W*32-1:0]   mx_data,
    output reg  [15:0]       progress,
    output wire              fault
);
    // the PART 2 engine top of ot_qwen_w12_matvec_part, fixed here
    localparam integer G = GT;
    localparam integer PART = 2;
    localparam integer GBASE = 0;
    localparam integer GBASE_PORT = 0;
    localparam integer INT8_WEIGHT = 1;
    localparam integer NX = 1 << SMAX;
    localparam integer MEM_EXTRA = 0;
    localparam integer GOUT = GT >> SMIN;
    wire [31:0] i_gbase = 32'd0;
    wire        active_o;
    localparam integer LW = $clog2(W);
    localparam integer LG = $clog2(G);
    localparam integer FB = IL - ACC_LAT; // circulation delay after the adder
    localparam integer SD = MUL_LAT + ACC_LAT;  // S3 -> the lane sums (products at +MUL_LAT, the accumulator add)
    localparam integer TA = TREE_LAT;     // split-tree adder: ot_hdc_qadd (rtl/hdc/ot_hdc_fastfp.sv), LATENCY 3, or ot_qwen_w12_ladd
    localparam integer TL = TA + 1;       // split-tree cycles per level: the adder + 1 output register
    localparam integer OD = TL * LG;      // split tree
    localparam integer XDD = (PART == 2) ? XD : 0;
    localparam integer LV0 = (PART == 2) ? TCUT : 0;   // tree levels LV0+1..LG live here
    localparam integer PRUNE = (SMIN > 0);
    // result-port groups: the only groups a K-split tree can deliver to
    localparam integer NPG = PRUNE ? (((GT >> SMIN) < G) ? (GT >> SMIN) : G) : G;
    localparam integer NPX = (NX < G) ? NX : G;
    localparam integer LANES = (PART != 2);
    localparam integer PORTS = (PART != 1);
    //: internal widths: the lanes' (GL), the split tree's (GI: the top holds only the positions of
    //: its input level) and the result path's (GR: the result-port groups when pruned)
    localparam integer GL = LANES ? G : 1;
    localparam integer GI = (PART == 2) ? (G >> TCUT) : G;
    localparam integer GR = PRUNE ? NPG : G;
    function automatic [15:0] int8_bf16(input [7:0] code);
        reg [7:0] mag, norm;
        reg [2:0] msb;
        integer bit_index;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            msb = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (mag[bit_index]) msb = bit_index[2:0];
            norm = mag << (3'd7 - msb);
            int8_bf16 = (mag == 0) ? 16'd0 :
                        {code[7], (8'd127 + {5'd0, msb}), norm[6:0]};
        end
    endfunction
    //: the global index of local group 0
    wire [31:0] gb = (GBASE_PORT != 0) ? i_gbase : GBASE;

    // -- issue loop -----------------------------------------------------------
    integer gi;
    reg              active;
    assign active_o = active;
    reg [NW-1:0]     nout_r, tiles_r, k_r;
    reg              wsrc_r, round_r, oen_r, amax_r, mmode_r, rmax_r;
    reg [AW-1:0]     mbase_r;
    reg [AW-1:0]     scale_base_r;
    reg [3:0]        split_r;
    reg [AW-1:0]     tstep_r;          // weight step per round: ts, or (G/S)*ts for KV ops
    reg [AW-1:0]     wcs_r;
    reg [NW-1:0]     ktot_r;           // KV ops: the whole K (elements past it multiply +0)
    reg [AW-1:0]     ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r;
    reg [2:0]        jsh_r;
    reg [NW-1:0]     t, k;
    reg [$clog2(IL)-1:0] j;
    reg [AW-1:0]     cur, base_k, base_t, xk, xc, xk_base, oa, ot, ot_step;
    reg [NW:0]       nb, nb_t, nb_step;    // first row of the current slot / round (port 0)
    reg [NW:0]       lb, lb_step;          // first lane-vector index of the round (mmode 1)
    reg              t_last, k_last;
    wire             j_last = (j == IL - 1);
    //: pruning: an op below the smallest split the pruned tree supports
    reg              split_fault;
    //: KV_PREP > 0: a KV-sourced op waits KV_PREP cycles after its go (ready low) for its per-group KV
    //: offsets, which leave the issue path as a pipelined multiply (see g_kv_addr)
    reg              pend;
    reg [3:0]        pcnt;

    assign ready = !active && !pend;

generate if (FAST_ISSUE == 0) begin : g_issue_legacy
    // tiles one round covers: GT/S (the whole engine's groups)
    wire [$clog2(GT):0] per_round = GT >> i_split;
    //: KV ops cut their whole K interleaved: ceil(K/S) steps
    wire [NW-1:0]    kc_in = i_wsrc ? ((i_k + ((16'd1 << i_split) - 16'd1)) >> i_split) : i_k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
            split_fault <= 1'b0;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                active <= 1'b1;
                if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; k_r <= kc_in; ktot_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                rmax_r <= i_rmax; mbase_r <= i_mbase;
                scale_base_r <= (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
                mmode_r <= i_mmode; split_r <= i_split; wcs_r <= i_wcs;
                ts_r <= i_ts; tstep_r <= i_wsrc ? (i_ts * per_round) : i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= (kc_in == 1);
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase; ot_step <= i_ots * per_round;
                nb <= 0; nb_t <= 0; nb_step <= per_round * (W * IL);
                lb <= 0; lb_step <= per_round * W;
            end
        end else begin
            // this cycle's element: (r, k, j) at `cur`
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa + ojs_r; nb <= nb + W; xc <= xc + xjs_r;
                //: the weight word advances once per 2^jsh slots
                if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur + js_r;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k + 1'b1; k_last <= (k + 2 == k_r);
                    base_k <= base_k + ks_r; cur <= base_k + ks_r;
                    xk <= xk + xks_r; xc <= xk + xks_r;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk_base; xc <= xk_base;
                    if (!t_last) begin
                        t <= t + 1'b1; t_last <= (t + 2 == tiles_r);
                        base_t <= base_t + tstep_r; base_k <= base_t + tstep_r; cur <= base_t + tstep_r;
                        ot <= ot + ot_step; oa <= ot + ot_step;
                        nb_t <= nb_t + nb_step; nb <= nb_t + nb_step; lb <= lb + lb_step;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end
end else begin : g_issue_fast
    //: FAST_ISSUE (1.2 GHz @ SS): the same schedule, cycle for cycle (plus KV_PREP on KV ops).
    //: (1) The per-op products (the round steps ts*(GT/S), ots*(GT/S), (GT/S)*W*IL, (GT/S)*W and the KV
    //:     K-step count ceil(K/S)) are first needed at the first K or round boundary, IL >= 3 cycles after
    //:     the go: they are two register stages computed from the latched fields, not an input-to-register
    //:     multiply; ts*(GT/S) is shifted adds of ts (GT's set bits), not a multiplier.
    //: (2) Every loop add is ot_qwen_w12_kadd: a Kogge-Stone prefix adder whose levels are kept netlist
    //:     boundaries (ABC re-maps a flattened `+` as a MAJ ripple: 22 cells, -656 ps at SS on `cur`).
    localparam integer PRW = $clog2(GT) + 1;
    //: x * (GT >> s), exactly, as the sum of x shifted to each set bit b >= s of the constant GT (two terms at
    //: 6,144): no multiplier
    function automatic [AW+PRW-1:0] mul_gt_shr(input [AW-1:0] x, input [3:0] sh);
        integer b;
        reg [AW+PRW-1:0] acc;
        begin
            acc = 0;
            for (b = 0; b < PRW; b = b + 1)
                if (((GT >> b) & 1) != 0 && b >= sh) acc = acc + ({{PRW{1'b0}}, x} << (b - sh));
            mul_gt_shr = acc;
        end
    endfunction
    reg [PRW-1:0]    pr_a;                 // GT >> split
    reg [AW+PRW-1:0] tsg_a, otsg_a;        // ts*(GT>>S), ots*(GT>>S)
    reg [NW-1:0]     kc_a;
    localparam [NW:0]   WNB = W;
    localparam [NW-1:0] ONE = 1, TWO = 2;
    //: three stages (the first use is IL >= 3 cycles after the go): the shifted terms, their kept sum, the result
    localparam integer NB_GT = PRW;
    reg [AW+PRW-1:0] tsh [0:NB_GT-1];
    reg [AW+PRW-1:0] osh [0:NB_GT-1];
    reg [NW:0]       kpad_a;
    always @(posedge clk) begin : p_terms
        integer b;
        for (b = 0; b < NB_GT; b = b + 1) begin
            tsh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ts_r} << (b - split_r)) : {(AW+PRW){1'b0}};
            osh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ots_r} << (b - split_r)) : {(AW+PRW){1'b0}};
        end
        pr_a <= GT >> split_r;
        kpad_a <= {1'b0, ktot_r} + ((1 << split_r) - 1);
    end
    wire [AW+PRW-1:0] tsum, osum;
    wire [NB_GT*(AW+PRW)-1:0] tsh_flat, osh_flat;
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_ts (.rows(tsh_flat), .s(tsum));
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_os (.rows(osh_flat), .s(osum));
    genvar tb;
    for (tb = 0; tb < NB_GT; tb = tb + 1) begin : g_fl
        assign tsh_flat[tb*(AW+PRW) +: AW+PRW] = tsh[tb];
        assign osh_flat[tb*(AW+PRW) +: AW+PRW] = osh[tb];
    end
    always @(posedge clk) begin
        tsg_a <= tsum; otsg_a <= osum;
        kc_a <= wsrc_r ? kpad_a[NW-1:0] >> split_r : ktot_r;       // ceil(K/S) (K + S - 1 < 2^NW)
        tstep_r <= !wsrc_r ? ts_r : tsg_a[AW-1:0];
        ot_step <= otsg_a[AW-1:0];
        nb_step <= pr_a * (W * IL);
        lb_step <= pr_a * W;
        k_r <= kc_a;
    end
    //: loop adds
    wire [AW-1:0] cur_js, oa_j, xc_j, bk_k, xk_k, bt_t, ot_t;
    wire [NW:0]   nb_j, nbt_t, lb_t;
    wire [NW-1:0] k_1, k_2, t_1, t_2;
    ot_qwen_w12_kadd #(.W(AW)) u_a0 (.a(cur), .b(js_r), .s(cur_js));
    ot_qwen_w12_kadd #(.W(AW)) u_a1 (.a(oa), .b(ojs_r), .s(oa_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a2 (.a(xc), .b(xjs_r), .s(xc_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a3 (.a(base_k), .b(ks_r), .s(bk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a4 (.a(xk), .b(xks_r), .s(xk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a5 (.a(base_t), .b(tstep_r), .s(bt_t));
    ot_qwen_w12_kadd #(.W(AW)) u_a6 (.a(ot), .b(ot_step), .s(ot_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a7 (.a(nb), .b(WNB), .s(nb_j));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a8 (.a(nb_t), .b(nb_step), .s(nbt_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a9 (.a(lb), .b(lb_step), .s(lb_t));
    ot_qwen_w12_kadd #(.W(NW)) u_a10 (.a(k), .b(ONE), .s(k_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a11 (.a(k), .b(TWO), .s(k_2));
    ot_qwen_w12_kadd #(.W(NW)) u_a12 (.a(t), .b(ONE), .s(t_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a13 (.a(t), .b(TWO), .s(t_2));
    //: the go's own first-boundary flags, without the K-step divide: ceil(K/S) == 1 <=> K <= S
    wire kc_is_1 = i_wsrc ? ({{(32-NW){1'b0}}, i_k} <= (32'd1 << i_split)) : (i_k == 1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
            split_fault <= 1'b0;
        end else if (pend) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (pcnt == 0) begin pend <= 1'b0; active <= 1'b1; end
            else pcnt <= pcnt - 1'b1;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                if (KV_PREP > 0 && i_wsrc) begin pend <= 1'b1; pcnt <= KV_PREP - 1; end
                else active <= 1'b1;
                if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; ktot_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                rmax_r <= i_rmax; mbase_r <= i_mbase;
                scale_base_r <= (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
                mmode_r <= i_mmode; split_r <= i_split; wcs_r <= i_wcs;
                ts_r <= i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= kc_is_1;
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase;
                nb <= 0; nb_t <= 0;
                lb <= 0;
            end
        end else begin
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa_j; nb <= nb_j; xc <= xc_j;
                if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur_js;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k_1; k_last <= (k_2 == k_r);
                    base_k <= bk_k; cur <= bk_k;
                    xk <= xk_k; xc <= xk_k;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk_base; xc <= xk_base;
                    if (!t_last) begin
                        t <= t_1; t_last <= (t_2 == tiles_r);
                        base_t <= bt_t; base_k <= bt_t; cur <= bt_t;
                        ot <= ot_t; oa <= ot_t;
                        nb_t <= nbt_t; nb <= nbt_t; lb <= lb_t;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end
end endgenerate

    // -- x reads -------------------------------------------------------------------------------------------
    //: accepted go: the edge that latches split_r / xcs_r (pend is never set on the FAST_ISSUE = 0 loop)
    wire go_acc = go && !active && !pend;
    //: x_re: the per-port enable (port < GT/S tiles of chunks) is a function of the op's split only -> latched at the go
    reg [NPX-1:0] xre_en;
    always @(posedge clk)
        if (go_acc)
            for (gi = 0; gi < NPX; gi = gi + 1)
                xre_en[gi] <= (((gb + gi) >> i_split) < (GT >> i_split));
    generate if (XADDR != 0) begin : g_xre
    always @(posedge clk or negedge rst_n) begin
            if (!rst_n) x_re <= 0;
            else if (!active) x_re <= 0;
            else
                for (gi = 0; gi < NX; gi = gi + 1)
                    x_re[gi] <= (gi < NPX) && xre_en[gi];
        end
    end else begin : g_noxre
        always @(*) x_re = '0;
    end endgenerate
    //: descriptor form of the same read (registered on the same edges as x_re / x_addr)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) x_dv <= 1'b0;
        else x_dv <= active;
    end
    always @(posedge clk) begin
        x_dc <= xc;
        if (go_acc) x_dcs <= i_xcs;
    end
    //: x_addr = xc + c * xcs (c = port mod S): c * xcs is constant through the op, latched at the go as the
    //: carry-save pair of its shifted rows (one row per set bit b of the port number, kept when b < split)
    function automatic integer pc_below(input integer v, input integer b);
        integer i;
        begin pc_below = 0; for (i = 0; i < b; i = i + 1) pc_below = pc_below + ((v >> i) & 1); end
    endfunction
    genvar xg, xb;
    generate if (XADDR == 0) begin : g_noxa
        always @(*) x_addr = '0;
    end else begin : g_xaddr
        for (xg = 0; xg < NX; xg = xg + 1) begin : g_xa
            localparam integer NB = pc_below(xg, 16);
            if (xg >= NPX) begin : g_none
                always @(posedge clk) x_addr[xg*AW +: AW] <= {AW{1'b0}};
            end else if (NB == 0) begin : g_zero
                always @(posedge clk) x_addr[xg*AW +: AW] <= xc;
            end else begin : g_off
                wire [NB*AW-1:0] rows;
                for (xb = 0; xb < 16; xb = xb + 1) begin : g_r
                    if ((xg >> xb) & 1) begin : g_set
                        assign rows[pc_below(xg, xb)*AW +: AW] = (xb < i_split) ? (i_xcs << xb) : {AW{1'b0}};
                    end
                end
                wire [AW-1:0] r_s, r_c;
                ot_qwen_w12_csa_tree #(.W(AW), .N(NB)) u_cs (.rows(rows), .s(r_s), .c(r_c));
                reg  [AW-1:0] o_s, o_c;
                always @(posedge clk) if (go_acc) begin o_s <= r_s; o_c <= r_c; end
                wire [AW-1:0] a_s = xc ^ o_s ^ o_c;
                wire [AW-1:0] a_c = ((xc & o_s) | (xc & o_c) | (o_s & o_c)) << 1;
                wire [AW-1:0] a_y;
                ot_qwen_w12_kadd #(.W(AW)) u_ka (.a(a_s), .b(a_c), .s(a_y));
                always @(posedge clk) x_addr[xg*AW +: AW] <= a_y;
            end
        end
    end endgenerate

    // -- element tags (as ot_qwen_w12_matvec_part; no lanes here) -----------------------------------------
    reg          e_v, e_first, e_last, e_oen, e_amax, e_wsrc, e_round, e_mmode;
    reg [3:0]    e_split;
    reg          e_rmax, e_opend;
    reg [2:0]    e_j;
    reg [AW-1:0] e_mbase;
    reg [AW-1:0] e_oa, e_ots;
    reg [NW:0]   e_nb, e_lb, e_rem;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0;
        else e_v <= active;
    end
    reg [NW-1:0] e_t, s1_t, s1b_t, s2_t, s3_t;
    wire [NW-1:0] m_t;
    ot_hdc_delay #(.W(NW), .D(MEM_EXTRA)) u_mtt (.clk(clk), .rst_n(rst_n), .d(e_t), .q(m_t));
    always @(posedge clk) begin e_t <= t; s1_t <= m_t; s1b_t <= s1_t; s2_t <= s1b_t; s3_t <= s2_t; end
    always @(posedge clk) begin
        e_first <= (k == 0); e_last <= k_last;
        e_oen <= oen_r; e_amax <= amax_r; e_wsrc <= wsrc_r; e_round <= round_r; e_mmode <= mmode_r;
        e_split <= split_r; e_oa <= oa; e_ots <= ots_r; e_nb <= nb; e_lb <= lb;
        e_rem <= {1'b0, nout_r};
        e_rmax <= rmax_r; e_j <= j; e_mbase <= mbase_r;
        e_opend <= t_last && k_last && j_last;
    end
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1) + 1 + 3 + 1 + AW + AW;
    wire [TW-1:0] e_tag = {e_last, e_oen, e_amax, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_rem,
                           e_rmax, e_j, e_opend, e_mbase, scale_base_r};
    reg  [TW-1:0] s1_tag, s1b_tag, s2_tag, s3_tag;
    wire [TW-1:0] m_tag;
    wire          m_first, m_wsrc, m_round;
    wire [MEM_EXTRA+2:0] m_vl;
    ot_hdc_vline #(.D(MEM_EXTRA + 2)) u_mv (.clk(clk), .rst_n(rst_n), .v(e_v), .vd(m_vl));
    wire          m_v = m_vl[MEM_EXTRA];
    ot_hdc_delay #(.W(TW + 3), .D(MEM_EXTRA)) u_mt (.clk(clk), .rst_n(rst_n),
        .d({e_tag, e_first, e_wsrc, e_round}), .q({m_tag, m_first, m_wsrc, m_round}));
    reg          s1_v, s1b_v, s2_v, s3_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 0; s1b_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= m_v; s1b_v <= s1_v; s2_v <= s1b_v; s3_v <= s2_v; end
    end
    always @(posedge clk) begin
        s1_tag <= m_tag; s1b_tag <= s1_tag; s2_tag <= s1b_tag; s3_tag <= s2_tag;
    end
    //: a_tag = s3_tag + (SD + OD + XDD); the port elements take it TWO cycles early (a_tag_e2) and register it twice
    localparam integer AD = SD + OD + XDD + RX;
    wire [TW-1:0] a_tag_e2;
    reg  [TW-1:0] a_tag_e1, a_tag;
    ot_qwen_me_rdelay_w12 #(.W(TW), .D(AD - 2), .MEM(RDMEM)) u_tag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(a_tag_e2));
    always @(posedge clk) begin a_tag_e1 <= a_tag_e2; a_tag <= a_tag_e1; end
    wire [AD:0] vline;
    ot_hdc_vline #(.D(AD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    assign p_v_e2 = vline[AD - 2];
    wire          pf_last, pf_oen, pf_amax, pf_wsrc, pf_mmode, pf_rmax, pf_opend;
    wire [3:0]    pf_split;
    wire [AW-1:0] pf_oa, pf_ots, pf_mbase, pf_sbase;
    wire [NW:0]   pf_nb, pf_lb, pf_nout;
    wire [2:0]    pf_j;
    assign {pf_last, pf_oen, pf_amax, pf_wsrc, pf_mmode, pf_split, pf_oa, pf_ots, pf_nb, pf_lb, pf_nout,
            pf_rmax, pf_j, pf_opend, pf_mbase, pf_sbase} = a_tag_e2;
    assign p_f_e2 = {pf_last, pf_oen, pf_wsrc, pf_mmode, pf_split, pf_oa, pf_ots, pf_nb, pf_lb, pf_nout};

    // -- split tree control: level lv's input split (split_at), its select and adder valid ----------------
    //: split_at[lv] at level lv+1's input; sat_e[lv] the same value one cycle earlier
    wire [LG*4+3:0] split_at, sat_e;
    wire [3:0] t_split, t_split_e;
    localparam integer D0 = SD + TL * LV0 + XDD;
    ot_qwen_me_rdelay_w12 #(.W(4), .D(D0 - 1)) u_ts (.clk(clk), .rst_n(rst_n), .d(s3_tag[TW-6 -: 4]), .q(t_split_e));
    reg [3:0] t_split_r;
    always @(posedge clk) t_split_r <= t_split_e;
    assign t_split = t_split_r;
    assign split_at[4*LV0+3 -: 4] = t_split;
    assign sat_e[4*LV0+3 -: 4] = t_split_e;
    genvar lv;
    generate
        for (lv = 0; lv <= LG; lv = lv + 1) begin : g_lctl
            if (lv <= LV0) begin : g_none
                assign t_sel_e[lv] = 1'b0;
                assign t_tv_e[lv] = 1'b0;
            end else begin : g_lvl
                //: sp_sel = split_at[lv-1] + TA (the select when the level's sums emerge); sp_e one cycle earlier
                wire [3:0] sp_e;
                reg  [3:0] sp_sel, sp_out;
                ot_hdc_delay #(.W(4), .D(TA - 1)) u_sd (.clk(clk), .rst_n(rst_n), .d(split_at[4*lv-1 -: 4]), .q(sp_e));
                always @(posedge clk) begin sp_sel <= sp_e; sp_out <= sp_sel; end
                assign split_at[4*lv+3 -: 4] = sp_out;
                assign sat_e[4*lv+3 -: 4] = sp_sel;
                assign t_sel_e[lv] = (sp_e >= lv);
                assign t_tv_e[lv] = vline[SD + TL*(lv-1) + XDD - 1] && (sat_e[4*lv-1 -: 4] >= lv);
            end
        end
    endgenerate

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

    // -- result tag (a_tag + SCALE_LAT, the post-scale multiply) and the result valid ---------------------------------
    wire [TW-1:0] result_tag;
    wire [SCALE_LAT:0] vd;
    ot_qwen_me_rdelay_w12 #(.W(TW), .D(SCALE_LAT)) u_rtag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(result_tag));
    ot_hdc_vline #(.D(SCALE_LAT)) u_rv (.clk(clk), .rst_n(rst_n), .v(vline[AD]), .vd(vd));
    wire [SCALE_LAT:0] post_pending = vd;
    wire          r_v = vd[SCALE_LAT];
    wire          r_last, r_oen, r_amax, r_wsrc, r_mmode;
    wire [3:0]    r_split;
    wire [AW-1:0] r_oa, r_ots;
    wire [NW:0]   r_nb, r_lb, r_nout;
    wire          r_rmax, r_opend;
    wire [2:0]    r_j;
    wire [AW-1:0] r_mbase, r_sbase;
    assign {r_last, r_oen, r_amax, r_wsrc, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout,
            r_rmax, r_j, r_opend, r_mbase, r_sbase} = result_tag;

    // -- fault: the tree elements register their adders' faults (as fault_q[G] here); the port elements
    //: register their multipliers' faults (seen one cycle later than the monolithic engine's)
    reg  fq_t;
    reg  [3:0] range_q;
    reg  range_fault;
    reg  fault_in;
    reg  fault_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fq_t <= 1'b0; fault_r <= 1'b0; fault_in <= 1'b0; range_fault <= 1'b0; end
        else begin
            fault_in <= fab_fault;
            fq_t <= fault_in;
            fault_r <= fq_t | (|tr_fault) | (|p_fault) | split_fault;
            if (go && ready && (i_split > SMAX)) range_fault <= 1'b1;
        end
    end
    assign fault = fault_r | range_fault;

    // -- results: the valid line (the data are the port elements') ---------------------------------------------
    reg ov1, ov2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ov1 <= 1'b0; ov2 <= 1'b0; end
        else begin ov1 <= r_v && r_last; ov2 <= ov1; end
    end
    wire [ORD+2:0] ov_line;
    ot_hdc_vline #(.D(ORD + 2)) u_ovl (.clk(clk), .rst_n(rst_n), .v(ov2), .vd(ov_line));
    generate if (ORD > 0) begin : g_ord
        assign ov = ov_line[ORD];
    end else begin : g_no_ord
        assign ov = ov2;
    end endgenerate

    // -- argmax: levels LPT+1 .. LV over the port elements' level-LPT nodes ---------------------------------
    localparam integer NL = NPG * W;
    localparam integer LV = $clog2(NL);
    localparam integer AN = 1 << LV;
    localparam integer LPT = $clog2(PQ * W);
    localparam integer NPT = NPG / PQ;
    localparam integer CW = 1 + 32 + NW;
    wire [CW*AN-1:0] alv [LPT:LV];
    //: AMI: AMC = the +1 compensation (AMI 1 only; AMI 2 registers p_am without it); LVT = the tree-top valid tap
    localparam integer AMC = (AMI == 1) ? 1 : 0;
    localparam integer LVT = LV + AMC;
    reg  [LVT:0] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 0;
        else tv <= {tv[LVT-1:0], r_v && r_last && (r_amax || r_rmax)};
    end
    wire [1+3+1+AW-1:0] ttag;
    wire [1+3+1+AW-1:0] ttag_ew;     // SC (b): the ring output one edge before ttag (PK)
    wire [31:0] rk_jx;              // SC (b): rk[t_j] (registered under SCB)
    wire        rseen_jx;
    generate if (PK != 0 && LV >= 2) begin : g_ttreg
        // PK: the same LV + 1 edges as a ring of LV and a register, so the mx write stage starts from flops
        wire [1+3+1+AW-1:0] ttag_e;
        ot_qwen_me_rdelay_w12 #(.W(1 + 3 + 1 + AW), .D(LV + AMC), .TREE(((SC & 1) != 0) ? 1 : 0)) u_ttag (.clk(clk), .rst_n(rst_n),
            .d({r_rmax, r_j, r_opend && r_last, r_mbase}), .q(ttag_e));
        reg [1+3+1+AW-1:0] ttag_q;
        always @(posedge clk) ttag_q <= ttag_e;
        assign ttag = ttag_q;
        assign ttag_ew = ttag_e;
    end else begin : g_ttline
        assign ttag_ew = '0;
        ot_qwen_me_rdelay_w12 #(.W(1 + 3 + 1 + AW), .D(LV + 1 + AMC)) u_ttag (.clk(clk), .rst_n(rst_n),
            .d({r_rmax, r_j, r_opend && r_last, r_mbase}), .q(ttag));
    end endgenerate
    wire          t_rmax, t_opend;
    wire [2:0]    t_j;
    wire [AW-1:0] t_mbase;
    assign {t_rmax, t_j, t_opend, t_mbase} = ttag;
    genvar e, al;
    generate
        if (AMI != 0) begin : g_ami
            reg [CW*NPT-1:0] pam_pin;     // AMI: the p_am pin register (datapath, no reset; qualified by tv)
            always @(posedge clk) pam_pin <= p_am;
            assign alv[LPT][CW*NPT-1:0] = pam_pin;
        end else begin : g_amd
            assign alv[LPT][CW*NPT-1:0] = p_am;
        end
        if ((AN >> LPT) > NPT) begin : g_ppad
            assign alv[LPT][CW*AN-1:CW*NPT] = 0;
        end else if (AN > (AN >> LPT)) begin : g_ppad2
            assign alv[LPT][CW*AN-1:CW*(AN >> LPT)] = 0;
        end
        for (al = LPT + 1; al <= LV; al = al + 1) begin : g_alvl
            for (e = 0; e < (AN >> al); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[al-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[al-1][CW*(2*e+1) +: CW];
                //: key0 > key1, or equal keys and row0 < row1  <=>  {key0, ~row0} > {key1, ~row1}: one kept
                //: prefix carry (A > B <=> carry out of A + ~B), not Yosys's rippled > / == / <
                wire          gt, gt_c;
                wire [32+NW-1:0] gt_s;
                ot_qwen_w12_ksa #(.W(32 + NW)) u_gt (.a({x0[CW-2 -: 32], ~x0[NW-1:0]}), .b(~{x1[CW-2 -: 32], ~x1[NW-1:0]}),
                    .cin(1'b0), .s(gt_s), .cout(gt_c));
                assign gt = gt_c;
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || gt);
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[al][CW*e +: CW] = c;
            end
            assign alv[al][CW*AN-1 : CW*(AN >> al)] = 0;
        end
    endgenerate
    wire [CW-1:0] top = alv[LV][CW-1:0];
    wire          top_v = top[CW-1];
    wire [31:0]   top_key = top[CW-2 -: 32];
    wire [31:0]   top_val = top_key[31] ? {1'b0, top_key[30:0]} : ~top_key;
    wire [NW-1:0] top_idx = top[NW-1:0];
    reg [31:0] best_key;
    //: AMR: the accumulator's own copy of the tree top (and its tag / clear), one edge after the tree
    wire [CW-1:0] atop;
    wire          a_tv, a_rmax, a_clr;
    //: the accumulator clear of an amax op at its issue (RXA > 0: RXA edges later, with the results)
    wire am_clr;
    generate if (RXA + AMC > 0) begin : g_amc
        ot_hdc_delay #(.W(1), .D(RXA + AMC), .RESET(1)) u_amc (.clk(clk), .rst_n(rst_n), .d(go && ready && i_amax), .q(am_clr));
    end else begin : g_amc0
        assign am_clr = go && ready && i_amax;
    end endgenerate
    //: top > best (key, then the lower index): the same kept carry as the tree nodes
    wire best_gt;
    wire [32+NW-1:0] best_s;
    generate if (AMR != 0) begin : g_amr
        reg [CW-1:0] atop_q;
        reg          a_tv_q, a_rmax_q, a_clr_q;
        always @(posedge clk) atop_q <= top;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin a_tv_q <= 1'b0; a_rmax_q <= 1'b0; a_clr_q <= 1'b0; end
            else begin a_tv_q <= tv[LVT]; a_rmax_q <= t_rmax; a_clr_q <= am_clr; end
        assign atop = atop_q; assign a_tv = a_tv_q; assign a_rmax = a_rmax_q; assign a_clr = a_clr_q;
    end else begin : g_amw
        assign atop = top; assign a_tv = tv[LVT]; assign a_rmax = t_rmax; assign a_clr = am_clr;
    end endgenerate
    wire          atop_v = atop[CW-1];
    wire [31:0]   atop_key = atop[CW-2 -: 32];
    wire [NW-1:0] atop_idx = atop[NW-1:0];
    wire [31:0]   atop_val = atop_key[31] ? {1'b0, atop_key[30:0]} : ~atop_key;
`ifdef OT_MUT_AMR
    // bench mutant (AMR path only, so the AMR = 0 reference is untouched): the accumulator stores a wrong row index
    wire [NW-1:0] atop_idx_w = atop_idx ^ {{(NW-1){1'b0}}, (AMR != 0) ? 1'b1 : 1'b0};
`else
    wire [NW-1:0] atop_idx_w = atop_idx;
`endif
    ot_qwen_w12_ksa #(.W(32 + NW)) u_bgt (.a({atop_key, ~atop_idx}), .b(~{best_key, ~am_idx}), .cin(1'b0), .s(best_s),
        .cout(best_gt));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            am_any <= 1'b0; am_idx <= 0; am_val <= 0; best_key <= 0;
        end else begin
            if (a_clr) am_any <= 1'b0;
            else if (a_tv && !a_rmax && atop_v && (!am_any || best_gt)) begin
                am_any <= 1'b1; best_key <= atop_key; am_idx <= atop_idx_w; am_val <= atop_val;
            end
        end
    end
    reg [31:0] rk [0:IL-1];
    reg [IL-1:0] rseen;
    integer rj;
    wire [31:0] rk_j = rk_jx;
    wire        rk_ge, rk_c;
    wire [31:0] rk_s;
    //: rk_j >= top_key (carry out of rk_j + ~top_key + 1), kept prefix
    ot_qwen_w12_ksa #(.W(32)) u_rge (.a(rk_j), .b(~top_key), .cin(1'b1), .s(rk_s), .cout(rk_c));
    assign rk_ge = rk_c;
    wire [31:0] nk = (!top_v || (rseen_jx && rk_ge)) ? rk_j : top_key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rseen <= 0; mx_we <= 1'b0;
`ifdef OT_TB_RK_RST
            // bench diagnostic only (el1011-q-seq TXN): clear the per-slot maxima in reset, so an mx write after a reset
            // cannot carry slot values left by an operation the reset aborted
            for (rj = 0; rj < IL; rj = rj + 1) rk[rj] <= 32'd0;
`endif
        end
        else begin
            mx_we <= 1'b0;
            if (tv[LVT] && t_rmax) begin
                if (t_opend) begin
                    mx_we <= 1'b1;
                    rseen <= 0;
                end else if (top_v) begin
                    rk[t_j] <= nk;
                    rseen[t_j] <= 1'b1;
                end
            end
        end
    end
    //: SC (b): the mx write from flops.  The lane rotate ((t_mbase + rj) % W) and the slot test (rj == t_j) are decoded
    //: from the ring output one edge early (registered beside ttag_q); the slot maximum rk[t_j] / rseen[t_j] are
    //: registered one edge early with forwarding of this edge's slot write, so nk no longer waits for a t_j mux.
    localparam integer SCB = ((SC & 1) != 0 && PK != 0 && LV >= 2 && IL <= W) ? 1 : 0;
    generate if (SCB != 0) begin : g_scb
        wire [2:0]    e_j = ttag_ew[AW+1 +: 3];
        wire [LW-1:0] e_mb = ttag_ew[LW-1:0];
        reg  [W*IL-1:0] l_sel;      // lane l holds slot rj
        reg  [W-1:0]    l_j;        // lane l holds slot t_j
        reg  [31:0]     rk_jr;
        reg             rs_jr;
        wire rk_wr = tv[LVT] && t_rmax && !t_opend && top_v;    // this edge's slot write (rk[t_j] <= nk)
        integer ll, jj;
        always @(posedge clk) begin
            for (ll = 0; ll < W; ll = ll + 1) begin
                l_j[ll] <= 1'b0;
                for (jj = 0; jj < IL; jj = jj + 1) begin
                    l_sel[ll*IL + jj] <= (((e_mb + jj) % W) == ll);
                    if ((((e_mb + jj) % W) == ll) && (jj == e_j)) l_j[ll] <= 1'b1;
                end
            end
        end
`ifdef OT_TB_RK_RST
        always @(posedge clk or negedge rst_n) if (!rst_n) rk_jr <= 32'd0; else
`else
        always @(posedge clk)
`endif
            rk_jr <= (rk_wr && (t_j == e_j) && ((SC & 2) == 0)) ? nk : rk[e_j];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rs_jr <= 1'b0;
            else if (tv[LVT] && t_rmax && t_opend) rs_jr <= 1'b0;
            else rs_jr <= (rk_wr && (t_j == e_j) && ((SC & 2) == 0)) ? 1'b1 : rseen[e_j];
        assign rk_jx = rk_jr; assign rseen_jx = rs_jr;
`ifdef OT_SC_COV
        // bench-only coverage (el1011-q-seq SC): slot writes forwarded into the registered slot maximum, mx writes
        integer cov_fwd = 0, cov_mxw = 0, cov_rkw = 0;
        always @(posedge clk) begin
            if (rk_wr && (t_j == e_j)) cov_fwd = cov_fwd + 1;
            if (rk_wr) cov_rkw = cov_rkw + 1;
            if (tv[LVT] && t_rmax && t_opend) cov_mxw = cov_mxw + 1;
        end
        final $display("SC_COV b: rk_writes=%0d fwd=%0d mx_writes=%0d", cov_rkw, cov_fwd, cov_mxw);
`endif
        always @(posedge clk) begin
            if (tv[LVT] && t_rmax && t_opend) begin
                mx_addr <= t_mbase >> LW;
                for (ll = 0; ll < W; ll = ll + 1) begin
                    mx_mask[ll] <= |l_sel[ll*IL +: IL];
                    mx_data[32*ll +: 32] <= 32'd0;
                    for (jj = 0; jj < IL; jj = jj + 1)
                        if (l_sel[ll*IL + jj] && !l_j[ll]) mx_data[32*ll +: 32] <= rk[jj][31] ? {1'b0, rk[jj][30:0]} : ~rk[jj];
                    if (l_j[ll]) mx_data[32*ll +: 32] <= nk[31] ? {1'b0, nk[30:0]} : ~nk;
                end
            end
        end
    end else begin : g_nscb
        assign rk_jx = rk[t_j]; assign rseen_jx = rseen[t_j];
    always @(posedge clk) begin
        if (tv[LVT] && t_rmax && t_opend) begin
            mx_addr <= t_mbase >> LW;
            mx_mask <= {W{1'b0}};
            mx_data <= {(W*32){1'b0}};
            for (rj = 0; rj < IL; rj = rj + 1) begin
                mx_mask[(t_mbase[LW-1:0] + rj) % W] <= 1'b1;
                mx_data[32*((t_mbase[LW-1:0] + rj) % W) +: 32] <=
                    (rj == t_j) ? (nk[31] ? {1'b0, nk[30:0]} : ~nk) : (rk[rj][31] ? {1'b0, rk[rj][30:0]} : ~rk[rj]);
            end
        end
    end
    end endgenerate

    // -- progress, idle (as ot_qwen_w12_matvec_part) ----------------------------------------------------------
    reg [15:0] n_last_issued, n_ov, ov_mark;
    //: LANDED (qwen-vm-me): the result rows reach the banked vector memory through the band serializers and the merge
    //: at a variable time; progress counts the bursts LANDED there (in order, ot_qfd_res_merge land_cnt) and the
    //: element is idle only when every burst it emitted has landed.  0: the base (bursts counted at the ports).
    wire [15:0] ov_done;
    generate if (PK != 0) begin : g_pks
        // a - b = a + ~b + 1 with kept log-depth prefix levels (ABC re-ripples a behavioural subtract)
        wire pk_co;
        ot_hdc_ksadd_k #(.W(16)) u_pks (.a((LANDED != 0) ? land_cnt : n_ov), .b(~ov_mark), .cin((PK == 2) ? 1'b0 : 1'b1),
            .s(ov_done), .cout(pk_co));
    end else begin : g_pkb
        assign ov_done = ((LANDED != 0) ? land_cnt : n_ov) - ov_mark;
    end endgenerate
    wire        land_wait = (LANDED != 0) && (land_cnt != n_ov);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_last_issued <= 0; n_ov <= 0; ov_mark <= 0; progress <= 0;
        end else begin
            n_last_issued <= n_last_issued + ((active && k_last) ? 16'd1 : 16'd0);
            n_ov <= n_ov + (ov ? 16'd1 : 16'd0);
            if (go && ready) begin
                ov_mark <= n_last_issued; progress <= 0;
            end else begin
                progress <= ov_done[15] ? 16'd0 : ov_done;
            end
        end
    end
    localparam [ORD+2:0] OMASK = (1 << (ORD + 1)) - 2;
    wire ord_busy = |(ov_line & OMASK);
    wire idle_c = !active && !pend && !e_v && !(|m_vl) && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|post_pending) && !(|tv) && !ov1
                  && !ov2 && !ord_busy && !mx_we && !land_wait && !((AMR != 0) && a_tv);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(go && ready);
    end

    // -- x network select stage: the split of the element whose x arrives now (ot_qwen_me_spine_w12) -------
    localparam integer NXL = NX / TG;
    reg  [3:0] op_split;
    always @(posedge clk) if (go && ready) op_split <= i_split;
    assign x_dsp = op_split;
    wire [3:0] x_split;
    ot_hdc_delay #(.W(4), .D(2 + XVM)) u_xs (.clk(clk), .rst_n(rst_n), .d(op_split), .q(x_split));
    genvar r, i;
    generate
        for (r = 0; r < NXL; r = r + 1) begin : g_line
            wire [SMAX:0] quads = (1 << x_split) / TG;
            wire [SMAX:0] src = r & (quads - 1);
            for (i = 0; i < TG; i = i + 1) begin : g_e
                always @(posedge clk) xl0[(r*TG + i)*32 +: 32] <= x_q[(src*TG + i)*32 +: 32];
            end
        end
    endgenerate
endmodule
module ot_qwen_w12_ksum #(parameter integer W = 24, parameter integer N = 8) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s
);
    wire [W-1:0] a, b;
    ot_qwen_w12_csa_tree #(.W(W), .N(N)) u_t (.rows(rows), .s(a), .c(b));
    ot_qwen_w12_kadd #(.W(W)) u_a (.a(a), .b(b), .s(s));
endmodule