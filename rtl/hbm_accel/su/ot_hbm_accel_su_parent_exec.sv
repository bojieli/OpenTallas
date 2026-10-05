`timescale 1ns/1ps
// Selected whole-engine virtual-edge construction, model e72bb27c1.
// Native words are the ORIGINAL 690-bit scheduled words transported in IM64.
// Minimum binding: one complete four-op HCpost group. Partial fragments refuse.
// Both unchanged engines use this SAME finite provider and publication calendar.
module ot_hbm_accel_su_parent_exec #(
 parameter integer ENABLE=0,N=1024,M=256,D=5120,IMW=14
)(
 input wire clk,rst_n,owned,config_idle,loader_we,
 input wire [IMW-1:0] loader_addr,input wire [63:0] loader_data,
 input wire [31:0] selected_pc,job_id,
 output wire req_v,input wire req_rdy,output wire [336:0] req,
 input wire rsp_v,output wire rsp_rdy,input wire [272:0] rsp,
 output wire done,fault,
 output wire [31:0] virtual_edges,read_requests,write_requests,publication_requests,
 output wire [3:0] retired_original_ops
);
 generate if(!ENABLE) begin:g_off
  assign req_v=0;assign req=0;assign rsp_rdy=0;assign done=0;assign fault=0;
  assign virtual_edges=0;assign read_requests=0;assign write_requests=0;
  assign publication_requests=0;assign retired_original_ops=0;
 end else begin:g_on
 import ot_gpu_w6_secded_pkg::*;
 localparam integer AW=24,NR=N/8,LV=7,BCAST_STAGES=7,RET_STAGES=8,MLAT=6,ALAT=5;
 `include "tb_hdc_v41x_vec_fields.svh"
 localparam integer RN=5*N,WN=2*N+NR;
 localparam [4:0] IDLE=0,SCALAR_SELECT=1,BOOT=2,SNAP0=3,SNAP1=4,STEP=5,
  READ_SELECT=6,READ_DECODE=7,READ_HEAD=8,RREQ=9,RWAIT=10,RENC0=11,RENC1=12,
  WRITE_SELECT=13,WRITE_DECODE=14,WRITE_HEAD=15,WREQ=16,WWAIT=17,
  FREQ=18,FWAIT=19,FRAME_DONE=20,FINISHED=21,STOP=22;
 reg [4:0] state;
 reg executing,candidate,started;
 reg bad;
 reg [3:0] pc,logical_retired;
 reg [12:0] cursor;
 reg [2:0] age;
 reg scalar_phase;
 reg [4:0] scalar_index;
 reg [31:0] jid;
 reg [15:0] tag;
 reg [31:0] vcount,rcount,wcount,fcount;
 reg [703:0] program_words[0:7];
 reg [10:0] program_valid[0:7];
 reg [71:0] read_meta[0:RN-1],reply_words[0:RN-1],writes[0:WN-1],scalar[0:9];
 reg [71:0] head;
 reg [31:0] response_word;
 wire [65:0] head_dec=decode64(head);
 wire [63:0] hr=head_dec[63:0];
 wire head_bad=|head_dec[65:64];
 wire engine_rst_n=rst_n && executing && started && !bad;
 wire engine_clk;
 ot_hdc_cg u_gate(.clk(clk),.en(!engine_rst_n || state==STEP),.gclk(engine_clk));
 wire [PW-1:0] w=program_words[pc<4?pc:0][PW-1:0];
 wire ready,idle,native_fault,native_order_fault,retire_o;
 wire [7:0] cr_seq,cr_dseq,cr_rseq;
 wire [15:0] cr_cnt,emitted;
 wire [7:0] dr=cr_rseq-w[F_W_RSEQ+:8],dd=cr_dseq-w[F_W_DSEQ+:8];
 wire cond=(!w[F_W_IDLE] || idle) && (!w[F_W_RSEQ_EN] || !dr[7]) &&
           (!w[F_W_DSEQ_EN] || !dd[7]);
 wire go=engine_rst_n && !candidate && pc<4 && cond;
 // The selected original has no external X producer. Unsupported X refuses.
 wire [7:0] x_seq=0,x_dseq=8'hff;wire [15:0] x_cnt=0;
 wire [N-1:0] vi_re,vm_we,kv_we;
 wire [N*AW-1:0] vi_addr,vm_waddr,kv_waddr;
 wire [N*32-1:0] vi_q,vm_wdata,kv_wdata;
 wire [4*N*AW-1:0] rd_addr;
 wire [4*N-1:0] rd_re;
 wire [8*N-1:0] rd_src;
 wire [4*N*32-1:0] rd_q;
 wire [NR-1:0] res_we;wire [NR*AW-1:0] res_addr;wire [NR*32-1:0] res_data;
 wire dbg_emit,dbg_ret,dbg_res;wire [7:0] dbg_eseq,dbg_rseq,dbg_sseq;
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV), .BCAST_STAGES(BCAST_STAGES), .RET_STAGES(RET_STAGES), .MLAT(MLAT), .ALAT(ALAT)) u_native (
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
 wire f_busy,f_done,f_fault,f_ready;
 wire [4*N*AW-1:0] f_ra;wire [4*N-1:0] f_re;wire [8*N-1:0] f_rs;
 wire [N-1:0] f_we;wire [N*AW-1:0] f_wa;wire [N*32-1:0] f_wd;
 wire [511:0] comb;wire [127:0] post;
 wire [639:0] scalar_raw;
 wire [9:0] scalar_bad;
 genvar s;
 for(s=0;s<10;s=s+1) begin:g_scalar
  wire [65:0] q=decode64(scalar[s]);
  assign scalar_raw[s*64+:64]=q[63:0];assign scalar_bad[s]=|q[65:64];
 end
 assign comb=scalar_raw[511:0];assign post=scalar_raw[639:512];
 wire [31:0] f_id;wire [15:0] f_reserve;
 ot_hbm_accel_su_fused_vm #(.ENABLE(1),.KIND(4),.N(N),.D(D),.RD(0),.AW(AW),.PUBLISH_QUANT(0)) u_fused(
  .clk(engine_clk),.rst_n(engine_rst_n),.cmd_valid(candidate && pc==0),
  .source_ready(owned && started && !bad),.landing_reserved(owned && started && !bad),
  .cmd_ready(f_ready),.busy(f_busy),.done(f_done),.fault(f_fault),.job_id(jid),
  .xbase(program_words[0][F_ABASE+:24]),.ubase(program_words[3][F_ABASE+:24]),
  .wbase(24'd0),.ybase(program_words[0][F_OBASE+:24]),.gain_base(24'd0),
  .comb(comb),.post_pre(post),.n_f(32'd0),.eps(32'd0),.lim(32'd0),.cos_t(32'd0),.sin_t(32'd0),
  .rd_addr(f_ra),.rd_re(f_re),.rd_src(f_rs),.rd_q(rd_q),
  .vm_we(f_we),.vm_waddr(f_wa),.vm_wdata(f_wd),
  .q_valid(),.q_index(),.q_codes(),.q_exp(),.q_bf16(),.completion_id(f_id),.reserve_events(f_reserve));
 wire [RN-1:0] reply_bad;
 for(s=0;s<RN;s=s+1) begin:g_reply
  wire [65:0] q=decode64(reply_words[s]);
  assign reply_bad[s]=(|q[65:64]) || q[47:32]!=s;
  if(s<N) assign vi_q[s*32+:32]=q[31:0];
  else assign rd_q[(s-N)*32+:32]=q[31:0];
 end
 // Both scheduled issuer and engine move on the SAME actual gated edge.
 always @(posedge engine_clk or negedge engine_rst_n) begin
  if(!engine_rst_n) pc<=0;
  else if((go && ready) || (candidate && pc==0 && f_ready)) pc<=pc+1;
 end
 wire read_enabled=hr[26];wire [1:0] read_source=hr[25:24];
 wire write_enabled=hr[58];wire write_kv=hr[56];
 wire [23:0] word_address=scalar_phase ?
  (scalar_index<16?program_words[0][F_BBASE+:24]+scalar_index:
                   program_words[3][F_BBASE+:24]+scalar_index-16):
  (state>=WRITE_SELECT && state<=FWAIT?hr[55:32]:hr[23:0]);
 wire doing_write=(state==WREQ || state==WWAIT || state==FREQ || state==FWAIT);
 wire [1:0] src=scalar_phase?2'd0:read_source;
 wire [31:0] byte_address=doing_write?
  (write_kv?32'h100000:32'd0)+{6'd0,word_address,2'd0}:
  (src==0?32'd0:src==1?32'h300000:src==2?32'h320000:32'h340000)+
   (src==3?{7'd0,word_address,1'b0}:{6'd0,word_address,2'd0});
 wire addr_ok=doing_write?(write_kv?word_address<524288:word_address<262144):
                (src==0?word_address<262144:src==3?word_address<65536:word_address<32768);
 wire [31:0] strobe=32'hf << byte_address[4:0];
 wire [255:0] payload={224'd0,hr[31:0]} << (byte_address[4:0]*8);
 assign req_v=owned && !bad && (state==RREQ || state==WREQ || state==FREQ) && addr_ok;
 assign req={state==WREQ,{byte_address[31:5],5'd0},payload,state==WREQ?strobe:32'd0,tag};
 wire waiting=state==RWAIT || state==WWAIT || state==FWAIT;
 wire matched=waiting && rsp[272:257]==tag && rsp[256]==(state==WWAIT);
 assign rsp_rdy=owned && !bad && matched;
 wire [31:0] result32=rsp[byte_address[4:0]*8+:32];
 wire [31:0] read_result=src==3?{rsp[byte_address[4:0]*8+:16],16'd0}:result32;
 assign done=state==FINISHED;assign fault=bad;
 assign virtual_edges=vcount;assign read_requests=rcount;assign write_requests=wcount;
 assign publication_requests=fcount;assign retired_original_ops=logical_retired;
 localparam [689:0] ORIGINAL_0=690'h000000000000000000000000000000000000000000000000000000000000000004005000019161001210000000000001006444000000800000000a2000000000000040191000000000000010000000000400014000004;
 localparam [689:0] ORIGINAL_1=690'h000000040000040100000000000000000000000000000000000000000000000004005000019161002010000000000000000000000000800a0000322c00000000000040191200000000000010000000028400014000004;
 localparam [689:0] ORIGINAL_2=690'h000000040000040500000000000000000000000000000000000000000000000004005000019161002010000000000000000000000000800a0000322c0000000000004019130000000000001000000003c400014000004;
 localparam [689:0] ORIGINAL_3=690'h000000040000040900000000000000000000000000000000000000000000000004005000019161802010000000000000000000000000800a0000322c00000000000040191400000000000010000000050400014000004;
 reg program_ok;
 integer i;
 always @* begin
  program_ok=(program_words[0][689:0]==ORIGINAL_0 && program_words[1][689:0]==ORIGINAL_1 &&
              program_words[2][689:0]==ORIGINAL_2 && program_words[3][689:0]==ORIGINAL_3);
  for(integer p=0;p<4;p=p+1) begin
   if(program_valid[p]!=11'h7ff || program_words[p][703:690]!=0 ||
      program_words[p][F_X_START] || program_words[p][F_NOUT+:16]!=4 ||
      program_words[p][F_NIN+:16]!=D || program_words[p][F_DST+:2]!=1 ||
      program_words[p][F_REDSQ] || program_words[p][F_RED+:2]!=0 ||
      program_words[p][F_OBASE+:24]!=program_words[0][F_OBASE+:24]) program_ok=0;
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE;executing<=0;candidate<=0;started<=0;bad<=0;
   cursor<=0;age<=0;scalar_phase<=0;scalar_index<=0;jid<=0;tag<=0;
   logical_retired<=0;vcount<=0;rcount<=0;wcount<=0;fcount<=0;head<=encode64(0);response_word<=0;
   for(i=0;i<8;i=i+1) begin program_words[i]<=0;program_valid[i]<=0;end
   for(i=0;i<RN;i=i+1) begin
    read_meta[i]<=encode64({16'(i),48'd0});reply_words[i]<=encode64({16'd0,16'(i),32'd0});
   end
   for(i=0;i<WN;i=i+1) writes[i]<=encode64(0);
   for(i=0;i<10;i=i+1) scalar[i]<=encode64(0);
  end else begin
   if(loader_we) begin
    if(!config_idle || owned || executing || loader_addr[3:0]>=11 ||
       loader_addr[IMW-2:7]!=0) bad<=1;
    else begin
     program_words[loader_addr[6:4]][loader_addr[3:0]*64+:64]<=loader_data;
     program_valid[loader_addr[6:4]][loader_addr[3:0]]<=1;
    end
   end
   if(owned && !executing && state==IDLE) begin
    if(!program_ok || (selected_pc!=32'h80000004 && selected_pc!=32'hc0000004)) begin bad<=1;state<=STOP;end
    else begin
     executing<=1;candidate<=selected_pc[30];jid<=job_id;logical_retired<=0;
     vcount<=0;rcount<=0;wcount<=0;fcount<=0;scalar_index<=0;scalar_phase<=selected_pc[30];
     started<=0;state<=selected_pc[30]?SCALAR_SELECT:BOOT;
    end
   end
   if(executing && !owned && state!=FINISHED) bad<=1;
   if(executing && (native_fault || native_order_fault || (candidate && f_fault) ||
      |reply_bad || (candidate && |scalar_bad))) bad<=1;
   if(!bad && owned) case(state)
    SCALAR_SELECT:begin head<=encode64(0);state<=RREQ;end
    BOOT:begin started<=1;state<=SNAP0;end
    SNAP0:state<=SNAP1;
    SNAP1:begin
     // Snapshot PRE-edge ports. Encode inputs have been held for two master edges.
     for(i=0;i<N;i=i+1) read_meta[i]<=encode64({16'(i),21'd0,!candidate && vi_re[i],2'd0,vi_addr[i*AW+:AW]});
     for(i=0;i<4*N;i=i+1) read_meta[N+i]<=encode64({16'(N+i),21'd0,
       candidate?f_re[i]:rd_re[i],candidate?f_rs[i*2+:2]:rd_src[i*2+:2],
       candidate?f_ra[i*AW+:AW]:rd_addr[i*AW+:AW]});
     for(i=0;i<N;i=i+1) begin
      writes[i]<=encode64({5'd0,candidate?f_we[i]:vm_we[i],2'd0,
        candidate?f_wa[i*AW+:AW]:vm_waddr[i*AW+:AW],candidate?f_wd[i*32+:32]:vm_wdata[i*32+:32]});
      writes[N+i]<=encode64({5'd0,!candidate && kv_we[i],2'd1,kv_waddr[i*AW+:AW],kv_wdata[i*32+:32]});
     end
     for(i=0;i<NR;i=i+1) writes[2*N+i]<=encode64({5'd0,!candidate && res_we[i],2'd0,res_addr[i*AW+:AW],res_data[i*32+:32]});
     state<=STEP;
    end
    STEP:begin vcount<=vcount+1;cursor<=0;state<=READ_SELECT;end
    READ_SELECT:begin head<=read_meta[cursor];age<=0;state<=READ_DECODE;end
    READ_DECODE:if(age==2) state<=READ_HEAD;else age<=age+1;
    READ_HEAD:begin
     if(head_bad || hr[63:48]!=cursor) bad<=1;
     else if(read_enabled) state<=RREQ;
     else if(cursor==RN-1) begin cursor<=0;state<=WRITE_SELECT;end
     else begin cursor<=cursor+1;state<=READ_SELECT;end
    end
    RREQ:if(!addr_ok) bad<=1;else if(req_rdy) state<=RWAIT;
    RWAIT:if(rsp_v && rsp_rdy) begin response_word<=read_result;rcount<=rcount+1;tag<=tag+1;state<=RENC0;end
    RENC0:state<=RENC1;
    RENC1:begin
     if(scalar_phase) begin
      if(scalar_index[0]) scalar[scalar_index>>1]<=encode64({response_word,scalar_raw[(scalar_index>>1)*64+:32]});
      else scalar[scalar_index>>1]<=encode64({scalar_raw[(scalar_index>>1)*64+32+:32],response_word});
      if(scalar_index==19) begin scalar_phase<=0;state<=BOOT;end
      else begin scalar_index<=scalar_index+1;state<=SCALAR_SELECT;end
     end else begin
      reply_words[cursor]<=encode64({16'd0,16'(cursor),response_word});
      if(cursor==RN-1) begin cursor<=0;state<=WRITE_SELECT;end
      else begin cursor<=cursor+1;state<=READ_SELECT;end
     end
    end
    WRITE_SELECT:begin head<=writes[cursor];age<=0;state<=WRITE_DECODE;end
    WRITE_DECODE:if(age==2) state<=WRITE_HEAD;else age<=age+1;
    WRITE_HEAD:begin
     if(head_bad) bad<=1;
     else if(write_enabled) state<=WREQ;
     else if(cursor==WN-1) state<=FRAME_DONE;
     else begin cursor<=cursor+1;state<=WRITE_SELECT;end
    end
    WREQ:if(!addr_ok) bad<=1;else if(req_rdy) state<=WWAIT;
    WWAIT:if(rsp_v && rsp_rdy) begin tag<=tag+1;wcount<=wcount+1;state<=FREQ;end
    FREQ:if(req_rdy) state<=FWAIT;
    FWAIT:if(rsp_v && rsp_rdy) begin
     // The actual same-sector visibility read must reproduce this write.
     if(result32!=hr[31:0]) bad<=1;
     else begin
      tag<=tag+1;fcount<=fcount+1;
      if(cursor==WN-1) state<=FRAME_DONE;
      else begin cursor<=cursor+1;state<=WRITE_SELECT;end
     end
    end
    FRAME_DONE:if(candidate?f_done:(pc==4 && idle)) begin
     // Whole original group retires AFTER real publication, no fake per-op credits.
     if(candidate && f_id!=jid) bad<=1;
     else begin logical_retired<=4;state<=FINISHED;end
    end else state<=SNAP0;
    FINISHED:if(!owned) begin executing<=0;started<=0;state<=IDLE;end
    default:;
   endcase
   if(state==FINISHED && !owned) begin executing<=0;started<=0;state<=IDLE;end
  end
 end
 initial if(N!=1024 || M!=256 || D!=5120 || IMW<8) $fatal(1,"selected source-bound full HCpost parent inventory");
 end endgenerate
endmodule
