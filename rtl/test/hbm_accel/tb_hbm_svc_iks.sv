`timescale 1ps/1ps
// Exact transport gate; adversarial finite controller queues, no timing/bandwidth claim.
module tb_hbm_svc_iks;
reg clk=0,efck=0,rst_n=0;always #512 clk=~clk;always #416 efck=~efck;
reg[127:0] ed=0;wire[31:0]kv,krdy,kwe,rv,rrdy;wire[959:0]addr;wire[127:0]len,beat;wire[543:0]tag,rtag;
wire[8191:0]data_;wire[8791:0]lines;wire done,fault;reg[7:0]credit=0;
reg[31:0]respv=0;reg[127:0]respb=0;reg[543:0]respt=0;reg[8191:0]respd=0;
assign rv=respv;assign beat=respb;assign rtag=respt;assign data_=respd;
ot_hbm_svc_core #(.IKS(1),.E_ST(2),.XST(0))dut(.ck(clk),.rst(rst_n),.q_d(336'd0),.q_v(8'd0),.q_fclk(8'd0),.q_rdy(),.line(),.fclk(),
.e_d(ed),.e_fclk(efck),.kv(),.ik(),.phy_clk(),.phy_rst_n(),.k_v(kv),.k_rdy(32'hffffffff),.k_addr(addr),.k_len(len),.k_tag(tag),.k_we(kwe),.k_wdata(),.k_wstrb(),
.kr_v(rv),.kr_rdy(rrdy),.kr_tag(rtag),.kr_beat(beat),.kr_data(data_),.w_v(),.w_rdy(1'b0),.w_addr(),.w_len(),.w_tag(),.w_room(8'd0),.wr_v(8'd0),.wr_rdy(),.wr_tag(80'd0),.wr_beat(40'd0),.wr_data(2048'd0),
.wq_d(292'd0),.wq_fclk(1'b0),.wq_g(),.k_wr_done(32'd0),.kvs(),.kvs_done(),.ik_credit(credit),.ik_lines(lines),.ik_done(done),.ik_fault(fault));
reg[16:0]qt[0:31][0:255];reg[3:0]qb[0:31][0:255];reg[29:0]qa[0:31][0:255];integer head[0:31],tail[0:31],count[0:31];integer p,b,w,cyc=0;
function automatic[29:0] kaddr(input integer pc,j);
 integer row,bank,col,bhi,blo,hi5;
 begin row=4006+(j>>10);bank=(((j>>7)&7)<<2)|(j&3);col=(j>>2)&31;bhi=(bank>>2)^((row>>2)&7);blo=(bank&3)^(row&3);hi5=((row&3)<<3)|bhi;
 kaddr=30'((row<<15)|(bhi<<12)|(col<<7)|(((pc^col^hi5)&31)<<2)|blo);end
endfunction
function automatic[255:0]pat(input[29:0]a);integer i;begin for(i=0;i<8;i=i+1)pat[i*32+:32]=(a*8+i)*32'h9E3779B1^32'h5bd1e995;end endfunction
always @(posedge clk)begin
 respv<=0;cyc<=cyc+1;
 if(rst_n)for(p=0;p<32;p=p+1)begin
  if(count[p]>0&&rrdy[p]&&((cyc+p)%5!=0))begin
   respv[p]<=1;respt[p*17+:17]<=qt[p][head[p]];respb[p*4+:4]<=qb[p][head[p]];respd[p*256+:256]<=pat(qa[p][head[p]]) ^ ((mut==1&&p==5&&qt[p][head[p]][14:5]==3&&qb[p][head[p]]==0)?256'd1:256'd0);
   head[p]=(head[p]+1)%256;count[p]=count[p]-1;
  end
  if(kv[p])begin

   if(kwe[p]||len[p*4+:4]!=4)$fatal(1,"bad request");
   for(b=0;b<4;b=b+1)begin qt[p][tail[p]]=tag[p*17+:17];qb[p][tail[p]]=b;qa[p][tail[p]]=addr[p*30+:30]+b;tail[p]=(tail[p]+1)%256;count[p]=count[p]+1;end
   if(count[p]>64)$fatal(1,"controller overflow");
  end
 end
end
integer got=0,l,i,g,pc,j,off,mut=0,t=0;reg[255:0]ex;integer pend[0:7];reg fin=0;
initial begin
if($value$plusargs("mut=%d",mut))begin end
for(p=0;p<32;p=p+1)begin head[p]=0;tail[p]=0;count[p]=0;end
for(l=0;l<8;l=l+1)pend[l]=0;
repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge efck);
ed[0]=1;ed[2:1]=2;ed[17:3]=4006;ed[70:62]=342;
@(negedge efck);ed[0]=0;
while(!fin)begin
 @(negedge clk);credit=0;
 for(l=0;l<8;l=l+1)if(lines[l*1099])begin
  if(lines[l*1099+1+:10]!==10'(got+l))$fatal(1,"tag");
  for(i=0;i<136;i=i+1)begin
   g=(got+l)*136+i;pc=(g/32)%32;j=g/1024;off=g%32;ex=pat(kaddr(pc,j));
   if(lines[l*1099+11+i*8+:8]!==ex[off*8+:8])$fatal(1,"data line=%0d byte=%0d",got+l,i);
  end
  pend[l]=pend[l]+1;
 end
 if(lines[0])got=got+8;
 // Credit delay forces the finite return-slot reservation to stall issue.
 if(t>300)for(l=0;l<8;l=l+1)if(pend[l]>0)begin credit[l]=1;pend[l]=pend[l]-1;end
 if(fault)$fatal(1,"svc fault got=%0d",got);
 fin=done;t=t+1;if(t>10000)$fatal(1,"timeout got=%0d",got);
end
if(got!=1368)$fatal(1,"count");$display("PASS_HBM_SVC_IKS lines=%0d cycles=%0d",got,t);$finish;
end
endmodule
