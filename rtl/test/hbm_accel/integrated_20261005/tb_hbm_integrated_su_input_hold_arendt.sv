`timescale 1ns/1fs
// Production CP + owner + engines + actual installed CDC/backend classes.
// SM arithmetic is outside this minimum cut; its prior LSU/bulk producers
// issue real requests, hold their responses, and retire only actual handshakes.
// Private INPUT-side integration cut: original MODE1 scalar fetches only.
// Same CP, real borrow grant, CDC and finite backend as Rawls's frozen runtime.
// Stop at the first native edge; no four-op arithmetic or publication claim.
module tb_hbm_integrated_su_input_hold_arendt;
 reg clk=0,clk_mem=0;always #0.416667 clk=~clk;always #0.5 clk_mem=~clk_mem;
 reg rst_n=0,cmd_we=0,db_v=0,loader_we=0,cpl_ready=0;
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
 wire [272:0] su_rsp, su_rsp_raw;
 wire su_rsp_v_raw,su_rsp_rdy_native;
 reg input_delivery=0;
 assign su_rsp_v=su_rsp_v_raw && input_delivery;
 assign su_rsp_rdy=su_rsp_rdy_native && input_delivery;
 assign su_rsp=su_rsp_raw;
 reg old_req_v=0,old_rsp_ready=0,bulk_req_v=0,bulk_rsp_ready=0;
 reg [31:0] old_address=0;
 reg [15:0] old_tag=16'h55;
 wire old_req_ready,old_rsp_v;
 wire [272:0] old_rsp;
 wire [3:0] obs_req,obs_rsp;
 wire [63:0] obs_req_tag,obs_rsp_tag;
 wire [3:0] obs_req_we,obs_rsp_we;
 wire [15:0] seen_tag=c_rsp_tag[15:0];
 assign obs_req={2'd0,bulk_req_v && c_req_rdy[1],old_req_v && old_req_ready};
 assign obs_rsp={2'd0,c_rsp_v[1] && bulk_rsp_ready && authorized[1],old_rsp_v && old_rsp_ready};
 assign obs_req_tag={32'd0,16'h77,old_tag};
 assign obs_rsp_tag={32'd0,c_rsp_tag[31:16],old_rsp[272:257]};
 assign obs_req_we=4'd0;assign obs_rsp_we={2'd0,c_rsp_we[1],old_rsp[256]};
 ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(2)) cp(
  .clk(clk),.rst_n(rst_n),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_data),
  .db_v(db_v),.db_rdy(db_rdy),.db_token(17'h1ffff),.db_pos(20'hfffff),.db_job(32'd41),.db_generation(4'd3),
  .cpl_position(cpl_pos),.cpl_job(cpl_job),.cpl_generation(cpl_gen),
  .launch_v(launch_v),.launch_pc(launch_pc),.launch_token(launch_token),.launch_pos(launch_pos),
  .sm_done({1'd0,owner_done}),.sm_fault({2{owner_fault|exec_fault}}),.res_v(2'd0),.res_data(64'd0),
  .cpl_v(cpl_v),.cpl_rdy(cpl_ready),.cpl_token(cpl_token),.cpl_status(cpl_status),.cpl_cycles(cpl_cycles),
  .st_kernels(),.st_busy());
 wire su_quiet,su_selected,lease_v,release_v,release_r,shared_fault,shared_idle,native_empty;
 wire [2:0] grants,releases;
 wire [3:0] route_ready,route_rsp_v,route_rsp_we,authorized;
 wire [63:0] route_rsp_tag;wire [1023:0] route_rsp_data;
 wire [31:0] held_job;wire [3:0] held_gen;wire [16:0] held_token;wire [19:0] held_pos;
 ot_hbm_integrated_su_cp_bind #(.ENABLE(1)) binding(
  .clk(clk),.por_n(rst_n),.launch_v(launch_v),.launch_pc(launch_pc),
  .cp_job(cpl_job),.cp_gen(cpl_gen),.launch_token(launch_token),.launch_pos(launch_pos),
  .native_launch(),.lease_v(lease_v),.lease_granted(grants[1]),
  .release_v(release_v),.release_r(releases[1]),.exec_done(exec_done),.exec_fault(exec_fault),
  .retired_original_ops(logical_retired),.shared_fault(shared_fault),.owned(owned),.pending(pending),
  .quiet(su_quiet),.selected(su_selected),.done(owner_done),.fault(owner_fault),
  .selected_pc(selected_pc),.held_job(held_job),.held_gen(held_gen),.held_token(held_token),.held_pos(held_pos));
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) owner(
  .clk(clk),.por_n(rst_n),.native_clients_drained(!old_req_v&&!bulk_req_v&&!sm_busy),
  .cdc_drained(native_empty),.native_credit_empty(native_empty),
  .observe_req(obs_req),.observe_rsp(obs_rsp),.observe_req_tag(obs_req_tag),.observe_rsp_tag(obs_rsp_tag),
  .observe_req_we(obs_req_we),.observe_rsp_we(obs_rsp_we),
  .return_offer({2'd0,c_rsp_v[1],route_rsp_v[0]}),.response_authorized(authorized),
  .native_job(cpl_job),.native_gen(cpl_gen),.native_token(launch_token),.native_pos(launch_pos),
  .lease_v({1'b0,lease_v,1'b0}),.borrower_quiet({1'b1,su_quiet,1'b1}),
  .lease_job({32'd0,held_job,32'd0}),.lease_gen({4'd0,held_gen,4'd0}),
  .lease_token({17'd0,held_token,17'd0}),.lease_pos({20'd0,held_pos,20'd0}),.lease_granted(grants),
  .release_v({1'b0,release_v,1'b0}),.release_r(releases),
  .release_job({32'd0,held_job,32'd0}),.release_gen({4'd0,held_gen,4'd0}),
  .release_token({17'd0,held_token,17'd0}),.release_pos({20'd0,held_pos,20'd0}),
  .req_v({1'b0,su_req_v,1'b0,old_req_v}),.req_rdy(route_ready),
  .req_we({1'b0,su_req[336],2'd0}),
  .req_addr({32'd0,su_req[335:304],32'd0,old_address}),
  .req_wdata({256'd0,su_req[303:48],512'd0}),
  .req_wstrb({32'd0,su_req[47:16],64'd0}),.req_tag({16'd0,su_req[15:0],16'd0,old_tag}),
  .rsp_v(route_rsp_v),.rsp_rdy({1'b0,su_rsp_rdy,1'b0,old_rsp_ready&&authorized[0]}),
  .rsp_we(route_rsp_we),.rsp_tag(route_rsp_tag),.rsp_data(route_rsp_data),
  .m_req_v(c_req_v[0]),.m_req_rdy(c_req_rdy[0]),.m_req_we(c_req_we[0]),
  .m_req_addr(c_req_addr[31:0]),.m_req_wdata(c_req_data[255:0]),
  .m_req_wstrb(c_req_strb[31:0]),.m_req_tag(c_req_tag[15:0]),
  .m_rsp_v(c_rsp_v[0]),.m_rsp_rdy(c_rsp_rdy[0]),.m_rsp_we(c_rsp_we[0]),
  .m_rsp_tag(seen_tag),.m_rsp_data(c_rsp_data[255:0]),.idle(shared_idle),.fault(shared_fault));
 assign old_req_ready=route_ready[0];assign su_req_rdy=route_ready[2];
 assign old_rsp_v=route_rsp_v[0]&&authorized[0];
 assign old_rsp={route_rsp_tag[15:0],route_rsp_we[0],route_rsp_data[255:0]};
 assign su_rsp_v_raw=route_rsp_v[2];
 assign su_rsp_raw={route_rsp_tag[47:32],route_rsp_we[2],route_rsp_data[767:512]};
 assign c_req_v[3:1]={2'd0,bulk_req_v};assign c_req_we[3:1]=0;
 assign c_req_addr[127:32]={64'd0,32'd96};assign c_req_data[1023:256]=0;
 assign c_req_strb[127:32]=0;assign c_req_tag[63:16]={32'd0,16'h77};
 assign c_rsp_rdy[3:1]={2'd0,bulk_rsp_ready&&authorized[1]};
 wire [31:0] vcount,rcount,wcount,fcount;wire [3:0] logical_retired;

 ot_hbm_accel_su_parent_exec #(.ENABLE(1)) exec(
  .clk(clk),.rst_n(rst_n),.owned(owned),.config_idle(db_rdy),.loader_we(loader_we),.loader_addr(loader_addr),.loader_data(loader_data),
  .selected_pc(selected_pc),.job_id(held_job),.req_v(su_req_v),.req_rdy(su_req_rdy),.req(su_req),
  .rsp_v(su_rsp_v),.rsp_rdy(su_rsp_rdy_native),.rsp(su_rsp),.done(exec_done),.fault(exec_fault),
  .virtual_edges(vcount),.read_requests(rcount),.write_requests(wcount),.publication_requests(fcount),.retired_original_ops(logical_retired));
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
 reg [689:0] words[0:3];
 integer cycle=0,old_accepted=0,old_consumed=0,bulk_consumed=0,hold_checks=0;
 integer start_cycle=-1,finish_cycle=-1,owned_cycle=-1,request_edge=0,wait_edges=0;
 reg late_prior=0;
 real start_time,finish_time,owned_time;
 always @(posedge clk) begin
  cycle<=cycle+1;
  if(old_req_v && old_req_ready) old_accepted=old_accepted+1;
  if(old_rsp_v && old_rsp_ready) old_consumed=old_consumed+1;
  if(c_rsp_v[1] && bulk_rsp_ready && authorized[1]) bulk_consumed=bulk_consumed+1;
  if(pending && (old_consumed==0 || bulk_consumed==0)) begin
   if(owned || owner_done || su_req_v) $fatal(1,"borrow before real prior response consumption");
   hold_checks=hold_checks+1;
  end
  if(db_v && db_rdy && start_cycle<0) begin start_cycle=cycle;start_time=$realtime;end
  if(owned && owned_cycle<0) begin owned_cycle=cycle;owned_time=$realtime;$display("PARENT_EVENT owned cycle=%0d time_ns=%0.9f",cycle,$realtime);end
  if(late_prior && owned) $fatal(1,"borrow while late actual producer request/response outstanding");
  if(su_req_v && su_req_rdy) request_edge=cycle;
  if(su_rsp_v && su_rsp_rdy) wait_edges=wait_edges+cycle-request_edge;
  if(owner_fault || shared_fault || exec_fault || |cdc_fault || mem_fault) $fatal(1,"parent/provider fault cycle=%0d",cycle);
 end
 integer i,j,input_holds=0,accepted_inputs=0;
 reg [272:0] held_input;
 initial begin
  $readmemh("prog.hex",words);
  repeat(5) @(negedge clk);rst_n=1;
  for(i=0;i<4;i=i+1) for(j=0;j<11;j=j+1) begin
   @(negedge clk);loader_we=1;loader_addr=14'h2000+(i<<4)+j;loader_data=words[i]>>(j*64);
  end
  @(negedge clk);loader_we=0;cmd_we=1;cmd_addr=0;
  cmd_data={4'd1,16'd1,12'd0,32'hc0000004};
  @(negedge clk);cmd_addr=1;cmd_data=64'h2000000000000000;
  @(negedge clk);cmd_we=0;
  db_v=1;do @(posedge clk);while(!db_rdy);@(negedge clk);db_v=0;
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
  wait(old_rsp_v && c_rsp_v[1]);
  repeat(8) @(negedge clk);
  old_rsp_ready=1;bulk_rsp_ready=1;
  wait(owned);
  // MODE1 has twenty scalar reads BEFORE BOOT admits any native engine edge.
  // Only response delivery is held; backend bytes, addresses and tags remain
  // the actual accepted request/response. The shared owner retains its lease.
  for(i=0;i<20;i=i+1) begin
   wait(su_rsp_v_raw);
   @(negedge clk);held_input=su_rsp_raw;
   if(held_input[256] || held_input[272:257]!==su_req[15:0])
    $fatal(1,"INPUT_RESPONSE_IDENTITY scalar=%0d",i);
   for(j=0;j<3+(i%6);j=j+1) begin
    @(negedge clk);
    if(!su_rsp_v_raw || su_rsp_raw!==held_input || su_rsp_rdy ||
       vcount!=0 || rcount!=i || wcount!=0 || fcount!=0 ||
       logical_retired!=0 || exec_done || owner_done || cpl_v ||
       !owned || !grants[1] || release_v)
     $fatal(1,"INPUT_HOLD_LOST scalar=%0d held_edge=%0d",i,j);
    input_holds=input_holds+1;
   end
   input_delivery=1;
   do @(posedge clk);while(!(su_rsp_v_raw && su_rsp_rdy_native));
   accepted_inputs=accepted_inputs+1;
   @(negedge clk);input_delivery=0;
   if(rcount!=accepted_inputs || vcount!=0 || logical_retired!=0)
    $fatal(1,"INPUT_ACCEPT_ADVANCED_ENGINE scalar=%0d",i);
  end
  wait(vcount!=0);@(negedge clk);
  if(vcount!=1 || rcount!=20 || accepted_inputs!=20 || input_holds!=106 ||
     wcount!=0 || fcount!=0 || logical_retired!=0 || !owned ||
     !grants[1] || exec_done || owner_done || cpl_v || release_v)
   $fatal(1,"INPUT_FIRST_NATIVE_EDGE_CONTRACT");
  $display("PASS_SU_INPUT_HOLD accepted_inputs=%0d held_edges=%0d native_edges=%0d prior_hold_checks=%0d retained_owner=1 retired=0 publications=0",
   accepted_inputs,input_holds,vcount,hold_checks);
  $finish;
 end
endmodule
