`timescale 1ns/1ps
module tb_dsrom_engram_lead_static(input wire clk);
 reg rst_n=0,tv=0,first=0,dead=0,slot=0,rv=0;
 reg[11:0]user=0,ru=0;reg[20:0]pos=0,tok=0;reg[2:0]rn=0;
 wire ov,od,os,fault;wire[67:0]ids;wire[11:0]ou;wire[20:0]op,ot;
 ot_dsrom_engram_lead_static dut(.clk(clk),.rst_n(rst_n),.t_v(tv),.t_user(user),.t_pos(pos),.t_tok(tok),.t_first(first),.t_dead(dead),.t_slot(slot),.rb_v(rv),.rb_user(ru),.rb_n(rn),.out_v(ov),.out_ids(ids),.out_dead(od),.out_slot(os),.out_user(ou),.out_pos(op),.out_tok(ot),.fault(fault));
 reg[16:0]expected[0:129279];reg[16:0]hist[0:63][0:31];reg hd[0:63][0:31];integer count[0:63];
 reg[67:0]want[0:3];reg[11:0]eu[0:3];reg[20:0]ep[0:3],et[0:3];reg[3:0]ev=0,ed=0,es=0;
 integer seen=0,issued=0,cy=0,mode=0,i,j,n,k,q,seq;reg blocked;
 reg[8191:0]dir;
 always @(posedge clk)begin
  cy<=cy+1;
  if(rst_n)begin
   ev<={ev[2:0],tv};ed<={ed[2:0],dead};es<={es[2:0],slot};
   for(integer z=3;z>0;z--)begin want[z]<=want[z-1];eu[z]<=eu[z-1];ep[z]<=ep[z-1];et[z]<=et[z-1];end
   if(tv&&user<64&&tok<129280)begin
    seq=first?0:count[user];blocked=dead;
    want[0][16:0]<=dead?17'd2:expected[tok];
    for(integer z=1;z<4;z++)begin
     blocked=blocked||seq<z;
     if(seq>=z)blocked=blocked||hd[user][seq-z];
     want[0][17*z+:17]<=blocked?17'd2:hist[user][seq-z];
    end
    eu[0]<=user;ep[0]<=pos;et[0]<=tok;
    hist[user][seq]=expected[tok];hd[user][seq]=dead;count[user]=seq+1;issued++;
   end
   if(rv&&ru<64&&rn<=count[ru])count[ru]=count[ru]-rn;
  end
 end
 always @(negedge clk)if(rst_n&&mode==0)begin
  if(fault)$fatal(1,"unexpected static lead fault cyc%0d",cy);
  if(ov!==ev[3])$fatal(1,"fixed lead latency changed cyc%0d v%0d want%0d",cy,ov,ev[3]);
  if(ov)begin
   if(ids!==want[3]||ou!==eu[3]||op!==ep[3]||ot!==et[3]||od!==ed[3]||os!==es[3])$fatal(1,"static lead window/context mismatch cyc%0d",cy);
   seen++;
  end
 end
 task step;begin @(negedge clk);end endtask
 initial begin
  if(!$value$plusargs("OT_ROM_DIR=%s",dir))$fatal(1,"missingimages");$readmemh({dir,"/expected.hex"},expected);
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  for(i=0;i<64;i++)count[i]=0;
  repeat(4)step();rst_n=1;step();
  if(mode!=0)begin
   tv=1;first=1;user=mode==2?64:0;tok=mode==1?129280:3;pos=mode==3?1:0;step();tv=0;
   if(mode==4)begin ru=0;rn=1;rv=1;step();rv=0;end
   repeat(10)step();if(!fault)$fatal(1,"negativeescaped");$display("ENGRAM_STATIC_NEG mode%0d caught",mode);$finish;
  end
  // Every user, sustained consecutive tokens including same-user RAW history.
  for(n=0;n<16;n++)for(q=0;q<64;q++)begin
   tv=1;user=q;first=n==0;pos=n;tok=(129279-37*n-193*q)%129280;dead=n==2||n==6;slot=n&1;step();
  end
  tv=0;repeat(6)step();
  // Compiler-reserved rewind slot, then replay rejected prefix from live history.
  for(q=0;q<64;q++)begin ru=q;rn=5;rv=1;step();rv=0;repeat(3)step();
   for(n=11;n<16;n++)begin tv=1;user=q;first=0;pos=n;tok=21946+n;dead=0;slot=n&1;step();end
   tv=0;repeat(5)step();
  end
  // Exhaustive released tokenizer-map address coverage through the actual
  // static producer, cold-first each token to keep history geometry bounded.
  for(n=0;n<129280;n++)begin tv=1;user=0;first=1;pos=0;tok=n;dead=0;slot=n&1;step();end
  tv=0;
  repeat(6)step();if(seen!=issued||seen!=130624)$fatal(1,"missingoutputs");
  $display("ENGRAM_STATIC_PASS issued%0d exactwindows%0d fixedcapture3 noflowcontrol",issued,seen);$finish;
 end
endmodule
