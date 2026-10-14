// DISTINCT R1 VARIANT: coherent parent return relay adds one data edge; valid pipeline adds one matching edge.
// SOURCE-ONLY RSO CANDIDATE: new master/port; existing closed views do not bind this variant.
`timescale 1ns/1ps
// ot_engc_t_io (el1011-ds-misc/engram, 2026-10-11): ENDPOINT / VM tile of the all-tile dsfd_engram_c (top right, under
// c_cmd / t_vm / f_vm / f_cfg).  Every flop of the old composition's endpoint / done / VM side, inside one tile:
//   ot_s81_slab_ep (c_cmd / c_done / c_st), descriptor jn (1st stage) toward T_WIN, wn / jf pin flops from T_WIN,
//   done side = the (n / 8 + 1)-th rising edge of rdy[n mod 8] (MUT 5 early done / MUT 6 rdy level, as before),
//   rdy / perr delay: 2 stages in T_WIN + 5 here = 7 edges after the sink's = the latest write commit (bank 2),
//   f_vm pin flops, read request: one REGISTERED kept copy per bank tile {r_oh 6 (valid-folded group one-hot), r_a 8},
//   bank read data pin flops (6 edges after the request copies), SECDED decode registered, out regs, t_vm regs,
//   prefetch fault (sticky: write / read address fault, uncorrectable read) -> 2 stages -> the endpoint's slab fault.
//   Read: rd_v at the f_vm pins -> out_v on t_vm 14 edges later (old 11); valid-tagged.
module ot_engc_t_io_rso_r1 #(
    parameter integer MUT = 0,
    parameter integer EPMUT = 0,
    parameter [71:0] READ_INJECT = 72'd0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [84:0]   c_cmd,
    output wire [8:0]    c_done,
    output wire [1:0]    c_st,
    input  wire [2:0]    f_cfg,
    output reg  [2:0]    cfg_o,
    input  wire [15:0]   f_vm,           // {rel_slot 3, rel_v, rd_addr 11, rd_v}
    output wire [531:0]  t_vm,           // {perr 8, rdy 8, fault, ue, ce, data 512, out_v}
    // T_WIN seams
    input  wire [7:0]    rdy_i, perr_i,
    output wire [3:0]    vrel_o,         // the f_vm pin flops (registered, no logic)
    output reg  [17:0]   jn_o,
    input  wire [15:0]   wn_i,
    input  wire          jf_i,
    input  wire          werr_i,
    // bank tiles
    output reg  [5:0]    r0_oh, r1_oh, r2_oh,
    output reg  [7:0]    r0_a, r1_a, r2_a,
    input  wire [255:0]  rd0, rd1,
    input  wire [63:0]   rd2
,
    output wire rso
);
    reg [1:0] rs_q;
    always @(posedge ck or negedge rst) if (!rst) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    wire ep_rso;
    assign rso = rn && ep_rso;
    always @(posedge ck) cfg_o <= f_cfg;

    // ---------------- endpoint
    wire j_v, j_new; wire [83:0] j_d, j_new_d; wire ep_fault;
    reg j_done; reg jf_q; reg [15:0] wn_q; reg [1:0] pff_r; reg pf_fault;
    ot_s81_slab_ep_rso #(.QD(8), .JQ(8), .MUT(EPMUT)) u_ep (.c_clk(ck), .c_rst_n(rst), .c_cmd(c_cmd), .c_done(c_done),
        .c_st(c_st), .e_clk(ck), .e_rst_n(rn), .j_v(j_v), .j_d(j_d), .j_new(j_new), .j_new_d(j_new_d),
        .j_present(1'b1), .j_done(j_done), .slab_fault(jf_q | pff_r[1]), .ep_fault(ep_fault), .rso(ep_rso));
    always @(posedge ck or negedge rn)
        if (!rn) begin jn_o <= 18'd0; wn_q <= 16'd0; jf_q <= 1'b0; pff_r <= 2'b00; end
        else begin jn_o <= {j_new, (j_new_d[30:23] != 8'd0), j_new_d[22:7]}; wn_q <= wn_i; jf_q <= jf_i;
                   pff_r <= {pff_r[0], pf_fault}; end

    // ---------------- rdy / perr delay (stages 3..7)
    reg [7:0] rdy_3, rdy_4, rdy_5, rdy_6, rdy_p, perr_3, perr_4, perr_5, perr_6, perr_p;
    always @(posedge ck or negedge rn)
        if (!rn) begin rdy_3 <= 0; rdy_4 <= 0; rdy_5 <= 0; rdy_6 <= 0; rdy_p <= 0;
                       perr_3 <= 0; perr_4 <= 0; perr_5 <= 0; perr_6 <= 0; perr_p <= 0; end
        else begin rdy_3 <= rdy_i; rdy_4 <= rdy_3; rdy_5 <= rdy_4; rdy_6 <= rdy_5; rdy_p <= rdy_6;
                   perr_3 <= perr_i; perr_4 <= perr_3; perr_5 <= perr_4; perr_6 <= perr_5; perr_p <= perr_6; end

    // ---------------- VM requests
    reg vrel_q, vrd_q; reg [2:0] vrels_q; reg [10:0] vra_q;
    always @(posedge ck or negedge rn) if (!rn) begin vrel_q <= 1'b0; vrd_q <= 1'b0; end
                                       else begin vrel_q <= f_vm[12]; vrd_q <= f_vm[0]; end
    always @(posedge ck) begin vrels_q <= f_vm[15:13]; vra_q <= f_vm[11:1]; end
    assign vrel_o = {vrels_q, vrel_q};
    wire rd_ok = vra_q[7:3] < 24;
    wire [10:0] rcmp = ({8'd0, vra_q[10:8]} << 7) + ({8'd0, vra_q[10:8]} << 6) + {3'd0, vra_q[7:0]};
    wire [5:0] roh = {6{vrd_q && rd_ok}} & (6'd1 << rcmp[10:8]);
    reg rerr_q, werr_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin r0_oh <= 0; r1_oh <= 0; r2_oh <= 0; rerr_q <= 1'b0; werr_q <= 1'b0; end
        else begin r0_oh <= roh; r1_oh <= roh; r2_oh <= roh; rerr_q <= vrd_q && !rd_ok; werr_q <= werr_i; end
    always @(posedge ck) begin r0_a <= rcmp[7:0]; r1_a <= rcmp[7:0]; r2_a <= rcmp[7:0]; end

    // ---------------- read data: pin flops, decode, out
    reg [575:0] rc_q;
    always @(posedge ck) rc_q <= {rd2, rd1, rd0};
    reg [9:0] rv_q;                                  // rv_q[9] aligned with rc_q
    always @(posedge ck or negedge rn) if (!rn) rv_q <= 10'd0; else rv_q <= {rv_q[8:0], vrd_q && rd_ok};
    wire [511:0] dec; wire [7:0] ce, ue;
    genvar l;
    generate for (l = 0; l < 8; l = l + 1) begin : g_dec
        ot_s81_secded_dec72 u_dec (.c(rc_q[72*l+:72] ^ (l == 0 ? READ_INJECT : 72'd0)), .d(dec[64*l+:64]),
            .ce(ce[l]), .ue(ue[l]));
    end endgenerate
    reg [511:0] d7_q, od_q, tvd_q; reg [7:0] ce7_q, ue7_q; reg v7_q, ov_q, oce_q, oue_q, tvv_q; reg [18:0] tvs_q;
    always @(posedge ck) begin d7_q <= dec; od_q <= d7_q; tvd_q <= od_q; end
    always @(posedge ck or negedge rn)
        if (!rn) begin v7_q <= 0; ce7_q <= 0; ue7_q <= 0; ov_q <= 0; oce_q <= 0; oue_q <= 0; pf_fault <= 0;
                       tvs_q <= 19'd0; tvv_q <= 1'b0; end
        else begin
            v7_q <= rv_q[9]; ce7_q <= ce & {8{rv_q[9]}}; ue7_q <= ue & {8{rv_q[9]}};
            ov_q <= v7_q; oce_q <= v7_q && (|ce7_q); oue_q <= v7_q && (|ue7_q);
            if (werr_q || rerr_q || oue_q) pf_fault <= 1'b1;
            tvs_q <= {perr_p, rdy_p, pf_fault, oue_q, oce_q}; tvv_q <= ov_q;
        end
    assign t_vm = {tvs_q, tvd_q, tvv_q};

    // ---------------- done side
    reg [7:0] rdy_d; reg [12:0] rise [0:7]; reg [15:0] dn; integer s;
    wire [2:0]  dslot = dn[2:0];
    wire [12:0] depo  = dn[15:3] + 1'b1;
    wire        dhit  = (MUT == 6) ? rdy_p[dslot] : (rise[dslot] == depo);
    always @(posedge ck or negedge rn)
        if (!rn) begin rdy_d <= 8'd0; dn <= 0; j_done <= 1'b0; for (s = 0; s < 8; s = s + 1) rise[s] <= 13'd0; end
        else begin
            rdy_d <= rdy_p;
            for (s = 0; s < 8; s = s + 1) if (rdy_p[s] && !rdy_d[s]) rise[s] <= rise[s] + 1'b1;
            j_done <= 1'b0;
            if (j_v && !j_done && dn != wn_q && (MUT == 5 ? 1'b1 : dhit)) begin j_done <= 1'b1; dn <= dn + 1'b1; end
        end
endmodule
