`timescale 1ns/1ps
module tb_hbm_attn_pv_serializer_local_banked;
 reg clk=0;always #2 clk=~clk;reg rst_n=0;
 reg cv=0,ce=0,dv=0,de=0;reg[3:0]cd=0,dh=0;reg[2:0]db=0;reg[15:0]base=0;
 reg[16383:0]data=0;reg[511:0]flags=0;
 wire wv,fault;wire[2047:0]out;wire[63:0]of;wire[15:0]sector;
 ot_hbm_attn_pv_serializer_local_banked dut(.clk(clk),.bank_clk({4{clk}}),.rst_n(rst_n),.capture_v(cv),.capture_epoch(ce),.capture_dim(cd),.capture_data(data),.capture_flags(flags),
 .drain_v(dv),.drain_epoch(de),.drain_head(dh),.drain_block(db),.drain_base_sector(base),
 .write_v(wv),.write_data(out),.write_flags(of),.write_base_sector(sector),.fault(fault));
 function automatic[31:0]word_(input integer seq,h,dim);word_=32'h9e3779b9^32'(seq*99991+h*777+dim*37037);endfunction
 function automatic flag_(input integer seq,h,dim);flag_=((seq*7+h*11+dim*13)%17)==3;endfunction
 integer seq=0,mut=0,overlap=0,c,t,h,k,d,checked=0;reg active=0;
 integer seq_q[0:2];reg[3:0]head_q[0:2];reg[2:0]block_q[0:2];
 always @(posedge clk)begin
  for(integer a=2;a>0;a--)begin seq_q[a]=seq_q[a-1];head_q[a]=head_q[a-1];block_q[a]=block_q[a-1];end
  seq_q[0]=seq;head_q[0]=dh;block_q[0]=db;
  #1;
  if(active&&fault)$fatal(1,"PV_LOCAL_SERIALIZER phase fault");
  if(active&&wv)begin
   if(sector!==16'(seq_q[2]*2048+int'(head_q[2])*64+int'(block_q[2])*8))$fatal(1,"PV_LOCAL_SERIALIZER sector mismatch");
   for(integer j=0;j<64;j=j+1)begin
    if(out[j*32+:32]!==word_(seq_q[2],int'(head_q[2]),int'(block_q[2])*64+j))$fatal(1,"PV_LOCAL_SERIALIZER data mismatch seq%0d h%0d block%0d word%0d",seq,dh,db,j);
    if(of[j]!==flag_(seq_q[2],int'(head_q[2]),int'(block_q[2])*64+j))$fatal(1,"PV_LOCAL_SERIALIZER flag mismatch");
    checked++;
   end
  end
 end
 initial begin
  void'($value$plusargs("MUT=%d",mut));void'($value$plusargs("OVERLAP=%d",overlap));repeat(5)@(negedge clk);rst_n=1;active=1;
  for(seq=0;seq<3;seq=seq+1)begin
   if(!overlap||seq==0)for(c=0;c<16;c=c+1)begin
    @(negedge clk);cv=1;ce=1'(seq%2);cd=4'(c);data=0;flags=0;
    for(t=0;t<32;t=t+1)for(h=0;h<16;h=h+1)begin
     data[(t*16+h)*32+:32]=word_(seq,h,t*16+c);flags[t*16+h]=flag_(seq,h,t*16+c);
    end
    if(mut==1&&seq==0&&c==0)data[0]=~data[0];
    if(mut==3&&seq==0&&c==0)flags[0]=~flags[0];
    if(mut==2&&seq==0&&c==14)begin dv=1;de=0;dh=0;db=0;base=0;end
   end
   @(negedge clk);cv=0;dv=0;repeat(2)@(negedge clk);
   for(h=0;h<16;h=h+1)for(k=0;k<8;k=k+1)begin
    @(negedge clk);dv=1;de=1'(seq%2);dh=4'(h);db=3'(k);base=16'(seq*2048);
    if(overlap)begin
     cv=(seq<2&&h*8+k<16);ce=1'((seq+1)%2);cd=4'(h*8+k);
     if(cv)for(t=0;t<32;t=t+1)for(integer hh=0;hh<16;hh=hh+1)begin
      data[(t*16+hh)*32+:32]=word_(seq+1,hh,t*16+h*8+k);
      flags[t*16+hh]=flag_(seq+1,hh,t*16+h*8+k);
     end
    end
   end
   @(negedge clk);dv=0;repeat(3)@(negedge clk);
  end
  if(checked!=24576)$fatal(1,"PV_LOCAL_SERIALIZER accounting%0d",checked);
  $display("PASS PV_LOCAL_SERIALIZER actual_H16_D512 records3 words24576 flags24576 readbeats384 actual_SRAM2048 epochs2 overlap%0d",overlap);$finish;
 end
endmodule
