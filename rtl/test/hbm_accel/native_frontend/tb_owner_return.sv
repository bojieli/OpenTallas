`timescale 1ns/1ps
module tb_owner_return;
 parameter integer MUT=0,J=2;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0,av=0,rv=0,stop=0;reg[16:0] at=0,rt=0;reg[46:0] am=0;reg[3:0] beat=0;
 reg[255:0] data=0;reg[1:0] reserved=3;wire ov,ot,fault;wire[284:0] packet;wire[31:0]live;
 ot_hbm_owner_return_native #(.J(J),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.alloc_v(av),.alloc_tag(at),.alloc_metadata(am),
  .return_v(rv),.return_tag(rt),.return_beat(beat),.return_data(data),.stop(stop),.target_reserved(reserved),
  .pair_v(ov),.pair_target(ot),.pair_packet(packet),.fault(fault),.live(live));
 reg[46:0] refmeta[0:31];reg[284:0] expected[0:7];reg[7:0] ev=0;reg[10:0] ordinal;
 integer checks=0,phase,g,gen,j,b,kind,idx;reg verifying=1;
 task automatic fail(input string s);begin $display("FAIL owner_return %s phase=%0d gen=%0d kind=%0d",s,phase,gen,kind);$fatal(1);end endtask
 task automatic tick;begin
  @(posedge clk);#0.01;
  if(verifying)begin
   if(ov!==ev[7])fail("fixed eight-edge publication age");
   if(ov)begin if(packet!==expected[7]||ot!==expected[7][276])fail("ordinal/bank/epoch/data/target identity");checks=checks+1;end
   if(fault)fail("unexpected source fault");
  end
  for(integer q=7;q>0;q=q-1)expected[q]=expected[q-1];
  if(av)refmeta[at&31]=am;
  idx=rt&31;ordinal=refmeta[idx][13:3]+(refmeta[idx][16]?((beat[1:0]^refmeta[idx][15:14])*4):0);
  expected[0]={ordinal,refmeta[idx][18:17],refmeta[idx][34:19],data};ev={ev[6:0],rv};
 end endtask
 task automatic idle;begin @(negedge clk);av=0;rv=0;tick();end endtask
 task automatic reset_all;begin
  @(negedge clk);rst_n=0;av=0;rv=0;stop=0;reserved=3;ev=0;verifying=1;
  #0.02;if(ov||fault||live)fail("occupied asynchronous reset");
  repeat(3)@(posedge clk);@(negedge clk);rst_n=1;repeat(3)@(posedge clk);
 end endtask
 task automatic allocate(input integer slot,input integer generation);begin
  @(negedge clk);av=1;rv=0;at=17'(generation*32+slot);
  am={12'(generation),16'(generation*71+slot),2'(slot),1'b1,2'(phase),11'(slot*4+J),3'd4};tick();
 end endtask
 task automatic respond(input integer slot,input integer generation,input integer bn);begin
  @(negedge clk);av=0;rv=1;rt=17'(generation*32+slot);beat=4'(bn^(phase&3));
  data={32'(slot),32'(generation),32'(bn),32'(phase),32'hcafef00d,32'h12345678,32'(slot*37+bn),32'(generation^bn)};tick();
 end endtask
 initial begin
  for(phase=0;phase<8;phase=phase+1)begin
   reset_all();
   for(g=0;g<4;g=g+1)begin
    gen=(g==2)?4095:(g==3)?0:g;
    for(j=0;j<32;j=j+1)allocate(j,gen);
    for(j=0;j<32;j=j+1)for(b=0;b<4;b=b+1)respond(j,gen,b);
    repeat(10)idle();if(live)fail("finite tag retirement");
   end
   // Earliest legal return follows allocation by just one edge.
   allocate(0,3);for(b=0;b<4;b=b+1)respond(0,3,b);repeat(10)idle();
   allocate(0,4);respond(0,4,0);@(negedge clk);#(0.02*phase);rst_n=0;#0.01;if(ov||fault||live)fail("occupied cancellation");
  end
  for(kind=0;kind<5;kind=kind+1)begin
   reset_all();allocate(0,1);verifying=0;
   if(kind==2)begin // malformed source metadata generation
    @(negedge clk);av=1;at=1;am={12'd7,16'd1,2'd0,1'b0,2'd0,11'(J),3'd4};tick();
   end
   if(kind==3)begin @(negedge clk);av=1;at=1;am={12'd0,16'd1,2'd0,1'b0,2'd0,11'(J^1),3'd4};tick();end
   if(kind==4)reserved=0;
   if(kind==1)begin respond(0,1,0);idle();end
   respond((kind==3)?1:0,(kind==0)?2:1,0);
   for(b=0;b<12;b=b+1)begin idle();if(ov)fail("malformed payload escaped");end
   if(!fault)fail("missing causal malformed fault");
  end
  $display("PASS owner_return checks=%0d slots32 generations0_1_4095_0 resets8 response_edges8 earliest_alloc_return1",checks);$finish;
 end
endmodule
