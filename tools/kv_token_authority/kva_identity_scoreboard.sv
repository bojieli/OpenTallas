// Verification-only ledger. No reset port: knowledge and errors survive reset.
// Caller packs {epoch,layer,position,token} into an exact ID_W-bit identity.
// expected_ids is constant throughout a run, entry i at i*ID_W +: ID_W.
// Drive/sample events after DUT NBA; monitor samples on the supplied sample_clk.
module kva_identity_scoreboard #(
  parameter integer ID_W=128, NPROG=1, RESULT_BEATS=32,
  parameter integer REQUIRE_RETIRE=1
) (
  input wire sample_clk,
  input wire [NPROG*ID_W-1:0] expected_ids,
  input wire required_monitors_known,
  input wire accept_v, input wire [ID_W-1:0] accept_id,
  input wire run_v, run_ok, input wire [ID_W-1:0] run_id,
  input wire source_done_v, input wire [ID_W-1:0] source_done_id,
  input wire result_v, input wire [ID_W-1:0] result_id,
  input wire [31:0] result_beat,
  input wire status_authoritative, status_v,
  input wire [ID_W-1:0] status_id,
  input wire status_payload_ok, status_success,
  input wire final_check,
  output integer errors=0, successful_count=0, raw_status_count=0,
  output reg programme_executed=0, final_pass=0
);
  reg accepted [0:NPROG-1];
  reg running [0:NPROG-1];
  reg source_done [0:NPROG-1];
  reg terminal [0:NPROG-1];
  reg [RESULT_BEATS-1:0] result_bitmap [0:NPROG-1];
  integer next_beat [0:NPROG-1];
  reg [NPROG*ID_W-1:0] frozen_expected;
  reg map_seen=0;
  reg authority_seen=0;
  integer i,j,k;

  function automatic integer lookup(input reg [ID_W-1:0] id);
    integer n;
    begin
      lookup=-1;
      if (!$isunknown(id))
        for(n=0;n<NPROG;n=n+1)
          if(id === expected_ids[n*ID_W +: ID_W]) lookup=n;
    end
  endfunction

  task automatic fail(input string reason);
    begin
      errors=errors+1;
      final_pass=0;
      $display("KVA_IDENTITY_ERROR %s",reason);
    end
  endtask

  initial begin
    if (NPROG<1 || RESULT_BEATS<1) $fatal(1,"invalid ledger dimensions");
    for(i=0;i<NPROG;i=i+1) begin
      accepted[i]=0; running[i]=0; source_done[i]=0;
      terminal[i]=0; result_bitmap[i]='0; next_beat[i]=0;
    end
  end

  always @(posedge sample_clk) begin
    if(!map_seen) begin
      frozen_expected=expected_ids;
      map_seen=1;
      if($isunknown(expected_ids)) fail("unknown programme identity map");
      for(j=0;j<NPROG;j=j+1)
        for(k=j+1;k<NPROG;k=k+1)
          if(expected_ids[j*ID_W +: ID_W] === expected_ids[k*ID_W +: ID_W])
            fail("duplicate programme identity");
    end else if(expected_ids !== frozen_expected) fail("programme identity map changed");

    if(status_authoritative === 1'b1) authority_seen=1;
    else if(authority_seen) fail("authority withdrawn after known frontier");
    if(status_v === 1'b1) raw_status_count=raw_status_count+1;
    // Raw status is observable before authority but never changes owned state.
    if(status_v !== 1'b0)
      $display("KVA_RAW_STATUS known=%b valid=%b id=%h",status_authoritative,status_v,status_id);

    if(accept_v === 1'b1) begin
      k=lookup(accept_id);
      if(required_monitors_known !== 1'b1) fail("admission before monitor authority");
      else if(k<0) fail("unowned acceptance");
      else if(accepted[k]) fail("duplicate acceptance");
      else accepted[k]=1;
    end else if(accept_v !== 1'b0) fail("unknown acceptance valid");

    if(run_v === 1'b1) begin
      k=lookup(run_id);
      if(k<0) fail("unowned run");
      else if(!accepted[k] || running[k] || terminal[k] || run_ok !== 1'b1)
        fail("unaccepted duplicate or failed run");
      else running[k]=1;
    end else if(run_v !== 1'b0) fail("unknown run valid");

    if(result_v === 1'b1) begin
      k=lookup(result_id);
      if(k<0) fail("unowned RESULT");
      else if(!running[k] || terminal[k]) fail("inactive RESULT");
      else if($isunknown(result_beat) || result_beat !== next_beat[k] || result_beat>=RESULT_BEATS)
        fail("wrong duplicate or unordered RESULT");
      else begin result_bitmap[k][result_beat]=1; next_beat[k]=next_beat[k]+1; end
    end else if(result_v !== 1'b0) fail("unknown RESULT valid");

    if(source_done_v === 1'b1) begin
      k=lookup(source_done_id);
      if(k<0) fail("unowned source completion");
      else if(!running[k] || terminal[k] || source_done[k]) fail("inactive duplicate source completion");
      else source_done[k]=1;
    end else if(source_done_v !== 1'b0) fail("unknown source completion valid");

    if(status_authoritative === 1'b1) begin
      if(status_v !== 1'b0 && status_v !== 1'b1) fail("unknown STATUS valid after authority");
      if(status_v === 1'b1) begin
        k=lookup(status_id);
        if(k<0) fail("STATUS identity has no fallback");
        else if(!running[k] || terminal[k]) fail("inactive or duplicate STATUS");
        else if(status_payload_ok !== 1'b1 || $isunknown(status_success)) fail("malformed STATUS payload");
        else if(status_success && (!source_done[k] || !(&result_bitmap[k]))) fail("early successful STATUS");
        else begin
          terminal[k]=1;
          if(status_success) successful_count=successful_count+1;
          else fail("source-owned error STATUS");
        end
      end
    end

    if(final_check === 1'b1) begin
      programme_executed=1;
      for(j=0;j<NPROG;j=j+1)
        if(!accepted[j] || !running[j]) programme_executed=0;
      if(!programme_executed) fail("PROGRAMME_EXECUTED missing acceptance/run");
      if(REQUIRE_RETIRE && successful_count!=NPROG) fail("missing successful retirement");
      final_pass=(errors==0);
    end
  end
endmodule
