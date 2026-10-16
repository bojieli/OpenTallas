`timescale 1ns/1ps
`ifndef KVD_HEADS
`define KVD_HEADS 2
`endif
`ifndef KVD_Q_FP32
`define KVD_Q_FP32 0
`endif
`ifndef KVD_QK_ONLY
`define KVD_QK_ONLY 0
`endif
// DEFAULT-OFF native arithmetic service. Build with KVD_HEADS=1,KVD_Q_FP32=1,
// KVD_QK_ONLY=1,KVD_ECTL3. Common-clock adapter is functional evidence only;
// it is not a routed clock contract or a qualified HBM timing model.
// Requires the explicitly source-bound fused program capability. Does not commit VM.
module ot_qwen_tp8_attention_service #(
 // Historical arbitrary-stall transport remains diagnostic only. Static K
 // mode requires its implemented return geometry in the compiler calendar;
 // V transport and phase scheduling must also qualify before native adoption.
 parameter integer STATIC_IO_TIMING=0,
 parameter integer STATIC_K_TRANSPORT=0,
 parameter integer K_RETURN_LATENCY=16,
 parameter integer STATIC_V_TRANSPORT=0,
 parameter integer E_READ_LATENCY=1,
 parameter integer V_RETURN_LATENCY=16+E_READ_LATENCY
) (
 input wire clk,rst_n,
 input wire request_valid,output wire request_ready,
 input wire [15:0] request_epoch,input wire [5:0] request_layer,
 input wire [17:0] request_position,input wire fused_program_capability,
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
 output reg [31:0] cycles,output wire [31:0] k_words,v_words
);
 localparam IDLE=0,QLOAD=1,QK=2,PVSTART=3,PV=4,EMIT=5,BAD=6,RELEASE=7;
 reg [2:0] state;reg start_qk,start_pv;reg [15:0] ep;reg [5:0] layer;
 reg [6:0] boot_count;
 reg [511:0] result_face;
 reg [13:0] ctx;reg [5:0] qnext;reg [4:0] beat;reg local_fault,cleared;
 wire [31:0] raw_req,raw_v,raw_g,checked_rsp,kbad;wire [415:0] raw_t;
 wire [3:0] sf,scdone,nonempty,exp_ready;wire [63:0] edone;wire [255:0] edata;wire [43:0] eaddr;
 wire [3:0] eread;wire [3:0] sv,sg,sa,pv_dummy,pg_dummy;
 wire [7:0] st,sh;wire [15:0] sk;wire [127:0] sd;
 wire mv,mg,hf,rzok;wire [1:0] mh;wire [31:0] md;wire [127:0] rz;
 wire [3:0] vbad;
 wire [1:0] vf,pf,vdone;wire ff,fvalid;wire [16383:0] fout;wire [15:0] fepoch;
 wire fready=state==EMIT&&result_ready&&beat==31;
 wire [31:0] kc[0:31];wire [31:0] vc[0:1];
 assign request_ready=state==IDLE&&!fault&&boot_count==80;
 assign busy=state!=IDLE;assign active_epoch=ep;assign active_layer=layer;
 assign result_epoch=ep;assign result_layer=layer;assign result_beat=beat;
 assign result_valid=state==EMIT&&fvalid&&!fault;
 assign result_data=result_face;
 assign q_ready=state==QLOAD&&!start_qk&&!fault;
 assign fault=local_fault|(|sf)|hf|(|kbad)|(|vbad)|(|vf)|(|pf)|ff;
 integer n;reg [31:0] ksum,vsum;
 always @*begin ksum=0;vsum=0;for(integer x=0;x<32;x=x+1)ksum=ksum+kc[x];for(integer x=0;x<2;x=x+1)vsum=vsum+vc[x];end
 assign k_words=ksum;assign v_words=vsum;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;start_qk<=0;start_pv<=0;ep<=0;layer<=0;ctx<=1;boot_count<=0;qnext<=0;beat<=0;result_face<=0;local_fault<=0;cleared<=0;cycles<=0;result_done<=0;end
  else begin
   start_qk<=0;start_pv<=0;result_done<=0;
   if(boot_count<80)boot_count<=boot_count+1'b1;
   if(busy)cycles<=cycles+1;
   if(STATIC_IO_TIMING)begin
    // A compiler command is followed by one arm edge, then exactly32 Q beats.
    // Interface availability is checked, never used to shift these slots.
    if(request_valid&&!request_ready)local_fault<=1;
    if((q_valid!=(state==QLOAD&&!start_qk)) || (result_valid&&!result_ready))local_fault<=1;
   end
   if(fault)state<=BAD;
   else case(state)
    IDLE:if(request_valid&&request_ready)begin
     if(!fused_program_capability||request_position>8191||`KVD_HEADS!=1||!`KVD_Q_FP32||!`KVD_QK_ONLY)begin local_fault<=1;state<=BAD;end
     else begin ep<=request_epoch;layer<=request_layer;ctx<=request_position+1'b1;qnext<=0;beat<=0;cleared<=0;cycles<=0;start_qk<=1;state<=QLOAD;end
    end
    QLOAD:begin
     if(!( |(scdone&nonempty))&&!rzok)cleared<=1;
     if(q_valid&&q_ready)begin
      if(q_beat!=qnext[4:0])begin local_fault<=1;state<=BAD;end
      else if(qnext==31)state<=QK;
      else qnext<=qnext+1'b1;
     end
    end
    QK:if(cleared&&(&scdone)&&(&exp_ready)&&rzok)begin start_pv<=1;state<=PVSTART;end
    PVSTART:state<=PV;
    PV:if(fvalid)begin
     if(fepoch!=ep)begin local_fault<=1;state<=BAD;end
     else begin state<=EMIT;beat<=0;result_face<=fout[511:0];end
    end
    EMIT:if(result_valid&&result_ready)begin if(beat==31)begin result_done<=1;state<=RELEASE;end else begin beat<=beat+1'b1;result_face<=fout[512*(beat+1)+:512];end end
    RELEASE:if(!fvalid)state<=IDLE;
    default:;
   endcase
  end
 end
 genvar s,e;
 generate for(s=0;s<4;s=s+1)begin:gs
  wire [13:0] base=128*s;
  wire [13:0] tail={5'd0,ctx[8:0]};
  wire [13:0] part=tail>base ? (tail-base>128 ? 14'd128 : tail-base) : 14'd0;
  wire [11:0] owned={ctx[13:9],7'd0}+part[11:0];
  wire [4:0] groups=owned>=128 ? 5'd16 : ((owned+7)>>3);
  wire [15:0] exp_mask=(17'd1<<groups)-1'b1;
  assign nonempty[s]=owned!=0;
  assign exp_ready[s]=(edone[16*s+:16]&exp_mask)==exp_mask;
  wire [31:0] unused_ev;wire [1:0] unused_done;wire [5:0] unused_pb;wire [511:0] unused_pd;
  ot_qwen_nearhbm_attn_stack_h #(.S(s),.R(8),.DQ(128)) u_h (
   .clk(clk),.rst_n(rst_n),.start(start_qk),.T(ctx),.q_valid(q_valid&&q_ready&&q_beat==qnext[4:0]),.q_beat({1'b0,q_beat}),.q_data(q_data),
   .req_valid(raw_req[8*s+:8]),.req_v(raw_v[8*s+:8]),.req_g(raw_g[8*s+:8]),.req_t(raw_t[104*s+:104]),
   .rsp_valid(checked_rsp[8*s+:8]),.rsp_data(k_rsp_data[8192*s+:8192]),
   .mi_valid(mv),.mi_g(mg),.mi_hh(mh),.mi_data(md),
   .so_valid(sv[s]),.so_type(st[2*s+:2]),.so_g(sg[s]),.so_hh(sh[2*s+:2]),.so_k(sk[4*s+:4]),.so_any(sa[s]),.so_data(sd[32*s+:32]),
   .pv_valid(pv_dummy[s]),.pv_g(pg_dummy[s]),.pv_beat(unused_pb),.pv_data(unused_pd),.pv_done(unused_done),.fault(sf[s]),.ev(unused_ev[15:0]),
   .native_e_read(eread[s]),.native_e_addr(eaddr[11*s+:11]),.native_e_data(edata[64*s+:64]),.native_exp_done(edone[16*s+:16]),.native_score_done(scdone[s]));
  for(e=0;e<8;e=e+1)begin:ge
   localparam I=s*8+e;
   if(STATIC_K_TRANSPORT)begin:gstatic
   ot_qwen_tp8_k_request_static #(.RETURN_LATENCY(K_RETURN_LATENCY)) u_req(.clk(clk),.rst_n(rst_n),.start(start_qk),.epoch(ep),.layer(layer),
    .raw_valid(raw_req[I]),.raw_t(raw_t[13*I+:13]),.raw_wrong_type(raw_v[I]|raw_g[I]),
    .req_valid(k_req_valid[I]),.req_ready(k_req_ready[I]),.req_t(k_req_t[13*I+:13]),
    .rsp_valid(k_rsp_valid[I]),.rsp_t(k_rsp_t[13*I+:13]),.rsp_epoch(k_rsp_epoch[16*I+:16]),.rsp_layer(k_rsp_layer[6*I+:6]),
    .checked_rsp(checked_rsp[I]),.fault(kbad[I]),.accepted(kc[I]));
   end else begin:ghistorical
   ot_qwen_tp8_k_request_adapter u_req(.clk(clk),.rst_n(rst_n),.start(start_qk),.epoch(ep),.layer(layer),
    .raw_valid(raw_req[I]),.raw_t(raw_t[13*I+:13]),.raw_wrong_type(raw_v[I]|raw_g[I]),
    .req_valid(k_req_valid[I]),.req_ready(k_req_ready[I]),.req_t(k_req_t[13*I+:13]),
    .rsp_valid(k_rsp_valid[I]),.rsp_t(k_rsp_t[13*I+:13]),.rsp_epoch(k_rsp_epoch[16*I+:16]),.rsp_layer(k_rsp_layer[6*I+:6]),
    .checked_rsp(checked_rsp[I]),.fault(kbad[I]),.accepted(kc[I]));
   end
  end
 end endgenerate
 ot_qwen_nearhbm_attn_hub_p #(.HEADS(1)) u_hub(.clk(clk),.rst_n(rst_n),.start(start_qk),
  .si_valid(sv),.si_type(st),.si_g(sg),.si_hh(sh),.si_k(sk),.si_any(sa),.si_data(sd),
  .pi_valid(4'd0),.pi_g(4'd0),.pi_beat(24'd0),.pi_data(2048'd0),
  .mo_valid(mv),.mo_g(mg),.mo_hh(mh),.mo_data(md),.out_valid(),.out_g(),.out_beat(),.out_data(),.fault(hf),.ev(),
  .native_reciprocal(rz),.native_rz_ok(rzok));
 wire [1:0] pvalid,pready;wire [32767:0] partial;wire [31:0] pep;wire rr;
 generate for(s=0;s<2;s=s+1)begin:gp
  wire want_ready;reg [13:0] want_t;reg want_run;
  wire [2:0] slot;wire [13:0] req_t;wire [15:0] req_ep;
  wire ov,ordy,first,last;wire [1023:0] vdata;wire [63:0] expdata;wire [13:0] ot;wire [15:0] oep;
  wire [1:0] rv;wire [5:0] slots;wire [27:0] ts;wire [31:0] eps;wire [2047:0] rows;
  wire [1:0] rsp_good;
  wire [1:0] rsp_ready;
  assign v_rsp_ready[s]=rsp_ready[0]&&state==PV&&!fault;
  assign v_rsp_ready[s+2]=rsp_ready[1]&&state==PV&&!fault;
  assign rsp_good[0]=v_rsp_epoch[16*s+:16]==ep&&v_rsp_layer[6*s+:6]==layer;
  assign rsp_good[1]=v_rsp_epoch[16*(s+2)+:16]==ep&&v_rsp_layer[6*(s+2)+:6]==layer;
  assign eread[s]=v_rsp_valid[s]&&v_rsp_ready[s]&&rsp_good[0];
  assign eread[s+2]=v_rsp_valid[s+2]&&v_rsp_ready[s+2]&&rsp_good[1];
  assign eaddr[11*s+:11]={v_rsp_t[14*s+9+:4],v_rsp_t[14*s+:7]};
  assign eaddr[11*(s+2)+:11]={v_rsp_t[14*(s+2)+9+:4],v_rsp_t[14*(s+2)+:7]};
  reg bad0,bad1;assign vbad[s]=bad0;assign vbad[s+2]=bad1;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin bad0<=0;bad1<=0;end
   else begin
    if(v_rsp_valid[s]&&((v_rsp_ready[s]&&!rsp_good[0])||(STATIC_V_TRANSPORT&&!v_rsp_ready[s])))bad0<=1;
    if(v_rsp_valid[s+2]&&((v_rsp_ready[s+2]&&!rsp_good[1])||(STATIC_V_TRANSPORT&&!v_rsp_ready[s+2])))bad1<=1;
   end
  end
  // Native ASTK EP reads take3 edges; the historical functional profile1.
  // E_READ_LATENCY must match the actually instantiated memory service.
  ot_qwen_tp8_vrow_capture #(.LATENCY(E_READ_LATENCY)) u_capture(
   .clk(clk),.rst_n(rst_n),.in_valid({eread[s+2],eread[s]}),
   .in_slot({v_rsp_slot[3*(s+2)+:3],v_rsp_slot[3*s+:3]}),
   .in_t({v_rsp_t[14*(s+2)+:14],v_rsp_t[14*s+:14]}),
   .in_epoch({v_rsp_epoch[16*(s+2)+:16],v_rsp_epoch[16*s+:16]}),
   .in_rows({v_rsp_data[1024*(s+2)+:1024],v_rsp_data[1024*s+:1024]}),
   .out_valid(rv),.out_slot(slots),.out_t(ts),.out_epoch(eps),.out_rows(rows));
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin want_t<=0;want_run<=0;end
   else if(start_pv)begin want_t<=s*128;want_run<=ctx>s*128;end
   else if(want_run&&want_ready)begin
    if(want_t[6:0]==127)begin if(want_t+129>=ctx)want_run<=0;else want_t<=want_t+129;end
    else if(want_t+1>=ctx)want_run<=0;else want_t<=want_t+1'b1;
   end
  end
  assign v_req_slot[3*s+:3]=slot;assign v_req_slot[3*(s+2)+:3]=slot;
  assign v_req_t[14*s+:14]=req_t;assign v_req_t[14*(s+2)+:14]=req_t;
  if(STATIC_V_TRANSPORT)begin:gstatic
   assign rsp_ready=2'b11;assign want_ready=1'b0;
  ot_qwen_tp8_vrow_static #(.PAIR(s),.RETURN_LATENCY(V_RETURN_LATENCY)) u_merge(.clk(clk),.rst_n(rst_n),.start(start_pv),.context_len(ctx),.epoch(ep),
   .lo_req_valid(v_req_valid[s]),.hi_req_valid(v_req_valid[s+2]),.lo_req_ready(v_req_ready[s]),.hi_req_ready(v_req_ready[s+2]),.req_slot(slot),.req_t(req_t),.req_epoch(req_ep),
   .lo_rsp_valid(rv[0]),.hi_rsp_valid(rv[1]),
   .lo_rsp_slot(slots[2:0]),.hi_rsp_slot(slots[5:3]),.lo_rsp_t(ts[13:0]),.hi_rsp_t(ts[27:14]),.lo_rsp_epoch(eps[15:0]),.hi_rsp_epoch(eps[31:16]),
   .lo_vrow(rows[1023:0]),.hi_vrow(rows[2047:1024]),.lo_exp(edata[64*s+:64]),.hi_exp(edata[64*(s+2)+:64]),
   .out_valid(ov),.out_ready(ordy),.out_vrow(vdata),.out_exp(expdata),.out_t(ot),.out_epoch(oep),.out_first(first),.out_last(last),.done(vdone[s]),.fault(vf[s]));
  end else begin:ghistorical
  ot_qwen_tp8_vrow_merge #(.PAIR(s)) u_merge(.clk(clk),.rst_n(rst_n),.start(start_pv),.context_len(ctx),.epoch(ep),
   .want_valid(want_run),.want_ready(want_ready),.want_t(want_t),
   .lo_req_valid(v_req_valid[s]),.hi_req_valid(v_req_valid[s+2]),.lo_req_ready(v_req_ready[s]),.hi_req_ready(v_req_ready[s+2]),.req_slot(slot),.req_t(req_t),.req_epoch(req_ep),
   .lo_rsp_valid(rv[0]),.hi_rsp_valid(rv[1]),.lo_rsp_ready(rsp_ready[0]),.hi_rsp_ready(rsp_ready[1]),
   .lo_rsp_slot(slots[2:0]),.hi_rsp_slot(slots[5:3]),.lo_rsp_t(ts[13:0]),.hi_rsp_t(ts[27:14]),.lo_rsp_epoch(eps[15:0]),.hi_rsp_epoch(eps[31:16]),
   .lo_vrow(rows[1023:0]),.hi_vrow(rows[2047:1024]),.lo_exp(edata[64*s+:64]),.hi_exp(edata[64*(s+2)+:64]),
   .out_valid(ov),.out_ready(ordy),.out_vrow(vdata),.out_exp(expdata),.out_t(ot),.out_epoch(oep),.out_first(first),.out_last(last),.done(vdone[s]),.fault(vf[s]));
  end
  ot_qwen_tp8_pv256_pair #(.PAIR(s),.TREE(1)) u_pv(.clk(clk),.rst_n(rst_n),.start(start_pv),.slice_clk({32{clk}}),.context_len(ctx),.epoch(ep),
   .in_valid(ov),.in_ready(ordy),.in_v(vdata),.in_e(expdata),.in_c(ot[6:0]),.in_t(ot),.in_epoch(oep),.in_first(first),.in_last(last),
   .out_valid(pvalid[s]),.out_ready(pready[s]),.out_leaf(partial[16384*s+:16384]),.out_c(),.out_epoch(pep[16*s+:16]),.fault(pf[s]),.busy(),.accepted(vc[s]),.committed(),.peak_inflight());
 end endgenerate
 ot_qwen_tp8_pv256_finalize u_final(.clk_control(clk),.clk_join({32{clk}}),.rst_n(rst_n),.start(start_pv),.epoch(ep),
  .reciprocal(rz),.reciprocal_valid(state==PV&&cleared&&rzok),.reciprocal_ready(rr),.reciprocal_epoch(ep),
  .p0_valid(pvalid[0]),.p1_valid(pvalid[1]),.p0_ready(pready[0]),.p1_ready(pready[1]),.p0_epoch(pep[15:0]),.p1_epoch(pep[31:16]),
  .p0_partial(partial[16383:0]),.p1_partial(partial[32767:16384]),.out_valid(fvalid),.out_ready(fready),.out_data(fout),.out_epoch(fepoch),.fault(ff));
endmodule

// Preserve H's issued-request credit contract across arbitrarily stalled external
// request transport. Requests remain queued through their ordered response.
module ot_qwen_tp8_k_request_adapter (
 input wire clk,rst_n,start,input wire [15:0] epoch,input wire [5:0] layer,
 input wire raw_valid,input wire [12:0] raw_t,input wire raw_wrong_type,
 output wire req_valid,input wire req_ready,output wire [12:0] req_t,
 input wire rsp_valid,input wire [12:0] rsp_t,input wire [15:0] rsp_epoch,input wire [5:0] rsp_layer,
 output wire checked_rsp,output reg fault,output reg [31:0] accepted
);
 reg [12:0] tags[0:127];reg [6:0] wp,sp,rp;reg [8:0] used,unsent,sent;
 reg active;
 assign req_valid=active&&!fault&&unsent!=0;assign req_t=tags[sp];
 wire issue=req_valid&&req_ready;
 wire good=active&&sent!=0&&rsp_t==tags[rp]&&rsp_epoch==epoch&&rsp_layer==layer;
 assign checked_rsp=rsp_valid&&good&&!fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wp<=0;sp<=0;rp<=0;used<=0;unsent<=0;sent<=0;fault<=0;accepted<=0;active<=0;end
  else if(start)begin
   if(used!=0||raw_valid||rsp_valid)fault<=1;
   else begin wp<=0;sp<=0;rp<=0;used<=0;unsent<=0;sent<=0;accepted<=0;active<=1;end
  end else begin
   if(raw_valid&&(used==128||raw_wrong_type||!active))fault<=1;
   if(rsp_valid&&!good)fault<=1;
   if(raw_valid&&used<128&&!raw_wrong_type&&active)begin tags[wp]<=raw_t;wp<=wp+1'b1;end
   if(issue)sp<=sp+1'b1;
   if(checked_rsp)begin rp<=rp+1'b1;accepted<=accepted+1'b1;end
   used<=used+(raw_valid?1:0)-(checked_rsp?1:0);
   unsent<=unsent+(raw_valid?1:0)-(issue?1:0);
   sent<=sent+(issue?1:0)-(checked_rsp?1:0);
  end
 end
endmodule
