`timescale 1ns/1ps
// qfd_sys_face_record_port (Q-SYSFACE rs1 2026-10-17): qfd_program_record_port (context_transport_20261014, unchanged
// and still used by its own benches) with the async reset split per sub-block, so no reset relay flop of the compute-die
// system face drives more than 256 flops (the rr1 gate textbook lint: one rst_rec relay drove 1,153 flops).  Logic,
// ports and every register are identical; only the reset net of each sub-block is its own region:
//   rst_rn[0] auth RX + TT descriptor-obs delay + slot fault   rst_rn[1] TT receipt (sink 0)   rst_rn[2] SU receipt (sink 1)
//   rst_rn[3] commit join                                       rst_rn[4] host context RX      rst_rn[5] witness TX
// All six are released on the same edge (qfd_sys_face ot_rst_relay), so the reset release is bit-identical.
// FILL (MU-DQ-BOOTCTX 10-19, opt-in, 0 = unchanged): the host context receiver admits the kind12 filler-context field
// (qfd_host_native_context_rx FILL); qfd_sys_face_fill_ctx below turns it into the ctlm runtime context word.
module qfd_sys_face_record_port #(parameter integer FILL = 0)(
 input wire ck,input wire[5:0]rst_rn,input wire auth_slot,context_slot,witness_slot,
 input wire rx_v,input wire[547:0]rx_record,
 input wire execution_active,
 // Two actual independent TT/SU consumed-write observer faces, v/full/address/data.
 input wire[151:0]program_obs2,input wire[68:0]descriptor_obs,
 input wire[1:0]cfg_image_ready,
 input wire head_context_v,input wire[5:0]head_stage,
 input wire[17:0]head_token,head_position,
 output wire begin_v,auth_v,output wire[15:0]begin_epoch,auth_epoch,
 output wire[10:0]expected_pw,output wire[3:0]expected_dw,output wire[63:0]auth_digest,
 output wire program_ready,installed_fusedcap,commit_v,
 output wire[15:0]program_epoch,output wire[63:0]program_digest,
 output wire host_epoch_valid,output wire[15:0]host_epoch,
 output wire[58:0]host_tag,output wire[1:0]host_gen,
 output wire tx_v,tx_observed_v,output wire[547:0]tx_record,
 output wire fault
);
 wire af,jf,cf,wf;reg slot_fault;
 wire[1:0]sink_ready,sink_fault,sink_fusedcap;
 wire[31:0]sink_epoch;wire[127:0]sink_digest;
 // SU owns the one actual descriptor store. TT's extra program-bank stage
 // needs the genuine consumed descriptor receipt delayed one fixed edge.
 reg[68:0]tt_descriptor_obs;
 always @(posedge ck or negedge rst_rn[0])
 if(!rst_rn[0])tt_descriptor_obs<=0;else tt_descriptor_obs<=descriptor_obs;
 for(genvar sink=0;sink<2;sink=sink+1)begin:g_actual_sink
 wire[75:0]pw=program_obs2[76*sink+:76];
 wire[68:0]dw=(sink==0)?tt_descriptor_obs:descriptor_obs;
 qkd_program_commit u_receipt(.ck(ck),.rst_n(rst_rn[1+sink]),.execution_active(execution_active),.control_stores_ready(cfg_image_ready[sink]),
 .begin_v(begin_v),.begin_epoch(begin_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),
 .auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),
 .pw_v(pw[75]),.pw_full_word(pw[74]),.pw_addr(pw[73:64]),.pw_data(pw[63:0]),
 .dw_v(dw[68]),.dw_full_word(dw[67]),.dw_addr(dw[66:64]),.dw_data(dw[63:0]),
 .commit_v(),.ready(sink_ready[sink]),.fault(sink_fault[sink]),.installed_fusedcap(sink_fusedcap[sink]),
 .commit_epoch(sink_epoch[16*sink+:16]),.commit_digest(sink_digest[64*sink+:64]));
 end
 wire context_cap;wire[15:0]context_image_epoch;wire[63:0]context_image_digest;
 always @(posedge ck or negedge rst_rn[0])
 if(!rst_rn[0])slot_fault<=0;
 else if((auth_slot&&context_slot)||(rx_v!==(auth_slot|context_slot)))slot_fault<=1;
 qfd_program_auth_rx u_auth(.ck(ck),.rst_n(rst_rn[0]),.receive_slot(auth_slot),.rx_v(rx_v&&auth_slot),.rx_record(rx_record),
 .begin_v(begin_v),.begin_epoch(begin_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),
 .auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),.fault(af));
 qkd_program_commit_join #(.SINKS(2))u_join(.ck(ck),.rst_n(rst_rn[3]),.begin_v(begin_v),.auth_v(auth_v),
 .execution_active(execution_active),.control_stores_ready(&cfg_image_ready),
 .auth_epoch(auth_epoch),.auth_digest(auth_digest),.sink_ready(sink_ready),.sink_fault(sink_fault),
 .sink_fusedcap(sink_fusedcap),.sink_epoch(sink_epoch),.sink_digest(sink_digest),
 .commit_v(commit_v),.ready(program_ready),.fault(jf),.installed_fusedcap(installed_fusedcap),
 .commit_epoch(program_epoch),.commit_digest(program_digest));
 qfd_host_native_context_rx #(.FILL(FILL)) u_context(.ck(ck),.rst_n(rst_rn[4]),.receive_slot(context_slot),.rx_v(rx_v&&context_slot),.rx_record(rx_record),
 .program_begin_v(begin_v),.program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_epoch(program_epoch),.program_digest(program_digest),
 .head_context_v(head_context_v),.head_stage(head_stage),.head_token(head_token),.head_position(head_position),.native_active(execution_active),
 .host_epoch_valid(host_epoch_valid),.host_epoch(host_epoch),.host_tag(host_tag),.host_gen(host_gen),
 .host_fusedcap(context_cap),.host_image_epoch(context_image_epoch),.host_image_digest(context_image_digest),.fault(cf));
 qfd_program_witness_tx u_witness(.ck(ck),.rst_n(rst_rn[5]),.send_slot(witness_slot),.commit_v(commit_v),
 .program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_fault(jf|af|slot_fault),
 .program_epoch(program_epoch),.program_digest(program_digest),.tx_v(tx_v),.tx_observed_v(tx_observed_v),.tx_record(tx_record),.fault(wf));
 assign fault=af|jf|cf|wf|slot_fault;
endmodule

// =====================================================================================================================
// qfd_sys_face_fill_ctx (MU-DQ-BOOTCTX 2026-10-19, coordinator 0kg (1)): the RUNTIME multi-user filler initial context.
// Source = the KV/system die host plane; transport = the EXISTING KV->compute D2D HOST context record (kind 12, the
// program port's compiled context_slot, one per token run of the latency user); no new D2D lane, slot or die port.
// The kind12 DATA[188:142] field (qfd_host_native_context_rx FILL 1) carries at most one filler context per record:
//   FC = {pos18 [188:171], tok18 [170:153], seq8 [152:145], user2 [144:143], v [142]}
// seq = the index (since the user's boot context load) of the filler RESULT whose bank write this context replaces:
// the context is applied on that result's edge instead of {argmax token, pos + 1} (a new request for user `user`
// starts at token `tok`, position `pos`).  The record arrives on its compiled slot edge s (static schedule: no credit,
// no ready); the receiver validates it on s (host_epoch_valid); this block registers FC on s and, when the record was
// accepted and v = 1, puts the ctlm runtime context word on the dh DW lane on edge s + 1 for one edge:
//   dw_v 1, dw_addr 5, dw_data = {16'h4346 'CF' [63:48], 2'b00 [47:46], seq8 [45:38], user2 [37:36], tok18 [35:18],
//   pos18 [17:0]}
// (qfd_dv_cmd_cal_mu CTX_DW: a DW5 word while the image is sealed and not loading = runtime context, ctx_rt; qfd_tt_ctlm_dv
// OPSEG checks tag / user / seq / ranges and arms the user's pending context; a bad or LATE record is a sticky op_fault).
// The face's own DW replay (program install) never overlaps: the host context is invalid between BEGIN and the
// commit; an overlap anyway (prog_dw_busy on the emit edge) is a sticky fault.  Cost: 47 + 1 + 68 + 1 flops, 0 edges on
// any existing path (+1 edge from the record slot to the dh word; the ctlm adds its pin + calendar + arm edges).
// =====================================================================================================================
module qfd_sys_face_fill_ctx (
    input  wire         ck,
    input  wire         rst_n,
    input  wire         context_slot,
    input  wire         rx_v,
    input  wire [46:0]  rx_fill,          // rx_record[188:142]
    input  wire         host_epoch_valid, // the receiver's verdict on the slot edge (registered by it)
    input  wire         prog_dw_busy,     // the face's DW replay drives the lane on this edge
    output reg  [67:0]  dw,               // {dw_v, dw_addr3, dw_data64}, OR-ed onto seq_dh's DW field
    output reg          fault
);
    reg        slot_q;
    reg [46:0] fq;
    wire       emit = slot_q && host_epoch_valid && fq[0];
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin slot_q <= 1'b0; fq <= 47'd0; dw <= 68'd0; fault <= 1'b0; end
        else begin
            slot_q <= context_slot && rx_v;
            if (context_slot) fq <= rx_fill;
            dw <= emit ? {1'b1, 3'd5, 16'h4346, 2'b00, fq[10:3], fq[2:1], fq[28:11], fq[46:29]} : 68'd0;
            if (emit && prog_dw_busy) fault <= 1'b1;
        end
    end
endmodule
