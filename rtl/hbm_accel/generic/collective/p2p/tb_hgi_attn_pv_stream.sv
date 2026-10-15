`timescale 1ns/1ps
`default_nettype none
// Literal compiler programme only. Golden values enter solely at the observed
// final boundary; no replacement arithmetic, memory, or scheduler exists here.
module tb_hgi_attn_pv_stream;
 import ot_hgi_attn_pv_pkg::*;
 import ot_hgi_attn_pv_stream_pkg::*;
 parameter integer MUT_CARRY=0,MUT_BANK=0;
 localparam integer MAX_CYCLES=128*82+165;
 reg clk=0,rst_n=0;
 always #0.5 clk=~clk;
 ring_cmd_t cmd[0:3],commands[0:3][0:MAX_CYCLES-1];
 ring_cmd_t ring_words[0:MAX_CYCLES-1];
 stream_cmd_t lc,local_words[0:MAX_CYCLES-1];
 reg [255:0] boundary[0:3],inputs[0:3][0:MAX_CYCLES-1];
 reg [255:0] input_words[0:MAX_CYCLES-1],expected[0:MAX_CYCLES-1];
 reg [31:0] meta[0:1];
 reg [4:0] land_words[0:MAX_CYCLES-1],landing;
 reg [1:0] destinations[0:MAX_CYCLES-1],destination;
 reg expected_v[0:MAX_CYCLES-1];
 reg [6:0] expected_batch[0:MAX_CYCLES-1];
 wire final_v,local_fault,scratch_fault;
 wire [255:0] out_data;
 wire [6:0] out_batch;
 wire [1:0] out_destination;
 wire [3:0] ring_fault;
 string programme="";
 integer expect_schedule_fault=0,last,batches;
 integer checked=0,first_output=-1,last_output=-1;
 integer ring_writes=0,local_writes=0,scratch_reads=0;
 integer overlap_read=0,overlap_write=0,overlap_reducer=0;
 ot_hgi_attn_pv_stream #(.MUT_CARRY(MUT_CARRY),.MUT_BANK(MUT_BANK)) dut(
  .clk(clk),.rst_n(rst_n),.cmd(cmd),.boundary_data(boundary),.dest_q(destination),
  .landing_slot(landing),.local_cmd(lc),.final_v(final_v),.out_data(out_data),
  .out_batch(out_batch),.out_destination(out_destination),.ring_fault(ring_fault),
  .local_fault(local_fault),.scratch_fault(scratch_fault));
 initial begin
  if(!$value$plusargs("PROGRAM_DIR=%s",programme))$fatal(1,"PROGRAM_DIR required");
  if($value$plusargs("EXPECT_SCHEDULE_FAULT=%d",expect_schedule_fault))begin end
  $readmemh({programme,"/cycles.hex"},meta);
  last=int'(meta[0]);batches=int'(meta[1]);
  if((batches!=128 && batches!=4)||last<0||last>=MAX_CYCLES)$fatal(1,"unsupported programme shape last%0d batches%0d",last,batches);
  for(integer q=0;q<4;q++)begin
   $readmemh($sformatf("%s/ring%0d.hex",programme,q),ring_words,0,last);
   $readmemh($sformatf("%s/input%0d.hex",programme,q),input_words,0,last);
   for(integer t=0;t<=last;t++)begin commands[q][t]=ring_words[t];inputs[q][t]=input_words[t];end
   cmd[q]='0;boundary[q]=0;
  end
  $readmemh({programme,"/local.hex"},local_words,0,last);
  $readmemh({programme,"/landing.hex"},land_words,0,last);
  $readmemh({programme,"/destination.hex"},destinations,0,last);
  $readmemh({programme,"/expected.hex"},expected,0,last);
  $readmemh({programme,"/expected_v.hex"},expected_v,0,last);
  $readmemh({programme,"/expected_batch.hex"},expected_batch,0,last);
  lc='0;landing=0;destination=0;
  repeat(4)@(negedge clk);
  rst_n=1;
  // One initial reset for all128 batches, all tag and SRAM bank reuses.
  for(integer t=0;t<=last;t++)begin
   for(integer q=0;q<4;q++)begin cmd[q]=commands[q][t];boundary[q]=inputs[q][t];end
   lc=local_words[t];landing=land_words[t];destination=destinations[t];
   #0.01;
   // Observe real writes at the macro face, before the sampling edge.
   if(dut.ring_write)begin
    ring_writes++;
    if(lc.scratch_read_v)begin
     overlap_read++;
     if(landing[4]==lc.scratch_read_slot[4])$fatal(1,"PV_STREAM_BANK_CONFLICT read cycle%0d",t);
    end
    if(lc.capture)begin
     overlap_write++;
     if(landing[4]==lc.capture_slot[4])$fatal(1,"PV_STREAM_BANK_CONFLICT write cycle%0d",t);
    end
    if(lc.load_v||lc.add_read||lc.add_issue||lc.pub_read||lc.pub_issue)overlap_reducer++;
   end
   if(lc.capture)local_writes++;
   if(lc.scratch_read_v)scratch_reads++;
   @(posedge clk);#0.01;
   if((|ring_fault)||local_fault||scratch_fault)begin
    if(expect_schedule_fault!=0 && local_fault && !(|ring_fault) && !scratch_fault)begin
     $display("PV_STREAM_EXPECTED_SCHEDULE_FAULT cycle%0d cause%h",t,dut.reduce_cause);$finish;
    end
    $fatal(1,"PV_STREAM_NATIVE_FAULT cycle%0d ring%h local%b scratch%b cause%h carry%0d bank%0d",t,ring_fault,local_fault,scratch_fault,dut.reduce_cause,MUT_CARRY,MUT_BANK);
   end
   if(final_v!==expected_v[t])$fatal(1,"PV_STREAM_VALID_MISMATCH cycle%0d got%b expected%b",t,final_v,expected_v[t]);
   if(expected_v[t])begin
    if(out_batch!==expected_batch[t] || out_destination!==2'((int'(expected_batch[t])/16)%4))
     $fatal(1,"PV_STREAM_IDENTITY_MISMATCH cycle%0d batch%0d/%0d destination%0d",t,out_batch,expected_batch[t],out_destination);
    if(out_data!==expected[t])$fatal(1,"PV_STREAM_DATA_MISMATCH faults_zero=1 cycle%0d batch%0d got%h expected%h carry%0d bank%0d",t,out_batch,out_data,expected[t],MUT_CARRY,MUT_BANK);
    if(first_output<0)first_output=t;
    last_output=t;checked+=8;
   end
   @(negedge clk);
  end
  if(expect_schedule_fault!=0)$fatal(1,"PV_STREAM schedule fault mutant survived");
  if(checked!=8*batches || ring_writes!=16*batches || local_writes!=14*batches || scratch_reads!=30*batches)
   $fatal(1,"PV_STREAM_COVERAGE checked%0d ring%0d writes%0d reads%0d",checked,ring_writes,local_writes,scratch_reads);
  if(overlap_read==0||overlap_reducer==0)$fatal(1,"PV_STREAM no measured ring/local overlap");
  if(first_output!=165 || last_output!=(batches-1)*82+165)$fatal(1,"PV_STREAM output timeline %0d/%0d",first_output,last_output);
  $display("PV_STREAM_PASS checked%0d batches%0d resets1 first%0d last%0d period82 ring_writes%0d local_writes%0d reads%0d overlap_read%0d overlap_write%0d overlap_reducer%0d SRAM2",checked,batches,first_output,last_output,ring_writes,local_writes,scratch_reads,overlap_read,overlap_write,overlap_reducer);
  $finish;
 end
endmodule
`default_nettype wire
