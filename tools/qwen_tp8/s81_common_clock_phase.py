#!/usr/bin/env python3
"""Derive candidate compiler phase ABI from executed divider RTL (not PLL BB).
No physical source, CTS, minpulse or static-timing qualification is implied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'rtl/dsrom_sys/s81_ph/ot_s81_common_clock_epoch.sv'
TB = ROOT / 'rtl/dsrom_sys/s81_ph/tb_common_clock_epoch.sv'
TRACE = '''`timescale 1ps/1ps
module trace;
reg master=0,rst=0,lock=0;
wire cs,cv,valid,win,toggle,fault,run;wire[3:0] phase;
ot_s81_common_clock_epoch d(master,rst,lock,cs,cv,valid,win,toggle,fault,phase,run);
always #50 master=~master;
initial begin repeat(3) @(negedge master);rst=1;lock=1;
repeat(70) begin @(negedge master);if(valid && d.window_armed) $display("ROW %d %b %b %b",phase,cs,cv,win);end $finish;end
endmodule
'''

def simulate(source, bench, top):
    with tempfile.TemporaryDirectory(prefix='s81epoch-') as td:
        p=Path(td); (p/'dut.sv').write_text(source);(p/'tb.sv').write_text(bench)
        subprocess.run(['iverilog','-g2012','-s',top,'-o',str(p/'sim'),str(p/'dut.sv'),str(p/'tb.sv')],check=True,capture_output=True,text=True)
        return subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True)

def derive(source):
    result=simulate(source,TRACE,'trace')
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    rows={int(a):[int(b),int(c),int(d)] for line in result.stdout.splitlines() if line.startswith('ROW') for _,a,b,c,d in [line.split()]}
    assert len(rows)==12, rows
    expected=[[int(i%3==0),int(i%4<2),int(i in (11,0))] for i in range(12)]
    assert [rows[i] for i in range(12)]==expected, rows
    clocks={}
    for name,column,divide,high in [('stream',0,3,1),('serial',1,4,2)]:
        rising=[i for i in range(12) if rows[i][column] and not rows[(i-1)%12][column]]
        falling=[i for i in range(12) if not rows[i][column] and rows[(i-1)%12][column]]
        clocks[name]={'divide':divide,'duty':[high,divide], 'rising_master_edges':rising,'falling_master_edges':falling}
    # All cross-domain launch/capture forward separations, including coincidence.
    windows={}
    for launch in clocks:
        for capture in clocks:
            if launch==capture:continue
            for le in ('rising','falling'):
                for ce in ('rising','falling'):
                    windows[f'{launch}_{le}_to_{capture}_{ce}']=[{'launch':a,'next_capture_delta_master_cycles':min((b-a)%12 for b in clocks[capture][ce+'_master_edges'])} for a in clocks[launch][le+'_master_edges']]
    return {'status':'CANDIDATE_NOT_PHYSICALLY_QUALIFIED','rtl_sha256':hashlib.sha256(source.encode()).hexdigest(),'master_period_ns':[5,18],'common_epoch_master_cycles':12,'phase_rows':[rows[i] for i in range(12)],'clocks':clocks,'related_windows':windows,'caveat':'Coincident edges have zero forward separation; timing must use real launch/capture constraints. No false paths or ideal phase grants. Reset serial pulses may be one master tick.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);ap.add_argument('--test',action='store_true');args=ap.parse_args()
    source=RTL.read_text();table=derive(source)
    if args.test:
        good=simulate(source,TB.read_text(),'tb_common_clock_epoch');assert good.returncode==0,good.stdout
        mutants={
            'duty':source.replace('next_phase == 0 || next_phase == 3','next_phase == 0 || next_phase == 1 || next_phase == 3'),
            'phase':source.replace('(phase == 11) ? 0','(phase == 10) ? 0'),
            'epoch':source.replace('(phase == 10 && armed)', '(phase == 9 && armed)'),
            'lock':source.replace('rst_n && source_lock && lock_sync','rst_n && lock_sync').replace('rst_n && source_lock;', 'rst_n;'),
            'fault':source.replace('epoch_fault <= 1;','epoch_fault <= 0;'),
        }
        for name,mutant in mutants.items():
            assert mutant != source
            rejected=simulate(mutant,TB.read_text(),'tb_common_clock_epoch').returncode!=0
            if not rejected:
                try:derive(mutant)
                except (AssertionError,RuntimeError):rejected=True
            assert rejected, f'mutant survived: {name}'
        print(good.stdout.strip());print('PASS duty/phase/epoch/lock/fault mutants rejected')
    if args.output:args.output.write_text(json.dumps(table,indent=2)+'\n')
    elif not args.test:print(json.dumps(table,indent=2))
if __name__=='__main__':main()
