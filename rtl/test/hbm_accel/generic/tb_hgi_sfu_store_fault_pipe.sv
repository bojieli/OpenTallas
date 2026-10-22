`timescale 1ns/1ps
// HBMb/HC-SFU 10-21: FPIPE=1 operand-store fault vs the released FPIPE=0 form on identical stimuli. Every fault class
// (per lane: VM write range, read range, read source, scalar identity; store-local: stage range, drain range) must raise
// the FPIPE=0 fault at edge t and the FPIPE=1 fault at exactly edge t+AGE (AGE=5), never earlier; idle = no fault.
module tb_hgi_sfu_store_fault_pipe;
 localparam LWB=15, AGE=5;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0;
 reg [3:0] scalar_load=0,scalar_enable=0;
 wire [31:0] scalar_load_leaves,scalar_enable_leaves;
 for(genvar g=0;g<4;g=g+1)begin:g_sc
  assign scalar_load_leaves[8*g+:8]={8{scalar_load[g]}};
  assign scalar_enable_leaves[8*g+:8]={8{scalar_enable[g]}};
 end
 reg [95:0] scalar_addr=0; reg [127:0] scalar_data=0;
 reg [63:0] rd_re=0; reg [1535:0] rd_addr=0; reg [127:0] rd_src=0;
 reg [15:0] vm_we=0; reg [383:0] vm_addr=0; reg [511:0] vm_data=0;
 reg [7:0] stage_v=0; reg [15:0] stage_group=0; reg [8*LWB-1:0] stage_addr=0; reg [2047:0] stage_data=0;
 reg [1:0] drain_v=0; reg [2*LWB-1:0] drain_addr=0;
 wire [31:0] drain_v_leaves; wire [2*16*LWB-1:0] drain_addr_leaves; wire [8*16*4-1:0] stage_lo_replicas;
 for(genvar sec=0;sec<2;sec=sec+1)for(genvar b=0;b<16;b=b+1)begin:g_dc
  assign drain_v_leaves[sec*16+b]=drain_v[sec]; assign drain_addr_leaves[(sec*16+b)*LWB+:LWB]=drain_addr[sec*LWB+:LWB];
 end
 for(genvar s=0;s<8;s=s+1)for(genvar cp=0;cp<16;cp=cp+1)begin:g_sl
  assign stage_lo_replicas[4*(s*16+cp)+:4]=stage_addr[LWB*s+:4];
 end
 wire f0,f1; wire [2047:0] q0,q1; wire [511:0] d0,d1; wire [1:0] r0,r1;
`define OT_STORE(NAME,FP,F,Q,D,R) \
 ot_hgi_sfu_static_operand_store #(.NATIVE32(1),.WROT(1),.WPIPE(1),.FPIPE(FP)) NAME(.clk(clk),.rst_n(rst_n),.clk_grp({5{clk}}),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(Q), \
 .vm_we(vm_we),.vm_waddr(vm_addr),.vm_wdata(vm_data),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_load_leaves(scalar_load_leaves),.scalar_enable_leaves(scalar_enable_leaves),.scalar_addr(scalar_addr),.scalar_data(scalar_data),.stage_v(stage_v),.stage_group(stage_group), \
 .stage_addr(stage_addr),.stage_lo_replicas(stage_lo_replicas),.stage_mask(64'hffffffffffffffff),.stage_data(stage_data), \
 .drain_v(drain_v),.drain_v_leaves(drain_v_leaves),.drain_addr_leaves(drain_addr_leaves),.drain_addr(drain_addr),.drain_data(D),.drain_result_v(R),.fault(F));
 `OT_STORE(u_ref,0,f0,q0,d0,r0)
 `OT_STORE(u_pipe,1,f1,q1,d1,r1)
 integer cyc=0, t0, t1, episodes=0;
 always @(posedge clk) cyc<=cyc+1;
 task automatic clear; begin
  scalar_load=0;scalar_enable=0;rd_re=0;rd_addr=0;rd_src=0;vm_we=0;vm_addr=0;stage_v=0;stage_addr=0;drain_v=0;drain_addr=0;
 end endtask
 task automatic episode(input integer cls, input integer l); begin
  clear; rst_n=0; repeat(3)@(negedge clk); rst_n=1; repeat(4)@(negedge clk);
  if(f0||f1)$fatal(1,"FPIPE_IDLE_FAULT cls=%0d lane=%0d",cls,l);
  case(cls)
   0: begin vm_we[l]=1; vm_addr[24*l+:24]=24'h800000; end
   1: begin rd_re[4*l+1]=1; rd_addr[24*(4*l+1)+:24]=24'h400000; end
   2: begin rd_re[4*l+2]=1; rd_src[8*l+2*2+:2]=2'd1; end
   3: begin rd_re[4*l+3]=1; scalar_enable[3]=1; end              // scalar not loaded -> identity fault
   4: begin stage_v[l%8]=1; stage_addr[LWB*(l%8)+:LWB]={LWB{1'b1}}; end
   5: begin drain_v[l%2]=1; drain_addr[LWB*(l%2)+:LWB]={LWB{1'b1}}; end
  endcase
  @(negedge clk); clear;
  t0=-1; t1=-1;
  for(integer k=0;k<12;k++)begin
   if(f0 && t0<0)t0=k; if(f1 && t1<0)t1=k;
   @(negedge clk);
  end
  if(t0!=0)$fatal(1,"FPIPE_REF_EDGE cls=%0d lane=%0d t0=%0d",cls,l,t0);
  if(t1!=AGE)$fatal(1,"FPIPE_AGE cls=%0d lane=%0d t0=%0d t1=%0d",cls,l,t0,t1);
  episodes++;
 end endtask
 initial begin
  for(integer cls=0;cls<4;cls++)for(integer l=0;l<16;l++)episode(cls,l);
  for(integer l=0;l<8;l++)episode(4,l);
  for(integer l=0;l<2;l++)episode(5,l);
  $display("PASS SFU_FAULT_PIPE episodes=%0d age=%0d",episodes,AGE);
  $finish;
 end
endmodule
