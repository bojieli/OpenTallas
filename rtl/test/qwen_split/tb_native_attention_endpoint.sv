`timescale 1ns/1ps
// Actual source endpoint component: typed link boundary stimuli and off-chip K/V
// are declared inputs; gold is compare-only. No reference producer exists inside
// the DUT. All issue/records/slots/finish are fixed by an external compiled image.
module tb_native_attention_endpoint;
 parameter integer K_EXT=16,V_EXT=16,DMUT=0;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 integer CTX,TX_FIRST,END_AGE;reg [175:0] calendar;
 reg issue=0,run=0,rx_event=0,tx_slot=0;
 reg [547:0] rx_payload=0;reg [3:0] tx_slot_kind=0;reg [4:0] tx_slot_beat=0;
 wire tx_valid,busy,fault;wire [547:0] tx_payload;wire [15:0] age;
 reg [15:0] request_epoch=17;reg [5:0] request_layer=6;
 wire [31:0] k_req_valid;wire [415:0] k_req_t;wire [15:0] active_epoch;wire [5:0] active_layer;
 reg [31:0] k_rsp_valid=0;reg [415:0] k_rsp_t=0;reg [511:0] k_rsp_epoch=0;reg [191:0] k_rsp_layer=0;reg [32767:0] k_rsp_data=0;
 wire [15:0] v_req_valid;wire [223:0] v_req_t;
 reg [15:0] v_rsp_valid=0;wire [15:0] v_rsp_ready;reg [223:0] v_rsp_t=0;
 reg [255:0] v_rsp_epoch=0;reg [95:0] v_rsp_layer=0;reg [16383:0] v_rsp_data=0;
 qkd_native_attention_endpoint #(.K_EXT(K_EXT),.V_EXT(V_EXT),.DMUT(DMUT)) u(
  .ck(clk),.rst_n(rst_n),.issue(issue),.run(run),.fused_program_capability(1'b1),.authority_valid(1'b1),
  .authority_epoch(request_epoch),.authority_token(18'd19),.authority_position(18'(CTX-1)),.authority_stage(6'd7),
  .compiled_calendar(calendar),.compiled_rx_cmd(16'd4),.compiled_tx_first(16'(TX_FIRST)),.compiled_end(16'(END_AGE)),
  .rx_event(rx_event),.rx_payload(rx_payload),.tx_slot(tx_slot),.tx_slot_kind(tx_slot_kind),.tx_slot_beat(tx_slot_beat),
  .tx_valid(tx_valid),.tx_payload(tx_payload),.busy(busy),.fault(fault),.age(age),
  .k_req_valid(k_req_valid),.k_req_ready(32'hffffffff),.k_req_t(k_req_t),.active_epoch(active_epoch),.active_layer(active_layer),
  .k_rsp_valid(k_rsp_valid),.k_rsp_t(k_rsp_t),.k_rsp_epoch(k_rsp_epoch),.k_rsp_layer(k_rsp_layer),.k_rsp_data(k_rsp_data),
  .v_req_valid(v_req_valid),.v_req_ready(16'hffff),.v_req_t(v_req_t),.v_rsp_valid(v_rsp_valid),.v_rsp_ready(v_rsp_ready),
  .v_rsp_t(v_rsp_t),.v_rsp_epoch(v_rsp_epoch),.v_rsp_layer(v_rsp_layer),.v_rsp_data(v_rsp_data));
 reg [31:0] qv[0:511];reg [31:0] gold[0:511];reg [1023:0] kv[0:16383];
 string vec,mode;
 // boundary return queues: per lane, indexed by presentation cycle
 localparam integer QN=64;
 integer kq_due[0:31][0:QN-1];integer kq_t[0:31][0:QN-1];integer kq_w[0:31],kq_r[0:31];
 integer vq_due[0:15][0:QN-1];integer vq_t[0:15][0:QN-1];integer vq_w[0:15],vq_r[0:15];

 integer cyc=0,anchor=-1,errors=0,words=0,status_count=0,first_result=-1,last_result=-1;
 integer i,j,n,pos,pa,b;
 always @(posedge clk)cyc<=cyc+1;
 initial begin
  if(!$value$plusargs("VEC=%s",vec)||!$value$plusargs("CTX=%d",CTX)||!$value$plusargs("CAL=%h",calendar)||!$value$plusargs("TX_FIRST=%d",TX_FIRST))$fatal(1,"compiled VEC/CTX/CAL/TX_FIRST required");
  END_AGE=TX_FIRST+34;
  if(!$value$plusargs("MODE=%s",mode))mode="steady";
  $readmemh({vec,"/q.hex"},qv);$readmemh({vec,"/gold.hex"},gold);$readmemh({vec,"/kv.hex"},kv);
  for(i=0;i<32;i=i+1)begin kq_w[i]=0;kq_r[i]=0;end
  for(i=0;i<16;i=i+1)begin vq_w[i]=0;vq_r[i]=0;end
  repeat(8)@(negedge clk);rst_n=1;
  // Exceptional cold-init has a fixed100-cycle reservation; never wait ready.
  repeat(100)@(negedge clk);issue=1;@(negedge clk);issue=0;
  repeat(5)@(negedge clk);run=1;@(negedge clk);run=0;anchor=cyc;
  repeat(END_AGE+6)@(negedge clk);
  $display("ENDPOINT CTX=%0d mode=%s errors=%0d words=%0d status=%0d fault=%b first=%0d last=%0d expected_first=%0d ctl=%b service=%h",
   CTX,mode,errors,words,status_count,fault,first_result,last_result,TX_FIRST+1,u.ctl_fault,u.service_fault_cause);
  if(mode=="steady"&&(fault||errors!=0||words!=512||status_count!=1||first_result!=TX_FIRST+1||last_result!=TX_FIRST+32))$fatal(1,"native endpoint exact/timeline gate failed");
  if(mode!="steady"&&!fault&&errors==0)$fatal(1,"injected fault undetected");
  $finish;
 end
 always @(negedge clk)begin
  pa=anchor<0?-1:cyc-anchor;rx_event=0;tx_slot=0;
  if(pa>=4&&pa<=36)begin
   b=pa-5;
   rx_event=!(mode=="q_drop"&&pa==14);
   rx_payload={5'd0,(pa==4?4'd1:4'd2),6'd6,16'd17,(pa==4?5'd0:5'(b)),512'd0};
   if(pa==4)rx_payload[511:0]=512'((CTX-1)*2+1);
   else for(j=0;j<16;j=j+1)rx_payload[32*j+:32]=qv[16*b+j];
  end
  if(pa>=TX_FIRST&&pa<TX_FIRST+32)begin tx_slot=1;tx_slot_kind=3;tx_slot_beat=5'(pa-TX_FIRST);end
  if(pa==TX_FIRST+33)begin tx_slot=1;tx_slot_kind=4;tx_slot_beat=0;end
 end
 // K/V boundary: requests visible in cycle X are presented in cycle X+EXT
 integer kdrop=0,klate=0,vlate=0,vswap=0;
 always @(negedge clk)if(rst_n)begin
  k_rsp_valid=0;v_rsp_valid=0;
  for(i=0;i<32;i=i+1)if(kq_r[i]!=kq_w[i]&&kq_due[i][kq_r[i]%QN]==cyc)begin
   pos=kq_t[i][kq_r[i]%QN];kq_r[i]=kq_r[i]+1;
   if(!(mode=="k_drop"&&i==5&&kdrop==100))begin
    k_rsp_valid[i]=1;k_rsp_t[13*i+:13]=13'(pos);k_rsp_epoch[16*i+:16]=request_epoch;k_rsp_layer[6*i+:6]=request_layer;
    k_rsp_data[1024*i+:1024]=kv[pos];
   end
   if(i==5)kdrop=kdrop+1;
  end
  for(i=0;i<16;i=i+1)if(vq_r[i]!=vq_w[i]&&vq_due[i][vq_r[i]%QN]==cyc)begin
   pos=vq_t[i][vq_r[i]%QN];
   v_rsp_valid[i]=1;v_rsp_t[14*i+:14]=14'(pos);
   v_rsp_epoch[16*i+:16]=request_epoch;v_rsp_layer[6*i+:6]=request_layer;v_rsp_data[1024*i+:1024]=kv[CTX+pos];
   if(mode=="v_swap"&&i==6)begin if(vswap==3)v_rsp_data[1024*i+:1024]=kv[CTX+((pos+1)%CTX)];vswap=vswap+1;end
   vq_r[i]=vq_r[i]+1;
  end
  // capture the requests visible in this cycle
  #0.5;
  for(i=0;i<32;i=i+1)if(k_req_valid[i])begin
   n=K_EXT;if(mode=="k_late"&&i==9&&klate==50)n=K_EXT+1;if(i==9)klate=klate+1;
   kq_due[i][kq_w[i]%QN]=cyc+n;kq_t[i][kq_w[i]%QN]=k_req_t[13*i+:13];kq_w[i]=kq_w[i]+1;
  end
  for(i=0;i<16;i=i+1)if(v_req_valid[i])begin
   n=V_EXT;if(mode=="v_late"&&i==13&&vlate==20)n=V_EXT+1;if(i==13)vlate=vlate+1;
   vq_due[i][vq_w[i]%QN]=cyc+n;vq_t[i][vq_w[i]%QN]=v_req_t[14*i+:14];vq_w[i]=vq_w[i]+1;
  end
 end

 // Compare-only reference. No expected value is connected to any DUT port.
 always @(posedge clk)if(rst_n&&tx_valid)begin
  if(tx_payload[542:539]==3)begin
   if(first_result<0)first_result=cyc-anchor;last_result=cyc-anchor;
   if(tx_payload[538:517]!={6'd6,16'd17}||tx_payload[516:512]!=5'(words/16))errors=errors+1;
   for(j=0;j<16;j=j+1)if(tx_payload[32*j+:32]!==gold[words+j])begin
    if(errors<8)$display("MISMATCH word%0d got%h want%h",words+j,tx_payload[32*j+:32],gold[words+j]);errors=errors+1;
   end
   words=words+16;
  end else if(tx_payload[542:539]==4)begin
   if(cyc-anchor!=TX_FIRST+34)errors=errors+1;
   status_count=status_count+1;
  end else errors=errors+1;
 end
endmodule
