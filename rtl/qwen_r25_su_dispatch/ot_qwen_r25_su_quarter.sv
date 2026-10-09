`timescale 1ns/1ps
// Real N256/M64 c12 arithmetic, native690 commands and finite protected service.
// Default off. Serial virtual edges retain the native fixed operand calendar;
// a native edge occurs only after all captured requests and publications finish.
module ot_qwen_r25_su_quarter #(
 parameter integer ENABLE=0,N=256,M=64,QID=0
)(
 input wire clk,rst_n,warm_abort,
 input wire cmd_v,output wire cmd_rdy,input wire [689:0] cmd_word,
 input wire [72:0] cmd_owner,input wire [11:0] cmd_pc,input wire [1:0] cmd_query,
 output wire done_v,output wire [72:0] done_owner,
 output wire [11:0] done_pc,output wire [1:0] done_query,
 output wire req_v,input wire req_rdy,output wire [336:0] req,
 input wire rsp_v,output wire rsp_rdy,input wire [272:0] rsp,
 output wire fault,output wire [31:0] virtual_edges,reads,writes,visibility_reads
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:g_off
  assign cmd_rdy=0;assign done_v=0;assign done_owner=0;assign done_pc=0;assign done_query=0;
  assign req_v=0;assign req=0;assign rsp_rdy=0;assign fault=0;
  assign virtual_edges=0;assign reads=0;assign writes=0;assign visibility_reads=0;
 end else begin:g_on
 localparam integer AW=24,NR=N/8,LV=7,BCAST_STAGES=5,RET_STAGES=6,MLAT=6,ALAT=6;
 `include "tb_hdc_v41x_vec_fields.svh"
 localparam integer RN=5*N,WN=2*N+NR;
 localparam IDLE=0,SNAP0=1,SNAP1=2,STEP=3,READ_SELECT=4,READ_DECODE=5,READ_HEAD=6,
  RREQ=7,RWAIT=8,RENC0=9,RENC1=10,WRITE_SELECT=11,WRITE_DECODE=12,WRITE_HEAD=13,
  WREQ=14,WWAIT=15,FREQ=16,FWAIT=17,FRAME_DONE=18,COMPLETE=19,FAILED=20;
 reg [71:0] control,identity,owner_low,word_chunks[0:10];
 reg [71:0] read_meta[0:RN-1],reply_words[0:RN-1],write_meta[0:WN-1];
 reg [71:0] head;
 reg [31:0] response_word,vcount,rcount,wcount,fcount;
 wire [65:0] cd=decode64(control),id=decode64(identity),od=decode64(owner_low);
 wire [63:0] c=cd[63:0],ident=id[63:0];
 wire [4:0] state=c[4:0];wire [12:0] cursor=c[17:5];
 wire [1:0] age=c[19:18];wire issued=c[20];wire [15:0] tag=c[36:21];
 wire sticky=c[37];wire [65:0] hd=decode64(head);wire [63:0] hr=hd[63:0];
 wire [703:0] padded_word;wire [10:0] word_ue;
 for(genvar k=0;k<11;k=k+1)begin:g_words
  wire [65:0] d=decode64(word_chunks[k]);
  assign padded_word[k*64+:64]=d[63:0];assign word_ue[k]=d[65];
 end
 wire [PW-1:0] w=padded_word[689:0];
 wire bad=sticky||cd[65]||id[65]||od[65]||hd[65]||(|word_ue);
 wire engine_rst_n=rst_n&&!bad;
 wire engine_clk;
 ot_hdc_cg u_gate(.clk(clk),.en(!engine_rst_n||state==STEP),.gclk(engine_clk));
 wire ready,idle,native_fault,native_order_fault,retire_o;
 wire [7:0] cr_seq,cr_dseq,cr_rseq;wire [15:0] cr_cnt,emitted;
 wire [7:0] dr=cr_rseq-w[F_W_RSEQ+:8],dd=cr_dseq-w[F_W_DSEQ+:8];
 wire cond=(!w[F_W_IDLE]||idle)&&(!w[F_W_RSEQ_EN]||!dr[7])&&
           (!w[F_W_DSEQ_EN]||!dd[7]);
 wire go=engine_rst_n&&state==STEP&&!issued&&cond;
 wire [7:0] x_seq=0,x_dseq=8'hff;wire [15:0] x_cnt=0;
 wire [N-1:0] vi_re,vm_we,kv_we;
 wire [N*AW-1:0] vi_addr,vm_waddr,kv_waddr;
 wire [N*32-1:0] vi_q,vm_wdata,kv_wdata;
 wire [4*N*AW-1:0] rd_addr;wire [4*N-1:0] rd_re;
 wire [8*N-1:0] rd_src;wire [4*N*32-1:0] rd_q;
 wire [NR-1:0] res_we;wire [NR*AW-1:0] res_addr;wire [NR*32-1:0] res_data;
 wire dbg_emit,dbg_ret,dbg_res;wire [7:0] dbg_eseq,dbg_rseq,dbg_sseq;
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV), .BCAST_STAGES(BCAST_STAGES), .RET_STAGES(RET_STAGES), .MLAT(MLAT), .ALAT(ALAT), .OPR(1), .DDIV(21), .SIDEX(4), .FSQ(1), .CAPR(1), .RPAD(1), .RSL(2), .RTAP(1), .ROUT(1), .RSLICE(64), .CTL12(2)) u_native (
        .clk(engine_clk), .rst_n(engine_rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(w[F_NOUT +: 16]), .i_nin(w[F_NIN +: 16]),
        .i_asrc(w[F_ASRC +: 2]), .i_bsrc(w[F_BSRC +: 2]), .i_csrc(w[F_CSRC +: 2]), .i_dsrc(w[F_DSRC +: 2]),
        .i_abase(w[F_ABASE +: 24]), .i_aso(w[F_ASO +: 24]), .i_asi(w[F_ASI +: 24]), .i_aibase(w[F_AIBASE +: 24]),
        .i_aind(w[F_AIND +: 2]),
        .i_bbase(w[F_BBASE +: 24]), .i_bso(w[F_BSO +: 24]), .i_bsi(w[F_BSI +: 24]), .i_bhalf(w[F_BHALF]),
        .i_cbase(w[F_CBASE +: 24]), .i_cso(w[F_CSO +: 24]), .i_csi(w[F_CSI +: 24]), .i_cpair(w[F_CPAIR]),
        .i_dbase(w[F_DBASE +: 24]), .i_dso(w[F_DSO +: 24]), .i_dsi(w[F_DSI +: 24]),
        .i_arnd(w[F_ARND]), .i_arelu(w[F_ARELU]), .i_amin(w[F_AMIN]), .i_cclip(w[F_CCLIP]),
        .i_m1(w[F_M1 +: 3]), .i_m2(w[F_M2 +: 2]), .i_qm(w[F_QM +: 3]), .i_ad(w[F_AD +: 3]), .i_sfu(w[F_SFU +: 3]),
        .i_e1(w[F_E1 +: 3]), .i_e2(w[F_E2 +: 2]), .i_rnd(w[F_RND]), .i_dst(w[F_DST +: 2]),
        .i_obase(w[F_OBASE +: 24]), .i_oso(w[F_OSO +: 24]), .i_osi(w[F_OSI +: 24]), .i_orow(w[F_OROW +: 24]),
        .i_red(w[F_RED +: 2]), .i_redsq(w[F_REDSQ]), .i_redwhole(w[F_REDWHOLE]), .i_redtree(w[F_REDTREE]),
        .i_redrnd(w[F_REDRND]), .i_rbase(w[F_RBASE +: 24]), .i_rso(w[F_RSO +: 24]),
        .i_imm1(w[F_IMM1 +: 32]), .i_imm2(w[F_IMM2 +: 32]), .i_imm3(w[F_IMM3 +: 32]),
        .i_ch_src(w[F_CH_SRC +: 2]), .i_ch_seq(w[F_CH_SEQ +: 8]), .i_ch_lead(w[F_CH_LEAD +: 16]),
        .i_ch_mul(w[F_CH_MUL +: 16]),
        .x_seq(x_seq), .x_dseq(x_dseq), .x_cnt(x_cnt),
        .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq), .cr_cnt(cr_cnt),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src),
        .rd_q(rd_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata), .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .fault(native_fault), .order_fault(native_order_fault), .emitted(emitted), .retire_o(retire_o),
        .dbg_emit(dbg_emit), .dbg_eseq(dbg_eseq), .dbg_ret(dbg_ret), .dbg_rseq(dbg_rseq),
        .dbg_res(dbg_res), .dbg_sseq(dbg_sseq));

 wire [RN-1:0] reply_ue;
 for(genvar k=0;k<RN;k=k+1)begin:g_reply
  wire [65:0] d=decode64(reply_words[k]);
  assign reply_ue[k]=d[65]||d[47:32]!=k;
  if(k<N)assign vi_q[k*32+:32]=d[31:0];
  else assign rd_q[(k-N)*32+:32]=d[31:0];
 end
 wire doing_write=state==WREQ||state==WWAIT||state==FREQ||state==FWAIT;
 wire write_kv=hr[56];wire [1:0] src=hr[25:24];
 wire [23:0] address=doing_write?hr[55:32]:hr[23:0];
 wire [31:0] byte_address=doing_write?
  (write_kv?32'h100000:32'd0)+{6'd0,address,2'd0}:
  (src==0?32'd0:src==1?32'h300000:src==2?32'h320000:32'h340000)+
  (src==3?{7'd0,address,1'b0}:{6'd0,address,2'd0});
 wire addr_ok=doing_write?(write_kv?address<524288:address<262144):
  (src==0?address<262144:src==3?address<65536:address<32768);
 assign req_v=!bad&&(state==RREQ||state==WREQ||state==FREQ)&&addr_ok;
 assign req={state==WREQ,{byte_address[31:5],5'd0},
  {224'd0,hr[31:0]}<<(byte_address[4:0]*8),
  state==WREQ?(32'hf<<byte_address[4:0]):32'd0,service_tag};
 wire [15:0] service_tag={2'(QID),tag[13:0]};
 wire waiting=state==RWAIT||state==WWAIT||state==FWAIT;
 wire matched=waiting&&rsp[272:257]==service_tag&&rsp[256]==(state==WWAIT);
 assign rsp_rdy=!bad&&matched;
 wire [31:0] result32=rsp[byte_address[4:0]*8+:32];
 wire [31:0] read_result=src==3?{rsp[byte_address[4:0]*8+:16],16'd0}:result32;
 assign cmd_rdy=state==IDLE&&!bad;assign done_v=state==COMPLETE&&!bad;
 assign done_owner={ident[8:0],od[63:0]};
 assign done_pc=ident[20:9];assign done_query=ident[22:21];
 assign fault=bad||state==FAILED;
 assign virtual_edges=vcount;assign reads=rcount;assign writes=wcount;assign visibility_reads=fcount;
 reg [63:0] next_c;integer i;
 always @* begin
  next_c=c;
  if(bad||warm_abort||native_fault||native_order_fault||(|reply_ue))begin next_c[37]=1;next_c[4:0]=FAILED;end
  else case(state)
   IDLE:if(cmd_v&&cmd_rdy)begin
    if(cmd_word[F_X_START]||cmd_word[F_NOUT+:16]==0||cmd_word[F_NIN+:16]==0)begin
     next_c[37]=1;next_c[4:0]=FAILED;
    end else begin next_c[20]=0;next_c[4:0]=SNAP0;end
   end
   SNAP0:next_c[4:0]=SNAP1;
   SNAP1:next_c[4:0]=STEP;
   STEP:begin if(go&&ready)next_c[20]=1;next_c[17:5]=0;next_c[4:0]=READ_SELECT;end
   READ_SELECT:begin next_c[19:18]=0;next_c[4:0]=READ_DECODE;end
   READ_DECODE:if(age==2)next_c[4:0]=READ_HEAD;else next_c[19:18]=age+1;
   READ_HEAD:if(hd[65]||hr[63:48]!=cursor)begin next_c[37]=1;next_c[4:0]=FAILED;end
    else if(hr[26])next_c[4:0]=RREQ;
    else if(cursor==RN-1)begin next_c[17:5]=0;next_c[4:0]=WRITE_SELECT;end
    else begin next_c[17:5]=cursor+1;next_c[4:0]=READ_SELECT;end
   RREQ:if(!addr_ok)begin next_c[37]=1;next_c[4:0]=FAILED;end else if(req_rdy)next_c[4:0]=RWAIT;
   RWAIT:if(rsp_v&&rsp_rdy)begin next_c[36:21]=tag+1;next_c[4:0]=RENC0;end
   RENC0:next_c[4:0]=RENC1;
   RENC1:if(cursor==RN-1)begin next_c[17:5]=0;next_c[4:0]=WRITE_SELECT;end
    else begin next_c[17:5]=cursor+1;next_c[4:0]=READ_SELECT;end
   WRITE_SELECT:begin next_c[19:18]=0;next_c[4:0]=WRITE_DECODE;end
   WRITE_DECODE:if(age==2)next_c[4:0]=WRITE_HEAD;else next_c[19:18]=age+1;
   WRITE_HEAD:if(hd[65])begin next_c[37]=1;next_c[4:0]=FAILED;end
    else if(hr[58])next_c[4:0]=WREQ;
    else if(cursor==WN-1)next_c[4:0]=FRAME_DONE;
    else begin next_c[17:5]=cursor+1;next_c[4:0]=WRITE_SELECT;end
   WREQ:if(!addr_ok)begin next_c[37]=1;next_c[4:0]=FAILED;end else if(req_rdy)next_c[4:0]=WWAIT;
   WWAIT:if(rsp_v&&rsp_rdy)begin next_c[36:21]=tag+1;next_c[4:0]=FREQ;end
   FREQ:if(req_rdy)next_c[4:0]=FWAIT;
   FWAIT:if(rsp_v&&rsp_rdy)begin
    if(result32!=hr[31:0])begin next_c[37]=1;next_c[4:0]=FAILED;end
    else begin next_c[36:21]=tag+1;
     if(cursor==WN-1)next_c[4:0]=FRAME_DONE;
     else begin next_c[17:5]=cursor+1;next_c[4:0]=WRITE_SELECT;end
    end
   end
   FRAME_DONE:next_c[4:0]=(issued&&idle)?COMPLETE:SNAP0;
   COMPLETE:next_c[4:0]=IDLE;
   default:;
  endcase
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   control<=encode64(0);identity<=encode64(0);owner_low<=encode64(0);head<=encode64(0);
   vcount<=0;rcount<=0;wcount<=0;fcount<=0;response_word<=0;
   for(i=0;i<11;i=i+1)word_chunks[i]<=encode64(0);
   for(i=0;i<RN;i=i+1)begin
    read_meta[i]<=encode64({16'(i),48'd0});reply_words[i]<=encode64({16'd0,16'(i),32'd0});
   end
   for(i=0;i<WN;i=i+1)write_meta[i]<=encode64(0);
  end else begin
   control<=encode64(next_c);
   if(state==IDLE&&cmd_v&&cmd_rdy)begin
    owner_low<=encode64(cmd_owner[63:0]);
    identity<=encode64({41'd0,cmd_query,cmd_pc,cmd_owner[72:64]});
    for(i=0;i<11;i=i+1)word_chunks[i]<=encode64(({14'd0,cmd_word}>>(i*64)));
   end
   if(!bad)case(state)
    SNAP1:begin
     for(i=0;i<N;i=i+1)read_meta[i]<=encode64({16'(i),21'd0,vi_re[i],2'd0,vi_addr[i*AW+:AW]});
     for(i=0;i<4*N;i=i+1)read_meta[N+i]<=encode64({16'(N+i),21'd0,rd_re[i],rd_src[i*2+:2],rd_addr[i*AW+:AW]});
     for(i=0;i<N;i=i+1)begin
      write_meta[i]<=encode64({5'd0,vm_we[i],2'd0,vm_waddr[i*AW+:AW],vm_wdata[i*32+:32]});
      write_meta[N+i]<=encode64({5'd0,kv_we[i],2'd1,kv_waddr[i*AW+:AW],kv_wdata[i*32+:32]});
     end
     for(i=0;i<NR;i=i+1)write_meta[2*N+i]<=encode64({5'd0,res_we[i],2'd0,res_addr[i*AW+:AW],res_data[i*32+:32]});
    end
    STEP:vcount<=vcount+1;
    READ_SELECT:head<=read_meta[cursor];
    RWAIT:if(rsp_v&&rsp_rdy)begin response_word<=read_result;rcount<=rcount+1;end
    RENC1:reply_words[cursor]<=encode64({16'd0,16'(cursor),response_word});
    WRITE_SELECT:head<=write_meta[cursor];
    WWAIT:if(rsp_v&&rsp_rdy)wcount<=wcount+1;
    FWAIT:if(rsp_v&&rsp_rdy)fcount<=fcount+1;
    default:;
   endcase
  end
 end
 initial if(N!=256||M!=64||QID<0||QID>3)$fatal(1,"Qwen real quarter requires N256/M64 and QID0..3");
 end endgenerate
endmodule
