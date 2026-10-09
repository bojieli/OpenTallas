`timescale 1ps/1fs
module tb_hgi_idx_native_ds_dispatch;
parameter MUTANT=0;
reg clk=0; always #416.6665 clk=~clk;
reg rst_n=0,held_valid=0;
reg [3:0]cmd_unit=9;reg [5:0]cmd_op=3;
reg [31:0]held_job=32'hface1234;reg[3:0]held_gen=13;
reg[19:0]held_pos=20'hfffff;reg[6:0]held_rank=0;
reg[3:0]in_valid=0,in_last=0,out_ready=0;
reg[63:0]in_lv=0;reg[1023:0]in_val=0;reg[1279:0]in_idx=0;
reg[11:0]in_k=512;
reg[271:0]mem_rdata=0,ref_mem_rdata=0;
reg[67:0]memory[0:4095],ref_memory[0:4095];
wire decode_error;
wire [31:0] out_job,ref_out_job;
wire [3:0] out_gen,ref_out_gen;
wire [19:0] out_pos,ref_out_pos;
wire [6:0] out_rank,ref_out_rank;
wire [4-1:0] in_ready,ref_in_ready;
wire [4-1:0] out_valid,ref_out_valid;
wire [4-1:0] out_last,ref_out_last;
wire [4*(16/8)-1:0] out_lv,ref_out_lv;
wire [4*(16/8)*16-1:0] out_val,ref_out_val;
wire [4*(16/8)*(20-3)-1:0] out_blk,ref_out_blk;
wire [4-1:0] mem_we,ref_mem_we;
wire [4*10-1:0] mem_waddr,ref_mem_waddr;
wire [4*(16/8)*(14+20)-1:0] mem_wdata,ref_mem_wdata;
wire [4-1:0] mem_re,ref_mem_re;
wire [4*10-1:0] mem_raddr,ref_mem_raddr;
wire  rep_req,ref_rep_req;
wire  ovf,ref_ovf;
wire  busy,ref_busy;
wire [4*3*(10+1)-1:0] stats,ref_stats;
ot_hgi_idx_native_ds_dispatch #(.MUTANT_ID(MUTANT)) dut(
.clk(clk),
.rst_n(rst_n),
.cmd_unit(cmd_unit),
.cmd_op(cmd_op),
.decode_error(decode_error),
.held_valid(held_valid),
.held_job(held_job),
.held_gen(held_gen),
.held_pos(held_pos),
.held_rank(held_rank),
.out_job(out_job),
.out_gen(out_gen),
.out_pos(out_pos),
.out_rank(out_rank),
.in_valid(in_valid),
.in_ready(in_ready),
.in_last(in_last),
.in_lv(in_lv),
.in_val(in_val),
.in_idx(in_idx),
.in_k(in_k),
.out_valid(out_valid),
.out_ready(out_ready),
.out_last(out_last),
.out_lv(out_lv),
.out_val(out_val),
.out_blk(out_blk),
.mem_we(mem_we),
.mem_waddr(mem_waddr),
.mem_wdata(mem_wdata),
.mem_re(mem_re),
.mem_raddr(mem_raddr),
.mem_rdata(mem_rdata),
.rep_req(rep_req),
.ovf(ovf),
.busy(busy),
.stats(stats)
);
ot_hbm_accel_index_candidate #(.ENABLE(1)) reference(
.clk(clk),
.rst_n(rst_n),
.held_valid(held_valid && cmd_unit==9 && cmd_op==3),
.held_job(held_job),
.held_gen(held_gen),
.held_pos(held_pos),
.held_rank(held_rank),
.out_job(ref_out_job),
.out_gen(ref_out_gen),
.out_pos(ref_out_pos),
.out_rank(ref_out_rank),
.in_valid(in_valid),
.in_ready(ref_in_ready),
.in_last(in_last),
.in_lv(in_lv),
.in_val(in_val),
.in_idx(in_idx),
.in_k(in_k),
.out_valid(ref_out_valid),
.out_ready(out_ready),
.out_last(ref_out_last),
.out_lv(ref_out_lv),
.out_val(ref_out_val),
.out_blk(ref_out_blk),
.mem_we(ref_mem_we),
.mem_waddr(ref_mem_waddr),
.mem_wdata(ref_mem_wdata),
.mem_re(ref_mem_re),
.mem_raddr(ref_mem_raddr),
.mem_rdata(ref_mem_rdata),
.rep_req(ref_rep_req),
.ovf(ref_ovf),
.busy(ref_busy),
.stats(ref_stats)
);
always @(posedge clk) for(integer q=0;q<4;q=q+1)begin
 if(mem_we[q])memory[q*1024+mem_waddr[q*10+:10]]<=mem_wdata[q*68+:68];
 if(mem_re[q])mem_rdata[q*68+:68]<=memory[q*1024+mem_raddr[q*10+:10]];
 if(ref_mem_we[q])ref_memory[q*1024+ref_mem_waddr[q*10+:10]]<=ref_mem_wdata[q*68+:68];
 if(ref_mem_re[q])ref_mem_rdata[q*68+:68]<=ref_memory[q*1024+ref_mem_raddr[q*10+:10]];
end
integer cycle=0,consumed=0,writes=0,reads=0;
always @(posedge clk)if(rst_n)begin
 cycle=cycle+1;
 if({in_ready,out_valid,out_last,mem_we,mem_waddr,mem_wdata,mem_re,mem_raddr,rep_req,ovf,busy,stats}!==
 {ref_in_ready,ref_out_valid,ref_out_last,ref_mem_we,ref_mem_waddr,ref_mem_wdata,ref_mem_re,ref_mem_raddr,ref_rep_req,ref_ovf,ref_busy,ref_stats})$fatal(1,"NATIVE_CONTROL_MEMORY_LOCKSTEP cycle%0d",cycle);
 if(rep_req||ovf)$fatal(1,"lawful native extent unexpectedly overflows");
 if({out_job,out_gen,out_pos,out_rank}!=={held_job,held_gen,held_pos,held_rank})$fatal(1,"tuple truncation");
 for(integer q=0;q<4;q=q+1)begin
  if(mem_we[q])writes=writes+1;
  if(mem_re[q])reads=reads+1;
  if(out_valid[q]&&out_ready[q]&&out_lv[q*2+:2]!==ref_out_lv[q*2+:2])$fatal(1,"consumed lane-valid mismatch");
  if(out_valid[q]&&out_ready[q])for(integer lane=0;lane<2;lane=lane+1)if(out_lv[q*2+lane])begin
   consumed=consumed+1;
   if(out_lv[q*2+lane]!==ref_out_lv[q*2+lane]||out_blk[(q*2+lane)*17+:17]!==ref_out_blk[(q*2+lane)*17+:17]||out_val[(q*2+lane)*16+:16]!==ref_out_val[(q*2+lane)*16+:16])$fatal(1,"CONSUMING_ID_VALUE_MUTANT cycle%0d q%0d lane%0d",cycle,q,lane);
  end
 end
end
integer sent[0:3],counts[0:3],base[0:3];reg[3:0]finished;
task automatic run_case(input integer k,input bit unbalanced);
 integer ticks,block_id,initial_consumed;
 begin
 @(negedge clk);rst_n=0;held_valid=0;in_valid=0;in_last=0;
 repeat(4)@(negedge clk);rst_n=1;held_valid=1;in_k=k;finished=0;ticks=0;initial_consumed=consumed;
 for(integer q=0;q<4;q=q+1)begin sent[q]=0;counts[q]=unbalanced?(q==0?1366:0):(q==3?346:340);base[q]=unbalanced?0:q*340;end
 while(finished!=15)begin
  in_valid=0;in_last=0;in_lv=0;in_val=0;in_idx=0;
  out_ready=4'hf;
  for(integer q=0;q<4;q=q+1)begin
   out_ready[q]=((ticks+q)%7!=0)&&((ticks+q)%11!=0);
   if(sent[q]<((counts[q]+1)/2) || (counts[q]==0&&sent[q]==0))begin
    in_valid[q]=((ticks+q)%5!=0);
    in_last[q]=counts[q]==0||sent[q]==(counts[q]+1)/2-1;
    for(integer lane=0;lane<16;lane=lane+1)begin
     block_id=base[q]+sent[q]*2+lane/8;
     if(sent[q]*2+lane/8<counts[q])begin
      in_lv[q*16+lane]=1;
      in_idx[(q*16+lane)*20+:20]=(block_id*96)*8+lane%8;
      // equal-score survivors exercise SRAM sweeps and exact tie order.
      in_val[(q*16+lane)*16+:16]=16'h3f80;
     end
    end
   end
  end
  @(posedge clk);
  for(integer q=0;q<4;q=q+1)begin
   if(in_valid[q]&&in_ready[q])sent[q]=sent[q]+1;
   if(out_valid[q]&&out_ready[q]&&out_last[q])finished[q]=1;
  end
  ticks=ticks+1;
  if(ticks>100000)$fatal(1,"native full context failed finite drain");
  @(negedge clk);
 end
 in_valid=0;held_valid=0;
 if(consumed-initial_consumed!=(k<1366?k:1366))$fatal(1,"native selected count mismatch");
 $display("PASS_NATIVE k=%0d unbalanced=%0d cycles=%0d consumed=%0d writes=%0d reads=%0d",k,unbalanced,ticks,consumed,writes,reads);
 end
endtask
initial begin
 run_case(512,0);run_case(512,1);run_case(2048,1);run_case(1,0);
 @(negedge clk);cmd_op=2;held_valid=1;in_valid=15;
 repeat(4)@(negedge clk);
 if(!decode_error||in_ready!=0||out_valid!=0||mem_we!=0)$fatal(1,"generic TOPK aliased DS SELECT");
 $display("PASS_HGI_NATIVE_INDEX512_LOCKSTEP");$finish;
end
endmodule
