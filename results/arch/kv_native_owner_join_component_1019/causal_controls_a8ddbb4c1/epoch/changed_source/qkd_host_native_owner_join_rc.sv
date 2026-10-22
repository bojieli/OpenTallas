// Private common-clock functional association only. No production CDC claim.
// Frozen state: pending 66 + active 95 + sticky protocol fault 1 = 162 bits.
module qkd_host_native_owner_join_rc #(
  parameter bit ENABLE_NATIVE_OWNER_JOIN = 1'b0
)(
  input wire clk, input wire raw_por_n,
  input wire issue_fire,
  input wire [15:0] issue_client,
  input wire [7:0] issue_slot,
  input wire [1:0] issue_desc_gen,
  input wire [17:0] issue_position, issue_input_token,
  input wire package_accept_v,
  input wire [17:0] package_position, package_input_token,
  input wire [1:0] package_gen,
  input wire hc_accept_v,
  input wire [17:0] hc_position, hc_input_token,
  input wire [1:0] hc_gen,
  input wire request_v,
  input wire [17:0] request_position, request_input_token,
  input wire [1:0] request_gen,
  input wire allocation_fire,
  input wire [58:0] allocation_tag,
  input wire [1:0] allocation_gen,
  input wire terminal_v,
  input wire [58:0] terminal_tag,
  input wire [1:0] terminal_gen,
  // Actual raw scheduler tuple; no invented native key or input/next comparison.
  input wire raw_done_v,
  input wire [15:0] raw_client,
  input wire [7:0] raw_slot,
  input wire [1:0] raw_desc_gen,
  input wire [17:0] raw_position,
  input wire raw_unready, raw_report_needed,
  // Keys: {client16,slot8,descriptor_generation2,terminal_TAG59,native_gen2}.
  // These must come from the immutable saved event/owner lineage, not latest grant.
  input wire certificate_v, certificate_health_bound,
  input wire [86:0] certificate_key,
  input wire event_copy_v,
  input wire [86:0] event_key,
  input wire prompt_retired_v,
  input wire [86:0] prompt_key,
  // Prospective saved CQ key is independent of the offer enable, avoiding
  // a certify/fault feedback loop while vetoing malformed success pre-offer.
  input wire cq_offer_native_valid,
  input wire [86:0] cq_offer_key,
  output wire cq_offer_ok,
  input wire cq_b_v,
  input wire [86:0] cq_key,
  input wire post_retired_v,
  input wire [58:0] post_tag,
  input wire [1:0] post_gen,
  output wire certificate_key_ok,
  output wire issue_ready, request_allow, binding_valid, protocol_fault,
  output wire [1:0] pending_phase,
  output wire [15:0] pending_client,
  output wire [7:0] pending_slot,
  output wire [1:0] pending_desc_gen,
  output wire [17:0] pending_position, pending_input_token,
  output wire [15:0] bound_client,
  output wire [7:0] bound_slot,
  output wire [17:0] bound_position,
  output wire [1:0] bound_desc_gen, bound_native_gen,
  output wire [58:0] bound_request_tag, bound_terminal_tag,
  output wire raw_cleanup_allow,
  output wire binding_certified
);
  localparam [1:0] EMPTY=2'd0, ISSUED=2'd1, PACKAGE=2'd2, HC=2'd3;
  typedef struct packed {
    logic [15:0] client;
    logic [7:0] slot;
    logic [17:0] position, input_token;
    logic [1:0] package_gen, desc_gen, phase;
  } pending_t;
  typedef struct packed {
    logic [15:0] client;
    logic [7:0] slot;
    logic [58:0] request_tag;
    logic [1:0] native_gen, desc_gen;
    logic valid, raw_seen, cert_seen, terminal_seen, event_copied;
    logic post_seen, report_needed, report_drained;
  } active_t;
  pending_t p_q, p_d;
  active_t a_q, a_d;
  logic fault_q, fault_d;
  wire [58:0] expected_terminal = {a_q.request_tag[58:43],6'd37,
                                  a_q.request_tag[36:0]};
  wire [86:0] expected_key = {a_q.client,a_q.slot,a_q.desc_gen,
                              expected_terminal,a_q.native_gen};
  wire raw_active_match = a_q.valid && raw_client==a_q.client &&
    raw_slot==a_q.slot && raw_desc_gen==a_q.desc_gen &&
    raw_position=={5'b0,a_q.request_tag[18:6]};
  wire raw_pending_match = p_q.phase!=EMPTY && raw_client==p_q.client &&
    raw_slot==p_q.slot && raw_desc_gen==p_q.desc_gen && raw_position==p_q.position;
  wire allocation_match = allocation_tag[42:37]==6'd0 &&
    allocation_tag[5:0]==6'd0 && p_q.position[17:13]==5'd0 &&
    allocation_tag[36:19]==p_q.input_token &&
    allocation_tag[18:6]==p_q.position[12:0] && allocation_gen==p_q.package_gen;

  // Prospective authority uses only pre-state plus independently validated
  // CURRENT raw/terminal inputs. Never certificate_v, event_copy_v or a_d.
  wire certificate_key_match = (certificate_key&87'h7fffffe0001fffffffffff)==(expected_key&87'h7fffffe0001fffffffffff);
  wire raw_current_valid = raw_active_match && !raw_unready && !a_q.raw_seen;
  wire terminal_current_valid = a_q.valid && !a_q.terminal_seen &&
    terminal_tag==expected_terminal && terminal_gen==a_q.native_gen;
  wire current_events_valid = (!raw_done_v || raw_current_valid) &&
                              (!terminal_v || terminal_current_valid);
  wire raw_seen_now = a_q.raw_seen || (raw_done_v && raw_current_valid);
  wire terminal_seen_now = a_q.terminal_seen || (terminal_v && terminal_current_valid);
  assign certificate_key_ok = !ENABLE_NATIVE_OWNER_JOIN ||
    (a_q.valid && !fault_q && !a_q.cert_seen && certificate_health_bound &&
     certificate_key_match && raw_seen_now && terminal_seen_now && current_events_valid);

  wire accepted_request_held = a_q.valid && request_position=={5'd0,a_q.request_tag[18:6]} &&
    request_input_token==a_q.request_tag[36:19] && request_gen==a_q.native_gen;
  wire request_match = request_position==p_q.position &&
    request_input_token==p_q.input_token && request_gen==p_q.package_gen;
  assign issue_ready = ENABLE_NATIVE_OWNER_JOIN && !fault_q && p_q.phase==EMPTY;
  assign request_allow = ENABLE_NATIVE_OWNER_JOIN && !fault_q &&
                          p_q.phase==HC && !a_q.valid && request_match;
  assign binding_valid = ENABLE_NATIVE_OWNER_JOIN && a_q.valid;
  assign binding_certified = binding_valid && a_q.cert_seen && !fault_q;
  assign protocol_fault = ENABLE_NATIVE_OWNER_JOIN && fault_q;
  assign cq_offer_ok = !ENABLE_NATIVE_OWNER_JOIN || (a_q.valid &&
    !fault_q && a_q.cert_seen && a_q.raw_seen && a_q.terminal_seen &&
    a_q.event_copied && cq_offer_native_valid && cq_offer_key==expected_key);
  assign pending_phase = ENABLE_NATIVE_OWNER_JOIN ? p_q.phase : EMPTY;
  assign pending_client = ENABLE_NATIVE_OWNER_JOIN ? p_q.client : 16'd0;
  assign pending_slot = ENABLE_NATIVE_OWNER_JOIN ? p_q.slot : 8'd0;
  assign pending_desc_gen = ENABLE_NATIVE_OWNER_JOIN ? p_q.desc_gen : 2'd0;
  assign pending_position = ENABLE_NATIVE_OWNER_JOIN ? p_q.position : 18'd0;
  assign pending_input_token = ENABLE_NATIVE_OWNER_JOIN ? p_q.input_token : 18'd0;
  assign bound_position = ENABLE_NATIVE_OWNER_JOIN ? {5'b0,a_q.request_tag[18:6]} : 18'd0;
  assign bound_client = ENABLE_NATIVE_OWNER_JOIN ? a_q.client : 16'd0;
  assign bound_slot = ENABLE_NATIVE_OWNER_JOIN ? a_q.slot : 8'd0;
  assign bound_desc_gen = ENABLE_NATIVE_OWNER_JOIN ? a_q.desc_gen : 2'd0;
  assign bound_native_gen = ENABLE_NATIVE_OWNER_JOIN ? a_q.native_gen : 2'd0;
  assign bound_request_tag = ENABLE_NATIVE_OWNER_JOIN ? a_q.request_tag : 59'd0;
  assign bound_terminal_tag = ENABLE_NATIVE_OWNER_JOIN ? expected_terminal : 59'd0;
  // Cleanup authority belongs to the raw producer, independent of this checker.
  assign raw_cleanup_allow = 1'b1;

  always_comb begin
    p_d=p_q; a_d=a_q; fault_d=fault_q;
    if (ENABLE_NATIVE_OWNER_JOIN) begin
      // Actual token transport samples ready; its accepted VALID can remain high.
      // Repeated presentation of the same owned tuple is not a new allocation.
      if (request_v && !(p_q.phase==HC && request_match) && !accepted_request_held) fault_d=1'b1;
      if (issue_fire) begin
        if (p_q.phase!=EMPTY || fault_q) fault_d=1'b1;
        else begin
          p_d.client=issue_client; p_d.slot=issue_slot;
          p_d.desc_gen=issue_desc_gen; p_d.position=issue_position;
          p_d.input_token=issue_input_token; p_d.package_gen=2'd0;
          p_d.phase=ISSUED;
        end
      end
      if (package_accept_v) begin
        if (p_q.phase!=ISSUED || package_position!=p_q.position ||
            package_input_token!=p_q.input_token) fault_d=1'b1;
        else begin p_d.package_gen=package_gen; p_d.phase=PACKAGE; end
      end
      if (hc_accept_v) begin
        if (p_q.phase!=PACKAGE || hc_position!=p_q.position ||
            hc_input_token!=p_q.input_token || hc_gen!=p_q.package_gen)
          fault_d=1'b1;
        else p_d.phase=HC;
      end
      // Match pre-edge HC, not a simultaneous newly captured HC reservation.
      if (allocation_fire) begin
        if (!request_v || !request_allow || !allocation_match || issue_fire || package_accept_v || hc_accept_v)
          fault_d=1'b1;
        else begin
          a_d='0; a_d.client=p_q.client; a_d.slot=p_q.slot;
          a_d.desc_gen=p_q.desc_gen; a_d.request_tag=allocation_tag;
          a_d.native_gen=allocation_gen; a_d.valid=1'b1;
          p_d.phase=EMPTY;
        end
      end
      if (terminal_v) begin
        if (!a_q.valid || a_q.terminal_seen || terminal_tag!=expected_terminal ||
            terminal_gen!=a_q.native_gen) fault_d=1'b1;
        else a_d.terminal_seen=1'b1;
      end
      if (raw_done_v) begin
        if (raw_unready && raw_pending_match && !allocation_fire) begin
          // Typed NO_NATIVE: no binding, epoch, or native key is manufactured.
          p_d.phase=EMPTY;
        end else if (!raw_unready && raw_active_match && !a_q.raw_seen) begin
          a_d.raw_seen=1'b1; a_d.report_needed=raw_report_needed;
        end else fault_d=1'b1;
      end
      if (certificate_v) begin
        if (!certificate_key_ok) fault_d=1'b1;
        else a_d.cert_seen=1'b1;
      end
      if (event_copy_v) begin
        if (!a_q.valid || a_q.event_copied || !a_d.raw_seen ||
            !a_d.report_needed || event_key!=expected_key) fault_d=1'b1;
        else a_d.event_copied=1'b1;
      end
      if (prompt_retired_v) begin
        if (!a_q.valid || !a_d.raw_seen || a_d.report_needed ||
            a_q.report_drained || prompt_key!=expected_key) fault_d=1'b1;
        else a_d.report_drained=1'b1;
      end
      if (cq_b_v) begin
        if (!a_q.valid || !a_d.raw_seen || !a_d.report_needed ||
            !a_d.event_copied || a_q.report_drained || cq_key!=expected_key)
          fault_d=1'b1;
        else a_d.report_drained=1'b1;
      end
      if (post_retired_v) begin
        if (!a_q.valid || a_q.post_seen || !a_d.raw_seen ||
            !a_d.terminal_seen || post_tag!=expected_terminal || post_gen!=a_q.native_gen) fault_d=1'b1;
        else a_d.post_seen=1'b1;
      end
      // Credit, terminal, raw completion and event-copy never independently free.
      // Prompt POST can precede the health cutoff. Keep its key until
      // actual certification too, so cutoff cannot lose its bound identity.
      if (a_q.valid && a_d.raw_seen && a_d.terminal_seen && a_d.cert_seen &&
          a_d.post_seen && a_d.report_drained &&
          (!a_d.report_needed || a_d.event_copied)) a_d.valid=1'b0;
    end
  end
  always_ff @(posedge clk or negedge raw_por_n) begin
    if (!raw_por_n) begin p_q<='0; a_q<='0; fault_q<=1'b0; end
    else begin p_q<=p_d; a_q<=a_d; fault_q<=fault_d; end
  end
endmodule
