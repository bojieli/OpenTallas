#!/usr/bin/env python3
"""Source resource compiler plus actual mapped-SRAM/controller/front/ring gate."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
MACRO='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/'
EXTRA_SOURCES=['rtl/qwen_sys/static_kv_20261014/qkd_kv_delta_calendar.sv',
 'rtl/qwen_sys/static_kv_20261014/qkd_kv_compact_reader.sv',
 'rtl/test/qwen_static_kv/tb_qkd_kv_compact_boundary.sv',
 MACRO+'ot_sram_1r1w_128x256_m1_r2c2.v']

def prepare(out,program,plan,stages):
    from qwen_static_kv.compact_reader_image import compile_images
    from qwen_static_kv.check_replay_boundary import PATHS
    sources=[p for p in PATHS if not p.endswith(('tb_qkd_kv_replay_boundary.sv','qkd_kv_calendar_replay.sv'))]+EXTRA_SOURCES
    out.mkdir(parents=True,exist_ok=False)
    for phase in (137,637):compile_images(program,plan,out/f'p{phase}',stages=stages,phase=phase)
    for p in sources:
        d=out/'source'/p;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,d)
    for p in ('tools/qwen_static_kv/reader_resource_schedule.py','tools/qwen_static_kv/compact_reader_image.py','tools/qwen_static_kv/check_compact_reader.py'):
        d=out/'compiler'/Path(p).name;d.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/p,d)
    (out/'actual_program.hex').write_bytes(program);(out/'actual_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'source_manifest.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},indent=2)+'\n')
    shutil.copy2(__file__,out/'execute.py')

def execute(out,mutants=False):
    manifest=json.loads((out/'source_manifest.json').read_text())
    for p,s in manifest.items():
        if hashlib.sha256((out/'source'/p).read_bytes()).hexdigest()!=s:raise RuntimeError('source SHA mismatch '+p)
    sources=[str(out/'source'/p) for p in manifest];top='tb_qkd_kv_compact_boundary';runs=[]
    for mut in (range(5) if mutants else [0]):
        obj=out/f'obj{mut}'
        with (out/f'build{mut}.log').open('w') as log:
            subprocess.run(['verilator','--binary','--timing','-Wno-fatal','-j','2',f'-I{out}/p137',
               '--top-module',top,f'-GMUT={mut}','--Mdir',str(obj),*sources],stdout=log,stderr=subprocess.STDOUT,check=True)
        for phase,jit in ([(137,0),(137,16),(637,16)] if mut==0 else [(137,16)]):
            name=f'm{mut}_p{phase}_j{jit}'
            r=subprocess.run([str(obj/('V'+top)),f'+image={out}/p{phase}',f'+phase={phase}',f'+jit={jit}'],capture_output=True,text=True)
            text=r.stdout+r.stderr;(out/(name+'.log')).write_text(text)
            good=r.returncode==0 and 'PASS compact mapped-SRAM' in text
            rejected=r.returncode!=0 and 'BOUNDARY_FAIL' in text
            runs.append(dict(name=name,returncode=r.returncode,pass_observed=good,mutant_rejected=rejected,
              measure=next((l for l in text.splitlines() if l.startswith('MEASURE')),None)))
            if (not good if mut==0 else not rejected):
                (out/'partial.json').write_text(json.dumps(runs,indent=2)+'\n');raise RuntimeError('actual gate failed '+name)
    report=dict(status='PASS_SOURCE_READ_ONLY_HARDWARE_PROGRAMME',source_sha256=manifest,runs=runs,
      gate_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      production_installable=False,physical_qualified=False,full_token_qualified=False,
      scope='actual mapped SRAM bytecode drives PROFILE0 controller/front/ring; full512/stage, persistent native reader state. Actual HOST/write/landing/consumer/physical join still OPEN.')
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(runs),'cases')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--program',type=Path);p.add_argument('--plan',type=Path)
    p.add_argument('--stages',type=int,default=36);p.add_argument('--prepare-only',action='store_true');p.add_argument('--execute-only',action='store_true');p.add_argument('--mutants',action='store_true')
    a=p.parse_args();a.out=a.out.resolve()
    if not a.execute_only:prepare(a.out,a.program.read_bytes(),json.loads(a.plan.read_text()),a.stages)
    if not a.prepare_only:execute(a.out,a.mutants)
