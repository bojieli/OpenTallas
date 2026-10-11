`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_svc_idx (CLAUDE s81die-1011/ctrl svch, 2026-10-11): the INDEX READER tile of the S81 scan-service slab
// dsfd_svc_c (u_x), in the slab's upper band between the station chains and the quadrant row's N edge, over the
// Q1 / Q2 boundary.  Content: ot_s81_svcq_idx UNCHANGED (IDX_Q parser, query store, ot_hdc_v41x_idx_ring_ranges,
// ot_hdc_v41x_idx_kstream_ring over the 32 PCs, ot_hdc_v41x_idx_score_quarter 4 x NK4, selector-native x words).
// Why one tile and not a slice per quadrant: the key stream is the ring's key order interleaved over all 32 PCs by
// the PHY map ((s >> 2) ^ (s >> 7) ^ (s >> 12)) mod 32, so a quadrant reading only its 8 PCs sees an out-of-order key
// subset; the x word order (16 consecutive positions a beat) would need a full reorder buffer.  The reader therefore
// stays whole and its 32 per-PC ports become A LANES into the quadrants' PC services (registered seams):
//   request  {len 4, addr 30, tag 16}  credit sender here (depth DEP(NRIg) = the quadrant receiver), NRIg relays
//   response {tag 16, beat 4, data 256} valid-only from the quadrant's PC service into a landing FIFO here (DRA
//            beats = the service's reservation), one credit pulse back per pop.
// q (quadrant 0's registered copy, relayed) in, x out to u_io's x skid via a relay chain of 2-slot skids (outside);
// a1 is unused by the reader (tied off: v = 0).  Every pin a flop; one local clock tree.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_svc_idx #(
    parameter integer ST = 0,
    parameter integer NRI0 = 7, NRI1 = 3, NRI2 = 3, NRI3 = 8,
    parameter integer DRA = 64
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,
    input  wire [514:0]        q,
    output wire [0:0]          a1_v, output wire [511:0] a1_d, input wire [0:0] a1_r,
    output wire [0:0]          x_v,  output wire [511:0] x_d,  input wire [0:0] x_r,
    output wire [31:0]         aq_v, output wire [32*50-1:0] aq_d, input wire [31:0] aq_c,
    input  wire [31:0]         ar_v, input wire [32*276-1:0] ar_d, output wire [31:0] ar_c,
    output wire [0:0]          fo
);
    function automatic integer dep(input integer nr); dep = 2 * nr + 8; endfunction
    function automatic integer nri(input integer d);
        nri = (d == 0) ? NRI0 : (d == 1) ? NRI1 : (d == 2) ? NRI2 : NRI3;
    endfunction
    wire clk = ck[0];
    reg [1:0] rs;
    always @(posedge clk or negedge rst[0]) if (!rst[0]) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    // pin flops
    reg qv_q; reg [511:0] qd_q; reg [31:0] aq_cq, ar_vq; reg [32*276-1:0] ar_dq; reg xr_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin qv_q <= 1'b0; aq_cq <= 0; ar_vq <= 0; end
`ifdef SVCH_MUT_ADROP
        else begin qv_q <= q[0]; aq_cq <= aq_c; ar_vq <= ar_v & ~{32{ar_d[256]}}; end   // MUTANT: A beats with tag bit 0 lost
`else
        else begin qv_q <= q[0]; aq_cq <= aq_c; ar_vq <= ar_v; end
`endif
    always @(posedge clk) begin qd_q <= q[512:1]; ar_dq <= ar_d; end
    wire [31:0] req_v, req_rdy, rsp_v, rsp_rdy; wire [32*30-1:0] req_addr; wire [32*4-1:0] req_len, rsp_beat;
    wire [32*16-1:0] req_tag, rsp_tag; wire [32*256-1:0] rsp_data; wire [31:0] ovf;
    genvar gp;
    generate for (gp = 0; gp < 32; gp = gp + 1) begin : g_a
        ot_s81_svch_ctx #(.W(50), .DEPTH(dep(nri(gp / 8)))) u_tx (.clk(clk), .rst_n(rn), .i_v(req_v[gp]), .i_r(req_rdy[gp]),
            .i_d({req_len[gp*4 +: 4], req_addr[gp*30 +: 30], req_tag[gp*16 +: 16]}),
            .o_v(aq_v[gp]), .o_d(aq_d[gp*50 +: 50]), .c_in(aq_cq[gp]));
        ot_s81_svch_crx #(.W(276), .DEPTH(DRA)) u_rx (.clk(clk), .rst_n(rn), .i_v(ar_vq[gp]), .i_d(ar_dq[gp*276 +: 276]),
            .o_v(rsp_v[gp]), .o_r(rsp_rdy[gp]), .o_d({rsp_tag[gp*16 +: 16], rsp_beat[gp*4 +: 4], rsp_data[gp*256 +: 256]}),
            .c_out(ar_c[gp]), .ovf(ovf[gp]));
    end endgenerate
    // x: the reader's registered x port behind a 2-slot skid (registered ready towards the reader's o_ready cone)
    wire ix_v, ix_r; wire [511:0] ix_d; wire ix_fault; wire [7:0] ix_fc;
    ot_s81_svcq_idx #(.ST(ST), .TAGW(16)) u_idx (
        .clk(clk), .rst_n(rn), .q_v(qv_q), .q_d(qd_q),
        .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data),
        .x_v(ix_v), .x_d(ix_d), .x_r(ix_r), .busy(), .fault(ix_fault), .fault_code(ix_fc));
    ot_s81ph_skid #(.W(512)) u_xs (.clk(clk), .rst_n(rn), .i_v(ix_v), .i_d(ix_d), .i_r(ix_r),
        .o_v(x_v[0]), .o_d(x_d), .o_r(x_r[0]));
    assign a1_v[0] = 1'b0; assign a1_d = '0;
    reg flt;
    always @(posedge clk or negedge rn) if (!rn) flt <= 1'b0; else if (ix_fault || |ovf) flt <= 1'b1;
    assign fo[0] = flt;
endmodule
