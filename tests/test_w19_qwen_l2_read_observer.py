"""Synthetic passive-monitor tests only; no shared-service or token evidence."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import w19_qwen_hbm_consumer_adapter as A

TB = r'''
`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,DUT_fault=0,finish_capture=0;
always #5 clk=~clk;
reg [63:0] read_v=0,read_ready=0;
reg [64*18-1:0] canonical_row=0;
reg [64*16-1:0] local_row=0,read_epoch=0;
reg [64*32-1:0] read_data=0;
reg [15:0] expected_epoch=16'h1234;
integer fault=0,r,p;
ot_w19_qwen_l2_read_observer #(.ENABLE_OBSERVER(ENABLED)) dut(.*);
initial begin
  if (!$value$plusargs("FAULT=%d",fault)) fault=0;
  repeat(2) @(negedge clk);rst_n=1;
  if (!ENABLED) begin
    DUT_fault=1;finish_capture=1;repeat(2) @(negedge clk);
    $display("PASS DEFAULT_DISABLED");$finish;
  end
  for(r=0;r<96;r=r+1) begin
    for(p=0;p<64;p=p+1) begin
      canonical_row[p*18+:18]=(p%32)*96+r;
      local_row[p*16+:16]=r;
      read_epoch[p*16+:16]=expected_epoch;
      read_data[p*32+:32]=32'h80000000+(p/32)*3072+(p%32)*96+r;
    end
    read_v={64{1'b1}};read_ready=0;
    // Held valid metadata/data must not count while stalled.
    repeat(2) @(negedge clk);
    read_ready={64{1'b1}};
    if(r==0) begin
      if(fault==1) canonical_row[17:0]=1;
      if(fault==2) read_epoch[15:0]=16'h1233;
      if(fault==5) DUT_fault=1;
      if(fault==6) read_data[31:0]=32'hxxxxxxxx;
    end
    if(r==1 && fault==3) begin canonical_row[17:0]=0;local_row[15:0]=0;end
    if(r==95 && fault==4) read_ready[63]=0;
    @(negedge clk);read_v=0;read_ready=0;
  end
  finish_capture=1;@(negedge clk);$finish;
end
endmodule
'''


@pytest.fixture(scope='module')
def compiled(tmp_path_factory):
    if not shutil.which('iverilog') or not shutil.which('vvp'):
        pytest.fail('Icarus required for the bounded passive observer gate')
    work = tmp_path_factory.mktemp('w19_read_observer')
    observer = ROOT / 'rtl/test/ot_w19_qwen_l2_read_observer.sv'
    binaries = {}
    for enabled in (0, 1):
        tb = work / f'tb{enabled}.sv'
        tb.write_text(TB.replace('ENABLED', str(enabled)))
        binary = work / f'sim{enabled}.vvp'
        subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(binary),
                        str(observer), str(tb)], check=True, capture_output=True, text=True)
        binaries[enabled] = binary
    return work, binaries


def run(compiled, name, fault=0, enabled=1):
    work, binaries = compiled
    trace = work / f'{name}.jsonl'
    args = ['vvp', str(binaries[enabled]), f'+FAULT={fault}']
    if enabled:
        args.append('+W19_READ_TRACE=' + str(trace))
    result = subprocess.run(args, capture_output=True, text=True, timeout=15)
    (work / f'{name}.log').write_text(result.stdout + result.stderr)
    (work / f'{name}.rc').write_text(str(result.returncode) + '\n')
    return result, trace


def test_full64ports_stalls_and_indexed_raw_capture(compiled):
    result, trace = run(compiled, 'full')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'rows=6144' in result.stdout
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    expected = {(d, 'raw_qkv_bits'): (32, [0x80000000+d*3072+r for r in range(3072)])
                for d in (0, 1)}
    report = A.check_records(expected, records, indexed_raw=True)
    assert report['elements'] == 6144 and report['runtime_admission'] is False
    with pytest.raises(ValueError, match='reordered'):
        A.check_records(expected, records)


def test_default_disabled(compiled):
    result, trace = run(compiled, 'disabled', enabled=0)
    assert result.returncode == 0 and 'PASS DEFAULT_DISABLED' in result.stdout
    assert not trace.exists()


@pytest.mark.parametrize('fault,message', [(1, 'identity/epoch'), (2, 'identity/epoch'),
    (3, 'duplicate'), (4, 'incomplete'), (5, 'DUT fault'), (6, 'unknown accepted')])
def test_monitor_faults_are_terminal_and_retained(compiled, fault, message):
    result, trace = run(compiled, f'fault{fault}', fault=fault)
    assert result.returncode != 0 and message in result.stdout
    assert trace.exists()


def test_indexed_raw_does_not_relax_numerical_order_or_duplicates():
    expected = {(0, 'q_norm_bits'): (32, [10, 11])}
    records = [dict(die=0, boundary='q_norm_bits', index=i, bits=10+i, cycle=0, fault=0)
               for i in (1, 0)]
    with pytest.raises(ValueError, match='reordered'):
        A.check_records(expected, records, indexed_raw=True)
    raw = {(0, 'raw_qkv_bits'): (32, [10, 11])}
    for record in records:
        record['boundary'] = 'raw_qkv_bits'
    with pytest.raises(ValueError, match='duplicate'):
        A.check_records(raw, records + records[:1], indexed_raw=True)
