#!/usr/bin/env python3
"""Negative gates on actual primitive body; keep mutant evidence distinct."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.work.mkdir(parents=True,exist_ok=False)
    raw=(ROOT/'rtl/common/ot_meso_fifo.sv').read_text()
    cases=[('wrong_slot','od<=mem[rp_next[AW-1:0]]','od<=mem[rp_next[AW-1:0]^1\'b1]','stall'),
           ('early_credit','if(pop)begin rp<=rp_next;','if(r_live)begin rp<=rp+1\'b1;','stall'),
           ('monitor_removed',"wire w_bad=(ws==RUN)","wire w_bad=1'b0 && (ws==RUN)",'drift')]
    records=[]
    for name,old,new,mode in cases:
        assert raw.count(old)==1
        source=raw.replace(old,new)
        if name=='monitor_removed':source=source.replace('wire r_bad=(rs==RUN)',"wire r_bad=1'b0 && (rs==RUN)")
        w=a.work/name;w.mkdir();rtl=w/'mutant.sv';rtl.write_text(source)
        cmd=['verilator','--cc','--exe','--build','-j','2','-O3','-Wno-fatal','--top-module','ot_meso_fifo','-GENABLE=1','-GW=512','-GDEPTH=4',str(rtl),str(ROOT/'rtl/test/rom_clock/tb_meso.cpp'),'-Mdir',str(w/'obj'),'-o','bench']
        build=subprocess.run(cmd,capture_output=True,text=True);(w/'build.log').write_text(build.stdout+build.stderr)
        if build.returncode:raise RuntimeError(name+' mutant did not build')
        result=subprocess.run([str(w/'obj/bench'),'5000',mode,'2000'],capture_output=True,text=True)
        records.append(dict(name=name,mutant_sha256=hashlib.sha256(rtl.read_bytes()).hexdigest(),returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,detected=result.returncode!=0))
    a.out.write_text(json.dumps(dict(status='PASS_NEGATIVE_GATES' if all(r['detected'] for r in records) else 'FAIL',runs=records),indent=2)+'\n')
    if not all(r['detected'] for r in records):raise SystemExit(1)
if __name__=='__main__':main()
