`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_l2 -- G-unit leaf L2 (4th of 6 from the top): the column-3 V-rung stop.
//
// Stack (N -> S, each 680 um wide): L5 tail | L4 finish | L0 HP roots | L2 stop | L1 select | L3 weights.
//   rung     ot_dsdv_vstop (unchanged): rn_* = the N side (toward L0 .. L5, s_3N), rs_* = the S side (L1, L3, s_3S);
//            taps + sinks SC (kind 5) and HP (kind 7); injects the unit's CTL rows both ways on one edge.
//   SC       the vstop's own deliver flops (dl_*) leave on the S face to L1 unfiltered (L1 filters kind 5 behind its
//            input flop: no extra edge on the router's critical path).
//   HP       kind 7 filtered into a registered copy, N face to L0 (off the critical path).
//   CTL      rct (L1: router rows) and hct (L0: HC rows relayed from L5) are zero when idle; their OR enters the vstop
//            inject flops; both on one edge is a sticky fault (the compiler never schedules it; no arbitration).
//   cw / sid E-face input flops, then one output flop per face (S: L1, N: L0).
//   fault    output flop: vstop | L1 | L0 | collision.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 9 = the CTL rows injected northbound only;
// 10 = the raw hct_b pin ORed into the S-side inject (skips its pin flop; native pin-register equivalence bench).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l2 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // N face (L0)
    input  wire [275:0]  rn_i,  output wire [275:0] rn_o,
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant / unused pins): hp_a / hp_b [243:40] (L0 reads no other bit), cws_a packed {a[9:8], a[5:0]},
    // dl_a / dl_b packed {dl[275:52], dl[49:40], dl[3:1]} (L1 reads no other bit), hct_b / rct_b = packed CTL rows.
    output reg           hp_av, output reg [243:40] hp_a, output reg hp_bv, output reg [243:40] hp_b,
    output wire          cwn_v, output wire [7:0] cwn_a, output wire [255:0] cwn_d, output wire [3:0] sidn,
    input  wire          hct_v, input wire [169:0] hct_b, input wire hf,
    // S face (L1)
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    output wire          dl_av, output wire [236:0] dl_a, output wire dl_bv, output wire [236:0] dl_b,
    output wire          cws_v, output wire [7:0] cws_a, output wire [255:0] cws_d, output wire [3:0] sids,
    input  wire          rct_v, input wire [169:0] rct_b, input wire rf,
    // E face (unit pins)
    input  wire [3:0]    sid,
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d,   // RTLC: packed {a[9:8], a[5:0]} (a[7:6] read by no leaf)
    output reg           fault
);
    localparam [7:0] KSC = 8'h20, KHP = 8'h80;
    // S81-NATIVE3 (10-17, NATIVE-2 audit: rst_n 394.4 / hct_b 283.9 capture, cws_d 236 launch): rst_n drives only a
    // local reset relay (2 sync + 1 tree stage per region: release +3 edges); hct_* and rct_* land in their own pin flops
    // (N / S face) and are ORed AFTER those flops, straight into the vstop's inject port (JREG 0: these flops ARE the
    // inject flops), so the inject slot and every rung edge are unchanged (reg(a | b) = reg(a) | reg(b)).
    wire [2:0] rsv;
    ot_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_v = rsv[0], rs_n = rsv[1], rs_s = rsv[2];      // vstop / N-face (L0) / S-face (L1) regions
    function automatic [275:0] ctlup(input [169:0] p);
        ctlup = {87'd0, p[169:23], 2'd0, p[22], 1'b0, p[21:5], 8'd0, p[4:1], 8'd0, p[0]};
    endfunction
    reg hct_vq, rct_vq; reg [169:0] hct_bq, rct_bq;
    always @(posedge clk or negedge rs_n) if (!rs_n) hct_vq <= 1'b0; else hct_vq <= hct_v;
    always @(posedge clk or negedge rs_s) if (!rs_s) rct_vq <= 1'b0; else rct_vq <= rct_v;
    always @(posedge clk) begin hct_bq <= hct_b; rct_bq <= rct_b; end
`ifdef OT_RTLC_MUT_L2   // RTLC bench mutant: CTL unpack loses data bit 0 (in_b[61])
    wire f_vs, in_v = rct_vq | hct_vq; wire [275:0] in_b = ctlup(rct_bq | hct_bq) & ~(276'd1 << 61);
`else
    wire f_vs, in_v = rct_vq | hct_vq; wire [275:0] in_b = ctlup(rct_bq | hct_bq);
`endif
    wire [275:0] dl_af, dl_bf;     // vstop S-face outputs; the pins carry the bits L1 reads (RTLC packing above)
    assign dl_a = {dl_af[275:52], dl_af[49:40], dl_af[3:1]}; assign dl_b = {dl_bf[275:52], dl_bf[49:40], dl_bf[3:1]};
    // rung: vi_s = northbound arrivals (from L1), vo_n = toward L0; vi_n = southbound arrivals (from L0), vo_s = toward L1
    ot_dsdv_vstop #(.V(276), .JREG(0)) u_vs (.clk(clk), .rst_n(rs_v), .tap_k(KSC | KHP), .sink_k(KSC | KHP),
        .vi_s(rs_i), .vo_n(rn_o), .vi_n(rn_i), .vo_s(rs_o), .dl_nv(dl_av), .dl_n(dl_af), .dl_sv(dl_bv), .dl_s(dl_bf),
        .in_nv(in_v), .in_n(in_b), .in_sv(MUT == 9 ? 1'b0 : in_v), .in_s(MUT == 9 ? 276'd0 : MUT == 10 ? ctlup(rct_bq | hct_b) : in_b), .fault(f_vs),
        .ra_s(ra_s), .ra_n(ra_n), .dk_n(dk_n), .dk_s(dk_s));
    // HP copy for L0 (kind 7).  S81-NATIVE3: taken from the rung input flops through its own stage (hc_*) and the vstop's
    // separate kind-7 flag, never from the dl_* output flops (those sit at the S pins; the NATIVE-2 CTS probe put
    // dl_a/dl_b[3:1] at 226-227 ps launch with this second load).  hp(t + 1) = dl(t) = arrival flop(t - 1): unchanged.
    wire [275:0] ra_s, ra_n; wire dk_n, dk_s;
    // S81-KITS-RTLC 10-24 (raw face_guard, 0 edges): hc_* took the same D as the vstop dl_* output flops (is_ / in_) and
    // synthesis folded the two (404 dl pin bits with a second load; keeping hc_* only moved the fold).  hc_* now captures
    // only a kind-7 header beat (bit 0 = head, [3:1] = 7; HP is one beat), else 0: a different D, so no fold.  Every
    // beat the vstop taps as HP (dk_*) is such a header, so hp_* is unchanged whenever hp_*v = 1.  Only [243:40] is read.
    reg [243:40] hc_a, hc_b;
    wire hk_a = ra_s[0] && ra_s[3:1] == 3'd7, hk_b = ra_n[0] && ra_n[3:1] == 3'd7;
    always @(posedge clk or negedge rs_n)
        if (!rs_n) begin hp_av <= 1'b0; hp_bv <= 1'b0; end
        else begin hp_av <= dk_n; hp_bv <= dk_s; end
    always @(posedge clk) begin hc_a <= hk_a ? ra_s[243:40] : 204'd0; hc_b <= hk_b ? ra_n[243:40] : 204'd0; hp_a <= hc_a; hp_b <= hc_b; end
    // cw / sid: E input flop, then one output flop per face
    wire [264:0] cw_q;
    dsdv_gunit_pass #(.W(265), .N(1)) u_cwi (.clk(clk), .rst_n(rs_v), .d({cw_d, cw_a, cw_v}), .q(cw_q));
    // S81-NATIVE3: the two output copies are TOP-module registers (not dsdv_gunit_pass instances): ot_keep_regs.tcl
    // (OT_KEEP_PIN_REGS) keeps only top-level pin registers apart, so the submodule copies with equal D were folded into
    // one flop that io_flop_at_pins seated at the N pins, and cws_* crossed the tile (CTS probe cws_d mean 182 ps).
    reg cwn_vq, cws_vq; reg [263:0] cwn_q, cws_q;
    always @(posedge clk or negedge rs_n) if (!rs_n) cwn_vq <= 1'b0; else cwn_vq <= cw_q[0];
    always @(posedge clk or negedge rs_s) if (!rs_s) cws_vq <= 1'b0; else cws_vq <= cw_q[0];
    always @(posedge clk) begin cwn_q <= cw_q[264:1]; cws_q <= cw_q[264:1]; end
    assign {cwn_d, cwn_a} = cwn_q; assign cwn_v = cwn_vq; assign {cws_d, cws_a} = cws_q; assign cws_v = cws_vq;
    reg [3:0] sid_q, sn_q, ss_q;
    always @(posedge clk) begin sid_q <= sid; sn_q <= sid_q; ss_q <= sid_q; end
    assign sidn = sn_q; assign sids = ss_q;
    // collision + fault
    reg col, rf_q, hf_q;
    // col reads the pin flops; fault ORs their AND directly, so a collision reaches fault on the same edge as before
    always @(posedge clk or negedge rs_v)
        if (!rs_v) begin col <= 1'b0; rf_q <= 1'b0; hf_q <= 1'b0; fault <= 1'b0; end
        else begin
            col <= col | (rct_vq & hct_vq); rf_q <= rf; hf_q <= hf;
            fault <= f_vs | rf_q | hf_q | col | (rct_vq & hct_vq);
        end
endmodule
