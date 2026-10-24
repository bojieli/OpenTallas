`timescale 1ns/1ps
// HBM-P5-RTLA (2026-10-23): lock-step of the store-side pin-register twin ot_hgi_sfu_static_engine_sp2 against the
// pinned ot_hgi_sfu_static_engine (same preload, same compiler image; the image's last row -- every field stable, no
// emit -- is held XH more edges = the compiler's op-horizon cost).  Checks every edge:
//   lane read requests (rd_re/rd_addr/rd_src) and gather reads (vi_re/vi_addr): twin == pinned (shift 0)
//   lane results (vm_we/vm_waddr/vm_wdata at the lane pins, ro_v/ro_x, kv_*): twin == pinned 2 edges earlier
//   the output group's write port (behind the store pin register): twin == pinned 3 edges earlier
//   fault 0 in both; then the drained output group: twin == pinned == the golden copy value(), every word.
module tb_hgi_sfu_static_engine_sp2;
 localparam LWB=15,WORDS=7168,ROWS=502,XH=3,SH=2;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0;
 reg [1741:0] controls[0:ROWS-1];
 reg [1741:0] compiler_control=0;
 reg [7:0] stage_v=0;
 reg [15:0] stage_group=0;
 reg [8*LWB-1:0] stage_addr=0;
 reg [2047:0] stage_data=0;
 reg [1:0] drain_v=0;
 reg [2*LWB-1:0] drain_addr=0;
 wire [511:0] drain_data,rdrain_data;
 wire [1:0] drain_rv,rdrain_rv;
 wire fault,rfault;
 wire [15:0] vi_re,rvi_re,ro_v,rro_v,kv_we,rkv_we;
 wire [383:0] vi_addr,rvi_addr,kv_waddr,rkv_waddr;
 wire [511:0] ro_x,rro_x,kv_wdata,rkv_wdata;
 integer checks=0,lchk=0,lerr=0,nwr=0,nrd=0;
 function automatic [31:0] value(input integer g,a);value=32'h3e000000+32'(100000*g+a*7);endfunction
 ot_hgi_sfu_static_engine ref_u(.clk(clk),.rst_n(rst_n),.clk_lane({16{clk}}),.clk_map({16{clk}}),
 .rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),.compiler_control(compiler_control),.vi_q(512'd0),
 .scalar_load(4'd0),.scalar_enable(4'd0),.scalar_addr(96'd0),.scalar_data(128'd0),.stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(64'hffffffffffffffff),.stage_data(stage_data),
 .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(rdrain_data),.drain_result_v(rdrain_rv),
 .vi_re(rvi_re),.vi_addr(rvi_addr),.ro_v(rro_v),.ro_x(rro_x),.kv_we(rkv_we),.kv_waddr(rkv_waddr),.kv_wdata(rkv_wdata),.fault(rfault));
 ot_hgi_sfu_static_engine_sp2 dut(.clk(clk),.rst_n(rst_n),.clk_lane({16{clk}}),.clk_map({16{clk}}),
 .rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),.compiler_control(compiler_control),.vi_q(512'd0),
 .scalar_load(4'd0),.scalar_enable(4'd0),.scalar_addr(96'd0),.scalar_data(128'd0),.stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(64'hffffffffffffffff),.stage_data(stage_data),
 .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_rv),
 .vi_re(vi_re),.vi_addr(vi_addr),.ro_v(ro_v),.ro_x(ro_x),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.fault(fault));
 // lane-side buses
 wire [63:0] r_rre=ref_u.rd_re,t_rre=dut.rd_re;wire [1535:0] r_rad=ref_u.rd_addr,t_rad=dut.rd_addr;
 wire [127:0] r_rsr=ref_u.rd_src,t_rsr=dut.rd_src;
 wire [15:0] r_vwe=ref_u.vm_we,t_vwe=dut.vm_we;wire [383:0] r_vwa=ref_u.vm_addr,t_vwa=dut.vm_addr;
 wire [511:0] r_vwd=ref_u.vm_data,t_vwd=dut.vm_data;
 // the output group's own write port (pinned: the lane pins; twin: behind the store pin register)
 wire [15:0] r_owe=ref_u.u_memory.u_output.lw,t_owe=dut.u_memory.u_store.u_output.lw;
 wire [383:0] r_owa=ref_u.u_memory.u_output.lwa,t_owa=dut.u_memory.u_store.u_output.lwa;
 wire [511:0] r_owd=ref_u.u_memory.u_output.lwd,t_owd=dut.u_memory.u_store.u_output.lwd;
 localparam integer RW=16+384+512+16+512+16+384+512;   // lane results: vm, ro, kv
 localparam integer OW=16+384+512;
 wire [RW-1:0] r_res={r_vwe,r_vwe!=0?r_vwa:384'd0,r_vwe!=0?r_vwd:512'd0,rro_v,rro_v!=0?rro_x:512'd0,rkv_we,rkv_we!=0?rkv_waddr:384'd0,rkv_we!=0?rkv_wdata:512'd0};
 wire [RW-1:0] t_res={t_vwe,t_vwe!=0?t_vwa:384'd0,t_vwe!=0?t_vwd:512'd0,ro_v,ro_v!=0?ro_x:512'd0,kv_we,kv_we!=0?kv_waddr:384'd0,kv_we!=0?kv_wdata:512'd0};
 wire [OW-1:0] r_ow={r_owe,r_owe!=0?r_owa:384'd0,r_owe!=0?r_owd:512'd0},t_ow={t_owe,t_owe!=0?t_owa:384'd0,t_owe!=0?t_owd:512'd0};
 reg [RW-1:0] rres_d[0:SH];reg [OW-1:0] row_d[0:SH+1];
 always @(posedge clk)begin
  rres_d[0]<=r_res;for(integer i=1;i<=SH;i++)rres_d[i]<=rres_d[i-1];
  row_d[0]<=r_ow;for(integer i=1;i<=SH+1;i++)row_d[i]<=row_d[i-1];
 end
 reg chk_on=0;
 always @(negedge clk)if(chk_on)begin
  lchk++;
  if(t_rre!==r_rre||(r_rre!=0&&(t_rad!==r_rad||t_rsr!==r_rsr))||vi_re!==rvi_re||(rvi_re!=0&&vi_addr!==rvi_addr))begin
   lerr++;if(lerr<6)$display("SP2_LOCKSTEP REQ mismatch edge %0d rd_re twin %h pinned %h",lchk,t_rre,r_rre);end
  if(t_res!==rres_d[SH-1])begin lerr++;if(lerr<6)$display("SP2_LOCKSTEP RESULT mismatch edge %0d vm_we twin %h pinned-%0d %h",lchk,t_vwe,SH,rres_d[SH-1][RW-1-:16]);end
  if(t_ow!==row_d[SH])begin lerr++;if(lerr<6)$display("SP2_LOCKSTEP OUTPUT-GROUP WRITE mismatch edge %0d twin %h pinned-%0d %h",lchk,t_owe,SH+1,row_d[SH][OW-1-:16]);end
  if(r_rre!=0)nrd++;if(t_owe!=0)nwr++;
  if(fault||rfault)begin lerr++;if(lerr<6)$display("SP2_LOCKSTEP FAULT twin %0d pinned %0d edge %0d",fault,rfault,lchk);end
 end
 initial begin
  $readmemh(`SFU_IMAGE,controls);
  repeat(16)@(negedge clk);rst_n=1;
  for(integer beat=0;beat<WORDS/16;beat++)begin
   stage_v=8'hff;
   for(integer s=0;s<8;s++)begin
    stage_group[2*s+:2]=2'(s/2);
    stage_addr[LWB*s+:LWB]=LWB'(beat*16+(s%2)*8);
    for(integer w=0;w<8;w++)stage_data[256*s+32*w+:32]=value(s/2,beat*16+(s%2)*8+w);
   end
   @(negedge clk);
  end
  stage_v=0;
  repeat(SH+2)@(negedge clk);chk_on=1;   // the pinned delay lines hold post-preload idle state
  for(integer t=0;t<ROWS+XH;t++)begin
   compiler_control=controls[t<ROWS?t:ROWS-1];
   @(negedge clk);
  end
  chk_on=0;
  for(integer beat=0;beat<WORDS/16;beat++)begin
   drain_v=3;drain_addr={LWB'(beat*16+8),LWB'(beat*16)};
   @(posedge clk);#0.001;
   if(fault||rfault||drain_rv!=3||rdrain_rv!=3)$fatal(1,"SP2_LOCKSTEP FAIL drain phase fault %0d/%0d rv %0d/%0d",fault,rfault,drain_rv,rdrain_rv);
   for(integer j=0;j<16;j++)begin
    if(drain_data[j*32+:32]!==value(0,beat*16+j)||rdrain_data[j*32+:32]!==value(0,beat*16+j))
     $fatal(1,"SP2_LOCKSTEP FAIL ENGINE_WORD beat=%0d lane=%0d twin=%h pinned=%h expected=%h lockstep_errors=%0d",beat,j,drain_data[j*32+:32],rdrain_data[j*32+:32],value(0,beat*16+j),lerr);
    checks++;
   end
   @(negedge clk);
  end
  if(lerr!=0)$fatal(1,"SP2_LOCKSTEP FAIL lockstep_errors=%0d edges=%0d",lerr,lchk);
  if(nwr!=WORDS/16*16/16*1 && nwr==0)$fatal(1,"SP2_LOCKSTEP FAIL no output-group writes observed");
  $display("SP2_LOCKSTEP PASS words=%0d exact_checks=%0d lockstep_edges=%0d read_edges=%0d write_edges=%0d read_shift=0 result_shift=%0d write_shift=%0d horizon_extra=%0d",WORDS,checks,lchk,nrd,nwr,SH,SH+1,XH);
  $finish;
 end
endmodule
