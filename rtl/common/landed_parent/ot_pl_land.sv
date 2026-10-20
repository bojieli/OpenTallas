`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// PARENTS-LANDED (2026-10-18, coordinator standard landed-regions-standard-1018): the shared LANDING of one region-seam
// crossing inside a hardened parent.  Identical semantics to qfd_c_land_w / qfd_c_land_r (Q-CLUSTER-LANDALL
// claude/q-cl-landall-1018 rtl/physical/qcluster/qfd_c_land.sv, benched there: lockstep PASS, mutants FAIL), renamed so
// every die's parents use ONE master pair (tools/landed_parent/lp.py emits the instances, SDC and records).
//   ot_pl_land_w  RING on the SOURCE region root, beside the source register (flop-first): every edge writes slot wc mod D.
//   ot_pl_land_r  READ on the DESTINATION region root, beside the destination register: slot (rc - K) mod D -> o (flop-last).
// Contract: lanes/LANDING-CONTRACT.md L1-L7.  Both halves take rsi from equal-depth reset runs (G == R0), so E = K and the
// crossing adds E + 1 edges, constant at every corner while (E - D) T + t_hold < dL < E T - t_cq - t_setup.
// SDC (lp.py): set_multicycle_path -setup E -hold (D - 1) -from <ring cells> -to <read cells>.
// FAULT: assertion only ($error LAND_FAULT in simulation); synthesis drops the epoch tags.  No ready / credit / training.
// ---------------------------------------------------------------------------------------------------------------------
module ot_pl_land_w #(
    parameter integer W  = 514,
    parameter integer D  = 4,                          // ring depth, power of two >= 2
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire              ck,                       // source region root
    input  wire              rsi,                      // reset-tree leaf (active low), re-registered here
    input  wire [W-1:0]      i,                        // source register q (one in-region hop)
    output wire [D*W-1:0]    bank,                     // ring slots -> ot_pl_land_r (multicycle E / D-1 paths)
    output wire [D*(AW+1)-1:0] epo,                    // slot write epochs (assertion only)
    output wire [D-1:0]      vld                       // slot written since the epoch
);
    reg            rq;
    reg [AW:0]     wc;
    reg [W-1:0]    b [0:D-1];
    reg [AW:0]     e [0:D-1];
    reg [D-1:0]    v;
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) wc <= {(AW + 1){1'b0}};
        else     wc <= wc + 1'b1;
    always @(posedge ck)
        if (!rq) v <= {D{1'b0}};
        else     v[wc[AW-1:0]] <= 1'b1;
    genvar s;
    generate for (s = 0; s < D; s = s + 1) begin : g_slot
        always @(posedge ck) if (rq && wc[AW-1:0] == s) begin b[s] <= i; e[s] <= wc; end
        assign bank[s*W +: W] = b[s];
        assign epo[s*(AW+1) +: AW+1] = e[s];
    end endgenerate
    assign vld = v;
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "ot_pl_land_w: D must be a power of two >= 2");
`endif
endmodule

module ot_pl_land_r #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer K  = 2,                          // read offset = E (G == R0); 1 <= K <= D - 1
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire              ck,                       // destination region root
    input  wire              rsi,                      // reset-tree leaf (active low), re-registered here
    input  wire [D*W-1:0]    bank,
    input  wire [D*(AW+1)-1:0] epo,
    input  wire [D-1:0]      vld,
    output reg  [W-1:0]      o                         // flop-last -> destination register
);
    reg            rq;
    reg [AW:0]     rc;
    reg            warm;
    wire [AW:0]    kk = K;
    wire [AW:0]    exp_ = rc - kk;
    wire [AW-1:0]  sel = exp_[AW-1:0];
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin rc <= {(AW + 1){1'b0}}; warm <= 1'b0; end
        else begin
            rc <= rc + 1'b1;
            if (rc == kk - 1'b1) warm <= 1'b1;
        end
    // decoded slot select (one-hot compare + AND-OR, constant-index slices): a runtime bank[sel*W +: W] is a W-bit
    // $shiftx that yosys SHARE can stall on for wide landings (pre_route_gate rtl runtime_partselect; PL-SMT W = 2,069)
    reg [W-1:0] pick;
    integer j;
    always @* begin
        pick = {W{1'b0}};
        for (j = 0; j < D; j = j + 1) pick = pick | ({W{sel == j[AW-1:0]}} & bank[j*W +: W]);
    end
    always @(posedge ck) o <= (warm && vld[sel]) ? pick : {W{1'b0}};
`ifndef SYNTHESIS
    reg fault = 1'b0;
    always @(posedge ck)
        if (warm && vld[sel] && epo[sel*(AW+1) +: AW+1] != exp_ && !fault) begin
            fault <= 1'b1;
            $error("LAND_FAULT %m: read slot %0d epoch %0d, expected %0d (calendar slip)", sel, epo[sel*(AW+1) +: AW+1], exp_);
        end
    initial if (D < 2 || (D & (D - 1)) != 0) $fatal(1, "ot_pl_land_r: D must be a power of two >= 2");
    initial if (K < 1 || K > D - 1) $fatal(1, "ot_pl_land_r: K must be in 1..D-1");
`endif
endmodule
`default_nettype wire

// Opt-in bounded local rings. Slot-major external bank layout and K/reset ages
// match ot_pl_land_w/r exactly; each small hierarchy owns its selector/counter.
// Keeping hierarchy prevents synthesis from merging the identical selectors back
// into a bus-wide high-fanout select. At CHUNK_BITS24 each ring stores96 data bits.
module ot_pl_land_chunk_w #(
    parameter integer W = 514, D = 4, CHUNK_BITS = 24,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld
);
    genvar c, s;
    generate for (c = 0; c < (W + CHUNK_BITS - 1) / CHUNK_BITS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        wire [D*CW-1:0] cb;
        wire [D*(AW+1)-1:0] ce;
        wire [D-1:0] cv;
        (* keep_hierarchy = "yes" *) ot_pl_land_local_w #(.W(CW), .D(D)) u_local (
            .ck(ck), .rsi(rsi), .i(i[c*CHUNK_BITS +: CW]), .bank(cb), .epo(ce), .vld(cv));
        for (s = 0; s < D; s = s + 1) begin : g_slot
            assign bank[s*W + c*CHUNK_BITS +: CW] = cb[s*CW +: CW];
        end
        assign vld[c*D +: D] = cv;
        if (c == 0) begin : g_tags
            assign epo = ce;

        end
    end endgenerate
`ifndef SYNTHESIS
    initial if (CHUNK_BITS < 1 || CHUNK_BITS > 24)
        $fatal(1, "ot_pl_land_chunk_w: CHUNK_BITS must be1..24");
`endif
endmodule

module ot_pl_land_chunk_r #(
    parameter integer W = 514, D = 4, K = 2, CHUNK_BITS = 24,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [D*W-1:0] bank,
    input wire [D*(AW+1)-1:0] epo,
    input wire [D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld,
    output wire [W-1:0] o
);
    genvar c, s;
    generate for (c = 0; c < (W + CHUNK_BITS - 1) / CHUNK_BITS; c = c + 1) begin : g_chunk
        localparam integer CW = (W - c*CHUNK_BITS < CHUNK_BITS) ? W - c*CHUNK_BITS : CHUNK_BITS;
        wire [D*CW-1:0] cb;
        for (s = 0; s < D; s = s + 1) begin : g_slot
            assign cb[s*CW +: CW] = bank[s*W + c*CHUNK_BITS +: CW];
        end
        (* keep_hierarchy = "yes" *) ot_pl_land_local_r #(.W(CW), .D(D), .K(K)) u_local (
            .ck(ck), .rsi(rsi), .bank(cb), .epo(epo), .vld(vld[c*D +: D]), .o(o[c*CHUNK_BITS +: CW]));
    end endgenerate
`ifndef SYNTHESIS
    initial if (CHUNK_BITS < 1 || CHUNK_BITS > 24)
        $fatal(1, "ot_pl_land_chunk_r: CHUNK_BITS must be1..24");
`endif
endmodule

// Small independently kept selectors. Data never passes through a binary indexed
// wide mux; the one-hot register advances ahead of the capture edge so K and the
// reset age remain exactly the original contract.
module ot_pl_land_local_w #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld
);
    reg rq;
    reg [AW:0] wc;
    (* keep *) reg [D-1:0] write_oh;
    reg [D-1:0] valid;
    reg [W-1:0] data [0:D-1];
    reg [AW:0] epoch [0:D-1];
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin wc <= 0; write_oh <= {{(D-1){1'b0}},1'b1}; valid <= 0; end
        else begin
            wc <= wc + 1'b1;
            write_oh <= {write_oh[D-2:0], write_oh[D-1]};
            valid <= valid | write_oh;
        end
    genvar s;
    generate for (s=0;s<D;s=s+1) begin:g_slot
        always @(posedge ck) if (rq && write_oh[s]) begin data[s] <= i; epoch[s] <= wc; end
        assign bank[s*W+:W] = data[s];
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
    assign vld = valid;
endmodule

module ot_pl_land_local_r #(
    parameter integer W = 24, D = 4, K = 2,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [D*W-1:0] bank,
    input wire [D*(AW+1)-1:0] epo,
    input wire [D-1:0] vld,
    output reg [W-1:0] o
);
    reg rq, warm;
    reg [AW:0] rc;
    (* keep *) reg [D-1:0] read_oh;
    wire [AW:0] expected_epoch = rc - (AW+1)'(K);
    reg [W-1:0] selected;
    reg selected_valid;
    integer s;
    always @* begin
        selected = 0;
        selected_valid = 0;
        for (integer j=0;j<D;j=j+1) begin
            selected = selected | (bank[j*W+:W] & {W{read_oh[j]}});
            selected_valid = selected_valid | (vld[j] & read_oh[j]);
        end
    end
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin
            rc <= 0; warm <= 0;
            for (s=0;s<D;s=s+1) read_oh[s] <= (s == ((D-K) % D));
        end else begin
            rc <= rc + 1'b1;
            if (rc == K-1) warm <= 1;
            read_oh <= {read_oh[D-2:0], read_oh[D-1]};
        end
    always @(posedge ck) o <= (warm && selected_valid) ? selected : {W{1'b0}};
`ifndef SYNTHESIS
    reg fault = 0;
    always @(posedge ck) if (warm && selected_valid && !fault) begin
        for (integer j=0;j<D;j=j+1) if (read_oh[j] && epo[j*(AW+1)+:AW+1] != expected_epoch) begin
            fault <= 1;
            $error("LAND_FAULT %m: slot%0d epoch%0d expected%0d",j,epo[j*(AW+1)+:AW+1],expected_epoch);
        end
    end
`endif
endmodule

`default_nettype none
// ot_pl_pad: N-stage register chain (N = 0: a wire).  tools/landed_parent/lp.py uses it for the alignment pads (a net whose
// reader runs t edges later than its driver plus the landing) and for the regional reset runs (W = 1).  Plain flops, no
// reset: they only delay a word (bubbles included), exactly like a relay stage.
module ot_pl_pad #(
    parameter integer W = 1,
    parameter integer N = 1
) (
    input  wire         ck,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (N == 0) begin : g_wire
        assign q = d;
    end else begin : g_reg
        reg [W-1:0] r [0:N-1];
        integer j;
        always @(posedge ck) begin
            r[0] <= d;
            for (j = 1; j < N; j = j + 1) r[j] <= r[j - 1];
        end
        assign q = r[N-1];
    end endgenerate
endmodule
`default_nettype wire
