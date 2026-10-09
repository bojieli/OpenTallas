#!/usr/bin/env python3
"""Minimum full-shape selector/candidate exactness gate for macro capture."""
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import rtl_hdc_v41x_sel_campaign as S
import rtl_hdc_v41x_sel_cand_campaign as C
ROOT = Path(__file__).resolve().parents[1]

def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    # Execute the authoritative unified-model function before elaboration.
    node = next(n for n in ast.parse((ROOT/'tools/uarch_model.py').read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == 'hbm_index_selector_capture_model')
    ns = {}; exec(compile(ast.Module(body=[node], type_ignores=[]), 'uarch_model.py', 'exec'), ns)
    model = ns[node.name](2)
    (out/'model.json').write_text(json.dumps(model, indent=2)+'\n')
    sources = list(dict.fromkeys(C.RTL + [S.TB, C.TB, S.HARNESS, C.HARNESS,
        ROOT/'tools/uarch_model.py', Path(__file__)]))
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    rng = np.random.default_rng(20261009)
    jobs = []
    for name, campaign, k, aw in [('selector', S, 512, 8), ('candidate', C, 2048, 10)]:
        segs=[]
        # Continuous requests, empty quarters, ties, GC, P2/P3 flush and stalled emit.
        for n, fam in [(1,'all_equal'), (10944,'ties'), (50000,'normal'), (50000,'ascending'), (64,'masked')]:
            b=S.family(rng,fam,n,k)
            segs.append(S.segment(rng,b,k,k,4,16,'even',True) if name=='selector'
                        else C.segment(rng,b,k,16,K=k))
        pfx, _ = campaign.write_vectors(segs,4,16,out,name)
        for lat, memlat in [(1,1),(2,2),(1,2)]: jobs.append((name,campaign,k,aw,pfx,lat,memlat))
    def run(job):
        name, camp,k,aw,pfx,lat,memlat=job
        tag=f'{name}_r{lat}_m{memlat}'; obj=out/tag; obj.mkdir()
        top='tb_hdc_v41x_sel'+('_cand' if name=='candidate' else '')
        cmd=[S.VERILATOR,'--cc','--exe','--build','-j','4','-O2','-Wno-fatal','--top-module',top,
             '-GQ=4', ('-GSL=16' if name=='candidate' else '-GW=16'), '-GIW=20',f'-GK={k}',f'-GAW={aw}',
             '-GMAXB=8192',f'-GREADLAT={lat}',f'-GMEMLAT={memlat}','-Mdir',str(obj),
             *map(str,camp.RTL),str(camp.TB),str(camp.HARNESS),'-CFLAGS','-O1']
        build=subprocess.run(cmd,capture_output=True,text=True)
        (obj/'compile.log').write_text(build.stdout+build.stderr)
        if build.returncode: return dict(tag=tag, build_exit=build.returncode, pass_gate=False)
        runs=[]
        for bubble,stall in [(0,0),(17,80)]:
            r=subprocess.run([str(obj/('V'+top)),f'+PFX={pfx}',f'+BUBBLE={bubble}',f'+ORDY={stall}',
                              '+SEED=9','+MAXCYC=2000000'],capture_output=True,text=True)
            (obj/f'run_{bubble}_{stall}.log').write_text(r.stdout+r.stderr)
            parsed=S.parse(r.stdout.replace('V41XSELC ','V41XSEL '))
            runs.append(dict(bubble=bubble,stall=stall,exit=r.returncode,**parsed))
        good=all(r['pass'] for r in runs)
        return dict(tag=tag,negative_control=lat!=memlat,runs=runs,pass_gate=(not good if lat!=memlat else good))
    with ThreadPoolExecutor(max_workers=2) as pool: rows=list(pool.map(run,jobs))
    evidence=dict(source_sha256=pins, model=model, rows=rows,pass_gate=all(r['pass_gate'] for r in rows),
                  scope='full-shape isolated selector/candidate; behavioural memory with explicit capture; not macro timing or die closure')
    (out/'gate.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'pass_gate':evidence['pass_gate'],'rows':[{k:v for k,v in r.items() if k!='runs'} for r in rows]}))
    return 0 if evidence['pass_gate'] else 1
if __name__=='__main__': sys.exit(main())
