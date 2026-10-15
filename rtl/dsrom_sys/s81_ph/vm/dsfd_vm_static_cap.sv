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
// Exact measured age, P=zero-based physical f_capture PIN SAMPLE edge: legacy lane row at P+1,
// CAP_PIPE=1 lane row at P+2; x34 samples that row at q=P+2+CAP_PIPE. Its stream output
// is registered at edge 4*floor(q/3)+2+(q%3). The bench's one-based tk adds1 only for reporting.
// +1 serial stage moves first stream visibility by [1,1,2] edges over the three phases; II remains1.
// ---------------------------------------------------------------------------------------------------------------
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
    reg [1:0] rq;
    always @(posedge ck_control_s or negedge rst_control_s) if (!rst_control_s) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    // Preserve the existing two-edge synchronized release to the capture
    // lanes. Its physical registered reset-distribution tree/epoch arrival
    // remains a native integration gate; replacing rn with raw reset or a
    // new synchronizer here would change the fixed capture startup age.
    wire rn = rq[1];
    // CAP_PIPE selects only the source-owned capture implementation; default0
    // preserves the existing lane age. Selecting1 requires the compiler
    // programme and leaf owner's fixed +1serial capture contract.
    // Status pin register; each hard lane owns its 832-bit data pin register.
    reg [63:0] status_q;
    always @(posedge ck_control_s) status_q <= rn ? f_capture[13312 +: 64] : 64'd0;
    wire [63:0] st = status_q;
    reg dr_q, armed, s_flt;
    wire flush = st[2] && !dr_q && armed && !st[0];
    always @(posedge ck_control_s)
        if (!rn) begin dr_q <= 1'b0; armed <= 1'b0; s_flt <= 1'b0; end
        else begin
            dr_q <= st[2];
            if (st[3]) s_flt <= 1'b1;
            if (st[0]) armed <= 1'b1;
            if (flush) armed <= 1'b0;
        end
    wire [15:0] lv; wire [16*542-1:0] ld; wire [79:0] lf; wire [15:0] xf;
    genvar g;
    generate for (g = 0; g < 16; g = g + 1) begin : lane
        wire ov; wire [13:0] orow; wire [15:0] om; wire [511:0] od;
        dsfd_vm_static_cap_leaf #(.E(E), .PIPE(CAP_PIPE)) u_l (.ck(ck_lane_s[g]), .rn(rn), .gid(g[3:0]), .f_c(f_capture[832*g +: 832]), .flush(flush),
            .o_v(ov), .o_row(orow), .o_m(om), .o_d(od), .flt(lf[5*g +: 5]));
        wire xv; wire [541:0] xd;
        ot_s81_vm_x34 #(.W(542)) u_x (.s_ck(ck_x34_s[g]), .s_rst_n(rst_x34_s[g]), .s_v(ov), .s_d({od, om, orow}),
            .t_ck(ck_x34_t[g]), .t_rst_n(rss_x34_t[g]), .o_v(xv), .o_d(xd), .fault(xf[g]));
        assign w_v[g] = xv;
        assign w_row[14*g +: 14] = xd[13:0];
        assign w_m[16*g +: 16] = xd[29:14];
        assign w_d[512*g +: 512] = xd[541:30];
    end endgenerate
    assign fault = |lf | s_flt | |xf;
endmodule
`default_nettype wire
