`timescale 1ns/1ps
// TOKSIM-KVATTN 2026-10-19: KV-die attention DATA PATH of the release attention vehicle, driven by the release attention
// tile's die words (qkd_kvs_attn_fl r16: ahs / prg / acal_* / pvst / pvfst in, fin + unit faults out).
//
// The data path is the qualified 16-row/cycle static native attention service (ot_qwen_tp8_attention_native_service_w16_sr)
// with its service root REMOVED: every start / context / epoch / calendar word comes from the release tile's own root
// (qkd_attn_service_root_r16) and calendar generator (qkd_attn_cal_gen_r16, G3S2=1, SERVICE_END 1777), exactly as the die
// wires them.  Composition (all current source, nothing replaced by C++ or a model):
//   4 x ot_qwen_tp8_attention_native_stack_w4_cp (ECTL3 STATIC_QK x8 + 32 x ot_qkh_head_native_r4 + mapped ASTK on its SRAM macros)
//   ot_qkd_ahub_static_die_cal (4 ZH trees + reciprocal leaf)
//   8 x ot_qwen_tp8_vrow_capture (LATENCY 3, the actual EP ER3 read)   2 x ot_qwen_tp8_pv_wide_pair (PV16: 8 banks each)
//   ot_qwen_tp8_pv256_finalize_static_cal (32 join16) + the 32-beat result emitter -> fin
// Vehicle frame (0 die relays; the tile's cfg D_QK = D_RL = 0, PV_LEAD = 0, F_DLY = the fin edges below):
//   ahs / acal / pvst / pvfst land in ONE relay edge (datapath age a = root age a + 1); prg is used as launched (its q beat b
//   is visible at root age b + 2 = datapath age b + 1, the q slot of the qualified service).  fin leaves the emitter
//   FIN_RLY edges later (0 = none; GMUT[1] adds one = the late-fin mutant).
// PLAN FRAME (KV-P2-RTL 10-23, tools/qwen_tokfunc/kv_planframe): PV_LAND = the relay edges of the PV start words pvst /
//   pvfst between the tile root (kvs_attn) and the PV datapath (pvw heads + pvfin).  1 = the vehicle frame above (pvst /
//   pvfst share the ahs / acal landing edge: D(pvp) = 1 -> F_DLY 3).  0 = the KV die plan v3 frame (kv_params_v3: pvfin,
//   kvs_attn and the pvw RH_r0 heads co-located in hub_C, D(pvp) = 0 -> F_DLY law 1 + 0 + 0 + 1 = 2): pvst / pvfst enter
//   the PV datapath as launched; ahs / acal keep their landing edge (QK frame unchanged), prg unchanged.  Every PV-frame age
//   (pv_ctx / P0 / P1 / R ages, V request -> row, the final join, the emitter) is relative to start_pv / fin_start, so the
//   PV frame moves as one; the QK -> PV joins (exp readback, reciprocal publish) are checked by er_bad / rz_late.
// Only side modeled: the HBM K / V boundary (rows presented K_EXT / V_EXT edges after their request; checked here).
// GMUT (bench-only runtime mutants, 0 = release): [0] reciprocal LSB flip of head 0, [1] fin one edge late, [2] context
//   length -1 on the data path.
module kvattn_rel_dp #(
 parameter integer K_EXT=16, V_EXT=16,
 parameter integer QK_ISSUE_AGE=34,
 parameter integer Z_STRIDE=16,
 parameter integer FIN_RLY=0,
 parameter integer PV_LAND=0
)(
 input wire clk,rst_n,
 input wire [2:0] gmut,
 // release attention tile die words
 input wire [164:0] ahs_i,input wire [536:0] prg_i,input wire [47:0] acal_ws,acal_wn,acal_es,acal_en,
 input wire [30:0] pvst_i,input wire [64:0] pvfst_i,
 output wire [533:0] fin,
 output wire [3:0] ufs,output wire ufh,ufp0,ufp1,uff,output wire [3:0] ufk,
 // HBM K / V boundary
 output wire [31:0] k_req_valid,input wire [31:0] k_req_ready,
 output wire [415:0] k_req_t,
 input wire [31:0] k_rsp_valid,input wire [415:0] k_rsp_t,
 input wire [511:0] k_rsp_epoch,input wire [191:0] k_rsp_layer,input wire [32767:0] k_rsp_data,
 output wire [15:0] v_req_valid,input wire [15:0] v_req_ready,
 output wire [223:0] v_req_t,
 input wire [15:0] v_rsp_valid,output wire [15:0] v_rsp_ready,
 input wire [223:0] v_rsp_t,
 input wire [255:0] v_rsp_epoch,input wire [95:0] v_rsp_layer,input wire [16383:0] v_rsp_data,
 // observation (bench taps only)
 output wire [15:0] dp_age_o,output wire dp_run_o,output wire [1:0] pv_out_o,output wire final_out_o,
 output wire [31:0] k_words,v_words,output wire [15:0] fault_cause
);
 localparam integer V_RL=V_EXT+3;
 localparam integer FIRST_INPUT_AGE=1+V_RL;
 localparam integer QK_REQ_RELAYS=2,QK_RSP_PIN_STAGES=3;
 localparam integer ROW_RETURN_LAT=K_EXT+QK_REQ_RELAYS+QK_RSP_PIN_STAGES;
 // Fixed genuine archive specializations; unsupported outer controls must not silently reuse them.
 generate if(QK_ISSUE_AGE!=34 || ROW_RETURN_LAT!=21 || Z_STRIDE!=16 || FIRST_INPUT_AGE!=20)begin:bad_archive_profile
  UNSUPPORTED_ATTENTION_ARCHIVE_PROFILE invalid();
 end endgenerate
 // ---------------- the one landing edge of the root-side words ----------------
 reg [164:0] ahs;reg [191:0] acal;reg [30:0] pvst_q;reg [64:0] pvfst_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin ahs<=0;pvst_q<=0;pvfst_q<=0;acal<=0;end
  else begin ahs<=ahs_i;pvst_q<=pvst_i;pvfst_q<=pvfst_i;acal<={acal_en,acal_es,acal_wn,acal_ws};end
 generate if(PV_LAND!=0&&PV_LAND!=1)begin:bad_pv_land UNSUPPORTED_PV_LAND invalid();end endgenerate
 wire [30:0] pvst=(PV_LAND!=0)?pvst_q:pvst_i;wire [64:0] pvfst=(PV_LAND!=0)?pvfst_q:pvfst_i;
 wire start_qk=ahs[0];
 wire [15:0] ep=ahs[16:1];wire [5:0] layer=ahs[22:17];
 wire [13:0] ctx=ahs[36:23]-((gmut[2])?14'd1:14'd0);
 // ahs[148:37] = root cal[127:16]
 wire [15:0] LMAX_START_AGE=ahs[52:37],Z_START_AGE=ahs[68:53];
 wire [15:0] HUB_LMAX_ISSUE_AGE=ahs[84:69],HUB_Z_START_AGE=ahs[100:85],HUB_RECIP_ISSUE_AGE=ahs[116:101],HUB_RZ_PUBLISH_AGE=ahs[132:117];
 wire start_pv=pvst[0];wire [13:0] pv_ctx=pvst[14:1]-((gmut[2])?14'd1:14'd0);wire [15:0] pv_ep=pvst[30:15];
 wire fin_start=pvfst[0];wire [15:0] fin_ep=pvfst[16:1];
 wire [15:0] P0_AGE=pvfst[32:17],P1_AGE=pvfst[48:33],R_AGE=pvfst[64:49];
 // ---------------- data-path frame ----------------
 reg [15:0] dp_age;reg dp_run;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin dp_age<=0;dp_run<=0;end
  else if(start_qk)begin dp_age<=0;dp_run<=1;end else if(dp_run)dp_age<=dp_age+1'b1;
 assign dp_age_o=dp_age;assign dp_run_o=dp_run;
 // ---------------- per stack: native QK stack, K boundary ----------------
 wire [3:0] stack_fault;
 wire [2251:0] ap_all;
 wire [143:0] hub_am;
 wire [15:0] er_v;wire [175:0] er_addr;
 wire [15:0] er_rsp_v;wire [175:0] er_rsp_addr;wire [1023:0] er_data;
 wire [63:0] exp_committed;wire [3:0] score_committed;
 wire [31:0] dbg;wire [31:0] kbad;reg [31:0] kcount[0:31];
 wire [539:0] aq;
 assign aq[0]=start_qk;assign aq[14:1]=ctx;assign aq[20:15]=6'd0;
 assign aq[21]=prg_i[19];assign aq[27:22]={1'b0,prg_i[24:20]};assign aq[539:28]=prg_i[536:25];
 genvar s,e;
 generate for(s=0;s<4;s=s+1)begin:gs
  wire [135:0] k_request;wire [8199:0] k_response;
  wire [35:0] am_s={hub_am[36*s+:32],hub_am[36*s+32+:2],hub_am[36*s+34],hub_am[36*s+35]};
  ot_qwen_tp8_attention_native_stack_w4_cp_5 u_stack(
   .cal(acal[48*s+:48]),.stack_id(2'(s)),.clk(clk),.rst_n(rst_n),.aq(aq),.am(am_s),.ap(ap_all[563*s+:563]),.active_layer_parity(layer[0]),
   .k_request(k_request),.k_response(k_response),
   .er_v(er_v[4*s+:4]),.er_addr(er_addr[44*s+:44]),.er_rsp_v(er_rsp_v[4*s+:4]),.er_rsp_addr(er_rsp_addr[44*s+:44]),
   .er_data(er_data[256*s+:256]),.exp_committed(exp_committed[16*s+:16]),.score_committed(score_committed[s]),
   .fault(stack_fault[s]),.dbg(dbg[8*s+:8]));
  for(e=0;e<8;e=e+1)begin:ge
   localparam integer I=8*s+e;
   wire [16:0] rq=k_request[17*e+:17];
   assign k_req_valid[I]=rq[0];
   assign k_req_t[13*I+:13]=rq[15:3];
   reg [K_EXT-1:0] due;reg [12:0] tag[0:K_EXT-1];reg bad;
   always @(posedge clk or negedge rst_n)begin
    if(!rst_n)begin due<=0;bad<=0;kcount[I]<=0;end
    else begin
     due<={due[K_EXT-2:0],rq[0]};
     if(rq[0]&&(rq[2:1]!=0||!k_req_ready[I]))bad<=1;
     if(k_rsp_valid[I]!=due[K_EXT-1])bad<=1;
     if(k_rsp_valid[I]&&(k_rsp_t[13*I+:13]!=tag[K_EXT-1]||k_rsp_epoch[16*I+:16]!=ep||k_rsp_layer[6*I+:6]!=layer))bad<=1;
     if(start_qk)kcount[I]<=0;else if(k_rsp_valid[I])kcount[I]<=kcount[I]+1;
    end
   end
   always @(posedge clk)begin tag[0]<=rq[15:3];for(integer j=1;j<K_EXT;j=j+1)tag[j]<=tag[j-1];end
   assign kbad[I]=bad;
   assign k_response[1025*e+:1025]={k_rsp_data[1024*I+:1024],k_rsp_valid[I]};
  end
  assign ufk[s]=|kbad[8*s+:8];
 end endgenerate
 integer x;reg [31:0] ksum;
 always @*begin ksum=0;for(x=0;x<32;x=x+1)ksum=ksum+kcount[x];end
 assign k_words=ksum;
 // ---------------- static AHUB ----------------
 reg [63:0] held_epoch;reg [23:0] held_layer;
 always @(posedge clk)if(start_qk)begin held_epoch<={4{ep}};held_layer<={4{layer}};end
 wire [3:0] si_valid,si_g,si_any;wire [7:0] si_type,si_hh;wire [15:0] si_k;wire [127:0] si_data;
 wire [3:0] legacy_pv;
 generate for(s=0;s<4;s=s+1)begin:gsi
  wire [562:0] ap=ap_all[563*s+:563];
  assign si_valid[s]=ap[0];assign si_type[2*s+:2]=ap[2:1];assign si_g[s]=ap[3];assign si_hh[2*s+:2]=ap[5:4];
  assign si_k[4*s+:4]=ap[9:6];assign si_any[s]=ap[10];assign si_data[32*s+:32]=ap[42:11];
  assign legacy_pv[s]=ap[43];
 end endgenerate
 wire rz_valid,rz_publish,hub_fault;wire [1:0] rz_head;wire [31:0] rz_data;wire [15:0] rz_epoch;wire [127:0] rz_vector;
 wire [15:0] LIN=LMAX_START_AGE+16'd2,ZIN=Z_START_AGE+16'd2;
 ot_qkd_ahub_static_die_cal_3 u_hub(
  .cal({HUB_RZ_PUBLISH_AGE,HUB_RECIP_ISSUE_AGE,HUB_Z_START_AGE,HUB_LMAX_ISSUE_AGE,ZIN,ZIN,ZIN,ZIN,LIN,LIN,LIN,LIN}),
  .ck_core(clk),.ck_recip(clk),.ck_zh({4{clk}}),.rst_n(rst_n),.start(start_qk),.active_layer_parity(layer[0]),
  .request_epoch(ep),.active_layer(layer),.T(ctx),
  .si_valid(si_valid),.si_g(si_g),.si_any(si_any),.si_epoch(held_epoch),.si_layer(held_layer),.si_type(si_type),.si_hh(si_hh),
  .si_k(si_k),.si_data(si_data),.am(hub_am),.rz_valid(rz_valid),.rz_head(rz_head),.rz_data(rz_data),.rz_epoch(rz_epoch),
  .rz_publish(rz_publish),.rz_vector(rz_vector),.fault(hub_fault));
 reg rz_published;reg rz_late;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)rz_published<=0;else if(start_qk)rz_published<=0;else if(rz_publish)rz_published<=1;
 // ---------------- V rows (16 ports), EP e read, PV16 pairs ----------------
 wire [1:0] vf,pf;wire [1:0] pvalid;wire [32767:0] partial;wire [31:0] pep;wire [31:0] pv_out_age;
 wire [15:0] cv;wire [223:0] ct;wire [255:0] cep;wire [16383:0] crow;
 reg [31:0] vcount[0:1];
 assign v_rsp_ready=16'hffff;
 genvar k;
 generate for(k=0;k<16;k=k+1)begin:gk
  assign er_v[k]=v_rsp_valid[k];
  assign er_addr[11*k+:11]={v_rsp_t[14*k+9+:4],v_rsp_t[14*k+:7]};
 end
 for(k=0;k<8;k=k+1)begin:gcap
  ot_qwen_tp8_vrow_capture #(.LATENCY(3)) u_capture(
   .clk(clk),.rst_n(rst_n),.in_valid(v_rsp_valid[2*k+:2]),.in_slot(6'd0),.in_t(v_rsp_t[28*k+:28]),
   .in_epoch(v_rsp_epoch[32*k+:32]),.in_rows(v_rsp_data[2048*k+:2048]),
   .out_valid(cv[2*k+:2]),.out_slot(),.out_t(ct[28*k+:28]),.out_epoch(cep[32*k+:32]),.out_rows(crow[2048*k+:2048]));
 end endgenerate
 reg er_bad;
 integer ea;
 always @(posedge clk or negedge rst_n)if(!rst_n)er_bad<=0;
  else for(ea=0;ea<16;ea=ea+1)begin
   if(er_rsp_v[ea]!=cv[ea])er_bad<=1;
   if(cv[ea]&&er_rsp_addr[11*ea+:11]!={ct[14*ea+9+:4],ct[14*ea+:7]})er_bad<=1;
   if(er_rsp_v[ea]&&!dp_run)er_bad<=1;
  end
 generate for(s=0;s<2;s=s+1)begin:gp
  wire [7:0] bv;wire [8191:0] bvrow;wire [511:0] bexp;wire [111:0] bt;wire [127:0] bep;
  genvar k2;
  for(k2=0;k2<8;k2=k2+1)begin:gport
   localparam integer K=(k2<4)?4*s+k2:4*(s+2)+k2-4;
   assign bv[k2]=cv[K];assign bvrow[1024*k2+:1024]=crow[1024*K+:1024];assign bexp[64*k2+:64]=er_data[64*K+:64];
   assign bt[14*k2+:14]=ct[14*K+:14];assign bep[16*k2+:16]=cep[16*K+:16];
  end
  wire [7:0] rq;wire [111:0] rqt;
  assign v_req_valid[4*s+:4]=rq[3:0];assign v_req_valid[4*(s+2)+:4]=rq[7:4];
  assign v_req_t[56*s+:56]=rqt[55:0];assign v_req_t[56*(s+2)+:56]=rqt[111:56];
  reg rqbad;
  always @(posedge clk or negedge rst_n)if(!rst_n)rqbad<=0;
   else if(((rq[3:0]&~v_req_ready[4*s+:4])!=0)||((rq[7:4]&~v_req_ready[4*(s+2)+:4])!=0))rqbad<=1;
  assign vf[s]=rqbad;
  kvattn_rel_pv_bound #(.PAIR(s),.FIRST_INPUT_AGE(FIRST_INPUT_AGE),.MUT(0)) u_pv(.clk(clk),.rst_n(rst_n),
   .start(start_pv),.col_clk({33{clk}}),.context_len(pv_ctx),.epoch(pv_ep),
   .in_valid(bv),.in_v(bvrow),.in_e(bexp),.in_t(bt),.in_epoch(bep),.req_valid(rq),.req_t(rqt),
   .out_valid(pvalid[s]),.out_leaf(partial[16384*s+:16384]),.out_epoch(pep[16*s+:16]),.fault(pf[s]),
   .busy(),.out_age(pv_out_age[16*s+:16]));
  always @(posedge clk or negedge rst_n)if(!rst_n)vcount[s]<=0;else if(start_pv)vcount[s]<=0;else vcount[s]<=vcount[s]+32'($countones(bv));
 end endgenerate
 assign v_words=vcount[0]+vcount[1];
 assign pv_out_o=pvalid;
 // ---------------- final join and the 32-beat result emitter (-> fin) ----------------
 wire ff,fvalid;wire [16383:0] fout;wire [15:0] fepoch;
 reg [15:0] pv_age;reg pv_run;
 wire [15:0] LAST_CAPTURE=(P0_AGE>P1_AGE)?((P0_AGE>R_AGE)?P0_AGE:R_AGE):((P1_AGE>R_AGE)?P1_AGE:R_AGE);
 wire [15:0] FINAL_OUT_AGE=LAST_CAPTURE+16'd16;
 reg [15:0] c_fin_out;   // pv age of the final out_valid edge, captured at fin_start
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin pv_age<=0;pv_run<=0;c_fin_out<=0;end
  else if(fin_start)begin pv_age<=0;pv_run<=1;c_fin_out<=FINAL_OUT_AGE;end
  else if(pv_run)begin pv_age<=pv_age+1'b1;if(pv_age+1==c_fin_out+2)pv_run<=0;end
 reg [15:0] c_r;always @(posedge clk)if(fin_start)c_r<=R_AGE;
 wire r_slot=pv_run&&pv_age+1==c_r;
 wire [127:0] rz_final=rz_vector^((gmut[0])?128'd1:128'd0);
 ot_qwen_tp8_pv256_finalize_static_cal_8 u_final(.cal(pvfst[64:17]),
  .clk_control(clk),.clk_join({32{clk}}),.rst_n(rst_n),.start(fin_start),.epoch(fin_ep),
  .reciprocal(rz_final),.reciprocal_valid(r_slot),.reciprocal_ready(),.reciprocal_epoch(rz_epoch),
  .p0_valid(pvalid[0]),.p1_valid(pvalid[1]),.p0_ready(),.p1_ready(),.p0_epoch(pep[15:0]),.p1_epoch(pep[31:16]),
  .p0_partial(partial[16383:0]),.p1_partial(partial[32767:16384]),.out_valid(fvalid),.out_ready(1'b1),.out_data(fout),
  .out_epoch(fepoch),.fault(ff));
 assign final_out_o=fvalid;
 reg [16383:0] rbuf;reg [5:0] rbeat;reg emitting;reg result_fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin emitting<=0;rbeat<=0;result_fault<=0;rz_late<=0;end
  else begin
   if(r_slot&&!rz_published)rz_late<=1;
   if(fvalid!=(pv_run&&pv_age+1==c_fin_out))result_fault<=1;
   if(fvalid)begin rbuf<=fout;rbeat<=0;emitting<=1;if(fepoch!=fin_ep)result_fault<=1;end
   else if(emitting)begin
    rbuf<={512'd0,rbuf[16383:512]};rbeat<=rbeat+1'b1;
    if(rbeat==31)emitting<=0;
   end
  end
 end
 // fin = {data 512, epoch 16, beat 5, valid}; FIN_RLY (+ GMUT[1]) relay edges toward the tile face
 wire [533:0] fin0={rbuf[511:0],fin_ep,rbeat[4:0],emitting};
 reg [533:0] frly[0:8];
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin for(integer j=0;j<9;j=j+1)frly[j]<=0;end
  else begin frly[0]<=fin0;for(integer j=1;j<9;j=j+1)frly[j]<=frly[j-1];end
 wire [3:0] fsel=4'(FIN_RLY)+((gmut[1])?4'd1:4'd0);
 assign fin=(fsel==0)?fin0:frly[fsel-1];
 // ---------------- unit faults to the tile's fault root ----------------
 assign ufs=stack_fault|legacy_pv;
 assign ufh=hub_fault|rz_late;
 assign ufp0=pf[0]|vf[0];assign ufp1=pf[1]|vf[1];
 assign uff=ff|result_fault|er_bad;
 assign fault_cause={3'd0,rz_late,er_bad,result_fault,ff,|pf,|vf,hub_fault,|legacy_pv,|stack_fault,|kbad,stack_fault[2:0]};
endmodule
