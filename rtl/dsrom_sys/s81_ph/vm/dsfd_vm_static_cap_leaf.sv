`timescale 1ns/1ps
`default_nettype none
// Physical static capture lane. PIPE 0 legacy, 1 staged merge (+1 serial), 2 = 1 with pin-stage decode (same age).
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
        // PIPE=2 (claude S81 VM F2 2026-10-15): the pin stage also registers the per-element validation and
        // one-hot entry target (dsfd_vm_static_capl_pre header).  Data pins are not reset-gated: every data use
        // downstream is gated by the reset-gated p_ok / p_tgt bits.  Same edge as PIPE=1's pin register.
        reg [15:0] p_ok; reg [16*E-1:0] p_tgt; reg p_rng, p_al;
        reg [15:0] d_ok; reg [16*E-1:0] d_tgt; reg d_rng, d_al;
        always @* begin : p_pre integer k; reg [50:0] el; reg v;
            d_rng = 1'b0; d_al = 1'b0; d_tgt = '0;
            for (k = 0; k < 16; k = k + 1) begin
                v  = (k % 2 == 0) ? f_c[104*(k/2)] : f_c[104*(k/2) + 52];
                el = (k % 2 == 0) ? f_c[104*(k/2) + 1 +: 51] : f_c[104*(k/2) + 53 +: 51];
                d_ok[k] = 1'b0;
                if (v) begin
                    if (el[18]) d_rng = 1'b1;
                    else if (el[7:1] != {gid, 3'(k / 2)}) d_al = 1'b1;
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
            pin_c <= f_c;
            pin_gid <= gid;
            if (!rn) begin pin_flush <= 1'b0; p_ok <= '0; p_tgt <= '0; p_rng <= 1'b0; p_al <= 1'b0; end
            else begin pin_flush <= flush; p_ok <= d_ok; p_tgt <= d_tgt; p_rng <= d_rng; p_al <= d_al; end
        end
        dsfd_vm_static_capl_pre #(.E(E)) u_l (.ck(ck), .rn(rn), .gid(pin_gid), .f_c(pin_c), .p_ok(p_ok), .p_tgt(p_tgt),
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
