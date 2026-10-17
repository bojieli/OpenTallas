`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-1 (2026-10-17): dsdv_gunit -- the S81-DV G-unit (column 3, 680 x 4035 um, six stacked leaves), whole unit.
//
// Interface (p4f/p4h): the column-3 V rung only, s_3S <-> gunit <-> s_3N, 276 b each way, plus the configuration / job
// port cw (p4i: from seq_host; a registered write port, statically scheduled) and the CTL source-id strap sid.
//   u_vs   ot_dsdv_vstop   L2   the V-rung stop: 2 edges pin -> pin both ways; taps + sinks SC (kind 5, router scores)
//                               and HP (kind 7, HC projection partial roots -- PROPOSED kind, p4i adopts it; format in
//                               dsdv_gunit_hcf); injects the unit's CTL row writes both ways on one edge
//   u_rt   dsdv_gunit_rt   L1/L3 router: bias + top-6 select (ot_dsrom_su_bias_select = ot_hdc_select_tree + bias add),
//                               routing-weight normalisation (ot_s81_su_rw); ids row first, weights after
//   u_hc   dsdv_gunit_hcf  L0/L4/L5 HC coefficients: HP root store, golden-tree finish, rsqrt, mixes, exact tail
//                               (ot_hbm_hc_tail_unit_static: sigmoid / exp / Sinkhorn on the /SDIV derived clock)
// CTL: both groups' row writes leave on the rung both ways on the same edge (each slice's xr re-injects them on its tier
// line).  The compiler keeps those rung slots free and never schedules the two groups' writes on the same edge; a
// collision is a sticky fault (no arbitration, no ready, no credit).
// cw: cw_a[9] = 0 table row write (set cw_a[8], row cw_a[5:0]: 0..55 router bias, 56..61 HC bases, 62 scales / route
// scale / eps); cw_a[9:8] = 2'b10 job (cw_a[0] = 0 router, 1 HC).  Field layouts: dsdv_gunit_rt / dsdv_gunit_hcf.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only) is passed to the groups.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit #(
    parameter integer V    = 276,
    parameter integer NSET = 2,
    parameter integer SDIV = 8,
    parameter integer MUT  = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,      // from / to s_3S
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,      // from / to s_3N
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d,
    output reg           fault
);
    localparam [7:0] KSC = 8'h20, KHP = 8'h80;
    wire dl_nv, dl_sv, f_vs, f_rt, f_hc, rt_v, hc_v; wire [V-1:0] dl_n, dl_s, rt_b, hc_b;
    reg ct_v; reg [V-1:0] ct_b; reg col;
    ot_dsdv_vstop #(.V(V)) u_vs (.clk(clk), .rst_n(rst_n), .tap_k(KSC | KHP), .sink_k(KSC | KHP),
        .vi_s(vi_s), .vo_n(vo_n), .vi_n(vi_n), .vo_s(vo_s), .dl_nv(dl_nv), .dl_n(dl_n), .dl_sv(dl_sv), .dl_s(dl_s),
        .in_nv(ct_v), .in_n(ct_b), .in_sv(ct_v), .in_s(ct_b), .fault(f_vs));
    // kind split of the delivered beats (registered, so each group's input flop sees one cycle of decode)
    reg sa_v, sb_v, ha_v, hb_v; reg [V-1:0] na_b, sb_b;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sa_v <= 1'b0; sb_v <= 1'b0; ha_v <= 1'b0; hb_v <= 1'b0; end
        else begin
            sa_v <= dl_nv && dl_n[3:1] == 3'd5; ha_v <= dl_nv && dl_n[3:1] == 3'd7;
            sb_v <= dl_sv && dl_s[3:1] == 3'd5; hb_v <= dl_sv && dl_s[3:1] == 3'd7;
        end
    always @(posedge clk) begin na_b <= dl_n; sb_b <= dl_s; end
    dsdv_gunit_rt #(.V(V), .NSET(NSET), .MUT(MUT)) u_rt (.clk(clk), .rst_n(rst_n), .sid(sid), .sa_v(sa_v), .sa_b(na_b),
        .sb_v(sb_v), .sb_b(sb_b), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .ct_v(rt_v), .ct_b(rt_b), .fault(f_rt));
    dsdv_gunit_hcf #(.V(V), .NSET(NSET), .SDIV(SDIV), .MUT(MUT)) u_hc (.clk(clk), .rst_n(rst_n), .sid(sid), .ha_v(ha_v),
        .ha_b(na_b), .hb_v(hb_v), .hb_b(sb_b), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .ct_v(hc_v), .ct_b(hc_b),
        .fault(f_hc));
    // CTL merge (registered): the compiler never schedules both groups on one edge
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ct_v <= 1'b0; col <= 1'b0; end
        else begin ct_v <= rt_v || hc_v; col <= col || (rt_v && hc_v); end
    always @(posedge clk) ct_b <= rt_v ? rt_b : hc_b;
    always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= f_vs | f_rt | f_hc | col;   // output flop
endmodule
