`timescale 1ns/1ps
module tb_cache_tail;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,open_v=0,open_bank=0,read_v=0,read_bank=0,retire_v=0,retire_bank=0;
 reg[15:0]open_epoch=0,read_epoch=0,retire_epoch=0;
 reg[6:0]open_count=0;reg[9:0]open_tag_base=0,read_tag=0;reg[5:0]read_row=0;
 reg[3:0]sector_v=0;reg[95:0]sector_index=0;reg[63:0]sector_epoch=0;reg[1023:0]sector_data=0;
 wire[1:0]block_ready,bank_owned;wire busy,fault;wire[1098:0]out_packet;
 ot_hbm_svc_static_sm_packed136 #(.PACKED136(1)) dut(.*);
 integer cycle=0,checks=0,tail_edges=0;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(rst_n&&open_v)$display("OPEN c=%0d bank=%0d epoch=%0d count=%0d ok=%0d running=%0d emitted=%0d rows=%0d received=%0d total=%0d",cycle,open_bank,open_epoch,open_count,dut.g_on.open_ok,busy,dut.g_on.emitted,dut.g_on.load_rows,dut.g_on.received,dut.g_on.total_sectors);
  if(rst_n&&read_v&&!dut.g_on.read_ok)$display("READ_REJECT c=%0d bank=%0d ready=%b epoch=%0d expected=%0d row=%0d count=%0d tag=%0d expected_tag=%0d",cycle,read_bank,block_ready,read_epoch,dut.g_on.epoch[read_bank],read_row,dut.g_on.count[read_bank],read_tag,dut.g_on.tags[{read_bank,read_row}]);
  if(rst_n&&retire_v)$display("RETIRE c=%0d bank=%0d epoch=%0d expected=%0d owned=%b running=%0d",cycle,retire_bank,retire_epoch,dut.g_on.epoch[retire_bank],bank_owned,busy);
 end
 task tick;begin @(posedge clk);#1;end endtask
 function automatic[7:0]byte_for(input integer b,input integer r,input integer j);byte_for=(b*113+r*37+j*13+(j>>3)*17)^8'hb5;endfunction
 task open_block(input bit b,input integer n);begin
  open_bank=b;open_epoch=16'd70+b;open_count=n;open_tag_base=b?300:100;open_v=1;tick;open_v=0;
 end endtask
 task sectors(input bit b,input integer rows);integer o,p,n,t,j,k,off;begin
  o=0;p=0;t=((rows*136+127)/128)*4;
  while(o<t)begin
   n=p==4?1:4;if(t-o<n)n=t-o;
   sector_v=0;sector_index=0;sector_epoch=0;sector_data=0;
   for(j=0;j<n;j=j+1)begin
    sector_v[j]=1;sector_index[j*24+:24]=o+j;sector_epoch[j*16+:16]=70+b;
    for(k=0;k<32;k=k+1)begin off=(o+j)*32+k;sector_data[j*256+k*8+:8]=off<rows*136?byte_for(b,off/136,off%136):0;end
   end
   tick;if(fault)$fatal(1,"SOURCE_REJECT cycle=%0d",cycle);
   o=o+n;p=p==4?0:p+1;
  end
  sector_v=0;
  $display("LAST_SECTOR c=%0d rows=%0d busy=%0d emitted=%0d received=%0d",cycle,rows,busy,dut.g_on.emitted,dut.g_on.received);
 end endtask
 task read_all(input bit b,input integer rows);integer r,j;reg[1087:0]expected;begin
  if(!block_ready[b])$fatal(1,"notready");
  for(r=0;r<rows;r=r+1)begin
   read_v=1;read_bank=b;read_epoch=(MUT==2)?999:70+b;read_row=r;read_tag=(b?300:100)+r;
   tick;if(fault)$fatal(1,"READ_REJECT sticky");
   for(j=0;j<136;j=j+1)expected[j*8+:8]=byte_for(b,r,j);
   if(out_packet!=={1'b1,read_tag,expected})$fatal(1,"PAYLOAD_TAG_MISMATCH");checks=checks+1;
  end
  read_v=0;tick;
  retire_v=1;retire_bank=b;retire_epoch=(MUT==3)?999:70+b;tick;retire_v=0;
  if(fault)$fatal(1,"RETIRE_REJECT sticky");
 end endtask
 integer c,rows,guard;
 initial begin
  for(c=0;c<4;c=c+1)begin
   rows=c==0?64:c==1?60:c==2?16:1;
   rst_n=0;open_v=0;sector_v=0;read_v=0;retire_v=0;tick;tick;rst_n=1;tick;
   open_block(0,rows);sectors(0,rows);
   // A producer drain interlock alone releases here. The packed-row assembler
   // still has completion work; this is the exact 80-sector-edge/64-row case.
   guard=0;
   if(MUT!=1)while(busy)begin tick;guard=guard+1;if(guard>3)$fatal(1,"tail unbounded");end
   tail_edges=tail_edges+guard;
   open_block(1,rows);
   if(fault)$fatal(1,"OPEN_REJECT running tail (baseline causal witness)");
   sectors(1,rows);while(busy)tick;
   read_all(0,rows);read_all(1,rows);
  end
  $display("CACHE_TAIL_PASS reads=%0d tail_edges=%0d cases=4",checks,tail_edges);$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
