#!/usr/bin/env python3
"""Source-pinned minimum Engram boot/marker gate; execute on admitted remote host."""
import argparse
import ast
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
OUT = ROOT/'results/rtl/engram_boot_dispatch_gate_20261009.json'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=OUT)
    a=ap.parse_args()
    if a.output.exists():
        raise FileExistsError('immutable boot gate record exists')
    import numpy as np
    import rtl_rom_host_ingest_bench as H
    import rtl_hdc_kv_ingest_campaign as C
    rtl=ROOT/'rtl/dsrom_sys/engram/ot_dsrom_engram_boot_dispatch.sv'
    tb=ROOT/'rtl/test/tb_dsrom_engram_boot_dispatch.sv'
    model=ROOT/'tools/uarch_model.py'
    tree=ast.parse(model.read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dsrom_engram_boot_dispatch_model')
    scope={}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(model),'exec'),scope)
    paths=[rtl,tb,model,Path(__file__),ROOT/'tools/engram_boot_image.py',H.TB,*H.RTL,
           ROOT/'tools/rtl_rom_host_ingest_bench.py',ROOT/'tools/rtl_hdc_kv_ingest_campaign.py',ROOT/'tools/kv_ingest_ref.py']
    rec=dict(schema='opentallas.engram-boot-gate.v1',
             claim_boundary='scoped dispatch, finite tagged writes and marker CDC; actual controller read/write mapping, die integration and physical closure pending',
             input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
             model=scope['dsrom_engram_boot_dispatch_model'](),cases={})
    with tempfile.TemporaryDirectory(prefix='engram-boot-') as tmp:
        work=Path(tmp)
        exe=work/'dispatch.vvp'
        build=subprocess.run(['iverilog','-g2012','-s','tb_dsrom_engram_boot_dispatch','-o',str(exe),str(rtl),str(tb)],
                             capture_output=True,text=True)
        if build.returncode:
            raise RuntimeError(build.stderr)
        for mode,name in enumerate(['control','stale_count','swapped_class','bad_fingerprint','duplicate_completion']):
            run=subprocess.run(['vvp',str(exe),f'+MODE={mode}'],capture_output=True,text=True)
            want='ENGRAM_BOOT PASS' if mode==0 else 'ENGRAM_BOOT NEG'
            rec['cases'][name]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,
                                    expected_observed=run.returncode==0 and want in run.stdout)
        case=C.case_raw(np.random.default_rng(12),300)
        case['nb']=H.stream_nb(case['descs'])
        memw=len(case['exp'])//32
        H.write_case(work,case,memw)
        hostexe=H.build(work,'host',memw,len(case['descs']),len(case['beats']),16,1,0)
        for region in [0,3]:
            result=H.run(hostexe,work,len(case['descs']),len(case['beats']),
                         BOOTEND=1,BCOUNT=300,BREG=region,MSTALL=40,HGAP=30)
            rec['cases'][f'marker_region_{region}']=dict(result,expected_observed=result['pass'])
        host=ROOT/'rtl/hdc/ingest/ot_rom_host_ingest.sv'
        text=host.read_text()
        needle="190'd0, hx_head[129:64]"
        assert text.count(needle)==1
        mutant=work/'host_drop_region.sv';mutant.write_text(text.replace(needle,"192'd0, hx_head[127:64]"))
        H.RTL=[mutant if p==host else p for p in H.RTL]
        mutexe=H.build(work,'hostmut',memw,len(case['descs']),len(case['beats']),16,1,0)
        result=H.run(mutexe,work,len(case['descs']),len(case['beats']),BOOTEND=1,BCOUNT=300,BREG=3,MSTALL=40,HGAP=30)
        rec['cases']['marker_region_dropped']=dict(result,expected_observed=(not result['pass'] and result['boot_end_marker_errors']==1))
    rec['status']='pass' if all(v['expected_observed'] for v in rec['cases'].values()) else 'fail'
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(rec['status'])
    return 0 if rec['status']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
