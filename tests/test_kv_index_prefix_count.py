"""Prefix-count admission matches the old popcount and independent mask rules."""
from pathlib import Path
import random
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('slots', [1, 3, 8, 64, 65, 128])
@pytest.mark.parametrize('simulator', ['iverilog', 'verilator'])
def test_prefix_admission(tmp_path, slots, simulator):
    rng = random.Random(301 + slots)
    masks = list(range(1 << slots)) if slots <= 8 else [rng.getrandbits(slots) for _ in range(256)]
    masks += [(1 << n) - 1 for n in range(slots + 1)]
    cases = []
    for mask in masks:
        for invalid_range in [False, True]:
            values = [rng.randrange(127) if mask >> i & 1 else 0xffffffff for i in range(slots)]
            if invalid_range and mask:
                values[(mask & -mask).bit_length() - 1] = 128
            range_error = any(x != 0xffffffff and x >= 128 for x in values)
            shape_error = mask == 0 or mask & (mask + 1) != 0
            # Codes come from the ABI engine package, emitted symbolically below.
            kind = 1 if range_error else 2 if shape_error else 0
            count = mask.bit_count() if kind == 0 else 0
            live = mask if kind == 0 else 0
            packed = sum(v << (32 * i) for i, v in enumerate(values))
            cases.append(f"{packed:x} {live:x} {count:x} {kind:x}\n")
    (tmp_path / 'vectors.txt').write_text(''.join(cases))
    old = (ROOT / 'results/rtl/kv_index_prefix_count/before.sv').read_text()
    (tmp_path / 'old.sv').write_text(old.replace('module ot_a3_attention_kv_index', 'module old_index'))
    bench = tmp_path / 'tb.sv'
    bench.write_text(f'''module tb;
localparam SLOTS={slots};
reg clk=0;always #5 clk=~clk;
reg rst_n=0,start=0;reg [31:0] cfg_kv_rows=128;
reg [SLOTS*32-1:0] indices;
wire busy,done,old_busy,old_done;
wire [SLOTS-1:0] lane_valid,old_mask;
wire [31:0] live_count,old_count;
wire [7:0] error_code,old_error;
ot_a3_attention_kv_index #(.SLOTS(SLOTS)) dut(.*);
old_index #(.SLOTS(SLOTS)) reference_dut(.clk(clk),.rst_n(rst_n),.start(start),
.cfg_kv_rows(cfg_kv_rows),.indices(indices),.busy(old_busy),.done(old_done),
.lane_valid(old_mask),.live_count(old_count),.error_code(old_error));
integer file_handle,rc,n=0,kind,count;reg [SLOTS-1:0] mask;
reg [7:0] expected_error;
initial begin
 repeat(2)@(negedge clk);rst_n=1;
 file_handle=$fopen("vectors.txt","r");
 while(!$feof(file_handle))begin
  rc=$fscanf(file_handle,"%h %h %h %h\\n",indices,mask,count,kind);
  if(rc!=4)$fatal(1,"bad vector");
  expected_error=kind==1?ot_a3_engine_pkg::ERR_INDEX_RANGE:
                 kind==2?ot_a3_engine_pkg::ERR_SHAPE:ot_a3_engine_pkg::ERR_NONE;
  start=1;@(negedge clk);
  if(!done || busy || lane_valid!==mask || live_count!==32'(count) || error_code!==expected_error)
   $fatal(1,"prefix contract case=%0d",n);
  if({{busy,done,lane_valid,live_count,error_code}}!=={{old_busy,old_done,old_mask,old_count,old_error}})
   $fatal(1,"baseline mismatch case=%0d",n);
  // Consecutive starts must publish a result every cycle. Periodically insert
  // idle cycles and perturb inputs; outputs must remain stable and done clear.
  if(n%7==0)begin
   start=0;indices=~indices;@(negedge clk);
   if(done || busy || lane_valid!==mask || live_count!==32'(count) || error_code!==expected_error)
    $fatal(1,"idle stability");
  end
  n=n+1;
 end
 start=0;rst_n=0;@(negedge clk);
 if(done || busy || lane_valid!=0 || live_count!=0 || error_code!=0)$fatal(1,"reset");
 $display("PASS slots=%0d cases=%0d",SLOTS,n);$finish;
end
endmodule
''')
    sources = [str(ROOT / 'rtl/abi3/ot_a3_engine_pkg.sv'),
               str(ROOT / 'rtl/abi3/ot_a3_attention_kv_index.sv'), str(tmp_path / 'old.sv'), str(bench)]
    if simulator == 'iverilog':
        if not shutil.which('iverilog'):
            pytest.skip('Icarus unavailable')
        command = ['iverilog', '-g2012', '-s', 'tb', '-o', str(tmp_path / 'sim'), *sources]
        run = ['vvp', str(tmp_path / 'sim')]
    else:
        verilator = Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'
        if not verilator.exists():
            pytest.skip('pinned Verilator unavailable')
        command = [str(verilator), '--binary', '--timing', '-j', '4', '-Wno-fatal',
                   '--top-module', 'tb', '--Mdir', str(tmp_path / 'obj'), *sources]
        run = [str(tmp_path / 'obj/Vtb')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(run, cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'cases={len(cases)}' in result.stdout
    print(result.stdout.splitlines()[0])
