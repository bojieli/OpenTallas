`timescale 1ns/1ps
module tb_hgi_vm_wide;
localparam NB=4,NC=2,CW=8,SB=11,DW=276;
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg [NB*DW-1:0] dma=0;wire[NB-1:0]dr,dd;
reg [CW*(DW+16)-1:0]coll=0;wire[CW-1:0]cr,cd;wire[CW*16-1:0]ct;
reg[NC-1:0]qv=0;wire[NC-1:0]qr;reg[NC*337-1:0]q=0;
wire[NC-1:0]sv;reg[NC-1:0]sr=0;wire[NC*273-1:0]s;
wire fault;wire[31:0]ce;
parameter MUT=0;
ot_hgi_vm_wide #(.ENABLE(1),.NB(NB),.NC(NC),.MUT(MUT)) dut(clk,rst_n,dma,dr,dd,coll,cr,cd,ct,qv,qr,q,sv,sr,s,fault,ce);
integer cyc=0,waccept=0,wack=0,naccept=0,nack=0,paccept=0,presp=0;
integer i,j,base,got;reg[255:0]gold[0:2047];reg[15:0] expected_tag[0:7];reg[7:0]live=0;
integer dt[0:3][0:511],nt[0:7][0:255];integer dh[0:3],dtail[0:3];integer nh[0:7],ntail[0:7];
reg[255:0]pat;reg[31:0]a;integer sector;
always @(posedge clk)if(rst_n)begin
 cyc=cyc+1;
 if(fault)$fatal(1,"unexpected fault cycle %0d",cyc);
 for(integer b=0;b<4;b=b+1)begin
 if(dr[b]&&dma[b*DW+DW-1])begin
 waccept=waccept+1;dt[b][dtail[b]]=cyc;dtail[b]=dtail[b]+1;
 sector=dma[b*DW+264+:SB];for(integer k=0;k<8;k=k+1)if(dma[b*DW+k])gold[sector][k*32+:32]=dma[b*DW+8+k*32+:32];end
 end
 for(integer l=0;l<8;l=l+1)if(cr[l]&&coll[l*(DW+16)+DW+15])begin
 naccept=naccept+1;nt[l][ntail[l]]=cyc;ntail[l]=ntail[l]+1;
 sector=coll[l*(DW+16)+280+:SB];for(integer k=0;k<8;k=k+1)if(coll[l*(DW+16)+16+k])gold[sector][k*32+:32]=coll[l*(DW+16)+24+k*32+:32];
 end
 for(integer c=0;c<NC;c=c+1)if(qv[c]&&qr[c])paccept=paccept+1;
 #1;
 for(integer b=0;b<4;b=b+1)if(dd[b])begin
 if(dh[b]>=dtail[b] || cyc-dt[b][dh[b]]!=5)$fatal(1,"DMA ACK identity/latency %0d",cyc-dt[b][dh[b]]);
 dh[b]=dh[b]+1;wack=wack+1;end
 for(integer l=0;l<8;l=l+1)if(cd[l])begin
 if(nh[l]>=ntail[l] || cyc-nt[l][nh[l]]!=5 || ct[l*16+:16]!==expected_tag[l])$fatal(1,"native ACK identity %h expected %h",ct[l*16+:16],expected_tag[l]);
 nh[l]=nh[l]+1;nack=nack+1;end
end
// Bank registered ACK is sampled by body one edge later: accept->bodyACK5 elapsed.
task packet_read(input integer c,input integer sec,input[15:0]tag);
 reg[272:0]held;
 begin
 @(negedge clk);q[c*337+:337]={1'b0,32'(sec*32),256'd0,32'd0,tag};qv[c]=1;
 do @(posedge clk);while(!qr[c]);@(negedge clk);qv[c]=0;
 wait(sv[c]);held=s[c*273+:273];
 if(held!=={tag,1'b0,gold[sec]})$fatal(1,"read mismatch sec%0d got%h expected%h",sec,held,gold[sec]);
 repeat(3)begin @(negedge clk);if(!sv[c]||s[c*273+:273]!==held)$fatal(1,"response changed under stall");end
 sr[c]=1;@(posedge clk);@(negedge clk);sr[c]=0;presp=presp+1;
 end
endtask
initial begin
 for(i=0;i<2048;i=i+1)gold[i]=0;
 for(i=0;i<4;i=i+1)begin dh[i]=0;dtail[i]=0;end
 for(i=0;i<8;i=i+1)begin nh[i]=0;ntail[i]=0;expected_tag[i]=16'hA100+i;end
 repeat(3)@(negedge clk);rst_n=1;
 // Four logical banks alternating real physical phases sustain four sectors/cycle.
 for(j=0;j<128;j=j+1)begin
 @(negedge clk);
 for(i=0;i<4;i=i+1)dma[i*DW+:DW]={1'b1,SB'(i+4*j),{8{32'(j*11+i)}},8'hff};
 @(posedge clk);if(dr!==4'hf)$fatal(1,"II2 phase admission cycle%0d ready%h",j,dr);
 end
 @(negedge clk);dma=0;repeat(8)@(negedge clk);
 if(waccept!=512||wack!=512)$fatal(1,"DMA count %0d/%0d",waccept,wack);
 // Eight COLL publishers collide at the same logical bank and phase, held until admitted.
 for(i=0;i<8;i=i+1)coll[i*(DW+16)+:DW+16]={1'b1,SB'(512+i*8),{8{32'(32'habc000+i)}},8'hff,expected_tag[i]};
 live=8'hff;
 fork
 begin
 while(live!=0)begin
 @(posedge clk);for(i=0;i<8;i=i+1)if(cr[i]&&live[i])live[i]=0;
 @(negedge clk);for(i=0;i<8;i=i+1)if(!live[i])coll[i*(DW+16)+DW+15]=0;
 end
 end
 packet_read(1,0,16'h4159);
 join
 coll=0;repeat(8)@(negedge clk);
 if(naccept!=8||nack!=8)$fatal(1,"native count");
 packet_read(0,0,16'hA501);packet_read(1,511,16'h4150);
 for(i=0;i<8;i=i+1)packet_read(0,512+i*8,16'hA580+i);
 // Eight outstanding requests are bounded; ninth cannot be accepted while responses stall.
 for(j=0;j<8;j=j+1)begin
 @(negedge clk);qv[0]=1;q[0+:337]={1'b0,32'(j*32),256'd0,32'd0,16'(16'hb000+j)};
 do @(posedge clk);while(!qr[0]);
 end
 @(negedge clk);q[0+:337]={1'b0,32'd256,256'd0,32'd0,16'hb008};
 repeat(4)begin @(posedge clk);if(qr[0])$fatal(1,"OUT8 overloaded");end
 @(negedge clk);qv[0]=0;
 for(j=0;j<8;j=j+1)begin
 wait(sv[0]);
 if(s[0+:273]!=={16'(16'hb000+j),1'b0,gold[j]})$fatal(1,"ordered OUT8 identity");
 @(negedge clk);sr[0]=1;@(posedge clk);@(negedge clk);sr[0]=0;presp=presp+1;
 end
 // Unwritten sectors remain unobservable; no SRAM reset-content assumption.
 @(negedge clk);qv[0]=1;q[0+:337]={1'b0,32'd32000,256'd0,32'd0,16'hdead};
 repeat(3)begin @(posedge clk);if(qr[0])$fatal(1,"uninitialized read admitted");end
 @(negedge clk);qv[0]=0;
 // High addresses and unaligned byte addresses are fail-closed (not aliases).
 @(negedge clk);qv=1;q[0+:337]={1'b0,32'h00800000,256'd0,32'd0,16'hdead};
 repeat(3)begin @(posedge clk);if(qr[0])$fatal(1,"high bounds accepted");end
 @(negedge clk);q[0+:337]={1'b0,32'd1,256'd0,32'd0,16'hdead};
 repeat(3)begin @(posedge clk);if(qr[0])$fatal(1,"unaligned accepted");end
 @(negedge clk);qv=0;
 $display("PASS wide body DMA=%0d native=%0d packets=%0d actual macros=16 II2 phase interleave exact tags bounds backpressure",wack,nack,presp);$finish;
end
initial begin #100000;$fatal(1,"watchdog");end
endmodule
