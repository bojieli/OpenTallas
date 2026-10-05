// Capacity-one protected-record next-state/control leaf. Default off.
// Storage is the b41 coded144 active record, decoded through selected HELD2
// cuts and re-encoded before capture by its owner. This leaf adds no storage.
// It does not instantiate macros, manufacture completion, or implement CDC.
// Maxwell selected schedule: old read/RDREG2, decode2, owner1, merge1,
// encode1, write1, verify/RDREG2, decode2, owner1, receipt1; bank II28.
// Cut providers must hold input/owner through each actual captured terminal.
// This is preparation, not a qualified sequential engine. Integration must
// schedule coded record decode/update/encode feedback within the selected
// cuts; next_capture is an update proposal, never permission to bypass codec.
module ot_dsrom_w11_bank_next #(
  parameter bit ENABLE = 1'b0
) (
  input logic record_checked, record_bad, phase_fault,
  input logic [100:0] current_record,
  output logic [100:0] next_record,
  output logic next_capture, fault_request,

  // Reservation metadata comes from captured coded header/row seats, not GO.
  input logic reserve_capture, reserve_init, reserve_authorized,
  input logic [82:0] reserve_owner,
  // These are held source-owned row authorities. whole_row_cold_empty must
  // cover live inputs/other columns too, not merely this output's mask.
  input logic retained_initialized, whole_row_cold_empty,
  input logic ports_exclusive, inputs_finished, columns_complete,

  output logic old_read_valid, merge_encode_valid, zero_encode_valid,
  output logic write_valid, verify_valid, receipt_valid,
  output logic [82:0] operation_owner,
  output logic operation_init,

  // All accept/terminal ports are source-owned positive captured events.
  // old_checked_capture covers copy0 checked data/check plus held owner;
  // verify_qualified covers whole256 image equality and all four W6 stripes,
  // not only the output mask. commit_qualified requires BOTH data and check
  // commits. No request, elapsed timer, or ready signal qualifies either.
  input logic old_read_accept, old_read_return, old_checked_capture,
  input logic merge_encode_capture, zero_encode_capture, write_accept,
  input logic verify_accept,
  input logic [82:0] accepted_owner,
  input logic accepted_init, accepted_bad,
  input logic [5:0] commit_valid, verify_terminal_valid,
  input logic [6*83-1:0] commit_owner, verify_owner,
  input logic [5:0] commit_init, verify_init, commit_qualified,
  input logic [5:0] verify_qualified, verify_bad,
  input logic receipt_capture, positive_reverse_capture,
  input logic [82:0] receipt_owner, reverse_owner,
  input logic receipt_init, reverse_init,
  input logic actual_phase_retire, no_external_debt,
  output logic initialized_capture, field_retired_capture
);
  // Raw101: owner83, state4, commit6, verified6, valid1, init1.
  // Both added operation bits fit the existing coded144 record allocations.
  localparam logic [3:0] EMPTY=0, INITIALIZE=1, COLLECT=2,
    READ_REQUEST=3, READ_RETURN=4, CHECK_OLD=5, ENCODE_MERGE=6,
    WRITE_REQUEST=7, ALL_COMMIT=8, VERIFY_REQUEST=9, ALL_VERIFY=10,
    COUNT_HELD=11, COUNT_RETURN=12, RETIRED=13, QUARANTINE=14;
  wire [82:0] owner = current_record[82:0];
  wire [3:0] state = current_record[86:83];
  wire [5:0] committed = current_record[92:87];
  wire [5:0] verified = current_record[98:93];
  wire live = current_record[99];
  wire init_kind = current_record[100];
  wire usable = ENABLE && record_checked && !record_bad && !phase_fault;
  wire match_accept = accepted_owner == owner && accepted_init == init_kind
                      && !accepted_bad;

  // Current-state view is independent of downstream ready/accept. No delta
  // feedback from secondary permission, fault, or helper retirement outputs.
  always_comb begin
    operation_owner = owner;
    operation_init = init_kind;
    old_read_valid = usable && live && ports_exclusive && state==READ_REQUEST;
    zero_encode_valid = usable && live && ports_exclusive && state==INITIALIZE;
    merge_encode_valid = usable && live && ports_exclusive && state==ENCODE_MERGE;
    write_valid = usable && live && ports_exclusive && state==WRITE_REQUEST;
    verify_valid = usable && live && ports_exclusive && state==VERIFY_REQUEST;
    receipt_valid = usable && live && state==COUNT_HELD && &committed && &verified;
  end

  logic bad_event;
  logic [5:0] commit_next, verify_next;
  integer copy_i;
  always_comb begin
    next_record = current_record;
    next_capture = 1'b0;
    fault_request = ENABLE && (record_bad || phase_fault ||
                    (record_checked && state==QUARANTINE));
    initialized_capture = 1'b0;
    field_retired_capture = 1'b0;
    bad_event = 1'b0;
    commit_next = committed;
    verify_next = verified;
    if (usable) begin
      // Refuse the complete edge before changing any mask if any event is bad.
      for (copy_i=0; copy_i<6; copy_i=copy_i+1) begin
        if (commit_valid[copy_i]) begin
          if (!live || !(state==ALL_COMMIT ||
              (state==WRITE_REQUEST && write_accept && match_accept && ports_exclusive)) ||
              committed[copy_i] ||
              !commit_qualified[copy_i] ||
              commit_owner[copy_i*83 +: 83]!=owner ||
              commit_init[copy_i]!=init_kind) bad_event=1'b1;
          commit_next[copy_i]=1'b1;
        end
        if (verify_terminal_valid[copy_i]) begin
          if (!live || state!=ALL_VERIFY || verified[copy_i] ||
              !verify_qualified[copy_i] || verify_bad[copy_i] ||
              verify_owner[copy_i*83 +: 83]!=owner ||
              verify_init[copy_i]!=init_kind) bad_event=1'b1;
          verify_next[copy_i]=1'b1;
        end
      end
      if (old_read_accept || old_read_return || old_checked_capture ||
          merge_encode_capture || zero_encode_capture || write_accept || verify_accept) begin
        if (!live || !ports_exclusive || !match_accept) bad_event=1'b1;
        if (old_read_accept && state!=READ_REQUEST) bad_event=1'b1;
        if (old_read_return && state!=READ_RETURN) bad_event=1'b1;
        if (old_checked_capture && state!=CHECK_OLD) bad_event=1'b1;
        if (merge_encode_capture && state!=ENCODE_MERGE) bad_event=1'b1;
        if (zero_encode_capture && state!=INITIALIZE) bad_event=1'b1;
        if (write_accept && state!=WRITE_REQUEST) bad_event=1'b1;
        if (verify_accept && state!=VERIFY_REQUEST) bad_event=1'b1;
      end
      if (receipt_capture && (!live || state!=COUNT_HELD ||
          !(&committed) || !(&verified) || receipt_owner!=owner ||
          receipt_init!=init_kind)) bad_event=1'b1;
      if (positive_reverse_capture && (!live || state!=COUNT_RETURN ||
          reverse_owner!=owner || reverse_init!=init_kind)) bad_event=1'b1;
      if (reserve_capture && (state!=EMPTY || live || !reserve_authorized ||
          reserve_owner[82:75]==0 ||
          (reserve_init ? !whole_row_cold_empty : !retained_initialized)))
        bad_event=1'b1;
      if ((state==EMPTY && live) || (state!=EMPTY && !live) ||
          (init_kind && (state==COLLECT || state==READ_REQUEST ||
           state==READ_RETURN || state==CHECK_OLD || state==ENCODE_MERGE ||
           state==RETIRED)) || (!init_kind && state==INITIALIZE)) bad_event=1'b1;
      if (live && state!=COLLECT && state!=COUNT_HELD &&
          state!=COUNT_RETURN && state!=RETIRED && state!=QUARANTINE &&
          !ports_exclusive) bad_event=1'b1;

      case (state)
        EMPTY: if (reserve_capture) begin
          next_record={reserve_init,1'b1,6'b0,6'b0,
                       (reserve_init ? INITIALIZE : COLLECT),reserve_owner};
          next_capture=1'b1;
        end
        INITIALIZE: if (zero_encode_capture) begin
          next_record[86:83]=WRITE_REQUEST; next_capture=1'b1;
        end
        COLLECT: if (live && !init_kind && columns_complete && inputs_finished &&
                     ports_exclusive && retained_initialized) begin
          next_record[86:83]=READ_REQUEST; next_capture=1'b1;
        end
        READ_REQUEST: if (old_read_accept) begin
          next_record[86:83]=READ_RETURN; next_capture=1'b1;
        end
        READ_RETURN: if (old_read_return) begin
          next_record[86:83]=CHECK_OLD; next_capture=1'b1;
        end
        CHECK_OLD: if (old_checked_capture) begin
          next_record[86:83]=ENCODE_MERGE; next_capture=1'b1;
        end
        ENCODE_MERGE: if (merge_encode_capture) begin
          next_record[86:83]=WRITE_REQUEST; next_capture=1'b1;
        end
        WRITE_REQUEST: if (write_accept) begin
          // Actual matched commits may share the accepted write edge. Do not
          // invent a mandatory extra ACK wait or drop simultaneous terminals.
          next_record[92:87]=commit_next;
          next_record[86:83]=(&commit_next) ? VERIFY_REQUEST : ALL_COMMIT;
          next_capture=1'b1;
        end
        ALL_COMMIT: if (|commit_valid) begin
          next_record[92:87]=commit_next; next_capture=1'b1;
          if (&commit_next) next_record[86:83]=VERIFY_REQUEST;
        end
        VERIFY_REQUEST: if (verify_accept) begin
          next_record[86:83]=ALL_VERIFY; next_capture=1'b1;
        end
        ALL_VERIFY: if (|verify_terminal_valid) begin
          next_record[98:93]=verify_next; next_capture=1'b1;
          if ((&committed) && (&verify_next)) next_record[86:83]=COUNT_HELD;
        end
        COUNT_HELD: if (receipt_capture) begin
          next_record[86:83]=COUNT_RETURN; next_capture=1'b1;
        end
        COUNT_RETURN: if (positive_reverse_capture) begin
          // Initialize only the retained row-image owner; clear this operation
          // so field admission captures its own owner/mask afresh. No field
          // received bits or source counters are fabricated by initialization.
          if (init_kind) begin
            initialized_capture=1'b1; next_record='0;
          end else begin
            next_record[86:83]=RETIRED; field_retired_capture=1'b1;
          end
          next_capture=1'b1;
        end
        RETIRED: if (actual_phase_retire && no_external_debt) begin
          next_record='0; next_capture=1'b1;
        end
        QUARANTINE: begin end // Only external authoritative all-copy rearm.
        default: bad_event=1'b1;
      endcase
      if (bad_event) begin
        next_record=current_record;
        next_record[86:83]=QUARANTINE;
        next_capture=1'b1; fault_request=1'b1;
        initialized_capture=1'b0; field_retired_capture=1'b0;
      end
    end
    // On a bad coded record no decoded owner is safe to rewrite. The header's
    // protected sticky fault retains all previously accepted external debt.
  end
endmodule
