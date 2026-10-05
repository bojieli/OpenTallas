`timescale 1ps/1ps
// FUNCTIONAL FIXTURE ONLY.833ps is a simulation tick, never SS/FF credit.
// Candidate module is an explicit unmet package dependency; no stub permitted.
module bench_dsrom_full_selector_dma_prepare;
  reg clk=0,rst_n=0,go=0,o_valid=0,o_last=0;
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
  integer normal_cases=0,abort_cases=0;
  reg active=0,ref_seen_busy=0,cand_seen_busy=0,abort_mode=0;
  string image_root;
  // High416ps/low417ps; NBA and async checks settle1ps before comparison.
  initial forever begin #416 clk=1; #417 clk=0; end

  // Exact full target shape on both sides, including native4-bank DMA.
  ot_w15_coll_dma #(.WA(15),.FW(512),.TAGW(32),.N(4),.GW(4),
    .VM_ALWAYS_READY(1),.TOPK(1),.TK_NMAX(2048),.TK_DIG(8)) reference (
    .clk(clk),.rst_n(rst_n),.go(go),.mode(1'b1),.rnd(1'b0),.tag(tag),
    .src(15'd0),.n(n),.dst(15'd8192),.topk(1'b1),.ibase(15'd4096),.tk_k(tk_k),.tk_stride(stride),
    .busy(ref_busy),.fault(ref_fault),.words_out(),.words_in(),.vm_re(ref_re),.vm_raddr(ref_ra),.vm_rq(ref_rq),
    .vm_we(),.vm_waddr(),.vm_wdata(),.vm_ready4(1'b1),.vm_we4(ref_we),.vm_waddr4(ref_wa),.vm_wdata4(ref_wd),
    .e_valid(ref_ev),.e_ready(1'b1),.e_data(),.e_last(ref_el),.e_mode(ref_em),.e_tag(ref_et),
    .o_valid(o_valid),.o_ready(ref_ready),.o_data(o_data),.o_last(o_last),.o_rank(2'd0),.o_err(1'b0),.engine_fault(1'b0));

  ot_w15_coll_dma_balanced_station_prepare #(.WA(15),.FW(512),.TAGW(32),.N(4),.GW(4),
    .VM_ALWAYS_READY(1),.TOPK(1),.TK_NMAX(2048),.TK_DIG(8),.TK_BALANCED(1),.TK_STATION(1)) candidate (
    .clk(clk),.rst_n(rst_n),.go(go),.mode(1'b1),.rnd(1'b0),.tag(tag),
    .src(15'd0),.n(n),.dst(15'd8192),.topk(1'b1),.ibase(15'd4096),.tk_k(tk_k),.tk_stride(stride),
    .busy(cand_busy),.fault(cand_fault),.words_out(),.words_in(),.vm_re(cand_re),.vm_raddr(cand_ra),.vm_rq(cand_rq),
    .vm_we(),.vm_waddr(),.vm_wdata(),.vm_ready4(1'b1),.vm_we4(cand_we),.vm_waddr4(cand_wa),.vm_wdata4(cand_wd),
    .e_valid(cand_ev),.e_ready(1'b1),.e_data(),.e_last(cand_el),.e_mode(cand_em),.e_tag(cand_et),
    .o_valid(o_valid),.o_ready(cand_ready),.o_data(o_data),.o_last(o_last),.o_rank(2'd0),.o_err(1'b0),.engine_fault(1'b0));

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

  // VM captures pre-NBA values at this edge, not subsequent combinational data.
  always @(posedge clk) begin : capture
    integer lane;
    cycle=cycle+1;
    if(!rst_n) begin
      ref_groups=0;cand_groups=0;ref_words=0;cand_words=0;
      ref_retire=-1;cand_retire=-1;ref_seen_busy=0;cand_seen_busy=0;
    end else if(active) begin
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
        if(cand_groups>=ref_groups) $fatal(1,"CAND_ORDER_DIFF");
        if(cand_we!==ref_saved_we[cand_groups] || cand_wa!==ref_saved_wa[cand_groups] ||
           cand_wd!==ref_saved_wd[cand_groups]) $fatal(1,"CAND_FORMED_PACKET_DIFF");
        if(cycle-ref_saved_cycle[cand_groups]!=368) $fatal(1,"CAND_EVENT_CALIBRATION_DIFF");
        for(lane=0;lane<4;lane=lane+1) if(cand_we[lane]) begin
          if(cand_words>=expected_words) $fatal(1,"CAND_EXTRA_WORD_DIFF");
          if(cand_wa[15*lane+:15]!==15'(8192+cand_words)) $fatal(1,"CAND_ADDR_DIFF");
          if(cand_wd[512*lane+:512]!==assertions[cand_words]) $fatal(1,"CAND_VALUE_DIFF");
          cand_words=cand_words+1;
        end
        cand_groups=cand_groups+1;
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
        if(!abort_mode && (cand_words!=expected_words || cand_groups!=ref_groups)) $fatal(1,"CAND_RETIRE_COUNT_DIFF");
        if(!abort_mode && cand_retire-ref_retire!=368) $fatal(1,"RETIRE_CALIBRATION_DIFF");
      end
    end else if(ref_we!=0 || cand_we!=0) $fatal(1,"STALE_WRITE_DIFF");
  end

  task automatic tick;
    @(negedge clk);#1;
  endtask
  task automatic reset_fixture;
    tick();rst_n=0;go=0;o_valid=0;o_last=0;active=0;
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
    $display("CASE_PASS case=%0d n=%0d k=%0d ref_words=%0d cand_words=%0d delta=%0d",index,runtime_n,wanted,ref_words,cand_words,cand_retire-ref_retire);
    normal_cases=normal_cases+1;active=0;tick();
  endtask

  initial begin
    if(!$value$plusargs("IMAGE_ROOT=%s",image_root)) $fatal(1,"IMMUTABLE_IMAGE_ROOT_REQUIRED");
    // Generated calls include37 fullgeometry legal cases and4 reset-aborts.
    `include "case_calls.svh"
    if(normal_cases!=37 || abort_cases!=4) $fatal(1,"COMPLETION_COUNT_DIFF");
    $display("FULL_SELECTOR_DMA_PASS cases=37 aborts=4 functional_only=1");$finish;
  end
endmodule
