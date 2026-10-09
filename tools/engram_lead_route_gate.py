#!/usr/bin/env python3
"""Bind approved unchanged lead765 payload/stall/DEAD/rewind gate and mutants to geometry recipe."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from engram_token_map_image import prepare
R=Path(__file__).resolve().parents[1]
paths=[*[R/'rtl/dsrom_sys/engram'/p for p in ['ot_dsrom_engram_token_map.sv','ot_dsrom_engram_lead_producer.sv','ot_dsrom_engram_idwin.sv']],R/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v',R/'rtl/test/tb_dsrom_engram_lead.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
def main():
    out=R/'results/rtl/engram_lead765_route_gate_20261009.json'
    if out.exists():raise FileExistsError(out)
    work=Path(tempfile.mkdtemp(prefix='engram-lead765-route-'));images=work/'images';prepare(images)
    rec=dict(schema='opentallas.engram-lead765-route-gate.v1',source_commit='765470589',physical_job='engram-lead-765470589-tt',successor='unchanged RTL geometry repair only; review before intake',retained_objects=str(work),input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},cases={})
    variants=[('control',None,None,None),('dead_mask_removed',1,'.t_dead(dead)',".t_dead(1'b0)"),('rewind_pointer_removed',2,'<= rwp - rb_n;','<= rwp;'),('output_hold_removed',1,'if(out_v && out_ready) out_v<=0;','if(out_v) out_v<=0;')]
    top='tb_dsrom_engram_lead'
    for name,index,old,new in variants:
        sources=list(paths);obj=work/name
        if index is not None:
            original=paths[index].read_text()
            if original.count(old)!=1:raise ValueError(f'{name}: expected single mutation site')
            mutant=work/f'{name}.sv';mutant.write_text(original.replace(old,new));sources[index]=mutant
        b=subprocess.run(['verilator','--timing','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in sources],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
        (work/f'{name}.build.log').write_text(b.stdout+b.stderr)
        if b.returncode:raise RuntimeError(b.stderr[-3000:])
        for mode in (range(5) if index is None else [0]):
            r=subprocess.run([str(obj/f'V{top}'),f'+MODE={mode}',f'+OT_ROM_DIR={images}'],capture_output=True,text=True)
            expected=(r.returncode==0 and ('ENGRAM_LEAD NEG' if mode else 'ENGRAM_LEAD PASS') in r.stdout) if index is None else r.returncode!=0 and any(s in r.stdout for s in ['lead mismatch','stalled lead changed'])
            rec['cases'][f'{name}_{mode}']=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,expected_observed=expected)
    rec['status']='pass' if all(c['expected_observed'] for c in rec['cases'].values()) else 'fail';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
