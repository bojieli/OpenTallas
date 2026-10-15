`timescale 1ns/1ps
// Q-ATTN 2026-10-15: Qwen TP8 native attention service on a compiler-fixed cycle calendar.
//
// Composition of the actual native parts (no functional stack_h, no hub_p, no credit adapters):
//   4 x ot_qwen_tp8_attention_native_stack_cal (8 ECTL3 STATIC_QK + 32 nativehead_r4 + mapped ASTK, real SRAM macros)
//   ot_qkd_ahub_static_die_cal (4 ZH trees + reciprocal leaf, six roots)
//   2 x ot_qwen_tp8_vrow_static + ot_qwen_tp8_vrow_capture(LATENCY=3, actual EP ER3 read)
//   2 x ot_qwen_tp8_pv256_pair STATIC_SCHEDULE=1 TREE=1
//   ot_qwen_tp8_pv256_finalize_static_cal (32 join16 slices, ADD7/MUL6)
// (*_cal = generated calendar-input variants of the sealed masters, tools/qwen_attention_native/gen_astk_cal.py)
// All FP arithmetic is project RTL (no DPI). Every operation happens at an age (edges after the start_qk edge)
// fixed by parameters, i.e. by the compiler calendar. No credit counter, ready or completion signal moves any
// slot: availability/identity/latency are integrity checks that raise `fault` (sticky) and never stretch time.
// Off-chip boundary (HBM K/V rows) is the only modeled side: responses must arrive exactly K_EXT/V_EXT edges after
// their request, which is checked here and inside the ECTL/vrow leaves.
// The calendar (all T-dependent start ages) is compiled per command and carried with it on request_calendar
// (tools/qwen_attention_native/calendar.py); the leaves capture it on their start edge. Common-phase clocks:
// all native clock roots are driven from clk; this is NOT a physical clock-phase qualification.
module ot_qwen_tp8_attention_native_service #(
 // boundary geometry (cycle naming: request visible in cycle i -> response presented in cycle i+EXT)
 parameter integer K_EXT=16, V_EXT=16,
 // ECTL3 QK
 parameter integer QK_ISSUE_AGE=34,
 parameter integer Z_STRIDE=16,
 // diagnostic mutant: 1 = flip LSB of head0 reciprocal inside the DUT
 parameter integer DMUT=0
) (
 input wire clk,rst_n,
 input wire request_valid,output wire request_ready,
 input wire [15:0] request_epoch,input wire [5:0] request_layer,
 input wire [17:0] request_position,input wire fused_program_capability,
 // compiler calendar, 11 x 16 b: {R, P1, P0 (after start_pv), PV_START, HUB_PUBLISH, HUB_RECIP_ISSUE, HUB_Z_START,
 //  HUB_LMAX_ISSUE, ASTK_Z_START, ASTK_LMAX_START, ASTK_EXP_BASE}; ages are edges after start_qk / leaf start
 input wire [175:0] request_calendar,
 input wire q_valid,output wire q_ready,input wire [4:0] q_beat,input wire [511:0] q_data,
 output wire [31:0] k_req_valid,input wire [31:0] k_req_ready,
 output wire [415:0] k_req_t,output wire [15:0] active_epoch,output wire [5:0] active_layer,
 input wire [31:0] k_rsp_valid,input wire [415:0] k_rsp_t,
 input wire [511:0] k_rsp_epoch,input wire [191:0] k_rsp_layer,input wire [32767:0] k_rsp_data,
 output wire [3:0] v_req_valid,input wire [3:0] v_req_ready,
 output wire [55:0] v_req_t,output wire [11:0] v_req_slot,
 input wire [3:0] v_rsp_valid,output wire [3:0] v_rsp_ready,
 input wire [55:0] v_rsp_t,input wire [11:0] v_rsp_slot,
 input wire [63:0] v_rsp_epoch,input wire [23:0] v_rsp_layer,input wire [4095:0] v_rsp_data,
 output wire result_valid,input wire result_ready,output wire [4:0] result_beat,
 output wire [511:0] result_data,output wire [15:0] result_epoch,output wire [5:0] result_layer,
 output reg result_done,output wire busy,output wire fault,
 output reg [31:0] cycles,output wire [31:0] k_words,v_words,
 output wire [15:0] fault_cause
);
 localparam integer V_RL=V_EXT+3;                 // external + actual EP ER3 capture
 localparam integer FIRST_INPUT_AGE=129+V_RL;      // pair-local age of the first V row slot
 reg [175:0] cal;
 wire [15:0] EXP_START_AGE=cal[15:0],LMAX_START_AGE=cal[31:16],Z_START_AGE=cal[47:32];
 wire [15:0] HUB_LMAX_ISSUE_AGE=cal[63:48],HUB_Z_START_AGE=cal[79:64],HUB_RECIP_ISSUE_AGE=cal[95:80],HUB_RZ_PUBLISH_AGE=cal[111:96];
 wire [15:0] PV_START_AGE=cal[127:112],P0_AGE=cal[143:128],P1_AGE=cal[159:144],R_AGE=cal[175:160];
 wire [15:0] LAST_CAPTURE=(P0_AGE>P1_AGE)?((P0_AGE>R_AGE)?P0_AGE:R_AGE):((P1_AGE>R_AGE)?P1_AGE:R_AGE);
 wire [15:0] FINAL_OUT_AGE=LAST_CAPTURE+16'd16;             // ot_qwen_tp8_pv_join16_static_cal OUT_AGE
 wire [15:0] RESULT_AGE=PV_START_AGE+FINAL_OUT_AGE;         // start_qk age of the final out_valid edge
 wire [15:0] END_AGE=RESULT_AGE+16'd33;
 localparam integer ROW_RETURN_LAT=K_EXT+6;   // ECTL tb geometry: L=3 <-> ROW_RETURN_LAT=9

 // ---------------- fixed calendar control ----------------
 reg [6:0] boot_count;
 reg running,start_qk,start_pv;
 reg [15:0] age;           // age 0 = the cycle in which start_qk is high
 reg [15:0] ep;reg [5:0] layer;reg [13:0] ctx;
 reg local_fault,io_fault,result_fault;
 assign request_ready=!running&&boot_count==80;
 assign busy=running;
 assign active_epoch=ep;assign active_layer=layer;
 wire q_window=running&&!start_qk&&age>=1&&age<=32;
 assign q_ready=q_window;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin boot_count<=0;running<=0;start_qk<=0;start_pv<=0;age<=0;ep<=0;layer<=0;ctx<=0;cal<=0;
   local_fault<=0;io_fault<=0;cycles<=0;end
  else begin
   start_qk<=0;start_pv<=0;
   if(boot_count<80)boot_count<=boot_count+1'b1;
   if(running)begin age<=age+1'b1;cycles<=cycles+1;end
   if(running&&age+1==PV_START_AGE)start_pv<=1;
   if(running&&age+1==END_AGE)running<=0;
   if(request_valid&&!request_ready)io_fault<=1;
   if(q_valid!=q_window)io_fault<=1;
   if(q_window&&q_valid&&q_beat!=5'(age-1))io_fault<=1;
   if(request_valid&&request_ready)begin
    if(!fused_program_capability||request_position>8191)local_fault<=1;
    ep<=request_epoch;layer<=request_layer;ctx<=14'(request_position+1);cal<=request_calendar;
    running<=1;start_qk<=1;age<=0;cycles<=0;
   end
  end
 end

 // ---------------- per stack: native QK stack, K boundary, held command context ----------------
 wire [3:0] stack_fault;
 wire [2251:0] ap_all;          // 4 x 563
 wire [143:0] hub_am;
 wire [3:0] er_v;wire [43:0] er_addr;
 wire [3:0] er_rsp_v;wire [43:0] er_rsp_addr;wire [255:0] er_data;
 wire [63:0] exp_committed;wire [3:0] score_committed;
 wire [31:0] dbg;wire [31:0] kbad;reg [31:0] kcount[0:31];
 // Q enters the actual ASTK ctl pins: {q_data 512, q_beat 6, rsv 6, q_valid, rsv, ...}
 wire [539:0] aq;
 assign aq[0]=start_qk;assign aq[14:1]=ctx;assign aq[20:15]=6'd0;
 assign aq[21]=q_window&&q_valid;assign aq[27:22]={1'b0,q_beat};assign aq[539:28]=q_data;
 genvar s,e;
 generate for(s=0;s<4;s=s+1)begin:gs
  wire [135:0] k_request;wire [8199:0] k_response;
  wire [35:0] am_s={hub_am[36*s+:32],hub_am[36*s+32+:2],hub_am[36*s+34],hub_am[36*s+35]};
  ot_qwen_tp8_attention_native_stack_cp #(.STACK(s),.QK_ISSUE_AGE(QK_ISSUE_AGE),.ROW_RETURN_LAT(ROW_RETURN_LAT),
   .Z_STRIDE(Z_STRIDE)) u_stack(
   .cal(cal[47:0]),.clk(clk),.rst_n(rst_n),.aq(aq),.am(am_s),.ap(ap_all[563*s+:563]),.active_layer_parity(layer[0]),
   .k_request(k_request),.k_response(k_response),
   .er_v(er_v[s]),.er_addr(er_addr[11*s+:11]),.er_rsp_v(er_rsp_v[s]),.er_rsp_addr(er_rsp_addr[11*s+:11]),
   .er_data(er_data[64*s+:64]),.exp_committed(exp_committed[16*s+:16]),.score_committed(score_committed[s]),
   .fault(stack_fault[s]),.dbg(dbg[8*s+:8]));
  for(e=0;e<8;e=e+1)begin:ge
   localparam integer I=8*s+e;
   wire [16:0] rq=k_request[17*e+:17];
   assign k_req_valid[I]=rq[0];
   assign k_req_t[13*I+:13]=rq[15:3];
   // fixed-latency return identity: rq visible in cycle X is in stage j during cycle X+1+j, so the response
   // presented in cycle X+K_EXT is checked against stage K_EXT-1.
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
 // the stack ap register is sampled by the hub two edges after the stack-local slot (start skew + pin flop)
 wire [15:0] LIN=LMAX_START_AGE+16'd2,ZIN=Z_START_AGE+16'd2;
 ot_qkd_ahub_static_die_cal #(.Z_IN_STRIDE(Z_STRIDE),.Z_LEVEL_GAP(10),.ZW_RLY(0),.ZR_RLY(0),.RX_RLY(1),.RY_RLY(1)) u_hub(
  .cal({HUB_RZ_PUBLISH_AGE,HUB_RECIP_ISSUE_AGE,HUB_Z_START_AGE,HUB_LMAX_ISSUE_AGE,ZIN,ZIN,ZIN,ZIN,LIN,LIN,LIN,LIN}),
  .ck_core(clk),.ck_recip(clk),.ck_zh({4{clk}}),.rst_n(rst_n),.start(start_qk),.active_layer_parity(layer[0]),
  .request_epoch(ep),.active_layer(layer),.T(ctx),
  .si_valid(si_valid),.si_g(si_g),.si_any(si_any),.si_epoch(held_epoch),.si_layer(held_layer),.si_type(si_type),.si_hh(si_hh),
  .si_k(si_k),.si_data(si_data),.am(hub_am),.rz_valid(rz_valid),.rz_head(rz_head),.rz_data(rz_data),.rz_epoch(rz_epoch),
  .rz_publish(rz_publish),.rz_vector(rz_vector),.fault(hub_fault));
 reg rz_published;reg rz_late;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin rz_published<=0;end
  else if(start_qk)rz_published<=0;else if(rz_publish)rz_published<=1;

 // ---------------- V rows, actual EP e read, static PV pairs ----------------
 wire [1:0] vf,pf,vdone;wire [1:0] pvalid;wire [32767:0] partial;wire [31:0] pep;
 reg [31:0] vcount[0:1];
 assign v_rsp_ready=4'hf;   // static: the slot is reserved; an unexpected return is a fault inside vrow_static
 generate for(s=0;s<2;s=s+1)begin:gp
  wire [2:0] slot;wire [13:0] req_t;wire [15:0] req_ep;
  wire ov,first,last;wire [1023:0] vdata;wire [63:0] expdata;wire [13:0] ot;wire [15:0] oep;
  wire [1:0] rv;wire [5:0] slots;wire [27:0] ts;wire [31:0] eps;wire [2047:0] rows;
  // the actual ASTK EP e-quad read is issued on the V return edge (fixed slot), address {block, row}
  assign er_v[s]=v_rsp_valid[s];assign er_v[s+2]=v_rsp_valid[s+2];
  assign er_addr[11*s+:11]={v_rsp_t[14*s+9+:4],v_rsp_t[14*s+:7]};
  assign er_addr[11*(s+2)+:11]={v_rsp_t[14*(s+2)+9+:4],v_rsp_t[14*(s+2)+:7]};
  ot_qwen_tp8_vrow_capture #(.LATENCY(3)) u_capture(
   .clk(clk),.rst_n(rst_n),.in_valid({v_rsp_valid[s+2],v_rsp_valid[s]}),
   .in_slot({v_rsp_slot[3*(s+2)+:3],v_rsp_slot[3*s+:3]}),
   .in_t({v_rsp_t[14*(s+2)+:14],v_rsp_t[14*s+:14]}),
   .in_epoch({v_rsp_epoch[16*(s+2)+:16],v_rsp_epoch[16*s+:16]}),
   .in_rows({v_rsp_data[1024*(s+2)+:1024],v_rsp_data[1024*s+:1024]}),
   .out_valid(rv),.out_slot(slots),.out_t(ts),.out_epoch(eps),.out_rows(rows));
  assign v_req_slot[3*s+:3]=slot;assign v_req_slot[3*(s+2)+:3]=slot;
  assign v_req_t[14*s+:14]=req_t;assign v_req_t[14*(s+2)+:14]=req_t;
  ot_qwen_tp8_vrow_static #(.PAIR(s),.RETURN_LATENCY(V_RL)) u_merge(.clk(clk),.rst_n(rst_n),.start(start_pv),.context_len(ctx),.epoch(ep),
   .lo_req_valid(v_req_valid[s]),.hi_req_valid(v_req_valid[s+2]),.lo_req_ready(v_req_ready[s]),.hi_req_ready(v_req_ready[s+2]),
   .req_slot(slot),.req_t(req_t),.req_epoch(req_ep),
   .lo_rsp_valid(rv[0]),.hi_rsp_valid(rv[1]),
   .lo_rsp_slot(slots[2:0]),.hi_rsp_slot(slots[5:3]),.lo_rsp_t(ts[13:0]),.hi_rsp_t(ts[27:14]),.lo_rsp_epoch(eps[15:0]),.hi_rsp_epoch(eps[31:16]),
   .lo_vrow(rows[1023:0]),.hi_vrow(rows[2047:1024]),.lo_exp(er_data[64*s+:64]),.hi_exp(er_data[64*(s+2)+:64]),
   .out_valid(ov),.out_ready(1'b1),.out_vrow(vdata),.out_exp(expdata),.out_t(ot),.out_epoch(oep),.out_first(first),.out_last(last),
   .done(vdone[s]),.fault(vf[s]));
  ot_qwen_tp8_pv256_pair #(.PAIR(s),.TREE(1),.STATIC_SCHEDULE(1),.FIRST_INPUT_AGE(FIRST_INPUT_AGE)) u_pv(.clk(clk),.rst_n(rst_n),
   .start(start_pv),.slice_clk({32{clk}}),.context_len(ctx),.epoch(ep),
   .in_valid(ov),.in_ready(),.in_v(vdata),.in_e(expdata),.in_c(ot[6:0]),.in_t(ot),.in_epoch(oep),.in_first(first),.in_last(last),
   .out_valid(pvalid[s]),.out_ready(1'b1),.out_leaf(partial[16384*s+:16384]),.out_c(),.out_epoch(pep[16*s+:16]),.fault(pf[s]),
   .busy(),.accepted(),.committed(),.peak_inflight());
  always @(posedge clk or negedge rst_n)if(!rst_n)vcount[s]<=0;else if(start_pv)vcount[s]<=0;else if(ov)vcount[s]<=vcount[s]+1;
 end endgenerate
 assign v_words=vcount[0]+vcount[1];
 // e-read identity: the actual ER3 response must carry the address issued three edges earlier
 reg er_bad;
 always @(posedge clk or negedge rst_n)if(!rst_n)er_bad<=0;
  else for(integer a=0;a<4;a=a+1)if(er_rsp_v[a]&&!running)er_bad<=1;

 // ---------------- final join (fixed capture slots) and fixed result emission ----------------
 wire ff,fvalid;wire [16383:0] fout;wire [15:0] fepoch;
 reg [15:0] pv_age;reg pv_run;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin pv_age<=0;pv_run<=0;end
  else if(start_pv)begin pv_age<=0;pv_run<=1;end
  else if(pv_run)begin pv_age<=pv_age+1'b1;if(pv_age+1==FINAL_OUT_AGE+2)pv_run<=0;end
 wire r_slot=pv_run&&pv_age+1==R_AGE;
 wire [127:0] rz_final=rz_vector^((DMUT==1)?128'd1:128'd0);
 ot_qwen_tp8_pv256_finalize_static_cal u_final(.cal({R_AGE,P1_AGE,P0_AGE}),
  .clk_control(clk),.clk_join({32{clk}}),.rst_n(rst_n),.start(start_pv),.epoch(ep),
  .reciprocal(rz_final),.reciprocal_valid(r_slot),.reciprocal_ready(),.reciprocal_epoch(rz_epoch),
  .p0_valid(pvalid[0]),.p1_valid(pvalid[1]),.p0_ready(),.p1_ready(),.p0_epoch(pep[15:0]),.p1_epoch(pep[31:16]),
  .p0_partial(partial[16383:0]),.p1_partial(partial[32767:16384]),.out_valid(fvalid),.out_ready(1'b1),.out_data(fout),
  .out_epoch(fepoch),.fault(ff));
 reg [16383:0] rbuf;reg [5:0] rbeat;reg emitting;
 assign result_valid=emitting;assign result_beat=rbeat[4:0];assign result_data=rbuf[511:0];
 assign result_epoch=ep;assign result_layer=layer;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin emitting<=0;rbeat<=0;result_done<=0;result_fault<=0;rz_late<=0;end
  else begin
   result_done<=0;
   if(r_slot&&!rz_published)rz_late<=1;
   if(fvalid!=(running&&age+1==RESULT_AGE+1))result_fault<=1;
   if(fvalid)begin rbuf<=fout;rbeat<=0;emitting<=1;if(fepoch!=ep)result_fault<=1;end
   else if(emitting)begin
    if(!result_ready)result_fault<=1;
    rbuf<={512'd0,rbuf[16383:512]};rbeat<=rbeat+1'b1;
    if(rbeat==31)begin emitting<=0;result_done<=1;end
   end
  end
 end
 assign fault_cause={rz_late,er_bad,result_fault,ff,|pf,|vf,hub_fault,|legacy_pv,|stack_fault,|kbad,io_fault,local_fault,stack_fault};
 assign fault=|fault_cause;
endmodule

// Common-phase stack entry: the actual native stack with every one of its 2822 clock roots driven from one clk.
// Functional/arithmetic composition only; per-root insertion/phase binding belongs to the KV die clock contract.
// Also the simulator hierarchy cut (one clock port), see tools/qwen_attention_native/native_service.vlt.
module ot_qwen_tp8_attention_native_stack_cp #(
 parameter integer STACK=0,QK_ISSUE_AGE=34,ROW_RETURN_LAT=9,Z_STRIDE=4
)(
 input wire [47:0] cal,
 input wire clk,rst_n,input wire[539:0] aq,input wire[35:0] am,output wire[562:0] ap,input wire active_layer_parity,
 output wire[135:0] k_request,input wire[8199:0] k_response,
 input wire er_v,input wire[10:0] er_addr,output wire er_rsp_v,output wire[10:0] er_rsp_addr,output wire[63:0] er_data,
 output wire[15:0] exp_committed,output wire score_committed,output wire fault,
 output wire[7:0] dbg   // calendar observation taps only
);
 assign dbg={3'd0,u_native.u_astk.cq[536],u_native.u_astk.ep_so[0],u_native.u_astk.cq[534],u_native.u_astk.score_committed,u_native.so[13]};
 ot_qwen_tp8_attention_native_stack_cal #(.STACK(STACK),.RL(1),.QK_ISSUE_AGE(QK_ISSUE_AGE),.ROW_RETURN_LAT(ROW_RETURN_LAT),
  .Z_STRIDE(Z_STRIDE)) u_native(
  .cal(cal),.rst_n(rst_n),.ck_astk_c(clk),.ck_astk_r(clk),.ck_astk_z({4{clk}}),.ck_astk_x({32{clk}}),.ck_astk_e({8{clk}}),
  .ck_ectl({24{clk}}),.ck_head({2752{clk}}),
  .aq(aq),.am(am),.ap(ap),.active_layer_parity(active_layer_parity),.k_request(k_request),.k_response(k_response),
  .er_v(er_v),.er_addr(er_addr),.er_rsp_v(er_rsp_v),.er_rsp_addr(er_rsp_addr),.er_data(er_data),
  .exp_committed(exp_committed),.score_committed(score_committed),.fault(fault));
endmodule
