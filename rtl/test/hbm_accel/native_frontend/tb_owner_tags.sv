`timescale 1ns/1ps
module tb_owner_tags;
 parameter integer MUT=0;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0,av=0,rv=0,stop=0;reg[16:0] at=0,rt=0;reg[2:0] len=4;reg[3:0] beat=0;
 wire[31:0] accepted,live;wire ok,fault;
 ot_hbm_owner_tags_native #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.alloc_v(av),.alloc_tag(at),.alloc_len(len),
 .return_v(rv),.return_tag(rt),.return_beat(beat),.stop(stop),.accepted_entry(accepted),.live(live),.response_ok(ok),.fault(fault));
 reg[31:0] vl=0,errors=0,expected=0;reg[11:0] generation[0:31];reg[2:0] lengths[0:31];reg[3:0] seen[0:31];
 reg pav=0,prv=0,pstop=0;reg[16:0] pat=0,prt=0;reg[2:0] plen=0;reg[3:0] pbeat=0;
 reg oldfault,oldok;integer checks=0,j,b,gen,phase,kind,idx;
 task automatic fail(input string s);begin $display("FAIL tags %s phase=%0d kind=%0d",s,phase,kind);$fatal(1);end endtask
 task automatic tick;begin
  @(posedge clk);oldfault=|errors;oldok=|expected;expected=0;
  if(pav)begin idx=pat&31;if(vl[idx]||(plen!=1&&plen!=4)||errors[idx]||pstop)errors[idx]=1;
   else begin vl[idx]=1;generation[idx]=pat>>5;lengths[idx]=plen;seen[idx]=0;end end
  if(prv)begin idx=prt&31;
   if(!vl[idx]||generation[idx]!=(prt>>5)||pbeat>=lengths[idx]||pbeat>=4||seen[idx][pbeat&3]||errors[idx]||pstop||(pav&&((pat&31)==idx)))errors[idx]=1;
   else begin expected[idx]=1;seen[idx]=seen[idx]|(1<<(pbeat&3));if(seen[idx]==((lengths[idx]==4)?15:1))vl[idx]=0;end
  end
  #0.01;
  if(accepted!==expected)fail("accepted generation/beat identity");
  if(live!==vl)fail("finite ownership/release");
  if(ok!==oldok||fault!==oldfault)fail("registered status age");
  checks=checks+1;pav=av;pat=at;plen=len;prv=rv;prt=rt;pbeat=beat;pstop=stop;
 end endtask
 task automatic idle;begin @(negedge clk);av=0;rv=0;stop=0;tick();end endtask
 task automatic reset_all;begin
  @(negedge clk);rst_n=0;av=0;rv=0;stop=0;pav=0;prv=0;pstop=0;vl=0;errors=0;expected=0;
  #0.02;if(accepted||live||ok||fault)fail("asynchronous occupied reset");
  repeat(3)@(posedge clk);@(negedge clk);rst_n=1;repeat(3)@(posedge clk);
 end endtask
 initial begin
  for(phase=0;phase<8;phase=phase+1)begin
   reset_all();
   for(gen=0;gen<8;gen=gen+1)begin
    for(j=0;j<32;j=j+1)begin @(negedge clk);av=1;at=17'(gen*32+j);len=(j%5==0)?1:4;rv=0;tick();end
    idle();idle();if(live!==32'hffffffff)fail("32-slot full capacity");
    for(j=0;j<32;j=j+1)for(b=0;b<((j%5==0)?1:4);b=b+1)begin
     @(negedge clk);av=0;rv=1;rt=17'(gen*32+j);beat=(j%5==0)?0:4'(b^(phase&3));tick();
    end
    idle();idle();idle();if(live!==0)fail("all beats retire");
   end
   // Occupied reset cancels all allocations/returns at varying offsets.
   @(negedge clk);av=1;at=0;len=4;tick();@(negedge clk);#(0.02*phase);rst_n=0;#0.01;if(live||accepted)fail("occupied reset leak");
  end
  for(kind=0;kind<7;kind=kind+1)begin
   reset_all();@(negedge clk);av=1;at=0;len=4;tick();idle();idle();
   if(kind==1)begin @(negedge clk);rv=1;rt=0;beat=0;tick();idle();idle();end
   @(negedge clk);av=0;rv=1;rt=(kind==0)?32:(kind==3)?3:0;beat=(kind==2)?4:0;
   if(kind==4||kind==5)begin av=1;at=0;len=4;if(kind==4)rv=0;end
   if(kind==6)stop=1;
   tick();idle();idle();idle();if(!fault)fail("malformed source did not fault");
  end
  $display("PASS owner_tags checks=%0d slots=32 generations=8 phases=8 malformed=7 native_entry_edge=2 scalar_edge=3",checks);$finish;
 end
endmodule
