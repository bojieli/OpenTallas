`timescale 1ps/1fs
module tb_hbm_index_global_order #(parameter integer SCAN_CASE=0);
 reg clk=0;always #416.667 clk=~clk;
 reg por_n=0,start=0,publication_complete=0,owner_valid=0;
 reg [72:0] start_frame={20'hfffff,53'h123456789ab},owner_frame={20'hfffff,53'h123456789ab};
 wire start_r,read_v;reg read_r=0;
 wire [72:0] read_frame;wire [6:0] read_rank;wire [16:0] read_ordinal;
 reg rsp_v=0;wire rsp_r;reg [72:0] rsp_frame=0;reg [6:0] rsp_rank=0;
 reg [16:0] rsp_ordinal=0;reg [33:0] rsp_tuple=0;reg rsp_last=0,rsp_empty=0;
 wire out_v;reg out_r=0;wire [33:0] out_tuple;wire [72:0] out_frame;
 wire [6:0] out_rank;wire retained,done,fault;
 ot_hbm_index_global_order #(.ENABLE(1),.STATIC_SCAN(SCAN_CASE)) dut(.*);
 integer cycle=0,received=0,requests=0,id,local_ord,expected_reads=0;
 reg pending=0;integer delay_count=0;reg [6:0] p_rank;reg [16:0] p_ord;
 reg [33:0] stalled_tuple;reg stalled=0;
 reg mutant,future_id;
 initial begin
  mutant=$test$plusargs("MUT_RANK");future_id=$test$plusargs("FUTURE_ID");
  if(future_id)begin start_frame={20'd0,53'h123456789ab};owner_frame=start_frame;end
 end
 always @(negedge clk)begin
  if(!por_n)begin read_r=0;out_r=0;rsp_v=0;pending=0;cycle=0;end
  else begin
   cycle=cycle+1;
   read_r=!pending&&!rsp_v&&(cycle%7!=0);
   out_r=(cycle%5==0);
   if(pending&&delay_count>0)delay_count=delay_count-1;
   if(pending&&delay_count==0&&!rsp_v)begin
    rsp_frame=owner_frame;rsp_rank=p_rank;rsp_ordinal=p_ord;
    // One leading invalid slot followed by actual round-robin owned blocks,
    // then one trailing invalid slot. Every extent comes from the provider.
    local_ord=p_ord-1;id=local_ord*96+p_rank;
    rsp_empty=0;
    if(p_ord==0)begin rsp_tuple=0;rsp_last=0;end
    else if(id>=131072)begin rsp_tuple=0;rsp_last=1;end
    else begin rsp_tuple={17'(id),16'(16'h3f00+(id%128)),1'b1};rsp_last=0;end
    if(mutant&&p_rank==1&&p_ord==1)rsp_rank=2;
    rsp_v=1;pending=0;
   end
  end
 end
 always @(posedge clk)if(por_n)begin
  if(read_v&&read_r)begin
   if(read_frame!==owner_frame||pending||rsp_v)$fatal(1,"read debt/owner violation");
   p_rank=read_rank;p_ord=read_ordinal;pending=1;delay_count=2+(cycle%3);requests=requests+1;
  end
  if(rsp_v&&rsp_r)rsp_v<=0;
  if(stalled&&out_v&&out_tuple!==stalled_tuple)$fatal(1,"output changed under stall");
  stalled=out_v&&!out_r;stalled_tuple=out_tuple;
  if(out_v&&out_r)begin
   if(out_frame!==owner_frame||out_rank!=(received%96)||
      out_tuple!=={17'(received),16'(16'h3f00+(received%128)),1'b1})
    $fatal(1,"canonical ID or exact score mismatch at %0d",received);
   received=received+1;
  end
  if(fault)begin
   if(mutant||future_id)begin $display("EXPECTED_BAD_IDENTITY_REJECT received=%0d",received);$finish;end
   else $fatal(1,"unexpected order fault at %0d",received);
  end
  if(done)begin
   if(mutant||future_id)$fatal(1,"wrong provider accepted");
   if(received!=131072||requests!=131264)$fatal(1,"full shape/debt mismatch %0d %0d",received,requests);
   $display("PASS_GLOBAL_ORDER ranks=96 tuples=%0d actual_reads=%0d cycles=%0d",received,requests,cycle);$finish;
  end
 end
 initial begin
  repeat(4)@(negedge clk);por_n=1;owner_valid=1;publication_complete=1;
  repeat(3)@(negedge clk);start=1;@(negedge clk);start=0;
 end
 initial begin repeat(5000000)@(posedge clk);$fatal(1,"finite order handshake deadlock");end
endmodule
