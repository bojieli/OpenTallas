`timescale 1ns/1ps
// E1 width-exact Engram request chain. New explicit masters; old defaults and
// frozen E5/h0/h1 modules remain unchanged. Request={tag7,sector_offset26,pc5,v}.
// Producer and every consumer must select the SAME aligned PCBASE. Consumers
// reconstruct its four sector prefix bits INSIDE the hard core, never at pins.
// +0 data/reset cycles. Source/profile/plan width adoption must be atomic.
// Dependencies: existing dsdv_eng_rr.sv tap helpers and frozen E5/h0/h1 sources.
module dsdv_eng_rr_req39 #(
    parameter integer RETURN_AGE = 640,
    parameter [29:0] PCBASE = 30'd0,
    parameter integer XQ_MUT = 0,
    parameter integer SPLIT_MUT = 0
) (
    input wire ck, input wire rst_n, input wire cfg_en, input wire cfg_layer, input wire [1:0] cfg_rank,
    input wire [52:0] f_ks, output wire [38:0] rco, input wire [267:0] pci,
    input wire [275:0] vi_s, output wire [275:0] vo_s, input wire [275:0] vi_n, output wire [275:0] vo_n,
    output wire [3:0] st
);
    wire [67:0] hx_w; wire [1151:0] res, res_m; wire [38:0] rco_e;
    // the dropped core pins (OWNER DECISION 8): rco sector bits [29:26] (old rco[35:32]) are PCBASE[29:26] (the atom
    // sector offset is 26 b, so with PCBASE[25:0] == 0 nothing carries into them); pci own [4:1] is not read by the core
    assign rco = rco_e;
    generate if (PCBASE[25:0] != 26'd0) begin : bad_req39_pcbase
        OT_S81ENG_REQ39_REQUIRES_ALIGNED_PCBASE invalid_configuration();
    end endgenerate
    dsdv_eng_rr_e #(.RETURN_AGE(RETURN_AGE), .PCBASE(PCBASE), .XQ_MUT(XQ_MUT)) u_e (.ck(ck), .rst_n(rst_n),
        .cfg_en(cfg_en), .cfg_layer(cfg_layer), .cfg_rank(cfg_rank), .f_ks(f_ks), .rco(rco_e), .pci({pci[267:5], pci[0]}), .vi_s(vi_s),
        .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .st(st), .hx_w(hx_w), .hx_res(res_m));
    dsdv_eng_rr_h0 u_h0 (.ck(ck), .in_w(hx_w), .out_res(res[575:0]));
    dsdv_eng_rr_h1 u_h1 (.ck(ck), .in_w(hx_w), .out_res(res[1151:576]));
    generate if (SPLIT_MUT == 2) begin : g_m2
        assign res_m = {res[575:0], res[1151:576]};
    end else if (SPLIT_MUT == 1) begin : g_m1
        assign res_m = res ^ (1152'd1 << 864);
    end else begin : g_m0
        assign res_m = res;
    end endgenerate
endmodule

module dsdv_eng_tap_c_req39 #(
    parameter bit WEST = 0,
    parameter [29:0] PCBASE = 30'd0,
    parameter integer RFD = 24,
    parameter integer EH  = 6,        // held Engram beats a lane: fixed 6 in the slices (a row's 9 atoms touch a PC once)
    parameter integer MUT = 0         // bench negative controls: 1 demux on g only (sc ignored), 2 pops not filtered
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [3:0]    sid,         // strap: controller index (PCs 2 sid, 2 sid + 1)
    input  wire [38:0]   rci,
    output reg  [38:0]   rco,
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
    ot_rst_relay_bounded32 #(.REGIONS(NR)) u_r (.clk(ck), .rst_n_in(rst_n), .rst_n(rl));
    // request chain forward
    always @(posedge ck or negedge rl[0]) if (!rl[0]) rco[0] <= 1'b0; else rco[0] <= rci[0];
    always @(posedge ck) rco[38:1] <= rci[38:1];
    // The removed sector prefix is constant only for an aligned region base.
    generate if (PCBASE[25:0] != 26'd0) begin : bad_req39_pcbase
        OT_S81ENG_REQ39_REQUIRES_ALIGNED_PCBASE invalid_configuration();
    end endgenerate
`ifdef OT_S81ENG_REQ39_MUT_SECTOR
    wire [3:0] sector_prefix = PCBASE[29:26] ^ 4'd1;
`else
    wire [3:0] sector_prefix = PCBASE[29:26];
`endif
    wire [42:0] request_full = {rci[38:32], sector_prefix, rci[31:0]};
    wire [9:0]  t10 = {1'b0, request_full[38:36], {1'b0, request_full[42:40]} + 4'd1, 1'b1, request_full[39]};
    wire [43:0] ew  = {t10, 4'd1, request_full[35:6]};
    // response chain slot
    reg [3:0]  gen;
    wire       pv_in = WEST ? 1'b0 : pci[0];
    wire [3:0] own   = WEST ? gen : pci[4:1];
    wire [1:0] fl, fxl;
    wire [9:0] bt0 = rri[6 +: 10], bt1 = rri[272 + 6 +: 10];
    wire       bv0 = rri[0], bv1 = rri[272];
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
    dsdv_eng_tap_rsc #(.MUT(MUT)) u_rs (.ck(ck), .rn(rl[5]), .sid(sd[3]), .rci(rci[5:0]), .pv_in(pv_in), .own(own),
        .bv0(bv0), .bt0(bt0), .bv1(bv1), .bt1(bt1), .rro_v0(rro_v0), .rro_v1(rro_v1), .pco_v(pco_v), .fxl(fxl));
    // hold-ring entries {d 256, col 3, atom 4} = {rri d, cell - 1, s3, slot3}
    wire [3:0]   colp0 = bt0[5:2] - 4'd1, colp1 = bt1[5:2] - 4'd1;
    wire [263:0] hin0 = {1'b0, rri[16 +: 256], colp0[2:0], bt0[0], bt0[8:6]};
    wire [263:0] hin1 = {1'b0, rri[272 + 16 +: 256], colp1[2:0], bt1[0], bt1[8:6]};
    wire [263:0] pcd  = {1'b0, pci[267:5]};
    wire [263:0] pcq;
    generate for (b = 0; b < NS; b = b + 1) begin : g_hs
        dsdv_eng_tap_hs #(.MUT(MUT),.W(SW)) u_s (.ck(ck), .rn0(rl[6 + 2 * b]), .rn1(rl[7 + 2 * b]), .sid(sd[b%4]), .pv_in(pv_in),
            .own(own), .bv0(bv0), .bt0(bt0), .bv1(bv1), .bt1(bt1), .hin0(hin0[SW * b +: SW]),
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

module dsdv_eng_tap_req39 #(parameter [29:0] PCBASE=30'd0) (
    input wire ck, input wire rst_n, input wire [3:0] sid,
    input wire [38:0] rci, output wire [38:0] rco, input wire [267:0] pci, output wire [267:0] pco,
    input wire [91:0] rqi, output wire [91:0] rqo, input wire [543:0] rri, output wire [543:0] rro, output wire fault
);
    dsdv_eng_tap_c_req39 #(.PCBASE(PCBASE),.WEST(0)) u_t (.ck(ck), .rst_n(rst_n), .sid(sid), .rci(rci), .rco(rco), .pci(pci), .pco(pco),
        .rqi(rqi), .rqo(rqo), .rri(rri), .rro(rro), .fault(fault));
endmodule

module dsdv_eng_tap_w_req39 #(parameter [29:0] PCBASE=30'd0) (
    input wire ck, input wire rst_n, input wire [3:0] sid,
    input wire [38:0] rci, output wire [267:0] pco,
    input wire [91:0] rqi, output wire [91:0] rqo, input wire [543:0] rri, output wire [543:0] rro, output wire fault
);
    wire [38:0] rco_end;              // chain end: the word is consumed here (decode only)
    dsdv_eng_tap_c_req39 #(.PCBASE(PCBASE),.WEST(1)) u_t (.ck(ck), .rst_n(rst_n), .sid(sid), .rci(rci), .rco(rco_end), .pci(268'd0),
        .pco(pco), .rqi(rqi), .rqo(rqo), .rri(rri), .rro(rro), .fault(fault));
endmodule
