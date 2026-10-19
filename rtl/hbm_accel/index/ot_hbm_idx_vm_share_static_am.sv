`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ARGMAX-merge variant (HBM-TILES-B 10-17, argmax successor ot_hbm_argmax_static_sw_vm_r2): the 8:1 sector select of the
// ARGMAX.LOCAL reader moves out of the argmax tile into the four bank-pair leaves, so the argmax VM response is ONE
// 264-bit word {lane valid8, data256} instead of 8 x 257 (2,056 pins -> 264; the argmax fits its 118.8 um slot).
// Each pair leaf (unchanged ot_hbm_idx_vm_share_leaf) gets a merge stage on its own clk_pair[p]: its two argmax lanes,
// data masked by their owner-steered valid, are delayed p edges and ORed into a chain p=0 -> 3 (one register per hop),
// so EVERY lane reaches am_rr after exactly 4 edges (VMX = 4 + the argmax pin register = 5 edges added to ARGMAX reads;
// INDEX / TOPK faces unchanged). Lane valid bits keep their own positions, so the argmax still checks every lane.
// AMMUT (bench only, default 0 = the RTL above; lane HBM-IDXAM 10-18, rtl/test/hbm_idx_static/run_idx_rootctl_am.sh):
//   1 pair 3 delayed one edge short (unequal chain); 2 lane valid bits mirrored (lane l at 7-l); 3 data not masked by
//   the owner-steered valid (an INDEX/TOPK response on the same pair ORs into the word); 4 the 8 fp32 elements of the
//   data word reversed (tie-break order: on tied logits a different element index wins).
module ot_hbm_idx_vm_share_ammerge #(parameter integer P = 0, parameter integer AMMUT = 0)(
    input  wire          clk,
    input  wire [513:0]  argmax_rr,          // this pair's two lanes (owner-masked valid, raw data)
    input  wire [263:0]  m_in,               // chain from pair P-1 (0 for P = 0)
    output reg  [263:0]  m_out
);
    reg [263:0] own;
    always @* begin
        own = 264'd0;
        for (integer b = 0; b < 2; b = b + 1) begin
            own[(AMMUT == 2) ? 256 + 7 - (2*P + b) : 256 + 2*P + b] = argmax_rr[257*b+256];
            if (argmax_rr[257*b+256] || AMMUT == 3) own[255:0] = own[255:0] | argmax_rr[257*b +: 256];
        end
    end
    localparam integer PD = (AMMUT == 1 && P == 3) ? P - 1 : P;
    reg [263:0] own_m;
    always @* begin
        own_m = own;
        if (AMMUT == 4) for (integer e = 0; e < 8; e = e + 1) own_m[32*e +: 32] = own[32*(7-e) +: 32];
    end
    reg [263:0] dly [0:(PD>0?PD:1)-1];
    wire [263:0] own_d;
    if (PD == 0) begin : g_nod assign own_d = own_m; end
    else begin : g_d
        always @(posedge clk) begin dly[0] <= own_m; for (integer d = 1; d < PD; d = d + 1) dly[d] <= dly[d-1]; end
        assign own_d = dly[PD-1];
    end
    always @(posedge clk) m_out <= m_in | own_d;
endmodule
module ot_hbm_idx_vm_share_static_am #(parameter integer MUT = 0, parameter integer AMMUT = 0)(
    input  wire [3:0]    clk_pair,
    input  wire          rst_n,
    input  wire [135:0]  index_rq, topk_rq, argmax_rq,
    output wire [135:0]  vm_rq,
    input  wire [2055:0] vm_rr,
    output wire [2055:0] index_rr, topk_rr,
    output wire [263:0]  argmax_m,          // {lane valid8, data256}, 4 edges after the pair leaves' n+7 steer
    output wire          fault
);
    wire [3:0] f; wire [263:0] m [0:4]; assign m[0] = 264'd0;
    for (genvar p = 0; p < 4; p = p + 1) begin : g_pair
        wire [513:0] am;
        ot_hbm_idx_vm_share_leaf #(.MUT(MUT)) leaf(.clk(clk_pair[p]), .rst_n(rst_n),
            .index_rq(index_rq[34*p +: 34]), .topk_rq(topk_rq[34*p +: 34]), .argmax_rq(argmax_rq[34*p +: 34]),
            .vm_rq(vm_rq[34*p +: 34]), .vm_rr(vm_rr[514*p +: 514]), .index_rr(index_rr[514*p +: 514]),
            .topk_rr(topk_rr[514*p +: 514]), .argmax_rr(am), .fault(f[p]));
        ot_hbm_idx_vm_share_ammerge #(.P(p), .AMMUT(AMMUT)) merge(.clk(clk_pair[p]), .argmax_rr(am), .m_in(m[p]), .m_out(m[p+1]));
    end
    assign argmax_m = m[4];
    assign fault = |f;
endmodule
`default_nettype wire
