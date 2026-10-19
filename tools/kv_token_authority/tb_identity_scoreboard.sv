module tb;
  reg clk=0;
  always #5 clk=~clk;
  localparam [31:0] ID=32'h03071302;
  reg known=0, av=0,rv=0,rok=1,dv=0,bv=0,sv=0,pok=1,success=1,check=0;
  reg [31:0] aid=ID,rid=ID,did=ID,bid=ID,sid=ID,beat=0;
  wire integer errors, count, raw_count;
  wire executed, passed;
  integer test_case=0, expected_errors=0;
  kva_identity_scoreboard #(.ID_W(32),.NPROG(1),.RESULT_BEATS(2),.REQUIRE_RETIRE(0)) dut(
    .sample_clk(clk),.expected_ids(ID),.required_monitors_known(known),
    .accept_v(av),.accept_id(aid),.run_v(rv),.run_ok(rok),.run_id(rid),
    .source_done_v(dv),.source_done_id(did),.result_v(bv),.result_id(bid),.result_beat(beat),
    .status_authoritative(known),.status_v(sv),.status_id(sid),.status_payload_ok(pok),
    .status_success(success),.final_check(check),.errors(errors),.successful_count(count),
    .raw_status_count(raw_count),.programme_executed(executed),.final_pass(passed));
  task tick; begin @(posedge clk); #1; @(negedge clk); end endtask
  task start; begin av=1; tick; av=0; rv=1; tick; rv=0; end endtask
  task done; begin bv=1; beat=0; tick; beat=1; tick; bv=0; dv=1; tick; dv=0; end endtask
  initial begin
    if(!$value$plusargs("CASE=%d",test_case)) test_case=0;
    @(negedge clk);
    case(test_case)
      0: begin known=1; start; done; sv=1; tick; sv=0; end
      1: begin // Arbitrary startup STATUS cannot allocate or retire.
        sv=1; sid=32'hdeadbeef; tick; sv=0;
        if(errors!=0 || count!=0 || raw_count!=1) $fatal(1,"STARTUP_AUTHORITY_ORACLE");
        known=1; sid=ID; start; done; sv=1; tick; sv=0;
      end
      2: begin // First known idle edge, before any programme or trace start.
        known=1; sv=1; pok=0; tick; sv=0; pok=1;
        if(errors!=1 || count!=0) $fatal(1,"FIRST_KNOWN_IDLE_ORACLE");
        expected_errors=1; start;
      end
      3: begin
        known=1; start; done; sv=1; sid=32'hdeadbeef; tick; sv=0;
        if(errors!=1 || count!=0) $fatal(1,"WRONG_IDENTITY_ORACLE");
        sid=ID; sv=1; tick; tick; sv=0; expected_errors=2;
      end
      4: begin known=1; expected_errors=1; end
      5: begin known=1; start; end // Explicit partial smoke: no retirement claim.
      6: begin known=1; start; sv=1; success=0; tick; sv=0; expected_errors=1; end
      7: begin known=1; start; sv=1'bx; tick; sv=0; expected_errors=1; end
      8: begin known=1; start; done; sv=1; tick; tick; sv=0; expected_errors=1; end
      9: begin known=1; start; sv=1; tick; sv=0; expected_errors=1; end
      10: begin known=1; start; bv=1; beat=1; tick; bv=0; expected_errors=1; end
      11: begin av=1; tick; av=0; known=1; start; expected_errors=1; end
      12: begin known=1; av=1'bx; tick; av=0; start; expected_errors=1; end
      default: $fatal(1,"unknown CASE");
    endcase
    check=1; tick; check=0;
    if(errors!=expected_errors) $fatal(1,"ERROR_COUNT_ORACLE got=%0d expected=%0d",errors,expected_errors);
    if(test_case==4 && executed) $fatal(1,"PROGRAMME_EXECUTED_ORACLE");
    if(test_case!=4 && !executed) $fatal(1,"PROGRAMME_EXECUTED_ORACLE");
    if(expected_errors==0 && !passed) $fatal(1,"FINAL_PASS_ORACLE");
    if(expected_errors!=0 && passed) $fatal(1,"FINAL_FAIL_ORACLE");
    if((test_case==0 || test_case==1 || test_case==3 || test_case==8) && count!=1)
      $fatal(1,"SUCCESS_COUNT_ORACLE");
    $display("IDENTITY_CONTROL_PASS case=%0d errors=%0d success=%0d",test_case,errors,count);
    $finish;
  end
endmodule
