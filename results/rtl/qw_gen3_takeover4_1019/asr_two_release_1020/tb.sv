`timescale 1ns/1ps
module tb #(parameter integer MUT=0);
 reg ck=0,other_ck=0,run_ck=1,raw_n=0,offered=1;
 always #5 if(run_ck) ck=~ck; else ck=0;
 initial begin #1; forever begin other_ck=1; #3.5;other_ck=0;#3.5;end end
 wire s0,s1;
 wire c0=(MUT==5)?other_ck:ck;
 wire c1=(MUT==2)?other_ck:ck;
 wire clear0=(MUT==7)?1'b1:raw_n;
 wire preset0=(MUT==7)?raw_n:1'b1;
 wire clear1=(MUT==4)?1'b1:((MUT==1)?raw_n:s0);
 wire preset1=(MUT==4)?s0:1'b1;
 // Positive logical release is QN. D=0 means release-to-one; SETN is active-low clear.
 DFFASRHQNx1_ASAP7_75t_R release0 (.CLK(c0),.D(MUT==6),.RESETN(preset0),.SETN(clear0),.QN(s0));
 DFFASRHQNx1_ASAP7_75t_R release1 (.CLK(c1),.D(MUT==3),.RESETN(preset1),.SETN(clear1),.QN(s1));
 reg ref0=0,ref1=0,ref_valid=0;
 always @(posedge ck or negedge raw_n)if(!raw_n)ref0<=0;else ref0<=1;
 always @(posedge ck or negedge ref0)if(!ref0)ref1<=0;else ref1<=1;
 always @(posedge ck or negedge ref1)if(!ref1)ref_valid<=0;else ref_valid<=offered;
 wire native_valid;
 DFFASRHQNx1_ASAP7_75t_R admitted_valid (.CLK(ck),.D(~offered),.RESETN(1'b1),.SETN(s1),.QN(native_valid));
 reg[3:0]data_in=4'ha,reference_payload=0;wire[3:0]native_payload;
 always @(negedge ck)data_in<=data_in+3;
 always @(posedge ck)reference_payload<=data_in;
 genvar b;generate for(b=0;b<4;b=b+1)begin:payload
  DFFHQNx1_ASAP7_75t_R d(.CLK(ck),.D(~data_in[b]),.QN(native_payload[b]));
 end endgenerate
 wire native_o,native_fault;
 ot_qfd_land8 #(.W(1),.ICG(0)) real_pattern(.ck_s(ck),.en(raw_n),.i(1'b1),.ck(ck),.rs(raw_n),.k(4'd2),.o(native_o),.fault(native_fault));
 integer edges=-1,R0=-999,checks=0,errors=0,asserts=0,firstvalids=0,warmchecks=0;reg previous_valid=0,first_seen=0;
 task check(input[255:0] why);
 begin
  checks=checks+1;
  if(s0!==ref0||s1!==ref1)begin errors=errors+1;if(errors<5)$display("CHAIN_NATIVE_MISMATCH MUT=%0d why=%s t=%0t edges=%0d s=%b%b ref=%b%b",MUT,why,$time,edges,s1,s0,ref1,ref0);end
  if(native_valid!==ref_valid)begin errors=errors+1;if(errors<5)$display("FIRST_VALID_MISMATCH MUT=%0d why=%s t=%0t actual=%b ref=%b",MUT,why,$time,native_valid,ref_valid);end
  if(native_valid===1'b1&&native_payload!==reference_payload)begin errors=errors+1;$display("INFLIGHT_PAYLOAD_MISMATCH");end
  if(real_pattern.en_s0!==ref0||real_pattern.en_icg!==ref1||real_pattern.rs0!==ref0||real_pattern.rs1!==ref1)begin errors=errors+1;$display("REAL_LAND8_TWO_RELEASE_MISMATCH");end
 end endtask
 always @(posedge ck)begin
  edges=edges+1;#0.002;check("own_rise");
  if(!first_seen&&native_valid===1'b1)begin first_seen=1;firstvalids=firstvalids+1;$display("FIRST_VALID MUT=%0d edge=%0d R0=%0d delta=%0d tag=%h",MUT,edges,R0,edges-R0,native_payload);if(edges!=R0+3)begin errors=errors+1;$display("FIRST_VALID_EDGE_FAIL");end end
  previous_valid=native_valid;
  if(raw_n&&R0!=-999)begin
   warmchecks=warmchecks+1;
   if(native_o!==((edges>=R0+5)?1'b1:1'b0)||native_fault)begin errors=errors+1;$display("REAL_LAND8_FIRST_WORD_FAIL edge=%0d R0=%0d o=%b fault=%b",edges,R0,native_o,native_fault);end
  end
 end
 always @(posedge other_ck)begin #0.002;check("wrong_clock_edge");end
 always @(posedge raw_n)begin R0=edges;#0.002;check("offphase_release");end
 always @(negedge raw_n)begin
  asserts=asserts+1;R0=-999;previous_valid=0;first_seen=0;#0.002;check("async_assert");
  if(s0!==0||s1!==0||native_valid!==0||real_pattern.warm!==0||real_pattern.g_region[0].u_region.warm_q!==0)begin errors=errors+1;$display("ASYNC_CLEAR_FAIL MUT=%0d t=%0t",MUT,$time);end
 end
 initial begin
  #2;check("cold_clear");#10;raw_n=1;#70;
  // Short assertion wholly between own rising edges; in-flight words must lose validity immediately.
  raw_n=0;#0.05;raw_n=1;#70;
  // Assert while own clock is high, proving phase-independent asynchronous clear.
  @(posedge ck);#2;raw_n=0;#0.05;raw_n=1;#70;
  // Held reset; deassert with own clock stopped, while the foreign clock keeps running.
  raw_n=0;#20;run_ck=0;#30;raw_n=1;#30;
  if(s0!==0||s1!==0||native_valid!==0)begin errors=errors+1;$display("HELD_RELEASE_LEAK MUT=%0d",MUT);end
  run_ck=1;#100;offered=0;#30;offered=1;#30;
  $display("TWO_RELEASE_SUMMARY MUT=%0d checks=%0d asserts=%0d firstvalids=%0d warmchecks=%0d errors=%0d",MUT,checks,asserts,firstvalids,warmchecks,errors);
  if(errors!=0||checks<100||firstvalids<4||warmchecks<20)$fatal(1,"TWO_RELEASE_CHAIN_FAIL");
  $display("TWO_RELEASE_CHAIN_PASS");$finish;
 end
endmodule
