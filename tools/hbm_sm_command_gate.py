#!/usr/bin/env python3
"""Minimum command ingress/credit proof; preserves all pinned SM RTL."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from hbm_sm_command_model import model
ROOT=Path(__file__).resolve().parents[1]
RTL='rtl/hbm_accel/control_20261007/ot_hbm_sm_seq_ingress.sv'
TB='rtl/hbm_accel/control_20261007/tb_sm_seq_ingress.sv'
DEPS=['rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv']
def pack_record(words):
    """Read the same ten 32-bit seq.hex words without invented instruction fields."""
    if len(words)!=10 or any(not 0<=x<2**32 for x in words): raise ValueError('ten unsigned words required')
    return sum(x<<(32*i) for i,x in enumerate(words))
def main():
    runs=[]
    with tempfile.TemporaryDirectory(prefix='hbm-sm-command-') as d:
        for hops,mut in [(0,None),(1,None),(8,None),(40,None),(81,None),(8,'zero_xb'),(8,'ignore_publication')]:
            src=(ROOT/RTL).read_text()
            if mut=='zero_xb':src=src.replace('seq_data[294:288]',"7'd0")
            if mut=='ignore_publication':src=src.replace(' && operand_published','')
            p=Path(d)/'dut.sv';p.write_text(src);binary=Path(d)/'sim'
            subprocess.run(['iverilog','-g2012','-s','tb_sm_seq_ingress',f'-Ptb_sm_seq_ingress.HOPS={hops}','-o',str(binary),str(p),str(ROOT/TB),*[str(ROOT/x) for x in DEPS]],check=True)
            r=subprocess.run(['vvp',str(binary)],capture_output=True,text=True)
            if (r.returncode==0)!=(mut is None):raise RuntimeError(r.stdout)
            runs.append(dict(hops=hops,mutation=mut,returncode=r.returncode,output=r.stdout.strip()))
    print(json.dumps(dict(scope='component only; no complete native program/loader binding or physical qualification',
        model=model(),runs=runs,sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [RTL,TB,*DEPS]},passed=True),indent=2))
if __name__=='__main__':main()
