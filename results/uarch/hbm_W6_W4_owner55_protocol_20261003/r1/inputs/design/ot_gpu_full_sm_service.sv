`timescale 1ns/1ps
module ot_gpu_full_sm_service #(parameter integer ENABLE=0,parameter integer ACK_ID=0) (
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
  assign identity_fault=identity_mismatch_fault || SIMD_ACK_mismatch || rf_identity_fault || ((state!=IDLE)&&simd_identity[55]);
  wire rr,rv,wr,wack;
  wire [4095:0] ra,rb;
  wire idle=state==IDLE;
  // Arbitration only at RF idle. An accepted SIMD reserves the entire RF
  // through its write ACK, preventing host modification between operands and writeback.
  wire choose_simd=simd_valid && (!host_rd_valid && !host_wr_valid || prefer_simd);
  assign simd_ready=idle && rr && wr && choose_simd;
  wire sg=simd_valid && simd_ready;
  assign host_rd_ready=idle && !choose_simd && rr;
  assign host_wr_ready=idle && !choose_simd && wr;
  assign host_rsp_valid=idle && rv;
  assign host_ack_valid=idle && wack;
  assign host_rsp_a=ra;assign host_rsp_b=rb;
  ot_gpu_rf_service #(.ACK_ID(1)) u_rf (
   .clk(clk),.rst_n(rst_n),
   .rd_valid(state==READ || (idle && !choose_simd && host_rd_valid)),.rd_ready(rr),
   .rd_a(idle?host_a:a_q),.rd_b(idle?host_b:b_q),
   .rsp_valid(rv),.rsp_ready(state==OPERATE || (idle && host_rsp_ready)),.rsp_a(ra),.rsp_b(rb),
   .wr_valid(state==WRITE || (idle && !choose_simd && host_wr_valid)),.wr_ready(wr),
   .wr_addr(idle?host_dst:dst_q),.wr_data(idle?host_wdata:result_q),
   .ack_valid(wack),.ack_ready(((state==ACK && SIMD_ACK_match) || (idle && host_ack_ready)) && !identity_fault),
   .wr_owner(idle?host_owner:simd_identity[54:9]),.ack_owner(rf_ack_owner),.ack_slot(rf_ack_slot),.ack_identity_fault(rf_identity_fault));
  wire [4095:0] add_result,mul_result;
  wire [127:0] add_fault,mul_fault;
  genvar l;
  for(l=0;l<128;l=l+1) begin:g_lane
   ot_gpu_fadd #(.LAT(7)) u_add (.clk(clk),.rst_n(rst_n),.v(state==OPERATE && rv && !mul_q),
    .a(ra[l*32+:32]),.b(rb[l*32+:32]),.y(add_result[l*32+:32]),.fault(add_fault[l]));
   ot_gpu_fmul #(.LAT(7)) u_mul (.clk(clk),.rst_n(rst_n),.v(state==OPERATE && rv && mul_q),
    .a(ra[l*32+:32]),.b(rb[l*32+:32]),.y(mul_result[l*32+:32]),.fault(mul_fault[l]));
  end
  reg [6:0] alu_valid;
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) alu_valid<=0;
   else alu_valid<={alu_valid[5:0],state==OPERATE && rv};
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
    READ: if(rr) state<=OPERATE;
    OPERATE: if(rv) state<=WAIT_ALU;
    WAIT_ALU: if(alu_valid[6]) begin
     result_q<=mul_q?mul_result:add_result;fault_q<=mul_q?(|mul_fault):(|add_fault);state<=WRITE;
    end
    WRITE: if(wr) state<=ACK;
    ACK: if(wack && !identity_fault && rf_ack_owner==simd_identity[54:9] && rf_ack_slot==dst_q) state<=DONE;
    DONE: if(simd_done_ready) state<=IDLE;
    default: state<=IDLE;
   endcase
   end
  end
  ot_gpu_scratch_service u_scratch (.clk(clk),.rst_n(rst_n),.valid(scratch_valid),.write(scratch_write),
   .ready(scratch_ready),.addr(scratch_addr),.wdata(scratch_wdata),.done(scratch_done),
   .done_ready(scratch_done_ready),.rdata(scratch_rdata));
 end else begin:g_disabled
  assign host_ack_owner=0;assign host_ack_slot=0;assign simd_done_owner=0;assign simd_done_slot=0;assign identity_fault=0;
  assign host_rd_ready=0;assign host_wr_ready=0;assign host_rsp_valid=0;assign host_ack_valid=0;
  assign host_rsp_a=0;assign host_rsp_b=0;assign simd_ready=0;assign simd_done=0;assign simd_fault=0;
  assign scratch_ready=0;assign scratch_done=0;assign scratch_rdata=0;
 end

end endgenerate
endmodule
`timescale 1ns/1ps
// Additive conventional GPU RF/SIMD/shared-memory provider, absent by default.
// Parent matrix ports/arithmetic stay in their original modules. Parent source
// join owns wiring these explicit ports and matrix result acceptance fences.
// No optional epilogue, gather, reduction, SFU or numerical-contract change.
module ot_gpu_full_sm_service_W4_original #(parameter integer ENABLE=0) (
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
 output wire scratch_done,input wire scratch_done_ready,output wire [511:0] scratch_rdata
);
 generate if(ENABLE) begin:g_enabled
  localparam IDLE=0, READ=1, OPERATE=2, WAIT_ALU=3, WRITE=4, ACK=5, DONE=6;
  reg [2:0] state;
  reg mul_q, fault_q, prefer_simd;
  reg [8:0] a_q,b_q,dst_q;
  reg [4095:0] result_q;
  wire rr,rv,wr,wack;
  wire [4095:0] ra,rb;
  wire idle=state==IDLE;
  // Arbitration only at RF idle. An accepted SIMD reserves the entire RF
  // through its write ACK, preventing host modification between operands and writeback.
  wire choose_simd=simd_valid && (!host_rd_valid && !host_wr_valid || prefer_simd);
  assign simd_ready=idle && rr && wr && choose_simd;
  wire sg=simd_valid && simd_ready;
  assign host_rd_ready=idle && !choose_simd && rr;
  assign host_wr_ready=idle && !choose_simd && wr;
  assign host_rsp_valid=idle && rv;
  assign host_ack_valid=idle && wack;
  assign host_rsp_a=ra;assign host_rsp_b=rb;
  ot_gpu_rf_service u_rf (
   .clk(clk),.rst_n(rst_n),
   .rd_valid(state==READ || (idle && !choose_simd && host_rd_valid)),.rd_ready(rr),
   .rd_a(idle?host_a:a_q),.rd_b(idle?host_b:b_q),
   .rsp_valid(rv),.rsp_ready(state==OPERATE || (idle && host_rsp_ready)),.rsp_a(ra),.rsp_b(rb),
   .wr_valid(state==WRITE || (idle && !choose_simd && host_wr_valid)),.wr_ready(wr),
   .wr_addr(idle?host_dst:dst_q),.wr_data(idle?host_wdata:result_q),
   .ack_valid(wack),.ack_ready(state==ACK || (idle && host_ack_ready)));
  wire [4095:0] add_result,mul_result;
  wire [127:0] add_fault,mul_fault;
  genvar l;
  for(l=0;l<128;l=l+1) begin:g_lane
   ot_gpu_fadd #(.LAT(7)) u_add (.clk(clk),.rst_n(rst_n),.v(state==OPERATE && rv && !mul_q),
    .a(ra[l*32+:32]),.b(rb[l*32+:32]),.y(add_result[l*32+:32]),.fault(add_fault[l]));
   ot_gpu_fmul #(.LAT(7)) u_mul (.clk(clk),.rst_n(rst_n),.v(state==OPERATE && rv && mul_q),
    .a(ra[l*32+:32]),.b(rb[l*32+:32]),.y(mul_result[l*32+:32]),.fault(mul_fault[l]));
  end
  reg [6:0] alu_valid;
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) alu_valid<=0;
   else alu_valid<={alu_valid[5:0],state==OPERATE && rv};
  end
  assign simd_done=state==DONE;assign simd_fault=fault_q;
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin state<=IDLE;mul_q<=0;fault_q<=0;prefer_simd<=0;a_q<=0;b_q<=0;dst_q<=0;end
   else case(state)
    IDLE: begin
     if(sg) begin state<=READ;mul_q<=simd_mul;a_q<=simd_a;b_q<=simd_b;dst_q<=simd_dst;fault_q<=0;prefer_simd<=0;end
     else if((host_rd_valid && host_rd_ready)||(host_wr_valid && host_wr_ready)) prefer_simd<=1;
    end
    READ: if(rr) state<=OPERATE;
    OPERATE: if(rv) state<=WAIT_ALU;
    WAIT_ALU: if(alu_valid[6]) begin
     result_q<=mul_q?mul_result:add_result;fault_q<=mul_q?(|mul_fault):(|add_fault);state<=WRITE;
    end
    WRITE: if(wr) state<=ACK;
    ACK: if(wack) state<=DONE;
    DONE: if(simd_done_ready) state<=IDLE;
    default: state<=IDLE;
   endcase
  end
  ot_gpu_scratch_service u_scratch (.clk(clk),.rst_n(rst_n),.valid(scratch_valid),.write(scratch_write),
   .ready(scratch_ready),.addr(scratch_addr),.wdata(scratch_wdata),.done(scratch_done),
   .done_ready(scratch_done_ready),.rdata(scratch_rdata));
 end else begin:g_disabled
  assign host_rd_ready=0;assign host_wr_ready=0;assign host_rsp_valid=0;assign host_ack_valid=0;
  assign host_rsp_a=0;assign host_rsp_b=0;assign simd_ready=0;assign simd_done=0;assign simd_fault=0;
  assign scratch_ready=0;assign scratch_done=0;assign scratch_rdata=0;
 end endgenerate
endmodule
