// Exact module-body extraction from 27ffa71c6; compile with OT_S81ENG_TAP_N32R2.
(* keep_hierarchy = 1 *) module dsdv_eng_tap_slot (
    input wire pv_in, input wire [3:0] own, input wire[15:0] own_oh, input wire [3:0] sq, output wire myslot
);
`ifdef OT_S81ENG_TAP_N32R2
    wire[15:0] sq_oh;
    dsdv_eng_tap_dec4 u_sq(.a(sq),.y(sq_oh));
    assign myslot = !pv_in && |(own_oh & sq_oh);
`else
    assign myslot = !pv_in && own == sq;
`endif
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_take (
    input wire myslot, input wire nz0, input wire nz1, output wire [1:0] take
);
    assign take = {myslot && nz1 && !nz0, myslot && nz0};
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_we (
    input wire eng, input wire [5:0] hw, output wire [5:0] we
);
    assign we = {6{eng}} & hw;
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_hit #(parameter integer P = 0) (
    input wire [5:0] rci, input wire [3:0] sq, output wire hit
);
    assign hit = rci[0] && rci[5:2] == sq && (P == 1 ? rci[1] : !rci[1]);
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_eng #(parameter integer MUT = 0) (
    input wire bv, input wire [9:0] bt, input wire cellnz, output wire eng
);
`ifdef OT_S81ENG_TAP_N32R2
    assign eng = bv && !bt[9] && ((MUT==1) || bt[1]) && cellnz;
`else
    assign eng = (MUT == 1) ? (bv && !bt[9] && bt[5:2] != 4'd0) : (bv && !bt[9] && bt[1] && bt[5:2] != 4'd0);
`endif
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_hs #(parameter integer MUT = 0, parameter integer W = 22) (
    input  wire        ck, input wire rn0, input wire rn1, input wire [3:0] sid,
    input  wire        pv_in, input wire [3:0] own, input wire[15:0] own_oh, input wire cn0, cn1,
    input  wire        bv0, input wire [9:0] bt0, input wire bv1, input wire [9:0] bt1,
    input  wire [W-1:0] hin0, input wire [W-1:0] hin1, input wire [W-1:0] pci_d,
    output reg  [W-1:0] pco_d
);
    localparam integer EH = 6;
    reg [3:0] sq;
    always @(posedge ck) sq <= sid;
    wire myslot, e0, e1;
    wire [1:0] tk_d, tk_c;
    dsdv_eng_tap_slot u_sl (.pv_in(pv_in), .own(own), .own_oh(own_oh), .sq(sq), .myslot(myslot));
    dsdv_eng_tap_eng #(.MUT(MUT)) u_e0 (.bv(bv0), .bt(bt0), .cellnz(cn0), .eng(e0));
    dsdv_eng_tap_eng #(.MUT(MUT)) u_e1 (.bv(bv1), .bt(bt1), .cellnz(cn1), .eng(e1));
    reg [EH-1:0] hw0, hr0, hw1, hr1;
    reg [3:0]    hn0, hn1;
    wire nz0 = hn0 != 4'd0, nz1 = hn1 != 4'd0;
    dsdv_eng_tap_take u_td (.myslot(myslot), .nz0(nz0), .nz1(nz1), .take(tk_d));
    dsdv_eng_tap_take u_tc (.myslot(myslot), .nz0(nz0), .nz1(nz1), .take(tk_c));
    always @(posedge ck or negedge rn0)
        if (!rn0) begin hw0 <= EH'(1); hr0 <= EH'(1); hn0 <= 4'd0; end
        else begin
            if (e0) hw0 <= {hw0[EH-2:0], hw0[EH-1]};
            if (tk_c[0]) hr0 <= {hr0[EH-2:0], hr0[EH-1]};
            hn0 <= hn0 + (e0 ? 4'd1 : 4'd0) - (tk_c[0] ? 4'd1 : 4'd0);
        end
    always @(posedge ck or negedge rn1)
        if (!rn1) begin hw1 <= EH'(1); hr1 <= EH'(1); hn1 <= 4'd0; end
        else begin
            if (e1) hw1 <= {hw1[EH-2:0], hw1[EH-1]};
            if (tk_c[1]) hr1 <= {hr1[EH-2:0], hr1[EH-1]};
            hn1 <= hn1 + (e1 ? 4'd1 : 4'd0) - (tk_c[1] ? 4'd1 : 4'd0);
        end
    wire [EH-1:0] we0, we1;
    dsdv_eng_tap_we u_w0 (.eng(e0), .hw(hw0), .we(we0));
    dsdv_eng_tap_we u_w1 (.eng(e1), .hw(hw1), .we(we1));
    reg [W-1:0] he0 [0:EH-1];
    reg [W-1:0] he1 [0:EH-1];
    integer e;
    always @(posedge ck)
        for (e = 0; e < EH; e = e + 1) begin
            if (we0[e]) he0[e] <= hin0;
            if (we1[e]) he1[e] <= hin1;
        end
    reg [W-1:0] hs0, hs1;
    always @* begin
        hs0 = '0; hs1 = '0;
        for (e = 0; e < EH; e = e + 1) begin
            hs0 = hs0 | ({W{hr0[e]}} & he0[e]);
            hs1 = hs1 | ({W{hr1[e]}} & he1[e]);
        end
    end
    always @(posedge ck) pco_d <= tk_d[0] ? hs0 : tk_d[1] ? hs1 : pci_d;
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_rqd #(parameter integer P = 0, parameter integer W = 22) (
    input wire ck, input wire [3:0] sid, input wire [5:0] rci,
    input wire [W-1:0] ew_d, input wire [W-1:0] rq_d, output reg [W-1:0] rqo_d
);
    reg [3:0] sq;
    always @(posedge ck) sq <= sid;
    wire hit;
    dsdv_eng_tap_hit #(.P(P)) u_h (.rci(rci), .sq(sq), .hit(hit));
    always @(posedge ck) rqo_d <= hit ? ew_d : rq_d;
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_ofb #(parameter integer P = 0, parameter integer B = 0) (
    input wire ck, input wire rn, input wire [3:0] sid, input wire [5:0] rci, input wire rv,
    input wire [2:0] orp_lo, input wire popv, output wire rd
);
    reg [3:0] sq;
    always @(posedge ck) sq <= sid;
    wire hit;
    dsdv_eng_tap_hit #(.P(P)) u_h (.rci(rci), .sq(sq), .hit(hit));
    wire out_v = hit | rv;
    reg [4:0] owp;
    reg [7:0] ofi;
    always @(posedge ck or negedge rn) if (!rn) owp <= 5'd0; else if (out_v) owp <= owp + 5'd1;
    always @(posedge ck) if (out_v && owp[4:3] == 2'(B)) ofi[owp[2:0]] <= hit;
`ifdef OT_S81ENG_TAP_N32R2
    reg [2:0] rp;
    always @(posedge ck or negedge rn) if (!rn) rp <= 3'd0; else if (popv) rp <= rp + 3'd1;
    assign rd = ofi[rp];
`else
    assign rd = ofi[orp_lo];
`endif
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_rqc #(parameter integer P = 0, parameter integer RFD = 24,
                                                  parameter integer MUT = 0) (
    input  wire ck, input wire rn, input wire [3:0] sid, input wire [5:0] rci,
    input  wire rv, input wire rsl, input wire pop, input wire [3:0] bank_rd,
    output reg  rqo_v, output reg rqo_sl, output reg rro_pop, output wire [4:0] orp_o, output wire popv_o, output reg fl
);
    localparam integer OQ = 32;
    reg [3:0] sq;
    always @(posedge ck) sq <= sid;
    wire hit;
    dsdv_eng_tap_hit #(.P(P)) u_h (.rci(rci), .sq(sq), .hit(hit));
    wire out_v = hit | rv;
    reg [5:0] eo, on_;
    reg [4:0] orp;
    assign orp_o = orp;
    wire nz    = on_ != 6'd0;
    wire popv  = pop && nz;
    assign popv_o = popv;
    wire ofr   = bank_rd[orp[4:3]];
    wire pop_e = popv && ofr;
    wire pop_r = (MUT == 2) ? pop : (pop && !(nz && ofr));
    always @(posedge ck or negedge rn)
        if (!rn) begin rqo_v <= 1'b0; rqo_sl <= 1'b0; rro_pop <= 1'b0; eo <= '0; on_ <= '0; orp <= '0; fl <= 1'b0; end
        else begin
            rqo_v   <= out_v;
            rqo_sl  <= rsl | hit | (eo != 6'd0);
            rro_pop <= pop_r;
            eo  <= eo + (hit ? 6'd1 : 6'd0) - (pop_e ? 6'd1 : 6'd0);
            if (popv) orp <= orp + 5'd1;
            on_ <= on_ + (out_v ? 6'd1 : 6'd0) - (popv ? 6'd1 : 6'd0);
            if ((hit && rv) || (hit && on_ >= 6'(RFD)) || (out_v && on_ == 6'(OQ)) || (pop && on_ == 6'd0)) fl <= 1'b1;
        end
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_rsc #(parameter integer MUT = 0) (
    input  wire ck, input wire rn, input wire [3:0] sid, input wire [5:0] rci,
    input  wire pv_in, input wire [3:0] own, input wire[15:0] own_oh, input wire cn0, cn1,
    input  wire bv0, input wire [9:0] bt0, input wire bv1, input wire [9:0] bt1,
    output reg  rro_v0, output reg rro_v1, output reg pco_v, output reg [1:0] fxl
);
    localparam integer EH = 6;
    reg [3:0] sq;
    always @(posedge ck) sq <= sid;
    wire h0, h1, e0, e1, myslot;
    wire [1:0] tk;
    dsdv_eng_tap_hit #(.P(0)) u_h0 (.rci(rci), .sq(sq), .hit(h0));
    dsdv_eng_tap_hit #(.P(1)) u_h1 (.rci(rci), .sq(sq), .hit(h1));
    dsdv_eng_tap_eng #(.MUT(MUT)) u_e0 (.bv(bv0), .bt(bt0), .cellnz(cn0), .eng(e0));
    dsdv_eng_tap_eng #(.MUT(MUT)) u_e1 (.bv(bv1), .bt(bt1), .cellnz(cn1), .eng(e1));
    dsdv_eng_tap_slot u_sl (.pv_in(pv_in), .own(own), .own_oh(own_oh), .sq(sq), .myslot(myslot));
    reg [3:0] hn0, hn1;
    reg [5:0] er0, er1;
    dsdv_eng_tap_take u_t (.myslot(myslot), .nz0(hn0 != 4'd0), .nz1(hn1 != 4'd0), .take(tk));
    always @(posedge ck or negedge rn)
        if (!rn) begin rro_v0 <= 1'b0; rro_v1 <= 1'b0; pco_v <= 1'b0; fxl <= 2'b0; hn0 <= '0; hn1 <= '0; er0 <= '0; er1 <= '0; end
        else begin
            rro_v0 <= bv0 && !e0;
            rro_v1 <= bv1 && !e1;
            pco_v  <= pv_in | (|tk);
            hn0 <= hn0 + (e0 ? 4'd1 : 4'd0) - (tk[0] ? 4'd1 : 4'd0);
            hn1 <= hn1 + (e1 ? 4'd1 : 4'd0) - (tk[1] ? 4'd1 : 4'd0);
            er0 <= er0 + (h0 ? 6'd1 : 6'd0) - (e0 ? 6'd1 : 6'd0);
            er1 <= er1 + (h1 ? 6'd1 : 6'd0) - (e1 ? 6'd1 : 6'd0);
            if ((e0 && hn0 == 4'(EH)) || (e0 && er0 == 6'd0)) fxl[0] <= 1'b1;
            if ((e1 && hn1 == 4'(EH)) || (e1 && er1 == 6'd0)) fxl[1] <= 1'b1;
        end
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_sid4(input wire ck,input wire[3:0] d,output reg[3:0] q);
 always @(posedge ck)q<=d;
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_dec4(input wire[3:0] a,output wire[15:0] y);
 for(genvar g=0;g<16;g=g+1)begin:g_d assign y[g]=(a==4'(g)); end
endmodule

(* keep_hierarchy = 1 *) module dsdv_eng_tap_cellnz(input wire[3:0] cell_id,output wire nz);
 assign nz=|cell_id;
endmodule

module dsdv_eng_tap_c #(
    parameter bit WEST = 0,
    parameter integer RFD = 24,
    parameter integer EH  = 6,        // held Engram beats a lane: fixed 6 in the slices (a row's 9 atoms touch a PC once)
    parameter integer MUT = 0         // bench negative controls: 1 demux on g only (sc ignored), 2 pops not filtered
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [3:0]    sid,         // strap: controller index (PCs 2 sid, 2 sid + 1)
    input  wire [42:0]   rci,
    output reg  [42:0]   rco,
    input  wire [267:0]  pci,
    output wire [267:0]  pco,
    input  wire [91:0]   rqi,         // from the reader
    output wire [91:0]   rqo,         // to the controller rrq
    input  wire [543:0]  rri,         // from the controller rrd
    output wire [543:0]  rro,         // to the reader
    output reg           fault
);
`ifdef OT_S81ENG_TAP_N32R2
    localparam integer NS = 24, NR = 62, SW = 11, RDCH = 4;
    wire [3:0] sd [0:3];
    for(genvar sg=0;sg<4;sg=sg+1)begin:g_sid
        dsdv_eng_tap_sid4 u_s(.ck(ck),.d(sid),.q(sd[sg]));
    end
`else
    localparam integer NR = 30, SW = 22, RDCH = 2;
    wire [3:0] sd [0:3];
    for(genvar sg=0;sg<4;sg=sg+1)begin:g_sid_direct assign sd[sg]=sid; end
    localparam integer NS = 12;       // hold-ring / payload bit slices of 22 b (12 x 22 = 264 >= 263)
`endif
    generate if (EH != 6) begin : bad_eh dsdv_eng_tap_c_EH_must_be_6 trap(); end endgenerate
    wire [NR-1:0] rl;
`ifdef OT_S81ENG_TAP_N32R2
    ot_s81eng_reset3n32 #(.LEAVES(NR)) u_r(.clk(ck),.rst_n_in(rst_n),.rst_n(rl),.early_n());
`else
    ot_rst_relay_bounded32 #(.REGIONS(NR)) u_r (.clk(ck), .rst_n_in(rst_n), .rst_n(rl));
`endif
    // request chain forward
    always @(posedge ck or negedge rl[0]) if (!rl[0]) rco[0] <= 1'b0; else rco[0] <= rci[0];
    always @(posedge ck) rco[42:1] <= rci[42:1];
    wire [9:0]  t10 = {1'b0, rci[38:36], {1'b0, rci[42:40]} + 4'd1, 1'b1, rci[39]};
    wire [43:0] ew  = {t10, 4'd1, rci[35:6]};
    // response chain slot
    reg [3:0]  gen;
    wire       pv_in = WEST ? 1'b0 : pci[0];
    wire [3:0] own   = WEST ? gen : pci[4:1];
    wire [1:0] fl, fxl;
    wire [9:0] bt0 = rri[6 +: 10], bt1 = rri[272 + 6 +: 10];
    wire       bv0 = rri[0], bv1 = rri[272];
    wire[15:0] own_oh; wire cn0,cn1;
`ifdef OT_S81ENG_TAP_N32R2
    dsdv_eng_tap_dec4 u_own(.a(own),.y(own_oh));
    dsdv_eng_tap_cellnz u_cn0(.cell_id(bt0[5:2]),.nz(cn0));
    dsdv_eng_tap_cellnz u_cn1(.cell_id(bt1[5:2]),.nz(cn1));
`else
    assign own_oh=0; assign cn0=0; assign cn1=0;
`endif
    genvar p, b;
    generate for (p = 0; p < 2; p = p + 1) begin : g_ln
        wire [3:0] brd;
        wire [4:0] orp;
        wire popv;
        dsdv_eng_tap_rqc #(.P(p), .RFD(RFD), .MUT(MUT)) u_c (.ck(ck), .rn(rl[1 + p]), .sid(sd[0]), .rci(rci[5:0]),
            .rv(rqi[46 * p]), .rsl(rqi[46 * p + 1]), .pop(rri[272 * p + 1]), .bank_rd(brd),
            .rqo_v(rqo[46 * p]), .rqo_sl(rqo[46 * p + 1]), .rro_pop(rro[272 * p + 1]), .orp_o(orp), .popv_o(popv), .fl(fl[p]));
        for (b = 0; b < 4; b = b + 1) begin : g_ob
            dsdv_eng_tap_ofb #(.P(p), .B(b)) u_b (.ck(ck), .rn(rl[(NR==62)?54+4*p+b:3+p]), .sid(sd[1]), .rci(rci[5:0]),
                .rv(rqi[46 * p]), .orp_lo(orp[2:0]), .popv(popv), .rd(brd[b]));
        end
        for (b = 0; b < RDCH; b = b + 1) begin : g_rd
            dsdv_eng_tap_rqd #(.P(p),.W(SW)) u_d (.ck(ck), .sid(sd[2]), .rci(rci[5:0]), .ew_d(ew[SW * b +: SW]),
                .rq_d(rqi[46 * p + 2 + SW * b +: SW]), .rqo_d(rqo[46 * p + 2 + SW * b +: SW]));
        end
        reg [269:0] rro_d;
        always @(posedge ck) rro_d <= rri[272 * p + 2 +: 270];
        assign rro[272 * p + 2 +: 270] = rro_d;
    end endgenerate
    wire rro_v0, rro_v1, pco_v;
    assign rro[0] = rro_v0;
    assign rro[272] = rro_v1;
    dsdv_eng_tap_rsc #(.MUT(MUT)) u_rs (.ck(ck), .rn(rl[5]), .sid(sd[3]), .rci(rci[5:0]), .pv_in(pv_in), .own(own), .own_oh(own_oh), .cn0(cn0), .cn1(cn1),
        .bv0(bv0), .bt0(bt0), .bv1(bv1), .bt1(bt1), .rro_v0(rro_v0), .rro_v1(rro_v1), .pco_v(pco_v), .fxl(fxl));
    // hold-ring entries {d 256, col 3, atom 4} = {rri d, cell - 1, s3, slot3}
    wire [3:0]   colp0 = bt0[5:2] - 4'd1, colp1 = bt1[5:2] - 4'd1;
    wire [263:0] hin0 = {1'b0, rri[16 +: 256], colp0[2:0], bt0[0], bt0[8:6]};
    wire [263:0] hin1 = {1'b0, rri[272 + 16 +: 256], colp1[2:0], bt1[0], bt1[8:6]};
    wire [263:0] pcd  = {1'b0, pci[267:5]};
    wire [263:0] pcq;
    generate for (b = 0; b < NS; b = b + 1) begin : g_hs
        dsdv_eng_tap_hs #(.MUT(MUT),.W(SW)) u_s (.ck(ck), .rn0(rl[6 + 2 * b]), .rn1(rl[7 + 2 * b]), .sid(sd[b%4]), .pv_in(pv_in),
            .own(own), .own_oh(own_oh), .cn0(cn0), .cn1(cn1), .bv0(bv0), .bt0(bt0), .bv1(bv1), .bt1(bt1), .hin0(hin0[SW * b +: SW]),
            .hin1(hin1[SW * b +: SW]), .pci_d(pcd[SW * b +: SW]), .pco_d(pcq[SW * b +: SW]));
    end endgenerate
    reg [3:0] own_q;
    always @(posedge ck) own_q <= own;
    assign pco = {pcq[262:0], own_q, pco_v};
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin gen <= 4'd0; fault <= 1'b0; end
        else begin
            gen <= gen + 4'd1;
            fault <= fault | (|fl) | (|fxl);
        end
endmodule

module dsdv_eng_tap (
    input wire ck, input wire rst_n, input wire [3:0] sid,
    input wire [42:0] rci, output wire [42:0] rco, input wire [267:0] pci, output wire [267:0] pco,
    input wire [91:0] rqi, output wire [91:0] rqo, input wire [543:0] rri, output wire [543:0] rro, output wire fault
);
    dsdv_eng_tap_c #(.WEST(0)) u_t (.ck(ck), .rst_n(rst_n), .sid(sid), .rci(rci), .rco(rco), .pci(pci), .pco(pco),
        .rqi(rqi), .rqo(rqo), .rri(rri), .rro(rro), .fault(fault));
endmodule

module dsdv_eng_tap_w (
    input wire ck, input wire rst_n, input wire [3:0] sid,
    input wire [42:0] rci, output wire [267:0] pco,
    input wire [91:0] rqi, output wire [91:0] rqo, input wire [543:0] rri, output wire [543:0] rro, output wire fault
);
    wire [42:0] rco_end;              // chain end: the word is consumed here (decode only)
    dsdv_eng_tap_c #(.WEST(1)) u_t (.ck(ck), .rst_n(rst_n), .sid(sid), .rci(rci), .rco(rco_end), .pci(268'd0),
        .pco(pco), .rqi(rqi), .rqo(rqo), .rri(rri), .rro(rro), .fault(fault));
endmodule
