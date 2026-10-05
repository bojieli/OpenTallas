"""Pass replay through real SRAM bank ownership, FIFO and compact fetch tags."""
from pathlib import Path
import shutil
import subprocess
import pytest
ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('reuse', [0, 1])
@pytest.mark.parametrize('interleave,rows,cols,depth', [
    (3, 6, 7, 160), (1, 3, 3, 1024), (3, 3, 7, 342),
    (3, 1, 7, 160), (3, 3, 2, 1), (3, 3, 7, 341)])
def test_pass_reuse(tmp_path, reuse, interleave, rows, cols, depth):
    expected_fetch, expected_issue = [], []
    for p in range(0, cols, interleave):
        words = [(c << 16) + k + 17 for k in range(depth)
                 for c in range(p, min(p+interleave, cols))]
        expected_issue.extend(words * rows)
        expected_fetch.extend(words if reuse and len(words)<=1024 and rows>1 else words*rows)
    for name, values in [('fetch', expected_fetch), ('issue', expected_issue)]:
        (tmp_path/f'{name}.hex').write_text(''.join(f'{v:032x}\n' for v in values))
    bench = tmp_path/'tb.sv'
    bench.write_text(r''' module tb;
parameter integer ROWS=3,COLS=7,DEPTH=160,INTERLEAVE=3;
parameter bit REUSE=1;
parameter integer FETCH_COUNT=1;
parameter [31:0] BASE=100;
parameter bit ABSOLUTE_ADDRESS=0;
parameter bit SINGLE_GENERATION=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0;
reg [31:0] command_generation=7,command_base=BASE,command_words=ROWS*COLS*DEPTH;
reg [15:0] command_rows=ROWS,command_local_cols=COLS,command_depth_words=DEPTH;
reg [127:0] expected_fetch[0:FETCH_COUNT-1],expected_issue[0:ROWS*COLS*DEPTH-1];
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
wire [127:0] response_data=expected_fetch[burst_base+32'(response_index)-BASE];
assign fetch_ready=!backing && ticks%3!=0;
wire cancel_valid=0,cancel_bank=0;wire [63:0] cancel_tag=0;
wire cancel_ready,word_valid,word_last,tile_released;
wire [127:0] word_data;wire [63:0] word_tag,released_tag;wire [9:0] word_index;
wire [1:0] ready_banks,active_banks;wire [3:0] reserved_slots;
wire word_ready=ticks%11<6;
ot_a3_weight_pass_scheduler #(.INTERLEAVE(INTERLEAVE),.REUSE_PASSES(REUSE)) scheduler(.*);
ot_a3_weight_tile_prefetch #(.SEPARATE_STREAM_TAG(1),.ABSOLUTE_STREAM_ADDRESS(ABSOLUTE_ADDRESS),.SINGLE_GENERATION(SINGLE_GENERATION)) prefetch(.*);
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
   if(fetch_address!=BASE+32'(fills) || fills+32'(fetch_words)>FETCH_COUNT)$fatal(1,"noncompact fetch");
   if(fetch_tag!={command_generation,fetch_address})$fatal(1,"fetch ownership tag");
  end
  if(response_valid && response_ready)begin
   fills<=fills+1;
   if(response_index==burst_words-1)backing<=0;else response_index<=response_index+1'b1;
  end
  if(word_valid && word_ready)begin
   if(word_tag[63:32]!=command_generation || word_tag[31:0]+(ABSOLUTE_ADDRESS?32'd0:32'(word_index))!=32'(BASE+consumed))$fatal(1,"issue identity lost at %0d",consumed);
   if(word_data!==expected_issue[consumed])$fatal(1,"wrong resident data");
   consumed<=consumed+1;
  end
 end
end
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task launch;begin
 command_base=BASE;command_rows=ROWS;command_local_cols=COLS;command_depth_words=DEPTH;
 command_valid=1;#1;if(!command_ready)$fatal(1,"not ready");tick();command_valid=0;
 command_base=0;command_rows=0;command_local_cols=0;command_depth_words=0;
end endtask
task finish_run;begin
 wait(consumed==command_words);repeat(10)tick();
 if(active || word_valid || ready_banks!=0 || active_banks!=0)$fatal(1,"final release incomplete");
 if(fills!=FETCH_COUNT)$fatal(1,"traffic mismatch got %0d",fills);
end endtask
initial begin
 $readmemh("FETCH_FILE",expected_fetch);$readmemh("ISSUE_FILE",expected_issue);
 tick();rst_n=1;launch();finish_run();
 // Cancel after first output while data remains in banks/FIFO, then restart.
 rst_n=0;tick();rst_n=1;command_generation=8;launch();
 wait(consumed==1);@(negedge clk);rst_n=0;tick();rst_n=1;
 command_generation=9;launch();finish_run();
 $display("PASS pass reuse fills=%0d outputs=%0d cycles=%0d",fills,consumed,ticks);$finish;
end
initial begin #2000000;$fatal(1,"timeout");end
endmodule
'''.replace('FETCH_FILE', str(tmp_path/'fetch.hex')).replace('ISSUE_FILE', str(tmp_path/'issue.hex')))
    names = ['ot_a3_weight_pass_scheduler', 'ot_a3_weight_tile_scheduler',
             'ot_a3_weight_tile_prefetch', 'ot_a3_runtime_weight_banks', 'ot_a3_operand_bank_owner']
    args = dict(ROWS=rows, COLS=cols, DEPTH=depth, INTERLEAVE=interleave,
                REUSE=reuse, FETCH_COUNT=len(expected_fetch), BASE=0xffff0000,
                ABSOLUTE_ADDRESS=1, SINGLE_GENERATION=1)
    built = subprocess.run(['iverilog', '-g2012', '-s', 'tb',
                            *[f'-Ptb.{k}={v}' for k,v in args.items()],
                            '-o', str(tmp_path/'sim'),
                            *[str(ROOT/'rtl/abi3'/f'{n}.sv') for n in names],
                            str(ROOT/'rtl/test/tb_a3_runtime_weight_banks.sv'), str(bench)],
                           capture_output=True, text=True, timeout=30)
    assert built.returncode == 0, built.stderr
    run = subprocess.run(['vvp', str(tmp_path/'sim')], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'PASS pass reuse' in run.stdout


def test_pass_admission_and_clear(tmp_path):
    if shutil.which('iverilog') is None:
        pytest.skip('iverilog unavailable')
    bench = tmp_path/'tb.sv'
    bench.write_text(r'''module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0;
reg [31:0] command_base=0;
reg [15:0] command_rows=1,command_local_cols=1,command_depth_words=1;
wire command_ready,command_error,active,reserve_valid,fetch_valid,tile_valid,response_ready;
integer stage;
ot_a3_weight_pass_scheduler dut(
.clk(clk),.rst_n(rst_n),.clear(clear),.command_valid(command_valid),.command_ready(command_ready),
.command_generation(32'd7),.command_base(command_base),.command_rows(command_rows),
.command_local_cols(command_local_cols),.command_depth_words(command_depth_words),
.command_error(command_error),.active(active),.reserve_valid(reserve_valid),.reserve_ready(1'b0),
.fetch_valid(fetch_valid),.fetch_ready(1'b0),.tile_valid(tile_valid),.tile_ready(1'b0),
.response_valid(1'b0),.response_ready(response_ready),.response_tag(64'd0),.response_index(10'd0),
.response_data(128'd0),.fill_ready(1'b0));
task tick;begin @(negedge clk);end endtask
task launch;begin command_valid=1;tick();command_valid=0;end endtask
task cancel;begin
 clear=1;#1;if(command_ready || reserve_valid || fetch_valid || tile_valid || response_ready)$fatal(1,"clear publication");
 @(posedge clk);tick();clear=0;#1;if(active || command_error || !command_ready)$fatal(1,"clear ownership");
end endtask
task refuse;begin
 launch();repeat(8)begin tick();if(reserve_valid || fetch_valid || tile_valid)$fatal(1,"invalid publication");end
 if(!command_error || active || command_ready)$fatal(1,"missing sticky refusal");cancel();
end endtask
initial begin
 tick();rst_n=1;
 command_rows=0;refuse();command_rows=1;
 command_local_cols=0;refuse();command_local_cols=1;
 command_depth_words=0;refuse();command_depth_words=1;
 command_rows=65535;command_local_cols=65535;command_depth_words=65535;refuse();
 command_rows=1;command_local_cols=1;command_depth_words=2;command_base=32'hffffffff;refuse();
 // A legal last word at UINT32_MAX is accepted. Cancel during every
 // admission state and while the first bank reservation is stalled.
 command_depth_words=1;
 for(stage=0;stage<9;stage=stage+1)begin
  launch();repeat(stage)tick();if(command_error)$fatal(1,"legal end rejected");cancel();
 end
 launch();wait(reserve_valid);#1;if(command_error)$fatal(1,"legal last word refused");cancel();
 $display("PASS pass admission and cancellation");$finish;
end
initial begin #10000;$fatal(1,"timeout");end
endmodule
''')
    sim = tmp_path/'sim'
    built = subprocess.run(['iverilog','-g2012','-s','tb','-o',str(sim),
                            str(ROOT/'rtl/abi3/ot_a3_weight_pass_scheduler.sv'),
                            str(ROOT/'rtl/abi3/ot_a3_weight_tile_scheduler.sv'),str(bench)],
                           capture_output=True,text=True,timeout=30)
    assert built.returncode == 0, built.stderr
    run = subprocess.run(['vvp',str(sim)],capture_output=True,text=True,timeout=30)
    assert run.returncode == 0, run.stdout+run.stderr
    assert 'PASS pass admission' in run.stdout


def test_registered_final_tile_ownership(tmp_path):
    if shutil.which('iverilog') is None:
        pytest.skip('iverilog unavailable')
    bench = tmp_path/'tb.sv'
    bench.write_text(r'''module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,tile_ready=0,backing=0;
wire command_ready,active,scheduled,command_error,fetch_valid,tile_valid;
wire response_ready,response_mismatch;
wire [63:0] fetch_tag,tile_tag,tile_stream_tag;
wire [9:0] tile_words;wire tile_bank,tile_retain;
reg [63:0] response_tag;
integer accepted=0,completions=0;
ot_a3_weight_pass_scheduler dut(
.clk(clk),.rst_n(rst_n),.clear(clear),.command_valid(command_valid),.command_ready(command_ready),
.command_generation(32'd7),.command_base(32'd100),.command_rows(16'd2),
.command_local_cols(16'd1),.command_depth_words(16'd1),
.active(active),.scheduled(scheduled),.command_error(command_error),
.reserve_ready(1'b1),.fetch_valid(fetch_valid),.fetch_ready(!backing),.fetch_tag(fetch_tag),
.response_valid(backing),.response_ready(response_ready),.response_mismatch(response_mismatch),
.response_tag(response_tag),.response_index(10'd0),.response_data(128'd17),.fill_ready(1'b1),
.tile_valid(tile_valid),.tile_ready(tile_ready),.tile_tag(tile_tag),.tile_stream_tag(tile_stream_tag),
.tile_words(tile_words),.tile_bank(tile_bank),.tile_retain(tile_retain));
always @(posedge clk)begin
 if(!rst_n || clear)begin backing<=0;accepted<=0;completions<=0;end
 else begin
  if(fetch_valid && !backing)begin backing<=1;response_tag<=fetch_tag;end
  if(backing && response_ready)backing<=0;
  if(command_error || response_mismatch)$fatal(1,"protocol error");
  if(tile_valid && tile_ready)begin
   if(tile_tag!={32'd7,32'd100} || tile_stream_tag!={32'd7,32'(100+accepted)} ||
      tile_words!=1 || tile_bank || tile_retain!=(accepted==0))$fatal(1,"tile identity");
   accepted<=accepted+1;
  end
  if(scheduled)begin
   if(accepted!=2 || tile_valid)$fatal(1,"early completion");completions<=completions+1;
  end
 end
end
task tick;begin @(negedge clk);end endtask
task launch;begin command_valid=1;tick();command_valid=0;end endtask
initial begin
 tick();rst_n=1;launch();wait(tile_valid);tick();
 tile_ready=1;tick();tile_ready=0;
 wait(tile_valid);repeat(12)begin
  tick();if(!active || scheduled || command_ready || tile_stream_tag!={32'd7,32'd101})$fatal(1,"lost stalled final ownership");
 end
 tile_ready=1;tick();tile_ready=0;wait(scheduled);repeat(4)tick();
 if(completions!=1 || active || !command_ready)$fatal(1,"completion count");
 // A held tile is revoked by clear and cannot leak into the next command.
 clear=1;tick();clear=0;launch();wait(tile_valid);tick();clear=1;
 #1;if(tile_valid || command_ready)$fatal(1,"clear publication");
 tick();clear=0;#1;if(tile_valid || active || !command_ready)$fatal(1,"clear ownership");
 launch();tile_ready=1;wait(scheduled);repeat(4)tick();
 if(accepted!=2 || completions!=1)$fatal(1,"restart failed");
 $display("PASS registered final tile ownership");$finish;
end
initial begin #10000;$fatal(1,"timeout");end
endmodule
''')
    sim = tmp_path/'sim'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(sim),
                    str(ROOT/'rtl/abi3/ot_a3_weight_pass_scheduler.sv'),
                    str(ROOT/'rtl/abi3/ot_a3_weight_tile_scheduler.sv'),str(bench)],
                   check=True,capture_output=True,timeout=30)
    run = subprocess.run(['vvp',str(sim)],capture_output=True,text=True,timeout=30)
    assert run.returncode == 0, run.stdout+run.stderr
    assert 'PASS registered final tile ownership' in run.stdout
