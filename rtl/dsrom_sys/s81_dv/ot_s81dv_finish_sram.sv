`timescale 1ns/1ps
// Opt-in XFIN SRAM payload successor. Source-bound model18f13c8ce; same operand capture edge.
module ot_s81dv_norm_finish_sram #(
    parameter integer NV = 80,          // global beats (NS slices x NVL)
    parameter integer K  = 5,           // beat partials per flit (NVL)
    parameter integer P  = 3,           // flit input ports (own, from W, from E)
    parameter integer D  = 5120,
    parameter integer LM = 5,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire              go_mem,
    input  wire [P-1:0]      f_v,
    input  wire [P*8-1:0]    f_base,      // global index of the flit's first partial
    input  wire [P*K*32-1:0] f_d,
    input  wire [31:0]       eps,
    output wire              r_v,
    output wire [31:0]       r,
    output wire              fault
);
    // SEQUENCED golden-order finish (gate 10-16: the replicated parallel tree was 58.7k flops on one root).  The tree is
    // ot_dsrom_su_norm's vector-level tree exactly (heap over NVP leaves; a node adds its two children when its right
    // subtree holds a real beat, else it passes its left child), evaluated by ONE pipelined adder with dataflow issue
    // (highest-index ready node first).  Same additions, same operands, same order of association -> bit-identical;
    // arrival times are compiler static, so the issue schedule is fixed (no flow control).
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer HB  = $clog2(NVP);
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer tz(input integer x);
        integer t;
        begin
            t = 0;
            while (t < 31 && ((x >> t) & 1) == 0) t = t + 1;
            tz = t;
        end
    endfunction
    function automatic integer isadd(input integer n);  // the verbatim g_add condition
        integer H;
        begin
            H = HB - ($clog2(n + 1) - 1);
            isadd = (n >= 1 && n < NVP && ((((2 * n + 1) << (H - 1)) - NVP) < NV)) ? 1 : 0;
        end
    endfunction
    localparam integer DK = tz(D);
    localparam integer DF = D >> DK;
    localparam integer NRS = 64;         // reset relay copies (one per 16-node region; gate 10-16: 766 loads on one flop)
    // N32 reset (r7): the former rs[1] (one register driving every control flop of every finish after merging) is
    // replaced by bounded 2-edge leaves of a control forest (same release edge); the arithmetic units take the raw
    // rst_n and build their own 2-edge forests (ot_s81dv_*_n32)
    wire [7:0] rc;
    ot_s81dv_finish_reset2 #(.LEAVES(8)) u_ctl_reset(.clk(clk),.rst_n(rst_n),.q(rc));
    wire [NRS-1:0] rsr;
    ot_s81dv_finish_reset2 #(.LEAVES(NRS)) u_meta_reset(.clk(clk),.rst_n(rst_n),.q(rsr));
    // Leaf-valid clears have distinct same-edge owners from the internal
    // issue/control go forest (actual r7 go_t33..38). go_mem also supplies
    // the read-command owners; its combined capture load remains<=32.
    (* keep *) reg[15:0] leaf_go;
    for(genvar lg=0;lg<16;lg=lg+1)begin:g_leaf_go
      always @(posedge clk or negedge rsr[(lg+16)%NRS])
        if(!rsr[(lg+16)%NRS])leaf_go[lg]<=0;else leaf_go[lg]<=go_mem;
    end
    // NATIVE32 (ELEM-XFV/XFIN 10-21): go_t and the leaf-match inputs are KEPT same-edge copies (census r1: go_t 4965,
    // iv 653, ib 177 loads); every copy is a function-identical register of the original, so no edge moves.
    // N8: NLC 2 = two leaf-match copies (set A: leaves, write enables and data[15:0]; set B: data[31:16])
`ifdef OT_S81DV_XFIN_N12
    // N12 (STW-S81c-COLLA-SLICE 10-22): set A gets one decode copy per bank group (NBGA groups by R) and the finish
    // leaf match keeps its own copy 0 (N11 census: one shared dec bit fed all 15 leaf write ports, max 43 NORM / 102 ENG).
    // Copies: 0 = finish leaf match, 1 = set B, 2..2+NBGA-1 = set A per bank group. Same register edge for every copy.
    localparam integer NBGA = 3;
    localparam integer NGO = 12, NLC = 2 + NBGA, NBK = P * K;
`else
    localparam integer NBGA = 1;
    localparam integer NGO = 12, NLC = 2, NBK = P * K;
`endif
    (* keep *) reg [NGO-1:0] go_t;
    genvar gk;
    generate for (gk = 0; gk < NGO; gk = gk + 1) begin : g_gt
        always @(posedge clk or negedge rc[gk / 8]) if (!rc[gk / 8]) go_t[gk] <= 1'b0; else go_t[gk] <= go;
    end endgenerate
    reg [P-1:0] iv; reg [P*8-1:0] ib; reg [P*K*32-1:0] id; reg [31:0] eps_c;
    always @(posedge clk or negedge rc[4]) if (!rc[4]) iv <= {P{1'b0}}; else iv <= go_t[0] ? {P{1'b0}} : f_v;
    always @(posedge clk) begin ib <= f_base; id <= f_d; eps_c <= eps; end
    (* keep *) reg [NLC*P-1:0] ivl; (* keep *) reg [NLC*P*8-1:0] ibl;   // leaf-match copies, one per IX region
    genvar cl;
    generate for (cl = 0; cl < NLC; cl = cl + 1) begin : g_lc
        always @(posedge clk or negedge rsr[cl % NRS]) if (!rsr[cl % NRS]) ivl[cl*P +: P] <= {P{1'b0}};
            else ivl[cl*P +: P] <= go_t[cl % NGO] ? {P{1'b0}} : f_v;
        always @(posedge clk) ibl[cl*P*8 +: P*8] <= f_base;
    end endgenerate
    // r2: leaf match from a predecoded one-hot per port (nibble decode, <=16 loads per net); N8: the bank write
    // ports read the same one-hots (set A = copy 0, set B = copy 1) instead of per-bank ivb/ibb decode
    wire [NV-1:0] dec [0:P-1];
    wire [NV*P-1:0] ph;
    wire [NBGA*P*NV-1:0] dca;
    wire [P*NV-1:0] dcb;
    generate for (p = 0; p < P; p = p + 1) begin : g_dec
        ot_s81dv_fin_dec #(.N(NV)) u_d (.v(ivl[p]), .b(ibl[p*8 +: 8]), .oh(dec[p]));
        ot_s81dv_fin_dec #(.N(NV)) u_db (.v(ivl[P + p]), .b(ibl[(P + p)*8 +: 8]), .oh(dcb[p*NV +: NV]));
`ifdef OT_S81DV_XFIN_N12
        for (genvar ga = 0; ga < NBGA; ga = ga + 1) begin : g_ga
            (* keep *) ot_s81dv_fin_dec #(.N(NV)) u_da (.v(ivl[(2 + ga) * P + p]), .b(ibl[((2 + ga) * P + p) * 8 +: 8]),
                .oh(dca[(ga * P + p) * NV +: NV]));
        end
`else
        assign dca[p*NV +: NV] = dec[p];
`endif
    end endgenerate
    // ---------------------------------------------------------------- node values: leaves (beats) and add nodes
    wire        VD [1:2*NVP-1];
    wire [NVP-1:0] dup;
    wire        wr_v;                   // adder result write-back
    wire [7:0]  wr_n;
    wire [31:0] wr_d;
    genvar n, p, k;
    generate
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            localparam integer IX = n - NVP;
            if (IX < NV) begin : g_live
                wire [P*K-1:0] m;
                wire [31:0] mv [0:P*K];
                assign mv[0] = 32'd0;
                for (p = 0; p < P; p = p + 1) begin : g_p
                    for (k = 0; k < K; k = k + 1) begin : g_k
`ifdef OT_S81DV_MUT_LEAF
                        // NEGATIVE CONTROL: leaf 1 is fed beat 2's partial (a wrong-operand exchange / tag error).
                        // (A 0/1 swap only commutes one add, and a 1/2 association swap rounded identically on the DS1M
                        // row: order exactness is evidenced by the golden match, operand identity by this control.)
                        localparam integer IXM = (IX == 1) ? 2 : IX;
`else
                        localparam integer IXM = IX;
`endif
                        if (IXM - k >= 0) begin : g_m
                            assign m[p * K + k] = dec[p][IXM - k];
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
                    end
                end
                wire hit = |m;
                for (p = 0; p < P; p = p + 1) begin : g_ph
                    assign ph[IX * P + p] = |m[p * K +: K];
                end
                reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (leaf_go[IX % 16]) vld <= 1'b0; else if (hit) vld <= 1'b1;

                assign dup[IX] = hit && (vld || ((m & (m - 1)) != 0));
                 assign VD[n] = vld;
            end else begin : g_pad
                if (IX < NV) begin : g_np
                    assign ph[IX * P +: P] = {P{1'b0}};
                end
                assign dup[IX] = 1'b0;
                 assign VD[n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg vld;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t[(n + 5) % NGO]) vld <= 1'b0; else if (wr_v && wr_n == n) vld <= 1'b1;

                 assign VD[n] = vld;
            end else begin : g_pass
                 assign VD[n] = VD[2 * n];
            end
        end
    endgenerate
    // ---------------------------------------------------------------- dataflow issue + the one adder
    // Ready add nodes (both children valid, not issued) are selected lowest heap index first in two registered
    // levels (16 groups of 8: in-group one-hot, then the lowest non-empty group), re-masked by `iss` at the second
    // level so a node never issues twice (a stale pick is a bubble).  Any fixed priority is exact: every node still adds
    // its own two golden children exactly once; arrival times are compiler static, so the issue schedule is static.
    localparam integer NG8 = NVP / 8;
    wire [NVP-1:0] rdy, iss_v;
    wire [NVP-1:0] oh1;                 // stage 1: in-group one-hot (lowest ready node of each group)
    wire [NG8-1:0] ga1;                 // stage 1: group has a ready node
    genvar q;
    generate
        for (n = 0; n < NVP; n = n + 1) begin : g_rdy
            if (n >= 1 && isadd(n)) begin : g_a
                reg iss;
                always @(posedge clk or negedge rsr[(n + 3) % NRS])
                    if (!rsr[(n + 3) % NRS]) iss <= 1'b0; else if (go_t[(n + 9) % NGO]) iss <= 1'b0; else if (win[n]) iss <= 1'b1;
                assign iss_v[n] = iss;
                // !go_t moved to the group flag g_r (same cycle): a stale o_r is never selected because its group's
                // ga1 is 0 in the cycle after go_t, and win is gated by go_t at the group (ga1g) below
                assign rdy[n] = VD[2 * n] && VD[2 * n + 1] && !iss;
            end else begin : g_n
                assign iss_v[n] = 1'b1; assign rdy[n] = 1'b0;
            end
        end
        for (q = 0; q < NG8; q = q + 1) begin : g_grp
            wire [7:0] r8 = rdy[q * 8 +: 8];
            wire [7:0] o8 = r8 & ~(r8 - 8'd1);          // lowest set bit (8-bit)
            reg [7:0] o_r; reg g_r;
            always @(posedge clk or negedge rsr[q % NRS])
                if (!rsr[q % NRS]) begin o_r <= 8'd0; g_r <= 1'b0; end
                else begin o_r <= o8; g_r <= (|r8) && !go_t[(q + 2) % NGO]; end
            assign oh1[q * 8 +: 8] = o_r; assign ga1[q] = g_r && !go_t[(q + 7) % NGO];
        end
    endgenerate
    wire [NG8-1:0] gs = ga1 & ~(ga1 - {{(NG8-1){1'b0}}, 1'b1});   // lowest non-empty group (16-bit)
    wire [NVP-1:0] win;
    generate
        for (n = 0; n < NVP; n = n + 1) begin : g_win
            assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n];
        end
    endgenerate
    wire fire = |win;
    wire [7:0]  ot [0:NVP];
    assign ot[0] = 8'd0;
    generate
        for (n = 1; n <= NVP; n = n + 1) begin : g_mux
            if (n < NVP && isadd(n)) begin : g_m


                assign ot[n] = ot[n - 1] | ({8{win[n]}} & n[7:0]);
            end else begin : g_z
                assign ot[n]=ot[n-1];
            end
        end
    endgenerate
    reg f_q; wire [31:0] a_q, b_q; reg [7:0] t_q;      // operand stage (registered: issue mux -> adder)
    always @(posedge clk or negedge rc[4]) if (!rc[4]) f_q <= 1'b0; else f_q <= fire;
    always @(posedge clk) t_q <= ot[NVP];
    function automatic integer mem_group_live(input integer q);
      integer j;
      begin
        mem_group_live=0;
        for(j=0;j<8;j=j+1)if(q*8+j>=1 && isadd(q*8+j))mem_group_live=1;
      end
    endfunction
    function automatic integer mem_group_index(input integer q);
      integer j;
      begin mem_group_index=0;for(j=0;j<q;j=j+1)mem_group_index=mem_group_index+mem_group_live(j);end
    endfunction
    localparam integer MLG=mem_group_index(NVP/8), MREAD=(P*K+2+2)/3;
    // Only retain one-hot captures with a real macro-field consumer.
    // Group validity still captures ALL ready nodes before this filter, so
    // dropping a zero-output node cannot select a different priority winner.
`ifdef OT_S81DV_MUT_LEAF
    localparam [MREAD*NVP-1:0] MEM_NODE_USED=768'h000000fffffffffd000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000fffffffffd000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36;
`else
    localparam [MREAD*NVP-1:0] MEM_NODE_USED=768'h000000fffffffffd000fffff03ff1f36000000fffffffffe000fffff03ff1f36000000fffffffffd000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36;
`endif
    wire[8*NVP-1:0] read_nodes;
    wire[MREAD*MLG*1-1:0] mem_reset;
    ot_s81dv_finish_reset2 #(.LEAVES(MREAD*MLG*1)) u_mem_reset(.clk(clk),.rst_n(rst_n),.q(mem_reset));
    (* keep *) reg[MLG-1:0] mem_go;
    for(genvar mg=0;mg<MLG;mg=mg+1)begin:g_mem_go
      always @(posedge clk or negedge mem_reset[mg])
        if(!mem_reset[mg])mem_go[mg]<=0;else mem_go[mg]<=go_mem;
    end
    // Every kept copy serves an actual bank group and live issue node.
    for(genvar mc=0;mc<MREAD;mc=mc+1)begin:g_mem_command
      wire[NVP-1:0] mo;wire[NG8-1:0] mg;
      for(genvar mq=0;mq<NG8;mq=mq+1)begin:g_group
        localparam integer Q=mq%(NVP/8), GI=mem_group_index(Q);
        if(mem_group_live(Q))begin:g_live
          localparam integer RI=mc*MLG*1+(mq/(NVP/8))*MLG+GI;
          wire[7:0] mr=rdy[mq*8+:8],oh=mr & ~(mr-8'd1);
          (* keep *) reg g;
          always @(posedge clk or negedge mem_reset[RI])
            if(!mem_reset[RI])g<=0;else g<=(|mr) && !mem_go[GI];
          for(genvar mb=0;mb<8;mb=mb+1)begin:g_bit
            if(Q*8+mb>=1 && isadd(Q*8+mb) && MEM_NODE_USED[mc*NVP+mq*8+mb])begin:g_node
              (* keep *) reg o;
              always @(posedge clk or negedge mem_reset[RI])if(!mem_reset[RI])o<=0;else o<=oh[mb];
              assign mo[mq*8+mb]=o;
            end else assign mo[mq*8+mb]=1'b0;
          end
          assign mg[mq]=g && !mem_go[GI];
        end else begin:g_empty
          assign mo[mq*8+:8]=8'd0;assign mg[mq]=1'b0;
        end
      end
      wire[NG8-1:0] ms=mg & ~(mg-1'b1);
      wire[NVP-1:0] mw;
      for(genvar mn=0;mn<NVP;mn=mn+1)begin:g_node
        assign mw[mn]=mo[mn] && ms[mn/8] && !iss_v[mn];
      end
      assign read_nodes[mc*NVP+:NVP]=mw;
    end
    for(genvar mc=MREAD;mc<8;mc=mc+1)begin:g_unused_command
      assign read_nodes[mc*NVP+:NVP]='0;
    end
    ot_s81dv_finish_banks #(.NV(NV),.K(K),.P(P),.TREES(1),.NBG(NBGA)) u_values(
      .clk(clk),.dca(dca),.dcb(dcb),.ph(ph),.id(id),.fire(fire),.issue_tag({1'b0,ot[NVP]}),
      .read_nodes(read_nodes),.rd_active(f_q),.a_q(a_q),.b_q(b_q),.wr_v(wr_v),.wr_tag({1'b0,wr_n}),.wr_d(wr_d));
    wire [LAV:0] av;
    wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rc[5]), .v(f_q), .vd(av));
    ot_s81dv_qadd_n32 #(.LAT(LAV)) u_a (clk, rst_n, f_q, a_q, b_q, wr_d, f_add);
    ot_hdc_delay #(.W(8), .D(LAV)) u_t (.clk(clk), .rst_n(rc[6]), .d(t_q), .q(wr_n));
    assign wr_v = av[LAV];
    // ---------------------------------------------------------------- tail: / D, + eps, rsqrt (ot_dsrom_su_norm)
    reg ssr_v; reg [31:0] ssr;
    always @(posedge clk or negedge rc[6]) if (!rc[6]) ssr_v <= 1'b0; else ssr_v <= wr_v && wr_n == 8'd1 && !go_t[1 % NGO];
    always @(posedge clk) ssr <= wr_d;
    wire [31:0] mq, me, rr;
    wire        mq_v, me_v, rr_v, f_div, f_eps, f_rsq;
    ot_s81dv_divc_n32 #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rst_n), .v(ssr_v), .x(ssr), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rc[7]), .v(mq_v), .vd(ve));
    // N8: the eps sum's KEPT copy mek feeds the rsqrt seed path (census R33: me drove m_half + seed, 34-39 loads)
    wire [31:0] mek;
    ot_s81dv_qadd_n32 #(.LAT(LA), .NYC(1)) u_eps (.clk(clk), .rst_n(rst_n), .v(mq_v), .a(mq), .b(eps_c), .y(me), .fault(f_eps),
        .yc(mek));
    assign me_v = ve[LA];
    ot_s81dv_rsqrt_n32 #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rst_n), .v(me_v), .x(me), .xk(mek), .y(rr), .vo(rr_v), .fault(f_rsq));
    reg r_v_o; reg [31:0] r_o; reg flt;
    always @(posedge clk or negedge rc[7])
        if (!rc[7]) begin r_v_o <= 1'b0; flt <= 1'b0; end
        else begin
            r_v_o <= rr_v;
            if (go_t[2 % NGO]) flt <= 1'b0;
            else if (f_add || f_div || f_eps || f_rsq || (|dup)) flt <= 1'b1;
        end
    always @(posedge clk) r_o <= rr;
    assign r_v = r_v_o; assign r = r_o; assign fault = flt;
endmodule

module ot_s81dv_eng_finish_sram #(
    parameter integer NV = 80,
    parameter integer K  = 5,
    parameter integer P  = 3,
    parameter integer LA = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire              go_mem,
    input  wire              go_mem2,     // N8: second same-edge copy of go_mem (mem_go owners of trees 1, 2)
    input  wire [P-1:0]      f_v,
    input  wire [P*2-1:0]    f_t,         // tree (0 hh, 1 kk, 2 dd)
    input  wire [P*8-1:0]    f_base,      // global index of the flit's first partial
    input  wire [P*K*32-1:0] f_d,
    output reg               r_v,         // one pulse when all three roots are final
    output reg  [31:0]       r_hh, r_kk, r_dd,
    output wire              fault,
    output wire [24:0]       r_vk         // N32: 12 byte capture/select owners + 13 pending owners
);
    localparam integer T   = 3;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer HB  = $clog2(NVP);
    localparam integer NC  = T * NVP;   // issue candidates (tree-major)
    localparam integer CW  = $clog2(NC);
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer isadd(input integer n);
        integer H;
        begin
            H = HB - ($clog2(n + 1) - 1);
            isadd = (n >= 1 && n < NVP && ((((2 * n + 1) << (H - 1)) - NVP) < NV)) ? 1 : 0;
        end
    endfunction
    function automatic integer ca(input integer n);     // left operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            ca = (n == 4) ? 8 : (n == 5) ? 9 : 2 * n;
`else
            ca = 2 * n;
`endif
        end
    endfunction
    function automatic integer cb(input integer n);     // right operand node
        begin
`ifdef OT_S81DV_MUT_EASSOC
            cb = (n == 4) ? 10 : (n == 5) ? 11 : 2 * n + 1;
`else
            cb = 2 * n + 1;
`endif
        end
    endfunction
    localparam integer NRS = 64;
    // N32 reset (r7): the former rs[1] (one register driving every control flop of every finish after merging) is
    // replaced by bounded 2-edge leaves of a control forest (same release edge); the arithmetic units take the raw
    // rst_n and build their own 2-edge forests (ot_s81dv_*_n32)
    wire [7:0] rc;
    ot_s81dv_finish_reset2 #(.LEAVES(8)) u_ctl_reset(.clk(clk),.rst_n(rst_n),.q(rc));
    wire [NRS-1:0] rsr;
    ot_s81dv_finish_reset2 #(.LEAVES(NRS)) u_meta_reset(.clk(clk),.rst_n(rst_n),.q(rsr));
    // Leaf-valid clears have distinct same-edge owners from the internal
    // issue/control go forest (actual r7 go_t33..38). go_mem also supplies
    // the read-command owners; its combined capture load remains<=32.
    (* keep *) reg[15:0] leaf_go;
    for(genvar lg=0;lg<16;lg=lg+1)begin:g_leaf_go
      always @(posedge clk or negedge rsr[(lg+16)%NRS])
        if(!rsr[(lg+16)%NRS])leaf_go[lg]<=0;else leaf_go[lg]<=go_mem;
    end
    // NATIVE32 (ELEM-XFV/XFIN 10-21): kept same-edge copies of go_t (census r1 4965 loads) and of the leaf-match
    // inputs iv/it/ib (59/92/120); function-identical registers, no edge moves.
    // NLC: one leaf-match copy per tree, twice (N8: set A copies 0..2 = leaves, write enables, data[15:0];
    // set B copies 3..5 = data[31:16])
`ifdef OT_S81DV_XFIN_N12
    // N12: copies t = finish leaf match (tree t), T+t = set B, 2T+ga*T+t = set A for bank group ga (NBGA groups by R).
    localparam integer NBGA = 3;
    localparam integer NGO = 32, NLC = 6 + 3 * NBGA, NBK = P * K;
`else
    localparam integer NBGA = 1;
    localparam integer NGO = 32, NLC = 6, NBK = P * K;
`endif
    (* keep *) reg [NGO-1:0] go_t;
    genvar gk;
    generate for (gk = 0; gk < NGO; gk = gk + 1) begin : g_gt
        always @(posedge clk or negedge rc[gk / 8]) if (!rc[gk / 8]) go_t[gk] <= 1'b0; else go_t[gk] <= go;
    end endgenerate
    reg [P-1:0] iv; reg [P*2-1:0] it; reg [P*8-1:0] ib; reg [P*K*32-1:0] id;
    always @(posedge clk or negedge rc[4]) if (!rc[4]) iv <= {P{1'b0}}; else iv <= go_t[0] ? {P{1'b0}} : f_v;
    always @(posedge clk) begin it <= f_t; ib <= f_base; id <= f_d; end
    (* keep *) reg [NLC*P-1:0] ivl; (* keep *) reg [NLC*P*2-1:0] itl; (* keep *) reg [NLC*P*8-1:0] ibl;
    genvar cl;
    generate for (cl = 0; cl < NLC; cl = cl + 1) begin : g_lc
        always @(posedge clk or negedge rsr[cl % NRS]) if (!rsr[cl % NRS]) ivl[cl*P +: P] <= {P{1'b0}};
            else ivl[cl*P +: P] <= go_t[cl % NGO] ? {P{1'b0}} : f_v;
        always @(posedge clk) begin itl[cl*P*2 +: P*2] <= f_t; ibl[cl*P*8 +: P*8] <= f_base; end
    end endgenerate
    // leaf match: per (tree, port) predecoded one-hot of the flit base, valid = iv && it == tree (copy = tree)
    wire [NV-1:0] dec [0:T*P-1];
    wire [T*NV*P-1:0] ph;
    wire [NBGA*T*P*NV-1:0] dca;
    wire [T*P*NV-1:0] dcb;
    wire        wr_v;
    wire [CW-1:0] wr_n;
    wire [31:0] wr_d;
    wire [NC-1:0] rdy, iss_v, win;
    wire [T*NVP-1:0] dup;
    wire        VD [0:T-1][1:2*NVP-1];
    genvar t, n, p, k;
    generate for (t = 0; t < T; t = t + 1) begin : g_t
        for (p = 0; p < P; p = p + 1) begin : g_dec
            ot_s81dv_fin_dec #(.N(NV)) u_d (.v(ivl[t * P + p] && itl[t * P * 2 + p * 2 +: 2] == t),
                .b(ibl[t * P * 8 + p * 8 +: 8]), .oh(dec[t * P + p]));
            ot_s81dv_fin_dec #(.N(NV)) u_db (.v(ivl[(T + t) * P + p] && itl[(T + t) * P * 2 + p * 2 +: 2] == t),
                .b(ibl[(T + t) * P * 8 + p * 8 +: 8]), .oh(dcb[(t * P + p) * NV +: NV]));
`ifdef OT_S81DV_XFIN_N12
            for (genvar ga = 0; ga < NBGA; ga = ga + 1) begin : g_ga
                localparam integer CA = 2 * T + ga * T + t;
                (* keep *) ot_s81dv_fin_dec #(.N(NV)) u_da (.v(ivl[CA * P + p] && itl[CA * P * 2 + p * 2 +: 2] == t),
                    .b(ibl[CA * P * 8 + p * 8 +: 8]), .oh(dca[((ga * T + t) * P + p) * NV +: NV]));
            end
`else
            assign dca[(t * P + p) * NV +: NV] = dec[t * P + p];
`endif
        end
        for (n = NVP; n < 2 * NVP; n = n + 1) begin : g_leaf
            localparam integer IX = n - NVP;
            if (IX < NV) begin : g_live
                wire [P*K-1:0] m;
                wire [31:0] mv [0:P*K];
                assign mv[0] = 32'd0;
                for (p = 0; p < P; p = p + 1) begin : g_p
                    for (k = 0; k < K; k = k + 1) begin : g_k
                        // ENG flit bases are sid * K by construction (xfin fb), so leaf IX is only ever slot IX % K:
                        // the other slots are not wired (3:1 leaf mux instead of 15:1)
                        if (k == IX % K) begin : g_m
                            assign m[p * K + k] = dec[t * P + p][IX - k];
                        end else begin : g_n
                            assign m[p * K + k] = 1'b0;
                        end
                        assign mv[p * K + k + 1] = mv[p * K + k] | ({32{m[p * K + k]}} & id[(p * K + k) * 32 +: 32]);
                    end
                end
                wire hit = |m;
                for (p = 0; p < P; p = p + 1) begin : g_ph
                    assign ph[(t * NV + IX) * P + p] = |m[p * K +: K];
                end
                reg vld;
                always @(posedge clk or negedge rsr[IX % NRS])
                    if (!rsr[IX % NRS]) vld <= 1'b0; else if (leaf_go[(t * NV + IX) % 16]) vld <= 1'b0; else if (hit) vld <= 1'b1;

                assign dup[t * NVP + IX] = hit && (vld || ((m & (m - 1)) != 0));
                 assign VD[t][n] = vld;
            end else begin : g_pad
                if (IX < NV) begin : g_np
                    assign ph[(t * NV + IX) * P +: P] = {P{1'b0}};
                end
                assign dup[t * NVP + IX] = 1'b0;
                 assign VD[t][n] = 1'b0;
            end
        end
        for (n = 1; n < NVP; n = n + 1) begin : g_node
            if (isadd(n)) begin : g_add
                reg vld;
                always @(posedge clk or negedge rsr[n % NRS])
                    if (!rsr[n % NRS]) vld <= 1'b0; else if (go_t[(t * NVP + n + 11) % NGO]) vld <= 1'b0;
                    else if (wr_v && wr_n == t * NVP + n) vld <= 1'b1;

                 assign VD[t][n] = vld;
            end else begin : g_pass
                 assign VD[t][n] = VD[t][2 * n];
            end
        end
        for (n = 0; n < NVP; n = n + 1) begin : g_rdy
            if (n >= 1 && isadd(n)) begin : g_a
                reg iss;
                always @(posedge clk or negedge rsr[(n + 3) % NRS])
                    if (!rsr[(n + 3) % NRS]) iss <= 1'b0; else if (go_t[(t * NVP + n + 21) % NGO]) iss <= 1'b0;
                    else if (win[t * NVP + n]) iss <= 1'b1;
                assign iss_v[t * NVP + n] = iss;
                assign rdy[t * NVP + n] = VD[t][ca(n)] && VD[t][cb(n)] && !iss;   // !go_t at the group (g_r / ga1)
            end else begin : g_n
                assign iss_v[t * NVP + n] = 1'b1; assign rdy[t * NVP + n] = 1'b0;
            end
        end
    end endgenerate
    // two-level registered priority issue (as ot_s81dv_norm_finish): 8-node groups, then the lowest non-empty group
    localparam integer NG8 = NC / 8;
    wire [NC-1:0] oh1; wire [NG8-1:0] ga1;
    genvar q;
    generate for (q = 0; q < NG8; q = q + 1) begin : g_grp
        wire [7:0] r8 = rdy[q * 8 +: 8];
        wire [7:0] o8 = r8 & ~(r8 - 8'd1);
        reg [7:0] o_r; reg g_r;
        always @(posedge clk or negedge rsr[q % NRS])
            if (!rsr[q % NRS]) begin o_r <= 8'd0; g_r <= 1'b0; end
            else begin o_r <= o8; g_r <= (|r8) && !go_t[(q + 3) % NGO]; end
        assign oh1[q * 8 +: 8] = o_r; assign ga1[q] = g_r && !go_t[(q + 17) % NGO];
    end endgenerate
    wire [NG8-1:0] gs = ga1 & ~(ga1 - {{(NG8-1){1'b0}}, 1'b1});
    generate for (n = 0; n < NC; n = n + 1) begin : g_win
        assign win[n] = oh1[n] && gs[n / 8] && !iss_v[n];
    end endgenerate
    wire fire = |win;
    wire [CW-1:0] ot [0:NC];
    assign ot[0] = {CW{1'b0}};
    generate for (t = 0; t < T; t = t + 1) begin : g_mt
        for (n = 0; n < NVP; n = n + 1) begin : g_mux
            localparam integer C = t * NVP + n;
            if (n >= 1 && isadd(n)) begin : g_m


                assign ot[C + 1] = ot[C] | ({CW{win[C]}} & C[CW-1:0]);
            end else begin : g_z
                assign ot[C+1]=ot[C];
            end
        end
    end endgenerate
    reg f_q; wire [31:0] a_q, b_q; reg [CW-1:0] t_q;
    always @(posedge clk or negedge rc[4]) if (!rc[4]) f_q <= 1'b0; else f_q <= fire;
    always @(posedge clk) t_q <= ot[NC];
    function automatic integer mem_group_live(input integer q);
      integer j;
      begin
        mem_group_live=0;
        for(j=0;j<8;j=j+1)if(q*8+j>=1 && isadd(q*8+j))mem_group_live=1;
      end
    endfunction
    function automatic integer mem_group_index(input integer q);
      integer j;
      begin mem_group_index=0;for(j=0;j<q;j=j+1)mem_group_index=mem_group_index+mem_group_live(j);end
    endfunction
    localparam integer MLG=mem_group_index(NVP/8), MREAD=(P*K+4+2)/3;
    // Only retain one-hot captures with a real macro-field consumer.
    // Group validity still captures ALL ready nodes before this filter, so
    // dropping a zero-output node cannot select a different priority winner.
`ifdef OT_S81DV_MUT_EASSOC
    localparam [MREAD*NC-1:0] MEM_NODE_USED=2688'h000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000fffffffffe000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000fffffffffe000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000fffffffffd000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000ffffffffff000fffff03ff1f36;
`else
    localparam [MREAD*NC-1:0] MEM_NODE_USED=2688'h000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000fffffffffe000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000fffffffffe000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000fffffffffd000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffff03ff1f36000000ffffffffff000fffbf03ff1f36000000ffffffffff000fffff03ff1f36;
`endif
    wire[8*NC-1:0] read_nodes;
    wire[MREAD*MLG*3-1:0] mem_reset;
    ot_s81dv_finish_reset2 #(.LEAVES(MREAD*MLG*3)) u_mem_reset(.clk(clk),.rst_n(rst_n),.q(mem_reset));
    // N8: one KEPT same-edge mem_go owner per (group, tree) (census R33: one owner gated 7 commands x 3 trees, 70
    // loads); tree 0 owners from go_mem, trees 1 and 2 from the equal pin copy go_mem2
    (* keep *) reg[MLG*T-1:0] mem_go;
    for(genvar mg=0;mg<MLG*T;mg=mg+1)begin:g_mem_go
      always @(posedge clk or negedge mem_reset[mg])
        if(!mem_reset[mg])mem_go[mg]<=0;else mem_go[mg]<=(mg<MLG)?go_mem:go_mem2;
    end
    // Every kept copy serves an actual bank group and live issue node.
    for(genvar mc=0;mc<MREAD;mc=mc+1)begin:g_mem_command
      wire[NC-1:0] mo;wire[NG8-1:0] mg;
      for(genvar mq=0;mq<NG8;mq=mq+1)begin:g_group
        localparam integer Q=mq%(NVP/8), GI=mem_group_index(Q);
        if(mem_group_live(Q))begin:g_live
          localparam integer RI=mc*MLG*3+(mq/(NVP/8))*MLG+GI;
          wire[7:0] mr=rdy[mq*8+:8],oh=mr & ~(mr-8'd1);
          (* keep *) reg g;
          always @(posedge clk or negedge mem_reset[RI])
            if(!mem_reset[RI])g<=0;else g<=(|mr) && !mem_go[(mq/(NVP/8))*MLG+GI];
          for(genvar mb=0;mb<8;mb=mb+1)begin:g_bit
            if(Q*8+mb>=1 && isadd(Q*8+mb) && MEM_NODE_USED[mc*NC+mq*8+mb])begin:g_node
              (* keep *) reg o;
              always @(posedge clk or negedge mem_reset[RI])if(!mem_reset[RI])o<=0;else o<=oh[mb];
              assign mo[mq*8+mb]=o;
            end else assign mo[mq*8+mb]=1'b0;
          end
          assign mg[mq]=g && !mem_go[(mq/(NVP/8))*MLG+GI];
        end else begin:g_empty
          assign mo[mq*8+:8]=8'd0;assign mg[mq]=1'b0;
        end
      end
      wire[NG8-1:0] ms=mg & ~(mg-1'b1);
      wire[NC-1:0] mw;
      for(genvar mn=0;mn<NC;mn=mn+1)begin:g_node
        assign mw[mn]=mo[mn] && ms[mn/8] && !iss_v[mn];
      end
      assign read_nodes[mc*NC+:NC]=mw;
    end
    for(genvar mc=MREAD;mc<8;mc=mc+1)begin:g_unused_command
      assign read_nodes[mc*NC+:NC]='0;
    end
    ot_s81dv_finish_banks #(.NV(NV),.K(K),.P(P),.TREES(3),.NBG(NBGA)) u_values(
      .clk(clk),.dca(dca),.dcb(dcb),.ph(ph),.id(id),.fire(fire),.issue_tag(ot[NC]),
      .read_nodes(read_nodes),.rd_active(f_q),.a_q(a_q),.b_q(b_q),.wr_v(wr_v),.wr_tag(wr_n),.wr_d(wr_d));
    wire [LAV:0] av; wire f_add;
    ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rc[5]), .v(f_q), .vd(av));
    ot_s81dv_qadd_n32 #(.LAT(LAV)) u_a (clk, rst_n, f_q, a_q, b_q, wr_d, f_add);
    ot_hdc_delay #(.W(CW), .D(LAV)) u_t (.clk(clk), .rst_n(rc[6]), .d(t_q), .q(wr_n));
    assign wr_v = av[LAV];
    // roots: node 1 of each tree
    reg [T-1:0] dn; reg flt;
    always @(posedge clk or negedge rc[7])
        if (!rc[7]) begin dn <= {T{1'b0}}; r_v <= 1'b0; flt <= 1'b0; end
        else begin
            r_v <= 1'b0;
            if (go_t[1]) begin dn <= {T{1'b0}}; flt <= 1'b0; end
            else begin
                if (wr_v && wr_n == 1 * 1)           dn[0] <= 1'b1;
                if (wr_v && wr_n == NVP + 1)         dn[1] <= 1'b1;
                if (wr_v && wr_n == 2 * NVP + 1)     dn[2] <= 1'b1;
                if (dn != {T{1'b1}} && (dn | {wr_v && wr_n == 2 * NVP + 1, wr_v && wr_n == NVP + 1, wr_v && wr_n == 1})
                    == {T{1'b1}}) r_v <= 1'b1;
                if (f_add || (|dup)) flt <= 1'b1;
            end
        end
    // r_vk: same next state as r_v (reset 0; go_t[1] clears; set on the completing root write)
    (* keep *) reg [24:0] rvk;
    for(genvar vg=0;vg<25;vg=vg+1)begin:g_result_pulse
      always @(posedge clk or negedge rc[6])
        if (!rc[6]) rvk[vg] <= 1'b0;
        else if (go_t[(vg+1)%NGO]) rvk[vg] <= 1'b0;
        else rvk[vg] <= dn != {T{1'b1}} && (dn | {wr_v && wr_n == 2 * NVP + 1, wr_v && wr_n == NVP + 1, wr_v && wr_n == 1})
                        == {T{1'b1}};
    end
    assign r_vk = rvk;
    // N8 root capture: per (root, byte) KEPT reset lines of the issue-stage root hit (f_q && t_q == root), LAV deep
    // like av / u_t, so rwl[r][b] == (wr_v && wr_n == root r) on every cycle (both 0 after reset); each enables 8 bits
    // (census R33: one root enable drove 32 capture muxes, 64-73 loads)
    wire [11:0] rwl;
`ifdef OT_S81DV_XFIN_N10
    wire[11:0] rwl_reset;
    ot_s81dv_finish_reset2 #(.LEAVES(12))u_root_capture_reset(.clk(clk),.rst_n(rst_n),.q(rwl_reset));
`endif
    genvar rr, rb;
    for (rr = 0; rr < T; rr = rr + 1) begin : g_root
        wire hit0 = f_q && t_q == rr * NVP + 1;
        for (rb = 0; rb < 4; rb = rb + 1) begin : g_b
            (* keep *) reg [LAV-1:0] l;
`ifdef OT_S81DV_XFIN_N10
            wire local_reset=rwl_reset[rr*4+rb];
            always @(posedge clk or negedge local_reset) if (!local_reset) l <= {LAV{1'b0}}; else l <= {l[LAV-2:0],hit0};
`else
            always @(posedge clk or negedge rc[5]) if (!rc[5]) l <= {LAV{1'b0}}; else l <= {l[LAV-2:0], hit0};
`endif
            assign rwl[rr * 4 + rb] = l[LAV-1];
        end
    end
    integer ry;
    always @(posedge clk)
        for (ry = 0; ry < 4; ry = ry + 1) begin
            if (rwl[ry])     r_hh[8*ry +: 8] <= wr_d[8*ry +: 8];
            if (rwl[4 + ry]) r_kk[8*ry +: 8] <= wr_d[8*ry +: 8];
            if (rwl[8 + ry]) r_dd[8*ry +: 8] <= wr_d[8*ry +: 8];
        end
    assign fault = flt;
endmodule
module ot_s81dv_finish_banks #(parameter integer NV=80,K=5,P=3,TREES=1,NVP=(1<<$clog2(NV)),NBG=1)(
 // N8 (STW-S81-COLLA-XFIN 10-21): the leaf write ports select from the finish's two predecoded one-hot flit base
 // sets dca/dcb ([t][p][x] = valid && tree == t && base == x, x < NV; one per payload half) instead of per-bank
 // subtract/compare decode of ivb/itb/ibb copies (census R33: 132-load ibb, 103-load payload nodes). Same values,
 // same edge. ph = the finish's per-port leaf hits (owner update).
 // N12: dca carries NBG same-value copies of set A; leaf bank with R = bank%K reads copy (R*NBG)/K.
 input wire clk,input wire[NBG*TREES*P*NV-1:0] dca,input wire[TREES*P*NV-1:0] dcb,
 input wire[TREES*NV*P-1:0] ph,input wire[P*K*32-1:0] id,
 input wire fire,input wire[8:0] issue_tag,input wire[8*TREES*NVP-1:0] read_nodes,input wire rd_active,output reg[31:0] a_q,b_q,
 input wire wr_v,input wire[8:0] wr_tag,input wire[31:0] wr_d
);
 localparam integer RM=(TREES==3)?2:1,NB=P*K+2*RM,NREAD=(NB+2)/3,NOWNER=(P*K+8)/9;
 localparam integer MUT_ASSOC=`ifdef OT_S81DV_MUT_EASSOC (TREES==3) `else 0 `endif;
 if(NV!=80 || K!=5 || P!=3 || (TREES!=1 && TREES!=3))begin:g_bad_profile
  ot_s81dv_finish_SRAM_requires_NV80_K5_P3_T1or3 u_bad();
 end
 reg[1:0] owner[0:TREES*NV-1];
 (* keep *) reg[1:0] owner_read[0:NOWNER*TREES*NV-1];
 // Each three-descriptor owner region owns a same-edge copy of the selected flit
 // owner, so retaining bank-local decode cannot move load onto owner flops.
 for(genvar t=0;t<TREES;t=t+1)begin:g_ot
  for(genvar ix=0;ix<NV;ix=ix+1)begin:g_ox
   wire[P-1:0] e=ph[(t*NV+ix)*P+:P];
   always @(posedge clk)begin
    if(e[0])owner[t*NV+ix]<=2'd0; else if(e[1])owner[t*NV+ix]<=2'd1; else if(e[2])owner[t*NV+ix]<=2'd2;
   end
   for(genvar c=0;c<NOWNER;c=c+1)begin:g_copy
    always @(posedge clk)begin
      if(e[0])owner_read[(c*TREES+t)*NV+ix]<=2'd0;
      else if(e[1])owner_read[(c*TREES+t)*NV+ix]<=2'd1;
      else if(e[2])owner_read[(c*TREES+t)*NV+ix]<=2'd2;
    end
   end
  end
 end
    function automatic [7:0] ca_node(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd1: ca_node=8'd2;
            8'd2: ca_node=8'd4;
            8'd4: ca_node=8'd8;
            8'd5: ca_node=8'd9;
            8'd8: ca_node=8'd16;
            8'd9: ca_node=8'd18;
            8'd10: ca_node=8'd20;
            8'd11: ca_node=8'd22;
            8'd12: ca_node=8'd24;
            8'd16: ca_node=8'd32;
            8'd17: ca_node=8'd34;
            8'd18: ca_node=8'd36;
            8'd19: ca_node=8'd38;
            8'd20: ca_node=8'd40;
            8'd21: ca_node=8'd42;
            8'd22: ca_node=8'd44;
            8'd23: ca_node=8'd46;
            8'd24: ca_node=8'd48;
            8'd25: ca_node=8'd50;
            8'd32: ca_node=8'd64;
            8'd33: ca_node=8'd66;
            8'd34: ca_node=8'd68;
            8'd35: ca_node=8'd70;
            8'd36: ca_node=8'd72;
            8'd37: ca_node=8'd74;
            8'd38: ca_node=8'd76;
            8'd39: ca_node=8'd78;
            8'd40: ca_node=8'd80;
            8'd41: ca_node=8'd82;
            8'd42: ca_node=8'd84;
            8'd43: ca_node=8'd86;
            8'd44: ca_node=8'd88;
            8'd45: ca_node=8'd90;
            8'd46: ca_node=8'd92;
            8'd47: ca_node=8'd94;
            8'd48: ca_node=8'd96;
            8'd49: ca_node=8'd98;
            8'd50: ca_node=8'd100;
            8'd51: ca_node=8'd102;
            8'd64: ca_node=8'd128;
            8'd65: ca_node=8'd130;
            8'd66: ca_node=8'd132;
            8'd67: ca_node=8'd134;
            8'd68: ca_node=8'd136;
            8'd69: ca_node=8'd138;
            8'd70: ca_node=8'd140;
            8'd71: ca_node=8'd142;
            8'd72: ca_node=8'd144;
            8'd73: ca_node=8'd146;
            8'd74: ca_node=8'd148;
            8'd75: ca_node=8'd150;
            8'd76: ca_node=8'd152;
            8'd77: ca_node=8'd154;
            8'd78: ca_node=8'd156;
            8'd79: ca_node=8'd158;
            8'd80: ca_node=8'd160;
            8'd81: ca_node=8'd162;
            8'd82: ca_node=8'd164;
            8'd83: ca_node=8'd166;
            8'd84: ca_node=8'd168;
            8'd85: ca_node=8'd170;
            8'd86: ca_node=8'd172;
            8'd87: ca_node=8'd174;
            8'd88: ca_node=8'd176;
            8'd89: ca_node=8'd178;
            8'd90: ca_node=8'd180;
            8'd91: ca_node=8'd182;
            8'd92: ca_node=8'd184;
            8'd93: ca_node=8'd186;
            8'd94: ca_node=8'd188;
            8'd95: ca_node=8'd190;
            8'd96: ca_node=8'd192;
            8'd97: ca_node=8'd194;
            8'd98: ca_node=8'd196;
            8'd99: ca_node=8'd198;
            8'd100: ca_node=8'd200;
            8'd101: ca_node=8'd202;
            8'd102: ca_node=8'd204;
            8'd103: ca_node=8'd206;
            default: ca_node=8'd0;
          endcase
        end else begin
          case(n)
            8'd1: ca_node=8'd2;
            8'd2: ca_node=8'd4;
            8'd4: ca_node=8'd8;
            8'd5: ca_node=8'd10;
            8'd8: ca_node=8'd16;
            8'd9: ca_node=8'd18;
            8'd10: ca_node=8'd20;
            8'd11: ca_node=8'd22;
            8'd12: ca_node=8'd24;
            8'd16: ca_node=8'd32;
            8'd17: ca_node=8'd34;
            8'd18: ca_node=8'd36;
            8'd19: ca_node=8'd38;
            8'd20: ca_node=8'd40;
            8'd21: ca_node=8'd42;
            8'd22: ca_node=8'd44;
            8'd23: ca_node=8'd46;
            8'd24: ca_node=8'd48;
            8'd25: ca_node=8'd50;
            8'd32: ca_node=8'd64;
            8'd33: ca_node=8'd66;
            8'd34: ca_node=8'd68;
            8'd35: ca_node=8'd70;
            8'd36: ca_node=8'd72;
            8'd37: ca_node=8'd74;
            8'd38: ca_node=8'd76;
            8'd39: ca_node=8'd78;
            8'd40: ca_node=8'd80;
            8'd41: ca_node=8'd82;
            8'd42: ca_node=8'd84;
            8'd43: ca_node=8'd86;
            8'd44: ca_node=8'd88;
            8'd45: ca_node=8'd90;
            8'd46: ca_node=8'd92;
            8'd47: ca_node=8'd94;
            8'd48: ca_node=8'd96;
            8'd49: ca_node=8'd98;
            8'd50: ca_node=8'd100;
            8'd51: ca_node=8'd102;
            8'd64: ca_node=8'd128;
            8'd65: ca_node=8'd130;
            8'd66: ca_node=8'd132;
            8'd67: ca_node=8'd134;
            8'd68: ca_node=8'd136;
            8'd69: ca_node=8'd138;
            8'd70: ca_node=8'd140;
            8'd71: ca_node=8'd142;
            8'd72: ca_node=8'd144;
            8'd73: ca_node=8'd146;
            8'd74: ca_node=8'd148;
            8'd75: ca_node=8'd150;
            8'd76: ca_node=8'd152;
            8'd77: ca_node=8'd154;
            8'd78: ca_node=8'd156;
            8'd79: ca_node=8'd158;
            8'd80: ca_node=8'd160;
            8'd81: ca_node=8'd162;
            8'd82: ca_node=8'd164;
            8'd83: ca_node=8'd166;
            8'd84: ca_node=8'd168;
            8'd85: ca_node=8'd170;
            8'd86: ca_node=8'd172;
            8'd87: ca_node=8'd174;
            8'd88: ca_node=8'd176;
            8'd89: ca_node=8'd178;
            8'd90: ca_node=8'd180;
            8'd91: ca_node=8'd182;
            8'd92: ca_node=8'd184;
            8'd93: ca_node=8'd186;
            8'd94: ca_node=8'd188;
            8'd95: ca_node=8'd190;
            8'd96: ca_node=8'd192;
            8'd97: ca_node=8'd194;
            8'd98: ca_node=8'd196;
            8'd99: ca_node=8'd198;
            8'd100: ca_node=8'd200;
            8'd101: ca_node=8'd202;
            8'd102: ca_node=8'd204;
            8'd103: ca_node=8'd206;
            default: ca_node=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] cb_node(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd1: cb_node=8'd12;
            8'd2: cb_node=8'd5;
            8'd4: cb_node=8'd10;
            8'd5: cb_node=8'd11;
            8'd8: cb_node=8'd17;
            8'd9: cb_node=8'd19;
            8'd10: cb_node=8'd21;
            8'd11: cb_node=8'd23;
            8'd12: cb_node=8'd25;
            8'd16: cb_node=8'd33;
            8'd17: cb_node=8'd35;
            8'd18: cb_node=8'd37;
            8'd19: cb_node=8'd39;
            8'd20: cb_node=8'd41;
            8'd21: cb_node=8'd43;
            8'd22: cb_node=8'd45;
            8'd23: cb_node=8'd47;
            8'd24: cb_node=8'd49;
            8'd25: cb_node=8'd51;
            8'd32: cb_node=8'd65;
            8'd33: cb_node=8'd67;
            8'd34: cb_node=8'd69;
            8'd35: cb_node=8'd71;
            8'd36: cb_node=8'd73;
            8'd37: cb_node=8'd75;
            8'd38: cb_node=8'd77;
            8'd39: cb_node=8'd79;
            8'd40: cb_node=8'd81;
            8'd41: cb_node=8'd83;
            8'd42: cb_node=8'd85;
            8'd43: cb_node=8'd87;
            8'd44: cb_node=8'd89;
            8'd45: cb_node=8'd91;
            8'd46: cb_node=8'd93;
            8'd47: cb_node=8'd95;
            8'd48: cb_node=8'd97;
            8'd49: cb_node=8'd99;
            8'd50: cb_node=8'd101;
            8'd51: cb_node=8'd103;
            8'd64: cb_node=8'd129;
            8'd65: cb_node=8'd131;
            8'd66: cb_node=8'd133;
            8'd67: cb_node=8'd135;
            8'd68: cb_node=8'd137;
            8'd69: cb_node=8'd139;
            8'd70: cb_node=8'd141;
            8'd71: cb_node=8'd143;
            8'd72: cb_node=8'd145;
            8'd73: cb_node=8'd147;
            8'd74: cb_node=8'd149;
            8'd75: cb_node=8'd151;
            8'd76: cb_node=8'd153;
            8'd77: cb_node=8'd155;
            8'd78: cb_node=8'd157;
            8'd79: cb_node=8'd159;
            8'd80: cb_node=8'd161;
            8'd81: cb_node=8'd163;
            8'd82: cb_node=8'd165;
            8'd83: cb_node=8'd167;
            8'd84: cb_node=8'd169;
            8'd85: cb_node=8'd171;
            8'd86: cb_node=8'd173;
            8'd87: cb_node=8'd175;
            8'd88: cb_node=8'd177;
            8'd89: cb_node=8'd179;
            8'd90: cb_node=8'd181;
            8'd91: cb_node=8'd183;
            8'd92: cb_node=8'd185;
            8'd93: cb_node=8'd187;
            8'd94: cb_node=8'd189;
            8'd95: cb_node=8'd191;
            8'd96: cb_node=8'd193;
            8'd97: cb_node=8'd195;
            8'd98: cb_node=8'd197;
            8'd99: cb_node=8'd199;
            8'd100: cb_node=8'd201;
            8'd101: cb_node=8'd203;
            8'd102: cb_node=8'd205;
            8'd103: cb_node=8'd207;
            default: cb_node=8'd0;
          endcase
        end else begin
          case(n)
            8'd1: cb_node=8'd12;
            8'd2: cb_node=8'd5;
            8'd4: cb_node=8'd9;
            8'd5: cb_node=8'd11;
            8'd8: cb_node=8'd17;
            8'd9: cb_node=8'd19;
            8'd10: cb_node=8'd21;
            8'd11: cb_node=8'd23;
            8'd12: cb_node=8'd25;
            8'd16: cb_node=8'd33;
            8'd17: cb_node=8'd35;
            8'd18: cb_node=8'd37;
            8'd19: cb_node=8'd39;
            8'd20: cb_node=8'd41;
            8'd21: cb_node=8'd43;
            8'd22: cb_node=8'd45;
            8'd23: cb_node=8'd47;
            8'd24: cb_node=8'd49;
            8'd25: cb_node=8'd51;
            8'd32: cb_node=8'd65;
            8'd33: cb_node=8'd67;
            8'd34: cb_node=8'd69;
            8'd35: cb_node=8'd71;
            8'd36: cb_node=8'd73;
            8'd37: cb_node=8'd75;
            8'd38: cb_node=8'd77;
            8'd39: cb_node=8'd79;
            8'd40: cb_node=8'd81;
            8'd41: cb_node=8'd83;
            8'd42: cb_node=8'd85;
            8'd43: cb_node=8'd87;
            8'd44: cb_node=8'd89;
            8'd45: cb_node=8'd91;
            8'd46: cb_node=8'd93;
            8'd47: cb_node=8'd95;
            8'd48: cb_node=8'd97;
            8'd49: cb_node=8'd99;
            8'd50: cb_node=8'd101;
            8'd51: cb_node=8'd103;
            8'd64: cb_node=8'd129;
            8'd65: cb_node=8'd131;
            8'd66: cb_node=8'd133;
            8'd67: cb_node=8'd135;
            8'd68: cb_node=8'd137;
            8'd69: cb_node=8'd139;
            8'd70: cb_node=8'd141;
            8'd71: cb_node=8'd143;
            8'd72: cb_node=8'd145;
            8'd73: cb_node=8'd147;
            8'd74: cb_node=8'd149;
            8'd75: cb_node=8'd151;
            8'd76: cb_node=8'd153;
            8'd77: cb_node=8'd155;
            8'd78: cb_node=8'd157;
            8'd79: cb_node=8'd159;
            8'd80: cb_node=8'd161;
            8'd81: cb_node=8'd163;
            8'd82: cb_node=8'd165;
            8'd83: cb_node=8'd167;
            8'd84: cb_node=8'd169;
            8'd85: cb_node=8'd171;
            8'd86: cb_node=8'd173;
            8'd87: cb_node=8'd175;
            8'd88: cb_node=8'd177;
            8'd89: cb_node=8'd179;
            8'd90: cb_node=8'd181;
            8'd91: cb_node=8'd183;
            8'd92: cb_node=8'd185;
            8'd93: cb_node=8'd187;
            8'd94: cb_node=8'd189;
            8'd95: cb_node=8'd191;
            8'd96: cb_node=8'd193;
            8'd97: cb_node=8'd195;
            8'd98: cb_node=8'd197;
            8'd99: cb_node=8'd199;
            8'd100: cb_node=8'd201;
            8'd101: cb_node=8'd203;
            8'd102: cb_node=8'd205;
            8'd103: cb_node=8'd207;
            default: cb_node=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] node_role(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd2: node_role=8'd0;
            8'd4: node_role=8'd0;
            8'd5: node_role=8'd1;
            8'd8: node_role=8'd0;
            8'd9: node_role=8'd0;
            8'd10: node_role=8'd1;
            8'd11: node_role=8'd1;
            8'd12: node_role=8'd1;
            8'd16: node_role=8'd0;
            8'd17: node_role=8'd1;
            8'd18: node_role=8'd0;
            8'd19: node_role=8'd1;
            8'd20: node_role=8'd0;
            8'd21: node_role=8'd1;
            8'd22: node_role=8'd0;
            8'd23: node_role=8'd1;
            8'd24: node_role=8'd0;
            8'd25: node_role=8'd1;
            8'd32: node_role=8'd0;
            8'd33: node_role=8'd1;
            8'd34: node_role=8'd0;
            8'd35: node_role=8'd1;
            8'd36: node_role=8'd0;
            8'd37: node_role=8'd1;
            8'd38: node_role=8'd0;
            8'd39: node_role=8'd1;
            8'd40: node_role=8'd0;
            8'd41: node_role=8'd1;
            8'd42: node_role=8'd0;
            8'd43: node_role=8'd1;
            8'd44: node_role=8'd0;
            8'd45: node_role=8'd1;
            8'd46: node_role=8'd0;
            8'd47: node_role=8'd1;
            8'd48: node_role=8'd0;
            8'd49: node_role=8'd1;
            8'd50: node_role=8'd0;
            8'd51: node_role=8'd1;
            8'd64: node_role=8'd0;
            8'd65: node_role=8'd1;
            8'd66: node_role=8'd0;
            8'd67: node_role=8'd1;
            8'd68: node_role=8'd0;
            8'd69: node_role=8'd1;
            8'd70: node_role=8'd0;
            8'd71: node_role=8'd1;
            8'd72: node_role=8'd0;
            8'd73: node_role=8'd1;
            8'd74: node_role=8'd0;
            8'd75: node_role=8'd1;
            8'd76: node_role=8'd0;
            8'd77: node_role=8'd1;
            8'd78: node_role=8'd0;
            8'd79: node_role=8'd1;
            8'd80: node_role=8'd0;
            8'd81: node_role=8'd1;
            8'd82: node_role=8'd0;
            8'd83: node_role=8'd1;
            8'd84: node_role=8'd0;
            8'd85: node_role=8'd1;
            8'd86: node_role=8'd0;
            8'd87: node_role=8'd1;
            8'd88: node_role=8'd0;
            8'd89: node_role=8'd1;
            8'd90: node_role=8'd0;
            8'd91: node_role=8'd1;
            8'd92: node_role=8'd0;
            8'd93: node_role=8'd1;
            8'd94: node_role=8'd0;
            8'd95: node_role=8'd1;
            8'd96: node_role=8'd0;
            8'd97: node_role=8'd1;
            8'd98: node_role=8'd0;
            8'd99: node_role=8'd1;
            8'd100: node_role=8'd0;
            8'd101: node_role=8'd1;
            8'd102: node_role=8'd0;
            8'd103: node_role=8'd1;
            default: node_role=8'd0;
          endcase
        end else begin
          case(n)
            8'd2: node_role=8'd0;
            8'd4: node_role=8'd0;
            8'd5: node_role=8'd1;
            8'd8: node_role=8'd0;
            8'd9: node_role=8'd1;
            8'd10: node_role=8'd0;
            8'd11: node_role=8'd1;
            8'd12: node_role=8'd1;
            8'd16: node_role=8'd0;
            8'd17: node_role=8'd1;
            8'd18: node_role=8'd0;
            8'd19: node_role=8'd1;
            8'd20: node_role=8'd0;
            8'd21: node_role=8'd1;
            8'd22: node_role=8'd0;
            8'd23: node_role=8'd1;
            8'd24: node_role=8'd0;
            8'd25: node_role=8'd1;
            8'd32: node_role=8'd0;
            8'd33: node_role=8'd1;
            8'd34: node_role=8'd0;
            8'd35: node_role=8'd1;
            8'd36: node_role=8'd0;
            8'd37: node_role=8'd1;
            8'd38: node_role=8'd0;
            8'd39: node_role=8'd1;
            8'd40: node_role=8'd0;
            8'd41: node_role=8'd1;
            8'd42: node_role=8'd0;
            8'd43: node_role=8'd1;
            8'd44: node_role=8'd0;
            8'd45: node_role=8'd1;
            8'd46: node_role=8'd0;
            8'd47: node_role=8'd1;
            8'd48: node_role=8'd0;
            8'd49: node_role=8'd1;
            8'd50: node_role=8'd0;
            8'd51: node_role=8'd1;
            8'd64: node_role=8'd0;
            8'd65: node_role=8'd1;
            8'd66: node_role=8'd0;
            8'd67: node_role=8'd1;
            8'd68: node_role=8'd0;
            8'd69: node_role=8'd1;
            8'd70: node_role=8'd0;
            8'd71: node_role=8'd1;
            8'd72: node_role=8'd0;
            8'd73: node_role=8'd1;
            8'd74: node_role=8'd0;
            8'd75: node_role=8'd1;
            8'd76: node_role=8'd0;
            8'd77: node_role=8'd1;
            8'd78: node_role=8'd0;
            8'd79: node_role=8'd1;
            8'd80: node_role=8'd0;
            8'd81: node_role=8'd1;
            8'd82: node_role=8'd0;
            8'd83: node_role=8'd1;
            8'd84: node_role=8'd0;
            8'd85: node_role=8'd1;
            8'd86: node_role=8'd0;
            8'd87: node_role=8'd1;
            8'd88: node_role=8'd0;
            8'd89: node_role=8'd1;
            8'd90: node_role=8'd0;
            8'd91: node_role=8'd1;
            8'd92: node_role=8'd0;
            8'd93: node_role=8'd1;
            8'd94: node_role=8'd0;
            8'd95: node_role=8'd1;
            8'd96: node_role=8'd0;
            8'd97: node_role=8'd1;
            8'd98: node_role=8'd0;
            8'd99: node_role=8'd1;
            8'd100: node_role=8'd0;
            8'd101: node_role=8'd1;
            8'd102: node_role=8'd0;
            8'd103: node_role=8'd1;
            default: node_role=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] node_rank(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd2: node_rank=8'd0;
            8'd4: node_rank=8'd1;
            8'd5: node_rank=8'd0;
            8'd8: node_rank=8'd2;
            8'd9: node_rank=8'd3;
            8'd10: node_rank=8'd1;
            8'd11: node_rank=8'd2;
            8'd12: node_rank=8'd3;
            8'd16: node_rank=8'd4;
            8'd17: node_rank=8'd4;
            8'd18: node_rank=8'd5;
            8'd19: node_rank=8'd5;
            8'd20: node_rank=8'd6;
            8'd21: node_rank=8'd6;
            8'd22: node_rank=8'd7;
            8'd23: node_rank=8'd7;
            8'd24: node_rank=8'd8;
            8'd25: node_rank=8'd8;
            8'd32: node_rank=8'd9;
            8'd33: node_rank=8'd9;
            8'd34: node_rank=8'd10;
            8'd35: node_rank=8'd10;
            8'd36: node_rank=8'd11;
            8'd37: node_rank=8'd11;
            8'd38: node_rank=8'd12;
            8'd39: node_rank=8'd12;
            8'd40: node_rank=8'd13;
            8'd41: node_rank=8'd13;
            8'd42: node_rank=8'd14;
            8'd43: node_rank=8'd14;
            8'd44: node_rank=8'd15;
            8'd45: node_rank=8'd15;
            8'd46: node_rank=8'd16;
            8'd47: node_rank=8'd16;
            8'd48: node_rank=8'd17;
            8'd49: node_rank=8'd17;
            8'd50: node_rank=8'd18;
            8'd51: node_rank=8'd18;
            8'd64: node_rank=8'd19;
            8'd65: node_rank=8'd19;
            8'd66: node_rank=8'd20;
            8'd67: node_rank=8'd20;
            8'd68: node_rank=8'd21;
            8'd69: node_rank=8'd21;
            8'd70: node_rank=8'd22;
            8'd71: node_rank=8'd22;
            8'd72: node_rank=8'd23;
            8'd73: node_rank=8'd23;
            8'd74: node_rank=8'd24;
            8'd75: node_rank=8'd24;
            8'd76: node_rank=8'd25;
            8'd77: node_rank=8'd25;
            8'd78: node_rank=8'd26;
            8'd79: node_rank=8'd26;
            8'd80: node_rank=8'd27;
            8'd81: node_rank=8'd27;
            8'd82: node_rank=8'd28;
            8'd83: node_rank=8'd28;
            8'd84: node_rank=8'd29;
            8'd85: node_rank=8'd29;
            8'd86: node_rank=8'd30;
            8'd87: node_rank=8'd30;
            8'd88: node_rank=8'd31;
            8'd89: node_rank=8'd31;
            8'd90: node_rank=8'd32;
            8'd91: node_rank=8'd32;
            8'd92: node_rank=8'd33;
            8'd93: node_rank=8'd33;
            8'd94: node_rank=8'd34;
            8'd95: node_rank=8'd34;
            8'd96: node_rank=8'd35;
            8'd97: node_rank=8'd35;
            8'd98: node_rank=8'd36;
            8'd99: node_rank=8'd36;
            8'd100: node_rank=8'd37;
            8'd101: node_rank=8'd37;
            8'd102: node_rank=8'd38;
            8'd103: node_rank=8'd38;
            default: node_rank=8'd0;
          endcase
        end else begin
          case(n)
            8'd2: node_rank=8'd0;
            8'd4: node_rank=8'd1;
            8'd5: node_rank=8'd0;
            8'd8: node_rank=8'd2;
            8'd9: node_rank=8'd1;
            8'd10: node_rank=8'd3;
            8'd11: node_rank=8'd2;
            8'd12: node_rank=8'd3;
            8'd16: node_rank=8'd4;
            8'd17: node_rank=8'd4;
            8'd18: node_rank=8'd5;
            8'd19: node_rank=8'd5;
            8'd20: node_rank=8'd6;
            8'd21: node_rank=8'd6;
            8'd22: node_rank=8'd7;
            8'd23: node_rank=8'd7;
            8'd24: node_rank=8'd8;
            8'd25: node_rank=8'd8;
            8'd32: node_rank=8'd9;
            8'd33: node_rank=8'd9;
            8'd34: node_rank=8'd10;
            8'd35: node_rank=8'd10;
            8'd36: node_rank=8'd11;
            8'd37: node_rank=8'd11;
            8'd38: node_rank=8'd12;
            8'd39: node_rank=8'd12;
            8'd40: node_rank=8'd13;
            8'd41: node_rank=8'd13;
            8'd42: node_rank=8'd14;
            8'd43: node_rank=8'd14;
            8'd44: node_rank=8'd15;
            8'd45: node_rank=8'd15;
            8'd46: node_rank=8'd16;
            8'd47: node_rank=8'd16;
            8'd48: node_rank=8'd17;
            8'd49: node_rank=8'd17;
            8'd50: node_rank=8'd18;
            8'd51: node_rank=8'd18;
            8'd64: node_rank=8'd19;
            8'd65: node_rank=8'd19;
            8'd66: node_rank=8'd20;
            8'd67: node_rank=8'd20;
            8'd68: node_rank=8'd21;
            8'd69: node_rank=8'd21;
            8'd70: node_rank=8'd22;
            8'd71: node_rank=8'd22;
            8'd72: node_rank=8'd23;
            8'd73: node_rank=8'd23;
            8'd74: node_rank=8'd24;
            8'd75: node_rank=8'd24;
            8'd76: node_rank=8'd25;
            8'd77: node_rank=8'd25;
            8'd78: node_rank=8'd26;
            8'd79: node_rank=8'd26;
            8'd80: node_rank=8'd27;
            8'd81: node_rank=8'd27;
            8'd82: node_rank=8'd28;
            8'd83: node_rank=8'd28;
            8'd84: node_rank=8'd29;
            8'd85: node_rank=8'd29;
            8'd86: node_rank=8'd30;
            8'd87: node_rank=8'd30;
            8'd88: node_rank=8'd31;
            8'd89: node_rank=8'd31;
            8'd90: node_rank=8'd32;
            8'd91: node_rank=8'd32;
            8'd92: node_rank=8'd33;
            8'd93: node_rank=8'd33;
            8'd94: node_rank=8'd34;
            8'd95: node_rank=8'd34;
            8'd96: node_rank=8'd35;
            8'd97: node_rank=8'd35;
            8'd98: node_rank=8'd36;
            8'd99: node_rank=8'd36;
            8'd100: node_rank=8'd37;
            8'd101: node_rank=8'd37;
            8'd102: node_rank=8'd38;
            8'd103: node_rank=8'd38;
            default: node_rank=8'd0;
          endcase
        end
      end
    endfunction
 function automatic [10:0] descriptor(input [7:0] n,input integer tree);
  integer ix,slot,bank;
  begin
   if(n>=128)begin
    ix=n-128;
`ifdef OT_S81DV_MUT_LEAF
    if(TREES==1 && ix==1)ix=2;
`endif
    slot=tree*16+ix/5;bank=owner[tree*NV+ix]*K+ix%K;
   end else begin
    slot=tree*39+node_rank(n);bank=P*K+node_role(n)*RM+slot/64;
   end
   descriptor={5'(bank),5'((slot>>1)%32),1'(slot%2)};
  end
 endfunction
 wire[10:0] dw=descriptor({1'b0,wr_tag[6:0]},wr_tag[8:7]);
 // N8: the half/operand selects are KEPT same-edge copies per byte lane (copy y drives a_q/b_q[8y+:8] only;
 // census R33: one ahc/bhc bit drove the whole 32-bit half mux, 64 loads)
 (* keep *) reg[4*NB-1:0] asel,bsel,ahc,bhc;
 wire[NOWNER*TREES*NV*2-1:0] owner_bits;
 for(genvar oi=0;oi<NOWNER*TREES*NV;oi=oi+1)begin:g_owner_bits
   assign owner_bits[oi*2+:2]=owner_read[oi];
 end
 wire[63:0] rd[0:NB-1];
 wire[NB-1:0] read_ren,read_sa,read_sb,read_ha,read_hb;
 wire[NB*5-1:0] read_ra;
 // One one-hot descriptor per three actual banks. The already captured
 // command identity drives constant owner indices, avoiding the measured201-load variable-index mux.
 for(genvar rg=0;rg<(NB+2)/3;rg=rg+1)begin:g_read_group
   localparam integer CNT=(NB-rg*3>=3)?3:NB-rg*3;
   ot_s81dv_finish_readgroup_oh #(.NV(NV),.K(K),.P(P),.TREES(TREES),.FIRST(rg*3),.CNT(CNT)) u_read(
     .nodes(read_nodes[rg*TREES*NVP+:TREES*NVP]),.owner(owner_bits[((rg/3<NOWNER)?rg/3:NOWNER-1)*TREES*NV*2+:TREES*NV*2]),
     .ren(read_ren[rg*3+:CNT]),.ra(read_ra[rg*15+:CNT*5]),.sa(read_sa[rg*3+:CNT]),.sb(read_sb[rg*3+:CNT]),.ha(read_ha[rg*3+:CNT]),.hb(read_hb[rg*3+:CNT]));
 end
 for(genvar bank=0;bank<NB;bank=bank+1)begin:g_bank
  wire ren=read_ren[bank];wire[4:0] ra=read_ra[bank*5+:5];
  always @(posedge clk)begin
    asel[bank*4+:4]<={4{read_sa[bank]}};bsel[bank*4+:4]<={4{read_sb[bank]}};
    ahc[bank*4+:4]<={4{read_ha[bank]}};bhc[bank*4+:4]<={4{read_hb[bank]}};
  end
  wire[38:0] wp;
  wire[63:0] leaf_mask;
  if(bank<P*K)begin:g_leaf
   ot_s81dv_finish_leafw #(.NV(NV),.K(K),.P(P),.TREES(TREES),.PB(bank/K),.R(bank%K)) u_w(
     .da(dca[(((bank%K)*NBG)/K)*TREES*P*NV+:TREES*P*NV]),.db(dcb),.id(id),.wp(wp),.wm(leaf_mask));
  end else begin:g_internal
   assign wp={wr_v && wr_tag[6:0]!=1 && dw[10:6]==bank,dw[5:1],dw[0],wr_d};
  end
  wire[63:0] mask;
`ifdef OT_S81DV_XFIN_N11
  if(bank<P*K)begin:g_local_leaf_mask
   assign mask=leaf_mask;
  end else begin:g_internal_mask
`endif
  for(genvar b=0;b<8;b=b+1)begin:g_mask
   ot_s81dv_finish_mask8 #(.UPPER(b>=4)) u_m(.en(wp[38]),.half(wp[32]),.m(mask[8*b+:8]));
  end
`ifdef OT_S81DV_XFIN_N11
  end
`endif
  ot_sram_1r1w_32x64_m1 u_m(.clk(clk),.r_ce_in(ren),.r_addr_in(ra),.rd_out(rd[bank]),
    .w_ce_in(wp[38]),.w_addr_in(wp[37:33]),.wd_in({wp[31:0],wp[31:0]}),.w_mask_in(mask));
 end
 integer b,y;
 always @*begin
  a_q=0;b_q=0;
  for(b=0;b<NB;b=b+1)for(y=0;y<4;y=y+1)begin
   if(asel[b*4+y])a_q[8*y+:8]=a_q[8*y+:8]|(ahc[b*4+y]?rd[b][32+8*y+:8]:rd[b][8*y+:8]);
   if(bsel[b*4+y])b_q[8*y+:8]=b_q[8*y+:8]|(bhc[b*4+y]?rd[b][32+8*y+:8]:rd[b][8*y+:8]);
  end
 end
endmodule
// N8 (STW-S81-COLLA-XFIN 10-21): one leaf bank's write port from the finish's predecoded one-hot flit bases.
//  NORM (TREES 1, any 8-bit base): the bank (PB, R) writes leaf ix = the one leaf of port PB's window [bp, bp+4] with
//  ix % K == R (ix < NV); one-hot over the candidates IX = K*j + R: w[j] = OR_k da[PB][IX-k].  Port q supplies that
//  leaf from slot k2 iff da[q][ix-k2] (== iv[q] && ix - ib[q] == k2), so sel[q][k2] = OR_j w[j] && da[q][K*j+R-k2].
//  ENG (TREES 3, aligned bases): w[t][j] = da[t][PB][K*j] (== iv && it == t && bp == K*j, ix = K*j + R < NV),
//  slot = t*16 + j, sel[q] = OR_{t,j} w[t][j] && da[t][q][K*j] (== iv[q] && it[q] == it[PB] && ib[q] == bp).
//  Data = OR sel & id; en = |w; slot from the one-hot.  Equal to the original leaf_write() for every input.  Half 0
//  (data[15:0], en, slot) reads set da, half 1 reads set db (equal same-edge copies): every select drives 16 bits.
`ifdef OT_S81DV_XFIN_N11
// N11: each SRAM owns its complete write selector; prevent five-bank CSE.
(* keep_hierarchy=1 *)
`endif
module ot_s81dv_finish_leafw #(parameter integer NV=80,K=5,P=3,TREES=1,PB=0,R=0)(
 input wire[TREES*P*NV-1:0] da,db,input wire[P*K*32-1:0] id,output wire[38:0] wp,output wire[63:0] wm);
 localparam integer NJ=(NV+K-1)/K, NW=TREES*NJ;
 wire[NW-1:0] wa,wb;
 wire[P*K-1:0] sa,sb;
 for(genvar t=0;t<TREES;t=t+1)begin:g_t
  for(genvar j=0;j<NJ;j=j+1)begin:g_j
   localparam integer IX=K*j+R;
   if(IX>=NV)begin:g_none
    assign wa[t*NJ+j]=1'b0;assign wb[t*NJ+j]=1'b0;
   end else if(TREES==1)begin:g_norm
    wire[K-1:0] ca,cb;
    for(genvar k=0;k<K;k=k+1)begin:g_k
     if(IX-k>=0)begin:g_v assign ca[k]=da[PB*NV+IX-k];assign cb[k]=db[PB*NV+IX-k];end
     else begin:g_z assign ca[k]=1'b0;assign cb[k]=1'b0;end
    end
    assign wa[t*NJ+j]=|ca;assign wb[t*NJ+j]=|cb;
   end else begin:g_eng
    assign wa[t*NJ+j]=da[(t*P+PB)*NV+K*j];assign wb[t*NJ+j]=db[(t*P+PB)*NV+K*j];
   end
  end
 end
 for(genvar q=0;q<P;q=q+1)begin:g_q
  for(genvar k2=0;k2<K;k2=k2+1)begin:g_k2
   wire[NW-1:0] ta,tb;
   for(genvar t=0;t<TREES;t=t+1)begin:g_t
    for(genvar j=0;j<NJ;j=j+1)begin:g_j
     localparam integer IX=K*j+R;
     if(TREES==1 && IX<NV && IX-k2>=0)begin:g_n
      assign ta[t*NJ+j]=wa[t*NJ+j]&&da[q*NV+IX-k2];assign tb[t*NJ+j]=wb[t*NJ+j]&&db[q*NV+IX-k2];
     end else if(TREES!=1 && k2==R && IX<NV)begin:g_e
      assign ta[t*NJ+j]=wa[t*NJ+j]&&da[(t*P+q)*NV+K*j];assign tb[t*NJ+j]=wb[t*NJ+j]&&db[(t*P+q)*NV+K*j];
     end else begin:g_z
      assign ta[t*NJ+j]=1'b0;assign tb[t*NJ+j]=1'b0;
     end
    end
   end
   assign sa[q*K+k2]=|ta;assign sb[q*K+k2]=|tb;
  end
 end
 reg[15:0] dlo,dhi;reg[5:0] slot;
 integer i,n;
 always @*begin
  dlo=0;dhi=0;slot=0;
  for(i=0;i<P*K;i=i+1)begin
   dlo=dlo|({16{sa[i]}}&id[i*32+:16]);
   dhi=dhi|({16{sb[i]}}&id[i*32+16+:16]);
  end
  for(n=0;n<NW;n=n+1)if(wa[n])slot=slot|6'(TREES==1?n:(n/NJ)*16+(n%NJ));
 end
`ifdef OT_S81DV_XFIN_N12
 // N12: one kept enable/half owner reads wa once; eight byte mask owners take (en, half) (N11 had each of the eight
 // byte owners re-read all of wa: 8 x 2 loads per wa net, census max 102 on the ENG set-A one-hot). Same values.
 wire en,half_o;
 ot_s81dv_finish_leaf_enhalf #(.NW(NW)) u_eh(.wa(wa),.en(en),.half(half_o));
 assign wp={en,slot[5:1],slot[0],dhi,dlo};
 for(genvar mb=0;mb<8;mb=mb+1)begin:g_mask_owner
  ot_s81dv_finish_mask8 #(.UPPER(mb>=4)) u_mask(.en(en),.half(half_o),.m(wm[mb*8+:8]));
 end
`else
 wire en=|wa;
 assign wp={en,slot[5:1],slot[0],dhi,dlo};
`endif
`ifdef OT_S81DV_XFIN_N12
`elsif OT_S81DV_XFIN_N11
 // Each mask byte owns the combinational slot reduction, with no data edge.
 for(genvar mb=0;mb<8;mb=mb+1)begin:g_mask_owner
  ot_s81dv_finish_leaf_mask8 #(.NW(NW),.UPPER(mb>=4)) u_mask(.wa(wa),.m(wm[mb*8+:8]));
 end
`else
 assign wm=64'b0;
`endif
endmodule
(* keep_hierarchy=1 *) module ot_s81dv_finish_leaf_enhalf #(parameter integer NW=16)(input wire[NW-1:0]wa,output wire en,half);
 wire[NW-1:0] odd;
 for(genvar j=0;j<NW;j=j+1)begin:g_odd
  assign odd[j]=(j%2)?wa[j]:1'b0;
 end
 // Every ENG tree starts at slot t*16; its low bit is exactly j%2 (as ot_s81dv_finish_leaf_mask8).
`ifdef OT_S81DV_MUT_N12_MASK
 assign half=~|odd;
`else
 assign half=|odd;
`endif
 assign en=|wa;
endmodule
(* keep_hierarchy=1 *) module ot_s81dv_finish_leaf_mask8 #(parameter integer NW=16,UPPER=0)(input wire[NW-1:0]wa,output wire[7:0]m);
 wire[NW-1:0] odd;
 for(genvar j=0;j<NW;j=j+1)begin:g_odd
  assign odd[j]=(j%2)?wa[j]:1'b0;
 end
 // Every ENG tree starts at slot t*16; its low bit is exactly j%2.
 wire half=|odd;
 wire en=|wa;
`ifdef OT_S81DV_MUT_N11_MASK
 assign m={8{en && (half!=UPPER)}};
`else
 assign m={8{en && (half==UPPER)}};
`endif
endmodule
// Leaf-match predecode: oh[x] = v && b == x from 16 + 16 nibble one-hots (each net <= 16 loads).
(* keep_hierarchy=1 *) module ot_s81dv_fin_dec #(parameter integer N=80)(input wire v,input wire[7:0] b,output wire[N-1:0] oh);
 wire[15:0] hi,lo;
 for(genvar i=0;i<16;i=i+1)begin:g_n
  assign hi[i]=v && b[7:4]==i;
  assign lo[i]=b[3:0]==i;
 end
 for(genvar x=0;x<N;x=x+1)begin:g_x
  assign oh[x]=hi[x>>4] && lo[x&15];
 end
endmodule
(* keep_hierarchy=1 *) module ot_s81dv_finish_mask8 #(parameter integer UPPER=0)(input wire en,half,output wire[7:0] m);
 assign m={8{en && (half==UPPER)}};
endmodule
// Same two release edges as the original rsr forest, bounded real regional consumers.
module ot_s81dv_finish_reset2 #(parameter integer LEAVES=64)(input wire clk,rst_n,output wire[LEAVES-1:0] q);
 localparam integer NP=(LEAVES+23)/24;
 (* keep=1 *) reg[NP-1:0] prefix;
 always @(posedge clk or negedge rst_n)if(!rst_n)prefix<=0;else prefix<={NP{1'b1}};
 for(genvar g=0;g<LEAVES;g=g+1)begin:g_leaf
  (* keep=1 *) reg r;
  always @(posedge clk or negedge prefix[g/24])if(!prefix[g/24])r<=0;else r<=1;
  assign q[g]=r;
 end
endmodule

(* keep_hierarchy=1 *) module ot_s81dv_finish_readgroup #(parameter integer NV=80,K=5,P=3,TREES=1,FIRST=0,CNT=3)(input wire fire,input wire[8:0] tag,input wire[TREES*NV*2-1:0] owner,output wire[CNT-1:0] ren,output wire[CNT*5-1:0] ra,output wire[CNT-1:0] sa,sb,ha,hb);
 localparam integer RM=(TREES==3)?2:1;
 localparam integer MUT_ASSOC=`ifdef OT_S81DV_MUT_EASSOC (TREES==3) `else 0 `endif;
    function automatic [7:0] ca_node(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd1: ca_node=8'd2;
            8'd2: ca_node=8'd4;
            8'd4: ca_node=8'd8;
            8'd5: ca_node=8'd9;
            8'd8: ca_node=8'd16;
            8'd9: ca_node=8'd18;
            8'd10: ca_node=8'd20;
            8'd11: ca_node=8'd22;
            8'd12: ca_node=8'd24;
            8'd16: ca_node=8'd32;
            8'd17: ca_node=8'd34;
            8'd18: ca_node=8'd36;
            8'd19: ca_node=8'd38;
            8'd20: ca_node=8'd40;
            8'd21: ca_node=8'd42;
            8'd22: ca_node=8'd44;
            8'd23: ca_node=8'd46;
            8'd24: ca_node=8'd48;
            8'd25: ca_node=8'd50;
            8'd32: ca_node=8'd64;
            8'd33: ca_node=8'd66;
            8'd34: ca_node=8'd68;
            8'd35: ca_node=8'd70;
            8'd36: ca_node=8'd72;
            8'd37: ca_node=8'd74;
            8'd38: ca_node=8'd76;
            8'd39: ca_node=8'd78;
            8'd40: ca_node=8'd80;
            8'd41: ca_node=8'd82;
            8'd42: ca_node=8'd84;
            8'd43: ca_node=8'd86;
            8'd44: ca_node=8'd88;
            8'd45: ca_node=8'd90;
            8'd46: ca_node=8'd92;
            8'd47: ca_node=8'd94;
            8'd48: ca_node=8'd96;
            8'd49: ca_node=8'd98;
            8'd50: ca_node=8'd100;
            8'd51: ca_node=8'd102;
            8'd64: ca_node=8'd128;
            8'd65: ca_node=8'd130;
            8'd66: ca_node=8'd132;
            8'd67: ca_node=8'd134;
            8'd68: ca_node=8'd136;
            8'd69: ca_node=8'd138;
            8'd70: ca_node=8'd140;
            8'd71: ca_node=8'd142;
            8'd72: ca_node=8'd144;
            8'd73: ca_node=8'd146;
            8'd74: ca_node=8'd148;
            8'd75: ca_node=8'd150;
            8'd76: ca_node=8'd152;
            8'd77: ca_node=8'd154;
            8'd78: ca_node=8'd156;
            8'd79: ca_node=8'd158;
            8'd80: ca_node=8'd160;
            8'd81: ca_node=8'd162;
            8'd82: ca_node=8'd164;
            8'd83: ca_node=8'd166;
            8'd84: ca_node=8'd168;
            8'd85: ca_node=8'd170;
            8'd86: ca_node=8'd172;
            8'd87: ca_node=8'd174;
            8'd88: ca_node=8'd176;
            8'd89: ca_node=8'd178;
            8'd90: ca_node=8'd180;
            8'd91: ca_node=8'd182;
            8'd92: ca_node=8'd184;
            8'd93: ca_node=8'd186;
            8'd94: ca_node=8'd188;
            8'd95: ca_node=8'd190;
            8'd96: ca_node=8'd192;
            8'd97: ca_node=8'd194;
            8'd98: ca_node=8'd196;
            8'd99: ca_node=8'd198;
            8'd100: ca_node=8'd200;
            8'd101: ca_node=8'd202;
            8'd102: ca_node=8'd204;
            8'd103: ca_node=8'd206;
            default: ca_node=8'd0;
          endcase
        end else begin
          case(n)
            8'd1: ca_node=8'd2;
            8'd2: ca_node=8'd4;
            8'd4: ca_node=8'd8;
            8'd5: ca_node=8'd10;
            8'd8: ca_node=8'd16;
            8'd9: ca_node=8'd18;
            8'd10: ca_node=8'd20;
            8'd11: ca_node=8'd22;
            8'd12: ca_node=8'd24;
            8'd16: ca_node=8'd32;
            8'd17: ca_node=8'd34;
            8'd18: ca_node=8'd36;
            8'd19: ca_node=8'd38;
            8'd20: ca_node=8'd40;
            8'd21: ca_node=8'd42;
            8'd22: ca_node=8'd44;
            8'd23: ca_node=8'd46;
            8'd24: ca_node=8'd48;
            8'd25: ca_node=8'd50;
            8'd32: ca_node=8'd64;
            8'd33: ca_node=8'd66;
            8'd34: ca_node=8'd68;
            8'd35: ca_node=8'd70;
            8'd36: ca_node=8'd72;
            8'd37: ca_node=8'd74;
            8'd38: ca_node=8'd76;
            8'd39: ca_node=8'd78;
            8'd40: ca_node=8'd80;
            8'd41: ca_node=8'd82;
            8'd42: ca_node=8'd84;
            8'd43: ca_node=8'd86;
            8'd44: ca_node=8'd88;
            8'd45: ca_node=8'd90;
            8'd46: ca_node=8'd92;
            8'd47: ca_node=8'd94;
            8'd48: ca_node=8'd96;
            8'd49: ca_node=8'd98;
            8'd50: ca_node=8'd100;
            8'd51: ca_node=8'd102;
            8'd64: ca_node=8'd128;
            8'd65: ca_node=8'd130;
            8'd66: ca_node=8'd132;
            8'd67: ca_node=8'd134;
            8'd68: ca_node=8'd136;
            8'd69: ca_node=8'd138;
            8'd70: ca_node=8'd140;
            8'd71: ca_node=8'd142;
            8'd72: ca_node=8'd144;
            8'd73: ca_node=8'd146;
            8'd74: ca_node=8'd148;
            8'd75: ca_node=8'd150;
            8'd76: ca_node=8'd152;
            8'd77: ca_node=8'd154;
            8'd78: ca_node=8'd156;
            8'd79: ca_node=8'd158;
            8'd80: ca_node=8'd160;
            8'd81: ca_node=8'd162;
            8'd82: ca_node=8'd164;
            8'd83: ca_node=8'd166;
            8'd84: ca_node=8'd168;
            8'd85: ca_node=8'd170;
            8'd86: ca_node=8'd172;
            8'd87: ca_node=8'd174;
            8'd88: ca_node=8'd176;
            8'd89: ca_node=8'd178;
            8'd90: ca_node=8'd180;
            8'd91: ca_node=8'd182;
            8'd92: ca_node=8'd184;
            8'd93: ca_node=8'd186;
            8'd94: ca_node=8'd188;
            8'd95: ca_node=8'd190;
            8'd96: ca_node=8'd192;
            8'd97: ca_node=8'd194;
            8'd98: ca_node=8'd196;
            8'd99: ca_node=8'd198;
            8'd100: ca_node=8'd200;
            8'd101: ca_node=8'd202;
            8'd102: ca_node=8'd204;
            8'd103: ca_node=8'd206;
            default: ca_node=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] cb_node(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd1: cb_node=8'd12;
            8'd2: cb_node=8'd5;
            8'd4: cb_node=8'd10;
            8'd5: cb_node=8'd11;
            8'd8: cb_node=8'd17;
            8'd9: cb_node=8'd19;
            8'd10: cb_node=8'd21;
            8'd11: cb_node=8'd23;
            8'd12: cb_node=8'd25;
            8'd16: cb_node=8'd33;
            8'd17: cb_node=8'd35;
            8'd18: cb_node=8'd37;
            8'd19: cb_node=8'd39;
            8'd20: cb_node=8'd41;
            8'd21: cb_node=8'd43;
            8'd22: cb_node=8'd45;
            8'd23: cb_node=8'd47;
            8'd24: cb_node=8'd49;
            8'd25: cb_node=8'd51;
            8'd32: cb_node=8'd65;
            8'd33: cb_node=8'd67;
            8'd34: cb_node=8'd69;
            8'd35: cb_node=8'd71;
            8'd36: cb_node=8'd73;
            8'd37: cb_node=8'd75;
            8'd38: cb_node=8'd77;
            8'd39: cb_node=8'd79;
            8'd40: cb_node=8'd81;
            8'd41: cb_node=8'd83;
            8'd42: cb_node=8'd85;
            8'd43: cb_node=8'd87;
            8'd44: cb_node=8'd89;
            8'd45: cb_node=8'd91;
            8'd46: cb_node=8'd93;
            8'd47: cb_node=8'd95;
            8'd48: cb_node=8'd97;
            8'd49: cb_node=8'd99;
            8'd50: cb_node=8'd101;
            8'd51: cb_node=8'd103;
            8'd64: cb_node=8'd129;
            8'd65: cb_node=8'd131;
            8'd66: cb_node=8'd133;
            8'd67: cb_node=8'd135;
            8'd68: cb_node=8'd137;
            8'd69: cb_node=8'd139;
            8'd70: cb_node=8'd141;
            8'd71: cb_node=8'd143;
            8'd72: cb_node=8'd145;
            8'd73: cb_node=8'd147;
            8'd74: cb_node=8'd149;
            8'd75: cb_node=8'd151;
            8'd76: cb_node=8'd153;
            8'd77: cb_node=8'd155;
            8'd78: cb_node=8'd157;
            8'd79: cb_node=8'd159;
            8'd80: cb_node=8'd161;
            8'd81: cb_node=8'd163;
            8'd82: cb_node=8'd165;
            8'd83: cb_node=8'd167;
            8'd84: cb_node=8'd169;
            8'd85: cb_node=8'd171;
            8'd86: cb_node=8'd173;
            8'd87: cb_node=8'd175;
            8'd88: cb_node=8'd177;
            8'd89: cb_node=8'd179;
            8'd90: cb_node=8'd181;
            8'd91: cb_node=8'd183;
            8'd92: cb_node=8'd185;
            8'd93: cb_node=8'd187;
            8'd94: cb_node=8'd189;
            8'd95: cb_node=8'd191;
            8'd96: cb_node=8'd193;
            8'd97: cb_node=8'd195;
            8'd98: cb_node=8'd197;
            8'd99: cb_node=8'd199;
            8'd100: cb_node=8'd201;
            8'd101: cb_node=8'd203;
            8'd102: cb_node=8'd205;
            8'd103: cb_node=8'd207;
            default: cb_node=8'd0;
          endcase
        end else begin
          case(n)
            8'd1: cb_node=8'd12;
            8'd2: cb_node=8'd5;
            8'd4: cb_node=8'd9;
            8'd5: cb_node=8'd11;
            8'd8: cb_node=8'd17;
            8'd9: cb_node=8'd19;
            8'd10: cb_node=8'd21;
            8'd11: cb_node=8'd23;
            8'd12: cb_node=8'd25;
            8'd16: cb_node=8'd33;
            8'd17: cb_node=8'd35;
            8'd18: cb_node=8'd37;
            8'd19: cb_node=8'd39;
            8'd20: cb_node=8'd41;
            8'd21: cb_node=8'd43;
            8'd22: cb_node=8'd45;
            8'd23: cb_node=8'd47;
            8'd24: cb_node=8'd49;
            8'd25: cb_node=8'd51;
            8'd32: cb_node=8'd65;
            8'd33: cb_node=8'd67;
            8'd34: cb_node=8'd69;
            8'd35: cb_node=8'd71;
            8'd36: cb_node=8'd73;
            8'd37: cb_node=8'd75;
            8'd38: cb_node=8'd77;
            8'd39: cb_node=8'd79;
            8'd40: cb_node=8'd81;
            8'd41: cb_node=8'd83;
            8'd42: cb_node=8'd85;
            8'd43: cb_node=8'd87;
            8'd44: cb_node=8'd89;
            8'd45: cb_node=8'd91;
            8'd46: cb_node=8'd93;
            8'd47: cb_node=8'd95;
            8'd48: cb_node=8'd97;
            8'd49: cb_node=8'd99;
            8'd50: cb_node=8'd101;
            8'd51: cb_node=8'd103;
            8'd64: cb_node=8'd129;
            8'd65: cb_node=8'd131;
            8'd66: cb_node=8'd133;
            8'd67: cb_node=8'd135;
            8'd68: cb_node=8'd137;
            8'd69: cb_node=8'd139;
            8'd70: cb_node=8'd141;
            8'd71: cb_node=8'd143;
            8'd72: cb_node=8'd145;
            8'd73: cb_node=8'd147;
            8'd74: cb_node=8'd149;
            8'd75: cb_node=8'd151;
            8'd76: cb_node=8'd153;
            8'd77: cb_node=8'd155;
            8'd78: cb_node=8'd157;
            8'd79: cb_node=8'd159;
            8'd80: cb_node=8'd161;
            8'd81: cb_node=8'd163;
            8'd82: cb_node=8'd165;
            8'd83: cb_node=8'd167;
            8'd84: cb_node=8'd169;
            8'd85: cb_node=8'd171;
            8'd86: cb_node=8'd173;
            8'd87: cb_node=8'd175;
            8'd88: cb_node=8'd177;
            8'd89: cb_node=8'd179;
            8'd90: cb_node=8'd181;
            8'd91: cb_node=8'd183;
            8'd92: cb_node=8'd185;
            8'd93: cb_node=8'd187;
            8'd94: cb_node=8'd189;
            8'd95: cb_node=8'd191;
            8'd96: cb_node=8'd193;
            8'd97: cb_node=8'd195;
            8'd98: cb_node=8'd197;
            8'd99: cb_node=8'd199;
            8'd100: cb_node=8'd201;
            8'd101: cb_node=8'd203;
            8'd102: cb_node=8'd205;
            8'd103: cb_node=8'd207;
            default: cb_node=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] node_role(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd2: node_role=8'd0;
            8'd4: node_role=8'd0;
            8'd5: node_role=8'd1;
            8'd8: node_role=8'd0;
            8'd9: node_role=8'd0;
            8'd10: node_role=8'd1;
            8'd11: node_role=8'd1;
            8'd12: node_role=8'd1;
            8'd16: node_role=8'd0;
            8'd17: node_role=8'd1;
            8'd18: node_role=8'd0;
            8'd19: node_role=8'd1;
            8'd20: node_role=8'd0;
            8'd21: node_role=8'd1;
            8'd22: node_role=8'd0;
            8'd23: node_role=8'd1;
            8'd24: node_role=8'd0;
            8'd25: node_role=8'd1;
            8'd32: node_role=8'd0;
            8'd33: node_role=8'd1;
            8'd34: node_role=8'd0;
            8'd35: node_role=8'd1;
            8'd36: node_role=8'd0;
            8'd37: node_role=8'd1;
            8'd38: node_role=8'd0;
            8'd39: node_role=8'd1;
            8'd40: node_role=8'd0;
            8'd41: node_role=8'd1;
            8'd42: node_role=8'd0;
            8'd43: node_role=8'd1;
            8'd44: node_role=8'd0;
            8'd45: node_role=8'd1;
            8'd46: node_role=8'd0;
            8'd47: node_role=8'd1;
            8'd48: node_role=8'd0;
            8'd49: node_role=8'd1;
            8'd50: node_role=8'd0;
            8'd51: node_role=8'd1;
            8'd64: node_role=8'd0;
            8'd65: node_role=8'd1;
            8'd66: node_role=8'd0;
            8'd67: node_role=8'd1;
            8'd68: node_role=8'd0;
            8'd69: node_role=8'd1;
            8'd70: node_role=8'd0;
            8'd71: node_role=8'd1;
            8'd72: node_role=8'd0;
            8'd73: node_role=8'd1;
            8'd74: node_role=8'd0;
            8'd75: node_role=8'd1;
            8'd76: node_role=8'd0;
            8'd77: node_role=8'd1;
            8'd78: node_role=8'd0;
            8'd79: node_role=8'd1;
            8'd80: node_role=8'd0;
            8'd81: node_role=8'd1;
            8'd82: node_role=8'd0;
            8'd83: node_role=8'd1;
            8'd84: node_role=8'd0;
            8'd85: node_role=8'd1;
            8'd86: node_role=8'd0;
            8'd87: node_role=8'd1;
            8'd88: node_role=8'd0;
            8'd89: node_role=8'd1;
            8'd90: node_role=8'd0;
            8'd91: node_role=8'd1;
            8'd92: node_role=8'd0;
            8'd93: node_role=8'd1;
            8'd94: node_role=8'd0;
            8'd95: node_role=8'd1;
            8'd96: node_role=8'd0;
            8'd97: node_role=8'd1;
            8'd98: node_role=8'd0;
            8'd99: node_role=8'd1;
            8'd100: node_role=8'd0;
            8'd101: node_role=8'd1;
            8'd102: node_role=8'd0;
            8'd103: node_role=8'd1;
            default: node_role=8'd0;
          endcase
        end else begin
          case(n)
            8'd2: node_role=8'd0;
            8'd4: node_role=8'd0;
            8'd5: node_role=8'd1;
            8'd8: node_role=8'd0;
            8'd9: node_role=8'd1;
            8'd10: node_role=8'd0;
            8'd11: node_role=8'd1;
            8'd12: node_role=8'd1;
            8'd16: node_role=8'd0;
            8'd17: node_role=8'd1;
            8'd18: node_role=8'd0;
            8'd19: node_role=8'd1;
            8'd20: node_role=8'd0;
            8'd21: node_role=8'd1;
            8'd22: node_role=8'd0;
            8'd23: node_role=8'd1;
            8'd24: node_role=8'd0;
            8'd25: node_role=8'd1;
            8'd32: node_role=8'd0;
            8'd33: node_role=8'd1;
            8'd34: node_role=8'd0;
            8'd35: node_role=8'd1;
            8'd36: node_role=8'd0;
            8'd37: node_role=8'd1;
            8'd38: node_role=8'd0;
            8'd39: node_role=8'd1;
            8'd40: node_role=8'd0;
            8'd41: node_role=8'd1;
            8'd42: node_role=8'd0;
            8'd43: node_role=8'd1;
            8'd44: node_role=8'd0;
            8'd45: node_role=8'd1;
            8'd46: node_role=8'd0;
            8'd47: node_role=8'd1;
            8'd48: node_role=8'd0;
            8'd49: node_role=8'd1;
            8'd50: node_role=8'd0;
            8'd51: node_role=8'd1;
            8'd64: node_role=8'd0;
            8'd65: node_role=8'd1;
            8'd66: node_role=8'd0;
            8'd67: node_role=8'd1;
            8'd68: node_role=8'd0;
            8'd69: node_role=8'd1;
            8'd70: node_role=8'd0;
            8'd71: node_role=8'd1;
            8'd72: node_role=8'd0;
            8'd73: node_role=8'd1;
            8'd74: node_role=8'd0;
            8'd75: node_role=8'd1;
            8'd76: node_role=8'd0;
            8'd77: node_role=8'd1;
            8'd78: node_role=8'd0;
            8'd79: node_role=8'd1;
            8'd80: node_role=8'd0;
            8'd81: node_role=8'd1;
            8'd82: node_role=8'd0;
            8'd83: node_role=8'd1;
            8'd84: node_role=8'd0;
            8'd85: node_role=8'd1;
            8'd86: node_role=8'd0;
            8'd87: node_role=8'd1;
            8'd88: node_role=8'd0;
            8'd89: node_role=8'd1;
            8'd90: node_role=8'd0;
            8'd91: node_role=8'd1;
            8'd92: node_role=8'd0;
            8'd93: node_role=8'd1;
            8'd94: node_role=8'd0;
            8'd95: node_role=8'd1;
            8'd96: node_role=8'd0;
            8'd97: node_role=8'd1;
            8'd98: node_role=8'd0;
            8'd99: node_role=8'd1;
            8'd100: node_role=8'd0;
            8'd101: node_role=8'd1;
            8'd102: node_role=8'd0;
            8'd103: node_role=8'd1;
            default: node_role=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] node_rank(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd2: node_rank=8'd0;
            8'd4: node_rank=8'd1;
            8'd5: node_rank=8'd0;
            8'd8: node_rank=8'd2;
            8'd9: node_rank=8'd3;
            8'd10: node_rank=8'd1;
            8'd11: node_rank=8'd2;
            8'd12: node_rank=8'd3;
            8'd16: node_rank=8'd4;
            8'd17: node_rank=8'd4;
            8'd18: node_rank=8'd5;
            8'd19: node_rank=8'd5;
            8'd20: node_rank=8'd6;
            8'd21: node_rank=8'd6;
            8'd22: node_rank=8'd7;
            8'd23: node_rank=8'd7;
            8'd24: node_rank=8'd8;
            8'd25: node_rank=8'd8;
            8'd32: node_rank=8'd9;
            8'd33: node_rank=8'd9;
            8'd34: node_rank=8'd10;
            8'd35: node_rank=8'd10;
            8'd36: node_rank=8'd11;
            8'd37: node_rank=8'd11;
            8'd38: node_rank=8'd12;
            8'd39: node_rank=8'd12;
            8'd40: node_rank=8'd13;
            8'd41: node_rank=8'd13;
            8'd42: node_rank=8'd14;
            8'd43: node_rank=8'd14;
            8'd44: node_rank=8'd15;
            8'd45: node_rank=8'd15;
            8'd46: node_rank=8'd16;
            8'd47: node_rank=8'd16;
            8'd48: node_rank=8'd17;
            8'd49: node_rank=8'd17;
            8'd50: node_rank=8'd18;
            8'd51: node_rank=8'd18;
            8'd64: node_rank=8'd19;
            8'd65: node_rank=8'd19;
            8'd66: node_rank=8'd20;
            8'd67: node_rank=8'd20;
            8'd68: node_rank=8'd21;
            8'd69: node_rank=8'd21;
            8'd70: node_rank=8'd22;
            8'd71: node_rank=8'd22;
            8'd72: node_rank=8'd23;
            8'd73: node_rank=8'd23;
            8'd74: node_rank=8'd24;
            8'd75: node_rank=8'd24;
            8'd76: node_rank=8'd25;
            8'd77: node_rank=8'd25;
            8'd78: node_rank=8'd26;
            8'd79: node_rank=8'd26;
            8'd80: node_rank=8'd27;
            8'd81: node_rank=8'd27;
            8'd82: node_rank=8'd28;
            8'd83: node_rank=8'd28;
            8'd84: node_rank=8'd29;
            8'd85: node_rank=8'd29;
            8'd86: node_rank=8'd30;
            8'd87: node_rank=8'd30;
            8'd88: node_rank=8'd31;
            8'd89: node_rank=8'd31;
            8'd90: node_rank=8'd32;
            8'd91: node_rank=8'd32;
            8'd92: node_rank=8'd33;
            8'd93: node_rank=8'd33;
            8'd94: node_rank=8'd34;
            8'd95: node_rank=8'd34;
            8'd96: node_rank=8'd35;
            8'd97: node_rank=8'd35;
            8'd98: node_rank=8'd36;
            8'd99: node_rank=8'd36;
            8'd100: node_rank=8'd37;
            8'd101: node_rank=8'd37;
            8'd102: node_rank=8'd38;
            8'd103: node_rank=8'd38;
            default: node_rank=8'd0;
          endcase
        end else begin
          case(n)
            8'd2: node_rank=8'd0;
            8'd4: node_rank=8'd1;
            8'd5: node_rank=8'd0;
            8'd8: node_rank=8'd2;
            8'd9: node_rank=8'd1;
            8'd10: node_rank=8'd3;
            8'd11: node_rank=8'd2;
            8'd12: node_rank=8'd3;
            8'd16: node_rank=8'd4;
            8'd17: node_rank=8'd4;
            8'd18: node_rank=8'd5;
            8'd19: node_rank=8'd5;
            8'd20: node_rank=8'd6;
            8'd21: node_rank=8'd6;
            8'd22: node_rank=8'd7;
            8'd23: node_rank=8'd7;
            8'd24: node_rank=8'd8;
            8'd25: node_rank=8'd8;
            8'd32: node_rank=8'd9;
            8'd33: node_rank=8'd9;
            8'd34: node_rank=8'd10;
            8'd35: node_rank=8'd10;
            8'd36: node_rank=8'd11;
            8'd37: node_rank=8'd11;
            8'd38: node_rank=8'd12;
            8'd39: node_rank=8'd12;
            8'd40: node_rank=8'd13;
            8'd41: node_rank=8'd13;
            8'd42: node_rank=8'd14;
            8'd43: node_rank=8'd14;
            8'd44: node_rank=8'd15;
            8'd45: node_rank=8'd15;
            8'd46: node_rank=8'd16;
            8'd47: node_rank=8'd16;
            8'd48: node_rank=8'd17;
            8'd49: node_rank=8'd17;
            8'd50: node_rank=8'd18;
            8'd51: node_rank=8'd18;
            8'd64: node_rank=8'd19;
            8'd65: node_rank=8'd19;
            8'd66: node_rank=8'd20;
            8'd67: node_rank=8'd20;
            8'd68: node_rank=8'd21;
            8'd69: node_rank=8'd21;
            8'd70: node_rank=8'd22;
            8'd71: node_rank=8'd22;
            8'd72: node_rank=8'd23;
            8'd73: node_rank=8'd23;
            8'd74: node_rank=8'd24;
            8'd75: node_rank=8'd24;
            8'd76: node_rank=8'd25;
            8'd77: node_rank=8'd25;
            8'd78: node_rank=8'd26;
            8'd79: node_rank=8'd26;
            8'd80: node_rank=8'd27;
            8'd81: node_rank=8'd27;
            8'd82: node_rank=8'd28;
            8'd83: node_rank=8'd28;
            8'd84: node_rank=8'd29;
            8'd85: node_rank=8'd29;
            8'd86: node_rank=8'd30;
            8'd87: node_rank=8'd30;
            8'd88: node_rank=8'd31;
            8'd89: node_rank=8'd31;
            8'd90: node_rank=8'd32;
            8'd91: node_rank=8'd32;
            8'd92: node_rank=8'd33;
            8'd93: node_rank=8'd33;
            8'd94: node_rank=8'd34;
            8'd95: node_rank=8'd34;
            8'd96: node_rank=8'd35;
            8'd97: node_rank=8'd35;
            8'd98: node_rank=8'd36;
            8'd99: node_rank=8'd36;
            8'd100: node_rank=8'd37;
            8'd101: node_rank=8'd37;
            8'd102: node_rank=8'd38;
            8'd103: node_rank=8'd38;
            default: node_rank=8'd0;
          endcase
        end
      end
    endfunction
 function automatic [10:0] descriptor(input [7:0] n,input integer tree);
  integer ix,slot,bank;
  begin
   if(n>=128)begin
    ix=n-128;
`ifdef OT_S81DV_MUT_LEAF
    if(TREES==1 && ix==1)ix=2;
`endif
    slot=tree*16+ix/5;bank=owner[(tree*NV+ix)*2+:2]*K+ix%K;
   end else begin
    slot=tree*39+node_rank(n);bank=P*K+node_role(n)*RM+slot/64;
   end
   descriptor={5'(bank),5'((slot>>1)%32),1'(slot%2)};
  end
 endfunction
 wire[10:0] da=descriptor(ca_node({1'b0,tag[6:0]}),tag[8:7]);
 wire[10:0] db=descriptor(cb_node({1'b0,tag[6:0]}),tag[8:7]);
 for(genvar b=0;b<CNT;b=b+1)begin:g_out
   assign sa[b]=fire && da[10:6]==FIRST+b;
   assign sb[b]=fire && db[10:6]==FIRST+b;
   assign ren[b]=sa[b]||sb[b];
   assign ra[b*5+:5]=(da[10:6]==FIRST+b)?da[5:1]:db[5:1];
   assign ha[b]=da[0];assign hb[b]=db[0];
 end
endmodule

// Candidate: consume the existing same-edge issue one-hot directly. All
// descriptor operands are constant node/tree indices, so owner lookup is a
// direct two-bit field instead of a variable 480-bit mux. No capture edge moves.
(* keep_hierarchy=1 *) module ot_s81dv_finish_readgroup_oh #(
 parameter integer NV=80,K=5,P=3,TREES=1,FIRST=0,CNT=3,
 parameter integer NVP=(NV<=1)?1:(1<<$clog2(NV))
)(input wire[TREES*NVP-1:0] nodes,input wire[TREES*NV*2-1:0] owner,
 output wire[CNT-1:0] ren,output wire[CNT*5-1:0] ra,output wire[CNT-1:0] sa,sb,ha,hb);
 localparam integer RM=(TREES==3)?2:1;
 localparam integer MUT_ASSOC=`ifdef OT_S81DV_MUT_EASSOC (TREES==3) `else 0 `endif;
    function automatic [7:0] ca_node(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd1: ca_node=8'd2;
            8'd2: ca_node=8'd4;
            8'd4: ca_node=8'd8;
            8'd5: ca_node=8'd9;
            8'd8: ca_node=8'd16;
            8'd9: ca_node=8'd18;
            8'd10: ca_node=8'd20;
            8'd11: ca_node=8'd22;
            8'd12: ca_node=8'd24;
            8'd16: ca_node=8'd32;
            8'd17: ca_node=8'd34;
            8'd18: ca_node=8'd36;
            8'd19: ca_node=8'd38;
            8'd20: ca_node=8'd40;
            8'd21: ca_node=8'd42;
            8'd22: ca_node=8'd44;
            8'd23: ca_node=8'd46;
            8'd24: ca_node=8'd48;
            8'd25: ca_node=8'd50;
            8'd32: ca_node=8'd64;
            8'd33: ca_node=8'd66;
            8'd34: ca_node=8'd68;
            8'd35: ca_node=8'd70;
            8'd36: ca_node=8'd72;
            8'd37: ca_node=8'd74;
            8'd38: ca_node=8'd76;
            8'd39: ca_node=8'd78;
            8'd40: ca_node=8'd80;
            8'd41: ca_node=8'd82;
            8'd42: ca_node=8'd84;
            8'd43: ca_node=8'd86;
            8'd44: ca_node=8'd88;
            8'd45: ca_node=8'd90;
            8'd46: ca_node=8'd92;
            8'd47: ca_node=8'd94;
            8'd48: ca_node=8'd96;
            8'd49: ca_node=8'd98;
            8'd50: ca_node=8'd100;
            8'd51: ca_node=8'd102;
            8'd64: ca_node=8'd128;
            8'd65: ca_node=8'd130;
            8'd66: ca_node=8'd132;
            8'd67: ca_node=8'd134;
            8'd68: ca_node=8'd136;
            8'd69: ca_node=8'd138;
            8'd70: ca_node=8'd140;
            8'd71: ca_node=8'd142;
            8'd72: ca_node=8'd144;
            8'd73: ca_node=8'd146;
            8'd74: ca_node=8'd148;
            8'd75: ca_node=8'd150;
            8'd76: ca_node=8'd152;
            8'd77: ca_node=8'd154;
            8'd78: ca_node=8'd156;
            8'd79: ca_node=8'd158;
            8'd80: ca_node=8'd160;
            8'd81: ca_node=8'd162;
            8'd82: ca_node=8'd164;
            8'd83: ca_node=8'd166;
            8'd84: ca_node=8'd168;
            8'd85: ca_node=8'd170;
            8'd86: ca_node=8'd172;
            8'd87: ca_node=8'd174;
            8'd88: ca_node=8'd176;
            8'd89: ca_node=8'd178;
            8'd90: ca_node=8'd180;
            8'd91: ca_node=8'd182;
            8'd92: ca_node=8'd184;
            8'd93: ca_node=8'd186;
            8'd94: ca_node=8'd188;
            8'd95: ca_node=8'd190;
            8'd96: ca_node=8'd192;
            8'd97: ca_node=8'd194;
            8'd98: ca_node=8'd196;
            8'd99: ca_node=8'd198;
            8'd100: ca_node=8'd200;
            8'd101: ca_node=8'd202;
            8'd102: ca_node=8'd204;
            8'd103: ca_node=8'd206;
            default: ca_node=8'd0;
          endcase
        end else begin
          case(n)
            8'd1: ca_node=8'd2;
            8'd2: ca_node=8'd4;
            8'd4: ca_node=8'd8;
            8'd5: ca_node=8'd10;
            8'd8: ca_node=8'd16;
            8'd9: ca_node=8'd18;
            8'd10: ca_node=8'd20;
            8'd11: ca_node=8'd22;
            8'd12: ca_node=8'd24;
            8'd16: ca_node=8'd32;
            8'd17: ca_node=8'd34;
            8'd18: ca_node=8'd36;
            8'd19: ca_node=8'd38;
            8'd20: ca_node=8'd40;
            8'd21: ca_node=8'd42;
            8'd22: ca_node=8'd44;
            8'd23: ca_node=8'd46;
            8'd24: ca_node=8'd48;
            8'd25: ca_node=8'd50;
            8'd32: ca_node=8'd64;
            8'd33: ca_node=8'd66;
            8'd34: ca_node=8'd68;
            8'd35: ca_node=8'd70;
            8'd36: ca_node=8'd72;
            8'd37: ca_node=8'd74;
            8'd38: ca_node=8'd76;
            8'd39: ca_node=8'd78;
            8'd40: ca_node=8'd80;
            8'd41: ca_node=8'd82;
            8'd42: ca_node=8'd84;
            8'd43: ca_node=8'd86;
            8'd44: ca_node=8'd88;
            8'd45: ca_node=8'd90;
            8'd46: ca_node=8'd92;
            8'd47: ca_node=8'd94;
            8'd48: ca_node=8'd96;
            8'd49: ca_node=8'd98;
            8'd50: ca_node=8'd100;
            8'd51: ca_node=8'd102;
            8'd64: ca_node=8'd128;
            8'd65: ca_node=8'd130;
            8'd66: ca_node=8'd132;
            8'd67: ca_node=8'd134;
            8'd68: ca_node=8'd136;
            8'd69: ca_node=8'd138;
            8'd70: ca_node=8'd140;
            8'd71: ca_node=8'd142;
            8'd72: ca_node=8'd144;
            8'd73: ca_node=8'd146;
            8'd74: ca_node=8'd148;
            8'd75: ca_node=8'd150;
            8'd76: ca_node=8'd152;
            8'd77: ca_node=8'd154;
            8'd78: ca_node=8'd156;
            8'd79: ca_node=8'd158;
            8'd80: ca_node=8'd160;
            8'd81: ca_node=8'd162;
            8'd82: ca_node=8'd164;
            8'd83: ca_node=8'd166;
            8'd84: ca_node=8'd168;
            8'd85: ca_node=8'd170;
            8'd86: ca_node=8'd172;
            8'd87: ca_node=8'd174;
            8'd88: ca_node=8'd176;
            8'd89: ca_node=8'd178;
            8'd90: ca_node=8'd180;
            8'd91: ca_node=8'd182;
            8'd92: ca_node=8'd184;
            8'd93: ca_node=8'd186;
            8'd94: ca_node=8'd188;
            8'd95: ca_node=8'd190;
            8'd96: ca_node=8'd192;
            8'd97: ca_node=8'd194;
            8'd98: ca_node=8'd196;
            8'd99: ca_node=8'd198;
            8'd100: ca_node=8'd200;
            8'd101: ca_node=8'd202;
            8'd102: ca_node=8'd204;
            8'd103: ca_node=8'd206;
            default: ca_node=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] cb_node(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd1: cb_node=8'd12;
            8'd2: cb_node=8'd5;
            8'd4: cb_node=8'd10;
            8'd5: cb_node=8'd11;
            8'd8: cb_node=8'd17;
            8'd9: cb_node=8'd19;
            8'd10: cb_node=8'd21;
            8'd11: cb_node=8'd23;
            8'd12: cb_node=8'd25;
            8'd16: cb_node=8'd33;
            8'd17: cb_node=8'd35;
            8'd18: cb_node=8'd37;
            8'd19: cb_node=8'd39;
            8'd20: cb_node=8'd41;
            8'd21: cb_node=8'd43;
            8'd22: cb_node=8'd45;
            8'd23: cb_node=8'd47;
            8'd24: cb_node=8'd49;
            8'd25: cb_node=8'd51;
            8'd32: cb_node=8'd65;
            8'd33: cb_node=8'd67;
            8'd34: cb_node=8'd69;
            8'd35: cb_node=8'd71;
            8'd36: cb_node=8'd73;
            8'd37: cb_node=8'd75;
            8'd38: cb_node=8'd77;
            8'd39: cb_node=8'd79;
            8'd40: cb_node=8'd81;
            8'd41: cb_node=8'd83;
            8'd42: cb_node=8'd85;
            8'd43: cb_node=8'd87;
            8'd44: cb_node=8'd89;
            8'd45: cb_node=8'd91;
            8'd46: cb_node=8'd93;
            8'd47: cb_node=8'd95;
            8'd48: cb_node=8'd97;
            8'd49: cb_node=8'd99;
            8'd50: cb_node=8'd101;
            8'd51: cb_node=8'd103;
            8'd64: cb_node=8'd129;
            8'd65: cb_node=8'd131;
            8'd66: cb_node=8'd133;
            8'd67: cb_node=8'd135;
            8'd68: cb_node=8'd137;
            8'd69: cb_node=8'd139;
            8'd70: cb_node=8'd141;
            8'd71: cb_node=8'd143;
            8'd72: cb_node=8'd145;
            8'd73: cb_node=8'd147;
            8'd74: cb_node=8'd149;
            8'd75: cb_node=8'd151;
            8'd76: cb_node=8'd153;
            8'd77: cb_node=8'd155;
            8'd78: cb_node=8'd157;
            8'd79: cb_node=8'd159;
            8'd80: cb_node=8'd161;
            8'd81: cb_node=8'd163;
            8'd82: cb_node=8'd165;
            8'd83: cb_node=8'd167;
            8'd84: cb_node=8'd169;
            8'd85: cb_node=8'd171;
            8'd86: cb_node=8'd173;
            8'd87: cb_node=8'd175;
            8'd88: cb_node=8'd177;
            8'd89: cb_node=8'd179;
            8'd90: cb_node=8'd181;
            8'd91: cb_node=8'd183;
            8'd92: cb_node=8'd185;
            8'd93: cb_node=8'd187;
            8'd94: cb_node=8'd189;
            8'd95: cb_node=8'd191;
            8'd96: cb_node=8'd193;
            8'd97: cb_node=8'd195;
            8'd98: cb_node=8'd197;
            8'd99: cb_node=8'd199;
            8'd100: cb_node=8'd201;
            8'd101: cb_node=8'd203;
            8'd102: cb_node=8'd205;
            8'd103: cb_node=8'd207;
            default: cb_node=8'd0;
          endcase
        end else begin
          case(n)
            8'd1: cb_node=8'd12;
            8'd2: cb_node=8'd5;
            8'd4: cb_node=8'd9;
            8'd5: cb_node=8'd11;
            8'd8: cb_node=8'd17;
            8'd9: cb_node=8'd19;
            8'd10: cb_node=8'd21;
            8'd11: cb_node=8'd23;
            8'd12: cb_node=8'd25;
            8'd16: cb_node=8'd33;
            8'd17: cb_node=8'd35;
            8'd18: cb_node=8'd37;
            8'd19: cb_node=8'd39;
            8'd20: cb_node=8'd41;
            8'd21: cb_node=8'd43;
            8'd22: cb_node=8'd45;
            8'd23: cb_node=8'd47;
            8'd24: cb_node=8'd49;
            8'd25: cb_node=8'd51;
            8'd32: cb_node=8'd65;
            8'd33: cb_node=8'd67;
            8'd34: cb_node=8'd69;
            8'd35: cb_node=8'd71;
            8'd36: cb_node=8'd73;
            8'd37: cb_node=8'd75;
            8'd38: cb_node=8'd77;
            8'd39: cb_node=8'd79;
            8'd40: cb_node=8'd81;
            8'd41: cb_node=8'd83;
            8'd42: cb_node=8'd85;
            8'd43: cb_node=8'd87;
            8'd44: cb_node=8'd89;
            8'd45: cb_node=8'd91;
            8'd46: cb_node=8'd93;
            8'd47: cb_node=8'd95;
            8'd48: cb_node=8'd97;
            8'd49: cb_node=8'd99;
            8'd50: cb_node=8'd101;
            8'd51: cb_node=8'd103;
            8'd64: cb_node=8'd129;
            8'd65: cb_node=8'd131;
            8'd66: cb_node=8'd133;
            8'd67: cb_node=8'd135;
            8'd68: cb_node=8'd137;
            8'd69: cb_node=8'd139;
            8'd70: cb_node=8'd141;
            8'd71: cb_node=8'd143;
            8'd72: cb_node=8'd145;
            8'd73: cb_node=8'd147;
            8'd74: cb_node=8'd149;
            8'd75: cb_node=8'd151;
            8'd76: cb_node=8'd153;
            8'd77: cb_node=8'd155;
            8'd78: cb_node=8'd157;
            8'd79: cb_node=8'd159;
            8'd80: cb_node=8'd161;
            8'd81: cb_node=8'd163;
            8'd82: cb_node=8'd165;
            8'd83: cb_node=8'd167;
            8'd84: cb_node=8'd169;
            8'd85: cb_node=8'd171;
            8'd86: cb_node=8'd173;
            8'd87: cb_node=8'd175;
            8'd88: cb_node=8'd177;
            8'd89: cb_node=8'd179;
            8'd90: cb_node=8'd181;
            8'd91: cb_node=8'd183;
            8'd92: cb_node=8'd185;
            8'd93: cb_node=8'd187;
            8'd94: cb_node=8'd189;
            8'd95: cb_node=8'd191;
            8'd96: cb_node=8'd193;
            8'd97: cb_node=8'd195;
            8'd98: cb_node=8'd197;
            8'd99: cb_node=8'd199;
            8'd100: cb_node=8'd201;
            8'd101: cb_node=8'd203;
            8'd102: cb_node=8'd205;
            8'd103: cb_node=8'd207;
            default: cb_node=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] node_role(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd2: node_role=8'd0;
            8'd4: node_role=8'd0;
            8'd5: node_role=8'd1;
            8'd8: node_role=8'd0;
            8'd9: node_role=8'd0;
            8'd10: node_role=8'd1;
            8'd11: node_role=8'd1;
            8'd12: node_role=8'd1;
            8'd16: node_role=8'd0;
            8'd17: node_role=8'd1;
            8'd18: node_role=8'd0;
            8'd19: node_role=8'd1;
            8'd20: node_role=8'd0;
            8'd21: node_role=8'd1;
            8'd22: node_role=8'd0;
            8'd23: node_role=8'd1;
            8'd24: node_role=8'd0;
            8'd25: node_role=8'd1;
            8'd32: node_role=8'd0;
            8'd33: node_role=8'd1;
            8'd34: node_role=8'd0;
            8'd35: node_role=8'd1;
            8'd36: node_role=8'd0;
            8'd37: node_role=8'd1;
            8'd38: node_role=8'd0;
            8'd39: node_role=8'd1;
            8'd40: node_role=8'd0;
            8'd41: node_role=8'd1;
            8'd42: node_role=8'd0;
            8'd43: node_role=8'd1;
            8'd44: node_role=8'd0;
            8'd45: node_role=8'd1;
            8'd46: node_role=8'd0;
            8'd47: node_role=8'd1;
            8'd48: node_role=8'd0;
            8'd49: node_role=8'd1;
            8'd50: node_role=8'd0;
            8'd51: node_role=8'd1;
            8'd64: node_role=8'd0;
            8'd65: node_role=8'd1;
            8'd66: node_role=8'd0;
            8'd67: node_role=8'd1;
            8'd68: node_role=8'd0;
            8'd69: node_role=8'd1;
            8'd70: node_role=8'd0;
            8'd71: node_role=8'd1;
            8'd72: node_role=8'd0;
            8'd73: node_role=8'd1;
            8'd74: node_role=8'd0;
            8'd75: node_role=8'd1;
            8'd76: node_role=8'd0;
            8'd77: node_role=8'd1;
            8'd78: node_role=8'd0;
            8'd79: node_role=8'd1;
            8'd80: node_role=8'd0;
            8'd81: node_role=8'd1;
            8'd82: node_role=8'd0;
            8'd83: node_role=8'd1;
            8'd84: node_role=8'd0;
            8'd85: node_role=8'd1;
            8'd86: node_role=8'd0;
            8'd87: node_role=8'd1;
            8'd88: node_role=8'd0;
            8'd89: node_role=8'd1;
            8'd90: node_role=8'd0;
            8'd91: node_role=8'd1;
            8'd92: node_role=8'd0;
            8'd93: node_role=8'd1;
            8'd94: node_role=8'd0;
            8'd95: node_role=8'd1;
            8'd96: node_role=8'd0;
            8'd97: node_role=8'd1;
            8'd98: node_role=8'd0;
            8'd99: node_role=8'd1;
            8'd100: node_role=8'd0;
            8'd101: node_role=8'd1;
            8'd102: node_role=8'd0;
            8'd103: node_role=8'd1;
            default: node_role=8'd0;
          endcase
        end else begin
          case(n)
            8'd2: node_role=8'd0;
            8'd4: node_role=8'd0;
            8'd5: node_role=8'd1;
            8'd8: node_role=8'd0;
            8'd9: node_role=8'd1;
            8'd10: node_role=8'd0;
            8'd11: node_role=8'd1;
            8'd12: node_role=8'd1;
            8'd16: node_role=8'd0;
            8'd17: node_role=8'd1;
            8'd18: node_role=8'd0;
            8'd19: node_role=8'd1;
            8'd20: node_role=8'd0;
            8'd21: node_role=8'd1;
            8'd22: node_role=8'd0;
            8'd23: node_role=8'd1;
            8'd24: node_role=8'd0;
            8'd25: node_role=8'd1;
            8'd32: node_role=8'd0;
            8'd33: node_role=8'd1;
            8'd34: node_role=8'd0;
            8'd35: node_role=8'd1;
            8'd36: node_role=8'd0;
            8'd37: node_role=8'd1;
            8'd38: node_role=8'd0;
            8'd39: node_role=8'd1;
            8'd40: node_role=8'd0;
            8'd41: node_role=8'd1;
            8'd42: node_role=8'd0;
            8'd43: node_role=8'd1;
            8'd44: node_role=8'd0;
            8'd45: node_role=8'd1;
            8'd46: node_role=8'd0;
            8'd47: node_role=8'd1;
            8'd48: node_role=8'd0;
            8'd49: node_role=8'd1;
            8'd50: node_role=8'd0;
            8'd51: node_role=8'd1;
            8'd64: node_role=8'd0;
            8'd65: node_role=8'd1;
            8'd66: node_role=8'd0;
            8'd67: node_role=8'd1;
            8'd68: node_role=8'd0;
            8'd69: node_role=8'd1;
            8'd70: node_role=8'd0;
            8'd71: node_role=8'd1;
            8'd72: node_role=8'd0;
            8'd73: node_role=8'd1;
            8'd74: node_role=8'd0;
            8'd75: node_role=8'd1;
            8'd76: node_role=8'd0;
            8'd77: node_role=8'd1;
            8'd78: node_role=8'd0;
            8'd79: node_role=8'd1;
            8'd80: node_role=8'd0;
            8'd81: node_role=8'd1;
            8'd82: node_role=8'd0;
            8'd83: node_role=8'd1;
            8'd84: node_role=8'd0;
            8'd85: node_role=8'd1;
            8'd86: node_role=8'd0;
            8'd87: node_role=8'd1;
            8'd88: node_role=8'd0;
            8'd89: node_role=8'd1;
            8'd90: node_role=8'd0;
            8'd91: node_role=8'd1;
            8'd92: node_role=8'd0;
            8'd93: node_role=8'd1;
            8'd94: node_role=8'd0;
            8'd95: node_role=8'd1;
            8'd96: node_role=8'd0;
            8'd97: node_role=8'd1;
            8'd98: node_role=8'd0;
            8'd99: node_role=8'd1;
            8'd100: node_role=8'd0;
            8'd101: node_role=8'd1;
            8'd102: node_role=8'd0;
            8'd103: node_role=8'd1;
            default: node_role=8'd0;
          endcase
        end
      end
    endfunction
    function automatic [7:0] node_rank(input [7:0] n);
      begin
        if(MUT_ASSOC) begin
          case(n)
            8'd2: node_rank=8'd0;
            8'd4: node_rank=8'd1;
            8'd5: node_rank=8'd0;
            8'd8: node_rank=8'd2;
            8'd9: node_rank=8'd3;
            8'd10: node_rank=8'd1;
            8'd11: node_rank=8'd2;
            8'd12: node_rank=8'd3;
            8'd16: node_rank=8'd4;
            8'd17: node_rank=8'd4;
            8'd18: node_rank=8'd5;
            8'd19: node_rank=8'd5;
            8'd20: node_rank=8'd6;
            8'd21: node_rank=8'd6;
            8'd22: node_rank=8'd7;
            8'd23: node_rank=8'd7;
            8'd24: node_rank=8'd8;
            8'd25: node_rank=8'd8;
            8'd32: node_rank=8'd9;
            8'd33: node_rank=8'd9;
            8'd34: node_rank=8'd10;
            8'd35: node_rank=8'd10;
            8'd36: node_rank=8'd11;
            8'd37: node_rank=8'd11;
            8'd38: node_rank=8'd12;
            8'd39: node_rank=8'd12;
            8'd40: node_rank=8'd13;
            8'd41: node_rank=8'd13;
            8'd42: node_rank=8'd14;
            8'd43: node_rank=8'd14;
            8'd44: node_rank=8'd15;
            8'd45: node_rank=8'd15;
            8'd46: node_rank=8'd16;
            8'd47: node_rank=8'd16;
            8'd48: node_rank=8'd17;
            8'd49: node_rank=8'd17;
            8'd50: node_rank=8'd18;
            8'd51: node_rank=8'd18;
            8'd64: node_rank=8'd19;
            8'd65: node_rank=8'd19;
            8'd66: node_rank=8'd20;
            8'd67: node_rank=8'd20;
            8'd68: node_rank=8'd21;
            8'd69: node_rank=8'd21;
            8'd70: node_rank=8'd22;
            8'd71: node_rank=8'd22;
            8'd72: node_rank=8'd23;
            8'd73: node_rank=8'd23;
            8'd74: node_rank=8'd24;
            8'd75: node_rank=8'd24;
            8'd76: node_rank=8'd25;
            8'd77: node_rank=8'd25;
            8'd78: node_rank=8'd26;
            8'd79: node_rank=8'd26;
            8'd80: node_rank=8'd27;
            8'd81: node_rank=8'd27;
            8'd82: node_rank=8'd28;
            8'd83: node_rank=8'd28;
            8'd84: node_rank=8'd29;
            8'd85: node_rank=8'd29;
            8'd86: node_rank=8'd30;
            8'd87: node_rank=8'd30;
            8'd88: node_rank=8'd31;
            8'd89: node_rank=8'd31;
            8'd90: node_rank=8'd32;
            8'd91: node_rank=8'd32;
            8'd92: node_rank=8'd33;
            8'd93: node_rank=8'd33;
            8'd94: node_rank=8'd34;
            8'd95: node_rank=8'd34;
            8'd96: node_rank=8'd35;
            8'd97: node_rank=8'd35;
            8'd98: node_rank=8'd36;
            8'd99: node_rank=8'd36;
            8'd100: node_rank=8'd37;
            8'd101: node_rank=8'd37;
            8'd102: node_rank=8'd38;
            8'd103: node_rank=8'd38;
            default: node_rank=8'd0;
          endcase
        end else begin
          case(n)
            8'd2: node_rank=8'd0;
            8'd4: node_rank=8'd1;
            8'd5: node_rank=8'd0;
            8'd8: node_rank=8'd2;
            8'd9: node_rank=8'd1;
            8'd10: node_rank=8'd3;
            8'd11: node_rank=8'd2;
            8'd12: node_rank=8'd3;
            8'd16: node_rank=8'd4;
            8'd17: node_rank=8'd4;
            8'd18: node_rank=8'd5;
            8'd19: node_rank=8'd5;
            8'd20: node_rank=8'd6;
            8'd21: node_rank=8'd6;
            8'd22: node_rank=8'd7;
            8'd23: node_rank=8'd7;
            8'd24: node_rank=8'd8;
            8'd25: node_rank=8'd8;
            8'd32: node_rank=8'd9;
            8'd33: node_rank=8'd9;
            8'd34: node_rank=8'd10;
            8'd35: node_rank=8'd10;
            8'd36: node_rank=8'd11;
            8'd37: node_rank=8'd11;
            8'd38: node_rank=8'd12;
            8'd39: node_rank=8'd12;
            8'd40: node_rank=8'd13;
            8'd41: node_rank=8'd13;
            8'd42: node_rank=8'd14;
            8'd43: node_rank=8'd14;
            8'd44: node_rank=8'd15;
            8'd45: node_rank=8'd15;
            8'd46: node_rank=8'd16;
            8'd47: node_rank=8'd16;
            8'd48: node_rank=8'd17;
            8'd49: node_rank=8'd17;
            8'd50: node_rank=8'd18;
            8'd51: node_rank=8'd18;
            8'd64: node_rank=8'd19;
            8'd65: node_rank=8'd19;
            8'd66: node_rank=8'd20;
            8'd67: node_rank=8'd20;
            8'd68: node_rank=8'd21;
            8'd69: node_rank=8'd21;
            8'd70: node_rank=8'd22;
            8'd71: node_rank=8'd22;
            8'd72: node_rank=8'd23;
            8'd73: node_rank=8'd23;
            8'd74: node_rank=8'd24;
            8'd75: node_rank=8'd24;
            8'd76: node_rank=8'd25;
            8'd77: node_rank=8'd25;
            8'd78: node_rank=8'd26;
            8'd79: node_rank=8'd26;
            8'd80: node_rank=8'd27;
            8'd81: node_rank=8'd27;
            8'd82: node_rank=8'd28;
            8'd83: node_rank=8'd28;
            8'd84: node_rank=8'd29;
            8'd85: node_rank=8'd29;
            8'd86: node_rank=8'd30;
            8'd87: node_rank=8'd30;
            8'd88: node_rank=8'd31;
            8'd89: node_rank=8'd31;
            8'd90: node_rank=8'd32;
            8'd91: node_rank=8'd32;
            8'd92: node_rank=8'd33;
            8'd93: node_rank=8'd33;
            8'd94: node_rank=8'd34;
            8'd95: node_rank=8'd34;
            8'd96: node_rank=8'd35;
            8'd97: node_rank=8'd35;
            8'd98: node_rank=8'd36;
            8'd99: node_rank=8'd36;
            8'd100: node_rank=8'd37;
            8'd101: node_rank=8'd37;
            8'd102: node_rank=8'd38;
            8'd103: node_rank=8'd38;
            default: node_rank=8'd0;
          endcase
        end
      end
    endfunction
 function automatic [10:0] descriptor(input [7:0] n,input integer tree);
  integer ix,slot,bank;
  begin
   if(n>=128)begin
    ix=n-128;
`ifdef OT_S81DV_MUT_LEAF
    if(TREES==1 && ix==1)ix=2;
`endif
    slot=tree*16+ix/5;bank=owner[(tree*NV+ix)*2+:2]*K+ix%K;
   end else begin
    slot=tree*39+node_rank(n);bank=P*K+node_role(n)*RM+slot/64;
   end
   descriptor={5'(bank),5'((slot>>1)%32),1'(slot%2)};
  end
 endfunction

 localparam integer NC=TREES*NVP, HB=$clog2(NVP);
 function automatic integer node_live(input integer n);
  integer H;
  begin
   H=HB-($clog2(n+1)-1);
   node_live=(n>=1 && n<NVP && ((((2*n+1)<<(H-1))-NVP)<NV));
  end
 endfunction
 wire[10:0] da[0:NC-1],db[0:NC-1];
 for(genvar c=0;c<NC;c=c+1)begin:g_descriptor
  localparam integer N=c%NVP,T=c/NVP;
  if(N>=1 && node_live(N))begin:g_live
   assign da[c]=descriptor(ca_node(8'(N)),T);
   assign db[c]=descriptor(cb_node(8'(N)),T);
  end else begin:g_empty
   assign da[c]=0;assign db[c]=0;
  end
 end
 for(genvar b=0;b<CNT;b=b+1)begin:g_out
  wire[NC-1:0] a,s,h,j;
  wire[NC-1:0] addr[0:4];
  for(genvar c=0;c<NC;c=c+1)begin:g_node
   localparam integer N=c%NVP;
   if(N>=1 && node_live(N))begin:g_live
    wire take_a=da[c][10:6]==FIRST+b;
    wire take_b=db[c][10:6]==FIRST+b;
    wire[4:0] row=take_a?da[c][5:1]:db[c][5:1];
    assign a[c]=nodes[c] && take_a;
    assign s[c]=nodes[c] && take_b;
    assign h[c]=nodes[c] && da[c][0];
    assign j[c]=nodes[c] && db[c][0];
    for(genvar k=0;k<5;k=k+1)begin:g_bit
     assign addr[k][c]=nodes[c] && row[k];
    end
   end else begin:g_empty
    assign a[c]=0;assign s[c]=0;assign h[c]=0;assign j[c]=0;
    for(genvar k=0;k<5;k=k+1)begin:g_bit
     assign addr[k][c]=0;
    end
   end
  end
  assign sa[b]=|a;assign sb[b]=|s;assign ren[b]=(|a)||(|s);
  assign ha[b]=|h;assign hb[b]=|j;
  for(genvar k=0;k<5;k=k+1)begin:g_addr
   assign ra[b*5+k]=|addr[k];
  end
 end
endmodule
