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
reg expect_fault=0;reg[4351:0]packed_row;reg[264:0]packed_group;integer gi,pi;
integer cyc=0,waccept=0,wack=0,naccept=0,nack=0,paccept=0,presp=0;
integer i,j,base,got;reg[255:0]gold[0:2047];reg[15:0] expected_tag[0:7];reg[7:0]live=0;
integer dt[0:3][0:511],nt[0:7][0:255];integer dh[0:3],dtail[0:3];integer nh[0:7],ntail[0:7];
reg[255:0]pat;reg[31:0]a;integer sector;
always @(posedge clk)if(rst_n)begin
 cyc=cyc+1;
 if(fault&&!expect_fault)$fatal(1,"unexpected fault cycle %0d",cyc);
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
 // Cold masked initialization: unreadable until all eight words actually commit.
 expected_tag[0]=16'hac01;
 @(negedge clk);coll[0+:DW+16]={1'b1,SB'(1000),{8{32'h12345678}},8'h0f,expected_tag[0]};
 do @(posedge clk);while(!cr[0]);@(negedge clk);coll=0;repeat(8)@(negedge clk);
 qv[0]=1;q[0+:337]={1'b0,32'd32000,256'd0,32'd0,16'hac01};
 repeat(3)begin @(posedge clk);if(qr[0])$fatal(1,"partially initialized sector read");end
 @(negedge clk);qv=0;expected_tag[0]=16'hac02;
 coll[0+:DW+16]={1'b1,SB'(1000),{8{32'h98765432}},8'hf0,expected_tag[0]};
 do @(posedge clk);while(!cr[0]);@(negedge clk);coll=0;repeat(8)@(negedge clk);
 packet_read(0,1000,16'ha5ff);
 // Actual PACKED1 producer layout0514f84d1: {fmt1,reserved120,scale1,scale0,codes128}.
 packed_row=0;
 for(gi=0;gi<16;gi=gi+1)begin
 packed_group={1'b1,120'd0,8'h36,8'h36,128'd0};
 for(pi=0;pi<32;pi=pi+1)packed_group[pi*4+:4]=(pi[0]?4'h5:4'h7);
 packed_row[gi*265+:265]=packed_group;
 end
 // The final112padbits remain exactly zero across group/word/sector boundaries.
 for(j=0;j<17;j=j+1)begin
 @(negedge clk);dma=0;dma[((1100+j)%4)*DW+:DW]={1'b1,SB'(1100+j),packed_row[j*256+:256],8'hff};
 do @(posedge clk);while(!dr[(1100+j)%4]);
 end
 @(negedge clk);dma=0;repeat(8)@(negedge clk);
 fork
 begin
 for(integer z=0;z<17;z=z+1)begin
 @(negedge clk);qv[0]=1;q[0+:337]={1'b0,32'((1100+z)*32),256'd0,32'd0,16'(16'ha500+z)};
 do @(posedge clk);while(!qr[0]);end
 @(negedge clk);qv[0]=0;
 end
 begin
 repeat(12)@(negedge clk);sr[0]=1;
 for(integer z=0;z<17;z=z+1)begin
 do @(posedge clk);while(!sv[0]);
 if(s[0+:273]!=={16'(16'ha500+z),1'b0,packed_row[z*256+:256]})$fatal(1,"packed row exact/tag sector%0d",z);
 presp=presp+1;
 end
 @(negedge clk);sr[0]=0;
 end
 join
 // High addresses and unaligned byte addresses are fail-closed (not aliases).
 @(negedge clk);qv=1;q[0+:337]={1'b0,32'h00800000,256'd0,32'd0,16'hdead};
 repeat(3)begin @(posedge clk);if(qr[0])$fatal(1,"high bounds accepted");end
 @(negedge clk);q[0+:337]={1'b0,32'd1,256'd0,32'd0,16'hdead};
 repeat(3)begin @(posedge clk);if(qr[0])$fatal(1,"unaligned accepted");end
 @(negedge clk);qv=0;
 // Corrupted visibility must be an explicit fault, distinct from legitimate coldbackpressure.
 @(negedge clk);expect_fault=1;dut.allocated_n[0][0]=8'h01;
 qv[0]=1;q[0+:337]={1'b0,32'd0,256'd0,32'd0,16'ha5ee};
 #1;if(qr[0])$fatal(1,"corrupted visibility admitted");
 @(posedge clk);#1;if(!fault)$fatal(1,"visibility corruption silently stalled");
 @(negedge clk);qv=0;repeat(2)@(negedge clk);if(!fault)$fatal(1,"fault not sticky");
 $display("PASS wide body DMA=%0d native=%0d packets=%0d actual macros=16 II2 phase interleave exact tags bounds backpressure",wack,nack,presp);$finish;
end
initial begin #100000;$fatal(1,"watchdog");end
endmodule
