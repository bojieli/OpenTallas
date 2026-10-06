`timescale 1ns/1fs
// Production CP + owner + engines + actual installed CDC/backend classes.
// SM arithmetic is outside this minimum cut; its prior LSU/bulk producers
// issue real requests, hold their responses, and retire only actual handshakes.
module tb_hbm_accel_su_parent #(parameter integer OWNER_ONLY=0);
 reg clk=0,clk_mem=0;always #0.416667 clk=~clk;always #0.5 clk_mem=~clk_mem;
 reg rst_n=0,cmd_we=0,db_v=0,loader_we=0;
 reg [7:0] cmd_addr=0;reg [63:0] cmd_data=0,loader_data=0;
 reg [13:0] loader_addr=0;
 wire db_rdy,cpl_v;wire [1:0] launch_v;
 wire [31:0] launch_pc,cpl_job;wire [16:0] launch_token,cpl_token;
 wire [19:0] launch_pos,cpl_pos;wire [3:0] cpl_gen,cpl_status;
 wire [31:0] cpl_cycles;
 wire pending,owned,owner_done,owner_fault,exec_done,exec_fault;
 wire [31:0] selected_pc;
 reg [1:0] sm_busy=0;
 wire [3:0] c_req_v,c_req_rdy,c_req_we,c_rsp_v,c_rsp_rdy,c_rsp_we;
 wire [127:0] c_req_addr,c_req_strb;wire [1023:0] c_req_data,c_rsp_data;
 wire [63:0] c_req_tag,c_rsp_tag;
 wire [3:0] x_req_v,x_req_rdy,x_req_we,x_rsp_v,x_rsp_rdy,x_rsp_we,cdc_fault;
 wire [127:0] x_req_addr,x_req_strb;wire [1023:0] x_req_data,x_rsp_data;
 wire [63:0] x_req_tag,x_rsp_tag;
 wire mem_fault;
 wire su_req_v,su_req_rdy,su_rsp_v,su_rsp_rdy;
 wire [336:0] su_req,route_req;
 wire [272:0] su_rsp;
 reg old_req_v=0,old_rsp_ready=0,bulk_req_v=0,bulk_rsp_ready=0;
 reg [31:0] old_address=0;
 reg [15:0] old_tag=16'h55;
 wire old_req_ready,old_rsp_v;
 wire [272:0] old_rsp;
 wire [3:0] obs_req,obs_rsp;
 wire [63:0] obs_req_tag,obs_rsp_tag;
 wire [3:0] obs_req_we,obs_rsp_we;
 integer mode=0,foreign=0;
 wire [15:0] seen_tag=foreign==1?c_rsp_tag[15:0]^16'd1:c_rsp_tag[15:0];
 assign obs_req={2'd0,bulk_req_v && c_req_rdy[1],owned?(su_req_v && su_req_rdy):(old_req_v && old_req_ready)};
 assign obs_rsp={2'd0,c_rsp_v[1] && bulk_rsp_ready,owned?(su_rsp_v && su_rsp_rdy):(old_rsp_v && old_rsp_ready)};
 assign obs_req_tag={32'd0,16'h77,owned?su_req[15:0]:old_tag};
 assign obs_rsp_tag={32'd0,c_rsp_tag[31:16],owned?su_rsp[272:257]:old_rsp[272:257]};
 assign obs_req_we={3'd0,owned && su_req[336]};assign obs_rsp_we={2'd0,c_rsp_we[1],owned?su_rsp[256]:old_rsp[256]};
 ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(2)) cp(
  .clk(clk),.rst_n(rst_n),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_data),
  .db_v(db_v),.db_rdy(db_rdy),.db_token(17'h1ffff),.db_pos(20'hfffff),.db_job(32'd41),.db_generation(4'd3),
  .cpl_position(cpl_pos),.cpl_job(cpl_job),.cpl_generation(cpl_gen),
  .launch_v(launch_v),.launch_pc(launch_pc),.launch_token(launch_token),.launch_pos(launch_pos),
  .sm_done({1'd0,owner_done}),.sm_fault({2{owner_fault|exec_fault}}),.res_v(2'd0),.res_data(64'd0),
  .cpl_v(cpl_v),.cpl_rdy(1'b0),.cpl_token(cpl_token),.cpl_status(cpl_status),.cpl_cycles(cpl_cycles),
  .st_kernels(),.st_busy());
 ot_hbm_accel_su_parent_borrow #(.ENABLE(1)) owner(
  .clk(clk),.rst_n(rst_n),.launch_v(launch_v),.launch_pc(launch_pc),.sm_busy(sm_busy),
  .su_done(exec_done),.su_fault(exec_fault),.pending(pending),.owned(owned),.done(owner_done),.fault(owner_fault),.selected_pc(selected_pc),
  .observe_req(obs_req),.observe_rsp(obs_rsp),.observe_req_tag(obs_req_tag),.observe_rsp_tag(obs_rsp_tag),
  .observe_req_we(obs_req_we),.observe_rsp_we(obs_rsp_we),
  .sm_req_v(old_req_v),.sm_req_rdy(old_req_ready),.sm_req({1'b0,old_address,256'd0,32'd0,old_tag}),
  .sm_rsp_v(old_rsp_v),.sm_rsp_rdy(old_rsp_ready),.sm_rsp(old_rsp),
  .su_req_v(su_req_v),.su_req_rdy(su_req_rdy),.su_req(su_req),.su_rsp_v(su_rsp_v),.su_rsp_rdy(su_rsp_rdy),.su_rsp(su_rsp),
  .req_v(c_req_v[0]),.req_rdy(c_req_rdy[0]),.req(route_req),
  .rsp_v(c_rsp_v[0]),.rsp_rdy(c_rsp_rdy[0]),.rsp({seen_tag,c_rsp_we[0],c_rsp_data[255:0]}));
 assign {c_req_we[0],c_req_addr[31:0],c_req_data[255:0],c_req_strb[31:0],c_req_tag[15:0]}=route_req;
 assign c_req_v[3:1]={2'd0,bulk_req_v};assign c_req_we[3:1]=0;
 assign c_req_addr[127:32]={64'd0,32'd96};assign c_req_data[1023:256]=0;
 assign c_req_strb[127:32]=0;assign c_req_tag[63:16]={32'd0,16'h77};
 assign c_rsp_rdy[3:1]={2'd0,bulk_rsp_ready};
 wire [31:0] vcount,rcount,wcount,fcount;wire [3:0] logical_retired;
 generate if(OWNER_ONLY==0) begin:g_exec
 ot_hbm_accel_su_parent_exec #(.ENABLE(1)) exec(
  .clk(clk),.rst_n(rst_n),.owned(owned),.config_idle(db_rdy),.loader_we(loader_we),.loader_addr(loader_addr),.loader_data(loader_data),
  .selected_pc(selected_pc),.job_id(cpl_job),.req_v(su_req_v),.req_rdy(su_req_rdy),.req(su_req),
  .rsp_v(su_rsp_v),.rsp_rdy(su_rsp_rdy),.rsp(su_rsp),.done(exec_done),.fault(exec_fault),
  .virtual_edges(vcount),.read_requests(rcount),.write_requests(wcount),.publication_requests(fcount),.retired_original_ops(logical_retired));
 end else begin:g_owner_only
 assign su_req_v=0;assign su_req=0;assign su_rsp_rdy=0;
 assign exec_done=0;assign exec_fault=0;assign vcount=0;assign rcount=0;
 assign wcount=0;assign fcount=0;assign logical_retired=0;
 end endgenerate
 genvar c;
 generate for(c=0;c<4;c=c+1) begin:g_cdc
  ot_gpu_mreq_cdc #(.ENABLE(1),.AW(3)) crossing(
   .clk_s(clk),.rst_s_n(rst_n),.clk_m(clk_mem),.rst_m_n(rst_n),
   .s_req_v(c_req_v[c]),.s_req_rdy(c_req_rdy[c]),.s_req_we(c_req_we[c]),.s_req_addr(c_req_addr[c*32+:32]),
   .s_req_wdata(c_req_data[c*256+:256]),.s_req_wstrb(c_req_strb[c*32+:32]),.s_req_tag(c_req_tag[c*16+:16]),
   .s_rsp_v(c_rsp_v[c]),.s_rsp_rdy(c_rsp_rdy[c]),.s_rsp_tag(c_rsp_tag[c*16+:16]),.s_rsp_we(c_rsp_we[c]),.s_rsp_data(c_rsp_data[c*256+:256]),
   .m_req_v(x_req_v[c]),.m_req_rdy(x_req_rdy[c]),.m_req_we(x_req_we[c]),.m_req_addr(x_req_addr[c*32+:32]),
   .m_req_wdata(x_req_data[c*256+:256]),.m_req_wstrb(x_req_strb[c*32+:32]),.m_req_tag(x_req_tag[c*16+:16]),
   .m_rsp_v(x_rsp_v[c]),.m_rsp_rdy(x_rsp_rdy[c]),.m_rsp_tag(x_rsp_tag[c*16+:16]),.m_rsp_we(x_rsp_we[c]),.m_rsp_data(x_rsp_data[c*256+:256]),.fault(cdc_fault[c]));
 end endgenerate
 ot_gpu_memsys #(.ENABLE(1),.NC(4),.NS(2),.NPC(2),.MEM_WORDS(65536),.USE_W2(0),.IMAGE_PREFIX("memory")) mem(
  .clk(clk_mem),.rst_n(rst_n),.req_v(x_req_v),.req_rdy(x_req_rdy),.req_we(x_req_we),.req_addr(x_req_addr),
  .req_wdata(x_req_data),.req_wstrb(x_req_strb),.req_tag(x_req_tag),.rsp_v(x_rsp_v),.rsp_rdy(x_rsp_rdy),
  .rsp_tag(x_rsp_tag),.rsp_we(x_rsp_we),.rsp_data(x_rsp_data),.fault(mem_fault));
 reg [689:0] words[0:3];reg [31:0] expected[0:20479];
 integer cycle=0,old_accepted=0,old_consumed=0,bulk_consumed=0,hold_checks=0;
 integer start_cycle=-1,finish_cycle=-1,owned_cycle=-1,request_edge=0,wait_edges=0;
 reg late_prior=0;
 real start_time,finish_time,owned_time;
 always @(posedge clk) begin
  cycle<=cycle+1;
  if(old_req_v && old_req_ready) old_accepted=old_accepted+1;
  if(old_rsp_v && old_rsp_ready) old_consumed=old_consumed+1;
  if(c_rsp_v[1] && bulk_rsp_ready) bulk_consumed=bulk_consumed+1;
  if(pending && (old_consumed==0 || bulk_consumed==0)) begin
   if(owned || owner_done || su_req_v) $fatal(1,"borrow before real prior response consumption");
   hold_checks=hold_checks+1;
  end
  if(db_v && db_rdy && start_cycle<0) begin start_cycle=cycle;start_time=$realtime;end
  if(owned && owned_cycle<0) begin owned_cycle=cycle;owned_time=$realtime;$display("PARENT_EVENT owned cycle=%0d time_ns=%0.9f",cycle,$realtime);end
  if(late_prior && owned) $fatal(1,"borrow while late actual producer request/response outstanding");
  if(su_req_v && su_req_rdy) request_edge=cycle;
  if(su_rsp_v && su_rsp_rdy) wait_edges=wait_edges+cycle-request_edge;
  if(owner_fault || exec_fault || |cdc_fault || mem_fault) $fatal(1,"parent/provider fault mode=%0d cycle=%0d",mode,cycle);
 end
 task automatic read_sector(input integer addr,input integer tag_value);
  begin
   @(negedge clk);old_address=addr;old_tag=tag_value;old_req_v=1;old_rsp_ready=0;
   do @(posedge clk);while(!old_req_ready);
   @(negedge clk);old_req_v=0;
   wait(old_rsp_v);@(negedge clk);old_rsp_ready=1;
   @(negedge clk);
  end
 endtask
 integer i,j,errors=0;
 initial begin
  if($value$plusargs("MODE=%d",mode)) begin end
  if($value$plusargs("FOREIGN=%d",foreign)) begin end
  $readmemh("prog.hex",words);$readmemh("expected.mem",expected);
  repeat(5) @(negedge clk);rst_n=1;
  for(i=0;i<4;i=i+1) for(j=0;j<11;j=j+1) begin
   @(negedge clk);loader_we=1;loader_addr=14'h2000+(i<<4)+j;loader_data=words[i]>>(j*64);
  end
  @(negedge clk);loader_we=0;cmd_we=1;cmd_addr=0;
  cmd_data={4'd1,16'd1,12'd0,mode==0?32'h80000004:32'hc0000004};
  @(negedge clk);cmd_addr=1;cmd_data=64'h2000000000000000;
  @(negedge clk);cmd_we=0;
  fork
   begin
    old_req_v=1;sm_busy=1;
    do @(posedge clk);while(!old_req_ready);
    @(negedge clk);old_req_v=0;sm_busy=0;
   end
   begin
    bulk_req_v=1;
    do @(posedge clk);while(!c_req_rdy[1]);
    @(negedge clk);bulk_req_v=0;
   end
  join
  db_v=1;@(negedge clk);db_v=0;
  if(foreign==1) wait(c_rsp_v[0] && c_rsp_v[1]);
  else wait(old_rsp_v && c_rsp_v[1]);
  repeat(8) @(negedge clk);
  if(foreign==1) begin
   if(owned || c_rsp_rdy[0] || !pending) $fatal(1,"foreign prior response released owner");
   $display("PARENT_FOREIGN_PASS hold=8 prior_debt=1 owned=0");$finish;
  end
  old_rsp_ready=1;bulk_rsp_ready=1;
  // A real old-producer request arrives on the would-be quiet grant edge.
  // It must retire through the same provider before ownership changes.
  wait(owner.quiet_age==3);@(negedge clk);
  late_prior=1;old_address=128;old_tag=16'h88;old_req_v=1;
  do @(posedge clk);while(!old_req_ready);
  @(negedge clk);old_req_v=0;
  wait(old_rsp_v);@(negedge clk);late_prior=0;
  if(OWNER_ONLY) begin
   wait(owned);@(negedge clk);
   if(old_consumed!=2 || bulk_consumed!=1 || !owned || pending || owner_done || cpl_v)
    $fatal(1,"late producer ownership exclusion/actual retirement");
   $display("BORROW_RACE_PASS old_consumed=2 bulk_consumed=1 true_grant=1 no_fake_done=1");$finish;
  end
  wait(cpl_v);@(negedge clk);finish_cycle=cycle;finish_time=$realtime;
  // This cut deliberately has no SM RESULT kernel: preserve CP's real status2.
  if(cpl_status!=2 || cpl_token!=0 || cpl_job!=41 || cpl_gen!=3 || cpl_pos!=20'hfffff ||
     owned || logical_retired!=4 || hold_checks<8 || wcount!=fcount) $fatal(1,"actual CP/lease publication contract");
  old_rsp_ready=0;bulk_rsp_ready=0;
  for(i=0;i<2560;i=i+1) begin
   read_sector((25688+i*8)*4,16'h8000+i);
   for(j=0;j<8;j=j+1) if(old_rsp[j*32+:32]!==expected[i*8+j]) begin
    if(errors<5) $display("PARENT_MISMATCH index=%0d got=%08x want=%08x",i*8+j,old_rsp[j*32+:32],expected[i*8+j]);
    errors=errors+1;
   end
   @(negedge clk);old_rsp_ready=0;
  end
  if(errors) $fatal(1,"cached1M comparison errors=%0d",errors);
  $display("PARENT_END mode=%0d start=%0d finish=%0d virtual_edges=%0d reads=%0d writes=%0d publications=%0d request_response_wait_edges=%0d hold_checks=%0d checked=20480 errors=%0d start_time_ns=%0.9f owned_cycle=%0d owned_time_ns=%0.9f finish_time_ns=%0.9f elapsed_us=%0.9f owned_us=%0.9f",mode,start_cycle,finish_cycle,vcount,rcount,wcount,fcount,wait_edges,hold_checks,errors,start_time,owned_cycle,owned_time,finish_time,(finish_time-start_time)/1000,(finish_time-owned_time)/1000);
  $display("PASS");$finish;
 end
endmodule
