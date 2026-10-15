`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_cap (claude S81 VM owner r9, 2026-10-14): the STATIC capture face of the S81 layer-die VM.
// f_capture 13,376 b = dsfd_sp_capture(_c) t_vm (serial 0.9 GHz, no ready): 128 roots x {row1 {data32, addr19}, v1,
// row0 {data32, addr19}, v0} | status 64 ([0] phase live, [2] phase drained, [3] capture fault, [13:4] phase).
//   16 pin-registered hard lanes dsfd_vm_static_cap_leaf over dsfd_vm_static_capl (lane G = roots 8G .. 8G+7, one row write a cycle at
//   most) -> 16 fixed-phase 3:4 transfers ot_s81_vm_x34 (W 542 = {row 14, mask 16, data 512}) -> 16 stream-domain
//   VM write sources (dsfd_vm_static_core sources 32..43, 48..51).
// Rates: 128 elements a stream cycle at full field rate = 8 rows a stream cycle; a lane carries at most one row a
// serial cycle (16 lanes x 3 serial = 48 rows an epoch = 12 a stream cycle of the 16 lanes' sources).  Aligned phases
// (obase multiple of 256 words) put the 16 rows of one key on 16 distinct banks (bank hash row[4:0] ^ {row[7:5],00},
// row[3:0] = G), so the write service's lane rule is met at full rate; any other overlap is a write-service fault.
// Faults (sticky, OR -> fault): lane faults (range, alignment, alias, duplicate, two rows due), capture status fault
// (st[3]), x34 epoch / phase assertions.  No ready, credit, queue or timeout.
// Latency (fixed): element at the f_capture pin, serial edge P -> lane row registered P + 3 (pin, merge, out) -> x34
// stream output at the fixed epoch slot of that serial edge (+2..4 stream edges, x34 header) -> write source.
// ---------------------------------------------------------------------------------------------------------------
// CAP_PIPE=2 (claude S81 VM F2 2026-10-15, native capture audit): lanes take every input in a pure pin flop and decode
// one edge later (lane row at P+3), and the 3:4 transfers run NAT=1 (ICG-gated serial banks; stream side captures each
// bank unmuxed at its read edge, output one stream edge later): x34 samples the row at q = P+2+CAP_PIPE, stream output
// at 4*floor(q/3)+2+(q%3)+1.  Explicit added edges vs legacy: 2 serial + 1 stream (static_face_model cap_pipeline=2).
module dsfd_vm_static_cap #(parameter integer E = 8, parameter integer CAP_PIPE = 0) (
    // Actual source categories. All serial/stream roots share the 3:4 PLL
    // epoch; each physical entry receives its own measured phi-R delivery.
    input wire ck_control_s,
    input wire [15:0] ck_lane_s, ck_x34_s, ck_x34_t,
    input wire rst_control_s,
    input wire [15:0] rst_x34_s, rss_x34_t, // per-root active-low epoch resets
    input  wire [13375:0]  f_capture,
    output wire [15:0]     w_v,                 // stream domain, one row write per lane
    output wire [223:0]    w_row,
    output wire [255:0]    w_m,
    output wire [8191:0]   w_d,
    output wire            fault                // serial-domain sticky level (lanes + status) | stream x34 faults
);
    // Control root (ck_control_s) = hard leaf dsfd_vm_static_cap_ctl (claude S81 VM F2 2026-10-15): the same
    // flops (two-edge reset release, status pin register, drained edge, armed, sticky status fault) moved, no edge.
    wire rn, flush, s_flt;
    dsfd_vm_static_cap_ctl u_ctl (.ck(ck_control_s), .rst_n(rst_control_s), .st_live(f_capture[13312]),
        .st_drn(f_capture[13314]), .st_flt(f_capture[13315]), .rn(rn), .flush(flush), .s_flt(s_flt));
    wire [15:0] lv; wire [16*542-1:0] ld; wire [79:0] lf; wire [15:0] xf;
    genvar g;
    generate for (g = 0; g < 16; g = g + 1) begin : lane
        wire ov; wire [13:0] orow; wire [15:0] om; wire [511:0] od;
        dsfd_vm_static_cap_leaf #(.E(E), .PIPE(CAP_PIPE)) u_l (.ck(ck_lane_s[g]), .rn(rn), .gid(g[3:0]), .f_c(f_capture[832*g +: 832]), .flush(flush),
            .o_v(ov), .o_row(orow), .o_m(om), .o_d(od), .flt(lf[5*g +: 5]));
        wire xv; wire [541:0] xd;
        ot_s81_vm_x34 #(.W(542), .NAT(CAP_PIPE == 2 ? 1 : 0), .BAL(CAP_PIPE == 2 ? 1 : 0)) u_x (.s_ck(ck_x34_s[g]), .s_rst_n(rst_x34_s[g]), .s_v(ov), .s_d({od, om, orow}),
            .t_ck(ck_x34_t[g]), .t_rst_n(rss_x34_t[g]), .o_v(xv), .o_d(xd), .fault(xf[g]));
        assign w_v[g] = xv;
        assign w_row[14*g +: 14] = xd[13:0];
        assign w_m[16*g +: 16] = xd[29:14];
        assign w_d[512*g +: 512] = xd[541:30];
    end endgenerate
    assign fault = |lf | s_flt | |xf;
endmodule

// dsfd_vm_static_cap_ctl: the capture face's control root.  rn = two-edge synchronized release of rst_n (the lanes'
// fixed startup age); status pin register of the three used status bits (live [0], drained [2], fault [3]); flush =
// drained rising after live armed, one cycle, combinational from flops (as before); s_flt sticky status fault.
module dsfd_vm_static_cap_ctl (
    input  wire ck, rst_n,
    input  wire st_live, st_drn, st_flt,
    output wire rn, flush,
    output reg  s_flt
);
    reg [1:0] rq;
    always @(posedge ck or negedge rst_n) if (!rst_n) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    assign rn = rq[1];
    reg q_live, q_drn, q_flt;
    always @(posedge ck) begin q_live <= rn & st_live; q_drn <= rn & st_drn; q_flt <= rn & st_flt; end
    reg dr_q, armed;
`ifdef OT_VM_CAP_CTL_MUT_FLUSH
    assign flush = q_drn && !dr_q && armed && q_live;     // MUTANT: live term inverted (phase flush lost)
`else
    assign flush = q_drn && !dr_q && armed && !q_live;
`endif
    always @(posedge ck)
        if (!rn) begin dr_q <= 1'b0; armed <= 1'b0; s_flt <= 1'b0; end
        else begin
            dr_q <= q_drn;
            if (q_flt) s_flt <= 1'b1;
            if (q_live) armed <= 1'b1;
            if (flush) armed <= 1'b0;
        end
endmodule
`default_nettype wire
