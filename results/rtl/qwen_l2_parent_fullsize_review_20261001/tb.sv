
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0;
reg [31:0] w_v=0,commit_ready=0,r_v=0,rsp_ready=0;
wire [31:0] w_ready,commit_v,r_ready,rsp_v,fault;
reg [511:0] w_local_row=0,w_epoch=0,w_id=0,r_local_row=0,r_epoch=0,r_id=0;
reg [575:0] w_global_row=0,w_partition_base=0,r_global_row=0,r_partition_base=0;
reg [1023:0] w_data=0;
wire [575:0] commit_row,rsp_row;
wire [511:0] commit_epoch,commit_id,rsp_epoch,rsp_id;
wire [8191:0] rsp_data;
reg [31:0] checkpoint[0:3071];
integer b,k,m,checks=0;reg [31:0] value;reg [17:0] savedrow;
ot_gpu_qwen_l2_macros #(.ENABLE_QWEN_L2(1)) dut(.*);
task write_word(input integer bank,input integer row,input reg [31:0] data);
begin
 @(negedge clk);
 w_local_row[bank*16+:16]=row;w_global_row[bank*18+:18]=bank*96+row;
 w_partition_base[bank*18+:18]=bank*96;w_epoch[bank*16+:16]=42;
 w_id[bank*16+:16]=row;w_data[bank*32+:32]=data;w_v[bank]=1;
 do @(posedge clk);while(!w_ready[bank]);
 @(negedge clk);w_v[bank]=0;
 wait(commit_v[bank]);@(negedge clk);
 savedrow=commit_row[bank*18+:18];
 repeat(3) begin @(negedge clk);
 if(!commit_v[bank] || commit_row[bank*18+:18]!==savedrow) $fatal(1,"unstable stalled commit");
 end
 if(savedrow!==bank*96+row || commit_epoch[bank*16+:16]!==42 || commit_id[bank*16+:16]!==row) $fatal(1,"commit tags");
 commit_ready[bank]=1;@(negedge clk);commit_ready[bank]=0;
end endtask
task read_word(input integer bank,input integer row,input reg [31:0] data);
begin
 @(negedge clk);
 r_local_row[bank*16+:16]=row;r_global_row[bank*18+:18]=bank*96+row;
 r_partition_base[bank*18+:18]=bank*96;r_epoch[bank*16+:16]=42;r_id[bank*16+:16]=row;
 r_v[bank]=1;
 do @(posedge clk);while(!r_ready[bank]);
 @(negedge clk);r_v[bank]=0;
 wait(rsp_v[bank]);@(negedge clk);
 repeat(3)begin
 if(!rsp_v[bank] || rsp_data[bank*256+(row%8)*32+:32]!==data) $fatal(1,"data or stalled response");
 @(negedge clk);end
 if(rsp_row[bank*18+:18]!==bank*96+row || rsp_epoch[bank*16+:16]!==42 || rsp_id[bank*16+:16]!==row) $fatal(1,"read tags");
 rsp_ready[bank]=1;@(negedge clk);rsp_ready[bank]=0;checks=checks+1;
end endtask
initial begin
 $readmemh("checkpoint.hex",checkpoint);
 repeat(3)@(negedge clk);rst_n=1;
 // Entire checkpoint-produced die0 QKV vector, bank partition96 rows.
 for(b=0;b<32;b=b+1)for(k=0;k<96;k=k+1)write_word(b,k,checkpoint[b*96+k]);
 for(b=0;b<32;b=b+1)for(k=0;k<96;k=k+1)read_word(b,k,checkpoint[b*96+k]);
 // Explicit full-depth/macro/lane boundary coverage using pinned payloads.
 for(b=0;b<32;b=b+1)for(m=0;m<8;m=m+1)begin
 write_word(b,m*8192+8184,checkpoint[b*96+m]);
 write_word(b,m*8192+8191,checkpoint[b*96+m+8]);end
 for(b=0;b<32;b=b+1)for(m=0;m<8;m=m+1)begin
 read_word(b,m*8192+8184,checkpoint[b*96+m]);
 read_word(b,m*8192+8191,checkpoint[b*96+m+8]);end
 if(fault!==0)$fatal(1,"unexpected fault");
 // Invalid global identity is rejected by the actual source, no commit.
 @(negedge clk);w_v[0]=1;w_local_row[15:0]=0;w_global_row[17:0]=9;w_partition_base[17:0]=0;
 @(negedge clk);w_v[0]=0;repeat(5)@(negedge clk);
 if(!fault[0] || commit_v[0])$fatal(1,"bad identity admission");
 repeat(160)@(negedge clk);
 $display("COMPLETE checkpoint3072 boundary512 checks=%0d trailing160 identity_negative1",checks);
 $finish;
end
initial begin #2000000;$fatal(1,"TIMEOUT");end
endmodule
