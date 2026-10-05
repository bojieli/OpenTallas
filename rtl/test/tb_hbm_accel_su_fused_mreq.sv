`timescale 1ns/1fs
// Changed finite transport gate: real request CDC, xbar/L2/shoreline backend,
// original saved operands, and expected data read only by this comparator.
module tb_hbm_accel_su_fused_mreq #(
 parameter integer N=256,D=1280,KIND=1,MEM_WORDS=32768
);
 reg clk=0,clk_m=0;always #0.416666667 clk=~clk;always #0.5 clk_m=~clk_m;
 reg rst_n=0,cmd_valid=0,lease=0;
 reg [31:0] cmd[0:7],expected[0:D-1];
 wire ready,busy,done,fault;
 wire req_v,req_rdy,req_we,rsp_v,rsp_rdy,rsp_we;
 wire [31:0] req_addr,req_strb;
 wire [255:0] req_data,rsp_data;
 wire [15:0] req_tag,rsp_tag;
 wire [31:0] completion,read_count,write_count,pub_count;
 wire rd_debt,wr_debt;
 integer neg=0;
 wire [15:0] checked_tag=neg==1 ? rsp_tag^16'h1:rsp_tag;
 ot_hbm_accel_su_fused_mreq #(.ENABLE(1),.N(N),.D(D),.KIND(KIND)) dut (
  .clk(clk),.rst_n(rst_n),.cmd_valid(cmd_valid),.lease_grant(lease),.prior_route_drained(!busy),
  .cmd_ready(ready),.busy(busy),.done(done),.fault(fault),.job_id(cmd[5]),
  .vm_byte_base(32'd0),.cr_byte_base(32'h100000),.xbase(cmd[0][23:0]),.ybase(cmd[3][23:0]),
  .gain_base(cmd[4][23:0]),.n_f(cmd[6]),.eps(cmd[7]),.completion_id(completion),
  .req_v(req_v),.req_rdy(req_rdy),.req_we(req_we),.req_addr(req_addr),.req_wstrb(req_strb),
  .req_wdata(req_data),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_we(rsp_we),
  .rsp_tag(checked_tag),.rsp_data(rsp_data),.read_sectors(read_count),.write_sectors(write_count),
  .publication_sectors(pub_count),.read_debt(rd_debt),.write_debt(wr_debt));
 wire mv,mr,mwe,rv,rr,rwe,cdc_fault,mem_fault;
 wire [31:0] ma,ms;wire [255:0] md,rd;wire [15:0] mt,rt;
 ot_gpu_mreq_cdc #(.ENABLE(1),.AW(3)) u_cdc (
  .clk_s(clk),.rst_s_n(rst_n),.clk_m(clk_m),.rst_m_n(rst_n),
  .s_req_v(req_v),.s_req_rdy(req_rdy),.s_req_we(req_we),.s_req_addr(req_addr),
  .s_req_wdata(req_data),.s_req_wstrb(req_strb),.s_req_tag(req_tag),
  .s_rsp_v(rsp_v),.s_rsp_rdy(rsp_rdy),.s_rsp_tag(rsp_tag),.s_rsp_we(rsp_we),.s_rsp_data(rsp_data),
  .m_req_v(mv),.m_req_rdy(mr),.m_req_we(mwe),.m_req_addr(ma),.m_req_wdata(md),.m_req_wstrb(ms),.m_req_tag(mt),
  .m_rsp_v(rv),.m_rsp_rdy(rr),.m_rsp_tag(rt),.m_rsp_we(rwe),.m_rsp_data(rd),.fault(cdc_fault));
 // Same source-selected backend classes, minimum one borrowed client. USE_W2
 // stays the current DS20 default0; this is not a claim about a W2 successor.
 ot_gpu_memsys #(.ENABLE(1),.NC(1),.NS(2),.NPC(2),.MEM_WORDS(MEM_WORDS),.USE_W2(0),.IMAGE_PREFIX("memory")) u_mem (
  .clk(clk_m),.rst_n(rst_n),.req_v(mv),.req_rdy(mr),.req_we(mwe),.req_addr(ma),
  .req_wdata(md),.req_wstrb(ms),.req_tag(mt),.rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_we(rwe),.rsp_data(rd),.fault(mem_fault));
 integer cyc=0,accept_cycle=-1,first_input=-1,last_input=-1,first_y=-1,last_y=-1;
 integer first_ack=-1,last_ack=-1,checked=0,errors=0,negative_cycles=0,requests=0;
 integer first_request=-1,wait_edges=0,request_cycle=0;
 initial begin
  if($value$plusargs("NEG=%d",neg)) begin end
  $readmemh("finite_cmd.mem",cmd);$readmemh("expected.mem",expected);
  repeat(5) @(negedge clk);rst_n=1;lease=1;cmd_valid=1;
  @(negedge clk);cmd_valid=0;
 end
 always @(posedge clk) begin
  cyc<=cyc+1;
  if(cmd_valid&&ready) begin accept_cycle=cyc;$display("FINITE_EVENT accept cycle=%0d time_ns=%0.9f",cyc,$realtime);end
  if(req_v&&req_rdy) begin
   requests=requests+1;request_cycle=cyc;
   if(first_request<0) first_request=cyc;
  end
  if(rsp_v&&rsp_rdy) wait_edges=wait_edges+cyc-request_cycle;
  if(dut.u_engine.gain_valid&&dut.u_engine.gain_ready)
   $display("FINITE_EVENT gain cycle=%0d beat=%0d time_ns=%0.9f",cyc,dut.beat,$realtime);
  if(dut.u_engine.in_valid&&dut.u_engine.in_ready) begin
   if(first_input<0) first_input=cyc;last_input=cyc;
   $display("FINITE_EVENT input cycle=%0d beat=%0d time_ns=%0.9f",cyc,dut.beat,$realtime);
  end
  if(dut.y_valid) begin
   if(first_y<0) first_y=cyc;last_y=cyc;
   $display("FINITE_EVENT engine_y cycle=%0d beat=%0d time_ns=%0.9f",cyc,dut.y_index,$realtime);
  end
  if(rsp_v&&rsp_rdy&&rsp_we) begin if(first_ack<0) first_ack=cyc;last_ack=cyc;end
  if(rsp_v&&rsp_rdy&&dut.state==12) begin
   for(integer k=0;k<8;k=k+1) if(k<dut.count) begin
    checked=checked+1;
    if(rsp_data[(dut.sector_word+k)*32+:32]!==expected[dut.output_index+k]) begin
     if(errors<5) $display("FINITE_MISMATCH index=%0d got=%08x want=%08x",dut.output_index+k,rsp_data[(dut.sector_word+k)*32+:32],expected[dut.output_index+k]);
     errors=errors+1;
    end
   end
  end
  if(cdc_fault||mem_fault) $fatal(1,"actual provider fault");
  if(fault) begin
   if(neg!=1) $fatal(1,"finite adapter fault");
   if(!busy||done||rsp_rdy||!rd_debt||requests!=1||req_v) $fatal(1,"foreign response advanced or released owner");
   negative_cycles=negative_cycles+1;
   if(negative_cycles==8) begin $display("FINITE_NEGATIVE_PASS foreign_tag held_cycles=8 requests=1 debt=1 completion=0");$finish;end
  end
 end
 always @(negedge clk) if(done) begin
  if(neg!=0||completion!=cmd[5]||rd_debt||wr_debt||busy||checked!=D||errors!=0) $fatal(1,"finite completion/cached check mismatch");
  $display("FINITE_END accepted=%0d first_request=%0d first_input=%0d last_input=%0d first_y=%0d last_y=%0d first_ack=%0d last_ack=%0d completion=%0d read_sectors=%0d write_sectors=%0d publication_sectors=%0d requests=%0d request_response_wait_edges=%0d checked=%0d errors=%0d debt=0 time_ns=%0.9f",accept_cycle,first_request,first_input,last_input,first_y,last_y,first_ack,last_ack,cyc,read_count,write_count,pub_count,requests,wait_edges,checked,errors,$realtime);
  lease=0;$display("PASS");$finish;
 end
endmodule
