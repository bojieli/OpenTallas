`timescale 1ns/1ps
module tb_qfd_su_static_copy;
 parameter DATA_MUT=0,LATENCY_MUT=0,CONFLICT=0;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg[55:0]cp=0;reg[2366:0]su_va=0;
 wire[2366:0]va;wire[2136:0]xsw;wire active,done,fault;
 reg[2047:0]data_pipe[0:14];wire[6143:0]vq={4096'd0,data_pipe[14]};
 qfd_su_static_copy #(.DATA_MUT(DATA_MUT),.LATENCY_MUT(LATENCY_MUT))dut(
 .ck(ck),.rst_n(rst_n),.cp(cp),.su_va(su_va),.vq(vq),.va(va),.xsw(xsw),.cp_active(active),.cp_done(done),.fault(fault));
 function[31:0]word(input integer a);
 begin
 // Includes signed zeros, infinities, signaling/quiet NaNs, subnormals and
 // arbitrary raw words. Replay is transport, not floating point arithmetic.
 case(a%8)
 0:word=32'h80000000;1:word=32'h7f800000;2:word=32'h7fa12345;
 3:word=32'hffc54321;4:word=32'h00000001;5:word=32'hffffffff;
 default:word=32'h9e3779b9*a;
 endcase
 end endfunction
 integer cycle=0,reads=0,writes=0,errors=0,last_read=-1,last_write=-1;
 integer i,lane,frame=0,first_read=-1,first_write=-1,start_cycle;
 reg[2047:0]d;
 always @(posedge ck)begin
  cycle=cycle+1;
  for(i=14;i>0;i=i-1)data_pipe[i]<=data_pipe[i-1];
  for(lane=0;lane<64;lane=lane+1)data_pipe[0][32*lane+:32]<=word(va[23:0]+lane);
  if(rst_n)begin
   if(va[48])begin
    if(reads==0)first_read=cycle;
    if(last_read>=0&&cycle!=last_read+1)errors=errors+1;
    if(va[49]!=1 || va[47:24]!=va[23:0]+1 || va[23:0]!=8192+64*reads)errors=errors+1;
    reads=reads+1;last_read=cycle;
   end
   if(|va[2309:2246])begin
    if(writes==0)first_write=cycle;
    if(last_write>=0&&cycle!=last_write+1)errors=errors+1;
    if(va[2309:2246]!==64'hffffffffffffffff || va[2221:2198]!=8192+64*writes || va[2245:2222]!=8193+64*writes)errors=errors+1;
    for(lane=0;lane<64;lane=lane+1)if(va[150+32*lane+:32]!==word(8192+64*writes+lane))begin
     if(errors<3)$display("data mismatch frame%0d write%0d lane%0d got%h expected%h",frame,writes,lane,va[150+32*lane+:32],word(8192+64*writes+lane));errors=errors+1;
    end
    if(xsw!=={va[2197:150],va[2309:2246],va[2221:2198],1'b1})errors=errors+1;
    writes=writes+1;last_write=cycle;
   end
  end
 end
 initial begin
  repeat(4)@(negedge ck);rst_n=1;
  // Inactive SU metadata may retain previous values and must not fault.
  su_va[23:0]=12345;
  for(frame=0;frame<3;frame=frame+1)begin
   reads=0;writes=0;last_read=-1;last_write=-1;
   @(negedge ck);start_cycle=cycle;cp={7'd64,24'd8192,24'd8192,1'b1};
   @(negedge ck);cp=0;
   if(CONFLICT!=0)begin repeat(5)@(negedge ck);su_va[48]=1;@(negedge ck);su_va[48]=0;end
   wait(done);@(negedge ck);
   if(reads!=64||writes!=64||first_write-first_read!=16)begin $display("counts/timing %0d %0d latency%0d",reads,writes,first_write-first_read);errors=errors+1;end
   $display("REPLAY frame%0d reads%0d writes%0d response_plus_copy%0d complete_after_start%0d",frame,reads,writes,first_write-first_read,cycle-start_cycle);
   repeat(4)@(negedge ck);
  end
  if(fault!=(CONFLICT!=0))errors=errors+1;
  if(errors)$fatal(1,"FAIL exact static replay errors%0d",errors);
  $display("PASS raw4096words x3 exact replay no FP computation, fault%0d",fault);$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
