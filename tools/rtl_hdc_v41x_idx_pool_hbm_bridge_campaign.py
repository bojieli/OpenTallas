#!/usr/bin/env python3
"""Timed four-stack index-key HBM write/read-order gate."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/hdc_v41x_idx_pool_hbm_bridge_campaign.json'
SOURCES=[ROOT/f'rtl/hdc/v41x/{name}.sv' for name in
         ('ot_hdc_v41x_idx_pool_hbm_bridge','ot_hdc_v41x_idx_hbm')]
SOURCES.append(ROOT/'rtl/test/tb_hdc_v41x_idx_pool_hbm_bridge.sv')
EXE=Path('/tmp/claude-1000/idx_pool_hbm_bridge.vvp')
PAT=re.compile(r'V41XPOOLHBMWR records=(\d+) writes=(\d+) reads=(\d+) highwater=(\d+) '
               r'read_stalls=(\d+) writer_stalls=(\d+) errors=(\d+)')

def main():
    subprocess.run(['iverilog','-g2012','-s','tb_hdc_v41x_idx_pool_hbm_bridge',
                    '-o',str(EXE),*[str(p) for p in SOURCES]],check=True,cwd=ROOT)
    run=subprocess.run(['vvp',str(EXE)],capture_output=True,text=True,timeout=120,check=True)
    match=PAT.search(run.stdout)
    if not match:
        raise RuntimeError(run.stdout+run.stderr)
    records,writes,reads,highwater,read_stalls,writer_stalls,errors=map(int,match.groups())
    assert (records,writes,reads,highwater,errors)==(6,72,4,4,0),match.groups()
    assert read_stalls>0 and writer_stalls>0,match.groups()
    rec=dict(schema='opentallas.hdc-v41x-idx-pool-hbm-bridge.v1',status='pass',
             records_committed=records,sector_writes_committed=writes,
             returned_reads_last_phase=reads,fifo_highwater=highwater,
             read_stall_cycles=read_stalls,writer_stall_cycles=writer_stalls,errors=errors,
             hbm_refresh_mode='REFPB=3 (refresh-aware per-bank with MRU tie-break)',
             coverage='Four-stack three-sector writes, partial scale-sector byte update, '
                      'read hold until write commit, four-record FIFO full/backpressure and fifth-record drain.',
             limitation='Simulation HBM controller with timed queues; no physical HBM PHY or routed core timing.',
             input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [*SOURCES,Path(__file__).resolve()]})
    OUT.write_text(json.dumps(rec,indent=2)+'\n')
    print(run.stdout.strip())

if __name__=='__main__':
    main()
