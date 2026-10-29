`timescale 1ns/1ps
module tb_replica;
parameter MUT=0;
reg clk=0;always #5 clk=~clk;reg rst_n=0,arm=0;reg[288:0]cfg=0;
reg[2247:0]coll=0,su=0;reg[31:0]legacy=0;
wire[9023:0]replicas;wire[31:0]collision;wire pending,fault;
ot_vms_idx_query_replica_n1 #(.MUT(MUT)) replicator(.clk_source(clk),.clk_destination({32{clk}}),.rst_n(rst_n),.arm(arm),.native_cfg(cfg),.canonical_coll_kq(coll),.canonical_su_wq(su),.destination_write_valid(legacy),.replica_wq(replicas),.collision(collision),.pending(pending),.fault(fault));
wire[281:0]wq=replicas[0+:282];reg[17:0]rq=0;wire[256:0]rr;wire done;wire[17:0]status;
wire rv=1'b1,wv=1'b1;wire[2:0]rs=0,ws=1;
hfd_vms_bank_native_q0_faces_r2048_oneclk #() newer(.clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),.rslot_v(rv),.rslot(rs),.wslot_v(wv),.wslot(ws),.rq0(rq),.rr0(rr),.rq1(18'd0),.rr1(),.rq2(18'd0),.rr2(),.rq3(18'd0),.rr3(),.rq4(18'd0),.rr4(),.wq0(282'd0),.wq_done0(),.wq1(wq),.wq_done1(done),.dq(282'd0),.dq_done(),.kq(282'd0),.kq_done(),.xq(277'd0),.xq_done(),.xq2(277'd0),.xq2_done(),.eg(),.pq(286'd0),.pr(),.status(status));

integer cyc=0,checks=0,issues=0;reg[9023:0]expected=0,next_expected=0;reg check_fault=1;
reg[255:0]model[0:63];reg[255:0]payload;reg[7:0]mask;integer off,bank,r,ds,ix,j;reg[16:0]target;reg[9023:0]current;
function automatic[255:0]bits(input integer i,input integer provider);
 for(integer k=0;k<8;k=k+1)bits[k*32+:32]=32'h3f000000+32'(i*8+k+provider*65536);
endfunction
task tick;begin
 @(posedge clk);#1;
 for(integer d=0;d<32;d=d+1)begin
 if(replicas[d*282+281]!==expected[d*282+281])$fatal(1,"replica valid/date cycle%0d dest%0d",cyc,d);
 if(expected[d*282+281] && replicas[d*282+:282]!==expected[d*282+:282])$fatal(1,"replica payload/sector/mask cycle%0d dest%0d",cyc,d);
 end
 if(check_fault && fault)$fatal(1,"unexpected source fault");
 expected=next_expected;next_expected=0;cyc=cyc+1;checks=checks+1;
end endtask
task send(input integer offset,provider,input[7:0]wm);
 begin
  @(negedge clk);coll=0;su=0;bank=(6+offset)%8;payload=bits(offset,provider);
  if(provider==0)coll[bank*281+:281]={1'b1,16'(18438+offset),payload,wm};
  else su[bank*281+:281]={1'b1,16'(18438+offset),payload,wm};
  current=0;
  for(r=0;r<4;r=r+1)if(r!=2)begin target=cfg[r*68+17+:17]+17'(offset);ds=r*8+32'(target[2:0]);current[ds*282+:282]={1'b1,target,payload,wm};end
  next_expected=current;
  // Packet issued at this source sampling edge appears after destination
  // capture on the following edge; actual bank samples one edge after that.
  tick();issues=issues+1;
  if(offset%8==0)for(j=0;j<8;j=j+1)if(wm[j])model[offset/8][j*32+:32]=payload[j*32+:32];
 end
endtask
initial begin
 for(ix=0;ix<64;ix=ix+1)model[ix]=0;
 cfg[17+:17]=17'h8000;cfg[68+17+:17]=17'h2200;cfg[136+17+:17]=17'd18438;cfg[204+17+:17]=17'h6200;cfg[276:272]=1;
 repeat(6)tick();@(negedge clk);rst_n=1;repeat(14)tick();@(negedge clk);arm=1;repeat(2)tick();
 for(off=0;off<512;off=off+1)send(off,0,8'hff);
 for(off=0;off<512;off=off+1)if(off%16>=8)send(off,1,8'h5a);
 @(negedge clk);coll=0;su=0;repeat(12)tick();
 for(ix=0;ix<64;ix=ix+1)begin
  @(negedge clk);rq={1'b1,17'(32768+ix*8)};tick();@(negedge clk);rq=0;repeat(7)tick();
  if(!rr[256] || rr[255:0]!==model[ix])$fatal(1,"replica realSRAM readback row%0d",ix);repeat(2)tick();
 end
 if(status!=0)$fatal(1,"replica bank status");
 // A future colliding owner is checked at the actual replica bank sampling
 // phase, not at the earlier canonical write edge.
 check_fault=0;send(0,1,8'hff);@(negedge clk);coll=0;su=0;legacy[0]=1;
 @(posedge clk);#1;if(!collision[0] || replicas[281])$fatal(1,"late destination collision failedopen");
 repeat(3)@(posedge clk);#1;if(!fault)$fatal(1,"collision fault absent");
 $display("QUERY_REPLICA_N1 PASS inputprovider2 querysectors512 sparseSU256 realhighSRAMrows64 issues%0d checks%0d source_to_bank_extra2 collisiondated",issues,checks);$finish;
end
endmodule
