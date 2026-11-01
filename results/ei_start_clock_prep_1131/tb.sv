`timescale 1ps/1fs
module vehicle #(parameter integer N=7, HAS_W=0,HAS_R=1,K0=-50,LAG=1)(
 input wire wc,rc,raw,input wire[34:0]d,input integer mutant,
 output integer checks=0,errors=0,boot_diffs=0,raw_errors=0,
 output integer first_ready_old=-1,first_ready_new=-1);
 localparam integer WN=HAS_W?N:0,RN=HAS_R?N:0,DELTA=LAG-K0;
 localparam integer SD=DELTA<0?-DELTA:0,RD=DELTA>0?DELTA:0;
 localparam integer K1=K0+WN-RN;
 wire[5:0] sr,rr,sc,rrc;
 for(genvar i=0;i<6;i=i+1)begin:g_ref
  ot_dp_rrelay s(.clk(wc),.d(i==0?raw:sr[i-1]),.q(sr[i]));
  ot_dp_rrelay r(.clk(rc),.d(i==0?raw:rr[i-1]),.q(rr[i]));
  if(i==0)begin assign sc[i]=sr[0];assign rrc[i]=rr[0];end
  else begin
   ot_dp_rrelay cs(.clk(wc),.d(sc[i-1]),.q(sc[i]));
   ot_dp_rrelay cr(.clk(rc),.d(rrc[i-1]),.q(rrc[i]));
  end
 end
 integer sp=0,rp=0;
 always @(posedge wc)if(!sr[5])sp<=0;else sp<=sp+1;
 always @(posedge rc)if(!rr[5])rp<=0;else rp<=rp+1;
 wire so,sd,ro,rd;
 ot_dp_landing_origin_s os(.clk(wc),.rst_raw_n(sr[5]),.p_start(sp>=12+SD),.strap_efall(1'b0),.strap_pad(1'b0),.start(so),.start_d(sd));
 ot_dp_landing_origin_s orr(.clk(rc),.rst_raw_n(rr[5]),.p_start(rp>=12+RD),.strap_efall(1'b0),.strap_pad(1'b0),.start(ro),.start_d(rd));
 wire gws,cws,crs;
 ot_dp_landing_relay gface(.clk(wc),.rst_raw_n(sr[5]),.d(sd),.q(gws));
 if(WN>0)begin:g_w
  wire[WN-1:0]wp;
  for(genvar j=0;j<WN;j=j+1)begin:g_p
   ot_dp_landing_relay s(.clk(wc),.rst_raw_n(sc[5]),.d(j==0?sd:wp[j-1]),.q(wp[j]));
  end
  wire last=(mutant!=0 && RN==0)?wp[WN-2]:wp[WN-1];
  ot_dp_landing_relay face(.clk(wc),.rst_raw_n(sc[5]),.d(last),.q(cws));
 end else assign cws=gws;
 if(RN>0)begin:g_r
  wire[RN:0]rpipe;
  for(genvar j=0;j<=RN;j=j+1)begin:g_p
   ot_dp_landing_relay s(.clk(rc),.rst_raw_n(rrc[5]),.d(j==0?ro:rpipe[j-1]),.q(rpipe[j]));
  end
  assign crs=mutant!=0?rpipe[RN]:rpipe[RN-1];
 end else assign crs=ro;
 wire[34:0]gq,cq;wire gr,gf,cr,cf;
 ot_dp_clk_landing_cas #(.W(35),.DEPTH(4)) gold(.fclk(wc),.t_rst_n(gws),.clk(rc),.rst_n(ro),.strap_k(6'(K0)),.d(d),.q(gq),.ready(gr),.fault(gf));
 ot_dp_clk_landing_cas #(.W(35),.DEPTH(4)) cand(.fclk(wc),.t_rst_n(cws),.clk(rc),.rst_n(crs),.strap_k(6'(K1)),.d(d),.q(cq),.ready(cr),.fault(cf));
 integer wc_count=0,rc_count=0,read_count=0;
 integer tx0=0;reg was_tx=0;
 function automatic[34:0] payload(input integer stamp);
  payload={3'b101,8'(stamp/512),24'(stamp)};
 endfunction
 always @(posedge wc)begin
  wc_count<=wc_count+1;
  if(!gws)was_tx<=0;
  else if(!was_tx)begin tx0<=int'(d[23:0]);was_tx<=1;end
 end
 always @(posedge rc)begin:check
  integer index_before;integer want;
  index_before=read_count;
  rc_count<=rc_count+1;
  if(!ro)read_count<=0;else read_count<=read_count+1;
  #1;
  if(rc_count>15 && rr[5]!==rrc[5])begin errors=errors+1;raw_errors=raw_errors+1;end
  if(gr && first_ready_old<0)first_ready_old=rc_count;
  if(cr && first_ready_new<0)first_ready_new=rc_count;
  if(gr && cr)begin
   checks=checks+1;
   want=tx0+index_before-K0;
   if(gq!==cq || gq!==payload(want) || gf || cf)begin
    errors=errors+1;
    if(errors<4)$display("BAD N%0d W%0d R%0d K%0d at%0d gold=%h cand=%h expected=%h gf%0d cf%0d",N,WN,RN,K0,rc_count,gq,cq,payload(want),gf,cf);
   end
  end else if(gq!==cq)boot_diffs=boot_diffs+1;
 end
endmodule
module tb;
 reg wc=0,rc=0,raw=0;reg[34:0]d=0;
 integer phase=0,mutant=0,t;always #416.5 wc=~wc;
 initial begin if($value$plusargs("PHASE=%d",phase))begin end #1;#(phase);forever #416.5 rc=~rc;end
 initial begin if($value$plusargs("MUT=%d",mutant))begin end end
wire integer checks0,errors0,boots0,raws0,gro0,cro0;
vehicle #(.N(7),.HAS_W(0),.HAS_R(1),.K0(-50),.LAG(1)) u0(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks0),.errors(errors0),.boot_diffs(boots0),.raw_errors(raws0),.first_ready_old(gro0),.first_ready_new(cro0));
wire integer checks1,errors1,boots1,raws1,gro1,cro1;
vehicle #(.N(7),.HAS_W(0),.HAS_R(1),.K0(47),.LAG(2)) u1(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks1),.errors(errors1),.boot_diffs(boots1),.raw_errors(raws1),.first_ready_old(gro1),.first_ready_new(cro1));
wire integer checks2,errors2,boots2,raws2,gro2,cro2;
vehicle #(.N(7),.HAS_W(1),.HAS_R(0),.K0(-44),.LAG(1)) u2(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks2),.errors(errors2),.boot_diffs(boots2),.raw_errors(raws2),.first_ready_old(gro2),.first_ready_new(cro2));
wire integer checks3,errors3,boots3,raws3,gro3,cro3;
vehicle #(.N(7),.HAS_W(1),.HAS_R(0),.K0(53),.LAG(2)) u3(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks3),.errors(errors3),.boot_diffs(boots3),.raw_errors(raws3),.first_ready_old(gro3),.first_ready_new(cro3));
wire integer checks4,errors4,boots4,raws4,gro4,cro4;
vehicle #(.N(7),.HAS_W(1),.HAS_R(1),.K0(2),.LAG(2)) u4(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks4),.errors(errors4),.boot_diffs(boots4),.raw_errors(raws4),.first_ready_old(gro4),.first_ready_new(cro4));
wire integer checks5,errors5,boots5,raws5,gro5,cro5;
vehicle #(.N(8),.HAS_W(0),.HAS_R(1),.K0(-50),.LAG(1)) u5(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks5),.errors(errors5),.boot_diffs(boots5),.raw_errors(raws5),.first_ready_old(gro5),.first_ready_new(cro5));
wire integer checks6,errors6,boots6,raws6,gro6,cro6;
vehicle #(.N(8),.HAS_W(0),.HAS_R(1),.K0(47),.LAG(2)) u6(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks6),.errors(errors6),.boot_diffs(boots6),.raw_errors(raws6),.first_ready_old(gro6),.first_ready_new(cro6));
wire integer checks7,errors7,boots7,raws7,gro7,cro7;
vehicle #(.N(8),.HAS_W(1),.HAS_R(0),.K0(-44),.LAG(1)) u7(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks7),.errors(errors7),.boot_diffs(boots7),.raw_errors(raws7),.first_ready_old(gro7),.first_ready_new(cro7));
wire integer checks8,errors8,boots8,raws8,gro8,cro8;
vehicle #(.N(8),.HAS_W(1),.HAS_R(0),.K0(53),.LAG(2)) u8(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks8),.errors(errors8),.boot_diffs(boots8),.raw_errors(raws8),.first_ready_old(gro8),.first_ready_new(cro8));
wire integer checks9,errors9,boots9,raws9,gro9,cro9;
vehicle #(.N(8),.HAS_W(1),.HAS_R(1),.K0(2),.LAG(2)) u9(.wc(wc),.rc(rc),.raw(raw),.d(d),.mutant(mutant),.checks(checks9),.errors(errors9),.boot_diffs(boots9),.raw_errors(raws9),.first_ready_old(gro9),.first_ready_new(cro9));
integer allchecks,allerrors; initial begin
 for(t=0;t<4096;t=t+1)begin @(negedge wc);d={3'b101,8'(t/512),24'(t)};if(t%512==0)raw=0;if(t%512==30)raw=1;end
 #100;allchecks=0;allerrors=0;
allchecks=allchecks+checks0;allerrors=allerrors+errors0;if(checks0<1000 || gro0<0 || cro0<0 || raws0!=0)$fatal(1,"coverage/raw case0");$display("CASE0 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks0,errors0,boots0,gro0,cro0);
allchecks=allchecks+checks1;allerrors=allerrors+errors1;if(checks1<1000 || gro1<0 || cro1<0 || raws1!=0)$fatal(1,"coverage/raw case1");$display("CASE1 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks1,errors1,boots1,gro1,cro1);
allchecks=allchecks+checks2;allerrors=allerrors+errors2;if(checks2<1000 || gro2<0 || cro2<0 || raws2!=0)$fatal(1,"coverage/raw case2");$display("CASE2 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks2,errors2,boots2,gro2,cro2);
allchecks=allchecks+checks3;allerrors=allerrors+errors3;if(checks3<1000 || gro3<0 || cro3<0 || raws3!=0)$fatal(1,"coverage/raw case3");$display("CASE3 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks3,errors3,boots3,gro3,cro3);
allchecks=allchecks+checks4;allerrors=allerrors+errors4;if(checks4<1000 || gro4<0 || cro4<0 || raws4!=0)$fatal(1,"coverage/raw case4");$display("CASE4 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks4,errors4,boots4,gro4,cro4);
allchecks=allchecks+checks5;allerrors=allerrors+errors5;if(checks5<1000 || gro5<0 || cro5<0 || raws5!=0)$fatal(1,"coverage/raw case5");$display("CASE5 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks5,errors5,boots5,gro5,cro5);
allchecks=allchecks+checks6;allerrors=allerrors+errors6;if(checks6<1000 || gro6<0 || cro6<0 || raws6!=0)$fatal(1,"coverage/raw case6");$display("CASE6 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks6,errors6,boots6,gro6,cro6);
allchecks=allchecks+checks7;allerrors=allerrors+errors7;if(checks7<1000 || gro7<0 || cro7<0 || raws7!=0)$fatal(1,"coverage/raw case7");$display("CASE7 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks7,errors7,boots7,gro7,cro7);
allchecks=allchecks+checks8;allerrors=allerrors+errors8;if(checks8<1000 || gro8<0 || cro8<0 || raws8!=0)$fatal(1,"coverage/raw case8");$display("CASE8 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks8,errors8,boots8,gro8,cro8);
allchecks=allchecks+checks9;allerrors=allerrors+errors9;if(checks9<1000 || gro9<0 || cro9<0 || raws9!=0)$fatal(1,"coverage/raw case9");$display("CASE9 checks=%0d errors=%0d boot_diffs=%0d firstready old/new=%0d/%0d",checks9,errors9,boots9,gro9,cro9);
if(mutant==0)begin if(allerrors!=0)$fatal(1,"BASEFAIL errors=%0d",allerrors);$display("BASEPASS actualnative4linkclasses+paired R/W7/8 checks=%0d warmepochs8,allbootdifferencesreported",allchecks);end else begin if(allerrors==0)$fatal(1,"MUTANTNOTCAUGHT");$display("PHASEMUTANTCAUGHT errors=%0d",allerrors);end $finish;end
endmodule
