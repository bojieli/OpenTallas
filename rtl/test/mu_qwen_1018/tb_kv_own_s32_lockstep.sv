`timescale 1ns/1ps
// KV-CTL3 10-20: qkd_static_kv_ownership_calendar_mu_s32 S32 1 (sliced root banks behind ot_s32_sel leaves) in lockstep
// with qkd_static_kv_ownership_calendar_mu (the tile form MU 1 PIPE 1 SAFE 1 RCOPIES 12): same inputs, EVERY output on
// EVERY edge.  Episodes: reset (also inside windows), boot of enter / leave / deadline roots + magic seal (sometimes
// wrong / out of order / during a window), then go pulses (re-arms inside the active window), quiet / drain drops and
// group faults.  PASS KV_OWN_S32_LOCKSTEP ... / FAIL KV_OWN_S32_LOCKSTEP mismatches<n>
module tb_kv_own_s32_lockstep;
 parameter integer EPIS=3000,SEED=7;
 reg ck=0;always #5 ck=~ck;
 integer seed=SEED;
 reg rst=0,we=0,go=0,host=1,up=1;reg[1:0]addr=0;reg[31:0]data=0,gd=32'hffffffff,gf=0;
 wire m0,v0,r0,a0,d0,c0,f0,m1,v1,r1,a1,d1,c1,f1;wire[31:0]cy0,cy1;wire[7:0]fc0,fc1;
 qkd_static_kv_ownership_calendar_mu #(.MUT(0),.MU(1),.PIPE(1),.SAFE(1),.RCOPIES(12)) ref0(.ck(ck),.rst_n(rst),.cfg_we(we),.cfg_addr(addr),
  .cfg_data(data),.go(go),.host_quiet(host),.upstream_quiet(up),.group_drained(gd),.group_fault(gf),.native_mode(m0),.ownership_valid(v0),
  .native_reserved(r0),.active(a0),.done(d0),.configured(c0),.cycle(cy0),.fault(f0),.fault_code(fc0));
 qkd_static_kv_ownership_calendar_mu_s32 #(.MUT(0),.MU(1),.PIPE(1),.SAFE(1),.RCOPIES(12),.S32(1)) dut(.ck(ck),.rst_n(rst),.cfg_we(we),.cfg_addr(addr),
  .cfg_data(data),.go(go),.host_quiet(host),.upstream_quiet(up),.group_drained(gd),.group_fault(gf),.native_mode(m1),.ownership_valid(v1),
  .native_reserved(r1),.active(a1),.done(d1),.configured(c1),.cycle(cy1),.fault(f1),.fault_code(fc1));
 wire[47:0]va={m0,v0,r0,a0,d0,c0,f0,fc0,cy0},vb={m1,v1,r1,a1,d1,c1,f1,fc1,cy1};
 integer mism=0,cycles=0,dones=0,faults=0,natives=0,cfgs=0;
 always @(posedge ck)begin
  #1;cycles=cycles+1;
  if(va!==vb)begin mism=mism+1;if(mism<=5)$display("MISMATCH cyc %0d ref %h dut %h",cycles,va,vb);end
  if(d0)dones=dones+1;if(m0)natives=natives+1;
 end
 task automatic step(input integer n);integer i;begin for(i=0;i<n;i=i+1)@(negedge ck);end endtask
 task automatic wr(input [1:0]a,input [31:0]d);begin @(negedge ck);we=1;addr=a;data=d;@(negedge ck);we=0;end endtask
 integer e,k,en,lv,dl,ngo,mode;
 initial begin
  for(e=0;e<EPIS;e=e+1)begin
   @(negedge ck);rst=0;we=0;go=0;gf=0;step(2+$unsigned($random(seed))%3);rst=1;step(3);
   mode=$unsigned($random(seed))%8;
   en=3+$unsigned($random(seed))%20;lv=en+1+$unsigned($random(seed))%40;dl=lv+1+$unsigned($random(seed))%30;
   if(mode==7)begin en=$unsigned($random(seed))%6;lv=$unsigned($random(seed))%8;dl=$unsigned($random(seed))%10;end
   wr(0,en);if(mode!=6)wr(1,lv);wr(2,dl);
   if(mode==5)wr(3,32'h514b564e);else wr(3,32'h514b564d);
   if(f0===1'b0)cfgs=cfgs+1;
   ngo=1+$unsigned($random(seed))%6;
   for(k=0;k<ngo;k=k+1)begin
    step($unsigned($random(seed))%((mode==4)?4:(lv+8)));
    @(negedge ck);go=1;@(negedge ck);go=0;
    if($unsigned($random(seed))%4==0)begin host=$unsigned($random(seed))%2;up=$unsigned($random(seed))%2;end else begin host=1;up=1;end
    gd=($unsigned($random(seed))%5==0)?$unsigned($random(seed)):32'hffffffff;
    gf=($unsigned($random(seed))%40==0)?(32'd1<<($unsigned($random(seed))%32)):0;
    if($unsigned($random(seed))%30==0)wr($unsigned($random(seed))%4,$unsigned($random(seed)));
    if($unsigned($random(seed))%50==0)begin @(negedge ck);rst=0;step(2);rst=1;end
   end
   step(dl+10);
   if(f0)faults=faults+1;
  end
  if(mism==0)$display("PASS KV_OWN_S32_LOCKSTEP mismatches0 episodes%0d cycles%0d configured%0d dones%0d native_cycles%0d fault_episodes%0d",EPIS,cycles,cfgs,dones,natives,faults);
  else $display("FAIL KV_OWN_S32_LOCKSTEP mismatches%0d cycles%0d",mism,cycles);
  $finish;
 end
endmodule
