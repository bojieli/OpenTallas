// HELD structural candidate: 45 independent compensated entries. All64 MACs and10 physical ROMs retained.
// Added roots:8 TX(780FFeach),5 faces,5 bank pair1,2 RQR. Existing clock/data stages unchanged.
// Physical adoption requires assigned pin file, localized placement, CTS/native/TT/FF/DRC and regional die clock proof.
`timescale 1ns/1ps
// Q-TILE-REPACK (2026-10-15, owner 20:35: re-pack the 64-lane compute tile to ~60 % fill, KEEP 64 MAC lanes):
// qfd_tile_nk_rp2_45 = qfd_tile_nk (rtl/physical/qfd_tile_nk_slot.sv) with the ROM pair pipeline SOFT in the tile parent
// (RPH 1: one ot_qwen_rpair_logic per bank row, the same logic the hardened leaf ot_qwen_tile_rpair holds) and the 10
// ROM macros ot_rom_4096x266_m8 placed directly in the tile (u_tile.u_tile.g_col[p].g_bank[b].u_rom).  The closed rpair
// leaf boxed 2 macros + channels in 311 x 130 um each, capping the tile near 38 % fill; placing the macros directly lets
// two macro columns share channels.  Same die ports, same values on the same edges as qfd_tile_nk (RPH 1 == RPH 2 by
// construction, gated by the r5 rom_pipe exact bench); only the clock structure changes:
//   ck_rp0..4 : was the hard-child entry of rpair leaf b, now the standard-cell CTS root of soft bank row b (~4.4k
//               sinks each; one 22k-sink root on ck would break the 15k sinks/root rule)
//   ck_rom0..9: NEW, one RAW macro clock entry per ROM macro, index p*5 + b = g_col[p].g_bank[b].u_rom (the die delivers
//               phi - R_i at each entry, R_i = the entry wire to the Liberty clock pin)
// The tile glue and the face pin registers stay on the CTS root ck; ck_lsl0..7 / ck_node are unchanged hard-child entries.  On die adoption this body takes
// the die name qfd_tile_nk (no new die master).  Every input bit and every output bit is registered at the pin (owner
// 19:50 rule 1); tie_hi / tie_lo are strap constants (tie cells), not timing paths.
// OT_QFD_TILE_NK_RP1_MUT (bench only): go taken from the top bit of the tap (wrong field order).
module qfd_tile_nk_rp2_45 #(
`ifndef SYNTHESIS
    parameter integer ROM_TILE = -1, // constant die tile identity for released simulation masks
`endif
    parameter integer NW = 18,
    parameter integer GT = 3072,
    parameter integer SMIN = 7,
    parameter integer CODE_BANKS = 5,
    parameter integer KV_VB = 131072,
    parameter integer KV_NH = 2,
    parameter integer MEM_EXTRA = 1,
    parameter integer ACC_LAT = 7,
    parameter integer FAST_ISSUE = 1,
    parameter integer KV_PREP = 4,
    parameter integer MUL_LAT = 8,
    parameter integer TREE_LAT = 7,
    parameter integer ROM_PIPE = 1,
    parameter integer ROM_ARELAY = 2,
    parameter integer ROM_CAP2 = 1,
    parameter integer ROM_CAPX = 2,
    parameter integer LRST = 3,
    parameter integer ARPB = 1,
    parameter integer MPR = 1,
    parameter integer HIER = 2,
    parameter integer HIER_HARD = 1,
    parameter integer TOREG = 1,
    parameter integer TIDR = 1,
    parameter integer LRR = 1,
    parameter integer GLUE_HARD = 0, // consumer-owned hard operand/RQR stages, zero extra edges
    parameter integer RPH = 1,
    parameter integer RQR = 1,
    parameter integer XTX = 2,
    parameter integer ANR = 1,
    parameter integer NDH = 1,
    parameter integer REGROOT = 0,    // Q-ROMPARENT: ck_dw/ck_de/ck_rsw/ck_rnw regional roots (RPH 3)
    // DIE-QC-58B form (1) (opt-in, default 0 = unchanged): 1 = the first stage after the input faces runs on ck_ireg
    // (the u_tile IREG stage go_q / go_cp / ib_q / xl_q, and the node-port alignment / fault registers mis_q / fy_q)
    // instead of ck / ck_fa3, so a parent clock gate on ck sees one more cycle of lead.  Same values on the same edges.
    parameter integer IRCK = 0,
    // NKP (DIE-QC-66 11-03, opt-in, default 0 = unchanged): ot_qwen_w12_matvec_part logic-depth cuts (bit0 K-limit
    // prep, bit1 raw XTX rung 0 + per-leaf round, bit2 round-step sum); 0 visible cycles (see the engine)
    parameter integer NKP = 0,
    // LQR (QC-A0C-B5 11-06 vB, opt-in, default 0 = unchanged): bit0 romleaf r_q capture register (+1 ROM cycle),
    // bit1 per-leaf request register (+1 ROM cycle), bit2 node t_d register (+1 t_out pin cycle)
    parameter integer PINC = 0, // tools/qwen_romleaf/a0core/lqr/pinc_patch.py
    parameter integer RSTP = 0, parameter integer LQR = 0
) (
    input  wire          ck,
    input wire ck_rp0,
    input wire ck_rp1,
    input wire ck_rp2,
    input wire ck_rp3,
    input wire ck_rp4,
    input wire ck_rom0,
    input wire ck_rom1,
    input wire ck_rom2,
    input wire ck_rom3,
    input wire ck_rom4,
    input wire ck_rom5,
    input wire ck_rom6,
    input wire ck_rom7,
    input wire ck_rom8,
    input wire ck_rom9,
    input wire ck_lsl0,
    input wire ck_lsl1,
    input wire ck_lsl2,
    input wire ck_lsl3,
    input wire ck_lsl4,
    input wire ck_lsl5,
    input wire ck_lsl6,
    input wire ck_lsl7,
    input wire ck_node,

    input wire ck_tx0,
    input wire ck_tx1,
    input wire ck_tx2,
    input wire ck_tx3,
    input wire ck_tx4,
    input wire ck_tx5,
    input wire ck_tx6,
    input wire ck_tx7,
    input wire ck_rp5,
    input wire ck_rp6,
    input wire ck_rp7,
    input wire ck_rp8,
    input wire ck_rp9,
    input wire ck_rqr0,
    input wire ck_rsw, input wire ck_rnw, input wire ck_dw, input wire ck_de,
    input wire ck_rqr1,
    input wire ck_rqr2,
    input wire ck_rqr3,
    input wire ck_fa0,
    input wire ck_fa1,
    input wire ck_fa2,
    input wire ck_fa3,
    input wire ck_fa4,
    input wire ck_ireg,      // IRCK 1 only (unused when IRCK = 0)
    input  wire          rst_n,
    input  wire [15:0]   tile_id,
    // die contract v1.2 (compute lead 21:23 10-14): strap ties.  The die wires every tile_id strap bit to this
    // instance's own tie_hi / tie_lo (E face, adjacent to tile_id): no die-netlist literal (one_/zero_ POWER nets).
    output wire          tie_hi,
    output wire          tie_lo,
    input  wire [507:0]  tap,
    output wire [513:0]  t_out,
    input  wire [513:0]  n_a,
    input  wire [513:0]  n_b,
    output wire [513:0]  n_y,
    output wire          me_idle   // QC-PG-5 ICG: u_tile.idle (engine drained, registered; tile-root ICG enable)
);
    (* keep = "true" *) wire tie_hi_w = 1'b1;
    (* keep = "true" *) wire tie_lo_w = 1'b0;
    assign tie_hi = tie_hi_w;
    assign tie_lo = tie_lo_w;
`ifndef SYNTHESIS
    // Rehosting the tree must preserve both the constant mask identity and
    // the real static die strap. A wrong binding is a simulation error.
    always @(posedge ck) if(rst_n && ROM_TILE>=0 && tile_id!==16'(ROM_TILE))
        $fatal(1,"native tile mask identity differs from real tile_id strap");
`endif
    // One kept native-face register per input bit; reset only controls
    // metadata. The child clocks remain independent compensated entries.
    (* keep *) reg [507:0] tap_q;
    (* keep *) reg [15:0] tile_id_q;
    // REGROOT 6 (QW-CLUSTER3/A0 10-19): the kit lands rst_n at the face in two registered stages on ck_fa4
    // (ref_tile reset_landing, last stage as kept copies of <= 32 loads each), so the single native reset_q sample
    // (one flop -> 104 loads in NK c1r9f) is not built; release is a scheduled boot constant (+1 edge: 2 kit stages
    // replace this 1 RTL stage).  REGROOT < 6: unchanged native sample.
    wire reset_q;
    generate if (REGROOT >= 6) begin : g_rst_land
        assign reset_q = rst_n;
    end else begin : g_rst_native
        (* keep *) reg q;
        always @(posedge ck_fa4) q <= rst_n;
        if (RSTP == 0) begin : g_rp0
            assign reset_q = q;
        end else begin : g_rp
            //: vR tree: identical kept copies per stage on the body clock (same gated tree as the sinks); no reset on any stage
            (* keep *) reg [7:0] s1__ot_rl1v;
            (* keep *) reg [63:0] s2__ot_rl2v;
            (* keep *) reg [511:0] s3__ot_rl3v;
`ifdef OT_RSTP_MUT
            localparam integer RMUT = `OT_RSTP_MUT;
`else
            localparam integer RMUT = 0;
`endif
            always @(posedge ck) begin
                s1__ot_rl1v <= {8{q}};
                s2__ot_rl2v <= {64{s1__ot_rl1v[0]}};
                s3__ot_rl3v <= {512{(RMUT == 4) ? 1'b1 : s2__ot_rl2v[0]}};
            end
`ifdef OT_RSTP_MUT
            reg seen = 1'b0;
            always @(posedge ck) if (s3__ot_rl3v[0] === 1'b1) seen <= 1'b1;
            assign reset_q = (RMUT == 1) ? 1'b0 : (RMUT == 2) ? s2__ot_rl2v[0] : (RMUT == 3) ? (s3__ot_rl3v[0] | seen) : s3__ot_rl3v[0];
`else
            assign reset_q = s3__ot_rl3v[0];
`endif
            initial if (RSTP != 3) $fatal(1, "RSTP form: RSTP must be 0 or 3");
        end
    end endgenerate
    always @(posedge ck_fa4) begin
        tap_q <= tap; tile_id_q <= tile_id;
    end
    (* keep *) reg [513:0] n_a_q,n_b_q;
    always @(posedge ck_fa0) n_a_q<=n_a;
    always @(posedge ck_fa1) n_b_q<=n_b;
    // PINC: channel stage after the face flops
    wire [513:0] n_a_c, n_b_c;
    generate if (PINC != 0) begin : g_pinc_in
        (* keep *) reg [513:0] n_a_p, n_b_p;
        always @(posedge ck_fa0) n_a_p <= n_a_q;
        always @(posedge ck_fa1) n_b_p <= n_b_q;
        assign n_a_c = n_a_p;
`ifdef OT_PINC_MUT
        assign n_b_c = (`OT_PINC_MUT == 1) ? n_b_q : n_b_p;
`else
        assign n_b_c = n_b_p;
`endif
    end else begin : g_pinc_in0
        assign n_a_c = n_a_q;
        assign n_b_c = n_b_q;
    end endgenerate
    localparam integer IBW = 3 * NW + 13 * 24 + 13;               // 379
    initial if (1 + IBW + 128 != 508) $fatal(1, "qfd_tile_nk_rp2_45: tap must be {xl 128, ib %0d, go 1} = 508 b", IBW);
`ifdef OT_QFD_TILE_NK_RP1_MUT
    wire           go = tap_q[507];
`else
    wire           go = tap_q[0];
`endif
    wire [IBW-1:0] ib = tap_q[IBW:1];
    wire [127:0]   xl = tap_q[507 -: 128];
    wire [511:0]   to, ny;
    wire           tv, nvy, tf;
    ot_qwen_rom_tile_nk #(
`ifndef SYNTHESIS
        .ROM_TILE(ROM_TILE),
`endif
        .GLUE_HARD(GLUE_HARD), .LOCAL_ROOTS(1), .CHILD_CLOCKS(1), .REGROOT(REGROOT), .NW(NW), .GT(GT), .SMIN(SMIN), .CODE_BANKS(CODE_BANKS), .KV_VB(KV_VB), .KV_NH(KV_NH),
        .MEM_EXTRA(MEM_EXTRA), .ACC_LAT(ACC_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT),
        .TREE_LAT(TREE_LAT), .ROM_PIPE(ROM_PIPE), .ROM_ARELAY(ROM_ARELAY), .ROM_CAP2(ROM_CAP2), .ROM_CAPX(ROM_CAPX),
        .LRST(LRST), .ARPB(ARPB), .MPR(MPR), .HIER(HIER), .HIER_HARD(HIER_HARD), .TOREG(TOREG), .TIDR(TIDR), .LRR(LRR),
        .RPH(RPH), .RQR(RQR), .XTX(XTX), .ANR(ANR), .NDH(NDH), .IRCK(IRCK), .NKP(NKP), .LQR(LQR)) u_tile (
        .ck_pair1({ck_rp9,ck_rp8,ck_rp7,ck_rp6,ck_rp5}), .ck_rqr({ck_rqr1,ck_rqr0}), .ck_rqre({ck_rqr3,ck_rqr2}),
        .ck_tx({ck_tx7,ck_tx6,ck_tx5,ck_tx4,ck_tx3,ck_tx2,ck_tx1,ck_tx0}),
        .ck_reg({ck_de,ck_dw,ck_rnw,ck_rsw}),
        .ck_rpair({ck_rp4,ck_rp3,ck_rp2,ck_rp1,ck_rp0}),   // RPH 1: CTS root of soft bank row b
        .ck_rom({ck_rom9,ck_rom8,ck_rom7,ck_rom6,ck_rom5,ck_rom4,ck_rom3,ck_rom2,ck_rom1,ck_rom0}),
        .ck_lsl({ck_lsl7,ck_lsl6,ck_lsl5,ck_lsl4,ck_lsl3,ck_lsl2,ck_lsl1,ck_lsl0}),
        .ck_node(ck_node), .ck_ireg(ck_ireg),
        .clk(ck), .rst_n(reset_q), .tile_id(tile_id_q), .ib_go(go), .ib(ib), .xl(xl), .t_out(to), .t_vout(tv),
        .n_a(n_a_c[511:0]), .n_b(n_b_c[511:0]), .n_va(n_a_c[512]), .n_y(ny), .n_vy(nvy), .fault(tf), .idle(me_idle));
`ifdef OT_A0_LOCAL_OUT_RESET
    // Scheduled neighbour reset delivery: root sample -> local W-output relay.
    // Adds ONE local boot-release edge; the compiler START offset includes it.
    (* keep = "true", dont_touch = "true" *) reg t_out_reset_q;
    always @(posedge ck_fa2) t_out_reset_q <= reset_q;
    wire t_out_reset_n = t_out_reset_q;
`else
    wire t_out_reset_n = reset_q;
`endif
    (* keep *) reg [513:0] t_out_q;
    wire [511:0] to_c; wire [1:0] tfv_c;
    generate if (PINC != 0) begin : g_pinc_to
        (* keep *) reg [513:0] t_out_p;
        always @(posedge ck_fa2) begin
            t_out_p[511:0] <= to;
            t_out_p[513:512] <= t_out_reset_n ? {tf,tv} : 2'd0;
        end
        assign to_c = t_out_p[511:0];
`ifdef OT_PINC_MUT
        assign tfv_c = (`OT_PINC_MUT == 2) ? {t_out_p[513], tv} : t_out_p[513:512];
`else
        assign tfv_c = t_out_p[513:512];
`endif
    end else begin : g_pinc_to0
        assign to_c = to;
        assign tfv_c = {tf,tv};
    end endgenerate
    always @(posedge ck_fa2) begin
        t_out_q[511:0]<=to_c;
        t_out_q[513:512]<=t_out_reset_n ? tfv_c : 2'd0;
    end
    assign t_out=t_out_q;
    // tree fault: the legs' faults ORed up one register per node (the reference fab_fault = OR of every tile fault,
    // registered at the top), plus a sticky leg-alignment fault
    (* keep *) reg fy_q;
    reg mis_q;
    wire ck_fy = (IRCK != 0) ? ck_ireg : ck_fa3;
    always @(posedge ck_fy)
        if (!reset_q) begin fy_q <= 1'b0; mis_q <= 1'b0; end
        else begin
            mis_q <= mis_q | (n_a_c[512] ^ n_b_c[512]);
            fy_q  <= n_a_c[513] | n_b_c[513] | mis_q;
        end
    (* keep *) reg [513:0] n_y_q;
    wire [511:0] ny_c; wire [1:0] fyv_c;
    generate if (PINC != 0) begin : g_pinc_ny
        (* keep *) reg [513:0] n_y_p;
        always @(posedge ck_fa3) begin
            n_y_p[511:0] <= ny;
            n_y_p[513:512] <= t_out_reset_n ? {fy_q,nvy} : 2'd0;
        end
        assign ny_c = n_y_p[511:0];
        assign fyv_c = n_y_p[513:512];
    end else begin : g_pinc_ny0
        assign ny_c = ny;
        assign fyv_c = {fy_q,nvy};
    end endgenerate
    always @(posedge ck_fa3) begin
        n_y_q[511:0]<=ny_c;
        n_y_q[513:512]<=t_out_reset_n ? fyv_c : 2'd0;
    end
    assign n_y=n_y_q;
endmodule
