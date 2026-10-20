`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// MU-S81/LINK (2026-10-18, owner MU.DECIDE option A): dsdv_mu_land = the SECOND h landing of an end-slice link endpoint
// (multi-user item 3, results/arch/rom_multiuser_1018 README s1: "one extra landing message a stage ingress, so user k+1
// lands while user k computes; no queueing beyond 2 under the shift calendar").  NEW leaf beside each end-slice lep
// (ot_s81sl_lep_mu, MU_EN 1); not on the single-user path (the latency user's h is cut through to ri as today).
//
// Why not reuse the MTP wavefront landing (0 mm2): the DV die has none.  The stage h lands straight into the 80 vn h
// stores (ot_s81sl_vn: 4 HC copies x 64 BF16 a beat leaf = the resident residual the whole stage reads and writes), so
// a second user's h arriving while the first still computes has no other place to land.
//
// Function (static, no ready / credit):
//   land    the lep sends every tagged beat with land = 1 (ml_wv / ml_wd, the full 1,104-b beat with its tag
//           [1045] tag, [1046] land, [1056:1047] user, [1077:1057] pos).  Beats fill slot ws in arrival order; a slot
//           holds one h message share of this endpoint (NB beats, one {user, pos}).  When the slot has NB beats it is
//           complete and ws advances (NS slots in a ring).  A write to a complete slot (the next message arrived before
//           this one was replayed) or a beat whose {user, pos} differs from its partly filled slot is a sticky fault and
//           is dropped (nothing is overwritten).
//   replay  rc = {user 10, v} from the die's seq_host program (compiler slot: the cycle the die starts that user):
//           slot rs must be complete and hold that user, else a sticky fault (read of an empty / partial / wrong slot);
//           its NB beats leave on rv / rd, one a cycle, in arrival order (the lep merges them into ri, tag stripped,
//           tag on mu_rt), then the slot is free and rs advances.  A replay command while one is running is a fault.
// Latency (compiler-known): rc pin -> first rv 4 edges (rc flop, issue, array read, output flop); one beat a cycle.
// Storage: NS x NB x 1,104 b (default 1 x 80 = 88,320 b = 11.0 KB a lep, 44.2 KB a rank die incl. headers).
//   SRAM = 1: 5 x ot_sram_1r1w_128x256_m1_r2c2 (NS * NB <= 128) or 5 x ot_sram_1r1w_256x256_m2_r2c2 (<= 256);
//   SRAM = 0: flops (same cycle behaviour; bench default).
// Pins: every input lands in a flop (wv / wd / rc), every output leaves a flop (rv / rd / fault); reset through
// ot_rst_relay.  Mutant (bench only): OT_DSDV_MU_LAND_MUT_OVR (a complete slot is overwritten, no fault).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_mu_land #(
    parameter integer W = 1104,
    parameter integer NB = 80,          // beats per message share (end-slice share of the 40,976-B h message)
    parameter integer NS = 1,           // slots (messages) beyond the vn h store
    parameter integer SRAM = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          wv,            // <- lep ml_wv / ml_wd
    input  wire [W-1:0]  wd,
    input  wire [10:0]   rc,            // replay command {user 10, v}
    output reg           rv,            // -> lep ml_rv / ml_rd
    output reg  [W-1:0]  rd,
    output reg           fault
);
    localparam integer TG = 1045;
    localparam integer D = NS * NB;
    localparam integer AW = (D > 1) ? $clog2(D) : 1;
    localparam integer CB = $clog2(NB + 1);
    localparam integer SB = (NS > 1) ? $clog2(NS) : 1;
    wire [0:0] rr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rstr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[0];

    // ---------------------------------------------------------------- pin flops
    reg wvq; reg [W-1:0] wdq; reg [10:0] rcq;
    always @(posedge clk or negedge rn) if (!rn) begin wvq <= 1'b0; rcq <= 11'd0; end else begin wvq <= wv; rcq <= rc; end
    always @(posedge clk) wdq <= wd;
    wire [30:0] wtag = {wdq[TG + 2 +: 10], wdq[TG + 12 +: 21]};      // {user, pos}

    // ---------------------------------------------------------------- slot state
    reg [CB-1:0] cnt [0:NS-1];
    reg [30:0]   tag [0:NS-1];
    reg [SB-1:0] ws, rs;
    reg [CB-1:0] ri_;                                  // replay beat index
    reg          busy, fl;
    wire [CB-1:0] wc = cnt[ws];
    wire w_new  = wvq && wc == '0;
    wire w_cont = wvq && wc != '0 && wc != CB'(NB) && tag[ws] == wtag;
`ifdef OT_DSDV_MU_LAND_MUT_OVR
    wire w_ovr  = wvq && wc == CB'(NB);                // MUTANT: a complete slot is overwritten from beat 0, no fault
    wire w_bad  = wvq && !w_new && !w_cont && !w_ovr;
    wire w_ok   = w_new || w_cont || w_ovr;
    wire [CB-1:0] widx = w_ovr ? '0 : wc;
`else
    wire w_ovr  = 1'b0;
    wire w_bad  = wvq && !w_new && !w_cont;            // complete slot (write to a full slot) or a foreign {user, pos}
    wire w_ok   = w_new || w_cont;
    wire [CB-1:0] widx = wc;
`endif
    wire [CB-1:0] wc_nx = w_ovr ? CB'(1) : wc + 1'b1;
    wire r_go  = rcq[0] && !busy && cnt[rs] == CB'(NB) && tag[rs][30:21] == rcq[10:1];
    wire r_bad = rcq[0] && !r_go;                      // busy, empty / partial slot, or another user's message
    wire r_last = busy && ri_ == CB'(NB - 1);
    function automatic [SB-1:0] nxs(input [SB-1:0] s);
        begin nxs = (NS > 1 && s != SB'(NS - 1)) ? s + 1'b1 : '0; end
    endfunction
    integer k;
    always @(posedge clk or negedge rn)
        if (!rn) begin
            for (k = 0; k < NS; k = k + 1) cnt[k] <= '0;
            ws <= '0; rs <= '0; ri_ <= '0; busy <= 1'b0; fl <= 1'b0;
        end else begin
            if (w_ok) begin
                cnt[ws] <= wc_nx;
                if (w_new || w_ovr) tag[ws] <= wtag;
                if (wc_nx == CB'(NB) && !w_ovr) ws <= nxs(ws);
            end
            if (r_go) begin busy <= 1'b1; ri_ <= '0; end
            else if (busy) ri_ <= ri_ + 1'b1;
            if (r_last) begin
                busy <= 1'b0; rs <= nxs(rs);
                if (!(w_ok && ws == rs)) cnt[rs] <= '0;
            end
            if (w_bad || r_bad) fl <= 1'b1;
        end

    // ---------------------------------------------------------------- array (registered read)
    wire [AW-1:0] wa = AW'(ws) * AW'(NB) + AW'(widx);
    wire [AW-1:0] ra = AW'(rs) * AW'(NB) + AW'(ri_);
    wire [W-1:0] q;
    generate if (SRAM == 0) begin : g_ff
        reg [W-1:0] mem [0:D-1]; reg [W-1:0] q_r;
        always @(posedge clk) begin
            if (w_ok) mem[wa] <= wdq;
            if (busy) q_r <= mem[ra];
        end
        assign q = q_r;
    end else begin : g_sram
        localparam integer NT = (W + 255) / 256;
        wire [NT*256-1:0] wdp = {{(NT*256-W){1'b0}}, wdq};
        wire [NT*256-1:0] qp;
        genvar t;
        for (t = 0; t < NT; t = t + 1) begin : g_t
            if (D <= 128) begin : g_128
                ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(busy), .r_addr_in(7'(ra)), .rd_out(qp[t*256 +: 256]),
                    .w_ce_in(w_ok), .w_addr_in(7'(wa)), .wd_in(wdp[t*256 +: 256]), .w_mask_in({256{1'b1}}),
                    .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            end else begin : g_256
                ot_sram_1r1w_256x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(busy), .r_addr_in(8'(ra)), .rd_out(qp[t*256 +: 256]),
                    .w_ce_in(w_ok), .w_addr_in(8'(wa)), .wd_in(wdp[t*256 +: 256]), .w_mask_in({256{1'b1}}),
                    .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            end
        end
        assign q = qp[W-1:0];
`ifndef SYNTHESIS
        initial if (D > 256) $fatal(1, "dsdv_mu_land: SRAM depth %0d > 256", D);
`endif
    end endgenerate

    // ---------------------------------------------------------------- outputs (flops)
    reg rv1;
    always @(posedge clk or negedge rn)
        if (!rn) begin rv1 <= 1'b0; rv <= 1'b0; fault <= 1'b0; end
        else begin rv1 <= busy; rv <= rv1; fault <= fl; end
    always @(posedge clk) rd <= q;
endmodule
