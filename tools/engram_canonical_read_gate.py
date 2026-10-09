#!/usr/bin/env python3
"""Actual full32-PC HBM timing models; canonical counts/map/stalls/SECDED."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[R/'rtl/dsrom_sys/engram/ot_dsrom_engram_rowstripe_read.sv',R/'rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv',R/'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',R/'rtl/test/tb_dsrom_engram_canonical_read.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
out=R/'results/rtl/engram_canonical_read_gate_20261009.json'
def main():
    if out.exists():raise FileExistsError(out)
    rec=dict(schema='opentallas.engram-canonical-read-gate.v1',boundary='six reserved rows, actual two32PC timing-model vehicles, count semantics, all4burst start offsets, perbeatPC/edge/bounds, stalls and SECDED; fixture aperture conditional; no physical/die qualification',input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',Path(__file__)]},cases={})
    work=Path(tempfile.mkdtemp(prefix='engram-canonical-read-'));rec['retained_objects']=str(work)
    top='tb_dsrom_engram_canonical_read'
    for inject in [0,4,5]:
        obj=work/f'obj{inject}'
        b=subprocess.run(['verilator','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,f'-GINJECT={inject}','-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
        if b.returncode:raise RuntimeError(b.stderr[-3000:])
        for mode in ([0,1,2,3,4] if inject==0 else [0]):
            run=subprocess.run([str(obj/f'V{top}'),f'+MODE={mode}'],capture_output=True,text=True)
            wanted='ENGRAM_CANONICAL_READ NEG' if mode else 'ENGRAM_CANONICAL_READ ECC double caught' if inject==5 else 'ENGRAM_CANONICAL_READ PASS'
            rec['cases'][f'inject{inject}_mode{mode}']=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and wanted in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
