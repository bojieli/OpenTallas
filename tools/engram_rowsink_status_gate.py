#!/usr/bin/env python3
"""Directed supplement to the immutable failed 07189f858 Engram campaign."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SINK = ROOT / 'rtl/dsrom_sys/engram/ot_dsrom_engram_rowsink.sv'
TB = ROOT / 'rtl/test/tb_dsrom_engram_status_order.sv'
DECODE = ROOT / 'rtl/hdc/v41/ot_hdc_engram_gather.sv'
PKG = ROOT / 'rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv'
OUT = ROOT / 'results/rtl/engram_rowsink_status_gate_20261009.json'


def main():
    source = SINK.read_text()
    needle = '&& (scnt[gt] == NC[5:0]);'
    assert source.count(needle) == 1
    rec = dict(schema='opentallas.engram-status-directed.v1',
               supplements='results/rtl/engram_lookup_recovered_07189f858/campaign.json',
               boundary='minimum full-shape rowsink status/data ordering; no whole-die/route credit',
               input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (SINK, TB, DECODE, PKG)}, cases={})
    with tempfile.TemporaryDirectory(prefix='engram-status-') as tmp:
        work = Path(tmp)
        for name, text in [('control', source),('statuses_not_awaited', source.replace(needle,';'))]:
            src = work / (name+'.sv');src.write_text(text)
            exe = work / (name+'.vvp')
            build = subprocess.run(['iverilog','-g2012','-s','tb_dsrom_engram_status_order','-o',str(exe),
                                    str(PKG),str(src),str(DECODE),str(TB)],capture_output=True,text=True)
            if build.returncode:
                raise RuntimeError(build.stderr)
            run = subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
            correct = (run.returncode==0 and 'ENGRAM_STATUS PASS' in run.stdout) if name=='control' else (
                run.returncode!=0 and 'premature ready before delayed statuses' in run.stdout)
            rec['cases'][name]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,
                                    expected_observed=correct)
    rec['status']='pass' if all(c['expected_observed'] for c in rec['cases'].values()) else 'fail'
    if OUT.exists():
        raise FileExistsError('immutable gate evidence exists')
    OUT.write_text(json.dumps(rec,indent=1)+'\n')
    print(rec['status'])
    return 0 if rec['status']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
