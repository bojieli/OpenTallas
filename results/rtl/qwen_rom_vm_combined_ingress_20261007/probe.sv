`timescale 1ns/1ps
module tb_qwen_vm_combined_ingress;
import ot_gpu_w6_secded_pkg::*;
localparam NR=2256,NW=865,VX0=208,NVX=2048,RED=848;
reg clk=0,rst_n=0;always #5 clk=~clk;
reg[NR-1:0]re=0;reg[NR*24-1:0]ra=0;wire[NR*32-1:0]rq;
reg[NW-1:0]we=0;reg[NW*24-1:0]wa=0;reg[NW*32-1:0]wd=0;
reg me_wanted=0,armed=0;reg[NR-1:0]zero_intent=0;reg use_normalizer=0;reg collar_hold=0;integer hold_step=0;
wire tick,lease,drained,fault,native_clk;
wire[63:0]epoch,reads,writes,acks,held;
integer negative=0,rawacks=0,native_edges=0,physical_edge=0;
integer read_start=-1,write_start=-1,read9=0,write28=0;
reg[31:0]fixture[0:4095];reg[NR*24-1:0]capture_addr[0:0];reg[NR-1:0]capture_en[0:0];
reg[1023:0]fixture_path,addresses_path,enables_path;
wire unpaid_shortcut=(negative==2 && armed && (|dut.g_bound.u_bank.raw_ack)) || (negative==3 && armed && (|dut.wr_accept));
ot_hdc_cg gate(.clk(clk),.en(!rst_n||tick||unpaid_shortcut),.gclk(native_clk));
ot_qwen_rom_vm_ingress_adapter #(.ROM_INGRESS(1),.ENABLE(1),.DIRECT_READBACK(1),.HEAD_CACHE(0),.W1_FRAME(0),.NR(NR),.NW(NW),.VX0(VX0),.NVX(NVX))dut(
.clk(clk),.rst_n(rst_n),.source_me_wanted(me_wanted),.head_source_producer_go(1'b0),.raw_read_en(use_normalizer?norm_ren:re),.raw_read_zero(use_normalizer?norm_zero:zero_intent),.read_addr(use_normalizer?norm_ra24:ra),.read_q(rq),.raw_write_en(use_normalizer?norm_wen:we),.write_addr(use_normalizer?norm_wa24:wa),.write_data(use_normalizer?norm_wdata:wd),.native_tick(tick),.native_me_lease(lease),.drained(drained),.fault(fault),.native_epoch(epoch),.physical_reads(reads),.physical_writes(writes),.physical_ACKs(acks),.held_edges(held),.head_fill_reads(),.head_hit_edges());

reg[2239:0]norm_scalar_re=0;reg[2240*24-1:0]norm_scalar_addr=0;
reg norm_seq_re=0;reg[23:0]norm_seq_word=0;
reg[48:0]norm_word_we=0;reg[49*24-1:0]norm_word_addr=0;reg[49*16-1:0]norm_word_mask=0;
wire[2255:0]norm_ren,norm_zero,norm_publish;wire[2256*32-1:0]norm_ra32;
wire[864:0]norm_wen;wire[865*32-1:0]norm_wa32,norm_wdata;
reg[2256*24-1:0]norm_ra24;reg[865*24-1:0]norm_wa24;
ot_qwen_rom_vm_request_normalizer #(.ENABLE(1),.VWA(24))norm(
.me_wanted(1'b1),.scalar_re(norm_scalar_re),.scalar_raddr(norm_scalar_addr),.seq_re(norm_seq_re),.seq_rword(norm_seq_word),
.word_we(norm_word_we),.word_waddr(norm_word_addr),.word_wmask(norm_word_mask),.scalar_we(65'd0),.scalar_waddr(1560'd0),
.seq_we(1'b0),.seq_wword(24'd0),.ordered_write_data({865{32'hfeedface}}),
.read_publish_en(norm_publish),.read_en(norm_ren),.read_zero(norm_zero),.read_addr(norm_ra32),.write_en(norm_wen),.write_addr(norm_wa32),.write_data(norm_wdata),
.backend_read_data({2256{32'hdeadbeef}}),.publish_read_data());
// Bench-only stateless width-pack boundary; exact original slices, not engine RTL.
always @* begin
 for(integer pi=0;pi<2256;pi=pi+1)norm_ra24[pi*24+:24]=norm_ra32[pi*32+:24];
 for(integer pi=0;pi<865;pi=pi+1)norm_wa24[pi*24+:24]=norm_wa32[pi*32+:24];
end
always @(negedge clk)begin
 for(integer pi=0;pi<2256;pi=pi+1)if(norm_ra24[pi*24+:24]!==norm_ra32[pi*32+:24])$fatal(1,"read width-pack4state mismatch");
 for(integer pi=0;pi<865;pi=pi+1)if(norm_wa24[pi*24+:24]!==norm_wa32[pi*32+:24])$fatal(1,"write width-pack4state mismatch");
end
// Change live raw packet and original intent only after existing CAP owns it.
always @(negedge clk)if(collar_hold && dut.state!=0)begin
 if(hold_step==0)begin me_wanted=0;we=0;wa=0;wd=0;end
 if(hold_step<4)begin
  if(dut.wen[560+:16]!==16'hffff || dut.wdata[560*32+:32]!==32'hc011a035 || dut.waddr[560*24+:24]!==24'd16192)$fatal(1,"CAP packet changed with live intent/payload");
 end
 if(hold_step==3)begin me_wanted=1;collar_hold=0;end
 hold_step=hold_step+1;
end

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
integer count,before_native,before_raw;reg expected_write;reg[63:0]before_epoch,before_reads,before_acks;
begin
 #1;expected_write=|dut.write_en;
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
 if(expected_write&&acks==before_acks)$fatal(1,"writer admitted without checked ACK");
 if(kind==1 && (reads-before_reads!=1024 || acks-before_acks!=1 || rawacks-before_raw!=1))$fatal(1,"captured overlap service counts wrong");
 $display("FRAME kind=%0d physical_edges=%0d read_delta=%0d checked_ACK_delta=%0d native=%0d",kind,count,reads-before_reads,acks-before_acks,native_edges);
 $fflush();
 @(negedge clk);re=0;we=0;zero_intent=0;use_normalizer=0;
end
endtask
initial begin
$display("PROBE start t=%0t",$time);$fflush();
#1;$display("PROBE settled t=%0t",$time);$fflush();
#30;rst_n=1;
#50;$display("PASS PROBE reset and empty clocks t=%0t epoch=%0d",$time,epoch);$fflush();$finish;
end
endmodule
