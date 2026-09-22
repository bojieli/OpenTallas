"""Gather real byte-addressed lines, compare assembled values and traffic."""
from pathlib import Path
import shutil
import subprocess
import pytest
ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('zero_latency', [0, 1])
@pytest.mark.parametrize('slots', [1, 3])
@pytest.mark.parametrize('retain', [0, 1])
def test_gather(tmp_path, slots, zero_latency, retain):
    bench = tmp_path / 'tb.sv'
    bench.write_text(r'''
module tb;
parameter integer SLOTS=3,ZERO=0,RETAIN=1;
localparam SB=SLOTS<2?1:$clog2(SLOTS);
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,coordinate_valid=0,word_ready=0;
reg [31:0] command_generation=3,command_object=17;
reg [63:0] command_object_bytes,coordinate_element_base;
reg [31:0] coordinate_lane_stride,coordinate_index=0;
reg [7:0] coordinate_mask;
reg [SB-1:0] coordinate_slot;
wire command_ready,coordinate_ready,word_valid,read_valid,response_ready,protocol_error,drained;
wire [127:0] word_data;
wire [31:0] word_index,read_object;
wire [63:0] read_tag,read_offset;
wire [4:0] read_bytes;
integer ticks=0,reads=0,bytes_read=0,checks=0;
reg pending=0;reg [63:0] saved_tag,saved_offset;integer delay_count=0;
reg fail_response=0,wrong_response=0,block_read=0;
wire read_ready=!block_read && !pending && ticks%4!=0;
wire response_valid=wrong_response || (ZERO?(read_valid && read_ready):(pending && delay_count==0));
wire [63:0] response_tag=wrong_response?64'hbadbad00:ZERO?read_tag:saved_tag;
wire response_error=fail_response;
wire [63:0] response_offset=ZERO?read_offset:saved_offset;
reg [127:0] response_data;
function automatic [7:0] byte_value(input [63:0] addr);byte_value=8'(addr*17+3);endfunction
always @*begin
 for(integer n=0;n<16;n=n+1)response_data[8*n+:8]=byte_value(response_offset+64'(n));
end
ot_a3_bf16_weight_gather #(.SLOTS(SLOTS),.RETAIN_LINES(RETAIN)) dut(.*);
reg held_read=0,held_word=0;
reg [164:0] saved_read;
reg [159:0] saved_word;
always @(posedge clk)begin
 ticks<=ticks+1;if(ticks>100000)$fatal(1,"timeout");
 if(!rst_n || clear)begin pending<=0;held_read<=0;held_word<=0;end
 else begin
  if(held_read && (!read_valid || saved_read!=={read_tag,read_object,read_offset,read_bytes}))$fatal(1,"read changed while stalled");
  if(held_word && (!word_valid || saved_word!=={word_index,word_data}))$fatal(1,"word changed while stalled");
  held_read<=read_valid && !read_ready;saved_read<={read_tag,read_object,read_offset,read_bytes};
  held_word<=word_valid && !word_ready;saved_word<={word_index,word_data};
  if(read_valid && read_ready)begin
   if(read_object!=command_object || read_tag[63:32]!=command_generation || read_offset%16 || read_bytes==0 || read_bytes>16 || read_offset+64'(read_bytes)>command_object_bytes)$fatal(1,"unbounded read");
   reads<=reads+1;bytes_read<=bytes_read+integer'(read_bytes);
   if(!ZERO)begin pending<=1;saved_tag<=read_tag;saved_offset<=read_offset;delay_count<=3;end
  end
  if(pending && delay_count>0)delay_count<=delay_count-1;
  if(!ZERO && response_valid && response_ready && !wrong_response)pending<=0;
 end
end
task reset_command(input [63:0] capacity);
 begin
  @(negedge clk);clear=1;coordinate_valid=0;word_ready=0;wrong_response=0;fail_response=0;block_read=0;
  @(negedge clk);clear=0;command_generation=command_generation+1;command_object_bytes=capacity;
  #1;if(!command_ready)$fatal(1,"command not ready");command_valid=1;
  @(negedge clk);command_valid=0;
 end
endtask
task submit(input [63:0] base,input [31:0] stride,input [7:0] mask,input integer slot_number);
 begin
  while(!coordinate_ready)@(negedge clk);
  coordinate_element_base=base;coordinate_lane_stride=stride;coordinate_mask=mask;coordinate_slot=SB'(slot_number);
  coordinate_valid=1;@(negedge clk);coordinate_valid=0;
 end
endtask
task check_word(input [63:0] base,input [31:0] stride,input [7:0] mask);
 reg [15:0] expected;integer lane;
 begin
  while(!word_valid)begin @(negedge clk);if(protocol_error)$fatal(1,"unexpected fault");end
  repeat(checks%3)@(negedge clk);
  if(word_index!=coordinate_index)$fatal(1,"word identity");
  for(lane=0;lane<8;lane=lane+1)begin
   expected=mask[lane]?{byte_value(2*(base+64'(lane)*64'(stride))+1),byte_value(2*(base+64'(lane)*64'(stride)))}:16'd0;
   if(word_data[16*lane+:16]!==expected)$fatal(1,"data mismatch lane=%0d",lane);
  end
  word_ready=1;@(negedge clk);word_ready=0;coordinate_index=coordinate_index+1;checks=checks+1;
 end
endtask
task expect_fault;
 begin repeat(15)@(negedge clk);if(!protocol_error || word_valid || !drained)$fatal(1,"fault/drain failed");end
endtask
integer row,p,k,c,l,start_reads,start_bytes,stop,start_ticks,work_ticks;
reg [7:0] mask;
initial begin
 repeat(2)@(negedge clk);rst_n=1;
 reset_command(8480);start_reads=reads;start_bytes=bytes_read;start_ticks=ticks;
 for(row=0;row<2;row=row+1)for(p=0;p<7;p=p+SLOTS)for(k=0;k<80;k=k+1)begin
  stop=p+SLOTS<7?p+SLOTS:7;
  for(c=p;c<stop;c=c+1)begin
   mask=0;for(l=0;l<8;l=l+1)mask[l]=8*c+l<53;
   submit(64'(8*c*80+k),80,mask,c-p);check_word(64'(8*c*80+k),80,mask);
  end
 end
 work_ticks=ticks-start_ticks;
 if(reads-start_reads!=(RETAIN?1060:8480) || bytes_read-start_bytes!=(RETAIN?16960:135680))$fatal(1,"line reuse reads=%0d bytes=%0d",reads-start_reads,bytes_read-start_bytes);
 // Nonunit strides, nonzero base, truncated last line, and zero-stride aliases.
 reset_command(55);submit(7,2,8'hff,0);check_word(7,2,8'hff);
 submit(26,0,8'hff,0);check_word(26,0,8'hff);
 // Every active lane is checked before any read is published.
 reset_command(10);start_reads=reads;submit(0,1,8'hff,0);expect_fault();if(reads!=start_reads)$fatal(1,"partial invalid read");
 reset_command(64'hffffffffffffffff);submit(64'h8000000000000000,0,1,0);expect_fault();
 reset_command(16);fail_response=1;submit(0,0,1,0);expect_fault();
 // A foreign response while a request is held cannot withdraw that request.
 reset_command(16);block_read=1;submit(0,0,1,0);wait(read_valid);@(negedge clk);
 wrong_response=1;@(negedge clk);wrong_response=0;
 repeat(3)@(negedge clk);if(!read_valid || !protocol_error || drained)$fatal(1,"published request lost");
 block_read=0;expect_fault();
 if(!ZERO)begin
  reset_command(16);submit(0,0,1,0);wait(pending);@(negedge clk);
  wrong_response=1;@(negedge clk);wrong_response=0;
  if(drained)$fatal(1,"foreign response retired accepted read");expect_fault();
 end
 // clear is paired with cancellation of the behavioral external transport.
 reset_command(16);block_read=1;submit(0,0,1,0);wait(read_valid);
 reset_command(16);submit(0,1,8'hff,0);check_word(0,1,8'hff);
 $display("PASS gather checks=%0d retain=%0d workload_cycles=%0d",checks,RETAIN,work_ticks);$finish;
end
endmodule
''')
    sim=tmp_path/'sim'
    subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.SLOTS={slots}',f'-Ptb.ZERO={zero_latency}',f'-Ptb.RETAIN={retain}',
                    '-o',str(sim),str(ROOT/'rtl/abi3/ot_a3_bf16_weight_gather.sv'),str(bench)],check=True,capture_output=True,text=True)
    r=subprocess.run(['vvp',str(sim)],capture_output=True,text=True,timeout=60)
    assert r.returncode==0,r.stdout+r.stderr
    assert f'PASS gather checks=1123 retain={retain}' in r.stdout
    print(f'slots={slots} zero_latency={zero_latency} '+r.stdout.splitlines()[0])
