`timescale 1ns/1ps
`default_nettype none
// TW2-COLLAR (10-19): the XDIE-HBM4 AR_ITER glue of ot_hfd_coll_q_hard_v8g_body (generate block g_ariter) as a leaf, so
// the WIRES-ONLY flat parents ot_hfd_coll_q{2,3}_lpf_ar (tools/hbm_coll_static/gen_coll_q2_lpf.py --ar-iter) keep no
// flop in the parent.  Exactly the v8g edges: it_d1 / it_d2 (the issuer iteration delayed two edges) on clk_issue, the
// iterated reduce load / read / publication tags and publication index (d2 fields + it_d2 x iter_ar_tag_step) registered
// on clk_reduce[0] (pin clk_tag) = the d3 edge every AR field already uses.  Static schedule; no credits / backpressure.
// No reset (as v8g): it_d* are defined two edges after the issuer's iteration, the tags one edge after the d2 stream.
// Mutants (bench only): OT_ARITER_TAG_MUT_NOSTEP drops the product (= v8g OT_COLL_ARITER_MUT_NOSTEP on the leaf alone);
// OT_ARITER_TAG_MUT_EDGE takes the iteration one edge early (it_d1).
module ot_hgi_coll_ariter_tag(
    input wire clk_issue,                  // v8g clk_issue (it_d1 / it_d2)
    input wire clk_tag,                    // v8g clk_reduce[0] (t_load / t_read / t_pa / t_pb / t_idx)
    input wire [15:0] iteration,           // issuer tap_iteration[15:0]
    input wire [54:0] ar2,                 // {inst_d2[688+:24], inst_d2[1505+:31]}
    input wire [3:0] st2,                  // inst_d2[714+:4] = iter_ar_tag_step
    output reg [3:0] load_tag,read_tag,pub_tag_a,pub_tag_b,
    output reg [15:0] pub_index
);
    reg [15:0] it_d1,it_d2;
`ifdef OT_ARITER_TAG_MUT_EDGE
    wire [19:0] prod=it_d1*st2;
`else
    wire [19:0] prod=it_d2*st2;
`endif
    always @(posedge clk_issue)begin it_d1<=iteration;it_d2<=it_d1;end
    always @(posedge clk_tag)begin
`ifdef OT_ARITER_TAG_MUT_NOSTEP
        load_tag<=ar2[1+:4];read_tag<=ar2[6+:4];pub_tag_a<=ar2[12+:4];pub_tag_b<=ar2[16+:4];pub_index<=ar2[31+:16];
`else
        load_tag<=ar2[1+:4]+prod[3:0];read_tag<=ar2[6+:4]+prod[3:0];pub_tag_a<=ar2[12+:4]+prod[3:0];
        pub_tag_b<=ar2[16+:4]+prod[3:0];pub_index<=ar2[31+:16]+prod[15:0];
`endif
    end
endmodule
`default_nettype wire
