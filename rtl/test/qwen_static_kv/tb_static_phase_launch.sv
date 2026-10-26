`timescale 1ps/1fs
module tb_static_phase_launch #(parameter integer MUT=0);
 reg ck=0,hck=0,rst_n=0,hrst_n=0;
 initial begin #1000;forever begin ck=1;#312.5;ck=0;#312.5;end end
 // First core edge with DUT.rn active is coreindex6 at4750u. HBM shares
 // that declared component phase origin. This is not physical phase evidence.
 initial begin #142;forever begin hck=1;#384;hck=0;#384;end end
 reg cg=0,kg=0,vg=0;reg[13:0]ctx=1;reg[15:0]ep=0;reg[5:0]layer=0;
 wire ch,kh,vh,fc,fh,ic,ih;wire[13:0]cth;wire[15:0]eph;wire[5:0]lh;
 qkd_static_kv_phase_launch #(.PH0(0),.SAFE_LOW_U(200),.SAFE_HIGH_U(600),.META_HOLD_CORE(8),.MUT(MUT))dut(
 .ck(ck),.rst_n(rst_n),.hck(hck),.hrst_n(hrst_n),.ctrl_go(cg),.kgo(kg),.vgo(vg),.ctx_t(ctx),.epoch(ep),.layer(layer),
 .ctrl_go_h(ch),.kgo_h(kh),.vgo_h(vh),.ctx_t_h(cth),.epoch_h(eph),.layer_h(lh),
 .fault_core(fc),.fault_hbm(fh),.idle_core(ic),.idle_hbm(ih));
 integer core_i=-1,hbm_i=-7,received=0,scheduled=0;
 reg[2:0]em[0:4095];reg[35:0]meta[0:4095];integer z;
 initial for(z=0;z<4096;z=z+1)begin em[z]=0;meta[z]=0;end
 always @(posedge ck)core_i<=core_i+1;
 always @(posedge hck)begin
  hbm_i=hbm_i+1;#1;
  if(hbm_i>=0)begin
  if({vh,kh,ch}!==em[hbm_i])$fatal(1,"fixed HBM edge differs index%0d actual%h expected%h",hbm_i,{vh,kh,ch},em[hbm_i]);
  if(em[hbm_i]!=0)begin
   if({cth,eph,lh}!==meta[hbm_i])$fatal(1,"actual held metadata changed");
   received=received+1;
  end
  end
 end
 task tick;begin @(posedge ck);#1;end endtask
 task send_safe(input integer p);integer gap,toggle_i,first,out;reg found;reg[2:0]mask;begin
  found=0;
  while(!found)begin
   @(negedge ck);toggle_i=core_i+2;
   gap=768-(((toggle_i-6)*625)%768);
   found=gap>=200&&gap<=600;
  end
  mask=3'(1+p%7);ctx=14'(1+p*17);ep=16'(1234+p);layer=6'(p%36);
  {vg,kg,cg}=mask;
  first=((toggle_i-6)*625)/768+1;out=first+2;
  if(out<0||out>=4096||em[out]!=0)$fatal(1,"invalid declared test schedule");
  em[out]=mask;meta[out]={ctx,ep,layer};scheduled=scheduled+1;
  tick();@(negedge ck);cg=0;kg=0;vg=0;
  repeat(12)tick();
  if(fc||fh)$fatal(1,"valid explicitly phased launch faulted");
 end endtask
 integer p,gap,ti;reg found;
 initial begin
  repeat(5)tick();@(negedge ck);rst_n=1;hrst_n=1;repeat(8)tick();
  for(p=0;p<36;p=p+1)send_safe(p);
  repeat(12)tick();if(received!=scheduled||!ic||!ih)$fatal(1,"real launch debt did not drain");
  // An unsafe phase must fault, without moving the event to a later slot.
  found=0;while(!found)begin @(negedge ck);ti=core_i+2;gap=768-(((ti-6)*625)%768);found=gap<200||gap>600;end
  cg=1;tick();@(negedge ck);cg=0;repeat(10)tick();
  if(!fc)$fatal(1,"unsafe phase accepted without explicit fault");
  if(received!=scheduled)$fatal(1,"unsafe phase was dynamically deferred");
  $display("PASS fixed-phase real transport36 packets, all3 lanes, held metadata, unsafe phase abort MUT=%0d",MUT);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
