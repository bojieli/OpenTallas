#!/usr/bin/env python3
"""Actual timing-model boot/read composition, phase fence, bounded PC leases."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[*[R/'rtl/dsrom_sys/engram'/x for x in ['ot_dsrom_engram_hbm_backend.sv','ot_dsrom_engram_boot_path.sv','ot_dsrom_engram_boot_dispatch.sv','ot_dsrom_engram_boot_ctrl_map.sv','ot_dsrom_engram_rowstripe_service.sv','ot_dsrom_engram_rowstripe_read.sv']],R/'rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv',R/'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',R/'rtl/test/tb_dsrom_engram_hbm_backend.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
out=R/'results/rtl/engram_hbm_backend_gate_20261009.json'
def main():
    if out.exists():raise FileExistsError(out)
    rec=dict(schema='opentallas.engram-hbm-backend-gate.v1',boundary='576 boot writes+marker then6runtime rows at actual two32PC timing models, registered phase fence and stalled PCgrant/claim/release; fixture aperture, no concurrent KV arbiter/die/physical qualification',input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',Path(__file__)]},cases={})
    work=Path(tempfile.mkdtemp(prefix='engram-hbm-backend-'));rec['retained_objects']=str(work)
    obj=work/'obj';top='tb_dsrom_engram_hbm_backend'
    b=subprocess.run(['verilator','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
    (work/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise RuntimeError(b.stderr[-3000:])
    for mode in [0,1,2]:
        run=subprocess.run([str(obj/f'V{top}'),f'+MODE={mode}'],capture_output=True,text=True)
        wanted='ENGRAM_BACKEND NEG' if mode else 'ENGRAM_BACKEND PASS'
        rec['cases'][f'mode{mode}']=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and wanted in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
