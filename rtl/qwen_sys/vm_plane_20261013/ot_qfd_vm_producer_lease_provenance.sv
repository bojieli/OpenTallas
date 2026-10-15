`timescale 1ns/1ps
// Distinct seq40/canonical-mode candidate, disabled by default.
// Historical9110 seq16 source is preserved.
// Candidate transport adapter. No region ABI or physical master adoption.
// commit_v must be the ACTUAL native write-commit event, not loader intent.
// commit_pending includes all accepted writes not yet committed. Writes remain
// reserved through GLOBAL release: one result is not a whole-operation snapshot.
module ot_qfd_vm_producer_lease_provenance #(
    parameter integer ENABLE = 0, parameter integer MUT = 0
)(
    input wire clk, rst_n,
    input wire acquire_v, output wire acquire_ready,
    input wire [378:0] held_ib, input wire held_mode,
    input wire [15:0] held_token, input wire [15:0] held_context, input wire [3:0] request_phase,
    input wire [95:0] request_address, input wire [4:0] request_root,
    input wire [15:0] request_recipient,
    input wire query_v, output wire query_ready,
    input wire [15:0] query_context, input wire [31:0] query_version,
    input wire [39:0] query_seq40, input wire query_mode,
    input wire [15:0] query_token, input wire [20:0] query_epoch,
    input wire commit_v, commit_pending,
    output wire native_write_allowed,
    output wire [31:0] acquire_version,
    output wire read_v, input wire read_ready,
    output wire [378:0] read_ib, output wire read_mode,
    output wire [3:0] read_phase, output wire [95:0] read_address,
    output wire [4:0] read_root, output wire [15:0] read_recipient,
    output wire [39:0] read_seq40, output wire [15:0] read_token, output wire [20:0] read_epoch,
    input wire response_v, output wire response_ready,
    input wire [511:0] response_data,
    output wire q_v, input wire q_ready, output wire [511:0] q_data,
    output wire [15:0] q_context, output wire [31:0] q_version,
    output wire q_mode, output wire [3:0] q_phase,
    output wire [95:0] q_address, output wire [4:0] q_root,
    output wire [15:0] q_recipient, output wire [39:0] q_seq40,
    output wire [15:0] q_token, output wire [20:0] q_epoch,
    input wire release_v, output wire release_ready,
    input wire [15:0] release_token, input wire [15:0] release_context, input wire [31:0] release_version,
    input wire recipients_quiescent,
    output wire source_output_drained,
    input wire transport_flush_req, output wire transport_flush_ack,
    output wire fault,
    output wire [31:0] blocked_write_cycles, output wire [31:0] leased_cycles
);
    // No token allocator: held_token must come from the real shared owner.
    reg [15:0] token_q;
    reg [20:0] epoch_q;
    reg active,provenance_fault;
    wire inner_fault,inner_query_ready,inner_release_ready,inner_drained;
    wire query_match=active && ((MUT==11) || query_token==token_q);
    wire release_match=active && ((MUT==14) || release_token==token_q);
    assign fault=inner_fault || provenance_fault;
    assign query_ready=inner_query_ready && query_match && !fault;
    assign release_ready=inner_release_ready && release_match && !query_v && !fault;
    assign source_output_drained=inner_drained && !query_v && !fault;
    assign read_token=(MUT==13) ? held_token : token_q;
    assign q_token=(MUT==13) ? held_token : token_q;
    assign read_epoch=(MUT==12) ? query_epoch : epoch_q;
    assign q_epoch=(MUT==12) ? query_epoch : epoch_q;
    always @(posedge clk) begin
        if(!rst_n) begin token_q<=0;epoch_q<=0;active<=0;provenance_fault<=0;end
        else if(ENABLE) begin
            if(transport_flush_ack) begin active<=0;provenance_fault<=0;end
            if(acquire_v && acquire_ready) begin token_q<=held_token;active<=1;end
            if(query_v && query_ready) epoch_q<=query_epoch;
            if(release_v && !release_match) provenance_fault<=1;
            if(release_v && release_ready) active<=0;
        end
    end
    ot_qfd_vm_producer_lease_seq40 #(.ENABLE(ENABLE),.MUT(MUT<=10 ? MUT : 0)) u_lease (
        .clk(clk),
        .rst_n(rst_n),
        .acquire_v(acquire_v),
        .acquire_ready(acquire_ready),
        .held_ib(held_ib),
        .held_mode(held_mode),
        .held_context(held_context),
        .request_phase(request_phase),
        .request_address(request_address),
        .request_root(request_root),
        .request_recipient(request_recipient),
        .query_v(query_v && query_match && !fault),
        .query_ready(inner_query_ready),
        .query_context(query_context),
        .query_version(query_version),
        .query_seq40(query_seq40),
        .query_mode(query_mode),
        .commit_v(commit_v),
        .commit_pending(commit_pending),
        .native_write_allowed(native_write_allowed),
        .acquire_version(acquire_version),
        .read_v(read_v),
        .read_ready(read_ready),
        .read_ib(read_ib),
        .read_mode(read_mode),
        .read_phase(read_phase),
        .read_address(read_address),
        .read_root(read_root),
        .read_recipient(read_recipient),
        .read_seq40(read_seq40),
        .response_v(response_v),
        .response_ready(response_ready),
        .response_data(response_data),
        .q_v(q_v),
        .q_ready(q_ready),
        .q_data(q_data),
        .q_context(q_context),
        .q_version(q_version),
        .q_mode(q_mode),
        .q_phase(q_phase),
        .q_address(q_address),
        .q_root(q_root),
        .q_recipient(q_recipient),
        .q_seq40(q_seq40),
        .release_v(release_v && release_match && !query_v && !fault),
        .release_ready(inner_release_ready),
        .release_context(release_context),
        .release_version(release_version),
        .recipients_quiescent(recipients_quiescent),
        .source_output_drained(inner_drained),
        .transport_flush_req(transport_flush_req),
        .transport_flush_ack(transport_flush_ack),
        .fault(inner_fault),
        .blocked_write_cycles(blocked_write_cycles),
        .leased_cycles(leased_cycles)
    );
endmodule
