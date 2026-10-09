`timescale 1ps/1ps
// Timed full-shape actual IKS service with REFpb; pattern exactness and final-credit drain.
module tb_hbm_svc_iks_timed #(parameter integer SRAM=0,ROTATE=0,HOLD_FINAL_CREDITS=0,BLOCKS=342,SURPLUS_UNUSED=0);
reg clk=0,efck=0,rst_n=0;always #512 clk=~clk;always #416 efck=~efck;
reg[127:0] ed=0;wire[31:0]kv,krdy,kwe,rv,rrdy;wire[959:0]addr;wire[127:0]len,beat;wire[543:0]tag,rtag;
wire[8191:0]data_;wire[8791:0]lines;wire done,fault;reg[7:0]credit=0;
wire phy_clk,phy_rst_n;wire[8191:0]rawdata;wire[8191:0]wdata;wire[1023:0]wstrb;wire[31:0]wdone;
assign data_=rawdata ^ ((mut==1 && rv[5]) ? (8192'd1 << (5*256)) : 8192'd0);
ot_hbm_svc_core #(.IKS(1),.IK_SRAM(SRAM),.IK_SRAM_ROTATE(ROTATE),.E_ST(11),.XST(2))dut(.ck(clk),.rst(rst_n),.q_d(336'd0),.q_v(8'd0),.q_fclk(8'd0),.q_rdy(),.line(),.fclk(),
.e_d(ed),.e_fclk(efck),.kv(),.ik(),.phy_clk(phy_clk),.phy_rst_n(phy_rst_n),.k_v(kv),.k_rdy(krdy),.k_addr(addr),.k_len(len),.k_tag(tag),.k_we(kwe),.k_wdata(wdata),.k_wstrb(wstrb),
.kr_v(rv),.kr_rdy(rrdy),.kr_tag(rtag),.kr_beat(beat),.kr_data(data_),.w_v(),.w_rdy(1'b0),.w_addr(),.w_len(),.w_tag(),.w_room(8'd0),.wr_v(8'd0),.wr_rdy(),.wr_tag(80'd0),.wr_beat(40'd0),.wr_data(2048'd0),
.wq_d(292'd0),.wq_fclk(1'b0),.wq_g(),.k_wr_done(wdone),.kvs(),.kvs_done(),.ik_credit(credit),.ik_lines(lines),.ik_done(done),.ik_fault(fault),.ip_v(1'b0),.ip_d(99'd0),.ip_fault(1'b0),.ip_take(),.wq_source(2'd0),.wq_source_g(),.wq_source_fault(),.wq_source_busy(),.wq_pending());
ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.DW(256),.MEM_WORDS(1024),.TAGW(17),.LENW(4),.BEATW(4),.QD(64),.REFPB(3),.MEM_MODE(1),.CLK_PS(1024)) mem(
.clk(phy_clk),.rst_n(phy_rst_n),.req_v(kv),.req_rdy(krdy),.req_addr(addr),.req_len(len),.req_tag(tag),.req_we(kwe),.req_wdata(wdata),.req_wstrb(wstrb),.wr_done(wdone),.rsp_v(rv),.rsp_rdy(rrdy),.rsp_tag(rtag),.rsp_beat(beat),.rsp_data(rawdata));
wire storage_retained=dut.gkvs.idx_busy;
integer row0=4006;
function automatic[29:0] kaddr(input integer pc,j);
 integer row,bank,col,bhi,blo,hi5;
 begin row=row0+(j>>10);bank=(((j>>7)&7)<<2)|(j&3);col=(j>>2)&31;bhi=(bank>>2)^((row>>2)&7);blo=(bank&3)^(row&3);hi5=((row&3)<<3)|bhi;
 kaddr=30'((row<<15)|(bhi<<12)|(col<<7)|(((pc^col^hi5)&31)<<2)|blo);end
endfunction
function automatic[255:0]pat(input[29:0]a);integer i;begin for(i=0;i<8;i=i+1)pat[i*32+:32]=(a*8+i)*32'h9E3779B1^32'h5bd1e995;end endfunction
integer got=0,l,i,g,pc,j,off,nactive,mut=0,t=0,phase=0,delay_=1,rep_=0;
integer owed[0:7];reg[255:0]ex;reg fin=0,surplus_injected=0;time launch,lastline,drained;
initial begin
if($value$plusargs("mut=%d",mut))begin end
if($value$plusargs("phase_ns=%d",phase))begin end
if($value$plusargs("credit_delay=%d",delay_))begin end
for(l=0;l<8;l=l+1)owed[l]=0;
repeat(10)@(negedge clk);rst_n=1;
#(phase*1000+3000);
for(rep_=0;rep_<2;rep_=rep_+1)begin
 got=0;t=0;fin=0;row0=4006+rep_*8;
 @(negedge efck);ed=0;ed[0]=1;ed[2:1]=2;ed[17:3]=15'(row0);ed[70:62]=9'(BLOCKS);launch=$time;
 @(negedge efck);ed[0]=0;
 while(!fin)begin
  @(negedge clk);credit=0;nactive=0;
  for(l=0;l<8;l=l+1)if(lines[l*1099])begin
   if(got+l>=BLOCKS*4)$fatal(1,"SPURIOUS_PARTIAL_LINE tag=%0d",got+l);
   nactive=nactive+1;
   if(lines[l*1099+1+:10]!==10'(got+l))$fatal(1,"tag");
   for(i=0;i<136;i=i+1)begin
    g=(got+l)*136+i;pc=(g/32)%32;j=g/1024;off=g%32;ex=pat(kaddr(pc,j));
    if(lines[l*1099+11+i*8+:8]!==ex[off*8+:8])$fatal(1,"data line=%0d byte=%0d",got+l,i);
   end
   owed[l]=owed[l]+1;
  end
  if(lines[0])begin got=got+nactive;lastline=$time;end
  if(t%delay_==0 && !(HOLD_FINAL_CREDITS!=0 && got==BLOCKS*4))for(l=0;l<8;l=l+1)if(owed[l]>0)begin credit[l]=1;owed[l]=owed[l]-1;drained=$time+512;end
  if(SURPLUS_UNUSED!=0 && !surplus_injected && dut.gkvs.gi.gsram.idx_lines.can)begin
   credit[7]=1;surplus_injected=1;$display("UNUSED_CREDIT_INJECT");
  end
  if(fault)$fatal(1,"svc fault got=%0d",got);
  fin=done;t=t+1;if(t>2000000)$fatal(1,"protocol timeout got=%0d",got);
 end
 if(got!=BLOCKS*4)$fatal(1,"count got=%0d",got);
 if(HOLD_FINAL_CREDITS!=0)for(i=0;i<12;i=i+1)begin
  @(negedge clk);credit=0;
  if(!storage_retained)$fatal(1,"frame context released with final credit debt");
  if(fault)$fatal(1,"fault while withholding final credits");
 end
 // Return every credit, including the final output group. Repetition proves restoration.
 for(i=0;i<200;i=i+1)begin
  @(negedge clk);credit=0;
  for(l=0;l<8;l=l+1)if(owed[l]>0)begin credit[l]=1;owed[l]=owed[l]-1;drained=$time+512;end
  if(fault)$fatal(1,"fault during final credit drain");
 end
 credit=0;
 if(HOLD_FINAL_CREDITS!=0 && storage_retained)$fatal(1,"retained did not clear after all credits returned");
 for(l=0;l<8;l=l+1)if(owed[l]!=0)$fatal(1,"credit debt lane=%0d owed=%0d",l,owed[l]);
 $display("IKS_TIMED rep=%0d phase_ns=%0d credit_delay=%0d lines=%0d bytes=%0d last_line_ns=%0.3f drain_ns=%0.3f logical_tbs=%0.6f",rep_,phase,delay_,got,BLOCKS*544,(lastline-launch)/1000.0,(drained-launch)/1000.0,(BLOCKS*544.0)/(lastline-launch));
end
$display("PASS_HBM_SVC_IKS_TIMED");$finish;
end
endmodule
