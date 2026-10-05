`timescale 1ns/1ps
// Finite contiguous norm provider. This replaces neither a whole VM nor its
// native issuer. The enclosing owner must grant a drained, exclusive source
// and destination lease on the actual SM0 LSU client. RD/quant remain original.
// One real tagged sector transaction is outstanding. Every output sector gets
// a matched write response AND ordered readback before completion publication.
module ot_hbm_accel_su_fused_mreq #(
 parameter integer ENABLE=0,KIND=1,N=256,D=1280
)(
 input wire clk,rst_n,cmd_valid,lease_grant,prior_route_drained,
 output wire cmd_ready,output reg busy,done,fault,
 input wire [31:0] job_id,vm_byte_base,cr_byte_base,
 input wire [23:0] xbase,ybase,gain_base,
 input wire [31:0] n_f,eps,
 output reg [31:0] completion_id,
 output wire req_v,input wire req_rdy,output wire req_we,
 output wire [31:0] req_addr,req_wstrb,
 output wire [255:0] req_wdata,output wire [15:0] req_tag,
 input wire rsp_v,output wire rsp_rdy,input wire [15:0] rsp_tag,
 input wire rsp_we,input wire [255:0] rsp_data,
 output reg [31:0] read_sectors,write_sectors,publication_sectors,
 output wire read_debt,write_debt
);
 localparam integer NV=(D+N-1)/N;
 localparam [3:0] IDLE=0,GAIN_REQ=1,GAIN_WAIT=2,GAIN_PUSH=3,START=4,
  DATA_REQ=5,DATA_WAIT=6,DATA_PUSH=7,DRAIN=8,
  WRITE_REQ=9,WRITE_WAIT=10,FENCE_REQ=11,FENCE_WAIT=12;
 reg [3:0] state;
 reg [31:0] jid,vmb,crb,nf,ep;
 reg [23:0] xb,yb,gb;
 reg [15:0] tag;
 reg [15:0] beat,word_index,output_index;
 reg [N*32-1:0] gain_buf,input_buf;
 reg [31:0] output_buf[0:D-1];
 reg [NV-1:0] landed;
 reg engine_finished;
 wire gain_ready,start_ready,in_ready,engine_busy,engine_done,engine_fault;
 wire y_valid,ro_valid,q_valid;
 wire [7:0] y_index;
 wire [N*32-1:0] y_data;
 wire [31:0] engine_id;
 wire legal_kind=(KIND==1 || KIND==2);
 assign cmd_ready=ENABLE && legal_kind && !busy && !fault && lease_grant && prior_route_drained;
 wire accepted=cmd_valid && cmd_ready;
 wire writing=state==WRITE_REQ || state==WRITE_WAIT;
 wire reading=state==GAIN_REQ || state==GAIN_WAIT || state==DATA_REQ || state==DATA_WAIT;
 wire fencing=state==FENCE_REQ || state==FENCE_WAIT;
 assign req_v=ENABLE && !fault && lease_grant &&
  (state==GAIN_REQ || state==DATA_REQ || state==WRITE_REQ || state==FENCE_REQ);
 assign req_we=writing;
 assign req_tag=tag;
 assign read_debt=(state==GAIN_WAIT || state==DATA_WAIT || state==FENCE_WAIT);
 assign write_debt=(state==WRITE_WAIT);
 // Widen before address arithmetic. Never alias overflowing/unaligned regions.
 wire [63:0] logical_word=writing||fencing ? {40'd0,yb}+output_index :
  (state==GAIN_REQ || state==GAIN_WAIT ? {40'd0,gb}:{40'd0,xb})+beat*N+word_index;
 wire [63:0] byte_address=(state==GAIN_REQ || state==GAIN_WAIT ? {32'd0,crb}:{32'd0,vmb})+(logical_word<<2);
 assign req_addr={byte_address[31:5],5'd0};
 wire [2:0] sector_word=byte_address[4:2];
 wire [15:0] extent_left=D-beat*N-word_index;
 wire [15:0] beat_left=N-word_index;
 wire [15:0] output_left=D-output_index;
 wire [15:0] sector_left=8-{13'd0,sector_word};
 wire [15:0] input_count=(extent_left<beat_left ? extent_left:beat_left);
 wire [15:0] count=writing||fencing ?
  (output_left<sector_left ? output_left:sector_left):
  (input_count<sector_left ? input_count:sector_left);
 reg [255:0] write_payload;
 reg [31:0] write_mask;
 integer k;
 always @* begin
  write_payload=0;write_mask=0;
  for(integer j=0;j<8;j=j+1) if(j<count && output_index+j<D) begin
   write_payload[(sector_word+j)*32+:32]=output_buf[output_index+j];
   write_mask[(sector_word+j)*4+:4]=4'hf;
  end
 end
 assign req_wdata=write_payload;
 assign req_wstrb=writing?write_mask:32'd0;
 wire expecting=read_debt||write_debt;
 wire matched=expecting && rsp_tag==tag && rsp_we==writing;
 assign rsp_rdy=ENABLE && !fault && lease_grant && matched;
 wire response=rsp_v&&rsp_rdy;
 wire [63:0] x_end={32'd0,vm_byte_base}+(({40'd0,xbase}+D)<<2);
 wire [63:0] y_end={32'd0,vm_byte_base}+(({40'd0,ybase}+D)<<2);
 wire [63:0] g_end={32'd0,cr_byte_base}+(({40'd0,gain_base}+D)<<2);
 wire command_bounds=(vm_byte_base[1:0]==0 && cr_byte_base[1:0]==0 &&
  x_end<=64'h100000000 && y_end<=64'h100000000 && g_end<=64'h100000000);
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE;busy<=0;done<=0;fault<=0;completion_id<=0;
   jid<=0;vmb<=0;crb<=0;nf<=0;ep<=0;xb<=0;yb<=0;gb<=0;tag<=0;
   beat<=0;word_index<=0;output_index<=0;gain_buf<=0;input_buf<=0;
   landed<=0;engine_finished<=0;read_sectors<=0;write_sectors<=0;publication_sectors<=0;
  end else if(ENABLE) begin
   done<=0;
   if(accepted) begin
    busy<=1;jid<=job_id;vmb<=vm_byte_base;crb<=cr_byte_base;
    xb<=xbase;yb<=ybase;gb<=gain_base;nf<=n_f;ep<=eps;
    beat<=0;word_index<=0;output_index<=0;gain_buf<=0;input_buf<=0;
    landed<=0;engine_finished<=0;read_sectors<=0;write_sectors<=0;publication_sectors<=0;
    if(!command_bounds) fault<=1;
    else state<=GAIN_REQ;
   end
   if(busy && !lease_grant) fault<=1;
   if(engine_fault || ro_valid || q_valid) fault<=1;
   // Foreign responses are held: no ACK edge, debt/producer remain unchanged.
   if(rsp_v && !matched) fault<=1;
   if(req_v && (byte_address[63:32]!=0 || count==0)) fault<=1;
   if(!fault && lease_grant) begin
    if(req_v && req_rdy) begin
     if(state==GAIN_REQ) state<=GAIN_WAIT;
     if(state==DATA_REQ) state<=DATA_WAIT;
     if(state==WRITE_REQ) state<=WRITE_WAIT;
     if(state==FENCE_REQ) state<=FENCE_WAIT;
    end
    if(response) begin
     tag<=tag+1;
     if(reading) begin
      read_sectors<=read_sectors+1;
      for(k=0;k<8;k=k+1) if(k<count) begin
       if(state==GAIN_WAIT) gain_buf[(word_index+k)*32+:32]<=rsp_data[(sector_word+k)*32+:32];
       else input_buf[(word_index+k)*32+:32]<=rsp_data[(sector_word+k)*32+:32];
      end
      word_index<=word_index+count;
      if(word_index+count==N || beat*N+word_index+count==D)
       state<=state==GAIN_WAIT?GAIN_PUSH:DATA_PUSH;
      else state<=state==GAIN_WAIT?GAIN_REQ:DATA_REQ;
     end
     if(state==WRITE_WAIT) begin write_sectors<=write_sectors+1;state<=FENCE_REQ;end
     if(state==FENCE_WAIT) begin
      for(k=0;k<8;k=k+1) if(k<count && rsp_data[(sector_word+k)*32+:32]!==output_buf[output_index+k]) fault<=1;
      publication_sectors<=publication_sectors+1;
      if(output_index+count==D) begin
       // Completion is conditional on the readback comparison, not ACK alone.
       state<=IDLE;busy<=0;done<=1;completion_id<=jid;
       for(k=0;k<8;k=k+1) if(k<count && rsp_data[(sector_word+k)*32+:32]!==output_buf[output_index+k]) begin
        state<=FENCE_WAIT;busy<=1;done<=0;
       end
      end else begin output_index<=output_index+count;state<=WRITE_REQ;end
     end
    end
    if(state==GAIN_PUSH && gain_ready) begin
     word_index<=0;gain_buf<=0;
     if(beat+1==NV) begin beat<=0;state<=START;end
     else begin beat<=beat+1;state<=GAIN_REQ;end
    end
    if(state==START && start_ready) begin beat<=0;word_index<=0;input_buf<=0;state<=DATA_REQ;end
    if(state==DATA_PUSH && in_ready) begin
     word_index<=0;input_buf<=0;
     if(beat+1==NV) state<=DRAIN;
     else begin beat<=beat+1;state<=DATA_REQ;end
    end
    if(y_valid) begin
     if(!busy || y_index>=NV || landed[y_index]) fault<=1;
     else begin
      landed[y_index]<=1;
      for(k=0;k<N;k=k+1) if(y_index*N+k<D) output_buf[y_index*N+k]<=y_data[k*32+:32];
     end
    end
    if(engine_done) begin
     if(engine_id!=jid) fault<=1;
     else engine_finished<=1;
    end
    if(state==DRAIN && engine_finished && (&landed)) begin output_index<=0;state<=WRITE_REQ;end
   end
  end
 end
 ot_hbm_accel_su_fused_stream #(.ENABLE(ENABLE),.KIND(KIND),.N(N),.D(D),.RD(0),.PUBLISH_QUANT(0)) u_engine (
  .clk(clk),.rst_n(rst_n),.cmd_valid(state==START && !fault),.cmd_id(jid),
  .reserve_grant(busy && lease_grant && !fault),.reserve_events(),.cmd_ready(start_ready),
  .busy(engine_busy),.done(engine_done),.completion_id(engine_id),
  .comb(512'd0),.post_pre(128'd0),.n_f(nf),.eps(ep),.lim(32'd0),.cos_t(32'd0),.sin_t(32'd0),
  .gain_valid(state==GAIN_PUSH && !fault),.gain_index(beat[7:0]),.gain_data(gain_buf),.gain_ready(gain_ready),
  .in_valid(state==DATA_PUSH && !fault),.in_ready(in_ready),.operands({{(3*N*32){1'b0}},input_buf}),
  .sink_ready(busy && lease_grant && !fault),.y_valid(y_valid),.ro_valid(ro_valid),.q_valid(q_valid),
  .y_index(y_index),.q_index(),.y_data(y_data),.ro_data(),.q_codes(),.q_exp(),.q_bf16(),.fault(engine_fault));
endmodule
