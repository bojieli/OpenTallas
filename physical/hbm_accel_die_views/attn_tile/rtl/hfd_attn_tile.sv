`timescale 1ns/1ps
// CLAUDE HBM-ABSTRACTS (attn), 2026-10-06: die view of the HBM attention tile (tools/hbm_accel_die_fp.py master
// hfd_attn_tile, r16g; 64 copies).  Default-off: a new die-view top, instantiated by nothing in the design tree.
//
// One tile = the H16 quad parent (ot_attn_tile_m6h1p, inlined so the forward taps see its ROOT): four hardened H4 quads
// ot_attn_tile_m6h1q (closed views physical/hbm_attn_tile_r/quad/ot_attn_tile_m6h1q) fed by ROOT -> ROW (one per quad
// row) -> the quad's HC bank.  The die ports (exact r16g names, widths, faces; tools/hbm_die_views.py ports):
//   k  [1040:0] S  KV / load half of the packet from the stream service: {ld_v, ld_mode, ld_bank, ld_grp, ld_w, ld_w2v}
//                  = k[1037:0]; k[1040:1038] are the segment's forwarded clocks (one per 512 b slice)
//   q  [581:0]  E  query half from the VM: {iv, ibank, ib} = q[579:0]; q[581:580] forwarded clocks
//   ci [1617:0] S  packet from the tile below (column), {k[1037:0], q[579:0]} order;  cf [1617:0] N  forward up
//   ri [1617:0] E  packet from the inner neighbour (row);                              rf [1617:0] W  forward out
//   i  [528:0]  W  results from the outer neighbour {ov, oy[511:0], oflt[15:0]};       o  [528:0]  E  results inward
//   ck E (clk_stream), rst E (ACTIVE LOW, synchronous to ck, quasi-static: held >= 3 cycles; carried as data like the
//   parent's rst_n - the die reset net's polarity is not stated by the generator, this view takes rst = rst_n)
// Role: the generator binds k / q only on the corner tile, ci only on column tiles, ri only on row tiles, i on all but
// the outermost; this view ORs the three packet sources, so an UNBOUND role input must be tied 0 at the die.
// Interim contract (defects recorded in view.json): (1) k / q are sampled on ck (synchronous); the generator's
// meso FIFO in the receiving tile needs a credit return the die nets do not carry, so the forwarded clocks k[1040:1038]
// / q[581:580] end on a capture flop only; (2) the result chain is a valid-priority merge (local word first, an
// arriving word from i in the same cycle is dropped and every oflt bit of the local word is set): the owner's merge
// input (ot_attn_tile_registered_parent) is not built.
// Latency: pin register + NS stages to ROOT (NS = 2: 1.35 mm tile, SS reach 504 um/stage), ROOT -> NF stages -> the
// cf / rf pin register; one tile hop = 1 + NS + 1 + NF + 1 = 6 cycles (the generator prices 1); results: quads ->
// NL stages -> o register, i -> pin register -> NI stages -> o register.
module hfd_attn_tile #(
    parameter integer NS = 2,
    parameter integer NF = 1,
    parameter integer NL = 2,
    parameter integer NI = 2
) (
    output wire [1617:0] cf,
    input  wire [1617:0] ci,
    input  wire [0:0]    ck,
    input  wire [528:0]  i,
    input  wire [1040:0] k,
    output wire [528:0]  o,
    input  wire [581:0]  q,
    output wire [1617:0] rf,
    input  wire [1617:0] ri,
    input  wire [0:0]    rst
);
    localparam integer PK = 1618, PW = PK + 1, RW = 529;
    wire clk = ck[0];
    // ---- pin registers (one bank per port, at its face)
    wire [1040:0] k_p; wire [581:0] q_p; wire [PK-1:0] ci_p, ri_p; wire [RW-1:0] i_p; wire rst_p;
    (* keep = "true" *) ot_attn_rp_reg #(.W(1041)) u_pk  (.clk(clk), .d(k),   .q(k_p));
    (* keep = "true" *) ot_attn_rp_reg #(.W(583))  u_pq  (.clk(clk), .d({rst[0], q}), .q({rst_p, q_p}));
    (* keep = "true" *) ot_attn_rp_reg #(.W(PK))   u_pci (.clk(clk), .d(ci),  .q(ci_p));
    (* keep = "true" *) ot_attn_rp_reg #(.W(PK))   u_pri (.clk(clk), .d(ri),  .q(ri_p));
    (* keep = "true" *) ot_attn_rp_reg #(.W(RW))   u_pi  (.clk(clk), .d(i),   .q(i_p));
    // the forwarded clocks k[1040:1038] / q[581:580] load only their pin-register flops; see header (1)
    // ---- NS stages from each face toward ROOT (rst rides with the local packet)
    wire [PW-1:0] loc_s, ci_s, ri_s;
    ot_attn_die_pipe #(.W(PW), .N(NS)) u_sl (.clk(clk), .d({rst_p, k_p[1037:0], q_p[579:0]}), .q(loc_s));
    ot_attn_die_pipe #(.W(PK), .N(NS)) u_sc (.clk(clk), .d(ci_p), .q(ci_s[PK-1:0]));
    ot_attn_die_pipe #(.W(PK), .N(NS)) u_sr (.clk(clk), .d(ri_p), .q(ri_s[PK-1:0]));
    assign ci_s[PK] = 1'b0;
    assign ri_s[PK] = 1'b0;
    // ---- ROOT: the parent's root bank, the OR of the three packet sources (unbound sources are 0)
    wire [PW-1:0] pk = loc_s | ci_s | ri_s;
    wire [PW-1:0] root_q;
    (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_root (.clk(clk), .d(pk), .q(root_q));
    // ---- forward: ROOT -> NF stages -> cf / rf pin registers
    wire [PK-1:0] cf_s, rf_s;
    ot_attn_die_pipe #(.W(PK), .N(NF)) u_fc (.clk(clk), .d(root_q[PK-1:0]), .q(cf_s));
    ot_attn_die_pipe #(.W(PK), .N(NF)) u_fr (.clk(clk), .d(root_q[PK-1:0]), .q(rf_s));
    (* keep = "true" *) ot_attn_rp_reg #(.W(PK)) u_ocf (.clk(clk), .d(cf_s), .q(cf));
    (* keep = "true" *) ot_attn_rp_reg #(.W(PK)) u_orf (.clk(clk), .d(rf_s), .q(rf));
    // ---- the H16 quad parent below ROOT (ot_attn_tile_m6h1p verbatim from its ROW bank down)
    wire [15:0] gov;
    wire [511:0] oy;
    wire [15:0] oflt;
    genvar y, x, l;
    generate for (y = 0; y < 2; y = y + 1) begin : g_y
        wire [PW-1:0] row_q;
        (* keep = "true" *) ot_attn_rp_reg #(.W(PW)) u_row (.clk(clk), .d(root_q), .q(row_q));
        wire          q_rst_n, q_ld_v, q_ld_mode, q_ld_w2v, q_iv;
        wire [2:0]    q_ld_bank, q_ibank;
        wire [7:0]    q_ld_grp;
        wire [1023:0] q_ld_w;
        wire [575:0]  q_ib;
        assign {q_rst_n, q_ld_v, q_ld_mode, q_ld_bank, q_ld_grp, q_ld_w, q_ld_w2v, q_iv, q_ibank, q_ib} = row_q;
        for (x = 0; x < 2; x = x + 1) begin : g_x
            localparam integer GB = 8 * y + 2 * x;
            wire [3:0]   qv, qf;
            wire [127:0] qy;
            ot_attn_tile_m6h1q u_q (.clk(clk), .rst_n(q_rst_n), .qgid(GB[7:0]), .ld_v(q_ld_v), .ld_mode(q_ld_mode),
                .ld_bank(q_ld_bank), .ld_grp(q_ld_grp), .ld_w(q_ld_w), .ld_w2v(q_ld_w2v), .iv(q_iv), .ibank(q_ibank),
                .ib(q_ib), .gov(qv), .oy(qy), .oflt(qf));
            for (l = 0; l < 4; l = l + 1) begin : g_l
                localparam integer G = GB + 4 * (l / 2) + (l % 2);
                assign {gov[G], oflt[G], oy[G*32 +: 32]} = {qv[l], qf[l], qy[l*32 +: 32]};
            end
        end
    end endgenerate
    // ---- results: local word and the arriving chain word, valid-priority merge into the o pin register
    wire [RW-1:0] loc_r, chn_r;
    ot_attn_die_pipe #(.W(RW), .N(NL)) u_rl (.clk(clk), .d({gov[0], oy, oflt}), .q(loc_r));
    ot_attn_die_pipe #(.W(RW), .N(NI)) u_ri (.clk(clk), .d(i_p), .q(chn_r));
    wire loc_v = loc_r[RW-1], chn_v = chn_r[RW-1];
    wire [RW-1:0] mrg = loc_v ? {loc_r[RW-1:16], loc_r[15:0] | {16{chn_v}}} : chn_r;
    (* keep = "true" *) ot_attn_rp_reg #(.W(RW)) u_oo (.clk(clk), .d(mrg), .q(o));
endmodule

// N kept register banks in series (N = 0: a wire)
module ot_attn_die_pipe #(parameter integer W = 1, parameter integer N = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    genvar s;
    generate if (N == 0) begin : g0
        assign q = d;
    end else begin : gn
        wire [W-1:0] st [0:N];
        assign st[0] = d;
        for (s = 0; s < N; s = s + 1) begin : g_s
            (* keep = "true" *) ot_attn_rp_reg #(.W(W)) u_r (.clk(clk), .d(st[s]), .q(st[s+1]));
        end
        assign q = st[N];
    end endgenerate
endmodule
