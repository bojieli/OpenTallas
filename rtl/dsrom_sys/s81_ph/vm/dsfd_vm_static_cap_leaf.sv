`timescale 1ns/1ps
`default_nettype none
// Physical static capture lane. PIPE 0 legacy, 1 staged merge (+1 serial), 2 = PIPE 1 behind one pure pin-flop stage
// (+2 serial vs legacy, +1 vs PIPE 1: every output and fault is exactly PIPE 1's one serial edge later).
// The input/flush registers formerly in the parent
// live inside this hard boundary. No cycle is added: parent flush is the combinational
// drained-edge predicate which previously fed the parent's flush register.
module dsfd_vm_static_cap_leaf #(parameter integer E=8, parameter integer PIPE=0) (
    input wire ck, rn,
    input wire [3:0] gid,
    input wire [831:0] f_c,
    input wire flush,
    output wire o_v, output wire [13:0] o_row,
    output wire [15:0] o_m, output wire [511:0] o_d,
    output wire [4:0] flt
);
    reg [831:0] pin_c;
    reg [3:0] pin_gid;
    reg pin_flush;
    localparam integer EB = $clog2(E);
    generate if (PIPE == 2) begin : pin_pre
        // PIPE=2 (claude S81 VM F2 2026-10-15, native2): every input (f_c, gid, flush, rn) lands in a PURE pin flop
        // (native audit: decode logic in front of the r6 pin stage gave capture 214..483 ps > 190 on 194 pins; pure pin
        // flops measure ~140).  The second stage registers the per-element validation and one-hot entry target
        // (dsfd_vm_static_capl_pre header) from the pin flops; merge and output follow.  ONE explicit added serial edge
        // vs PIPE=1 (compiler / tools/s81_vm/static_face_model.py cap_pipeline=2): the lane is PIPE=1 delayed by one
        // edge, outputs, faults and reset response alike (tb_dsfd_vm_static_cap_leaf_pre_equiv).
        reg [831:0] q_c; reg [3:0] q_gid; reg q_flush, q_rn;
        always @(posedge ck) begin q_c <= f_c; q_gid <= gid; q_flush <= flush; q_rn <= rn; end
        reg [15:0] p_ok; reg [16*E-1:0] p_tgt; reg p_rng, p_al;
        reg [15:0] d_ok; reg [16*E-1:0] d_tgt; reg d_rng, d_al;
        always @* begin : p_pre integer k; reg [50:0] el; reg v;
            d_rng = 1'b0; d_al = 1'b0; d_tgt = '0;
            for (k = 0; k < 16; k = k + 1) begin
                v  = (k % 2 == 0) ? q_c[104*(k/2)] : q_c[104*(k/2) + 52];
                el = (k % 2 == 0) ? q_c[104*(k/2) + 1 +: 51] : q_c[104*(k/2) + 53 +: 51];
                d_ok[k] = 1'b0;
                if (v) begin
                    if (el[18]) d_rng = 1'b1;
                    else if (el[7:1] != {q_gid, 3'(k / 2)}) d_al = 1'b1;
                    else d_ok[k] = 1'b1;
                end
`ifdef OT_VM_CAP_PRE_MUT_TGT
                d_tgt[E*k +: E] = d_ok[k] ? (E'(1) << (el[8 +: EB] + 1'b1)) : '0;
`else
                d_tgt[E*k +: E] = d_ok[k] ? (E'(1) << el[8 +: EB]) : '0;
`endif
            end
        end
        always @(posedge ck) begin
            pin_c <= q_c;
            pin_gid <= q_gid;
            if (!q_rn) begin pin_flush <= 1'b0; p_ok <= '0; p_tgt <= '0; p_rng <= 1'b0; p_al <= 1'b0; end
            else begin pin_flush <= q_flush; p_ok <= d_ok; p_tgt <= d_tgt; p_rng <= d_rng; p_al <= d_al; end
        end
        dsfd_vm_static_capl_pre #(.E(E)) u_l (.ck(ck), .rn(q_rn), .gid(pin_gid), .f_c(pin_c), .p_ok(p_ok), .p_tgt(p_tgt),
            .p_rng(p_rng), .p_al(p_al), .flush(pin_flush), .o_v(o_v), .o_row(o_row), .o_m(o_m), .o_d(o_d), .flt(flt));
    end else begin : pin_raw
        always @(posedge ck) begin
            pin_c <= rn ? f_c : 832'd0;
            pin_gid <= gid;
            if (!rn) pin_flush <= 1'b0;
            else pin_flush <= flush;
        end
    end endgenerate
    generate if (PIPE == 2) begin : pre
    end else if (PIPE == 0) begin : legacy
        dsfd_vm_static_capl #(.E(E)) u_l (.ck(ck), .rn(rn), .gid(pin_gid), .f_c(pin_c), .flush(pin_flush),
        .o_v(o_v), .o_row(o_row), .o_m(o_m), .o_d(o_d), .flt(flt));
    end else begin : staged
        dsfd_vm_static_capl_pipe #(.E(E)) u_l (.ck(ck), .rn(rn), .gid(pin_gid), .f_c(pin_c), .flush(pin_flush),
            .o_v(o_v), .o_row(o_row), .o_m(o_m), .o_d(o_d), .flt(flt));
    end endgenerate
endmodule
`default_nettype wire
