`timescale 1ns/1ps
`default_nettype none
// hgi-takeover 2026-10-09 (mtp-lead item (1), decision (3)): the ARGMAX unit die master of the SINGLE-CP generic die
// (hgi_dispatch has 'cp' and 'argmax'), instance hb_mtp_am in the MTP slot beside hgi_mtp_native.
// = ot_hgi_argmax_slot (closed record adapter ot_hgi_argmax_record + closed engine ot_hgi_argmax18_m) with its ports
// renamed to the die nets (tools/hgi_die_dispatch.py):
//   f_hgi_cmdproc 691 = {die_id 8, n_O, n_A, desc_O, desc_A, header, valid} from the sequencer (ot_hgi_cp_die am_rec);
//     die_id is the 683 -> 691 sideband (the slot flops it; the adapter reads it one cycle after valid, the record's
//     own cycle value, so the first record of a job already carries the rank: global id = local + RANK * imm_a);
//   t_hgi_cmdproc 3 = {fault, done, ready};
//   t_hgi_vmq 338 / f_hgi_vmr 274: the unit is a VM packet client of hfd_hgi_vm (A = VM reads, O {value, id} writes);
//   in_* 523: the su_red logit STREAM (A = STREAM); out_* 54: the flopped engine result (legacy hb_am_vm bus).
module hfd_hgi_am #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [690:0]  f_hgi_cmdproc,
    output wire [2:0]    t_hgi_cmdproc,
    output wire [337:0]  t_hgi_vmq,
    input  wire [273:0]  f_hgi_vmr,
    input  wire          in_v, in_last, in_bias_en,
    input  wire [7:0]    in_mask,
    input  wire [255:0]  in_vals, in_bias,
    output wire          out_v,
    output wire [17:0]   out_idx,
    output wire          out_nan, fault, out_range_fault,
    output wire [31:0]   out_value
);
    ot_hgi_argmax_slot #(.MUT(MUT)) u_slot (.clk(clk), .rst_n(rst_n), .f_hgi_cmdproc(f_hgi_cmdproc[682:0]),
        .t_hgi_cmdproc(t_hgi_cmdproc), .die_id(f_hgi_cmdproc[690:683]), .vmq(t_hgi_vmq), .vmr(f_hgi_vmr),
        .in_v(in_v), .in_last(in_last), .in_bias_en(in_bias_en), .in_mask(in_mask), .in_vals(in_vals), .in_bias(in_bias),
        .out_v(out_v), .out_idx(out_idx), .out_nan(out_nan), .fault(fault), .out_range_fault(out_range_fault),
        .out_value(out_value));
endmodule
`default_nettype wire
