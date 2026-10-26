`timescale 1ns/1ps
module tb_static_layer_programme #(parameter integer MUT=0);
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,we=0,start=0,av=1,authorized=1;
 reg[8:0]addr=0;reg[63:0]data=0,pdigest=64'h123456789abcdef0;
 reg[15:0]pepoch=3,aepoch=16'h1234;reg[17:0]atoken=17,apos=8191;reg[1:0]agen=2;
 wire cg,kg,vg,ai,ar,ws,ls,ss,sd,eq,configured,active,done,fault;
 wire[5:0]stage,layer,completed;wire[15:0]epoch;wire[17:0]token,position;wire[13:0]ctx;wire[1:0]generation;
 wire[7:0]fc;wire[31:0]age,cycles;
 qkd_static_kv_layer_programme #(.MUT(MUT))dut(.ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),
 .start(start),.authority_valid(av),.programme_authorized(authorized),.programme_epoch(pepoch),.programme_digest(pdigest),
 .authority_epoch(aepoch),.authority_token(atoken),.authority_position(apos),.authority_generation(agen),
 .ctrl_go(cg),.kgo(kg),.vgo(vg),.attention_issue(ai),.attention_run(ar),.writer_start(ws),.link_start(ls),
 .stage_start(ss),.stage_done(sd),.expected_upstream_quiet(eq),.completed_stage(completed),
 .stage(stage),.layer(layer),.epoch(epoch),.token(token),.position(position),.ctx_t(ctx),.generation(generation),
 .configured(configured),.active(active),.done(done),.fault(fault),.fault_code(fc),.age(age),.token_cycles(cycles));
 task tick;begin @(posedge ck);#1;end endtask
 task write_word(input integer a,input[63:0]d);begin
  @(negedge ck);we=1;addr=9'(a);data=d;tick();@(negedge ck);we=0;tick();tick();
 end endtask
 task reset_all;begin
  @(negedge ck);rst_n=0;we=0;start=0;av=1;authorized=1;pdigest=64'h123456789abcdef0;pepoch=3;
  repeat(5)tick();@(negedge ck);rst_n=1;repeat(5)tick();
 end endtask
 task boot;integer s,w;reg[31:0]r;begin
  for(s=1;s<=36;s=s+1)for(w=0;w<9;w=w+1)begin
   case(w)0:r=3;1:r=4;2:r=5;3:r=6;4:r=10;5:r=8;6:r=7;7:r=14;8:r=20+s;endcase
   write_word(9*(s-1)+w,{32'b0,r});
  end
  write_word(324,64'h123456789abcdef0);write_word(325,64'd3);write_word(326,64'h514b564c59523336);
  if(!configured||fault)$fatal(1,"complete image not sealed code=%h",fc);
 end endtask
 task execute(input[15:0]ep,input[17:0]tok,input[17:0]pos,input[1:0]gen);
 integer s,t,total;reg expected_ss;begin
  @(negedge ck);aepoch=ep;atoken=tok;apos=pos;agen=gen;start=1;
  tick();@(negedge ck);start=0;tick();
  if(!active||!ss||stage!=1||age!=0)$fatal(1,"actual accepted start differs");
  total=0;
  // Live inputs are not allowed to relabel any of the36 actual stage events.
  @(negedge ck);aepoch=16'hffff;atoken=0;apos=0;agen=0;
  for(s=1;s<=36;s=s+1)begin
   for(t=1;t<=20+s;t=t+1)begin
    tick();total=total+1;
    if(fault)$fatal(1,"valid schedule faulted stage%0d age%0d code%h",s,t,fc);
    if(epoch!=ep||token!=tok||position!=pos||ctx!=pos+1||generation!=gen)$fatal(1,"authoritative context relabeled");
    if(cg!==(t==3)||kg!==(t==4)||vg!==(t==5)||ai!==(t==6)||ar!==(t==10)||ws!==(t==8)||ls!==(t==7))
      $fatal(1,"fixed event differs stage%0d age%0d bits%0b",s,t,{cg,kg,vg,ai,ar,ws,ls});
    if(t<20+s)begin
     if(stage!=s||layer!=s-1||age!=t||sd||ss)$fatal(1,"actual stage/age differs");
     if(eq!==(t>=14))$fatal(1,"compiled quiet marker moved");
    end else begin
     if(!sd||completed!=s)$fatal(1,"stage completion identity differs");
     if(s<36)begin if(stage!=s+1||age!=0||!ss)$fatal(1,"next stage did not start at fixed edge");end
     else if(active||!done||stage!=36)$fatal(1,"all36 fixed completion differs");
    end
    if(cycles!=total)$fatal(1,"token timeline moved");
   end
  end
 end endtask
 integer which=-1;
 initial begin
  if($value$plusargs("CASE=%d",which))begin end
  if(which==-1||which==0)begin
   reset_all();boot();execute(16'h1234,17,8191,2);execute(16'h2345,18,127,1);
  end
  if(which==-1||which==1)begin
   reset_all();@(negedge ck);start=1;repeat(3)tick();if(!fault||!fc[3])$fatal(1,"unsealed start accepted");
  end
  if(which==-1||which==2)begin
   reset_all();boot();@(negedge ck);pdigest=0;start=1;repeat(3)tick();if(!fault||!fc[3])$fatal(1,"wrong authorized programme accepted");
  end
  if(which==-1||which==3)begin
   reset_all();write_word(1,3);if(!fault||!fc[0])$fatal(1,"unordered boot accepted");
  end
  $display("PASS real all36 control roots, persistent two-token context, invalid image/start checks MUT=%0d",MUT);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
