`timescale 1ns/1ps
// Real SU memory-ABI reader/landing adapter. One-cycle rd_q, as the existing
// ot_hdc_v41x_vec bench/VM. No new memory ports; parent arbitrates these ports
// against the unchanged generic SU. Descriptor scalars are actual VM/CR bits
// loaded by the program caller, never computed here. PUBLISH_QUANT=0 preserves
// partial routed shards for the original cross-boundary quantisation consumer.
module ot_hbm_accel_su_fused_vm #(
 parameter integer ENABLE=0,KIND=0,N=1024,D=5120,RD=0,AW=24,
 parameter integer PUBLISH_QUANT=1,ROUTED=1,ADOPTED_SWIGLU_QUANT_ONLY=0
)(
 input wire clk,rst_n,cmd_valid,source_ready,landing_reserved,
 output wire cmd_ready,output reg busy,output wire done,output wire fault,
 input wire [31:0] job_id,
 // Actual enclosing protected stage owner, held through publication/drain.
 // Required only by the explicitly selected quant-only SwiGLU hook.
 input wire [72:0] held_frame,output wire [72:0] q_frame,
 input wire [AW-1:0] xbase,ubase,wbase,ybase,gain_base,
 input wire [511:0] comb,input wire [127:0] post_pre,
 input wire [31:0] n_f,eps,lim,
 input wire [(RD?RD/2:1)*32-1:0] cos_t,sin_t,
 output reg [4*N*AW-1:0] rd_addr,output reg [4*N-1:0] rd_re,
 output reg [8*N-1:0] rd_src,input wire [4*N*32-1:0] rd_q,
 output reg [N-1:0] vm_we,output reg [N*AW-1:0] vm_waddr,
 output wire [N*32-1:0] vm_wdata,
 output wire q_valid,output wire [7:0] q_index,
 output wire [N*8-1:0] q_codes,output wire [(N/32)*10-1:0] q_exp,
 output wire [N*16-1:0] q_bf16,
 output wire [31:0] completion_id,output wire [15:0] reserve_events
);
 localparam integer NV=(D+N-1)/N,NB=KIND==4?(4*D+N-1)/N:NV;
 localparam [2:0] IDLE=0,GAIN=1,START=2,DATA=3,DRAIN=4;
 reg [2:0] state;
 reg [AW-1:0] xb,ub,wb,yb,gb;
 reg [31:0] jid;
 reg [511:0] cb;reg [127:0] pp;
 reg [31:0] nf,ep,li;
 reg [(RD?RD/2:1)*32-1:0] ct,st;
 reg [15:0] requested;
 reg reply_gain,reply_data;
 reg [7:0] reply_index;
 wire start_ready,gain_ready,in_ready,engine_busy;
 wire y_valid,ro_valid;
 wire [7:0] y_index;
 wire [N*32-1:0] yd,rod;
 reg [7:0] ro_index;
 reg collision;
 wire read_gain=state==GAIN && requested<NV && gain_ready;
 wire read_data=state==DATA && requested<NB && in_ready;
 assign cmd_ready=ENABLE && !busy && !fault && source_ready && landing_reserved;
 wire accepted=cmd_valid && cmd_ready;
 integer l,k,element,wl;
 always @* begin
  rd_addr=0;rd_re=0;rd_src=0;
  if(read_gain) for(l=0;l<N;l=l+1) begin
   rd_addr[l*AW+:AW]=gb+requested*N+l; rd_re[l]=(requested*N+l<D);rd_src[l*2+:2]=1;
  end
  if(read_data) for(l=0;l<N;l=l+1) begin
   if(KIND==0) for(k=0;k<4;k=k+1) begin
    rd_addr[(k*N+l)*AW+:AW]=xb+k*D+requested*N+l;
    rd_re[k*N+l]=(requested*N+l<D);
   end
   else if(KIND==4) begin
    element=requested*(N/4)+l/4;
    rd_addr[l*AW+:AW]=xb+(l%4)*D+element;rd_re[l]=(element<D);
    if(l<N/4) begin
     rd_addr[(N+l)*AW+:AW]=ub+requested*(N/4)+l;
     rd_re[N+l]=(requested*(N/4)+l<D);
    end
   end else begin
    rd_addr[l*AW+:AW]=xb+requested*N+l;rd_re[l]=(requested*N+l<D);
    if(KIND==3) begin
     rd_addr[(N+l)*AW+:AW]=ub+requested*N+l;rd_re[N+l]=(requested*N+l<D);
     rd_addr[(2*N+l)*AW+:AW]=wb;rd_re[2*N+l]=ROUTED && (requested*N+l<D);
    end
   end
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE;busy<=0;requested<=0;reply_gain<=0;reply_data<=0;reply_index<=0;ro_index<=0;collision<=0;
   xb<=0;ub<=0;wb<=0;yb<=0;gb<=0;jid<=0;cb<=0;pp<=0;nf<=0;ep<=0;li<=0;ct<=0;st<=0;
  end else begin
   reply_gain<=read_gain;reply_data<=read_data;reply_index<=requested[7:0];
   if(accepted) begin
    busy<=1;state<=KIND<3?GAIN:START;requested<=0;ro_index<=0;
    xb<=xbase;ub<=ubase;wb<=wbase;yb<=ybase;gb<=gain_base;
    jid<=job_id;cb<=comb;pp<=post_pre;nf<=n_f;ep<=eps;li<=lim;ct<=cos_t;st<=sin_t;
   end
   if(read_gain || read_data) requested<=requested+1;
   if(state==GAIN && requested==NV && !reply_gain) state<=START;
   if(state==START && start_ready) begin state<=DATA;requested<=0;end
   if(state==DATA && requested==NB && !reply_data) state<=DRAIN;
   if(ro_valid || (ADOPTED_SWIGLU_QUANT_ONLY && q_valid)) ro_index<=ro_index+1;
   if(y_valid && ro_valid) collision<=1;
   // Accepted VM replies cannot be silently dropped if the enclosing lease or
   // whole-output reservation is withdrawn. Retain busy/debt until root POR.
   if(ADOPTED_SWIGLU_QUANT_ONLY && busy && (!source_ready || !landing_reserved)) collision<=1;
   if(done && !collision) begin busy<=0;state<=IDLE;end
  end
 end
 // Actual VM writes, with the HCpost group-to-copy-major scatter retained.
 assign vm_wdata=ro_valid?rod:yd;
 always @* begin
  vm_we=0;vm_waddr=0;
  for(wl=0;wl<N;wl=wl+1) begin
   if(KIND==4) begin
    vm_waddr[wl*AW+:AW]=yb+(wl%4)*D+y_index*(N/4)+wl/4;
    vm_we[wl]=y_valid && (y_index*(N/4)+wl/4<D) && !fault;
   end else begin
    vm_waddr[wl*AW+:AW]=yb+(ro_valid?ro_index:y_index)*N+wl;
    vm_we[wl]=(y_valid||ro_valid) && ((ro_valid?ro_index:y_index)*N+wl<D) && !fault;
   end
  end
 end
 wire ef;
 assign fault=ef|collision;
 generate if(ADOPTED_SWIGLU_QUANT_ONLY) begin:g_adopted_swiglu_quant
  initial if(KIND!=3 || !PUBLISH_QUANT || D%N!=0 || D/N>256)
   $fatal(1,"adopted SwiGLU quant-only requires KIND3 and complete quant beats");
  // Reuse the VM command/one-cycle reader state. No second arithmetic engine,
  // no duplicate protected owner, no extra payload staging/traversal. ro_index
  // is unused by KIND3 and is the existing ordered OUTPUT cursor in this mode.
  assign gain_ready=0;assign start_ready=busy&&landing_reserved;
  assign engine_busy=busy;assign y_valid=0;assign ro_valid=0;
  assign y_index=0;assign yd=0;assign rod=0;
  assign reserve_events=ENABLE?NV:0;
  assign completion_id=jid;
  assign done=q_valid && ro_index==NV-1 && requested==NB && !reply_data && !fault;
  // q_bf16 is QDQ, not original prequant BF16: vm_we remains zero. Parent
  // completion is still its checked quant landing/drain, never this pulse alone.
  ot_hbm_integrated_swiglu_quant_adapter #(.ENABLE(ENABLE),.N(N),.ROUTED(ROUTED)) u_quant(
   .clk(clk),.por_n(rst_n),.launch_permit(busy&&source_ready&&!collision),
   .landing_reserved(landing_reserved),.in_valid(reply_data),.in_ready(in_ready),
   .held_frame(held_frame),.landing_index(ro_index),.lim(li),.operands(rd_q),
   .q_valid(q_valid),.q_frame(q_frame),.q_index(q_index),
   .q_codes(q_codes),.q_exp(q_exp),.q_bf16(q_bf16),.fault(ef));
 end else begin:g_original
 assign q_frame=0;
 ot_hbm_accel_su_fused_stream #(.ENABLE(ENABLE),.KIND(KIND),.N(N),.D(D),.RD(RD),
   .PUBLISH_QUANT(PUBLISH_QUANT),.ROUTED(ROUTED)) u_engine
  (.clk(clk),.rst_n(rst_n),.cmd_valid(state==START),.cmd_id(jid),
   .reserve_grant(landing_reserved),.reserve_events(reserve_events),.cmd_ready(start_ready),
   .busy(engine_busy),.done(done),.completion_id(completion_id),
   .comb(cb),.post_pre(pp),.n_f(nf),.eps(ep),.lim(li),.cos_t(ct),.sin_t(st),
   .gain_valid(reply_gain),.gain_index(reply_index),.gain_data(rd_q[0+:N*32]),.gain_ready(gain_ready),
   .in_valid(reply_data),.in_ready(in_ready),.operands(rd_q),.sink_ready(landing_reserved && !collision),
   .y_valid(y_valid),.ro_valid(ro_valid),.q_valid(q_valid),.y_index(y_index),.q_index(q_index),
   .y_data(yd),.ro_data(rod),.q_codes(q_codes),.q_exp(q_exp),.q_bf16(q_bf16),.fault(ef));
 end endgenerate
endmodule
