
module ot_hnx_fused_tnode #(parameter integer LA = 6, parameter integer UW = 271, parameter integer DW = 173, parameter integer DELIVERED_RESET = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    pad_k,      // strap: pad depth (edges)
    input  wire          pad_b,      // strap: 1 pads child b, 0 child a
    input  wire [UW-1:0] ua,         // up from child a (lower lanes)
    input  wire [UW-1:0] ub,         // up from child b (upper lanes)
    output wire [UW-1:0] uo,         // up to the parent
    input  wire [DW-1:0] dn,         // down from the parent
    output wire [DW-1:0] da,         // down to child a
    output wire [DW-1:0] db          // down to child b
);
    wire [3:0] rl;
    generate if (DELIVERED_RESET != 0) begin : g_delivered_reset
        ot_hnx_fused_delivered_reset #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    end else begin : g_legacy_reset
        ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    end endgenerate
    // ---- up: pin flops (control reset, data not)
    reg [14:0] iac, ibc; reg [255:0] iad, ibd;
    always @(posedge clk or negedge rl[0])
        if (!rl[0]) begin iac <= '0; ibc <= '0; end else begin iac <= ua[270:256]; ibc <= ub[270:256]; end
    always @(posedge clk) begin iad <= ua[255:0]; ibd <= ub[255:0]; end
    // ---- alignment pad on the earlier child (static strap select)
    // straps are die ties (case-analysed); registered once here so no tile-input net fans out into the muxes
    reg [5:0] pk_q; reg pb_q;
    always @(posedge clk) begin pk_q <= pad_k; pb_q <= pad_b; end
    wire [14:0] pc; wire [255:0] pd;
    ot_hnx_fused_pad #(.WC(15)) u_pad (.clk(clk), .rst_n(rl[1]), .k(pk_q), .dc(pb_q ? ibc : iac),
        .dd(pb_q ? ibd : iad), .qc(pc), .qd(pd));
    // aligned pair, registered (the SRAM read -> select path ends here; +1 edge on both sides of every node)
    reg [14:0] ac, bc; reg [255:0] ad, bd;
    always @(posedge clk or negedge rl[1])
        if (!rl[1]) begin ac <= '0; bc <= '0; end else begin ac <= pb_q ? iac : pc; bc <= pb_q ? pc : ibc; end
    always @(posedge clk) begin ad <= pb_q ? iad : pd; bd <= pb_q ? pd : ibd; end
    wire ach = ac[14] && ac[13], bch = bc[14] && bc[13], asc = ac[14] && !ac[13], bsc = bc[14] && !bc[13];
    // ---- chunk sums: one registered FP32 add in the golden order (a = lower lanes = even chunk)
    wire cgo = ach && bch;
    wire [LA:0] cvl; wire [31:0] s; wire sf;
    ot_hdc_vline #(.D(LA)) u_cv (.clk(clk), .rst_n(rl[1]), .v(cgo), .vd(cvl));
    ot_dsrom_qadd #(.LAT(LA)) u_add (clk, rl[1], cgo, ad[31:0], bd[31:0], s, sf);
    wire cout = cvl[LA];
    // ---- scalars / fins / faults: one register
    reg sv, sfa, sfo, sfl; reg [9:0] sx; reg [255:0] sd;
    always @(posedge clk or negedge rl[1])
        if (!rl[1]) begin sv <= 1'b0; sfa <= 1'b0; sfo <= 1'b0; sfl <= 1'b0; end
        else begin
            sv <= asc || bsc;
            sfa <= ac[2] && bc[2];
            sfo <= ac[1] || bc[1];
            sfl <= ac[0] || bc[0] || (ach != bch) || (asc && bsc);    // misaligned block / scalar collision
        end
    always @(posedge clk) begin sx <= asc ? ac[12:3] : bc[12:3]; sd <= asc ? ad : bd; end
    // ---- output register
    reg [14:0] oc; reg [255:0] od;
    always @(posedge clk or negedge rl[1])
        if (!rl[1]) oc <= '0;
        else oc <= {sv || cout, cout, cout ? 10'd0 : sx, sfa, sfo, sfl || (sv && cout) || sf};
    always @(posedge clk) od <= cout ? {224'd0, s} : sd;
    assign uo = {oc, od};
    // ---- down: pin flops, then one KEPT copy per child (2 edges a node)
    reg [1:0] idv; reg [DW-3:0] idd;
    always @(posedge clk or negedge rl[2]) if (!rl[2]) idv <= '0; else idv <= {dn[172], dn[32]};
    always @(posedge clk) idd <= {dn[171:33], dn[31:0]};
    (* keep = "true" *) reg [1:0] av_q, bv_q;
    (* keep = "true" *) reg [DW-3:0] ad_q, bd_q;
    always @(posedge clk or negedge rl[3]) if (!rl[3]) begin av_q <= '0; bv_q <= '0; end else begin av_q <= idv; bv_q <= idv; end
    always @(posedge clk) begin ad_q <= idd; bd_q <= idd; end
    assign da = {av_q[1], ad_q[DW-3:32], av_q[0], ad_q[31:0]};
    assign db = {bv_q[1], bd_q[DW-3:32], bv_q[0], bd_q[31:0]};
endmodule
