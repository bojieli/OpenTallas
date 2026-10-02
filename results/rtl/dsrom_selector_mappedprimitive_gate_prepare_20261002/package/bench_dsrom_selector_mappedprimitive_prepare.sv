`timescale 1ns/1ps
// Functional backend diagnosis only. Official library sources are unchanged.
// This bench is not a smaller selector/transport timing qualification.
module bench_dsrom_selector_mappedprimitive_prepare;
  reg clk=0,rst_n=1,payload_d=0,flag_d=0;
  integer mode=0,steps=0,events=0,checks=0,vector_index=0;
  reg want_payload=0,want_flag=0;
  reg [31:0] inputs[0:31];
  wire p0,p1,pd,pqn,payload,f0,f1,fd,fqn,flag,setn,permit,guarded;
  wire reset_to_cell=(mode==2)?1'b1:rst_n;
  BUFx4_ASAP7_75t_R p_repeat0(.A(payload_d),.Y(p0));
  BUFx4_ASAP7_75t_R p_repeat1(.A(p0),.Y(p1));
  BUFx4_ASAP7_75t_R p_terminal(.A(p1),.Y(pd));
  DFFHQNx1_ASAP7_75t_R p_ff(.D(pd),.CLK(clk),.QN(pqn));
  INVx1_ASAP7_75t_R p_restore(.A(pqn),.Y(payload));
  BUFx4_ASAP7_75t_R f_repeat0(.A(flag_d),.Y(f0));
  BUFx4_ASAP7_75t_R f_repeat1(.A(f0),.Y(f1));
  BUFx4_ASAP7_75t_R f_terminal(.A(f1),.Y(fd));
  TIEHIx1_ASAP7_75t_R f_setn(.H(setn));
  DFFASRHQNx1_ASAP7_75t_R f_ff(.D(fd),.CLK(clk),.RESETN(reset_to_cell),.SETN(setn),.QN(fqn));
  INVx1_ASAP7_75t_R f_restore(.A(fqn),.Y(flag));
  AND2x2_ASAP7_75t_R reset_permitted(.A(rst_n),.B(flag),.Y(permit));
  AND2x2_ASAP7_75t_R control_guard(.A(payload),.B(permit),.Y(guarded));
  wire observed_payload=(mode==1)?pqn:payload;
  wire observed_control=(mode==3)?payload:guarded;

  task automatic check(input string kind,input string phase,input integer index,input bit wanted,input logic actual);
    checks=checks+1;
    if(actual!==wanted) begin
      if(mode>=1 && mode<=3) begin
        $display("PRIMITIVE_DIFF mode=%0d kind=%s phase=%s index=%0d expected=%0d actual=%0d",mode,kind,phase,index,wanted,actual);
        $finish;
        #1;$fatal(1,"PRIMITIVE_FINISH_DID_NOT_STOP");
      end
      $display("PRIMITIVE_FAILURE mode=%0d kind=%s phase=%s index=%0d expected=%0d actual=%0d",mode,kind,phase,index,wanted,actual);
      $fatal(1,"OFFICIAL_MAPPED_PRIMITIVE_FAILURE");
    end
  endtask
  task automatic sample(input string phase,input integer index);
    check("PAYLOAD",phase,index,want_payload,observed_payload);
    check("FLAG",phase,index,want_flag,flag);
    check("CONTROL",phase,index,want_payload & want_flag & rst_n,observed_control);
  endtask
  task automatic step(input bit data_value,input bit flag_value);
    if(clk!==0) $fatal(1,"PRIMITIVE_FIXTURE_CLOCK_PHASE");
    payload_d=data_value;flag_d=flag_value;
    #1; // D/continuous assignments settle before free-clock rising edge.
    #415;clk=1;want_payload=data_value;want_flag=rst_n & flag_value;
    #1;sample("RISE",steps);check("TIE","RISE",steps,1,setn);
    #415;clk=0;
    #1;sample("FALL",steps);
    $display("PRIMITIVE_STEP_PASS mode=%0d index=%0d payload=%0d flag=%0d reset=%0d",mode,steps,want_payload,want_flag,rst_n);
    steps=steps+1;
  endtask
  task automatic reset_event(input bit level);
    if(clk!==0 || rst_n===level) $fatal(1,"PRIMITIVE_FIXTURE_RESET_EVENT");
    // No D or CLK mutation in the reset delta; prior falling checks settled.
    rst_n=level;if(!level)want_flag=0;
    #1;events=events+1;sample("ASYNC",events);
    $display("PRIMITIVE_ASYNC_PASS mode=%0d index=%0d reset=%0d",mode,events,level);
  endtask
  initial begin
    if(!$value$plusargs("MODE=%d",mode)) $fatal(1,"EXPLICIT_PRIMITIVE_MODE_REQUIRED");
    if(mode<0 || mode>3) $fatal(1,"PRIMITIVE_MODE_BOUND");
    $readmemh("inputs.mem",inputs);
    #1;step(0,1); // Establish known flag state before asserting async reset.
    reset_event(0);reset_event(1);
    for(vector_index=0;vector_index<32;vector_index=vector_index+1) begin
      if(inputs[vector_index]!==32'(vector_index%4))$fatal(1,"IMMUTABLE_PRIMITIVE_INPUT_IMAGE");
      if(vector_index==8 || vector_index==24)reset_event(0);
      if(vector_index==12 || vector_index==25)reset_event(1);
      step(inputs[vector_index][0],inputs[vector_index][1]);
    end
    reset_event(0);
    if(mode!=0)$fatal(1,"PRIMITIVE_MUTANT_NO_DIFFERENCE");
    if(steps!=33 || events!=7 || checks!=252)$fatal(1,"PRIMITIVE_COMPLETION_COUNTS");
    $display("PRIMITIVE_PASS mode=0 steps=33 async=7 assertions=252");$finish;
  end
endmodule
