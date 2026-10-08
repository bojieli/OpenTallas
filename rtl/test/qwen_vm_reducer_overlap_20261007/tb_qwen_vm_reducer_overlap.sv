`timescale 1ns/1ps
module tb_qwen_vm_reducer_overlap;
localparam NR=2256,NW=865,VX0=208,NVX=2048,RED=848;
reg clk=0,rst_n=0;always #5 clk=~clk;
reg[NR-1:0]re=0;reg[NR*24-1:0]ra=0;wire[NR*32-1:0]rq;
reg[NW-1:0]we=0;reg[NW*24-1:0]wa=0;reg[NW*32-1:0]wd=0;
reg me_wanted=0,armed=0;
wire tick,lease,drained,fault,native_clk;
wire[63:0]epoch,reads,writes,acks,held;
integer negative=0,rawacks=0,native_edges=0,physical_edge=0;
integer read_start=-1,write_start=-1,read9=0,write28=0;
reg[31:0]fixture[0:4095];reg[NR*24-1:0]capture_addr[0:0];reg[NR-1:0]capture_en[0:0];
reg[1023:0]fixture_path,addresses_path,enables_path;
wire unpaid_shortcut=(negative==2 && armed && (|dut.g_bound.u_bank.raw_ack)) || (negative==3 && armed && (|dut.wr_accept));
ot_hdc_cg gate(.clk(clk),.en(!rst_n||tick||unpaid_shortcut),.gclk(native_clk));
ot_qwen_finite_vm_adapter_direct_readback #(.ENABLE(1),.DIRECT_READBACK(1),.HEAD_CACHE(0),.W1_FRAME(0),.NR(NR),.NW(NW),.VX0(VX0),.NVX(NVX))dut(
.clk(clk),.rst_n(rst_n),.source_me_wanted(me_wanted),.head_source_producer_go(1'b0),.read_en(re),.read_addr(ra),.read_q(rq),.write_en(we),.write_addr(wa),.write_data(wd),.native_tick(tick),.native_me_lease(lease),.drained(drained),.fault(fault),.native_epoch(epoch),.physical_reads(reads),.physical_writes(writes),.physical_ACKs(acks),.held_edges(held),.head_fill_reads(),.head_hit_edges());
always @(posedge native_clk)if(rst_n)native_edges<=native_edges+1;
always @(posedge clk)begin
physical_edge=physical_edge+1;
if(rst_n)begin
 if(|dut.g_bound.u_bank.raw_ack)rawacks=rawacks+1;
 if(dut.rd_accept)read_start=physical_edge;
 if(|dut.wr_accept)write_start=physical_edge;
 if(dut.rd_valid)begin
  if($isunknown(dut.rd_words))$fatal(1,"unknown checked read payload");
  if(physical_edge-read_start!=9)$fatal(1,"read9 changed");read9=read9+1;
 end
 if(|dut.wr_ACK)begin
  if($isunknown(dut.g_bound.u_bank.decoded[dut.g_bound.u_bank.bank*512+:512]))$fatal(1,"unknown postverify ACK");
  if(physical_edge-write_start!=28)$fatal(1,"write28 changed");write28=write28+1;
 end
 if(tick&&dut.pack_valid)$fatal(1,"native tick with unpaid pack");
end
end
// Existing finite source-walk/service upper bound; no wall/build timeout.
localparam FRAME_BOUND=2+NR*14+NW*33+32;
task automatic frame(input integer kind);
integer count,before_native,before_raw;reg[63:0]before_epoch,before_reads,before_acks;
begin
 before_native=native_edges;before_epoch=epoch;before_reads=reads;before_acks=acks;before_raw=rawacks;count=0;
 do begin
  @(posedge clk);#1;count=count+1;
  if(fault)begin
   if(negative==1 && armed && !tick && !lease && native_edges==before_native)$fatal(1,"FOREIGN_REDUCER_ACK_REJECTED");
   $fatal(1,"unexpected physical frame fault");
  end
  if(epoch==before_epoch && native_edges!=before_native)$fatal(1,"UNPAID_NATIVE_ADVANCE");
  if(count>FRAME_BOUND)$fatal(1,"source-derived frame deadlock bound");
 end while(epoch==before_epoch);
 if(native_edges!=before_native+1 || !drained)$fatal(1,"native admission/drain mismatch");
 if((|we)&&acks==before_acks)$fatal(1,"writer admitted without checked ACK");
 if(kind==1 && (reads-before_reads!=1024 || acks-before_acks!=1 || rawacks-before_raw!=1))$fatal(1,"captured overlap service counts wrong");
 $display("FRAME kind=%0d physical_edges=%0d read_delta=%0d checked_ACK_delta=%0d native=%0d",kind,count,reads-before_reads,acks-before_acks,native_edges);
 @(negedge clk);re=0;we=0;
end
endtask
integer base,j,n,addr;
initial begin
 if(!$value$plusargs("FIXTURE=%s",fixture_path)||!$value$plusargs("ADDRESSES=%s",addresses_path)||!$value$plusargs("ENABLES=%s",enables_path))$fatal(1,"source fixtures required");
 if($value$plusargs("NEGATIVE=%d",negative))begin end
 $readmemh(fixture_path,fixture);$readmemh(addresses_path,capture_addr);$readmemh(enables_path,capture_en);
 if($isunknown(fixture[0])||$isunknown(fixture[4095])||$isunknown(capture_addr[0])||$isunknown(capture_en[0]))$fatal(1,"fixture unknown");
 repeat(3)@(negedge clk);rst_n=1;
 // Physical source-owned initialization: opaque authorized HEAD initial words.
 for(base=0;base<4096;base=base+NW)begin
  n=(4096-base>NW)?NW:4096-base;we=0;
  for(j=0;j<n;j=j+1)begin we[j]=1;wa[j*24+:24]=4096+base+j;wd[j*32+:32]=fixture[base+j];end
  frame(0);
 end
 // Establish real checked initial contents of the reducer word as well.
 for(j=0;j<16;j=j+1)begin we[j]=1;wa[j*24+:24]=16160+j;wd[j*32+:32]=fixture[j];end
 frame(0);
 // Immutable actual parent160: all2048 VX reads plus one delayed reducer write.
 ra=capture_addr[0];re=capture_en[0];we=0;we[RED]=1;wa[RED*24+:24]=16160;wd[RED*32+:32]=fixture[3];me_wanted=1;armed=1;
 frame(1);armed=0;
 // Real XVM1 holds returned VX until the next admitted ME event.
 @(posedge clk);#1;
 for(j=0;j<NVX;j=j+1)begin
  addr=capture_addr[0][(VX0+j)*24+:24];
  if(rq[(VX0+j)*32+:32]!==fixture[addr-4096])$fatal(1,"VX source-seat returned wrong data seat=%0d addr=%0d",j,addr);
 end
 @(negedge clk);me_wanted=0;re=3;ra[0+:24]=16160;ra[24+:24]=16161;frame(2);
 if(rq[0+:32]!==fixture[3] || rq[32+:32]!==fixture[1])$fatal(1,"reducer publication or untouched neighbor wrong");
 $display("PASS full_aperture_parent160 VX2048 delayed_reducer checked_ACK native_hold XVM1 read9=%0d write28=%0d rawACKs=%0d native=%0d held=%0d",read9,write28,rawacks,native_edges,held);
 $finish;
end
initial begin
 wait(armed);
 if(negative==1)begin wait(|dut.wr_ACK);force dut.wr_ACK_owner=908'h1;end
end
endmodule
