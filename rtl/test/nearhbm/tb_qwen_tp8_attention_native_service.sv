`timescale 1ns/1ps
// Q-ATTN bench for ot_qwen_tp8_attention_native_service. Q and K/V rows are declared boundary stimuli (the HBM
// side is the only modeled part); gold.hex is compare-only. The bench drives every boundary event on the fixed
// calendar derived from the accept edge; it never waits on DUT readiness.
// Plusargs: +VEC=<dir> (q.hex kv.hex gold.hex) +CTX=<rows> +CAL=<44 hex digits> (compiler calendar; default = generous
// discovery calendar) +MODE=steady|q_late|k_late|k_drop|precision
module tb_qwen_tp8_attention_native_service;
 parameter integer K_EXT=16,V_EXT=16,DMUT=0,TRACE=1;
 parameter integer QK_ISSUE_AGE=34,Z_STRIDE=16;
 integer CTX=8192;
 reg [175:0] calendar;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg request_valid=0;wire request_ready;reg [15:0] request_epoch=17;reg [5:0] request_layer=6;
 reg q_valid=0;wire q_ready;reg [4:0] q_beat=0;reg [511:0] q_data=0;
 wire [31:0] k_req_valid;wire [415:0] k_req_t;wire [15:0] active_epoch;wire [5:0] active_layer;
 reg [31:0] k_rsp_valid=0;reg [415:0] k_rsp_t=0;reg [511:0] k_rsp_epoch=0;reg [191:0] k_rsp_layer=0;reg [32767:0] k_rsp_data=0;
 wire [3:0] v_req_valid;wire [55:0] v_req_t;wire [11:0] v_req_slot;
 reg [3:0] v_rsp_valid=0;wire [3:0] v_rsp_ready;reg [55:0] v_rsp_t=0;reg [11:0] v_rsp_slot=0;
 reg [63:0] v_rsp_epoch=0;reg [23:0] v_rsp_layer=0;reg [4095:0] v_rsp_data=0;
 wire result_valid;wire [4:0] result_beat;wire [511:0] result_data;wire [15:0] result_epoch;wire [5:0] result_layer;
 wire result_done,busy,fault;wire [31:0] cycles,k_words,v_words;wire [15:0] fault_cause;
 ot_qwen_tp8_attention_native_service #(.K_EXT(K_EXT),.V_EXT(V_EXT),.QK_ISSUE_AGE(QK_ISSUE_AGE),
  .Z_STRIDE(Z_STRIDE),.DMUT(DMUT)) u(
  .clk(clk),.rst_n(rst_n),.request_valid(request_valid),.request_ready(request_ready),.request_epoch(request_epoch),
  .request_layer(request_layer),.request_position(18'(CTX-1)),.fused_program_capability(1'b1),.request_calendar(calendar),
  .q_valid(q_valid),.q_ready(q_ready),.q_beat(q_beat),.q_data(q_data),
  .k_req_valid(k_req_valid),.k_req_ready(32'hffffffff),.k_req_t(k_req_t),.active_epoch(active_epoch),.active_layer(active_layer),
  .k_rsp_valid(k_rsp_valid),.k_rsp_t(k_rsp_t),.k_rsp_epoch(k_rsp_epoch),.k_rsp_layer(k_rsp_layer),.k_rsp_data(k_rsp_data),
  .v_req_valid(v_req_valid),.v_req_ready(4'hf),.v_req_t(v_req_t),.v_req_slot(v_req_slot),
  .v_rsp_valid(v_rsp_valid),.v_rsp_ready(v_rsp_ready),.v_rsp_t(v_rsp_t),.v_rsp_slot(v_rsp_slot),.v_rsp_epoch(v_rsp_epoch),
  .v_rsp_layer(v_rsp_layer),.v_rsp_data(v_rsp_data),
  .result_valid(result_valid),.result_ready(1'b1),.result_beat(result_beat),.result_data(result_data),
  .result_epoch(result_epoch),.result_layer(result_layer),.result_done(result_done),.busy(busy),.fault(fault),
  .cycles(cycles),.k_words(k_words),.v_words(v_words),.fault_cause(fault_cause));

 reg [31:0] qv[0:511];reg [31:0] gold[0:511];reg [1023:0] kv[0:16383];
 string vec,mode;
 // boundary return queues: per lane, indexed by presentation cycle
 localparam integer QN=64;
 integer kq_due[0:31][0:QN-1];integer kq_t[0:31][0:QN-1];integer kq_w[0:31],kq_r[0:31];
 integer vq_due[0:3][0:QN-1];integer vq_t[0:3][0:QN-1];integer vq_s[0:3][0:QN-1];integer vq_w[0:3],vq_r[0:3];
 integer cyc=0,acc=-1,errors=0,words=0,first_fault=-1;
 always @(posedge clk)cyc<=cyc+1;
 // trace of calendar events (ages after start_qk)
 integer ev_first[0:31];
 task automatic mark(input integer id,input string what);
  if(ev_first[id]<0)begin ev_first[id]=u.age;if(TRACE)$display("EVENT %-28s age=%0d cyc=%0d",what,u.age,cyc);end
 endtask
 always @(negedge clk)if(rst_n&&u.running)begin
  if(u.dbg[0])mark(0,"s0e0_score_so13");
  if(u.dbg[1])mark(1,"s0_score_committed");
  if(u.dbg[2])mark(2,"s0_ctl_kdone");
  if(u.si_valid[0]&&u.si_type[1:0]==0)mark(3,"s0_ap_lmax");
  if(u.hub_am[35])mark(4,"hub_am0");
  if(u.dbg[3])mark(5,"s0_ep0_so_ce");
  if(u.dbg[24])mark(6,"s3e0_score_so13");
  if(u.exp_committed[15:0]==16'hffff)mark(7,"s0_exp_all_committed");
  if(u.si_valid[0]&&u.si_type[1:0]==1)mark(8,"s0_ap_z_first");
  if(u.si_valid[0]&&u.si_type[1:0]==2)mark(9,"s0_ap_zdone");
  if(u.rz_valid)mark(10,"hub_rz_valid");
  if(u.rz_publish)mark(11,"hub_rz_publish");
  if(|u.v_req_valid)mark(12,"v_req_first");
  if(|u.er_v)mark(13,"er_read_first");
  if(u.gp[0].ov)mark(14,"pv0_in_first");
  if(u.pvalid[0])mark(15,"pv0_out");
  if(u.pvalid[1])mark(16,"pv1_out");
  if(u.fvalid)mark(17,"final_out");
  if(|u.k_req_valid)mark(18,"k_req_first");
  if(u.dbg[4])mark(19,"s0_am_into_qchain");
  if(u.exp_committed==64'hffffffffffffffff)mark(20,"all_exp_committed");
  if(fault&&first_fault<0)begin first_fault=u.age;$display("FIRST_FAULT age=%0d cause=%b stackf=%b kbad=%h vf=%b pf=%b",u.age,fault_cause,u.stack_fault,u.kbad,u.vf,u.pf);end
 end
 integer i,j,n,pos;
 initial begin
  for(i=0;i<32;i=i+1)ev_first[i]=-1;
  if(!$value$plusargs("VEC=%s",vec))$fatal(1,"+VEC required");
  if(!$value$plusargs("MODE=%s",mode))mode="steady";
  if(!$value$plusargs("CTX=%d",CTX))CTX=8192;
  // discovery calendar {R,P1,P0,PV_START,HUB_PUB,HUB_RECIP,HUB_Z,HUB_LMAX,Z,LMAX,EXP}
  calendar={16'd4401,16'd4400,16'd4400,16'd1450,16'd1980,16'd1900,16'd1711,16'd807,16'd1450,16'd800,16'd850};
  if($value$plusargs("CAL=%h",calendar))$display("CALENDAR %h",calendar);
  $readmemh({vec,"/q.hex"},qv);$readmemh({vec,"/gold.hex"},gold);$readmemh({vec,"/kv.hex"},kv);
  for(i=0;i<32;i=i+1)begin kq_w[i]=0;kq_r[i]=0;end
  for(i=0;i<4;i=i+1)begin vq_w[i]=0;vq_r[i]=0;end
  repeat(8)@(negedge clk);rst_n=1;
  while(!request_ready)@(negedge clk);
  request_valid=1;@(negedge clk);request_valid=0;
 end
 // q beats: the bench anchors on the start cycle (the cycle after the accept edge) and presents beat b in
 // anchor+1+b, independent of q_ready.
 integer qa;integer started=0;
 always @(negedge clk)begin
  if(u.start_qk&&acc<0)acc=cyc;
  qa=(acc<0)?-1:cyc-acc;
  q_valid=0;
  begin : qdrive
   integer b;b=qa-1;
   if(mode=="q_late"&&b>=9)b=b-1;
   if(b>=0&&b<32&&!(mode=="q_late"&&qa==10))begin
    q_valid=1;q_beat=5'(b);
    for(j=0;j<16;j=j+1)begin q_data[32*j+:32]=qv[16*b+j];if(mode=="precision")q_data[32*j+:16]=16'd0;end
   end
  end
 end
 // K/V boundary: requests visible in cycle X are presented in cycle X+EXT
 integer kdrop=0,klate=0;
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
  for(i=0;i<4;i=i+1)if(vq_r[i]!=vq_w[i]&&vq_due[i][vq_r[i]%QN]==cyc)begin
   pos=vq_t[i][vq_r[i]%QN];
   v_rsp_valid[i]=1;v_rsp_t[14*i+:14]=14'(pos);v_rsp_slot[3*i+:3]=3'(vq_s[i][vq_r[i]%QN]);
   v_rsp_epoch[16*i+:16]=request_epoch;v_rsp_layer[6*i+:6]=request_layer;v_rsp_data[1024*i+:1024]=kv[CTX+pos];
   vq_r[i]=vq_r[i]+1;
  end
  // capture the requests visible in this cycle
  #0.5;
  for(i=0;i<32;i=i+1)if(k_req_valid[i])begin
   n=K_EXT;if(mode=="k_late"&&i==9&&klate==50)n=K_EXT+1;if(i==9)klate=klate+1;
   kq_due[i][kq_w[i]%QN]=cyc+n;kq_t[i][kq_w[i]%QN]=k_req_t[13*i+:13];kq_w[i]=kq_w[i]+1;
  end
  for(i=0;i<4;i=i+1)if(v_req_valid[i])begin
   vq_due[i][vq_w[i]%QN]=cyc+V_EXT;vq_t[i][vq_w[i]%QN]=v_req_t[14*i+:14];vq_s[i][vq_w[i]%QN]=v_req_slot[3*i+:3];vq_w[i]=vq_w[i]+1;
  end
 end
 // compare-only golden check
 always @(posedge clk)if(rst_n&&result_valid)begin
  for(j=0;j<16;j=j+1)if(result_data[32*j+:32]!==gold[16*result_beat+j])begin
   if(errors<8)$display("MISMATCH word %0d got %08h want %08h",16*result_beat+j,result_data[32*j+:32],gold[16*result_beat+j]);
   errors=errors+1;end
  if(result_epoch!==request_epoch||result_layer!==request_layer)errors=errors+1;
  words=words+16;
 end
 initial begin
  #400000;$display("TIMEOUT");$finish;
 end
 always @(negedge clk)if(acc>=0&&!u.running&&started==0)begin
  started=1;
  repeat(4)@(posedge clk);
  $display("{\"scope\":\"NATIVE_STATIC_ATTENTION_SERVICE_T8192_COMMONPHASE\",\"mode\":\"%s\",\"exact\":%s,\"fault\":%0d,\"fault_cause\":\"%b\",\"data_errors\":%0d,\"output_words\":%0d,\"k_rows\":%0d,\"v_rows\":%0d,\"service_cycles\":%0d,\"first_fault_age\":%0d}",
   mode,(errors==0&&!fault&&words==512)?"true":"false",fault,fault_cause,errors,words,k_words,v_words,cycles,first_fault);
  $finish;
 end
endmodule
