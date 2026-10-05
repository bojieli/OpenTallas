`timescale 1ps/1ps
// FUNCTIONAL FIXTURE ONLY.833ps is a simulation tick, never SS/FF credit.
// Full candidate dependencies are packaged; no HDL qualification claimed.
module bench_dsrom_balanced_selector_gate_prepare #(parameter integer MUTANT=0);
  reg clk=0,rst_n=0,go=0,o_valid=0,o_last=0,o_err=0,engine_fault=0;
  reg [1:0] o_rank=0;
  reg [14:0] src=0,dst=8192,ibase=4096;
  reg [14:0] n=0;
  reg [15:0] tk_k=0;
  reg [31:0] stride=0,tag=0;
  reg [2047:0] o_data=0;
  reg [511:0] ref_rq=0,cand_rq=0;
  wire ref_busy,cand_busy,ref_fault,cand_fault,ref_re,cand_re;
  wire [14:0] ref_ra,cand_ra;
  wire [3:0] ref_we,cand_we;
  wire [59:0] ref_wa,cand_wa;
  wire [2047:0] ref_wd,cand_wd;
  wire [511:0] ref_ed,cand_ed;
  wire ref_ev,cand_ev,ref_el,cand_el,ref_em,cand_em,ref_ready,cand_ready;
  wire [31:0] ref_et,cand_et;
  reg [2047:0] operands[0:255];
  reg [511:0] assertions[0:511]; // Assertion-only, never connected to a DUT input.
  reg [3:0] ref_saved_we[0:511];
  reg [59:0] ref_saved_wa[0:511];
  reg [2047:0] ref_saved_wd[0:511];
  integer ref_saved_cycle[0:511];
  integer cycle=0,ref_groups=0,cand_groups=0,ref_words=0,cand_words=0;
  integer expected_words=0,operand_half=0,ref_retire=-1,cand_retire=-1;
  integer normal_cases=0,abort_cases=0,fault_cases=0,active_case=-1;
  integer ref_return_groups=0,cand_return_groups=0,fetch_words=0;
  integer ref_return_cycle[0:511];
  reg [2:0] ref_return_nw[0:511];
  reg ref_return_last[0:511];
  reg [2047:0] ref_return_data[0:511];
  reg active=0,ref_seen_busy=0,cand_seen_busy=0,abort_mode=0;
  string image_root;
  // High416ps/low417ps; NBA and async checks settle1ps before comparison.
  initial forever begin #416 clk=1; #417 clk=0; end

  // Exact full target shape on both sides, including native4-bank DMA.
  ot_w15_coll_dma #(.WA(15),.FW(512),.TAGW(32),.N(4),.GW(4),
    .VM_ALWAYS_READY(1),.TOPK(1),.TK_NMAX(2048),.TK_DIG(8)) reference (
    .clk(clk),.rst_n(rst_n),.go(go),.mode(1'b1),.rnd(1'b0),.tag(tag),
    .src(src),.n(n),.dst(dst),.topk(1'b1),.ibase(ibase),.tk_k(tk_k),.tk_stride(stride),
    .busy(ref_busy),.fault(ref_fault),.words_out(),.words_in(),.vm_re(ref_re),.vm_raddr(ref_ra),.vm_rq(ref_rq),
    .vm_we(),.vm_waddr(),.vm_wdata(),.vm_ready4(1'b1),.vm_we4(ref_we),.vm_waddr4(ref_wa),.vm_wdata4(ref_wd),
    .e_valid(ref_ev),.e_ready(1'b1),.e_data(ref_ed),.e_last(ref_el),.e_mode(ref_em),.e_tag(ref_et),
    .o_valid(o_valid),.o_ready(ref_ready),.o_data(o_data),.o_last(o_last),.o_rank(o_rank),.o_err(o_err),.engine_fault(engine_fault));

  ot_w15_coll_dma_balanced_station_prepare #(.WA(15),.FW(512),.TAGW(32),.N(4),.GW(4),
    .VM_ALWAYS_READY(1),.TOPK(1),.TK_NMAX(2048),.TK_DIG(8),.TK_BALANCED(MUTANT==4?0:1),.TK_STATION(MUTANT==4?0:1),.TK_MUTANT(MUTANT==4?0:MUTANT)) candidate (
    .clk(clk),.rst_n(rst_n),.go(go),.mode(1'b1),.rnd(1'b0),.tag(tag),
    .src(src),.n(n),.dst(dst),.topk(1'b1),.ibase(ibase),.tk_k(tk_k),.tk_stride(stride),
    .busy(cand_busy),.fault(cand_fault),.words_out(),.words_in(),.vm_re(cand_re),.vm_raddr(cand_ra),.vm_rq(cand_rq),
    .vm_we(),.vm_waddr(),.vm_wdata(),.vm_ready4(1'b1),.vm_we4(cand_we),.vm_waddr4(cand_wa),.vm_wdata4(cand_wd),
    .e_valid(cand_ev),.e_ready(1'b1),.e_data(cand_ed),.e_last(cand_el),.e_mode(cand_em),.e_tag(cand_et),
    .o_valid(o_valid),.o_ready(cand_ready),.o_data(o_data),.o_last(o_last),.o_rank(o_rank),.o_err(o_err),.engine_fault(engine_fault));

  function automatic [511:0] local_operand(input [14:0] addr);
    if(addr<n) local_operand=operands[addr][511:0];
    else if(addr>=4096 && addr<4096+n) local_operand=operands[operand_half+addr-4096][511:0];
    else local_operand=0;
  endfunction
  // Real one-edge VM read contract. Root returns are immutable operand inputs.
  always @(posedge clk) begin
    if(ref_re) ref_rq<=local_operand(ref_ra);
    if(cand_re) cand_rq<=local_operand(cand_ra);
  end

  task automatic value_diff(input string kind,input integer index,input [511:0] wanted,input [511:0] got);
    if(MUTANT>=1 && MUTANT<=3) begin
      $display("MUTANT_DIFF mode=%0d case=%0d kind=%s index=%0d expected=%h actual=%h",MUTANT,active_case,kind,index,wanted,got);$finish;
    end
    $display("VALUE_DIFF case=%0d kind=%s index=%0d expected=%h actual=%h",active_case,kind,index,wanted,got);
    $fatal(1,"FULL_VALUE_DIFF");
  endtask
  task automatic count_diff(input string kind,input integer wanted,input integer got);
    if(MUTANT>=1 && MUTANT<=3) begin
      $display("MUTANT_DIFF mode=%0d case=%0d kind=%s index=0 expected=%0d actual=%0d",MUTANT,active_case,kind,wanted,got);$finish;
    end
    $display("COUNT_DIFF case=%0d kind=%s expected=%0d actual=%0d",active_case,kind,wanted,got);
    $fatal(1,"FULL_COUNT_DIFF");
  endtask

  // VM captures pre-NBA values at this edge, not subsequent combinational data.
  always @(posedge clk) begin : capture
    integer lane;
    cycle=cycle+1;
    if(!rst_n) begin
      ref_groups=0;cand_groups=0;ref_words=0;cand_words=0;
      ref_retire=-1;cand_retire=-1;ref_seen_busy=0;cand_seen_busy=0;ref_return_groups=0;cand_return_groups=0;fetch_words=0;
    end else if(active) begin
      if(ref_re!==cand_re || (ref_re && ref_ra!==cand_ra)) $fatal(1,"NATIVE_VM_READ_DIFF");
      if(ref_ev!==cand_ev) $fatal(1,"NATIVE_EMIT_VALID_DIFF");
      if(ref_ev) begin
        if(ref_ed!==cand_ed || ref_el!==cand_el || ref_em!==cand_em || ref_et!==cand_et) $fatal(1,"NATIVE_EMIT_PACKET_DIFF");
        if(fetch_words>=2*operand_half) $fatal(1,"NATIVE_EXTRA_INPUT_DIFF");
        if(ref_ed!==operands[fetch_words][511:0] || ref_el!==(fetch_words==2*operand_half-1)) $fatal(1,"NATIVE_OPERAND_ORDER_DIFF");
        fetch_words=fetch_words+1;
      end
      if(ref_ev && (!ref_em || ref_et!==tag)) $fatal(1,"REF_TAG_DIFF");
      if(cand_ev && (!cand_em || cand_et!==tag)) $fatal(1,"CAND_TAG_DIFF");
      if(ref_we!=0) begin
        if(ref_groups>=512) $fatal(1,"REF_GROUP_BOUND_DIFF");
        ref_saved_we[ref_groups]=ref_we;ref_saved_wa[ref_groups]=ref_wa;
        ref_saved_wd[ref_groups]=ref_wd;ref_saved_cycle[ref_groups]=cycle;
        for(lane=0;lane<4;lane=lane+1) if(ref_we[lane]) begin
          if(ref_words>=expected_words) $fatal(1,"REF_EXTRA_WORD_DIFF");
          if(ref_wa[15*lane+:15]!==15'(8192+ref_words)) $fatal(1,"REF_ADDR_DIFF");
          if(ref_wd[512*lane+:512]!==assertions[ref_words]) $fatal(1,"REF_VALUE_DIFF");
          ref_words=ref_words+1;
        end
        ref_groups=ref_groups+1;
      end
      if(cand_we!=0) begin
        for(lane=0;lane<4;lane=lane+1) if(cand_we[lane]) begin
          if(cand_words>=expected_words) $fatal(1,"CAND_EXTRA_WORD_DIFF");
          if(cand_wa[15*lane+:15]!==15'(8192+cand_words)) $fatal(1,"CAND_ADDR_DIFF");
          if(cand_wd[512*lane+:512]!==assertions[cand_words]) value_diff("CAND_VALUE_DIFF",cand_words,assertions[cand_words],cand_wd[512*lane+:512]);
          cand_words=cand_words+1;
        end
        if(cand_groups>=ref_groups) $fatal(1,"CAND_ORDER_DIFF");
        if(cand_we!==ref_saved_we[cand_groups] || cand_wa!==ref_saved_wa[cand_groups] ||
           cand_wd!==ref_saved_wd[cand_groups]) $fatal(1,"CAND_FORMED_PACKET_DIFF");
        if(cycle-ref_saved_cycle[cand_groups]!=(MUTANT==4?0:368)) $fatal(1,"CAND_EVENT_CALIBRATION_DIFF");
        cand_groups=cand_groups+1;
      end
      if(reference.tk_ov) begin
        if(ref_return_groups>=512) $fatal(1,"REF_RETURN_BOUND_DIFF");
        ref_return_nw[ref_return_groups]=reference.tk_nw;
        ref_return_last[ref_return_groups]=reference.tk_ol;
        ref_return_data[ref_return_groups]=reference.tk_od;
        ref_return_cycle[ref_return_groups]=cycle;
        if(reference.tk_nw==0 || reference.tk_nw>4) $fatal(1,"REF_PUBLIC_NW_DIFF");
        if(reference.tk_ol!==(4*(ref_return_groups+1)>=expected_words)) $fatal(1,"REF_PUBLIC_LAST_DIFF");
        ref_return_groups=ref_return_groups+1;
      end
      if(candidate.tk_ov) begin
        // Direct independent assertions also catch an early corrupt return,
        // before reference ordinal/time checks could obscure the actual value.
        for(lane=0;lane<4;lane=lane+1) if(lane<candidate.tk_nw) begin
          if(4*cand_return_groups+lane>=expected_words) count_diff("CAND_RETURN_EXTRA_WORD",expected_words,4*cand_return_groups+lane+1);
          if(candidate.tk_od[512*lane+:512]!==assertions[4*cand_return_groups+lane])
            value_diff("CAND_VALUE_DIFF",4*cand_return_groups+lane,assertions[4*cand_return_groups+lane],candidate.tk_od[512*lane+:512]);
        end
        if(cand_return_groups>=ref_return_groups) $fatal(1,"CAND_PUBLIC_ORDER_DIFF");
        if(candidate.tk_nw!==ref_return_nw[cand_return_groups] || candidate.tk_ol!==ref_return_last[cand_return_groups] ||
           candidate.tk_od!==ref_return_data[cand_return_groups]) $fatal(1,"CAND_PUBLIC_PACKET_DIFF");
        if(cycle-ref_return_cycle[cand_return_groups]!=(MUTANT==4?0:340)) $fatal(1,"CAND_PUBLIC_EVENT_DIFF");
        cand_return_groups=cand_return_groups+1;
      end
      #1;
      if(ref_fault || cand_fault) $fatal(1,"LEGAL_INPUT_FAULT_DIFF");
      if(ref_busy) ref_seen_busy=1;
      if(cand_busy) cand_seen_busy=1;
      if(ref_seen_busy && !ref_busy && ref_retire<0) begin
        ref_retire=cycle;
        if(!abort_mode && ref_words!=expected_words) $fatal(1,"REF_RETIRE_COUNT_DIFF");
      end
      if(cand_seen_busy && !cand_busy && cand_retire<0) begin
        cand_retire=cycle;
        if(!abort_mode && cand_words!=expected_words) count_diff("CAND_RETIRE_COUNT_DIFF",expected_words,cand_words);
        if(!abort_mode && cand_groups!=ref_groups) $fatal(1,"CAND_RETIRE_GROUP_DIFF");
        if(!abort_mode && cand_retire-ref_retire!=(MUTANT==4?0:368)) $fatal(1,"RETIRE_CALIBRATION_DIFF");
      end
    end else if(ref_we!=0 || cand_we!=0) $fatal(1,"STALE_WRITE_DIFF");
  end

  task automatic tick;
    @(negedge clk);#1;
  endtask
  task automatic reset_fixture;
    tick();rst_n=0;go=0;o_valid=0;o_last=0;o_err=0;engine_fault=0;o_rank=0;active=0;
    src=0;dst=8192;ibase=4096;
    #1;
    if(ref_we!==0 || cand_we!==0 || ref_busy!==0 || cand_busy!==0) $fatal(1,"ASYNC_RESET_DIFF");
    repeat(4) tick();rst_n=1;
    repeat(2) tick();
  endtask

  task automatic observe_reset_drain;
    // Cover the modeled368-edge transport/service increment after each abort.
    // This is a stale-event observation window, not a simulation wall limit.
    repeat(370) begin
      tick();
      if(ref_busy || cand_busy || ref_we!=0 || cand_we!=0 || ref_ev || cand_ev)
        $fatal(1,"RESET_REAPPEAR_DIFF");
    end
  endtask

  task automatic run_case(input integer index,input integer runtime_n,input integer wanted,input integer abort_phase);
    integer beat;
    reset_fixture();
    $readmemh($sformatf("%s/inputs/case_%02d.mem",image_root,index),operands,0,2*(runtime_n/16)-1);
    $readmemh($sformatf("%s/expected/case_%02d.mem",image_root,index),assertions,0,(wanted+15)/16-1);
    n=15'(runtime_n/16);tk_k=16'(wanted);stride=32'(2*runtime_n);tag=32'(index+1);
    active_case=index;
    expected_words=(wanted+15)/16;operand_half=runtime_n/16;
    active=1;abort_mode=(abort_phase!=0);go=1;tick();go=0;
    // Native nh/wpr must settle before the first returned gather beat.
    repeat(3) tick();
    for(beat=0;beat<2*operand_half;beat=beat+1) begin
      if(!ref_ready || !cand_ready) $fatal(1,"NATIVE_ACCEPTANCE_DIFF");
      o_valid=1;o_data=operands[beat];o_last=(beat==2*operand_half-1);tick();
      if(abort_phase==1 && beat==7) begin
        reset_fixture();observe_reset_drain();abort_cases=abort_cases+1;$display("ABORT_PASS phase=1 case=%0d",index);return;
      end
    end
    o_valid=0;o_last=0;
    if(abort_phase==2) begin
      repeat(30) tick();reset_fixture();observe_reset_drain();abort_cases=abort_cases+1;$display("ABORT_PASS phase=2 case=%0d",index);return;
    end
    if(abort_phase==3) begin
      while(ref_words==0) tick();reset_fixture();observe_reset_drain();abort_cases=abort_cases+1;$display("ABORT_PASS phase=3 case=%0d",index);return;
    end
    if(abort_phase==4) begin
      while(cand_words==0) tick();reset_fixture();observe_reset_drain();abort_cases=abort_cases+1;$display("ABORT_PASS phase=4 case=%0d",index);return;
    end
    while(cand_retire<0) tick();
    if(ref_retire<0 || ref_words!=expected_words || cand_words!=expected_words) $fatal(1,"FINAL_COUNT_DIFF");
    if(fetch_words!=2*operand_half) $fatal(1,"NATIVE_INPUT_COUNT_DIFF");
    $display("CASE_PASS case=%0d n=%0d k=%0d ref_words=%0d cand_words=%0d delta=%0d fetch_words=%0d",index,runtime_n,wanted,ref_words,cand_words,cand_retire-ref_retire,fetch_words);
    normal_cases=normal_cases+1;active=0;tick();
  endtask

  task automatic check_sticky_fault(input integer kind,input integer wanted_busy);
    repeat(204) tick(); //99 input +99 return +6 settling/observation edges.
    if(ref_fault!==1 || cand_fault!==1 || ref_busy!==wanted_busy[0] || cand_busy!==wanted_busy[0])
      $fatal(1,"FAULT_FLAG_OR_OWNERSHIP_DIFF");
    repeat(8) begin
      tick();
      if(!ref_fault || !cand_fault || ref_we!=0 || cand_we!=0) $fatal(1,"FAULT_STICKY_DIFF");
    end
    fault_cases=fault_cases+1;$display("FAULT_PASS kind=%0d busy=%0d",kind,wanted_busy);
    reset_fixture();observe_reset_drain();
  endtask
  task automatic bad_command_case(input integer kind);
    reset_fixture();n=32;tk_k=1;stride=1024;operand_half=32;tag=100+kind;
    case(kind)
      0:tk_k=0;
      1:n=0;
      2:n=129;
      3:tk_k=2049;
      4:dst=8193;
      5:ibase=8192;
      6:src=32760;
      7:begin dst=32764;tk_k=1024;end
      default:$fatal(1,"UNKNOWN_BAD_COMMAND_CASE");
    endcase
    go=1;tick();go=0;
    check_sticky_fault(kind,0);
  endtask
  task automatic external_fault_case(input integer kind);
    reset_fixture();n=32;tk_k=1;stride=1024;operand_half=32;tag=100+kind;
    if(kind==8) o_err=1;
    else if(kind==9) engine_fault=1;
    else begin go=1;tick();go=0;tick();end
    if(kind==10) begin go=1;tick();go=0;end
    if(kind==11) begin o_rank=1;o_valid=1;o_data=0;tick();o_valid=0;o_rank=0;end
    tick();o_err=0;engine_fault=0;
    check_sticky_fault(kind,kind>=10?1:0);
  endtask
  task automatic core_fault_case(input integer kind);
    integer beat,half;
    reset_fixture();
    if(kind==14) begin
      $readmemh($sformatf("%s/inputs/case_05.mem",image_root),operands,0,63);n=31;
    end else begin
      $readmemh($sformatf("%s/fault_inputs/kind_%0d.mem",image_root,kind),operands,0,63);n=32;
    end
    tk_k=1;stride=1024;operand_half=32;tag=100+kind;go=1;tick();go=0;repeat(3) tick();
    half=integer'(n);
    for(beat=0;beat<2*half;beat=beat+1) begin
      if(!ref_ready || !cand_ready) $fatal(1,"FAULT_INPUT_ACCEPTANCE_DIFF");
      o_valid=1;o_data=operands[beat<half?beat:32+beat-half];o_last=(beat==2*half-1);tick();
    end
    o_valid=0;o_last=0;
    check_sticky_fault(kind,1);
  endtask

  initial begin
    if(MUTANT<0 || MUTANT>4) $fatal(1,"UNKNOWN_PROFILE");
    if(!$value$plusargs("IMAGE_ROOT=%s",image_root)) $fatal(1,"IMMUTABLE_IMAGE_ROOT_REQUIRED");
    if(MUTANT>=1 && MUTANT<=3) begin
      if(MUTANT<1 || MUTANT>3) $fatal(1,"UNKNOWN_MUTANT_MODE");
      run_case(0,512,1,0);
      $fatal(1,"MUTANT_NO_DIFFERENCE");
    end else begin
      `include "case_calls.svh"
      for(integer kind=0;kind<8;kind=kind+1) bad_command_case(kind);
      for(integer kind=8;kind<12;kind=kind+1) external_fault_case(kind);
      for(integer kind=12;kind<15;kind=kind+1) core_fault_case(kind);
      if(normal_cases!=37 || abort_cases!=4 || fault_cases!=15) $fatal(1,"COMPLETION_COUNT_DIFF");
      $display("FULL_SELECTOR_DMA_PASS profile=%0d cases=37 aborts=4 faults=15 functional_only=1",MUTANT);$finish;
    end
  end
endmodule
