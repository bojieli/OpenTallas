`timescale 1ns/1ps
// Q-B2r 10-16: exact bench for qfd_b2_word_status (six-half native word/result status checker).
// Reference: inputs are registered once (vq/fq/rq), fault is sticky from the first edge after reset release
// (rs_q) and rises on the edge after any registered fault bit or any registered valid / result-valid mismatch.
// Pure checker: the bench drives aligned six-half valid/result streams (random burst shapes, both polarities) and
// asserts fault==ref every edge; then injects each fault class at a random half / edge and checks the exact rise edge.
// +MUT=1 (negative control): half 3 word valid arrives one edge late while the REFERENCE assumes aligned arrivals
// (the misalignment the status checker exists to catch) -> DUT fault rises, bench must FAIL.
// +MUT=2: half 5 result valid one edge late, same expectation.
module tb_b2_word_status;
 reg ck=0,rst_n=0; reg [5:0] word_v=0,word_fault=0,result_v=0; wire fault;
 qfd_b2_word_status dut(.ck(ck),.rst_n(rst_n),.word_v(word_v),.word_fault(word_fault),.result_v(result_v),.fault(fault));
 always #0.4166 ck=~ck;
 integer mut=0,cyc=0,checks=0,errors=0,rises=0,seed=7,phase;
 reg ref_rs=0,ref_fault=0; reg [5:0] rv=0,rf=0,rr=0;
 reg [5:0] stim_v,stim_r;
 reg [5:0] ref_v_in, ref_r_in;
 // reference model, same edge semantics as the source contract above
 always @(posedge ck or negedge rst_n) if(!rst_n) ref_rs<=0; else ref_rs<=1;
 always @(posedge ck) begin rv<=ref_v_in; rf<=word_fault; rr<=ref_r_in; end
 always @(posedge ck or negedge ref_rs) if(!ref_rs) ref_fault<=0;
  else ref_fault<=ref_fault|(|rf)|(|(rv^{6{rv[0]}}))|(|(rr^{6{rr[0]}}));
 // ref_v_in/ref_r_in: what the reference believes was sent (aligned); the DUT sees the (possibly mutated) wires
 task step; begin @(negedge ck); cyc=cyc+1; end endtask
 task check; begin
  @(posedge ck); #0.05;
  if(rst_n) begin checks=checks+1; if(fault!==ref_fault) begin errors=errors+1;
   if(errors<6) $display("MISMATCH cyc%0d fault=%b ref=%b",cyc,fault,ref_fault); end end
 end endtask
 reg v_prev3=0, r_prev5=0;
 task drive(input [5:0] v, input [5:0] r, input [5:0] f); begin
  ref_v_in=v; ref_r_in=r; word_fault=f;
  word_v=v; result_v=r;
  if(mut==1) begin word_v[3]=v_prev3; end
  if(mut==2) begin result_v[5]=r_prev5; end
  v_prev3=v[3]; r_prev5=r[5];
 end endtask
 integer k,n,inj,h;
 initial begin
  if(!$value$plusargs("MUT=%d",mut)) mut=0;
  ref_v_in=0; ref_r_in=0;
  repeat(3) step; rst_n=1;
  // phase A: aligned random bursts, no faults -> fault must stay 0 and match the reference every edge
  for(n=0;n<4000;n=n+1) begin
   step; stim_v={6{(($random(seed)&32'h7fffffff)%3)!=0}}; stim_r={6{(($random(seed)&32'h7fffffff)%4)==0}};
   drive(stim_v,stim_r,6'd0); fork check; join
  end
  if(fault!==0 && mut==0) begin $display("FAIL aligned stream raised fault"); $finish; end
  // phase B: per-class injection with reset between cases; exact rise edge vs reference
  for(inj=0;inj<36;inj=inj+1) begin
   step; rst_n=0; drive(0,0,0); step; step; rst_n=1;
   for(k=0;k<20;k=k+1) begin step; drive({6{k[0]}},{6{k[1]}},0); fork check; join end
   h=inj%6; phase=inj/6;
   step;
   case(phase%3)
    0: drive({6{1'b1}},0,6'd1<<h);                       // native word fault on half h
    1: drive(6'b111111 ^ (6'd1<<h),0,0);                  // one half's word valid missing
    2: drive(0,6'b000000 | (6'd1<<h),0);                  // one half's result valid alone
   endcase
   fork check; join
   for(k=0;k<4;k=k+1) begin step; drive(0,0,0); fork check; join end
   if(ref_fault!==1) begin $display("FAIL reference did not latch case %0d",inj); $finish; end
   if(fault===1) rises=rises+1;
  end
  if(errors==0 && rises==36 && checks>4000)
   $display("PASS b2 word status exact checks=%0d rises=%0d",checks,rises);
  else $display("FAIL b2 word status errors=%0d rises=%0d checks=%0d mut=%0d",errors,rises,checks,mut);
  $finish;
 end
endmodule
