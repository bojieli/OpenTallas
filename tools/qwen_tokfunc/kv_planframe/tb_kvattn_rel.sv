`timescale 1ns/1ps
// TOKSIM-KVATTN 2026-10-19: release KV-die attention vehicle, one Qwen3-8B decode layer (TP8 rank: 4 Q heads x 128, one FP8
// KV head, T rows) at production shape, 1 or 4 users back to back.
//   tile  = qkd_kvs_attn_fl r16 (release attention tile, kits rv3/rv4; RETIRE_STATIC=1 STATUS_DELAY=213 = the kit params):
//           d2d RX landing + record check + command guard + controller + calendar generator + service root + result face
//           + fault root + d2d TX records
//   data  = kvattn_rel_dp (4 native QK stacks, AHUB, V capture, 2 PV16 pairs, final join, result emitter)
// Stimulus = the die's static schedule only: kvs_ctl i_ctl (cfg / authority / go / issue / run), the compute die's RX record
// stream (CMD + 32 Q beats on the controller's compiled RX ages), the d2d TX slots (RESULT x32 on tx_first, STATUS on its
// compiled slot), the HBM K / V rows (K_EXT / V_EXT edges after each request).  Nothing waits on a ready.
// Checks: every RESULT word == the CPU golden (tools/qwen_tp8_attention_native.py vectors), STATUS ready & !fault, no tile /
// unit fault, K/V row counts.  Cycle counts: CMD landing -> last RESULT beat (start -> retire) and -> STATUS, per user.
// Plusargs: +NU=1|4 +VEC0..+VEC3=<dir> (q.hex kv.hex gold.hex) +CTX=<T> +FD=<F_DLY cfg> +GMUT=<data-path mutant bits>
//   +MODE=steady|k_shift|v_swap|q_swap|k_late  (bench mutants on the boundary stimulus)
// KV-P2-RTL 10-23 (tools/qwen_tokfunc/kv_planframe, bench 0e597ed1c + this edit only): +DQK=<D_QK cfg> (default 0 = as
//   before).  The KV die plan v3 frame (kv_planframe/kvattn_rel_dp.sv PV_LAND 0) keeps the QK words' landing edge while
//   the PV words land 0 edges: the QK path is one relay edge longer than the PV path -> kvs_ctl D_QK 1.
module tb_kvattn_rel;
 parameter integer K_EXT=16,V_EXT=16,RS=1,SD=213,FIN_RLY=0;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0;
 reg [108:0] ictl=0;
 reg rx_ev=0;reg [547:0] rx_pl=0;
 reg sl=0;reg [3:0] sk=0;reg [4:0] sb=0;
 integer NU=1,CTX=8192,FD=3,GM=0,DQK=0;string mode;
 wire txv;wire [547:0] txp;wire [30:0] pvst;wire [64:0] pvfst;wire [164:0] ahs;wire [536:0] prg;
 wire [47:0] c0,c1,c2,c3;wire [7:0] arh;
 wire [533:0] fin;wire [3:0] ufs,ufk;wire ufh,ufp0,ufp1,uff;
 qkd_kvs_attn_fl #(.MUT(0),.RETIRE_STATIC(RS),.STATUS_DELAY(SD)) ut(.ck(ck),.rst_n(rst_n),
  .ufs_WS(ufs[0]),.ufs_WN(ufs[1]),.ufs_ES(ufs[2]),.ufs_EN(ufs[3]),.ufh(ufh),.ufp0(ufp0),.ufp1(ufp1),.uff(uff),
  .ufk_WS(ufk[0]),.ufk_WN(ufk[1]),.ufk_ES(ufk[2]),.ufk_EN(ufk[3]),
  .d2d__srx({521'd0,rx_ev}),.d2d__rx_payload(rx_pl),.d2d__att_tx_slot(sl),.d2d__att_tx_kind(sk),.d2d__att_tx_beat(sb),
  .fin(fin),.attn__tx_valid(txv),.attn__tx_payload(txp),.pvst(pvst),.pvfst(pvfst),.ahs(ahs),.prg(prg),
  .acal_WS(c0),.acal_WN(c1),.acal_ES(c2),.acal_EN(c3),.arh(arh),.i_ctl(ictl));
 wire [31:0] k_req_valid;wire [415:0] k_req_t;
 reg [31:0] k_rsp_valid=0;reg [415:0] k_rsp_t=0;reg [511:0] k_rsp_epoch=0;reg [191:0] k_rsp_layer=0;reg [32767:0] k_rsp_data=0;
 wire [15:0] v_req_valid;wire [223:0] v_req_t;
 reg [15:0] v_rsp_valid=0;wire [15:0] v_rsp_ready;reg [223:0] v_rsp_t=0;
 reg [255:0] v_rsp_epoch=0;reg [95:0] v_rsp_layer=0;reg [16383:0] v_rsp_data=0;
 wire [15:0] dp_age;wire dp_run;wire [1:0] pv_out;wire final_out;wire [31:0] k_words,v_words;wire [15:0] dp_fc;
 reg [2:0] gmut=0;
 kvattn_rel_dp #(.K_EXT(K_EXT),.V_EXT(V_EXT),.FIN_RLY(FIN_RLY)) ud(.clk(ck),.rst_n(rst_n),.gmut(gmut),
  .ahs_i(ahs),.prg_i(prg),.acal_ws(c0),.acal_wn(c1),.acal_es(c2),.acal_en(c3),.pvst_i(pvst),.pvfst_i(pvfst),
  .fin(fin),.ufs(ufs),.ufh(ufh),.ufp0(ufp0),.ufp1(ufp1),.uff(uff),.ufk(ufk),
  .k_req_valid(k_req_valid),.k_req_ready(32'hffffffff),.k_req_t(k_req_t),
  .k_rsp_valid(k_rsp_valid),.k_rsp_t(k_rsp_t),.k_rsp_epoch(k_rsp_epoch),.k_rsp_layer(k_rsp_layer),.k_rsp_data(k_rsp_data),
  .v_req_valid(v_req_valid),.v_req_ready(16'hffff),.v_req_t(v_req_t),
  .v_rsp_valid(v_rsp_valid),.v_rsp_ready(v_rsp_ready),.v_rsp_t(v_rsp_t),.v_rsp_epoch(v_rsp_epoch),
  .v_rsp_layer(v_rsp_layer),.v_rsp_data(v_rsp_data),
  .dp_age_o(dp_age),.dp_run_o(dp_run),.pv_out_o(pv_out),.final_out_o(final_out),.k_words(k_words),.v_words(v_words),
  .fault_cause(dp_fc));
 // ---- tile state taps (stimulus timing only; every check uses ports) ----
 wire busy=ut.u_core.u_attn.ctl.busy;
 wire [15:0] age=ut.u_core.u_attn.ctl.age,rxc=ut.u_core.u_attn.ctl.rx_cmd,txf=ut.u_core.u_attn.ctl.tx_first;
 wire [15:0] last=ut.u_core.u_attn.ctl.last;wire [15:0] st_age=(RS!=0)?last-16'd1:txf+16'd33;
 wire [15:0] c_ep=ut.u_core.u_attn.ctl.ep;wire [5:0] c_ly=ut.u_core.u_attn.ctl.layer;wire [17:0] c_pos=ut.u_core.u_attn.ctl.pos;
 wire ctl_fault=ut.u_core.u_attn.ctl.fault;
 wire r_run=ut.u_core.u_attn_root.running,r_sq=ut.u_core.u_attn_root.start_qk;
 wire [15:0] r_age=ut.u_core.u_attn_root.age;wire [15:0] res_t=ut.u_core.u_attn_face.res_t;
 wire r_lf=ut.u_core.u_attn_root.local_fault,r_iof=ut.u_core.u_attn_root.io_fault;
 wire svc_fault=ut.u_core.w_face__service_fault,res_fault=ut.u_core.u_attn_face.result_fault,cal_fault=ut.u_core.u_attn_cal.fault;
 // ---- vectors ----
 reg [31:0] qv[0:3][0:511];reg [31:0] gold[0:3][0:511];reg [1023:0] kv[0:3][0:16383];
 reg [31:0] qtmp[0:511];reg [31:0] gtmp[0:511];reg [1023:0] kvtmp[0:16383];
 string vec;
 integer cyc=0,u=0,errors=0,i,j,n,pos;
 always @(posedge ck)cyc<=cyc+1;
 // per-user measurements
 integer m_go[0:3],m_run[0:3],m_cmd[0:3],m_sq[0:3],m_klast[0:3],m_vfirst[0:3],m_vlast[0:3],m_pv0[0:3],m_pv1[0:3],m_fin[0:3];
 integer m_res0[0:3],m_res31[0:3],m_st[0:3],m_end[0:3],m_words[0:3],m_errs[0:3],m_stw[0:3],m_kw[0:3],m_vw[0:3],m_fin0age[0:3];
 function [511:0] qbeat(input integer uu,input integer b);
  integer w;begin for(w=0;w<16;w=w+1)qbeat[32*w+:32]=qv[uu][16*b+w];end
 endfunction
 // ---- RX records (CMD at rx_cmd, Q beats rx_cmd+1..+32) and TX slots on the controller's compiled ages ----
 always @(negedge ck)begin
  rx_ev=0;rx_pl=0;sl=0;sk=0;sb=0;
  if(busy&&age>=rxc&&age<=rxc+32)begin
   rx_ev=1;
   if(age==rxc)rx_pl={5'd0,4'd1,c_ly,c_ep,5'd0,{493'd0,5'd0,c_pos[12:0],1'b1}};
   else begin
    integer b;b=age-rxc-1;
    if(mode=="q_swap"&&b==3)b=4;else if(mode=="q_swap"&&b==4)b=3;
    rx_pl={5'd0,4'd2,c_ly,c_ep,5'(age-rxc-1),qbeat(u,b)};
   end
  end
  if(busy&&((age>=txf&&age<txf+32)||age==st_age))begin
   sl=1;sk=(age==st_age)?4'd4:4'd3;sb=(age==st_age)?5'd0:5'(age-txf);
  end
 end
 // ---- HBM K / V boundary: request visible in cycle X -> row presented in cycle X + EXT ----
 localparam integer QN=64;
 integer kq_due[0:31][0:QN-1];integer kq_t[0:31][0:QN-1];integer kq_w[0:31],kq_r[0:31];
 integer vq_due[0:15][0:QN-1];integer vq_t[0:15][0:QN-1];integer vq_w[0:15],vq_r[0:15];
 integer klate=0,vswap=0;
 always @(negedge ck)if(rst_n)begin
  k_rsp_valid=0;v_rsp_valid=0;
  for(i=0;i<32;i=i+1)if(kq_r[i]!=kq_w[i]&&kq_due[i][kq_r[i]%QN]==cyc)begin
   pos=kq_t[i][kq_r[i]%QN];kq_r[i]=kq_r[i]+1;
   k_rsp_valid[i]=1;k_rsp_t[13*i+:13]=13'(pos);k_rsp_epoch[16*i+:16]=c_ep;k_rsp_layer[6*i+:6]=c_ly;
   k_rsp_data[1024*i+:1024]=kv[u][((mode=="k_shift"&&pos==77)?pos+1:pos)%16384];
  end
  for(i=0;i<16;i=i+1)if(vq_r[i]!=vq_w[i]&&vq_due[i][vq_r[i]%QN]==cyc)begin
   pos=vq_t[i][vq_r[i]%QN];
   v_rsp_valid[i]=1;v_rsp_t[14*i+:14]=14'(pos);
   v_rsp_epoch[16*i+:16]=c_ep;v_rsp_layer[6*i+:6]=c_ly;v_rsp_data[1024*i+:1024]=kv[u][(CTX+pos)%16384];
   if(mode=="v_swap"&&i==6)begin if(vswap==3)v_rsp_data[1024*i+:1024]=kv[u][CTX+((pos+1)%CTX)];vswap=vswap+1;end
   vq_r[i]=vq_r[i]+1;
  end
  #0.5;
  for(i=0;i<32;i=i+1)if(k_req_valid[i])begin
   n=K_EXT;if(mode=="k_late"&&i==9&&klate==10)n=K_EXT+1;if(i==9)klate=klate+1;  // KV-MU6 10-20: was klate==50, never reached at T1024 (32 rows/lane)
   kq_due[i][kq_w[i]%QN]=cyc+n;kq_t[i][kq_w[i]%QN]=k_req_t[13*i+:13];kq_w[i]=kq_w[i]+1;
  end
  for(i=0;i<16;i=i+1)if(v_req_valid[i])begin
   n=V_EXT;vq_due[i][vq_w[i]%QN]=cyc+n;vq_t[i][vq_w[i]%QN]=v_req_t[14*i+:14];vq_w[i]=vq_w[i]+1;
  end
 end
 // ---- observation of the ports (posedge-settled values) ----
 always @(posedge ck)if(rst_n)begin
  if(rx_ev&&rx_pl[542:539]==4'd1&&m_cmd[u]<0)m_cmd[u]=cyc;
  if(r_sq&&m_sq[u]<0)m_sq[u]=cyc;
  if(|k_req_valid)m_klast[u]=cyc;
  if(|v_req_valid)begin if(m_vfirst[u]<0)m_vfirst[u]=cyc;m_vlast[u]=cyc;end
  if(pv_out[0]&&m_pv0[u]<0)m_pv0[u]=cyc;
  if(pv_out[1]&&m_pv1[u]<0)m_pv1[u]=cyc;
  if(final_out&&m_fin[u]<0)m_fin[u]=cyc;
  if(fin[0]&&fin[5:1]==0&&m_fin0age[u]<0)begin m_fin0age[u]=r_age;
   $display("FIN0 user %0d root age %0d face res_t %0d (fin pin -> face core +1)",u,r_age,res_t);end
  if(txv&&txp[542:539]==4'd3)begin
   if(txp[516:512]==0)m_res0[u]=cyc;
   if(txp[516:512]==31)m_res31[u]=cyc;
   for(j=0;j<16;j=j+1)if(txp[32*j+:32]!==gold[u][16*txp[516:512]+j])begin
    if(m_errs[u]<6)$display("MISMATCH user %0d word %0d got %08h want %08h",u,16*txp[516:512]+j,txp[32*j+:32],gold[u][16*txp[516:512]+j]);
    m_errs[u]=m_errs[u]+1;end
   if(txp[532:517]!==c_ep||txp[538:533]!==c_ly)m_errs[u]=m_errs[u]+1;
   m_words[u]=m_words[u]+16;
  end
  // STATUS leaves on the cycle the controller has dropped busy; by then the request loop has already advanced u (the
  // next user's go pulse does not raise busy before its run): attribute it to the request that just retired
  // (KV-MU6 10-20: job3 tagged user k's STATUS to user k+1, so every 1-user run and every mutant FAILed on STATUS).
  if(txv&&txp[542:539]==4'd4)begin m_st[(busy||r_run)?u:u-1]=cyc;m_stw[(busy||r_run)?u:u-1]=txp[4:0];end
 end
 task automatic pulse(input integer bit_i);
  begin ictl[bit_i]=1'b1;@(negedge ck);ictl[bit_i]=1'b0;end
 endtask
 integer w,tf=0;reg [17:0] tok;
 initial begin
  if(!$value$plusargs("NU=%d",NU))NU=1;
  if(!$value$plusargs("CTX=%d",CTX))CTX=8192;
  if(!$value$plusargs("FD=%d",FD))FD=3;
  if(!$value$plusargs("GMUT=%d",GM))GM=0;
  if(!$value$plusargs("DQK=%d",DQK))DQK=0;
  $display("KVATTN_CFG fd=%0d dqk=%0d",FD,DQK);
  if(!$value$plusargs("MODE=%s",mode))mode="steady";
  gmut=3'(GM);
  for(u=0;u<4;u=u+1)begin
   m_go[u]=-1;m_run[u]=-1;m_cmd[u]=-1;m_sq[u]=-1;m_klast[u]=-1;m_vfirst[u]=-1;m_vlast[u]=-1;m_pv0[u]=-1;m_pv1[u]=-1;m_fin[u]=-1;
   m_res0[u]=-1;m_res31[u]=-1;m_st[u]=-1;m_end[u]=-1;m_words[u]=0;m_errs[u]=0;m_stw[u]=-1;m_kw[u]=0;m_vw[u]=0;m_fin0age[u]=-1;
  end
  for(u=0;u<NU;u=u+1)begin
   case(u)
    0:if(!$value$plusargs("VEC0=%s",vec))$fatal(1,"+VEC0 required");
    1:if(!$value$plusargs("VEC1=%s",vec))$fatal(1,"+VEC1 required");
    2:if(!$value$plusargs("VEC2=%s",vec))$fatal(1,"+VEC2 required");
    default:if(!$value$plusargs("VEC3=%s",vec))$fatal(1,"+VEC3 required");
   endcase
   $readmemh({vec,"/q.hex"},qtmp);$readmemh({vec,"/gold.hex"},gtmp);$readmemh({vec,"/kv.hex"},kvtmp);
   for(i=0;i<512;i=i+1)begin qv[u][i]=qtmp[i];gold[u][i]=gtmp[i];end
   for(i=0;i<2*CTX&&i<16384;i=i+1)kv[u][i]=kvtmp[i];
  end
  for(i=0;i<32;i=i+1)begin kq_w[i]=0;kq_r[i]=0;end
  for(i=0;i<16;i=i+1)begin vq_w[i]=0;vq_r[i]=0;end
  // kvs_ctl static configuration: PV_LEAD 0, F_DLY = FD, D_QK = DQK, D_RL 0, fused programme, authority valid
  ictl[7:0]=8'd0;ictl[15:8]=8'(FD);ictl[23:16]=8'(DQK);ictl[31:24]=8'd0;ictl[32]=1'b1;ictl[33]=1'b1;
  u=0;
  repeat(4)@(negedge ck);rst_n=1;
  repeat(100)@(negedge ck);
  for(u=0;u<NU;u=u+1)begin
   tok=18'(19+u*101);
   ictl[49:36]=14'(CTX);ictl[65:50]=16'h0b00+16'(u);ictl[83:66]=18'(CTX-1);ictl[89:84]=6'(1+u);ictl[108:91]=tok;
   m_go[u]=cyc;pulse(90);                 // calendar for this context
   repeat(16)@(negedge ck);
   pulse(34);                             // issue
   repeat(6)@(negedge ck);
   m_run[u]=cyc;pulse(35);                // run
   w=0;
   while(w<20000&&(busy||r_run||w<8))begin @(negedge ck);w=w+1;end
   m_end[u]=cyc;m_kw[u]=k_words;m_vw[u]=v_words;
   if(w>=20000)tf=1;
   for(i=0;i<32;i=i+1)begin kq_w[i]=0;kq_r[i]=0;end
   for(i=0;i<16;i=i+1)begin vq_w[i]=0;vq_r[i]=0;end
  end
  repeat(4)@(negedge ck);
  for(u=0;u<NU;u=u+1)begin
   if(m_errs[u]!=0||m_words[u]!=512||m_stw[u][2]!=1'b0||m_stw[u][0]!=1'b1||m_kw[u]!=CTX||m_vw[u]!=CTX)errors=errors+1;
   $display("{\"user\":%0d,\"ctx\":%0d,\"exact\":%s,\"data_errors\":%0d,\"result_words\":%0d,\"status_word\":%0d,\"k_rows\":%0d,\"v_rows\":%0d,\"cyc_go\":%0d,\"cyc_run\":%0d,\"cyc_cmd\":%0d,\"cyc_start_qk\":%0d,\"cyc_k_last\":%0d,\"cyc_v_first\":%0d,\"cyc_v_last\":%0d,\"cyc_pv0_out\":%0d,\"cyc_pv1_out\":%0d,\"cyc_final_out\":%0d,\"cyc_result0\":%0d,\"cyc_result31\":%0d,\"cyc_status\":%0d,\"cyc_idle\":%0d,\"fin0_root_age\":%0d,\"start_to_retire\":%0d,\"start_to_status\":%0d,\"work_span\":%0d}",
    u,CTX,(m_errs[u]==0&&m_words[u]==512)?"true":"false",m_errs[u],m_words[u],m_stw[u],m_kw[u],m_vw[u],m_go[u],m_run[u],m_cmd[u],m_sq[u],
    m_klast[u],m_vfirst[u],m_vlast[u],m_pv0[u],m_pv1[u],m_fin[u],m_res0[u],m_res31[u],m_st[u],m_end[u],m_fin0age[u],
    m_res31[u]-m_cmd[u],m_st[u]-m_cmd[u],m_fin[u]-m_cmd[u]);
  end
  $display("KVATTN_REL %s mode=%s gmut=%0d nu=%0d ctx=%0d fd=%0d tile_fault=%0d svc_fault=%0d result_fault=%0d cal_fault=%0d root_lf=%0d root_iof=%0d dp_fault=%b timeout=%0d period=%0d",
   (errors==0&&!ctl_fault&&!svc_fault&&!tf)?"PASS":"FAIL",mode,GM,NU,CTX,FD,ctl_fault,svc_fault,res_fault,cal_fault,r_lf,r_iof,dp_fc,tf,
   (NU>1)?(m_cmd[NU-1]-m_cmd[0])/(NU-1):0);
  $finish;
 end
endmodule
