`timescale 1ps/1fs
module tb;
reg clk=0;always #512 clk=~clk;
wire[31:0]pc_clk={32{clk}};reg rst_n=0;
reg[31:0]k_v=0,k_we=0;wire[31:0]k_rdy,k_wr_done,kr_v;
reg[959:0]k_addr=0;reg[127:0]k_len={32{4'd1}};reg[543:0]k_tag=0;
reg[8191:0]k_wdata=0;reg[1023:0]k_wstrb='1;reg[31:0]kr_rdy='1;
wire[543:0]kr_tag;wire[127:0]kr_beat;wire[8191:0]kr_data;
wire[31:0]row_v,col_v,col_we;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
wire[8191:0]col_data;wire[1023:0]col_strb;reg[31:0]dram_rvalid=0;reg[8191:0]dram_rdata=0;wire fault;
ot_hbm_svc_native_sector_queued_stack dut(.*);
integer cyc=0,writes=0,reads=0,acks=0,responses=0,refreshes=0,first_req=-1,last_ack=0,max_count=0;
reg opened[0:31][0:31];integer current_row[0:31][0:31],act_at[0:31][0:31],pre_at[0:31][0:31],refresh_until[0:31][0:31];
reg[255:0]mem[0:31][0:19];integer col_writes[0:31],pc_acks[0:31];reg[19:0]read_seen[0:31];
reg[5:0]due_v[0:31];reg[255:0]due_data[0:31];
function[29:0]sector(input integer pc,input integer j);reg[29:0]s;begin
 s=(30'd20736<<15)|((((j%4)>>2)^(20736>>2))&7)<<12|((j/4)<<7)|(((j%4)^20736)&3);
 s=s|((pc^((s>>7)&31)^((s>>12)&31))<<2);sector=s;
end endfunction
function[255:0]word(input integer pc,input integer j);begin word={8{32'hc0a50000 ^32'(pc*731)^32'(j*17)}};end endfunction
always @(posedge clk)begin:external_dram
 integer p,b,kind,idx,tag_j;
 cyc=cyc+1;dram_rvalid<=0;
 if(rst_n)begin
  if(fault)$fatal(1,"native queued controller fault cy%0d",cyc);
  for(p=0;p<32;p=p+1)begin
   if(k_v[p]&&k_rdy[p]&&first_req<0)first_req=cyc;
   if(row_v[p])begin
    b=row_bank[p*5+:5];kind=row_op[p*3+:3];
    if(kind==1)begin
     if(opened[p][b]||cyc-pre_at[p][b]<16||cyc<refresh_until[p][b])$fatal(1,"illegalACT");
     opened[p][b]=1;current_row[p][b]=row_row[p*19+:19];act_at[p][b]=cyc;
    end else if(kind==0)begin
     if(opened[p][b]&&cyc-act_at[p][b]<28)$fatal(1,"earlyPRE");
     opened[p][b]=0;pre_at[p][b]=cyc;
    end else if(kind==6)begin
     if(opened[p][b]||cyc-pre_at[p][b]<16||cyc<refresh_until[p][b])$fatal(1,"illegalREFpb");
     refresh_until[p][b]=cyc+196;refreshes=refreshes+1;
    end else if(kind==5)begin for(integer bb=0;bb<32;bb=bb+1)begin opened[p][bb]=0;pre_at[p][bb]=cyc;end end
    else $fatal(1,"unexpected row command");
   end
   if(col_v[p])begin
    b=col_bank[p*5+:5];
    if(!opened[p][b]||cyc-act_at[p][b]<(col_we[p]?10:19)||cyc<refresh_until[p][b])$fatal(1,"column timing");
    idx=col_col[p*5+:5]*4+b;
    if(current_row[p][b]!=20736||b>3||idx>=20)$fatal(1,"actual physical command address wrong");
    if(col_we[p])begin
     if(col_data[p*256+:256]!==word(p,idx)||col_strb[p*32+:32]!==32'hffffffff)$fatal(1,"queued write payload/identity");
     mem[p][idx]=col_data[p*256+:256];writes=writes+1;col_writes[p]=col_writes[p]+1;
    end else begin
     if(due_v[p]!=0)$fatal(1,"overlapping read");due_v[p]<=6'b1;due_data[p]<=mem[p][idx];reads=reads+1;
    end
   end
   if(due_v[p]!=0)begin due_v[p]<=due_v[p]<<1;if(due_v[p][5])begin dram_rvalid[p]<=1;dram_rdata[p*256+:256]<=due_data[p];end end
   if(k_wr_done[p])begin
    if(pc_acks[p]>=col_writes[p])$fatal(1,"enqueue ACK or duplicate WR");pc_acks[p]=pc_acks[p]+1;acks=acks+1;last_ack=cyc;
   end
   if(kr_v[p]&&kr_rdy[p])begin
    tag_j=kr_tag[p*17+:17]/32;
    if(tag_j>=20||kr_tag[p*17+:17]%32!=p||kr_beat[p*4+:4]!=0||read_seen[p][tag_j]||kr_data[p*256+:256]!==word(p,tag_j))$fatal(1,"queued read identity/data");
    read_seen[p][tag_j]=1;responses=responses+1;
   end
  end
  for(integer pp=0;pp<32;pp=pp+1)if(dut.g_pc[0].count>max_count)max_count=dut.g_pc[0].count;
 end
end
task tick;begin @(posedge clk);#1;end endtask
reg[31:0]pending;integer j,guard;
initial begin
 for(integer p=0;p<32;p=p+1)begin
  due_v[p]=0;due_data[p]=0;col_writes[p]=0;pc_acks[p]=0;read_seen[p]=0;
  for(integer b=0;b<32;b=b+1)begin opened[p][b]=0;current_row[p][b]=0;act_at[p][b]=-1000;pre_at[p][b]=-1000;refresh_until[p][b]=-1000;end
  for(integer i=0;i<20;i=i+1)mem[p][i]=0;
 end
 repeat(4)tick;@(negedge clk);rst_n=1;repeat(8)tick;
 for(integer mode=0;mode<2;mode=mode+1)begin
  for(j=0;j<20;j=j+1)begin
   @(negedge clk);k_we=mode==0?'1:0;
   for(integer p=0;p<32;p=p+1)begin k_addr[p*30+:30]=sector(p,j);k_tag[p*17+:17]=17'(j*32+p);k_wdata[p*256+:256]=word(p,j);end
   pending='1;k_v=pending;guard=0;
   while(pending!=0)begin @(posedge clk);pending=pending&~k_rdy;#1;@(negedge clk);k_v=pending;guard=guard+1;if(guard>2000)$fatal(1,"request admission timeout");end
  end
  guard=0;
  while(mode==0?acks<640:responses<640)begin tick;guard=guard+1;if(guard>5000)$fatal(1,"completion timeout");end
  if(mode==0)$display("NATIVE_QUEUED_WRITE640 first=%0d final_ACK=%0d elapsed_HBM_cycles=%0d max_PC0_pending=%0d",first_req,last_ack,last_ack-first_req,max_count);
 end
 repeat(512)tick;
 if(writes!=640||acks!=640||reads!=640||responses!=640||refreshes<32||max_count<16)$fatal(1,"production queue/count proof incomplete");
 $display("NATIVE_QUEUED_PRODUCTION PASS actual_WR640 true_ACK640 actual_RD640 exact_response640 REFpb%0d cycles%0d",refreshes,cyc);$finish;
end
initial begin #20000000;$fatal(1,"timeout");end
endmodule
