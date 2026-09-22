"""Resident weight rows replay through real bank ownership and FIFO identities."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('row_words', [1, 31, 32, 512, 513, 1024, 1025, 2049])
def test_resident_row_replay(tmp_path, row_words):
    bench = tmp_path / 'tb.sv'
    bench.write_text(r'''module tb;
parameter integer ROW_WORDS=1;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0;
reg [31:0] command_generation=7,command_base=100,command_words=3*ROW_WORDS;
wire [31:0] command_row_words=ROW_WORDS;
wire command_ready,active,scheduled,command_error;
wire reserve_valid,reserve_ready,reserve_bank,fetch_valid,fetch_ready;
wire [63:0] reserve_tag,fetch_tag,fill_tag,tile_tag,tile_stream_tag;
wire [9:0] reserve_words,fetch_words,tile_words;
wire [31:0] fetch_address;
wire fill_valid,fill_ready,fill_bank,tile_valid,tile_ready,tile_bank,tile_retain;
wire [127:0] fill_data;
reg backing=0;reg [63:0] response_tag=0;
reg [9:0] response_index=0,burst_words=0;
reg [31:0] burst_base=0;
integer ticks=0,fills=0,consumed=0;
wire response_valid=backing && ticks%5!=0;
wire response_ready,response_mismatch;
wire [127:0] response_data=128'((burst_base+32'(response_index)-100)%ROW_WORDS+17);
assign fetch_ready=!backing && ticks%3!=0;
wire cancel_valid=0,cancel_bank=0;wire [63:0] cancel_tag=0;
wire cancel_ready,word_valid,word_last,tile_released;
wire [127:0] word_data;wire [63:0] word_tag,released_tag;wire [9:0] word_index;
wire [1:0] ready_banks,active_banks;wire [3:0] reserved_slots;
wire word_ready=ticks%11<6;
ot_a3_weight_tile_scheduler #(.TILE_WORDS(32),.ROW_REUSE(1)) scheduler(.*);
ot_a3_weight_tile_prefetch #(.SEPARATE_STREAM_TAG(1)) prefetch(.*);
reg held=0;reg [202:0] held_payload;
always @(posedge clk)begin
 if(!rst_n)begin backing<=0;response_index<=0;fills<=0;consumed<=0;held<=0;ticks<=0;end
 else begin
  ticks<=ticks+1;
  if(command_error || response_mismatch)$fatal(1,"unexpected protocol error");
  if(held && (!word_valid || {word_data,word_tag,word_index,word_last}!==held_payload))$fatal(1,"stalled output changed");
  held<=word_valid && !word_ready;held_payload<={word_data,word_tag,word_index,word_last};
  if(fetch_valid && fetch_ready)begin
   backing<=1;response_tag<=fetch_tag;burst_base<=fetch_address;burst_words<=fetch_words;response_index<=0;
   if(fills==0 && ROW_WORDS<=1024 && fetch_words!=
      ((ROW_WORDS<=32)?ROW_WORDS:((ROW_WORDS>544)?ROW_WORDS-512:32)))$fatal(1,"first bank not minimized");
   if(fetch_tag!={command_generation,fetch_address})$fatal(1,"fetch ownership tag");
  end
  if(response_valid && response_ready)begin
   fills<=fills+1;
   if(response_index==burst_words-1)backing<=0;else response_index<=response_index+1'b1;
  end
  if(word_valid && word_ready)begin
   if(word_tag[63:32]!=command_generation || word_tag[31:0]+32'(word_index)!=32'(100+consumed))$fatal(1,"issue identity lost at %0d",consumed);
   if(word_data!=128'(consumed%ROW_WORDS+17))$fatal(1,"wrong resident data");
   consumed<=consumed+1;
  end
 end
end
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task launch;begin
 command_valid=1;#1;if(!command_ready)$fatal(1,"not ready");tick();command_valid=0;
end endtask
task finish_run;begin
 wait(consumed==command_words);repeat(10)tick();
 if(active || word_valid || ready_banks!=0 || active_banks!=0)$fatal(1,"final release incomplete");
 if(fills!=((ROW_WORDS<=1024)?ROW_WORDS:command_words))$fatal(1,"traffic mismatch got %0d",fills);
end endtask
initial begin
 tick();rst_n=1;launch();finish_run();
 // Cancel after first output while data remains in banks/FIFO, then restart.
 rst_n=0;tick();rst_n=1;command_generation=8;launch();
 wait(consumed==1);@(negedge clk);rst_n=0;tick();rst_n=1;
 command_generation=9;launch();finish_run();
 $display("PASS row reuse words=%0d fills=%0d outputs=%0d",ROW_WORDS,fills,consumed);$finish;
end
initial begin #2000000;$fatal(1,"timeout");end
endmodule
''')
    names = ['ot_a3_weight_tile_scheduler', 'ot_a3_weight_tile_prefetch',
             'ot_a3_runtime_weight_banks', 'ot_a3_operand_bank_owner']
    built = subprocess.run(['iverilog', '-g2012', '-s', 'tb', f'-Ptb.ROW_WORDS={row_words}',
                            '-o', str(tmp_path/'sim'),
                            *[str(ROOT/'rtl/abi3'/f'{n}.sv') for n in names],
                            str(ROOT/'rtl/test/tb_a3_runtime_weight_banks.sv'), str(bench)],
                           capture_output=True, text=True, timeout=30)
    assert built.returncode == 0, built.stderr
    run = subprocess.run(['vvp', str(tmp_path/'sim')], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'PASS row reuse' in run.stdout
