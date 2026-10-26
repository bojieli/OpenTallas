`timescale 1ns/1fs
// Actual dual-clock return FIFO at declared component phases; no phase or
// depth result is a routed die contract. Fixed slots derive from clock edges,
// not rd_valid/ready. Missing, wrong tag and late slots must fail.
module tb_static_return_slots_mc;
 parameter integer DEPTH=8;
 parameter real CORE_PHASE=0.137;
 localparam real CORE_T=0.833334,HBM_T=1.024;
 reg hclk=0,ck=0;
 always #0.512 hclk=~hclk;
 initial begin #(CORE_PHASE);forever #0.416667 ck=~ck;end
 reg rst=0;reg [293:0] co=0;
 reg hput=0;reg put=0;reg [9:0] sec=0;
 wire av,hf,cf;wire [9:0] as;wire [15:0] ae;wire [5:0] al;wire [255:0] ad;
 qkd_static_kv_return_slots_mc #(.DEPTH(DEPTH))dut(.pll_hbm(hclk),.pll_hbm_data({4{hclk}}),.hrst(rst),.ck(ck),.rsi(rst),
  .controller_co(co),.compiled_hbm_put(hput),.controller_epoch(16'd7),.expected_put(put),.expected_sector(sec),.expected_epoch(16'd7),.expected_layer(6'd3),
  .actual_valid(av),.actual_sector(as),.actual_epoch(ae),.actual_layer(al),.actual_data(ad),.fault_hbm(hf),.fault_core(cf));
 function automatic [255:0] pattern(input integer s);
  for(integer w=0;w<8;w++)pattern[32*w+:32]=32'h23981100^32'(s*71+w*19);
 endfunction
 reg wanted[0:1800];integer sector[0:1800];integer mode=0,errors=0,seen=0;
 reg prev=0;integer prevsector=0;
 initial begin
  void'($value$plusargs("faultmode=%d",mode));
  for(integer j=0;j<1801;j++)begin wanted[j]=0;sector[j]=0;end
  // HBM puts occur on input edges numbered200..455 and1000..1255.
  // Two HBM pin/storage edges then four complete core edges before issue.
  for(integer n=0;n<512;n++)begin
   automatic integer h=n<256?200+n:1000+n-256;
   automatic integer s=n<256?n:512+n-256;
   automatic real write_t=0.512+(h+1)*HBM_T;
   automatic integer j=integer'($ceil((write_t-(CORE_PHASE+CORE_T/2))/CORE_T))+4;
   if(wanted[j])$fatal(1,"compiled duplicate delivery edge");
   wanted[j]=1;sector[j]=s;
  end
  #20;rst=1;
 end
 integer hi=0;
 always @(negedge hclk)begin
  co=0;hput=0;
  if(hi>=200&&hi<456||hi>=1000&&hi<1256)begin
   automatic integer s=hi<456?hi-200:512+hi-1000;
   hput=1;co[0]=1;co[17:1]={6'd3,3'(s>>7),1'b0,7'(s)};co[281:26]=pattern(s);
   if(mode==1&&hi==217)co[0]=0;
   if(mode==2&&hi==217)co[1]=~co[1];
  end
  hi++;
 end
 integer ci=0;
 // Drive on core falling edges for the following rising edge ci. Initial
 // first rising edge has no driver yet, so this falling edge prepares ci=1.
 always @(negedge ck)begin
  ci++;put=ci<=1800?wanted[ci]:0;sec=ci<=1800?10'(sector[ci]):0;
  if(mode==3&&ci>0&&ci<=1800)begin put=wanted[ci-1];sec=10'(sector[ci-1]);end
 end
 always @(posedge ck)begin
  automatic reg ev=prev;automatic integer es=prevsector;
  prev=ci<=1800?wanted[ci]:0;prevsector=ci<=1800?sector[ci]:0;
  #0.000001;
  if(rst)begin
   if(av!==ev)errors++;
   if(av)begin seen++;if(ad!==pattern(es)||as!=es||ae!=7||al!=3)errors++;end
  end
  if(ci==1800)begin
   if(errors||hf||cf||seen!=512)begin $display("FAIL native return slots depth%0d rows%0d errors%0d hbfault%b corefault%b mode%0d",DEPTH,seen,errors,hf,cf,mode);$fatal(1);end
   $display("PASS native return slots depth%0d rows512 core833.334ps HBM1024ps phase%0.3fps fixedSlots noRuntimeReady",DEPTH,CORE_PHASE*1000);$finish;
  end
 end
endmodule
