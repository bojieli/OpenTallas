`timescale 1ps/1ps
// Directed actual sector-root/rank-boundary test. Caller events are fixtures;
// no W2 datapath, backend/CDC, token or physical timing claim.
module rank_boundary_tb;
 parameter TB_ENABLE=1;
 reg clk=0,por_n=0,run_enable=1,local_reset=0;
 reg alloc_valid=0,map_valid=1,map_rank=0,reverse_valid=0,reverse_rank=0;
 reg [126:0] alloc_source=0;
 reg [6:0] map_PC=127;
 reg alloc_rmw=0;
 reg issue_valid=0,capture_valid=0,release_valid=0;
 reg issue_write=1,capture_write=1,reverse_write=1;
 reg [206:0] issue_identity=0,capture_identity=0,reverse_identity=0,release_identity=0;
 wire grant_live,grant_rmw,fault;
 wire [206:0] grant_identity;
 wire [2:0] grant_phase;
 wire av,mv,rv,ar,rr,raw_ar,raw_rr,issue_ready,capture_ready,release_ready,refusal;
 wire [6:0] selected_PC;
 wire [7:0] selected_index;
 wire [5:0] guard_permit;
 ot_gpu_qwen_rank_boundary #(.ENABLE(TB_ENABLE)) boundary(
  .grant_live(grant_live),.grant_identity(grant_identity),.alloc_valid(alloc_valid),.map_valid(map_valid),
  .map_rank(map_rank),.alloc_source(alloc_source),.map_PC(map_PC),.raw_alloc_ready(raw_ar),
  .reverse_valid(reverse_valid),.reverse_rank(reverse_rank),.raw_reverse_ready(raw_rr),
  .alloc_valid_checked(av),.map_valid_checked(mv),.alloc_ready(ar),
  .reverse_valid_checked(rv),.reverse_ready(rr),.selected_PC(selected_PC),.selected_index(selected_index),.rank_refusal(refusal));
 ot_gpu_qwen_payload_sector_authority #(.ENABLE(TB_ENABLE)) actual_root(
  .clk(clk),.por_n(por_n),.run_enable(run_enable),.local_reset(local_reset),
  .alloc_valid(av),.alloc_ready(raw_ar),.alloc_source(alloc_source),.alloc_rmw(alloc_rmw),
  .map_valid(mv),.map_sector_clear(1'b1),.map_addr(34'b0),.map_PC(map_PC),.map_client(3'd5),
  .map_tag(32'hffffffff),.map_gen(4'hf),.grant_live(grant_live),.grant_identity(grant_identity),
  .grant_rmw(grant_rmw),.grant_phase(grant_phase),.guard_addr(204'b0),.guard_owner(276'b0),
  .guard_write(6'b0),.guard_permit(guard_permit),.issue_valid(issue_valid),.issue_ready(issue_ready),
  .issue_identity(issue_identity),.issue_write(issue_write),.capture_valid(capture_valid),.capture_ready(capture_ready),
  .capture_identity(capture_identity),.capture_write(capture_write),.reverse_valid(rv),.reverse_ready(raw_rr),
  .reverse_identity(reverse_identity),.reverse_write(reverse_write),.release_valid(release_valid),
  .release_ready(release_ready),.release_identity(release_identity),.fault(fault));
 task edge_step;begin #416;clk=1;#417;clk=0;#1;end endtask
 task require(input cond,input [511:0] message);begin if(cond!==1'b1)$fatal(1,"%s",message);end endtask
 task reverse_stage(input integer expected_phase,input bit rank);
 begin
  reverse_identity=grant_identity;reverse_valid=1;reverse_rank=!rank;#1;
  require(!rr && !rv && refusal,"WRONG_RANK must refuse both sides");
  repeat(3)begin edge_step();require(grant_live && grant_phase==expected_phase && !fault,"WRONG_RANK advanced/forgot ownership");end
  reverse_rank=rank;#1;require(rr && rv && !refusal,"matching real sender rank refused");
  edge_step();reverse_valid=0;
 end endtask
 integer r,m;
 reg [63:0] held;
 initial begin
  edge_step();por_n=1;edge_step();
  if(!TB_ENABLE)begin
   alloc_valid=1;reverse_valid=1;reverse_rank=1;map_rank=1;#1;
   require(!av && !mv && !ar && !rv && !rr && !refusal,"defaultoff produced grant or reverse ACK");
   repeat(4)edge_step();require(!grant_live && !fault,"defaultoff root changed");
   $display("PASS_DEFAULT_OFF_RANK_BOUNDARY");$finish;
  end
  for(r=0;r<2;r=r+1)for(m=0;m<2;m=m+1)begin
   alloc_rmw=m;alloc_source={64'h1234,20'(r<<13),9'(m ? 0:256),34'b0};
   map_rank=!r;alloc_valid=1;#1;
   require(!ar && !av && !mv && refusal,"wrong map rank admitted");
   edge_step();require(!grant_live && !fault,"wrong map allocated ownership");
   map_rank=r;#1;require(ar,"legal source rank not ready");edge_step();alloc_valid=0;
   require(grant_live && selected_index==r*128+127 && selected_PC==127,"rank/localPC not retained exactly");
   require(grant_identity[136]==r && grant_identity[45:39]==127,"owner PC/rank corrupted");
   if(m)begin
    issue_write=0;issue_identity=grant_identity;issue_valid=1;#1;require(issue_ready,"old read issue refused");
    edge_step();issue_valid=0;capture_write=0;capture_identity=grant_identity;capture_valid=1;#1;
    require(capture_ready,"old read capture refused");edge_step();capture_valid=0;reverse_write=0;
    reverse_stage(3,r);require(grant_phase==4,"old reverse did not enter NEW_REQ");
   end
   issue_write=1;issue_identity=grant_identity;issue_valid=1;#1;require(issue_ready,"new write issue refused");
   edge_step();issue_valid=0;capture_write=1;capture_identity=grant_identity;capture_valid=1;#1;
   require(capture_ready,"new write capture refused");edge_step();capture_valid=0;reverse_write=1;
   reverse_stage(6,r);require(grant_phase==7,"new reverse did not enter RELEASE");
   release_identity=grant_identity;release_valid=1;#1;require(release_ready,"owned release refused");
   edge_step();release_valid=0;require(!grant_live && !fault,"owned release not accepted");
  end
  // Async POR removes existing root ownership; boundary cannot retain stale rank.
  alloc_source={64'h5678,20'h2000,9'd256,34'b0};alloc_rmw=0;map_rank=1;alloc_valid=1;
  edge_step();alloc_valid=0;require(grant_live,"reset setup missing owner");por_n=0;#1;
  require(!grant_live && !rr,"POR left accepted owner/reverse ready");
  $display("PASS_RANKED_ACTUAL_ROOT_4_TRANSACTIONS_STALLED_REVERSE_RESET");$finish;
 end
endmodule
