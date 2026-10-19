`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// MU-S81/HOST (2026-10-18, MU.S81.BUF host part (b)): dsdv_mu_seed -- per-MTP-user seed-state addressing for the S81
// MTP draft dies.  SPEC + SMALLEST LEAF: there is NO S81-DV draft-die RTL today.
//   * p4l (rtl/dsrom_sys/s81_dv/**) holds no draft / DSpark die (RELEASE_TREE TOK.DS.LAYER.6: "a measured draft layer
//     still needs the draft/head die netlist (not in p4l)"; claude/lb2-s81-mtp-1018 a64ea3dba is a FIXTURE: the
//     reference's DSpark window-state snapshot, bit-exact, no RTL).
//   * The legacy S81PH MTP tree (rtl/dsrom_sys/mtp, 10-09/10) has per-user state, but not in the form the S81-DV
//     static rule needs: ot_dsrom_mtp_seed_launch keeps per-user {next unseeded position, epoch} for MAXU = 8 users and
//     reads per-user hidden rows from dsfd_mtp_hrow at {epoch, user, pos mod WIN, beat} (MAXU x RS x 30 KB); both use
//     the grant (valid / ready) protocol and wait states, MAXU 8 < the 10 MTP users, and neither is in any S81-DV die.
//   So the per-user seed STATE (the DSpark draft block's carried hidden state, 4 HC x 5,120 BF16 = 40,960 B a user;
//   design study item 10: up to 10 MTP users, AR fillers none) is specified here and given its smallest leaf.
//
// Spec.  The seed state of MTP user u lives at SB + u * 40,960 B of the draft die's seed SRAM (or its HBM window), as
// SW = 320 words of 1,024 b (one VM beat).  The draft die's compiled calendar moves a user's state in one window of
// 320 consecutive edges (one beat an edge, beat 0..319), the commit write after the user's verify step and the read
// at the user's next draft launch, both inside the user's MTP slot (user k = the single-user schedule shifted by k
// slots).  This leaf turns the calendar's beat command {v, wr, user 10, beat 9} into the store address
// SB + u * 320 + beat (u * 320 = (u << 8) + (u << 6): no multiplier) and checks the static rule; it never stalls and
// never reorders: a bad beat is NOT forwarded (t_a valid 0) and raises a sticky fault.
//   t_mf [0] collision: a beat that does not continue the open window (beat 0 while a window is open, a beat != the
//            next one, or another user's beat inside the window = two users' windows overlap: compiler error);
//        [1] range: user >= NUSER or beat >= 320;
//        [2] protocol: a write data valid without a write beat (f_d valid only with wr beats).
// Latency: command pin flop -> t_a output flop = 2 edges for every NUSER (user 0's addresses and edges are the same as
// the NUSER 1 leaf's: base SB + 0).  NUSER 1 (default) = the single-user draft die: base SB, any user != 0 faults.
// Area (NUSER 10): ~60 control flops + 1,024 + 34 data / address flops (the data pipe the store port needs anyway);
// the store itself is 10 x 40 KB = 400 KB of the draft die's SRAM (modelled 0.21 mm^2) or an HBM window.
// MUT (bench negative controls): 1 user field dropped from the address (every user on user 0's state), 2 collision
// check dropped.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_mu_seed #(parameter integer NUSER = 1, parameter integer SB = 0, parameter integer AW = 24,
                      parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [20:0]     f_c,             // {v, wr, user 10, beat 9} from the draft die calendar
    input  wire [1024:0]   f_d,             // {write data 1024, v}
    output wire [AW+1:0]   t_a,             // {v, we, addr AW} to the seed store (1,024-b words)
    output reg  [1023:0]   t_d,             // write data, same edge as t_a
    output reg  [2:0]      t_mf             // sticky faults
);
    localparam integer SW = 320;
`ifndef SYNTHESIS
    initial if (NUSER < 1 || NUSER > 1023 || SB + NUSER * SW > (1 << AW)) $fatal(1, "dsdv_mu_seed: bad NUSER / SB / AW");
`endif
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    reg [20:0] c_q; reg [1024:0] d_q;
    always @(posedge ck) begin c_q <= {rn & f_c[20], f_c[19:0]}; d_q <= {f_d[1024:1], rn & f_d[0]}; end
    wire cv = c_q[20], cw = c_q[19]; wire [9:0] cu = c_q[18:9]; wire [8:0] cb = c_q[8:0];
    reg open; reg [9:0] wu; reg [8:0] wb; reg ta_v; reg [AW:0] ta_p;
    assign t_a = {ta_v, ta_p};
    wire rng = cu >= 10'(NUSER) || cb >= 9'(SW);
    wire seq = open ? (cb == wb && cu == wu) : (cb == 9'd0);
    wire ok = cv && !rng && (seq || MUT == 2);
    wire [9:0] ua = (MUT == 1) ? 10'd0 : cu;
    wire [AW-1:0] ad = AW'(SB) + AW'({ua, 8'd0}) + AW'({ua, 6'd0}) + AW'(cb);
    always @(posedge ck or negedge rn)
        if (!rn) begin open <= 1'b0; wu <= 10'd0; wb <= 9'd0; t_mf <= 3'd0; ta_v <= 1'b0; end
        else begin
            ta_v <= ok;
            if (cv && rng) t_mf[1] <= 1'b1;
            if (cv && !rng && !seq && MUT != 2) t_mf[0] <= 1'b1;
            if (d_q[0] && !(cv && cw)) t_mf[2] <= 1'b1;
            if (ok) begin
                open <= cb != 9'(SW - 1); wu <= cu; wb <= cb + 9'd1;
            end
        end
    always @(posedge ck) begin ta_p <= {cw, ad}; t_d <= d_q[1024:1]; end
endmodule
