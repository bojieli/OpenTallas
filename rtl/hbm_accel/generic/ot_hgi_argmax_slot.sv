`timescale 1ns/1ps
`default_nettype none
// mtp-lead 2026-10-09: the ARGMAX unit of the R25G MTP slot (instance hb_mtp_am, beside hgi_mtp_native) as a dispatched
// HGI unit.  = the closed record adapter ot_hgi_argmax_record (hgi-adapters, CLOSED hgi_adp_argmax_b-c226d244d) in front
// of the closed engine ot_hgi_argmax18_m (GENERIC18 = 1, LP 8), behind the die dispatch bus of tools/hgi_die_dispatch.py
// 'argmax' (f_hgi_cmdproc 683 = {n_O, n_A, desc_O, desc_A, header, valid}; t_hgi_cmdproc 3 = {fault, done, ready}).
//   A = STREAM: the su_red logit stream (in_* 523, unchanged die bus) is consumed only while a record is active (the
//       adapter gates in_v); A = VM: read through the VM packet client.  O {value, id}: written to VM by the client.
//   cfg_rank = die_id (runtime rank, global id = local + RANK * imm_a), cfg_imm_a = header imm_a: driven by the adapter.
//   out_*: the engine result, flopped (the legacy se bus; the record's O write is the normative result).
// Ports beyond the 683 / 3 ABI (proposed to hgi-takeover, tools/hgi_die_dispatch.py owner): vmq / vmr (argmax as a VM
// packet client) and die_id (argmax dispatch sideband, as coll's).  MUT (bench): 1 = die rank not bound (RANK 0).
module ot_hgi_argmax_slot #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [682:0]  f_hgi_cmdproc,
    output wire [2:0]    t_hgi_cmdproc,
    input  wire [7:0]    die_id,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    input  wire          in_v, in_last, in_bias_en,
    input  wire [7:0]    in_mask,
    input  wire [255:0]  in_vals, in_bias,
    output reg           out_v,
    output reg  [17:0]   out_idx,
    output reg           out_nan, fault, out_range_fault,
    output reg  [31:0]   out_value
);
    reg [7:0] rank_q;
    always @(posedge clk) rank_q <= (MUT == 1) ? 8'd0 : die_id;          // static strap per die, one pin flop
    wire e_in_v, e_in_last, e_bias_en, e_out_v, e_out_nan, e_fault, e_rf;
    wire [7:0] e_mask; wire [255:0] e_vals, e_bias; wire [6:0] e_rank; wire [17:0] e_imm, e_idx; wire [31:0] e_val;
    wire nan_flag;
    ot_hgi_argmax_record u_rec (.clk(clk), .rst_n(rst_n), .cfg_rank(rank_q), .rec(f_hgi_cmdproc), .ret(t_hgi_cmdproc),
        .nan_flag(nan_flag), .vmq(vmq), .vmr(vmr),
        .am_stream({in_bias_en, in_bias, in_vals, in_mask, in_last, in_v}),
        .e_in_v(e_in_v), .e_in_last(e_in_last), .e_bias_en(e_bias_en), .e_mask(e_mask), .e_vals(e_vals), .e_bias(e_bias),
        .e_rank(e_rank), .e_imm(e_imm), .e_out_v(e_out_v), .e_out_idx(e_idx), .e_out_nan(e_out_nan), .e_fault(e_fault),
        .e_range_fault(e_rf), .e_out_value(e_val));
    ot_hgi_argmax18_m #(.LP(8), .GENERIC18(1)) u_e (.clk(clk), .rst_n(rst_n), .in_v(e_in_v), .in_last(e_in_last),
        .in_bias_en(e_bias_en), .in_mask(e_mask), .in_vals(e_vals), .in_bias(e_bias), .cfg_rank(e_rank), .cfg_imm_a(e_imm),
        .out_v(e_out_v), .out_idx(e_idx), .out_nan(e_out_nan), .fault(e_fault), .out_range_fault(e_rf), .out_value(e_val));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin out_v <= 1'b0; fault <= 1'b0; out_range_fault <= 1'b0; out_nan <= 1'b0; end
        else begin out_v <= e_out_v; fault <= e_fault; out_range_fault <= e_rf; out_nan <= e_out_nan; end
    always @(posedge clk) begin out_idx <= e_idx; out_value <= e_val; end
endmodule
`default_nettype wire
