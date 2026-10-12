`timescale 1ps/1fs
// tputx-gord 2026-10-11: sparse random production-shape bench for ot_hbm_index_global_order_mt.
// N distinct random ids in [0, 131072) (seeded); rank r publishes the ids = r (mod 96) ascending, with random explicit
// invalid slots (quarter padding) between them, and ends with either an invalid last slot or (EMPTY_END and the rank
// empty) an rsp_empty last.  The provider is an in-order pipelined read port (LAT cycles), the sink stalls with
// probability STALL/8.  Checks: every output equals the next id of the sorted set with its exact score and rank,
// output stable under stall, read count = sum over ranks of slots, done after exactly N outputs.
module tb_hbm_index_global_order_sparse #(parameter integer N=512,LAT=3,SEED=1,STALL=0,EMPTY_END=1);
 reg clk=0;always #416.667 clk=~clk;
 reg por_n=0,start=0,publication_complete=0,owner_valid=0;
 reg [72:0] start_frame={20'hfffff,53'h123456789ab},owner_frame={20'hfffff,53'h123456789ab};
 wire start_r,read_v;reg read_r=0;
 wire [72:0] read_frame;wire [6:0] read_rank;wire [16:0] read_ordinal;
 reg rsp_v=0;wire rsp_r;reg [72:0] rsp_frame=0;reg [6:0] rsp_rank=0;
 reg [16:0] rsp_ordinal=0;reg [33:0] rsp_tuple=0;reg rsp_last=0,rsp_empty=0;
 wire out_v;reg out_r=0;wire [33:0] out_tuple;wire [72:0] out_frame;
 wire [6:0] out_rank;wire retained,done,fault;
 ot_hbm_index_global_order_mt #(.ENABLE(1)) dut(.*);
 // slot table: slot[r][k] = {kind(2), id(17)}: kind 0 invalid, 1 valid, 2 invalid last, 3 empty last
 reg [18:0] slot[0:95][0:1379]; integer nslot[0:95];
 reg [16:0] sorted[0:131071]; reg used[0:131071];
 integer seed,i,r,k,id,total_reads=0,requests=0,received=0,cycle=0;
 integer qh=0,qt=0; reg [6:0] qr[0:8191]; reg [16:0] qo[0:8191]; integer qdue[0:8191];
 reg [6:0] p_rank; reg [16:0] p_ord; reg [33:0] stalled_tuple; reg stalled=0;
 initial begin
  seed=SEED;
  for(i=0;i<131072;i=i+1) used[i]=0;
  i=0; while(i<N) begin id=$unsigned($random(seed))%131072; if(!used[id]) begin used[id]=1; i=i+1; end end
  k=0; for(i=0;i<131072;i=i+1) if(used[i]) begin sorted[k]=i; k=k+1; end
  for(r=0;r<96;r=r+1) begin
   nslot[r]=0;
   slot[r][nslot[r]]={2'd0,17'd0}; nslot[r]=nslot[r]+1;          // leading invalid slot
   for(id=r;id<131072;id=id+96) if(used[id]) begin
    while($unsigned($random(seed))%8==0 && nslot[r]<1300) begin slot[r][nslot[r]]={2'd0,17'd0}; nslot[r]=nslot[r]+1; end
    slot[r][nslot[r]]={2'd1,17'(id)}; nslot[r]=nslot[r]+1;
   end
   if(EMPTY_END && nslot[r]==1 && r%2==0) slot[r][nslot[r]-1]={2'd3,17'd0};   // empty rank: one rsp_empty last slot
   else begin slot[r][nslot[r]]={2'd2,17'd0}; nslot[r]=nslot[r]+1; end
   total_reads=total_reads+nslot[r];
  end
 end
 always @(negedge clk)begin
  if(!por_n)begin read_r=0;out_r=0;rsp_v=0;cycle=0;end
  else begin
   cycle=cycle+1;
   read_r=1;
   out_r=STALL==0 ? 1'b1 : ($unsigned($random(seed))%8>=STALL);
   if(qh!=qt&&cycle>=qdue[qh%8192]&&!rsp_v)begin
    p_rank=qr[qh%8192];p_ord=qo[qh%8192];qh=qh+1;
    rsp_frame=owner_frame;rsp_rank=p_rank;rsp_ordinal=p_ord;
    if(p_ord>=nslot[p_rank]) $fatal(1,"read past the last slot rank %0d ord %0d",p_rank,p_ord);
    case(slot[p_rank][p_ord][18:17])
     2'd0:begin rsp_empty=0;rsp_last=0;rsp_tuple=0;end
     2'd1:begin rsp_empty=0;rsp_last=0;id=slot[p_rank][p_ord][16:0];rsp_tuple={17'(id),16'(16'h3f00+(id%128)),1'b1};end
     2'd2:begin rsp_empty=0;rsp_last=1;rsp_tuple=0;end
     2'd3:begin rsp_empty=1;rsp_last=1;rsp_tuple=0;end
    endcase
    rsp_v=1;
   end
  end
 end
 always @(posedge clk)if(por_n)begin
  if(read_v&&read_r)begin
   if(read_frame!==owner_frame)$fatal(1,"read owner violation");
   qr[qt%8192]=read_rank;qo[qt%8192]=read_ordinal;qdue[qt%8192]=cycle+LAT;qt=qt+1;requests=requests+1;
  end
  if(rsp_v&&rsp_r)rsp_v<=0;
  if(stalled&&out_v&&out_tuple!==stalled_tuple)$fatal(1,"output changed under stall");
  stalled=out_v&&!out_r;stalled_tuple=out_tuple;
  if(out_v&&out_r)begin
   if(received>=N)$fatal(1,"extra output");
   id=sorted[received];
   if(out_frame!==owner_frame||out_rank!=(id%96)||out_tuple!=={17'(id),16'(16'h3f00+(id%128)),1'b1})
    $fatal(1,"sparse order mismatch at %0d: got %0d want %0d",received,out_tuple[33:17],id);
   received=received+1;
  end
  if(fault)$fatal(1,"unexpected order fault at %0d",received);
  if(done)begin
   if(received!=N||requests!=total_reads)$fatal(1,"sparse shape/debt mismatch %0d %0d %0d",received,requests,total_reads);
   $display("PASS_GLOBAL_ORDER_SPARSE n=%0d seed=%0d lat=%0d stall=%0d reads=%0d cycles=%0d",N,SEED,LAT,STALL,requests,cycle);$finish;
  end
 end
 initial begin
  repeat(4)@(negedge clk);por_n=1;owner_valid=1;publication_complete=1;
  repeat(3)@(negedge clk);start=1;@(negedge clk);start=0;
 end
 initial begin repeat(2000000)@(posedge clk);$fatal(1,"sparse order deadlock");end
endmodule
