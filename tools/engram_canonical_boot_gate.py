#!/usr/bin/env python3
"""Class11 scoped boot through actual32PC timing models and count semantics."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[*[R/'rtl/dsrom_sys/engram'/x for x in ['ot_dsrom_engram_boot_path.sv','ot_dsrom_engram_boot_dispatch.sv','ot_dsrom_engram_boot_ctrl_map.sv']],R/'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',R/'rtl/test/tb_dsrom_engram_canonical_boot.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
out=R/'results/rtl/engram_canonical_boot_gate_20261009.json'
def main():
    if out.exists():raise FileExistsError(out)
    rec=dict(schema='opentallas.engram-canonical-boot-gate.v1',boundary='576 real write completions from actual two32PC timing models, payload/PC/canonical address/exclusive limits/scoped marker; fixture region conditional, no physical or installed capacity credit',input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',Path(__file__)]},cases={})
    work=Path(tempfile.mkdtemp(prefix='engram-canonical-boot-'));rec['retained_objects']=str(work)
    top='tb_dsrom_engram_canonical_boot'
    for mutant in [False,True]:
        sources=paths.copy()
        if mutant:
            text=paths[2].read_text();needle="(CANONICAL ? 4'd1 : 4'd0)";assert text.count(needle)==1
            src=work/'zero_len.sv';src.write_text(text.replace(needle,"4'd0"));sources[2]=src
        obj=work/('zero_len' if mutant else 'control')
        b=subprocess.run(['verilator','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in sources],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
        (work/(obj.name+'.build.log')).write_text(b.stdout+b.stderr)
        if b.returncode:raise RuntimeError(b.stderr[-3000:])
        for mode in ([2] if mutant else [0,1]):
            run=subprocess.run([str(obj/f'V{top}'),f'+MODE={mode}'],capture_output=True,text=True)
            wanted='ENGRAM_CANONICAL_BOOT NEG' if mode else 'ENGRAM_CANONICAL_BOOT PASS'
            rec['cases'][f'mutant{int(mutant)}_mode{mode}']=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and wanted in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
