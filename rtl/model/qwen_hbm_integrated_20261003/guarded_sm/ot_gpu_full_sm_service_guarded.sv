`timescale 1ps/1ps
module ot_gpu_full_sm_service_guarded #(parameter integer ENABLE=0,ACK_ID=0,INSTANCE_ID=0,parameter bit OPT_CONTEXT=0)(
 input wire clk,
 input wire rst_n,
 input wire host_rd_valid,
 output wire host_rd_ready,
 input wire [8:0] host_a,
 input wire [8:0] host_b,
 output wire host_rsp_valid,
 input wire host_rsp_ready,
 output wire [4095:0] host_rsp_a,
 output wire [4095:0] host_rsp_b,
 input wire host_wr_valid,
 output wire host_wr_ready,
 input wire [8:0] host_dst,
 input wire [4095:0] host_wdata,
 output wire host_ack_valid,
 input wire host_ack_ready,
 input wire simd_valid,
 output wire simd_ready,
 input wire simd_mul,
 input wire [8:0] simd_a,
 input wire [8:0] simd_b,
 input wire [8:0] simd_dst,
 output wire simd_done,
 input wire simd_done_ready,
 output wire simd_fault,
 input wire scratch_valid,
 input wire scratch_write,
 output wire scratch_ready,
 input wire [9:0] scratch_addr,
 input wire [511:0] scratch_wdata,
 output wire scratch_done,
 input wire scratch_done_ready,
 output wire [511:0] scratch_rdata,
 input wire [45:0] host_owner,
 input wire [45:0] simd_owner,
 output wire [45:0] host_ack_owner,
 output wire [45:0] simd_done_owner,
 output wire [8:0] host_ack_slot,
 output wire [8:0] simd_done_slot,
 output wire identity_fault,
 input wire simd_context_permit,
 input wire rd_permit,
 input wire wr_permit,
 input wire rf_rsp_allow,
 input wire rf_ack_allow,
 input wire simd_binding_valid,
 input wire simd_KV_related,
 input wire [63:0] simd_source_identity,
 input wire [19:0] simd_key,
 input wire host_rd_binding_valid,
 input wire host_rd_KV_related,
 input wire [63:0] host_rd_identity,
 input wire [19:0] host_rd_key,
 input wire host_wr_binding_valid,
 input wire host_wr_KV_related,
 input wire [63:0] host_wr_identity,
 input wire [19:0] host_wr_key,
 input wire host_rd_continuation_valid,
 input wire host_wr_continuation_valid,
 output wire rf_write_accept,
 output wire [54:0] rf_write_owner55,
 output wire rf_ack_valid,
 output wire rf_ack_accept,
 output wire [54:0] rf_ack_owner55,
 output wire rf_ack_fault,
 output wire rf_read_accept,
 output wire [8:0] rf_read_a,
 output wire [8:0] rf_read_b,
 output wire rf_rsp_valid,
 output wire rf_rsp_accept,
 output wire simd_context_accept,
 output wire [54:0] simd_context_owner55,
 output wire simd_context_retire,
 output wire [54:0] simd_retire_owner55,
 output wire wr_continuation_valid,
 output wire wr_continuation_source,
 output wire rd_continuation_valid,
 output wire rd_continuation_source,
 output wire [54:0] rd_context_owner55,
 output wire [63:0] wr_context_identity,
 output wire [19:0] wr_context_key,
 output wire wr_context_binding_valid,
 output wire wr_context_KV_related,
 output wire [63:0] rd_context_identity,
 output wire [19:0] rd_context_key,
 output wire rd_context_binding_valid,
 output wire rd_context_KV_related
);
generate if(!OPT_CONTEXT)begin:original
assign rf_write_accept='0;
assign rf_write_owner55='0;
assign rf_ack_valid='0;
assign rf_ack_accept='0;
assign rf_ack_owner55='0;
assign rf_ack_fault='0;
assign rf_read_accept='0;
assign rf_read_a='0;
assign rf_read_b='0;
assign rf_rsp_valid='0;
assign rf_rsp_accept='0;
assign simd_context_accept='0;
assign simd_context_owner55='0;
assign simd_context_retire='0;
assign simd_retire_owner55='0;
assign wr_continuation_valid='0;
assign wr_continuation_source='0;
assign rd_continuation_valid='0;
assign rd_continuation_source='0;
assign rd_context_owner55='0;
assign wr_context_identity='0;
assign wr_context_key='0;
assign wr_context_binding_valid='0;
assign wr_context_KV_related='0;
assign rd_context_identity='0;
assign rd_context_key='0;
assign rd_context_binding_valid='0;
assign rd_context_KV_related='0;
ot_gpu_full_sm_service #(.ENABLE(ENABLE),.ACK_ID(ACK_ID)) baseline(.clk(clk),
.rst_n(rst_n),
.host_rd_valid(host_rd_valid),
.host_rd_ready(host_rd_ready),
.host_a(host_a),
.host_b(host_b),
.host_rsp_valid(host_rsp_valid),
.host_rsp_ready(host_rsp_ready),
.host_rsp_a(host_rsp_a),
.host_rsp_b(host_rsp_b),
.host_wr_valid(host_wr_valid),
.host_wr_ready(host_wr_ready),
.host_dst(host_dst),
.host_wdata(host_wdata),
.host_ack_valid(host_ack_valid),
.host_ack_ready(host_ack_ready),
.simd_valid(simd_valid),
.simd_ready(simd_ready),
.simd_mul(simd_mul),
.simd_a(simd_a),
.simd_b(simd_b),
.simd_dst(simd_dst),
.simd_done(simd_done),
.simd_done_ready(simd_done_ready),
.simd_fault(simd_fault),
.scratch_valid(scratch_valid),
.scratch_write(scratch_write),
.scratch_ready(scratch_ready),
.scratch_addr(scratch_addr),
.scratch_wdata(scratch_wdata),
.scratch_done(scratch_done),
.scratch_done_ready(scratch_done_ready),
.scratch_rdata(scratch_rdata),
.host_owner(host_owner),
.simd_owner(simd_owner),
.host_ack_owner(host_ack_owner),
.simd_done_owner(simd_done_owner),
.host_ack_slot(host_ack_slot),
.simd_done_slot(simd_done_slot),
.identity_fault(identity_fault));
end else begin:guarded
ot_gpu_full_sm_service_guarded_context #(.ENABLE(ENABLE),.ACK_ID(ACK_ID),.INSTANCE_ID(INSTANCE_ID)) actual(.clk(clk),
.rst_n(rst_n),
.host_rd_valid(host_rd_valid),
.host_rd_ready(host_rd_ready),
.host_a(host_a),
.host_b(host_b),
.host_rsp_valid(host_rsp_valid),
.host_rsp_ready(host_rsp_ready),
.host_rsp_a(host_rsp_a),
.host_rsp_b(host_rsp_b),
.host_wr_valid(host_wr_valid),
.host_wr_ready(host_wr_ready),
.host_dst(host_dst),
.host_wdata(host_wdata),
.host_ack_valid(host_ack_valid),
.host_ack_ready(host_ack_ready),
.simd_valid(simd_valid),
.simd_ready(simd_ready),
.simd_mul(simd_mul),
.simd_a(simd_a),
.simd_b(simd_b),
.simd_dst(simd_dst),
.simd_done(simd_done),
.simd_done_ready(simd_done_ready),
.simd_fault(simd_fault),
.scratch_valid(scratch_valid),
.scratch_write(scratch_write),
.scratch_ready(scratch_ready),
.scratch_addr(scratch_addr),
.scratch_wdata(scratch_wdata),
.scratch_done(scratch_done),
.scratch_done_ready(scratch_done_ready),
.scratch_rdata(scratch_rdata),
.host_owner(host_owner),
.simd_owner(simd_owner),
.host_ack_owner(host_ack_owner),
.simd_done_owner(simd_done_owner),
.host_ack_slot(host_ack_slot),
.simd_done_slot(simd_done_slot),
.identity_fault(identity_fault),
.simd_context_permit(simd_context_permit),
.rd_permit(rd_permit),
.wr_permit(wr_permit),
.rf_rsp_allow(rf_rsp_allow),
.rf_ack_allow(rf_ack_allow),
.simd_binding_valid(simd_binding_valid),
.simd_KV_related(simd_KV_related),
.simd_source_identity(simd_source_identity),
.simd_key(simd_key),
.host_rd_binding_valid(host_rd_binding_valid),
.host_rd_KV_related(host_rd_KV_related),
.host_rd_identity(host_rd_identity),
.host_rd_key(host_rd_key),
.host_wr_binding_valid(host_wr_binding_valid),
.host_wr_KV_related(host_wr_KV_related),
.host_wr_identity(host_wr_identity),
.host_wr_key(host_wr_key),
.host_rd_continuation_valid(host_rd_continuation_valid),
.host_wr_continuation_valid(host_wr_continuation_valid),
.rf_write_accept(rf_write_accept),
.rf_write_owner55(rf_write_owner55),
.rf_ack_valid(rf_ack_valid),
.rf_ack_accept(rf_ack_accept),
.rf_ack_owner55(rf_ack_owner55),
.rf_ack_fault(rf_ack_fault),
.rf_read_accept(rf_read_accept),
.rf_read_a(rf_read_a),
.rf_read_b(rf_read_b),
.rf_rsp_valid(rf_rsp_valid),
.rf_rsp_accept(rf_rsp_accept),
.simd_context_accept(simd_context_accept),
.simd_context_owner55(simd_context_owner55),
.simd_context_retire(simd_context_retire),
.simd_retire_owner55(simd_retire_owner55),
.wr_continuation_valid(wr_continuation_valid),
.wr_continuation_source(wr_continuation_source),
.rd_continuation_valid(rd_continuation_valid),
.rd_continuation_source(rd_continuation_source),
.rd_context_owner55(rd_context_owner55),
.wr_context_identity(wr_context_identity),
.wr_context_key(wr_context_key),
.wr_context_binding_valid(wr_context_binding_valid),
.wr_context_KV_related(wr_context_KV_related),
.rd_context_identity(rd_context_identity),
.rd_context_key(rd_context_key),
.rd_context_binding_valid(rd_context_binding_valid),
.rd_context_KV_related(rd_context_KV_related));
end endgenerate
endmodule
`timescale 1ns/1ps
module ot_gpu_full_sm_service_guarded_context #(parameter integer ENABLE=0,parameter integer ACK_ID=0,parameter integer INSTANCE_ID=0) (
  input wire simd_context_permit,
 input wire rd_permit,
 input wire wr_permit,
 input wire rf_rsp_allow,
 input wire rf_ack_allow,
 input wire simd_binding_valid,
 input wire simd_KV_related,
 input wire [63:0] simd_source_identity,
 input wire [19:0] simd_key,
 input wire host_rd_binding_valid,
 input wire host_rd_KV_related,
 input wire [63:0] host_rd_identity,
 input wire [19:0] host_rd_key,
 input wire host_wr_binding_valid,
 input wire host_wr_KV_related,
 input wire [63:0] host_wr_identity,
 input wire [19:0] host_wr_key,
 input wire host_rd_continuation_valid,
 input wire host_wr_continuation_valid,
 output wire rf_write_accept,
 output wire [54:0] rf_write_owner55,
 output wire rf_ack_valid,
 output wire rf_ack_accept,
 output wire [54:0] rf_ack_owner55,
 output wire rf_ack_fault,
 output wire rf_read_accept,
 output wire [8:0] rf_read_a,
 output wire [8:0] rf_read_b,
 output wire rf_rsp_valid,
 output wire rf_rsp_accept,
 output wire simd_context_accept,
 output wire [54:0] simd_context_owner55,
 output wire simd_context_retire,
 output wire [54:0] simd_retire_owner55,
 output wire wr_continuation_valid,
 output wire wr_continuation_source,
 output wire rd_continuation_valid,
 output wire rd_continuation_source,
 output wire [54:0] rd_context_owner55,
 output wire [63:0] wr_context_identity,
 output wire [19:0] wr_context_key,
 output wire wr_context_binding_valid,
 output wire wr_context_KV_related,
 output wire [63:0] rd_context_identity,
 output wire [19:0] rd_context_key,
 output wire rd_context_binding_valid,
 output wire rd_context_KV_related,
 input wire clk,rst_n,
 input wire host_rd_valid, output wire host_rd_ready,
 input wire [8:0] host_a,host_b,
 output wire host_rsp_valid, input wire host_rsp_ready,
 output wire [4095:0] host_rsp_a,host_rsp_b,
 input wire host_wr_valid, output wire host_wr_ready,
 input wire [8:0] host_dst, input wire [4095:0] host_wdata,
 output wire host_ack_valid, input wire host_ack_ready,
 input wire simd_valid, output wire simd_ready,
 input wire simd_mul, input wire [8:0] simd_a,simd_b,simd_dst,
 output wire simd_done, input wire simd_done_ready, output wire simd_fault,
 input wire scratch_valid,scratch_write,output wire scratch_ready,
 input wire [9:0] scratch_addr,input wire [511:0] scratch_wdata,
 output wire scratch_done,input wire scratch_done_ready,output wire [511:0] scratch_rdata,
 input wire [45:0] host_owner,simd_owner,
 output wire [45:0] host_ack_owner,simd_done_owner,
 output wire [8:0] host_ack_slot,simd_done_slot,output wire identity_fault
);
function automatic [71:0] w4_encode(input [54:0] payload);
 reg [63:0] data;reg [71:0] c;reg parity;integer p,k,j;
 begin
  data={9'b0,payload};c=0;j=0;
  for(p=1;p<=71;p=p+1) if((p&(p-1))!=0)begin c[p-1]=data[j];j=j+1;end
  for(k=1;k<=64;k=k*2)begin parity=0;for(p=1;p<=71;p=p+1)if((p&k)!=0)parity=parity^c[p-1];c[k-1]=parity;end
  c[71]=^c[70:0];w4_encode=c;
 end
endfunction
function automatic [55:0] w4_decode(input [71:0] word);
 reg [71:0] c;reg [63:0] data;reg parity,bad;integer p,k,j,syndrome;
 begin
  c=word;syndrome=0;
  for(k=1;k<=64;k=k*2)begin parity=0;for(p=1;p<=71;p=p+1)if((p&k)!=0)parity=parity^c[p-1];if(parity)syndrome=syndrome+k;end
  bad=0;
  if((^c)==1'b1)begin if(syndrome>0&&syndrome<=71)c[syndrome-1]=~c[syndrome-1];else if(syndrome>71)bad=1;end
  else if(syndrome!=0)bad=1;
  data=0;j=0;for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin data[j]=c[p-1];j=j+1;end
  if(data[63:55]!=0)bad=1;
  w4_decode={bad,data[54:0]};
 end
endfunction

initial if(ACK_ID!=1)$fatal(1,"guarded context requires actual ACK_ID1");
generate if(ACK_ID==0)begin:g_original
assign host_ack_owner=0;assign host_ack_slot=0;assign simd_done_owner=0;assign simd_done_slot=0;assign identity_fault=0;
ot_gpu_full_sm_service_W4_original #(.ENABLE(ENABLE)) u_original(.clk(clk),
.rst_n(rst_n),
.host_rd_valid(host_rd_valid),
.host_rd_ready(host_rd_ready),
.host_a(host_a),
.host_b(host_b),
.host_rsp_valid(host_rsp_valid),
.host_rsp_ready(host_rsp_ready),
.host_rsp_a(host_rsp_a),
.host_rsp_b(host_rsp_b),
.host_wr_valid(host_wr_valid),
.host_wr_ready(host_wr_ready),
.host_dst(host_dst),
.host_wdata(host_wdata),
.host_ack_valid(host_ack_valid),
.host_ack_ready(host_ack_ready),
.simd_valid(simd_valid),
.simd_ready(simd_ready),
.simd_mul(simd_mul),
.simd_a(simd_a),
.simd_b(simd_b),
.simd_dst(simd_dst),
.simd_done(simd_done),
.simd_done_ready(simd_done_ready),
.simd_fault(simd_fault),
.scratch_valid(scratch_valid),
.scratch_write(scratch_write),
.scratch_ready(scratch_ready),
.scratch_addr(scratch_addr),
.scratch_wdata(scratch_wdata),
.scratch_done(scratch_done),
.scratch_done_ready(scratch_done_ready),
.scratch_rdata(scratch_rdata));
end else begin:g_identity

 if(ENABLE) begin:g_enabled
  localparam IDLE=0, READ=1, OPERATE=2, WAIT_ALU=3, WRITE=4, ACK=5, DONE=6;
  reg [2:0] state;
  reg mul_q, fault_q, prefer_simd;
  reg [8:0] a_q,b_q,dst_q;
  reg [4095:0] result_q;
  reg [71:0] simd_identity_q;
  wire [55:0] simd_identity=w4_decode(simd_identity_q);
  wire [45:0] rf_ack_owner;wire [8:0] rf_ack_slot;wire rf_identity_fault;
  reg identity_mismatch_fault;
  wire SIMD_ACK_match=rf_ack_owner==simd_identity[54:9] && rf_ack_slot==dst_q;
  wire SIMD_ACK_mismatch=state==ACK && wack && !rf_identity_fault && !SIMD_ACK_match;
  assign host_ack_owner=host_ack_valid?rf_ack_owner:46'd0;
  assign host_ack_slot=host_ack_valid?rf_ack_slot:9'd0;
  assign simd_done_owner=simd_done?simd_identity[54:9]:46'd0;
  assign simd_done_slot=simd_done?simd_identity[8:0]:9'd0;
  assign identity_fault=!ctx_clean || identity_mismatch_fault || SIMD_ACK_mismatch || rf_identity_fault || ((state!=IDLE)&&simd_identity[55]);
  wire rr,rv,wr,wack;
  wire [4095:0] ra,rb;
  wire idle=state==IDLE;
  // Arbitration only at RF idle. An accepted SIMD reserves the entire RF
  // through its write ACK, preventing host modification between operands and writeback.
  wire choose_simd=simd_valid && simd_context_permit && ctx_clean && (!host_rd_valid && !host_wr_valid || prefer_simd);
  assign simd_ready=idle && rr && wr && choose_simd;
  wire sg=simd_valid && simd_ready;

  wire [85:0] ctx;
  wire ctx_clean;
  wire ctx_retire=state==DONE && simd_done_ready;
  ot_gpu_qwen_guard_context_record #(.BITS(86),.INDEX(INSTANCE_ID)) context_record(
   .clk(clk),.por_n(rst_n),.write_enable(sg || ctx_retire),
   .next_data(ctx_retire ? 86'b0 : {simd_binding_valid,simd_KV_related,simd_key,simd_source_identity}),.data(ctx),.clean(ctx_clean));
  assign rf_read_accept=(state==READ || (idle && !choose_simd && host_rd_valid)) && rd_permit && ctx_clean && rr;
  assign rf_write_accept=(state==WRITE || (idle && !choose_simd && host_wr_valid)) && wr_permit && ctx_clean && wr;
  assign rf_read_a=idle ? host_a : a_q;assign rf_read_b=idle ? host_b : b_q;
  assign rf_write_owner55=idle ? {host_owner,host_dst} : simd_identity[54:0];
  assign rf_ack_valid=wack;assign rf_ack_owner55={rf_ack_owner,rf_ack_slot};assign rf_ack_fault=identity_fault;
  assign rf_ack_accept=wack && (((state==ACK && SIMD_ACK_match) || (idle && host_ack_ready)) && !identity_fault && rf_ack_allow && ctx_clean);
  assign rf_rsp_valid=rv;assign rf_rsp_accept=rv && (state==OPERATE || (idle && host_rsp_ready)) && rf_rsp_allow && ctx_clean;
  assign simd_context_accept=sg;assign simd_context_owner55={simd_owner,simd_dst};
  assign simd_context_retire=ctx_retire;assign simd_retire_owner55=simd_identity[54:0];
  assign wr_continuation_valid=idle ? host_wr_continuation_valid : state==WRITE;
  assign wr_continuation_source=!idle;
  assign rd_continuation_valid=idle ? host_rd_continuation_valid : state==READ;
  assign rd_continuation_source=!idle;
  assign rd_context_owner55=idle ? {host_owner,host_dst} : simd_identity[54:0];
  assign wr_context_identity=idle ? host_wr_identity : ctx[63:0];assign wr_context_key=idle ? host_wr_key : ctx[83:64];
  assign wr_context_KV_related=idle ? host_wr_KV_related : ctx[84];assign wr_context_binding_valid=idle ? host_wr_binding_valid : ctx[85];
  assign rd_context_identity=idle ? host_rd_identity : ctx[63:0];assign rd_context_key=idle ? host_rd_key : ctx[83:64];
  assign rd_context_KV_related=idle ? host_rd_KV_related : ctx[84];assign rd_context_binding_valid=idle ? host_rd_binding_valid : ctx[85];

  assign host_rd_ready=idle && !choose_simd && rr && rd_permit && ctx_clean;
  assign host_wr_ready=idle && !choose_simd && wr && wr_permit && ctx_clean;
  assign host_rsp_valid=idle && rv;
  assign host_ack_valid=idle && wack;
  assign host_rsp_a=ra;assign host_rsp_b=rb;
  ot_gpu_rf_service #(.ACK_ID(1)) u_rf (
   .clk(clk),.rst_n(rst_n),
   .rd_valid((state==READ || (idle && !choose_simd && host_rd_valid)) && rd_permit && ctx_clean),.rd_ready(rr),
   .rd_a(idle?host_a:a_q),.rd_b(idle?host_b:b_q),
   .rsp_valid(rv),.rsp_ready((state==OPERATE || (idle && host_rsp_ready)) && rf_rsp_allow && ctx_clean),.rsp_a(ra),.rsp_b(rb),
   .wr_valid((state==WRITE || (idle && !choose_simd && host_wr_valid)) && wr_permit && ctx_clean),.wr_ready(wr),
   .wr_addr(idle?host_dst:dst_q),.wr_data(idle?host_wdata:result_q),
   .ack_valid(wack),.ack_ready(((state==ACK && SIMD_ACK_match) || (idle && host_ack_ready)) && !identity_fault && rf_ack_allow && ctx_clean),
   .wr_owner(idle?host_owner:simd_identity[54:9]),.ack_owner(rf_ack_owner),.ack_slot(rf_ack_slot),.ack_identity_fault(rf_identity_fault));
  wire [4095:0] add_result,mul_result;
  wire [127:0] add_fault,mul_fault;
  genvar l;
  for(l=0;l<128;l=l+1) begin:g_lane
   ot_gpu_fadd #(.LAT(7)) u_add (.clk(clk),.rst_n(rst_n),.v(state==OPERATE && rv && rf_rsp_allow && ctx_clean && !mul_q),
    .a(ra[l*32+:32]),.b(rb[l*32+:32]),.y(add_result[l*32+:32]),.fault(add_fault[l]));
   ot_gpu_fmul #(.LAT(7)) u_mul (.clk(clk),.rst_n(rst_n),.v(state==OPERATE && rv && rf_rsp_allow && ctx_clean && mul_q),
    .a(ra[l*32+:32]),.b(rb[l*32+:32]),.y(mul_result[l*32+:32]),.fault(mul_fault[l]));
  end
  reg [6:0] alu_valid;
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) alu_valid<=0;
   else alu_valid<={alu_valid[5:0],state==OPERATE && rv && rf_rsp_allow && ctx_clean};
  end
  assign simd_done=state==DONE;assign simd_fault=fault_q;
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin identity_mismatch_fault<=0;simd_identity_q<=0;state<=IDLE;mul_q<=0;fault_q<=0;prefer_simd<=0;a_q<=0;b_q<=0;dst_q<=0;end
   else begin
    if(SIMD_ACK_mismatch)identity_mismatch_fault<=1;
    case(state)
    IDLE: begin
     if(sg) begin simd_identity_q<=w4_encode({simd_owner,simd_dst});state<=READ;mul_q<=simd_mul;a_q<=simd_a;b_q<=simd_b;dst_q<=simd_dst;fault_q<=0;prefer_simd<=0;end
     else if((host_rd_valid && host_rd_ready)||(host_wr_valid && host_wr_ready)) prefer_simd<=1;
    end
    READ: if(rr && rd_permit && ctx_clean) state<=OPERATE;
    OPERATE: if(rv && rf_rsp_allow && ctx_clean) state<=WAIT_ALU;
    WAIT_ALU: if(alu_valid[6]) begin
     result_q<=mul_q?mul_result:add_result;fault_q<=mul_q?(|mul_fault):(|add_fault);state<=WRITE;
    end
    WRITE: if(wr && wr_permit && ctx_clean) state<=ACK;
    ACK: if(wack && rf_ack_allow && ctx_clean && !identity_fault && rf_ack_owner==simd_identity[54:9] && rf_ack_slot==dst_q) state<=DONE;
    DONE: if(simd_done_ready) state<=IDLE;
    default: state<=IDLE;
   endcase
   end
  end
  ot_gpu_scratch_service u_scratch (.clk(clk),.rst_n(rst_n),.valid(scratch_valid),.write(scratch_write),
   .ready(scratch_ready),.addr(scratch_addr),.wdata(scratch_wdata),.done(scratch_done),
   .done_ready(scratch_done_ready),.rdata(scratch_rdata));
 end else begin:g_disabled
assign rf_write_accept='0;
assign rf_write_owner55='0;
assign rf_ack_valid='0;
assign rf_ack_accept='0;
assign rf_ack_owner55='0;
assign rf_ack_fault='0;
assign rf_read_accept='0;
assign rf_read_a='0;
assign rf_read_b='0;
assign rf_rsp_valid='0;
assign rf_rsp_accept='0;
assign simd_context_accept='0;
assign simd_context_owner55='0;
assign simd_context_retire='0;
assign simd_retire_owner55='0;
assign wr_continuation_valid='0;
assign wr_continuation_source='0;
assign rd_continuation_valid='0;
assign rd_continuation_source='0;
assign rd_context_owner55='0;
assign wr_context_identity='0;
assign wr_context_key='0;
assign wr_context_binding_valid='0;
assign wr_context_KV_related='0;
assign rd_context_identity='0;
assign rd_context_key='0;
assign rd_context_binding_valid='0;
assign rd_context_KV_related='0;
  assign host_ack_owner=0;assign host_ack_slot=0;assign simd_done_owner=0;assign simd_done_slot=0;assign identity_fault=0;
  assign host_rd_ready=0;assign host_wr_ready=0;assign host_rsp_valid=0;assign host_ack_valid=0;
  assign host_rsp_a=0;assign host_rsp_b=0;assign simd_ready=0;assign simd_done=0;assign simd_fault=0;
  assign scratch_ready=0;assign scratch_done=0;assign scratch_rdata=0;
 end

end endgenerate
endmodule

module ot_gpu_qwen_guard_context_record #(
 parameter integer BITS=86, WORDS=(BITS+43)/44, INDEX=0
)(input wire clk,por_n,write_enable,input wire [BITS-1:0] next_data,
 output wire [BITS-1:0] data,output wire clean);
 reg [WORDS*72-1:0] coded;
 wire [WORDS*44-1:0] padded={{(WORDS*44-BITS){1'b0}},next_data};
 wire [WORDS*44-1:0] decoded;
 wire [WORDS*72-1:0] encoded;
 wire [WORDS-1:0] word_clean;
 function automatic [71:0] reset_word(input integer word_index);
  reg [63:0] value;reg [71:0] result;integer p,j,k;
  begin
   value={3'd6,10'(word_index),7'(INDEX),44'b0};result=0;j=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin result[p-1]=value[j];j=j+1;end
   for(k=0;k<7;k=k+1)begin
    for(p=1;p<=71;p=p+1)if((p&(1<<k))!=0)result[(1<<k)-1]=result[(1<<k)-1]^result[p-1];
   end
   result[71]=^result[70:0];reset_word=result;
  end
 endfunction
 for(genvar w=0;w<WORDS;w=w+1)begin:g_words
  wire [6:0] syndrome;
  wire odd,cc,ce,ue,seal_ok,pad_ok;
  wire [71:0] repaired;
  ot_w2_sealed_secded72 #(.PC_ID(7'(INDEX)),.WORD_INDEX(10'(w)),.WORD_KIND(3'd6),
   .PAYLOAD_BITS(w==WORDS-1 ? BITS-w*44 : 44)) codec(
    .payload(padded[w*44+:44]),.current_word(coded[w*72+:72]),.encoded_word(encoded[w*72+:72]),
    .syndrome(syndrome),.overall_odd(odd),.clean(cc),.correctable(ce),.uncorrectable(ue),
    .seal_ok(seal_ok),.padding_ok(pad_ok),.release_clean(word_clean[w]),
    .repaired_payload(decoded[w*44+:44]),.repaired_word(repaired));
  localparam [71:0] RESET_CODE=reset_word(w);
  always @(posedge clk or negedge por_n)
   if(!por_n)coded[w*72+:72]<=RESET_CODE;
   else if(write_enable && clean)coded[w*72+:72]<=encoded[w*72+:72];
 end
 assign data=decoded[BITS-1:0];
 assign clean=&word_clean;
endmodule

