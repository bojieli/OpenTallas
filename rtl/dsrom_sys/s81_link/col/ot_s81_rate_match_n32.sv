`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_rate_match_n32 (S81-LINK4 10-20, S81.STA.OWN.7): NATIVE32 form of the SerDes column rate matcher
// ot_s81_rate_match (rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv, closed tile s81lk_rate_match, kept unchanged).
// Why: the lpk4 mapped native census (Codex d1d3da6c3) refused u_rm: read pointer rp drove 1,248-1,752 loads, the
// row write enables 512, empty 1,026-1,539 and the read-side reset 535 (> 32 each).
// Same elastic function (8 x 512 gray-pointer FIFO, IDLE beats dropped at fill >= 6, IDLE out when empty, sticky
// overflow fault), restructured so that no driver has more than 32 loads:
//   * 24 kept slices (8 x 22 b + 16 x 21 b), each with its own write-pointer replica, one-hot read-pointer replica,
//     8-row storage slice and r_d slice (keep_hierarchy instances: synthesis cannot merge the replicas back);
//   * the per-cycle broadcast decisions (full, fill >= 6, empty) are PRECOMPUTED one edge early from the pointers and
//     registered into 25 copies (24 slices + the central gray/fault logic).  That needs the synchronised gray pointer one
//     edge before use, so each synchroniser has a THIRD stage (the decision uses stage 3 = the precompute's stage 2:
//     no logic ever reads a first-stage synchroniser flop);
//   * resets go through a 2-level kept reset tree per side (asynchronous assertion, release 2 edges later), so the
//     input reset drives 2 flops and every leaf <= 31.
// Differences to ot_s81_rate_match (all at the elastic off-die boundary, owner 10-14 static-schedule rule allows the
// rate matcher as the ONLY elastic element): pointer synchronisers 3 stages instead of 2 (fill / empty seen one edge
// later) and reset release +2 edges per side.  Steady-state data path, IDLE policy and fault are unchanged.
// Storage stays 8 x 512 flops (4,096 b) as in the closed tile: same waiver as lpk3/lpk4 (dual-clock SRAM is not a
// supported landed-cluster sink).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy = "yes" *)
module ot_s81_rm_rleaf (
    input  wire clk,
    input  wire rn,          // asynchronous assert (active low)
    output reg  q
);
    always @(posedge clk or negedge rn) if (!rn) q <= 1'b0; else q <= 1'b1;
endmodule

(* keep_hierarchy = "yes" *)
module ot_s81_rm_rtree #(parameter integer N = 25) (
    input  wire         clk,
    input  wire         rst_n,
    output wire [N-1:0] q
);
    localparam integer NM = (N + 15) / 16;
    wire [NM-1:0] m;
    genvar i;
    generate
        for (i = 0; i < NM; i = i + 1) begin : g_mid
            (* keep_hierarchy = "yes" *) ot_s81_rm_rleaf u_m (.clk(clk), .rn(rst_n), .q(m[i]));
        end
        for (i = 0; i < N; i = i + 1) begin : g_leaf
            (* keep_hierarchy = "yes" *) ot_s81_rm_rleaf u_l (.clk(clk), .rn(m[i / 16]), .q(q[i]));
        end
    endgenerate
endmodule

// SERDES5 10-20 (lpk5 mapped census: q_v 219, idle 49, slice nets 42-45, slice e 37-38): the push decision, the
// write pointer and the read empty / one-hot read pointer are KEPT control modules per slice, so w_v and idle
// see one gate per slice and synthesis cannot fold the broadcast decision into every storage bit; each row enable
// (push & (wp == r)) and read enable (roh[r] & !e) is one gate driving the slice's SW <= 22 bits.  Same function.
// lpk5b census: ABC folded push into every row enable inside one kept wctl (q_v 220) and a mapped enable costs 2 load
// pins per bit (wr 42-44 at 22 bits).  So: push is its own kept module (w_v / idle: one pin per user), the one-hot
// binary write pointer is a kept register module, and the row enables are 2 kept half-bank decoders (11 bits each,
// distinct ID so no merge) -> push <= 3 x 2 + 2 x 8, wp bits <= 2 x 8 + 3, wr 22.
(* keep_hierarchy = "yes" *)
module ot_s81_rm_push (
    input  wire w_v, idle, full, ge6,
    output wire push
);
    assign push = w_v && !full && !(idle && ge6);
endmodule

(* keep_hierarchy = "yes" *)
module ot_s81_rm_wp (
    input  wire       wclk,
    input  wire       wrn,
    input  wire       push,
    output reg  [2:0] wp                  // binary write pointer replica (== wp[2:0] of the central logic)
);
    always @(posedge wclk or negedge wrn) if (!wrn) wp <= 3'd0; else if (push) wp <= wp + 1'b1;
endmodule

(* keep_hierarchy = "yes" *)
module ot_s81_rm_rowen #(parameter integer ID = 0) (
    input  wire       push,
    input  wire [2:0] wp,
    output wire [7:0] wr                  // row write enables (one-hot or 0)
);
    assign wr = {7'd0, push} << wp;
endmodule

(* keep_hierarchy = "yes" *)
module ot_s81_rm_rctl (
    input  wire       rclk,
    input  wire       rrn,
    input  wire       nempty,             // precomputed empty for the NEXT read edge
    output wire [7:0] ren,                // read row enables (one-hot, 0 when empty)
    output wire       e
);
    (* keep *) reg       e_q;
    (* keep *) reg [7:0] roh;
    always @(posedge rclk or negedge rrn)
        if (!rrn) begin e_q <= 1'b1; roh <= 8'b0000_0001; end
        else begin e_q <= nempty; if (!e_q) roh <= {roh[6:0], roh[7]}; end
    assign ren = roh & {8{!e_q}};
    assign e = e_q;
endmodule

(* keep_hierarchy = "yes" *)
module ot_s81_rm_slice #(parameter integer SW = 22, parameter [21:0] IV = 22'd0) (
    input  wire          wclk,
    input  wire          wrn,          // write-side reset leaf
    input  wire          w_v,
    input  wire          idle,
    input  wire          full,         // registered copy: fill == 8 this edge
    input  wire          ge6,          // registered copy: fill >= 6 this edge
    input  wire [SW-1:0] w_d,
    input  wire          rclk,
    input  wire          rrn,          // read-side reset leaf
    input  wire          nempty,       // precomputed empty for the NEXT read edge (registered in u_rc)
    output reg  [SW-1:0] r_d
);
    localparam integer HW = (SW + 1) / 2;          // half-bank widths: HW and SW - HW (11 / 11 or 11 / 10)
    wire [7:0] wr0, wr1, ren;
    wire [2:0] wp;
    wire       push, e;
    (* keep_hierarchy = "yes" *) ot_s81_rm_push u_p (.w_v(w_v), .idle(idle), .full(full), .ge6(ge6), .push(push));
    (* keep_hierarchy = "yes" *) ot_s81_rm_wp u_wp (.wclk(wclk), .wrn(wrn), .push(push), .wp(wp));
    (* keep_hierarchy = "yes" *) ot_s81_rm_rowen #(.ID(0)) u_we0 (.push(push), .wp(wp), .wr(wr0));
    (* keep_hierarchy = "yes" *) ot_s81_rm_rowen #(.ID(1)) u_we1 (.push(push), .wp(wp), .wr(wr1));
    (* keep_hierarchy = "yes" *) ot_s81_rm_rctl u_rc (.rclk(rclk), .rrn(rrn), .nempty(nempty), .ren(ren), .e(e));
    // 8 rows x SW flops, each row two half-bank write enables; read = one-hot AND-OR (ren == 0 when empty, so the
    // pick is 0 then and the IDLE value IV is ORed in by e: only the IV one-bits read e)
    wire [8*SW-1:0] term;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_row
        reg [SW-1:0] m;
        always @(posedge wclk) if (wr0[g]) m[HW-1:0] <= w_d[HW-1:0];
        always @(posedge wclk) if (wr1[g]) m[SW-1:HW] <= w_d[SW-1:HW];
        assign term[g*SW +: SW] = m & {SW{ren[g]}};
    end endgenerate
    reg [SW-1:0] pick;
    integer r;
    always @* begin
        pick = {SW{1'b0}};
        for (r = 0; r < 8; r = r + 1) pick = pick | term[r*SW +: SW];
    end
    always @(posedge rclk or negedge rrn)
        if (!rrn) r_d <= IV[SW-1:0];
        else      r_d <= pick | (IV[SW-1:0] & {SW{e}});
endmodule

module ot_s81_rate_match_n32 (
    input  wire          wclk, wrst_n,
    input  wire          w_v,
    input  wire [511:0]  w_d,
    input  wire          rclk, rrst_n,
    output wire [511:0]  r_d,
    output wire          fault
);
    localparam integer NS = 24;
    function automatic [3:0] g2b(input [3:0] g); begin g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; end endfunction
    function automatic [3:0] b2g(input [3:0] b); begin b2g = b ^ (b >> 1); end endfunction
    // ---- reset trees: leaf NS = central, leaves 0..NS-1 = slices
    wire [NS:0] wl, rl;
    (* keep_hierarchy = "yes" *) ot_s81_rm_rtree #(.N(NS + 1)) u_wrt (.clk(wclk), .rst_n(wrst_n), .q(wl));
    (* keep_hierarchy = "yes" *) ot_s81_rm_rtree #(.N(NS + 1)) u_rrt (.clk(rclk), .rst_n(rrst_n), .q(rl));
    wire wcn = wl[NS], rcn = rl[NS];
    // ---- write side (central replica + gray publication + fault)
    reg  [3:0] wp, wp_g, rp_g1, rp_g2, rp_g3;
    reg        full_c, ge6_c, flt;
    wire idle = w_d[1] && !w_d[0];
    wire push;
    (* keep_hierarchy = "yes" *) ot_s81_rm_push u_pc (.w_v(w_v), .idle(idle), .full(full_c), .ge6(ge6_c), .push(push));
    wire [3:0] wp_n = push ? wp + 1'b1 : wp;
    wire [3:0] nfill = wp_n - g2b(rp_g2);            // = fill at the next edge (rp_g3 then holds today's rp_g2)
    wire full_n = nfill == 4'd8;
    wire ge6_n = nfill >= 4'd6;
    reg  [NS-1:0] full_k, ge6_k;
    always @(posedge wclk or negedge wcn)
        if (!wcn) begin
            wp <= 4'd0; wp_g <= 4'd0; rp_g1 <= 4'd0; rp_g2 <= 4'd0; rp_g3 <= 4'd0;
            full_c <= 1'b0; ge6_c <= 1'b0; flt <= 1'b0;
        end else begin
            rp_g1 <= rp_g; rp_g2 <= rp_g1; rp_g3 <= rp_g2;
            wp <= wp_n; if (push) wp_g <= b2g(wp + 1'b1);
            full_c <= full_n; ge6_c <= ge6_n;
            if (w_v && full_c && !idle) flt <= 1'b1;
        end
    // ---- read side (central binary pointer + gray publication)
    reg  [3:0] rp, rp_g, wp_g1, wp_g2, wp_g3;
    reg        e_c, f1, f2;
    wire [3:0] rp_n = e_c ? rp : rp + 1'b1;
    wire nempty = g2b(wp_g2) == rp_n;                // = empty at the next edge (wp_g3 then holds today's wp_g2)
    always @(posedge rclk or negedge rcn)
        if (!rcn) begin
            rp <= 4'd0; rp_g <= 4'd0; wp_g1 <= 4'd0; wp_g2 <= 4'd0; wp_g3 <= 4'd0; e_c <= 1'b1; f1 <= 1'b0; f2 <= 1'b0;
        end else begin
            wp_g1 <= wp_g; wp_g2 <= wp_g1; wp_g3 <= wp_g2;
            rp <= rp_n; if (!e_c) rp_g <= b2g(rp + 1'b1);
            e_c <= nempty;
            f1 <= flt; f2 <= f1;
        end
    assign fault = f2;
    // ---- registered decision copies for the slices (one flop per slice per decision)
    genvar k;
    generate for (k = 0; k < NS; k = k + 1) begin : g_cp
        always @(posedge wclk or negedge wl[k])
            if (!wl[k]) begin full_k[k] <= 1'b0; ge6_k[k] <= 1'b0; end
            else begin full_k[k] <= full_n; ge6_k[k] <= ge6_n; end
    end endgenerate
    // ---- 24 kept slices: 8 x 22 b (bits 0..175) then 16 x 21 b (bits 176..511); IDLE value 512'd2 lives in slice 0
    generate for (k = 0; k < NS; k = k + 1) begin : g_s
        localparam integer SW = (k < 8) ? 22 : 21;
        localparam integer LO = (k < 8) ? k * 22 : 176 + (k - 8) * 21;
        localparam [21:0] IV = (k == 0) ? 22'd2 : 22'd0;
        (* keep_hierarchy = "yes" *) ot_s81_rm_slice #(.SW(SW), .IV(IV)) u_s (
            .wclk(wclk), .wrn(wl[k]), .w_v(w_v), .idle(idle), .full(full_k[k]), .ge6(ge6_k[k]), .w_d(w_d[LO +: SW]),
            .rclk(rclk), .rrn(rl[k]), .nempty(nempty), .r_d(r_d[LO +: SW]));
    end endgenerate
endmodule
`default_nettype wire
