#!/usr/bin/env python3
"""Released full-map and bounded lead producer exact gate; retain build objects."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from engram_token_map_image import prepare
R=Path(__file__).resolve().parents[1]
paths=[*[R/'rtl/dsrom_sys/engram'/p for p in ['ot_dsrom_engram_token_map.sv','ot_dsrom_engram_lead_producer.sv','ot_dsrom_engram_idwin.sv']],R/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v',R/'rtl/test/tb_dsrom_engram_lead.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
def main():
    out=R/'results/rtl/engram_lead_gate_20261009.json'
    if out.exists():raise FileExistsError(out)
    work=Path(tempfile.mkdtemp(prefix='engram-lead-'));images=work/'images';model=prepare(images)
    rec=dict(schema='opentallas.engram-lead-gate.v1',retained_objects=str(work),model=model,cases={},input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',R/'tools/engram_token_map_image.py',Path(__file__)]})
    obj=work/'obj';top='tb_dsrom_engram_lead'
    build=subprocess.run(['verilator','--timing','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
    (work/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise RuntimeError(build.stderr[-3000:])
    for mode in range(5):
        run=subprocess.run([str(obj/f'V{top}'),f'+MODE={mode}',f'+OT_ROM_DIR={images}'],capture_output=True,text=True)
        rec['cases'][str(mode)]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and ('ENGRAM_LEAD NEG' if mode else 'ENGRAM_LEAD PASS') in run.stdout)
    rec['status']='pass' if all(c['expected_observed'] for c in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
