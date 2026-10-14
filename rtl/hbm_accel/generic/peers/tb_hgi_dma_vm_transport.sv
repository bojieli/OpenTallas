`timescale 1ns/1ps
module tb_hgi_dma_vm_transport #(parameter integer MUT=0);
 reg sc=0,vc=0,rst=0;always #3 sc=~sc;always #4 vc=~vc;
 reg [31:0] issue=0;wire [32*281-1:0] packet;wire [31:0] credit,done,qfault;wire [7:0] rfault;wire [3:0] drained,lfault;
 wire [32*281-1:0] dq;reg [31:0] dqdone=0;reg [3:0] busy=4'hf;
 ot_hgi_dma_vm_transport #(.MUT(MUT)) dut(.source_clk({4{sc}}),.vm_clk(vc),.rst_n(rst),.lease_grant(4'hf),.producer_busy(busy),
 .issue_v(issue),.source_packet(packet),.source_credit(credit),.source_done(done),.queue_fault(qfault),.drained(drained),.lease_fault(lfault),.dma_q(dq),.dma_done(dqdone),.router_fault(rfault));
 integer sent[0:3],received[0:3],completed[0:3],cr[0:3],target[0:3];
 reg [280:0] launch[0:3][0:4];reg [3:0] mask[0:3][0:127],required[0:3][0:127];
 reg [31:0] commit_tag[0:3][0:63];reg [63:0] commit_v[0:3];
 integer errors=0,cycles=0,totalwrites=0;
 for(genvar s=0;s<4;s++)begin: src
 assign packet[(s*8)*281+:281]=launch[s][4];
 for(genvar b=1;b<8;b++)assign packet[(s*8+b)*281+:281]=281'd0;
 end
 always @(posedge sc)if(rst)begin
 cycles++;issue<=0;
 for(integer s=0;s<4;s++)begin
 integer n,d;reg m;reg [14:0] sector;reg [255:0] data;
 if(done[s*8])begin received[s]++;if(received[s]>completed[s])begin errors++;$display("FAIL transport premature/wrongowner src%0d done%0d actualcomplete%0d",s,received[s],completed[s]);end end
 cr[s]=cr[s]+(credit[s*8]?1:0);
 for(integer k=4;k>0;k--)launch[s][k]<=launch[s][k-1];launch[s][0]<=0;
 if(sent[s]<target[s]&&cr[s]>0 && (s==0||cycles>35))begin
 n=sent[s];d=(n+s+2)%4;m=n%9==4;
 sector=m?15'(n*8):15'((d<<13)+(n*8));data=0;data[31:0]=(s<<16)|n;
 required[s][n]=m?4'hf:(4'd1<<d);mask[s][n]=0;
 launch[s][0]<={1'b1,m,sector,data,8'hff};issue[s*8]<=1;cr[s]--;sent[s]++;
 end
 busy[s]<=sent[s]<target[s]||launch[s][0][280]||launch[s][1][280]||launch[s][2][280]||launch[s][3][280]||launch[s][4][280];
 end
 if(qfault||rfault||lfault)begin errors++;$display("FAIL transport fault queue%h router%h lease%h",qfault,rfault,lfault);end
 if(cycles>3000)$fatal(1,"FATAL TRANSPORT timeout errors=%0d",errors);
 end
 always @(posedge vc)if(rst)begin
 dqdone<=0;
 for(integer d=0;d<4;d++)begin
 integer tag,s,n;reg [280:0] p;
 if(commit_v[d][4+d*12])begin
 tag=commit_tag[d][4+d*12];s=(tag>>16)&3;n=tag&65535;
 if(mask[s][n][d])begin errors++;$display("FAIL duplicatewrite src%0d seq%0d dst%0d",s,n,d);end
 mask[s][n][d]=1;if(mask[s][n]==required[s][n])completed[s]++;
 dqdone[d*8]<=1;
 end
 for(integer k=63;k>0;k--)begin commit_v[d][k]<=commit_v[d][k-1];commit_tag[d][k]<=commit_tag[d][k-1];end
 commit_v[d][0]<=dq[d*8*281+280];commit_tag[d][0]<=dq[d*8*281+8+:32];
 p=dq[d*8*281+:281];if(p[280])begin
 tag=p[39:8];s=(tag>>16)&3;n=tag&65535;
 if(n>=sent[s]||(!p[279]&&p[278:277]!=2'(d))||p[276:264]!=13'(n*8)||p[7:0]!=8'hff||p[266:264]!=0||!required[s][n][d])begin errors++;$display("FAIL native_route dst%0d packet%h",d,p);end
 totalwrites++;
 end
 for(integer b=1;b<8;b++)if(dq[(d*8+b)*281+280])begin errors++;$display("FAIL unexpectedbank");end
 end
 end
 initial begin
 for(integer s=0;s<4;s++)begin sent[s]=0;received[s]=0;completed[s]=0;cr[s]=10;target[s]=37+s*14;commit_v[s]=0;for(integer k=0;k<5;k++)launch[s][k]=0;end
 repeat(6)@(negedge sc);rst=1;
 wait(received[0]==target[0]&&received[1]==target[1]&&received[2]==target[2]&&received[3]==target[3]);
 repeat(30)@(negedge sc);
 for(integer s=0;s<4;s++)if(received[s]!=target[s]||completed[s]!=target[s]||cr[s]!=10||!drained[s])errors++;
 if(errors)$fatal(1,"FATAL TRANSPORT errors=%0d",errors);
 $display("PASS TRANSPORT 3to4clocks sourcequeue10reservations native_sid mirror_all4done ownertickets writes=%0d cycles=%0d",totalwrites,cycles);$finish;
 end
endmodule
