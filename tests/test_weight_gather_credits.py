"""Ordered delayed memory exercises concurrent line reads and fault drain."""
from pathlib import Path
import re
import shutil
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which('iverilog') is None,reason='iverilog unavailable')
@pytest.mark.parametrize('simulator', ['iverilog', 'verilator'])
def test_overlapped_reads_and_fault_drain(tmp_path, simulator):
    bench=tmp_path/'tb.sv'
    bench.write_text(r'''module tb;
parameter integer CREDITS=1;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,coordinate_valid=0,word_ready=0;
reg [31:0] command_generation=7;wire [31:0] command_object=1,command_lane_stride=8;
wire [63:0] command_object_bytes=4096;reg [63:0] coordinate_element_base=0;
wire [7:0] coordinate_mask=255;wire [1:0] coordinate_slot=0;
reg [31:0] coordinate_index=0;
wire command_ready,coordinate_ready,word_valid,read_valid,response_ready,protocol_error,drained;
wire [127:0] word_data;wire [31:0] word_index,read_object;
wire [63:0] read_tag,read_offset;wire [4:0] read_bytes;
reg [63:0] tags[0:7],offsets[0:7];integer due[0:7];
integer head=0,tail=0,count=0,ticks=0,peak=0,reads=0;
reg fail_response=0,foreign_response=0,block_read=0,hold_response=0,force_ready=0;
wire read_ready=!block_read && count<8 && (force_ready || ticks%5!=0);
wire response_valid=foreign_response || (!hold_response && count!=0 && ticks>=due[head]);
wire [63:0] response_tag=foreign_response?64'hbad:tags[head];
wire response_error=fail_response;reg [127:0] response_data;
wire push=read_valid && read_ready;
wire pop=response_valid && response_ready && !foreign_response;
function automatic [7:0] byte_at(input [63:0] addr);byte_at=8'(addr^(addr>>8));endfunction
always @*for(integer b=0;b<16;b=b+1)response_data[b*8+:8]=byte_at(offsets[head]+64'(b));
ot_a3_bf16_weight_gather #(.READ_CREDITS(CREDITS)) dut(.*);
reg held=0;reg [164:0] saved_read;
always @(posedge clk)begin
 ticks<=ticks+1;
 if(!rst_n || clear)begin head<=0;tail<=0;count<=0;held<=0;end
 else begin
  if(held && (!read_valid || saved_read!={read_tag,read_object,read_offset,read_bytes}))$fatal(1,"unstable request");
  held<=read_valid && !read_ready;saved_read<={read_tag,read_object,read_offset,read_bytes};
  if(count>CREDITS)$fatal(1,"credit overflow");
  if(count>peak)peak<=count;
  case({push,pop})2'b10:count<=count+1;2'b01:count<=count-1;default:begin end endcase
  if(push)begin
   tags[tail]<=read_tag;offsets[tail]<=read_offset;due[tail]<=ticks+32;
   tail<=(tail+1)%8;reads<=reads+1;
   if(read_offset+read_bytes>4096 || read_bytes!=16)$fatal(1,"bounds");
  end
  if(pop)head<=(head+1)%8;
 end
end
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task begin_command;begin
 clear=1;block_read=0;hold_response=0;force_ready=0;coordinate_valid=0;word_ready=0;fail_response=0;foreign_response=0;tick();clear=0;
 command_generation=command_generation+1;command_valid=1;tick();command_valid=0;
end endtask
task submit(input integer idx);begin
 coordinate_index=32'(idx);coordinate_element_base=64'(idx*128);
 coordinate_valid=1;while(!coordinate_ready)tick();tick();coordinate_valid=0;
end endtask
integer start_tick,elapsed,before_reads;
reg [127:0] saved_word;
initial begin
 tick();rst_n=1;begin_command();start_tick=ticks;before_reads=reads;
 for(integer n=0;n<8;n=n+1)begin
  submit(n);wait(word_valid);@(negedge clk);
  if(protocol_error || word_index!=n)$fatal(1,"word identity");
  for(integer l=0;l<8;l=l+1)
   if(word_data[l*16+:16]!={byte_at(64'(n*256+l*16+1)),byte_at(64'(n*256+l*16))})$fatal(1,"wrong gathered data");
  saved_word=word_data;repeat(3)begin tick();if(!word_valid || word_data!=saved_word)$fatal(1,"word stall");end
  word_ready=1;tick();word_ready=0;
 end
 elapsed=ticks-start_tick;
 if(reads-before_reads!=64 || peak<CREDITS)$fatal(1,"overlap not exercised");
 // Foreign identity must not retire any expected read.
 begin_command();submit(0);wait(count==CREDITS);@(negedge clk);
 foreign_response=1;tick();foreign_response=0;
 if(!protocol_error || drained)$fatal(1,"foreign response lost ownership");
 wait(drained);@(negedge clk);if(word_valid || count!=0)$fatal(1,"fault leaked word or read");
 // Error on the head response retains ownership of other accepted reads.
 begin_command();submit(0);wait(count==CREDITS);@(negedge clk);fail_response=1;
 wait(protocol_error);@(negedge clk);fail_response=0;
 wait(drained);@(negedge clk);if(word_valid || count!=0)$fatal(1,"error did not drain");
 // An error response must not withdraw a different already-published
 // request that the receiver is stalling.
 if(CREDITS>1)begin
  begin_command();submit(0);wait(count==1);@(negedge clk);block_read=1;
  wait(read_valid);@(negedge clk);fail_response=1;
  wait(protocol_error);@(negedge clk);fail_response=0;
  repeat(3)begin tick();if(!read_valid || drained)$fatal(1,"fault withdrew held request");end
  block_read=0;wait(drained);@(negedge clk);
  if(word_valid || count!=0)$fatal(1,"held fault drain");
 end
 // Retire a faulted old read and accept a new held read on the same edge.
 if(CREDITS>1)begin
  begin_command();hold_response=1;submit(0);wait(count==1);@(negedge clk);block_read=1;
  wait(read_valid);repeat(40)tick();before_reads=reads;
  block_read=0;force_ready=1;hold_response=0;fail_response=1;
  #1;if(!push || !pop)$fatal(1,"simultaneous boundary not exercised");
  tick();force_ready=0;fail_response=0;
  if(!protocol_error || drained || count!=1 || reads!=before_reads+1)$fatal(1,"simultaneous fault ownership");
  wait(drained);@(negedge clk);if(word_valid || count!=0)$fatal(1,"simultaneous fault drain");
 end
 // Paired external cancellation revokes all queued reads before restart.
 begin_command();submit(0);wait(count==CREDITS);@(negedge clk);
 begin_command();submit(0);wait(word_valid);@(negedge clk);
 if(protocol_error)$fatal(1,"restart failed");word_ready=1;tick();
 $display("PASS credits=%0d cycles=%0d peak=%0d",CREDITS,elapsed,peak);$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
''')
    cycles=[]
    for credits in [1,2,4,8]:
        exe=tmp_path/f'sim{credits}'
        sources=[str(ROOT/'rtl/abi3/ot_a3_bf16_weight_gather.sv'),str(bench)]
        if simulator == 'iverilog':
            compile_cmd=['iverilog','-g2012','-s','tb',f'-Ptb.CREDITS={credits}','-o',str(exe),*sources]
            run_cmd=['vvp',str(exe)]
        else:
            verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
            if not verilator.exists():
                pytest.skip('pinned Verilator unavailable')
            obj=tmp_path/f'obj{credits}'
            compile_cmd=[str(verilator),'--binary','--timing','-j','4','-Wno-fatal','--top-module','tb',f'-GCREDITS={credits}','--Mdir',str(obj),*sources]
            run_cmd=[str(obj/'Vtb')]
        r=subprocess.run(compile_cmd,capture_output=True,text=True,timeout=120)
        assert r.returncode==0,r.stderr
        r=subprocess.run(run_cmd,capture_output=True,text=True,timeout=30)
        assert r.returncode==0,r.stdout+r.stderr
        cycles.append(int(re.search(r'cycles=(\d+)',r.stdout).group(1)))
    assert cycles[3]<cycles[2]<cycles[1]<cycles[0],cycles
    print(f'ordered gather workload cycles credits1/2/4/8={cycles}')
