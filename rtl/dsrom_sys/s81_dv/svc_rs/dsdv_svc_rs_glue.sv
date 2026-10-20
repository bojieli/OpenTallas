`timescale 1ns/1ps
// PL-SVC (10-18): the glue children of dsdv_svc_rs_f (moved unchanged out of dsdv_svc_rs_c; see dsdv_svc_rs_f.sv)
// ---------------------------------------------------------------------------------------------------------------------
// the slice's reset synchroniser + role register (dsdv_svc_rs_c lines `rs` / `role` / `pvs`, unchanged)
module dsdv_svc_rs_rl #(parameter integer ST = 0) (
    input  wire        ck,
    input  wire        rst,
    input  wire [3:0]  sid,
    output wire        rn,
    output reg  [21:0] role,
    output reg  [7:0]  pvs
);
`include "dsdv_svc_rs_roles.svh"
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    assign rn = rs[1];
    always @(posedge ck or negedge rn) if (!rn) begin role <= '0; pvs <= 8'd255; end
        else begin role <= rs_role(sid); pvs <= rs_pvslot(2'(ST), sid); end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// dn stream tree node (the centre register takes the parent face, or at the entry (parent 0) the host stream hst;
// non-entry slices tie hst to 0 as dsdv_svc_rs_c's g_nohost)
module dsdv_svc_rs_dn #(parameter integer ST = 0) (
    input  wire             ck,
    input  wire             rst,
    input  wire [3:0]       sid,
    input  wire [804:0]     hst,
    input  wire [4*805-1:0] dn_i,
    output wire [4*805-1:0] dn_o,
    output reg  [804:0]     cs,
    output reg              dstray
);
    localparam integer DW = 805;
    wire rn; wire [21:0] role; wire [7:0] pvs;
    dsdv_svc_rs_rl #(.ST(ST)) u_rl (.ck(ck), .rst(rst), .sid(sid), .rn(rn), .role(role), .pvs(pvs));
    wire [3:0] chm = role[7:4];
    wire [2:0] par = role[10:8];
    genvar f;
    wire [DW-1:0] dfi [0:3];
    generate for (f = 0; f < 4; f = f + 1) begin : g_di
        reg [DW-1:0] p0, p1;
        always @(posedge ck or negedge rn) if (!rn) begin p0[0] <= 1'b0; p0[513] <= 1'b0; p1[0] <= 1'b0; p1[513] <= 1'b0; end
            else begin p0[0] <= dn_i[DW*f]; p0[513] <= dn_i[DW*f + 513]; p1[0] <= p0[0]; p1[513] <= p0[513]; end
        always @(posedge ck) begin p0[512:1] <= dn_i[DW*f + 1 +: 512]; p0[DW-1:514] <= dn_i[DW*f + 514 +: DW - 514];
                                   p1[512:1] <= p0[512:1]; p1[DW-1:514] <= p0[DW-1:514]; end
        assign dfi[f] = p1;
    end endgenerate
    wire [DW-1:0] cin = (par == 3'd0) ? hst : dfi[par - 3'd1];
    always @(posedge ck or negedge rn) if (!rn) begin cs[0] <= 1'b0; cs[513] <= 1'b0; end
        else begin cs[0] <= cin[0]; cs[513] <= cin[513]; end
    always @(posedge ck) begin cs[512:1] <= cin[512:1]; cs[DW-1:514] <= cin[DW-1:514]; end
    generate for (f = 0; f < 4; f = f + 1) begin : g_do
        reg [DW-1:0] o0, o1;
        always @(posedge ck or negedge rn) if (!rn) begin o0[0] <= 1'b0; o0[513] <= 1'b0; o1[0] <= 1'b0; o1[513] <= 1'b0; end
            else begin o0[0] <= cs[0] && chm[f]; o0[513] <= cs[513] && chm[f]; o1[0] <= o0[0]; o1[513] <= o0[513]; end
        always @(posedge ck) begin o0[512:1] <= cs[512:1]; o0[DW-1:514] <= cs[DW-1:514];
                                   o1[512:1] <= o0[512:1]; o1[DW-1:514] <= o0[DW-1:514]; end
        assign dn_o[DW*f +: DW] = o1;
    end endgenerate
    always @(posedge ck or negedge rn) if (!rn) dstray <= 1'b0;
        else for (int i = 0; i < 4; i++) if ((dfi[i][0] || dfi[i][513]) && par != 3'(i + 1)) dstray <= 1'b1;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// attention share + its role inputs (root = ENTRY: ROOT 1 on the entry slices)
module dsdv_svc_rs_attw #(parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                          parameter integer SRAM_MACRO = 0, parameter integer ROOT = 0, parameter integer PMEM = 1,
                          parameter integer TEXT = 0, parameter integer TLX = 0, parameter integer TXD = 0) (
    input  wire             ck,
    input  wire             rst,
    input  wire [3:0]       sid,
    input  wire [804:0]     cs,
    output wire [2*341-1:0] qrq,
    input  wire [1:0]       qrk,
    input  wire [1:0]       qwd,
    input  wire [1:0]       qrv,
    input  wire [2*256-1:0] qr_data,
    input  wire [2*17-1:0]  qr_tag,
    input  wire [2*4-1:0]   qr_beat,
    output wire             l_v,
    output wire [2131:0]    l_d,
    output wire             pv_ov,
    output wire [512:0]     pv_od,
    output wire             sm_st,
    output wire [3:0]       sm_kind,
    output wire [7:0]       sm_jid,
    output wire             sm_rv,
    output wire             sm_rp,
    output wire [2:0]       sm_rj,
    output wire [511:0]     sm_rd,
    output wire             go_o,
    output wire [9:0]       tjob_o,
    output wire             done,
    output wire [7:0]       tagj,
    output wire [1:0]       hcr,
    output wire [1:0]       hack,
    output wire             fault,
    // SVC4 landed engine (TEXT 1): engine tile t's input bundle (1,618 b) out / output bundle (529 b) back, one port per
    // tile so each lands in its own region (dsdv_svc_attw_f -> dsdv_svc_attw_f_lp); unused when TEXT 0
    output wire [1617:0]    tx_i0, output wire [1617:0] tx_i1, output wire [1617:0] tx_i2, output wire [1617:0] tx_i3,
    input  wire [528:0]     tx_o0, input  wire [528:0]  tx_o1, input  wire [528:0]  tx_o2, input  wire [528:0]  tx_o3
);
    wire rn; wire [21:0] role; wire [7:0] pvs;
    dsdv_svc_rs_rl #(.ST(ST)) u_rl (.ck(ck), .rst(rst), .sid(sid), .rn(rn), .role(role), .pvs(pvs));
    wire [3:0] tile = role[3:0];
`ifdef RS_MUT_GD
    wire [7:0] gd = role[21:14] + 8'(sid == 4'd0);    // bench negative control: one slice starts a cycle late
`else
    wire [7:0] gd = role[21:14];
`endif
    wire [31:0] a_fc;
    dsdv_svc_att #(.MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO != 0), .PMEM(PMEM), .TEXT(TEXT), .TLX(TLX),
                   .TXD(TXD)) u_att (
        .clk(ck), .rst_n(rn), .sid(sid), .tile(tile), .gd(gd), .pvs(pvs), .root(ROOT != 0),
        .q_v(cs[0]), .q_d(cs[512:1]), .hw_v(cs[513]), .hw_d(cs[804:514]),
        .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat),
        .l_v(l_v), .l_d(l_d), .pv_ov(pv_ov), .pv_od(pv_od),
        .sm_st(sm_st), .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd),
        .go_o(go_o), .tjob_o(tjob_o), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(fault), .fault_code(a_fc),
        .tx_i({tx_i3, tx_i2, tx_i1, tx_i0}), .tx_o({tx_o3, tx_o2, tx_o1, tx_o0}));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// SE row assembler (tap -> 16-score SE rows) + SM row mux + collision fault (dsdv_svc_rs_c, unchanged)
module dsdv_svc_rs_se (
    input  wire         ck,
    input  wire         rst,
    input  wire         t_v,
    input  wire [19:0]  t_tag,
    input  wire [127:0] t_y,
    input  wire [3:0]   t_f,
    input  wire [9:0]   tjob,
    input  wire         go,
    input  wire         sm_rv,
    input  wire         sm_rp,
    input  wire [2:0]   sm_rj,
    input  wire [511:0] sm_rd,
    output wire         r_v,
    output wire         r_p,
    output wire [2:0]   r_j,
    output wire [511:0] r_d,
    output reg          rcol
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [511:0] se_acc, se_d; reg se_v, se_flag;
    wire [15:0] t_row = t_tag[19:4]; wire [3:0] t_m = t_tag[3:0];
    wire [2:0] t_n = 3'(t_m[0]) + 3'(t_m[1]) + 3'(t_m[2]) + 3'(t_m[3]);
    wire t_last = (t_row[3:2] == 2'd3) || (32'(t_row) + 32'(t_n) >= 32'(tjob));
    reg [511:0] se_nxt;
    always @(*) begin
        se_nxt = se_acc;
        for (int i = 0; i < 4; i++) if (t_m[i]) se_nxt[32 * (4 * t_row[3:2] + i) +: 32] = t_y[32*i +: 32];
            else se_nxt[32 * (4 * t_row[3:2] + i) +: 32] = 32'd0;
    end
    always @(posedge ck) begin
        if (t_v) se_acc <= t_last ? 512'd0 : se_nxt;
        if (t_v && t_last) se_d <= se_nxt;
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin se_v <= 1'b0; se_flag <= 1'b0; end
        else begin
            se_v <= t_v && t_last;
            if (go) se_flag <= 1'b0; else if (t_v && |(t_f & t_m)) se_flag <= 1'b1;
        end
    assign r_v = se_v || sm_rv;
    assign r_p = se_v ? 1'b0 : sm_rp;
    assign r_j = se_v ? 3'd0 : sm_rj;
    assign r_d = se_v ? se_d : sm_rd;
    always @(posedge ck or negedge rn) if (!rn) rcol <= 1'b0; else if (se_v && sm_rv) rcol <= 1'b1;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// the slice's SM share + its head strap
module dsdv_svc_rs_smw (
    input  wire         ck,
    input  wire         rst,
    input  wire [3:0]   sid,
    input  wire         j_st,
    input  wire [3:0]   j_kind,
    input  wire [7:0]   j_jid,
    input  wire         r_v,
    input  wire         r_p,
    input  wire [2:0]   r_j,
    input  wire [511:0] r_d,
    output wire         w_v,
    output wire [13:0]  w_a,
    output wire [15:0]  w_m,
    output wire [511:0] w_d,
    output wire [11:0]  w_st,
    output wire         o_fo
);
    wire rn; wire [21:0] role; wire [7:0] pvs;
    dsdv_svc_rs_rl #(.ST(0)) u_rl (.ck(ck), .rst(rst), .sid(sid), .rn(rn), .role(role), .pvs(pvs));
    wire o_fu, o_alive, o_den; wire [7:0] o_rjid;
    ot_s81_su_sms u_sms (.clk(ck), .rst_in(rst), .cfg_g(role[3:0]), .j_st(j_st), .j_kind(j_kind), .j_jid(j_jid),
        .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(r_d),
        .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rjid(o_rjid));
    assign w_st = {o_rjid, o_den, o_alive, o_fo, o_fu};
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// P.V return tree node (ENTRY 1: the half's return tree root word pv_v / pv_d; non-entry leaves them open)
module dsdv_svc_rs_pv #(parameter integer ST = 0, parameter integer ENTRY = 0) (
    input  wire             ck,
    input  wire             rst,
    input  wire [3:0]       sid,
    input  wire [4*514-1:0] ri,
    output wire [4*514-1:0] ro,
    input  wire             a_pv_v,
    input  wire [512:0]     a_pv_d,
    output reg              r_f,
    output reg              pv_v,
    output reg  [512:0]     pv_d
);
    localparam integer RW = 514;
    wire rn; wire [21:0] role; wire [7:0] pvs;
    dsdv_svc_rs_rl #(.ST(ST)) u_rl (.ck(ck), .rst(rst), .sid(sid), .rn(rn), .role(role), .pvs(pvs));
    wire [3:0] chm = role[7:4];
    wire [2:0] par = role[10:8];
    genvar f;
    wire [RW-1:0] rfi [0:3];
    generate for (f = 0; f < 4; f = f + 1) begin : g_ri
        reg p0v, p1v; reg [RW-2:0] p0d, p1d;
        always @(posedge ck or negedge rn) if (!rn) begin p0v <= 1'b0; p1v <= 1'b0; end
            else begin p0v <= ri[RW*f]; p1v <= p0v; end
        always @(posedge ck) begin p0d <= ri[RW*f + 1 +: RW - 1]; p1d <= p0d; end
        assign rfi[f] = {p1d, p1v};
    end endgenerate
    reg rm_v; reg [RW-2:0] rm_d;
    always @(posedge ck or negedge rn)
        if (!rn) begin rm_v <= 1'b0; r_f <= 1'b0; end
        else begin
            reg [2:0] n;
            n = 3'(a_pv_v);
            for (int i = 0; i < 4; i++) begin
                if (rfi[i][0] && chm[i]) n = n + 1'b1;
                if (rfi[i][0] && !chm[i]) r_f <= 1'b1;
            end
            if (n > 3'd1) r_f <= 1'b1;
            rm_v <= n != 0;
        end
    always @(posedge ck) begin
        rm_d <= a_pv_d;
        for (int i = 0; i < 4; i++) if (rfi[i][0] && chm[i]) rm_d <= rfi[i][RW-1:1];
    end
    generate for (f = 0; f < 4; f = f + 1) begin : g_ro
        reg o0v, o1v; reg [RW-2:0] o0d, o1d;
        always @(posedge ck or negedge rn) if (!rn) begin o0v <= 1'b0; o1v <= 1'b0; end
            else begin o0v <= rm_v && par == 3'(f + 1); o1v <= o0v; end
`ifdef RS_MUT_RO
        always @(posedge ck) begin o0d <= rm_d ^ {511'd0, (sid == 4'd7 || sid == 4'd9), 1'b0}; o1d <= o0d; end
`else
        always @(posedge ck) begin o0d <= rm_d; o1d <= o0d; end
`endif
        assign ro[RW*f +: RW] = {o1d, o1v};
    end endgenerate
    always @(posedge ck or negedge rn) if (!rn) pv_v <= 1'b0; else pv_v <= (ENTRY != 0) && rm_v && par == 3'd0;
    always @(posedge ck) pv_d <= rm_d;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// up tree, split in two lanes (PL-SVC 10-18, coordinator decision PARENTS-LANDED option (a)) so that the job END / done
// reduce never sees the SM head's fault o_fo (which lives in clock region sm and is LANDED into region c):
//   up_d = {done, cr 6, ack 6}   (dsdv_svc_rs_up bits [13], [11:0]) : dsdv_svc_rs_ud, offset 0 in the landed slice
//   up_f = {rg fault, rg live, fault} (bits [15], [14], [12])         : dsdv_svc_rs_uf, behind the o_fo landing
// Same fold (done = AND, fault = OR, credits / acks = sum, rg fault = OR, rg live = AND over the child faces) and the
// same 5-cycle hop (face in: pin flop + relay; centre register; face out: register + pin flop) as dsdv_svc_rs_up.
module dsdv_svc_rs_ud #(parameter integer ST = 0) (
    input  wire            ck,
    input  wire            rst,
    input  wire [3:0]      sid,
    input  wire            done,
    input  wire [1:0]      hcr,
    input  wire [1:0]      hack,
    input  wire [4*13-1:0] up_d_i,
    output wire [4*13-1:0] up_d_o,
    output reg  [12:0]     ucd             // {done, cr 6, ack 6} of the subtree (the entry's job gate / host credits)
);
    localparam integer UW = 13;
    wire rn; wire [21:0] role; wire [7:0] pvs;
    dsdv_svc_rs_rl #(.ST(ST)) u_rl (.ck(ck), .rst(rst), .sid(sid), .rn(rn), .role(role), .pvs(pvs));
    wire [3:0] chm = role[7:4];
    wire [2:0] par = role[10:8];
    genvar f;
    wire [UW-1:0] ufi [0:3];
    generate for (f = 0; f < 4; f = f + 1) begin : g_ui
        reg [UW-1:0] p0, p1;
        always @(posedge ck or negedge rn) if (!rn) begin p0 <= '0; p1 <= '0; end
            else begin p0 <= up_d_i[UW*f +: UW]; p1 <= p0; end
        assign ufi[f] = p1;
    end endgenerate
    always @(posedge ck or negedge rn)
        if (!rn) ucd <= '0;
        else begin
            reg dn_all; reg [5:0] c6, a6;
            dn_all = done; c6 = 6'(hcr); a6 = 6'(hack);
            for (int i = 0; i < 4; i++) if (chm[i]) begin
                dn_all = dn_all & ufi[i][12]; c6 = c6 + ufi[i][11:6]; a6 = a6 + ufi[i][5:0];
            end
            ucd <= {dn_all, c6, a6};
        end
    generate for (f = 0; f < 4; f = f + 1) begin : g_uo
        reg [UW-1:0] o0, o1;
        always @(posedge ck or negedge rn) if (!rn) begin o0 <= '0; o1 <= '0; end
            else begin o0 <= (par == 3'(f + 1)) ? ucd : '0; o1 <= o0; end
        assign up_d_o[UW*f +: UW] = o1;
    end endgenerate
endmodule

// local fault OR + ctrl_rg2 hs status synchroniser + the up_f lane node {rg fault, rg live, fault}
module dsdv_svc_rs_uf #(parameter integer ST = 0) (
    input  wire            ck,
    input  wire            rst,
    input  wire [3:0]      sid,
    input  wire [1:0]      hs,
    input  wire            a_f,
    input  wire            x_f,
    input  wire            rcol,
    input  wire            o_fo,
    input  wire            dstray,
    input  wire            r_f,
    input  wire [4*3-1:0]  up_f_i,
    output wire [4*3-1:0]  up_f_o,
    output reg  [2:0]      ucf,            // {rg fault, rg live, fault} of the subtree (entry: fault / st_rg)
    output wire            hl              // this slice's synchronised hs live (RS_MUT_ST negative control only)
);
    localparam integer UW = 3;
    wire rn; wire [21:0] role; wire [7:0] pvs;
    dsdv_svc_rs_rl #(.ST(ST)) u_rl (.ck(ck), .rst(rst), .sid(sid), .rn(rn), .role(role), .pvs(pvs));
    wire [3:0] chm = role[7:4];
    wire [2:0] par = role[10:8];
    wire lf = a_f | x_f | rcol | o_fo | dstray | r_f;
    (* async_reg = "true" *) reg [1:0] hs0, hs1;
    reg hs_up, hs_hf, hs_f;
    always @(posedge ck or negedge rn)
        if (!rn) begin hs0 <= 2'b00; hs1 <= 2'b00; hs_up <= 1'b0; hs_hf <= 1'b0; hs_f <= 1'b0; end
        else begin
            hs0 <= hs; hs1 <= hs0;
            if (hs1[0]) hs_up <= 1'b1;
            if (hs1[1] || (hs_up && !hs1[0])) hs_hf <= 1'b1;
            hs_f <= lf | hs_hf;
        end
    assign hl = hs1[0];
    genvar f;
    wire [UW-1:0] ufi [0:3];
    generate for (f = 0; f < 4; f = f + 1) begin : g_ui
        reg [UW-1:0] p0, p1;
        always @(posedge ck or negedge rn) if (!rn) begin p0 <= '0; p1 <= '0; end
            else begin p0 <= up_f_i[UW*f +: UW]; p1 <= p0; end
        assign ufi[f] = p1;
    end endgenerate
    always @(posedge ck or negedge rn)
        if (!rn) ucf <= '0;
        else begin
            reg fl_, rgf, rgl;
            fl_ = hs_f; rgf = hs1[1]; rgl = hs1[0];
            for (int i = 0; i < 4; i++) if (chm[i]) begin
                fl_ = fl_ | ufi[i][0]; rgf = rgf | ufi[i][2]; rgl = rgl & ufi[i][1];
            end
            ucf <= {rgf, rgl, fl_};
        end
    generate for (f = 0; f < 4; f = f + 1) begin : g_uo
        reg [UW-1:0] o0, o1;
        always @(posedge ck or negedge rn) if (!rn) begin o0 <= '0; o1 <= '0; end
            else begin o0 <= (par == 3'(f + 1)) ? ucf : '0; o1 <= o0; end
        assign up_f_o[UW*f +: UW] = o1;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ENTRY host endpoint (dsdv_svc_rs_c g_host + the done / credit half of g_rt, unchanged): host pins (pin flop) -> job
// gate ot_s81_svc_job (same cycle) -> relay = the dn centre input hst; the synthetic END result word rad from the up_d
// done edge; host credits hc from the up_d credit / ack sums.  Region c: the END loop job -> dn -> att -> done -> up_d
// -> rad -> job stays inside one clock region (it never sees the SM head).
module dsdv_svc_rs_eh (
    input  wire         ck,
    input  wire         rst,
    input  wire [32:0]  j,
    input  wire [514:0] q,
    input  wire [291:0] hw,
    input  wire [12:0]  ucd,
    input  wire [7:0]   tagj,
    output wire [804:0] hst,
    output wire [1:0]   jdc,
    output reg  [8:0]   hc
);
    localparam integer DW = 805;
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [513:0] rad;
    reg [514:0] qp; reg [291:0] hp;
    always @(posedge ck or negedge rn) if (!rn) begin qp[0] <= 1'b0; hp[0] <= 1'b0; end
        else begin qp[0] <= q[0]; hp[0] <= hw[0]; end
    always @(posedge ck) begin qp[514:1] <= q[514:1]; hp[291:1] <= hw[291:1]; end
    wire [514:0] cq;
    ot_s81_svc_job #(.MUT(0)) u_job (.ck(ck), .rs_n(rn), .j_cmd(j), .j_dn(jdc), .q(qp), .core_q(cq),
        .ad({513'd0, rad[512:0]}), .xd({512'd0, 1'b0, 1'b1}), .od({512'd0, 1'b0, 1'b1}));
    reg [DW-1:0] r1;
    always @(posedge ck or negedge rn) if (!rn) begin r1[0] <= 1'b0; r1[513] <= 1'b0; end
        else begin r1[0] <= cq[0]; r1[513] <= hp[0]; end
    always @(posedge ck) begin r1[512:1] <= cq[512:1]; r1[DW-1:514] <= hp[291:1]; end
    assign hst = r1;
    reg dprev; reg [7:0] crc;
    always @(posedge ck or negedge rn)
        if (!rn) begin dprev <= 1'b0; rad <= '0; crc <= 0; hc <= 0; end
        else begin
            dprev <= ucd[12];
            rad[0] <= ucd[12] && !dprev;
            rad[512:1] <= {4'd8, 1'b1, 4'd0, tagj, 3'd0, 12'd0, 480'd0};
            crc <= crc + 8'(ucd[11:6]) - 8'(crc != 0);
            hc <= {2'b00, ucd[5:0], crc != 0};
        end
endmodule

// ENTRY fault / region status (the fault half of dsdv_svc_rs_c g_rt, unchanged): the half's sticky fault from the up_f
// fold, folded into the job-done fault bit; st_rg = the up_f region status {fault OR, live AND}
module dsdv_svc_rs_ef (
    input  wire        ck,
    input  wire        rst,
    input  wire [1:0]  jdc,
    input  wire [2:0]  ucf,
    input  wire        hl,
    output wire [1:0]  jd,
    output wire        fault,
    output reg  [1:0]  st_rg
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg flt;
    always @(posedge ck or negedge rn) if (!rn) flt <= 1'b0; else if (ucf[0]) flt <= 1'b1;
    assign jd = {jdc[1] | flt, jdc[0]};
    assign fault = flt;
`ifdef RS_MUT_ST
    always @(posedge ck or negedge rn) if (!rn) st_rg <= 2'b00; else st_rg <= {ucf[2], hl};   // NEG CTRL (as dsdv_svc_rs_c)
`else
    always @(posedge ck or negedge rn) if (!rn) st_rg <= 2'b00; else st_rg <= ucf[2:1];
`endif
endmodule
