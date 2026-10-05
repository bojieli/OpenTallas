"""Multi-slot state lookup stays cycle-equivalent to the encoded-mux baseline."""
from pathlib import Path
import random
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('simulator', ['iverilog', 'verilator'])
@pytest.mark.parametrize('slots', [3, 16])
def test_parallel_lookup(tmp_path, simulator, slots):
    rng = random.Random(1093 + slots)
    commands = []
    # Allocate all slots with distinct identities/policies, then access them in
    # reverse order with unrelated payload fields to exercise stored-field use.
    for i in range(slots):
        commands.append((0, 0, 0, 1, 1, i + 1, 1, 3, i % 3, 7, 127, i))
    for i in reversed(range(slots)):
        commands.append((0, 0, 0, 1, 2, i + 1, 1, 3, 2, 999, 0, 0xffffffff))
    commands.append((0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
    commands += [(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)] * (40 * slots)
    for _ in range(5000):
        commands.append((int(rng.randrange(200) == 0), int(rng.randrange(40) == 0),
                         int(rng.randrange(70) == 0), int(rng.randrange(5) != 0),
                         rng.randrange(6), rng.randrange(1, slots + 4), rng.randrange(2),
                         rng.choice([0, 1, 2, 7, 31, 0x80000000, 0xffffffff]),
                         rng.randrange(3), rng.getrandbits(32),
                         rng.choice([0, 1, 3, 128, 0xffffffff]), rng.getrandbits(32)))
    (tmp_path / 'vectors.txt').write_text(''.join(' '.join(f'{v:x}' for v in row) + '\n' for row in commands))
    old = (ROOT / 'results/rtl/state_parallel_admission/before.sv').read_text()
    (tmp_path / 'old.sv').write_text(old.replace('module ot_a3_state_controller', 'module old_state'))
    outputs = ['op_done', 'op_ok', 'op_trap_class', 'apply_busy', 'apply_done', 'apply_overflow',
               'count_prepares', 'count_commits', 'count_discards', 'count_reads',
               'count_generation_advances', 'count_commits_applied', 'count_rows_committed', 'count_bytes_written']
    compare = '\n'.join(f'if(dut.{x}!==reference_dut.{x})$fatal(1,"{x} cycle=%0d",n);' for x in outputs)
    fields = ['slot_descriptor', 'slot_cursor', 'slot_capacity', 'slot_row_bytes', 'slot_generation', 'slot_policy']
    compare_slots = '\n'.join(f'if(dut.{x}[i]!==reference_dut.{x}[i])$fatal(1,"{x} slot=%0d cycle=%0d",i,n);' for x in fields)
    ports = '.clk(clk),.rst_n(rst_n),.clear(clear),.op_valid(op_valid),.op_sub(op_sub),.op_descriptor_id(op_descriptor_id),.op_rows(op_rows),.op_rows_bound(op_rows_bound),.op_payload(op_payload),.commit_all(commit_all),.discard_all(discard_all),.session_state_count(32\'d1)'
    bench = tmp_path / 'tb.sv'
    bench.write_text(f'''module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,op_valid=0,commit_all=0,discard_all=0,op_rows_bound=0;
reg [7:0] op_sub=0;reg [31:0] op_descriptor_id=0,op_rows=0;
reg [511:0] op_payload=0;
ot_a3_state_controller #(.SLOTS({slots})) dut({ports});
old_state #(.SLOTS({slots})) reference_dut({ports});
integer fh,rc,n=0;reg [31:0] policy,row_bytes,capacity,cursor;
initial begin
 repeat(2)@(negedge clk);rst_n=1;fh=$fopen("vectors.txt","r");
 while(!$feof(fh))begin
  rc=$fscanf(fh,"%h %h %h %h %h %h %h %h %h %h %h %h\\n",clear,commit_all,discard_all,op_valid,op_sub,op_descriptor_id,op_rows_bound,op_rows,policy,row_bytes,capacity,cursor);
  if(rc!=12)$fatal(1,"vector");
  op_payload=0;op_payload[8+:8]=policy[7:0];op_payload[128+:32]=row_bytes;
  op_payload[192+:32]=capacity;op_payload[256+:32]=cursor;
  @(negedge clk);
  {compare}
  if(dut.slot_used!==reference_dut.slot_used || dut.slot_open!==reference_dut.slot_open || dut.pending_count!==reference_dut.pending_count)$fatal(1,"ownership");
  for(integer i=0;i<{slots};i=i+1)begin
   {compare_slots}
   for(integer j=0;j<i;j=j+1)
    if(dut.slot_used[i] && dut.slot_used[j] && dut.slot_descriptor[i]==dut.slot_descriptor[j])$fatal(1,"duplicate descriptor allocation");
   if(i<dut.pending_count && (dut.pending_slot[i]!==reference_dut.pending_slot[i] || dut.pending_rows[i]!==reference_dut.pending_rows[i] || dut.pending_span[i]!==reference_dut.pending_span[i]))$fatal(1,"pending payload");
  end
  n=n+1;
 end
 $display("PASS slots={slots} cycles=%0d",n);$finish;
end
endmodule
''')
    sources = [str(ROOT / 'rtl/abi3/ot_a3_pkg.sv'), str(ROOT / 'rtl/abi3/ot_a3_state_controller.sv'), str(tmp_path / 'old.sv'), str(bench)]
    if simulator == 'iverilog':
        command = ['iverilog', '-g2012', '-s', 'tb', '-o', str(tmp_path / 'sim'), *sources]
        run = ['vvp', str(tmp_path / 'sim')]
    else:
        tool = Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'
        command = [str(tool), '--binary', '--timing', '-j', '4', '-Wno-fatal', '--top-module', 'tb', '--Mdir', str(tmp_path / 'obj'), *sources]
        run = [str(tmp_path / 'obj/Vtb')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(run, cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'cycles={len(commands)}' in result.stdout
    print(result.stdout.splitlines()[0])
