`timescale 1ps/1fs
module tb;
reg clk=0;always #512 clk=~clk;
reg rst_n=0;reg[31:0]k_v=0,k_we=0;wire[31:0]k_rdy;
reg[959:0]k_addr=0;reg[127:0]k_len=0;reg[543:0]k_tag=0;reg[8191:0]k_wdata=0;reg[1023:0]k_wstrb='1;
wire[31:0]kr_v,k_wr_done;reg[31:0]kr_rdy='1;
wire[543:0]kr_tag;wire[127:0]kr_beat;wire[8191:0]kr_data;
wire[31:0]row_v,col_v,col_we;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
wire[8191:0]col_data;wire[1023:0]col_strb;reg[31:0]dram_rvalid=0;reg[8191:0]dram_rdata=0;wire fault;
wire[31:0]pc_clk={32{clk}};ot_hbm_svc_native_sector_queued_stack dut(.*);
integer cyc=0,reads=0,writes=0,acks=0,responses=0,refreshes=0;
reg opened[0:31][0:31];integer current_row[0:31][0:31],act_at[0:31][0:31],pre_at[0:31][0:31],refresh_until[0:31][0:31];
reg[255:0]mem[0:31][0:1];integer memrow[0:1],membank[0:31][0:1],memcol[0:31][0:1];
reg[5:0]due_v[0:31];reg[255:0]due_data[0:31];reg[31:0]wr_posted=0;
reg[31:0]ack_seen=0,rsp_seen=0;integer round_no=0;integer accepted[0:31],max_write=0,max_read=0;
function[255:0]word(input integer pc,input integer roundid);begin word={8{32'hda710000 ^ 32'(pc*731) ^ 32'(roundid*17)}};end endfunction
always @(posedge clk)begin:external_dram
 integer p,b,kind,rr,idx;
 cyc=cyc+1;dram_rvalid<=0;
 if(rst_n)begin
  if(fault)$fatal(1,"native controller fault at%0d",cyc);
  for(p=0;p<32;p=p+1)begin
   if(k_v[p] && k_rdy[p])accepted[p]=cyc;
   if(row_v[p])begin
    b=row_bank[p*5+:5];kind=row_op[p*3+:3];rr=row_row[p*19+:19];
    if(kind==1)begin
     if(opened[p][b] || cyc-pre_at[p][b]<16 || cyc<refresh_until[p][b])$fatal(1,"illegalACT p%0d b%0d cy%0d",p,b,cyc);
     opened[p][b]=1;current_row[p][b]=rr;act_at[p][b]=cyc;
    end else if(kind==0)begin
     if(opened[p][b] && cyc-act_at[p][b]<28)$fatal(1,"earlyPRE");
     opened[p][b]=0;pre_at[p][b]=cyc;
    end else if(kind==6)begin
     if(opened[p][b] || cyc-pre_at[p][b]<16 || cyc<refresh_until[p][b])$fatal(1,"illegalREFpb p%0d b%0d cy%0d",p,b,cyc);
     refresh_until[p][b]=cyc+196;refreshes=refreshes+1;
    end else if(kind!=5)$fatal(1,"unexpectedrowcommand%0d",kind);
   end
   if(col_v[p])begin
    b=col_bank[p*5+:5];
    if(!opened[p][b] || cyc-act_at[p][b]<(col_we[p]?10:19) || cyc<refresh_until[p][b])$fatal(1,"columnbeforeactualACT/tRCD p%0d b%0d",p,b);
    idx=-1;
    for(integer j=0;j<2;j=j+1)if(current_row[p][b]==memrow[j] && b==membank[p][j] && col_col[p*5+:5]==memcol[p][j])idx=j;
    if(idx<0)$fatal(1,"actualphysicalcommandaddresswrong p%0d b%0d row%0d col%0d",p,b,current_row[p][b],col_col[p*5+:5]);
    if(col_we[p])begin
     if(col_strb[p*32+:32]!==32'hffffffff)$fatal(1,"mask");
     mem[p][idx]=col_data[p*256+:256];writes=writes+1;wr_posted[p]<=1;
    end else begin
     if(due_v[p]!=0)$fatal(1,"overlappingphysicalread");
     due_v[p]<=6'b1;due_data[p]<=mem[p][idx];reads=reads+1;
    end
   end
   if(due_v[p]!=0)begin
    due_v[p]<=due_v[p]<<1;
    if(due_v[p][5])begin dram_rvalid[p]<=1;dram_rdata[p*256+:256]<=due_data[p];end
   end
   if(k_wr_done[p])begin
    if(!wr_posted[p] || ack_seen[p])$fatal(1,"enqueueACKorWRduplicate p%0d",p);
    wr_posted[p]<=0;ack_seen[p]=1;acks=acks+1;if(cyc-accepted[p]>max_write)max_write=cyc-accepted[p];
   end
   if(kr_v[p])begin
    if(rsp_seen[p] || kr_tag[p*17+:17]!==17'(round_no*32+p) || kr_beat[p*4+:4]!=0 || kr_data[p*256+:256]!==word(p,round_no/2))$fatal(1,"actualreturnidentity/data p%0d",p);
    rsp_seen[p]=1;responses=responses+1;if(cyc-accepted[p]>max_read)max_read=cyc-accepted[p];
   end
  end
 end
end
task tick;begin @(posedge clk);#1;end endtask
initial begin
 for(integer p=0;p<32;p=p+1)begin
  due_v[p]=0;due_data[p]=0;
  for(integer b=0;b<32;b=b+1)begin opened[p][b]=0;current_row[p][b]=0;act_at[p][b]=-1000;pre_at[p][b]=-1000;refresh_until[p][b]=-1000;end
 end
memrow[0]=3;
membank[0][0]=0;memcol[0][0]=0;mem[0][0]=0;
membank[1][0]=7;memcol[1][0]=3;mem[1][0]=0;
membank[2][0]=14;memcol[2][0]=6;mem[2][0]=0;
membank[3][0]=21;memcol[3][0]=9;mem[3][0]=0;
membank[4][0]=28;memcol[4][0]=12;mem[4][0]=0;
membank[5][0]=3;memcol[5][0]=15;mem[5][0]=0;
membank[6][0]=10;memcol[6][0]=18;mem[6][0]=0;
membank[7][0]=17;memcol[7][0]=21;mem[7][0]=0;
membank[8][0]=24;memcol[8][0]=24;mem[8][0]=0;
membank[9][0]=31;memcol[9][0]=27;mem[9][0]=0;
membank[10][0]=6;memcol[10][0]=30;mem[10][0]=0;
membank[11][0]=13;memcol[11][0]=1;mem[11][0]=0;
membank[12][0]=20;memcol[12][0]=4;mem[12][0]=0;
membank[13][0]=27;memcol[13][0]=7;mem[13][0]=0;
membank[14][0]=2;memcol[14][0]=10;mem[14][0]=0;
membank[15][0]=9;memcol[15][0]=13;mem[15][0]=0;
membank[16][0]=16;memcol[16][0]=16;mem[16][0]=0;
membank[17][0]=23;memcol[17][0]=19;mem[17][0]=0;
membank[18][0]=30;memcol[18][0]=22;mem[18][0]=0;
membank[19][0]=5;memcol[19][0]=25;mem[19][0]=0;
membank[20][0]=12;memcol[20][0]=28;mem[20][0]=0;
membank[21][0]=19;memcol[21][0]=31;mem[21][0]=0;
membank[22][0]=26;memcol[22][0]=2;mem[22][0]=0;
membank[23][0]=1;memcol[23][0]=5;mem[23][0]=0;
membank[24][0]=8;memcol[24][0]=8;mem[24][0]=0;
membank[25][0]=15;memcol[25][0]=11;mem[25][0]=0;
membank[26][0]=22;memcol[26][0]=14;mem[26][0]=0;
membank[27][0]=29;memcol[27][0]=17;mem[27][0]=0;
membank[28][0]=4;memcol[28][0]=20;mem[28][0]=0;
membank[29][0]=11;memcol[29][0]=23;mem[29][0]=0;
membank[30][0]=18;memcol[30][0]=26;mem[30][0]=0;
membank[31][0]=25;memcol[31][0]=29;mem[31][0]=0;
memrow[1]=821;
membank[0][1]=11;memcol[0][1]=5;mem[0][1]=0;
membank[1][1]=18;memcol[1][1]=8;mem[1][1]=0;
membank[2][1]=25;memcol[2][1]=11;mem[2][1]=0;
membank[3][1]=0;memcol[3][1]=14;mem[3][1]=0;
membank[4][1]=7;memcol[4][1]=17;mem[4][1]=0;
membank[5][1]=14;memcol[5][1]=20;mem[5][1]=0;
membank[6][1]=21;memcol[6][1]=23;mem[6][1]=0;
membank[7][1]=28;memcol[7][1]=26;mem[7][1]=0;
membank[8][1]=3;memcol[8][1]=29;mem[8][1]=0;
membank[9][1]=10;memcol[9][1]=0;mem[9][1]=0;
membank[10][1]=17;memcol[10][1]=3;mem[10][1]=0;
membank[11][1]=24;memcol[11][1]=6;mem[11][1]=0;
membank[12][1]=31;memcol[12][1]=9;mem[12][1]=0;
membank[13][1]=6;memcol[13][1]=12;mem[13][1]=0;
membank[14][1]=13;memcol[14][1]=15;mem[14][1]=0;
membank[15][1]=20;memcol[15][1]=18;mem[15][1]=0;
membank[16][1]=27;memcol[16][1]=21;mem[16][1]=0;
membank[17][1]=2;memcol[17][1]=24;mem[17][1]=0;
membank[18][1]=9;memcol[18][1]=27;mem[18][1]=0;
membank[19][1]=16;memcol[19][1]=30;mem[19][1]=0;
membank[20][1]=23;memcol[20][1]=1;mem[20][1]=0;
membank[21][1]=30;memcol[21][1]=4;mem[21][1]=0;
membank[22][1]=5;memcol[22][1]=7;mem[22][1]=0;
membank[23][1]=12;memcol[23][1]=10;mem[23][1]=0;
membank[24][1]=19;memcol[24][1]=13;mem[24][1]=0;
membank[25][1]=26;memcol[25][1]=16;mem[25][1]=0;
membank[26][1]=1;memcol[26][1]=19;mem[26][1]=0;
membank[27][1]=8;memcol[27][1]=22;mem[27][1]=0;
membank[28][1]=15;memcol[28][1]=25;mem[28][1]=0;
membank[29][1]=22;memcol[29][1]=28;mem[29][1]=0;
membank[30][1]=29;memcol[30][1]=31;mem[30][1]=0;
membank[31][1]=4;memcol[31][1]=2;mem[31][1]=0;
repeat(4)tick;@(negedge clk);rst_n=1;repeat(32)tick;
@(negedge clk);round_no=0;ack_seen=0;rsp_seen=0;k_we=32'hffffffff;
k_addr[0*30+:30]=30'd98403;k_len[0*4+:4]=1;k_tag[0*17+:17]=17'd0;k_wdata[0*256+:256]=word(0,0);
k_addr[1*30+:30]=30'd102892;k_len[1*4+:4]=1;k_tag[1*17+:17]=17'd1;k_wdata[1*256+:256]=word(1,0);
k_addr[2*30+:30]=30'd111485;k_len[2*4+:4]=1;k_tag[2*17+:17]=17'd2;k_wdata[2*256+:256]=word(2,0);
k_addr[3*30+:30]=30'd120030;k_len[3*4+:4]=1;k_tag[3*17+:17]=17'd3;k_wdata[3*256+:256]=word(3,0);
k_addr[4*30+:30]=30'd128607;k_len[4*4+:4]=1;k_tag[4*17+:17]=17'd4;k_wdata[4*256+:256]=word(4,0);
k_addr[5*30+:30]=30'd100296;k_len[5*4+:4]=1;k_tag[5*17+:17]=17'd5;k_wdata[5*256+:256]=word(5,0);
k_addr[6*30+:30]=30'd108857;k_len[6*4+:4]=1;k_tag[6*17+:17]=17'd6;k_wdata[6*256+:256]=word(6,0);
k_addr[7*30+:30]=30'd117434;k_len[7*4+:4]=1;k_tag[7*17+:17]=17'd7;k_wdata[7*256+:256]=word(7,0);
k_addr[8*30+:30]=30'd126011;k_len[8*4+:4]=1;k_tag[8*17+:17]=17'd8;k_wdata[8*256+:256]=word(8,0);
k_addr[9*30+:30]=30'd130484;k_len[9*4+:4]=1;k_tag[9*17+:17]=17'd9;k_wdata[9*256+:256]=word(9,0);
k_addr[10*30+:30]=30'd106293;k_len[10*4+:4]=1;k_tag[10*17+:17]=17'd10;k_wdata[10*256+:256]=word(10,0);
k_addr[11*30+:30]=30'd110790;k_len[11*4+:4]=1;k_tag[11*17+:17]=17'd11;k_wdata[11*256+:256]=word(11,0);
k_addr[12*30+:30]=30'd119383;k_len[12*4+:4]=1;k_tag[12*17+:17]=17'd12;k_wdata[12*256+:256]=word(12,0);
k_addr[13*30+:30]=30'd123856;k_len[13*4+:4]=1;k_tag[13*17+:17]=17'd13;k_wdata[13*256+:256]=word(13,0);
k_addr[14*30+:30]=30'd99697;k_len[14*4+:4]=1;k_tag[14*17+:17]=17'd14;k_wdata[14*256+:256]=word(14,0);
k_addr[15*30+:30]=30'd108258;k_len[15*4+:4]=1;k_tag[15*17+:17]=17'd15;k_wdata[15*256+:256]=word(15,0);
k_addr[16*30+:30]=30'd116851;k_len[16*4+:4]=1;k_tag[16*17+:17]=17'd16;k_wdata[16*256+:256]=word(16,0);
k_addr[17*30+:30]=30'd121340;k_len[17*4+:4]=1;k_tag[17*17+:17]=17'd17;k_wdata[17*256+:256]=word(17,0);
k_addr[18*30+:30]=30'd129901;k_len[18*4+:4]=1;k_tag[18*17+:17]=17'd18;k_wdata[18*256+:256]=word(18,0);
k_addr[19*30+:30]=30'd105678;k_len[19*4+:4]=1;k_tag[19*17+:17]=17'd19;k_wdata[19*256+:256]=word(19,0);
k_addr[20*30+:30]=30'd114255;k_len[20*4+:4]=1;k_tag[20*17+:17]=17'd20;k_wdata[20*256+:256]=word(20,0);
k_addr[21*30+:30]=30'd118744;k_len[21*4+:4]=1;k_tag[21*17+:17]=17'd21;k_wdata[21*256+:256]=word(21,0);
k_addr[22*30+:30]=30'd123177;k_len[22*4+:4]=1;k_tag[22*17+:17]=17'd22;k_wdata[22*256+:256]=word(22,0);
k_addr[23*30+:30]=30'd98986;k_len[23*4+:4]=1;k_tag[23*17+:17]=17'd23;k_wdata[23*256+:256]=word(23,0);
k_addr[24*30+:30]=30'd107563;k_len[24*4+:4]=1;k_tag[24*17+:17]=17'd24;k_wdata[24*256+:256]=word(24,0);
k_addr[25*30+:30]=30'd112036;k_len[25*4+:4]=1;k_tag[25*17+:17]=17'd25;k_wdata[25*256+:256]=word(25,0);
k_addr[26*30+:30]=30'd120613;k_len[26*4+:4]=1;k_tag[26*17+:17]=17'd26;k_wdata[26*256+:256]=word(26,0);
k_addr[27*30+:30]=30'd129238;k_len[27*4+:4]=1;k_tag[27*17+:17]=17'd27;k_wdata[27*256+:256]=word(27,0);
k_addr[28*30+:30]=30'd105031;k_len[28*4+:4]=1;k_tag[28*17+:17]=17'd28;k_wdata[28*256+:256]=word(28,0);
k_addr[29*30+:30]=30'd109504;k_len[29*4+:4]=1;k_tag[29*17+:17]=17'd29;k_wdata[29*256+:256]=word(29,0);
k_addr[30*30+:30]=30'd118113;k_len[30*4+:4]=1;k_tag[30*17+:17]=17'd30;k_wdata[30*256+:256]=word(30,0);
k_addr[31*30+:30]=30'd126706;k_len[31*4+:4]=1;k_tag[31*17+:17]=17'd31;k_wdata[31*256+:256]=word(31,0);
k_v=32'hffffffff;#1;if(k_rdy!==32'hffffffff)$fatal(1,"fixedrequestslotnotavailable");tick;@(negedge clk);k_v=0;repeat(512)tick;
if(ack_seen!==32'hffffffff || rsp_seen!=0)$fatal(1,"writewindow incomplete");
@(negedge clk);round_no=1;ack_seen=0;rsp_seen=0;k_we=32'h00000000;
k_addr[0*30+:30]=30'd98403;k_len[0*4+:4]=1;k_tag[0*17+:17]=17'd32;k_wdata[0*256+:256]=word(0,0);
k_addr[1*30+:30]=30'd102892;k_len[1*4+:4]=1;k_tag[1*17+:17]=17'd33;k_wdata[1*256+:256]=word(1,0);
k_addr[2*30+:30]=30'd111485;k_len[2*4+:4]=1;k_tag[2*17+:17]=17'd34;k_wdata[2*256+:256]=word(2,0);
k_addr[3*30+:30]=30'd120030;k_len[3*4+:4]=1;k_tag[3*17+:17]=17'd35;k_wdata[3*256+:256]=word(3,0);
k_addr[4*30+:30]=30'd128607;k_len[4*4+:4]=1;k_tag[4*17+:17]=17'd36;k_wdata[4*256+:256]=word(4,0);
k_addr[5*30+:30]=30'd100296;k_len[5*4+:4]=1;k_tag[5*17+:17]=17'd37;k_wdata[5*256+:256]=word(5,0);
k_addr[6*30+:30]=30'd108857;k_len[6*4+:4]=1;k_tag[6*17+:17]=17'd38;k_wdata[6*256+:256]=word(6,0);
k_addr[7*30+:30]=30'd117434;k_len[7*4+:4]=1;k_tag[7*17+:17]=17'd39;k_wdata[7*256+:256]=word(7,0);
k_addr[8*30+:30]=30'd126011;k_len[8*4+:4]=1;k_tag[8*17+:17]=17'd40;k_wdata[8*256+:256]=word(8,0);
k_addr[9*30+:30]=30'd130484;k_len[9*4+:4]=1;k_tag[9*17+:17]=17'd41;k_wdata[9*256+:256]=word(9,0);
k_addr[10*30+:30]=30'd106293;k_len[10*4+:4]=1;k_tag[10*17+:17]=17'd42;k_wdata[10*256+:256]=word(10,0);
k_addr[11*30+:30]=30'd110790;k_len[11*4+:4]=1;k_tag[11*17+:17]=17'd43;k_wdata[11*256+:256]=word(11,0);
k_addr[12*30+:30]=30'd119383;k_len[12*4+:4]=1;k_tag[12*17+:17]=17'd44;k_wdata[12*256+:256]=word(12,0);
k_addr[13*30+:30]=30'd123856;k_len[13*4+:4]=1;k_tag[13*17+:17]=17'd45;k_wdata[13*256+:256]=word(13,0);
k_addr[14*30+:30]=30'd99697;k_len[14*4+:4]=1;k_tag[14*17+:17]=17'd46;k_wdata[14*256+:256]=word(14,0);
k_addr[15*30+:30]=30'd108258;k_len[15*4+:4]=1;k_tag[15*17+:17]=17'd47;k_wdata[15*256+:256]=word(15,0);
k_addr[16*30+:30]=30'd116851;k_len[16*4+:4]=1;k_tag[16*17+:17]=17'd48;k_wdata[16*256+:256]=word(16,0);
k_addr[17*30+:30]=30'd121340;k_len[17*4+:4]=1;k_tag[17*17+:17]=17'd49;k_wdata[17*256+:256]=word(17,0);
k_addr[18*30+:30]=30'd129901;k_len[18*4+:4]=1;k_tag[18*17+:17]=17'd50;k_wdata[18*256+:256]=word(18,0);
k_addr[19*30+:30]=30'd105678;k_len[19*4+:4]=1;k_tag[19*17+:17]=17'd51;k_wdata[19*256+:256]=word(19,0);
k_addr[20*30+:30]=30'd114255;k_len[20*4+:4]=1;k_tag[20*17+:17]=17'd52;k_wdata[20*256+:256]=word(20,0);
k_addr[21*30+:30]=30'd118744;k_len[21*4+:4]=1;k_tag[21*17+:17]=17'd53;k_wdata[21*256+:256]=word(21,0);
k_addr[22*30+:30]=30'd123177;k_len[22*4+:4]=1;k_tag[22*17+:17]=17'd54;k_wdata[22*256+:256]=word(22,0);
k_addr[23*30+:30]=30'd98986;k_len[23*4+:4]=1;k_tag[23*17+:17]=17'd55;k_wdata[23*256+:256]=word(23,0);
k_addr[24*30+:30]=30'd107563;k_len[24*4+:4]=1;k_tag[24*17+:17]=17'd56;k_wdata[24*256+:256]=word(24,0);
k_addr[25*30+:30]=30'd112036;k_len[25*4+:4]=1;k_tag[25*17+:17]=17'd57;k_wdata[25*256+:256]=word(25,0);
k_addr[26*30+:30]=30'd120613;k_len[26*4+:4]=1;k_tag[26*17+:17]=17'd58;k_wdata[26*256+:256]=word(26,0);
k_addr[27*30+:30]=30'd129238;k_len[27*4+:4]=1;k_tag[27*17+:17]=17'd59;k_wdata[27*256+:256]=word(27,0);
k_addr[28*30+:30]=30'd105031;k_len[28*4+:4]=1;k_tag[28*17+:17]=17'd60;k_wdata[28*256+:256]=word(28,0);
k_addr[29*30+:30]=30'd109504;k_len[29*4+:4]=1;k_tag[29*17+:17]=17'd61;k_wdata[29*256+:256]=word(29,0);
k_addr[30*30+:30]=30'd118113;k_len[30*4+:4]=1;k_tag[30*17+:17]=17'd62;k_wdata[30*256+:256]=word(30,0);
k_addr[31*30+:30]=30'd126706;k_len[31*4+:4]=1;k_tag[31*17+:17]=17'd63;k_wdata[31*256+:256]=word(31,0);
k_v=32'hffffffff;#1;if(k_rdy!==32'hffffffff)$fatal(1,"fixedrequestslotnotavailable");tick;@(negedge clk);k_v=0;repeat(512)tick;
if(rsp_seen!==32'hffffffff || ack_seen!=0)$fatal(1,"readwindow incomplete");
@(negedge clk);round_no=2;ack_seen=0;rsp_seen=0;k_we=32'hffffffff;
k_addr[0*30+:30]=30'd26931882;k_len[0*4+:4]=1;k_tag[0*17+:17]=17'd64;k_wdata[0*256+:256]=word(0,1);
k_addr[1*30+:30]=30'd26907651;k_len[1*4+:4]=1;k_tag[1*17+:17]=17'd65;k_wdata[1*256+:256]=word(1,1);
k_addr[2*30+:30]=30'd26916232;k_len[2*4+:4]=1;k_tag[2*17+:17]=17'd66;k_wdata[2*256+:256]=word(2,1);
k_addr[3*30+:30]=30'd26924801;k_len[3*4+:4]=1;k_tag[3*17+:17]=17'd67;k_wdata[3*256+:256]=word(3,1);
k_addr[4*30+:30]=30'd26921190;k_len[4*4+:4]=1;k_tag[4*17+:17]=17'd68;k_wdata[4*256+:256]=word(4,1);
k_addr[5*30+:30]=30'd26929791;k_len[5*4+:4]=1;k_tag[5*17+:17]=17'd69;k_wdata[5*256+:256]=word(5,1);
k_addr[6*30+:30]=30'd26905572;k_len[6*4+:4]=1;k_tag[6*17+:17]=17'd70;k_wdata[6*256+:256]=word(6,1);
k_addr[7*30+:30]=30'd26914141;k_len[7*4+:4]=1;k_tag[7*17+:17]=17'd71;k_wdata[7*256+:256]=word(7,1);
k_addr[8*30+:30]=30'd26926818;k_len[8*4+:4]=1;k_tag[8*17+:17]=17'd72;k_wdata[8*256+:256]=word(8,1);
k_addr[9*30+:30]=30'd26931227;k_len[9*4+:4]=1;k_tag[9*17+:17]=17'd73;k_wdata[9*256+:256]=word(9,1);
k_addr[10*30+:30]=30'd26907008;k_len[10*4+:4]=1;k_tag[10*17+:17]=17'd74;k_wdata[10*256+:256]=word(10,1);
k_addr[11*30+:30]=30'd26915609;k_len[11*4+:4]=1;k_tag[11*17+:17]=17'd75;k_wdata[11*256+:256]=word(11,1);
k_addr[12*30+:30]=30'd26911934;k_len[12*4+:4]=1;k_tag[12*17+:17]=17'd76;k_wdata[12*256+:256]=word(12,1);
k_addr[13*30+:30]=30'd26920503;k_len[13*4+:4]=1;k_tag[13*17+:17]=17'd77;k_wdata[13*256+:256]=word(13,1);
k_addr[14*30+:30]=30'd26929084;k_len[14*4+:4]=1;k_tag[14*17+:17]=17'd78;k_wdata[14*256+:256]=word(14,1);
k_addr[15*30+:30]=30'd26904917;k_len[15*4+:4]=1;k_tag[15*17+:17]=17'd79;k_wdata[15*256+:256]=word(15,1);
k_addr[16*30+:30]=30'd26917562;k_len[16*4+:4]=1;k_tag[16*17+:17]=17'd80;k_wdata[16*256+:256]=word(16,1);
k_addr[17*30+:30]=30'd26926099;k_len[17*4+:4]=1;k_tag[17*17+:17]=17'd81;k_wdata[17*256+:256]=word(17,1);
k_addr[18*30+:30]=30'd26934680;k_len[18*4+:4]=1;k_tag[18*17+:17]=17'd82;k_wdata[18*256+:256]=word(18,1);
k_addr[19*30+:30]=30'd26910481;k_len[19*4+:4]=1;k_tag[19*17+:17]=17'd83;k_wdata[19*256+:256]=word(19,1);
k_addr[20*30+:30]=30'd26902774;k_len[20*4+:4]=1;k_tag[20*17+:17]=17'd84;k_wdata[20*256+:256]=word(20,1);
k_addr[21*30+:30]=30'd26911343;k_len[21*4+:4]=1;k_tag[21*17+:17]=17'd85;k_wdata[21*256+:256]=word(21,1);
k_addr[22*30+:30]=30'd26919924;k_len[22*4+:4]=1;k_tag[22*17+:17]=17'd86;k_wdata[22*256+:256]=word(22,1);
k_addr[23*30+:30]=30'd26928461;k_len[23*4+:4]=1;k_tag[23*17+:17]=17'd87;k_wdata[23*256+:256]=word(23,1);
k_addr[24*30+:30]=30'd26908402;k_len[24*4+:4]=1;k_tag[24*17+:17]=17'd88;k_wdata[24*256+:256]=word(24,1);
k_addr[25*30+:30]=30'd26916875;k_len[25*4+:4]=1;k_tag[25*17+:17]=17'd89;k_wdata[25*256+:256]=word(25,1);
k_addr[26*30+:30]=30'd26925456;k_len[26*4+:4]=1;k_tag[26*17+:17]=17'd90;k_wdata[26*256+:256]=word(26,1);
k_addr[27*30+:30]=30'd26934025;k_len[27*4+:4]=1;k_tag[27*17+:17]=17'd91;k_wdata[27*256+:256]=word(27,1);
k_addr[28*30+:30]=30'd26930350;k_len[28*4+:4]=1;k_tag[28*17+:17]=17'd92;k_wdata[28*256+:256]=word(28,1);
k_addr[29*30+:30]=30'd26906151;k_len[29*4+:4]=1;k_tag[29*17+:17]=17'd93;k_wdata[29*256+:256]=word(29,1);
k_addr[30*30+:30]=30'd26914732;k_len[30*4+:4]=1;k_tag[30*17+:17]=17'd94;k_wdata[30*256+:256]=word(30,1);
k_addr[31*30+:30]=30'd26919237;k_len[31*4+:4]=1;k_tag[31*17+:17]=17'd95;k_wdata[31*256+:256]=word(31,1);
k_v=32'hffffffff;#1;if(k_rdy!==32'hffffffff)$fatal(1,"fixedrequestslotnotavailable");tick;@(negedge clk);k_v=0;repeat(512)tick;
if(ack_seen!==32'hffffffff || rsp_seen!=0)$fatal(1,"writewindow incomplete");
@(negedge clk);round_no=3;ack_seen=0;rsp_seen=0;k_we=32'h00000000;
k_addr[0*30+:30]=30'd26931882;k_len[0*4+:4]=1;k_tag[0*17+:17]=17'd96;k_wdata[0*256+:256]=word(0,1);
k_addr[1*30+:30]=30'd26907651;k_len[1*4+:4]=1;k_tag[1*17+:17]=17'd97;k_wdata[1*256+:256]=word(1,1);
k_addr[2*30+:30]=30'd26916232;k_len[2*4+:4]=1;k_tag[2*17+:17]=17'd98;k_wdata[2*256+:256]=word(2,1);
k_addr[3*30+:30]=30'd26924801;k_len[3*4+:4]=1;k_tag[3*17+:17]=17'd99;k_wdata[3*256+:256]=word(3,1);
k_addr[4*30+:30]=30'd26921190;k_len[4*4+:4]=1;k_tag[4*17+:17]=17'd100;k_wdata[4*256+:256]=word(4,1);
k_addr[5*30+:30]=30'd26929791;k_len[5*4+:4]=1;k_tag[5*17+:17]=17'd101;k_wdata[5*256+:256]=word(5,1);
k_addr[6*30+:30]=30'd26905572;k_len[6*4+:4]=1;k_tag[6*17+:17]=17'd102;k_wdata[6*256+:256]=word(6,1);
k_addr[7*30+:30]=30'd26914141;k_len[7*4+:4]=1;k_tag[7*17+:17]=17'd103;k_wdata[7*256+:256]=word(7,1);
k_addr[8*30+:30]=30'd26926818;k_len[8*4+:4]=1;k_tag[8*17+:17]=17'd104;k_wdata[8*256+:256]=word(8,1);
k_addr[9*30+:30]=30'd26931227;k_len[9*4+:4]=1;k_tag[9*17+:17]=17'd105;k_wdata[9*256+:256]=word(9,1);
k_addr[10*30+:30]=30'd26907008;k_len[10*4+:4]=1;k_tag[10*17+:17]=17'd106;k_wdata[10*256+:256]=word(10,1);
k_addr[11*30+:30]=30'd26915609;k_len[11*4+:4]=1;k_tag[11*17+:17]=17'd107;k_wdata[11*256+:256]=word(11,1);
k_addr[12*30+:30]=30'd26911934;k_len[12*4+:4]=1;k_tag[12*17+:17]=17'd108;k_wdata[12*256+:256]=word(12,1);
k_addr[13*30+:30]=30'd26920503;k_len[13*4+:4]=1;k_tag[13*17+:17]=17'd109;k_wdata[13*256+:256]=word(13,1);
k_addr[14*30+:30]=30'd26929084;k_len[14*4+:4]=1;k_tag[14*17+:17]=17'd110;k_wdata[14*256+:256]=word(14,1);
k_addr[15*30+:30]=30'd26904917;k_len[15*4+:4]=1;k_tag[15*17+:17]=17'd111;k_wdata[15*256+:256]=word(15,1);
k_addr[16*30+:30]=30'd26917562;k_len[16*4+:4]=1;k_tag[16*17+:17]=17'd112;k_wdata[16*256+:256]=word(16,1);
k_addr[17*30+:30]=30'd26926099;k_len[17*4+:4]=1;k_tag[17*17+:17]=17'd113;k_wdata[17*256+:256]=word(17,1);
k_addr[18*30+:30]=30'd26934680;k_len[18*4+:4]=1;k_tag[18*17+:17]=17'd114;k_wdata[18*256+:256]=word(18,1);
k_addr[19*30+:30]=30'd26910481;k_len[19*4+:4]=1;k_tag[19*17+:17]=17'd115;k_wdata[19*256+:256]=word(19,1);
k_addr[20*30+:30]=30'd26902774;k_len[20*4+:4]=1;k_tag[20*17+:17]=17'd116;k_wdata[20*256+:256]=word(20,1);
k_addr[21*30+:30]=30'd26911343;k_len[21*4+:4]=1;k_tag[21*17+:17]=17'd117;k_wdata[21*256+:256]=word(21,1);
k_addr[22*30+:30]=30'd26919924;k_len[22*4+:4]=1;k_tag[22*17+:17]=17'd118;k_wdata[22*256+:256]=word(22,1);
k_addr[23*30+:30]=30'd26928461;k_len[23*4+:4]=1;k_tag[23*17+:17]=17'd119;k_wdata[23*256+:256]=word(23,1);
k_addr[24*30+:30]=30'd26908402;k_len[24*4+:4]=1;k_tag[24*17+:17]=17'd120;k_wdata[24*256+:256]=word(24,1);
k_addr[25*30+:30]=30'd26916875;k_len[25*4+:4]=1;k_tag[25*17+:17]=17'd121;k_wdata[25*256+:256]=word(25,1);
k_addr[26*30+:30]=30'd26925456;k_len[26*4+:4]=1;k_tag[26*17+:17]=17'd122;k_wdata[26*256+:256]=word(26,1);
k_addr[27*30+:30]=30'd26934025;k_len[27*4+:4]=1;k_tag[27*17+:17]=17'd123;k_wdata[27*256+:256]=word(27,1);
k_addr[28*30+:30]=30'd26930350;k_len[28*4+:4]=1;k_tag[28*17+:17]=17'd124;k_wdata[28*256+:256]=word(28,1);
k_addr[29*30+:30]=30'd26906151;k_len[29*4+:4]=1;k_tag[29*17+:17]=17'd125;k_wdata[29*256+:256]=word(29,1);
k_addr[30*30+:30]=30'd26914732;k_len[30*4+:4]=1;k_tag[30*17+:17]=17'd126;k_wdata[30*256+:256]=word(30,1);
k_addr[31*30+:30]=30'd26919237;k_len[31*4+:4]=1;k_tag[31*17+:17]=17'd127;k_wdata[31*256+:256]=word(31,1);
k_v=32'hffffffff;#1;if(k_rdy!==32'hffffffff)$fatal(1,"fixedrequestslotnotavailable");tick;@(negedge clk);k_v=0;repeat(512)tick;
if(rsp_seen!==32'hffffffff || ack_seen!=0)$fatal(1,"readwindow incomplete");
if(reads!=64 || writes!=64 || acks!=64 || responses!=64 || refreshes<32)$fatal(1,"fullcounts");$display("PASS nativeRW32PC physicalcommands64WR64RD ACK64 responses64 REFpb%0d cycles%0d maxWR%0d maxRD%0d",refreshes,cyc,max_write,max_read);$finish;end endmodule
