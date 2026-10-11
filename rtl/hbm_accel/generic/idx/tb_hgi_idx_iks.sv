`timescale 1ps/1ps
// hgi-1010/g: the IDX index-key stream issuer (ot_hgi_idx_iks_issue) driving a REAL svc stack (ot_hbm_svc_core_native
// IKS = 1, the kind-2 stripe over 32 PCs) on a 32-PC DRAM controller model: every PC accepts a 4-sector read a cycle and
// returns its beats in order LAT cycles later, one beat a PC a cycle (+ADV=1: the adversarial model of
// tb_loader_service_iks -- a stall every 5th cycle per PC and index-line credits returned every 23 cycles).
// One frame of n keys; the bench feeds quarter QSEL's command to the stack, checks every index line (tag order and all
// 136 bytes, against the address map of the issuer's header: DRAM sector of (pc, j) from row0) and the line count
// 4 B_q, and reports the scan: go -> ik_done cycles and delivered B/cycle against the stack's share of the priced
// bandwidth (3,166.7 B/cycle a die / 4 stacks) plus the measured first access (104).
// MUT=1 (issuer: B_q from the previous quarter) must FAIL at QSEL > 0.
module tb_hgi_idx_iks;
parameter integer MUT = 0, QSEL = 0, MISALIGN = 0;   // MISALIGN: low base bits set -> the issuer must fault, issue nothing
reg clk=0,rst_n=0;always #416 clk=~clk;
integer N = 9000, LAT = 104, ADV = 0, ROW0 = 4006;
reg go=0; wire [511:0] e_all; wire [35:0] blocks; wire ifault;
ot_hgi_idx_iks_issue #(.MUT(MUT)) iss(.clk(clk),.rst_n(rst_n),.go(go),.n(N),.ik_base(40'(ROW0) << 20 | 40'(MISALIGN)),.tag(13'h0abc),.no_credit(1'b0),
  .e_d(e_all),.blocks(blocks),.fault(ifault));
wire [127:0] ed = e_all[QSEL*128 +: 128];
wire[31:0]kv,rrdy,kwe;wire[959:0]addr;wire[127:0]len;wire[543:0]tag;
wire[8791:0]lines;wire done,fault;reg[7:0]credit=0;
reg[31:0]respv=0;reg[127:0]respb=0;reg[543:0]respt=0;reg[8191:0]respd=0;
ot_hbm_svc_core_native #(.NATIVE(1),.NATIVE_CHAIN(0),.IKS(1),.E_ST(2),.XST(0))dut(.ck(clk),.rst(rst_n),.q_d(336'd0),.q_v(8'd0),.q_fclk(8'd0),.q_rdy(),.line(),.fclk(),
.e_d(ed),.e_fclk(clk),.kv(),.ik(),.phy_clk(),.phy_rst_n(),.k_v(kv),.k_rdy(32'hffffffff),.k_addr(addr),.k_len(len),.k_tag(tag),.k_we(kwe),.k_wdata(),.k_wstrb(),
.kr_v(respv),.kr_rdy(rrdy),.kr_tag(respt),.kr_beat(respb),.kr_data(respd),.w_v(),.w_rdy(1'b0),.w_addr(),.w_len(),.w_tag(),.w_room(8'd0),.wr_v(8'd0),.wr_rdy(),.wr_tag(80'd0),.wr_beat(40'd0),.wr_data(2048'd0),
.wq_d(292'd0),.wq_fclk(1'b0),.wq_g(),.k_wr_done(32'd0),.wq_source(2'd0),.wq_source_g(),.wq_source_fault(),.wq_source_busy(),.wq_pending(),
.kvs(),.kvs_done(),.ik_credit(credit),.ik_lines(lines),.ik_done(done),.ik_fault(fault),
.outer_write_pending(1'b0),.native_v(1'b0),.native_rdy(),.native_pc(5'd0),.native_addr(30'd0),.native_tag(16'h0),.native_len(4'd1),
.native_rsp_v(),.native_rsp_rdy(1'b1),.native_rsp_pc(),.native_rsp_tag(),.native_rsp_beat(),.native_rsp_data(),.native_fault());
reg[16:0]qt[0:31][0:255];reg[3:0]qb[0:31][0:255];reg[29:0]qa[0:31][0:255];integer qr[0:31][0:255];
integer head[0:31],tail[0:31],count[0:31];integer p,b,cyc=0;
function automatic[29:0] kaddr(input integer pc,j);
 integer row,bank,col,bhi,blo,hi5;
 begin row=ROW0+(j>>10);bank=(((j>>7)&7)<<2)|(j&3);col=(j>>2)&31;bhi=(bank>>2)^((row>>2)&7);blo=(bank&3)^(row&3);hi5=((row&3)<<3)|bhi;
 kaddr=30'((row<<15)|(bhi<<12)|(col<<7)|(((pc^col^hi5)&31)<<2)|blo);end
endfunction
function automatic[255:0]pat(input[29:0]a);integer i;begin for(i=0;i<8;i=i+1)pat[i*32+:32]=(a*8+i)*32'h9E3779B1^32'h5bd1e995;end endfunction
longint beats=0;
always @(posedge clk)begin
 respv<=0;cyc<=cyc+1;
 if(rst_n)for(p=0;p<32;p=p+1)begin
  if(count[p]>0&&rrdy[p]&&qr[p][head[p]]<=cyc&&(!ADV||((cyc+p)%5!=0)))begin
   respv[p]<=1;respt[p*17+:17]<=qt[p][head[p]];respb[p*4+:4]<=qb[p][head[p]];respd[p*256+:256]<=pat(qa[p][head[p]]);
   head[p]=(head[p]+1)%256;count[p]=count[p]-1;beats=beats+1;
  end
  if(kv[p])begin
   if(kwe[p])$fatal(1,"FATAL: write request on the key stream");
   for(b=0;b<len[p*4+:4];b=b+1)begin qt[p][tail[p]]=tag[p*17+:17];qb[p][tail[p]]=b;qa[p][tail[p]]=addr[p*30+:30]+b;qr[p][tail[p]]=cyc+LAT;tail[p]=(tail[p]+1)%256;count[p]=count[p]+1;end
   if(count[p]>64)$fatal(1,"FATAL: controller overflow");
  end
 end
end
integer got=0,l,i,g,pc,j,off,t=0,t0,bad=0,nb_q,expect_lines;reg[255:0]ex;reg[7:0]pend=0;reg fin=0;
initial begin
 void'($value$plusargs("N=%d",N)); void'($value$plusargs("LAT=%d",LAT)); void'($value$plusargs("ADV=%d",ADV));
 for(p=0;p<32;p=p+1)begin head[p]=0;tail[p]=0;count[p]=0;end
 repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);
 // the bench's own quarter split (independent of the issuer): nb = ceil(N / 8), quarter q owns [342 q, 342 q + 342)
 nb_q = (N + 7) / 8 - 342 * QSEL; if (nb_q < 0) nb_q = 0; if (nb_q > 342) nb_q = 342; expect_lines = 4 * nb_q;
 @(negedge clk); go=1; t0=cyc; @(negedge clk); go=0;
 while(!fin)begin
  @(negedge clk);credit=0;
  for(l=0;l<8;l=l+1)if(lines[l*1099])begin
   if(lines[l*1099+1+:10]!==10'(got+l))begin if(bad<4)$display("MISMATCH tag line %0d",got+l);bad=bad+1;end
   for(i=0;i<136;i=i+1)begin
    g=(got+l)*136+i;pc=(g/32)%32;j=g/1024;off=g%32;ex=pat(kaddr(pc,j));
    if(lines[l*1099+11+i*8+:8]!==ex[off*8+:8])begin if(bad<4)$display("MISMATCH data line=%0d byte=%0d",got+l,i);bad=bad+1;end
   end
   pend[l]=1;
  end
  for(l=0;l<8;l=l+1)if(lines[l*1099])got=got+1;
  if(!ADV||t%23==0)begin credit=pend;pend=0;end
  if(fault)begin $display("svc fault got=%0d",got);bad=bad+1;fin=1;end
  if(done)fin=1;
  if(ifault)begin $display("issuer fault: misaligned key-region base");bad=bad+1;fin=1;end
  t=t+1;if(t>200000)begin $display("timeout got=%0d",got);bad=bad+1;fin=1;end
 end
 if(got!=expect_lines)begin $display("MISMATCH line count %0d expected %0d (issued B %0d)",got,expect_lines,blocks[QSEL*9+:9]);bad=bad+1;end
 $display("IKS quarter %0d: B %0d blocks, %0d lines, %0d bytes, go->ik_done %0d cycles, %0d DRAM beats, %.1f B/cycle (priced %.1f B/cycle a stack, scan priced %.1f cycles)",
   QSEL,nb_q,got,got*136,cyc-t0,beats,(got*136.0)/(cyc-t0),3166.7/4,104+(nb_q*544.0)/(3166.7/4));
 if(bad==0)$display("PASS HGI_IDX_IKS");else $display("HGI_IDX_IKS FAIL %0d",bad);
 $finish;
end
endmodule
