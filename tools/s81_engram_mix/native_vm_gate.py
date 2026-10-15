#!/usr/bin/env python3
"""Source-bound native MIX4 + READ_PIPE4 VM128 gate. Default emits a build plan.

Run --execute only in a coordinator-approved ot-run allocation after checking the
EPYC queue and staging the coherent sources plus CPU fixture onto that machine.
No scheduler, daemon, flow or cache state is modified by this runner.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TOP='tb_s81_engram_mix4_native_vm'
VARIANTS={'base':(0,[]),'key':(1,[]),'copy':(2,[]),'stale_v':(3,[]),
          'vm_slot':(0,['OT_VM_RSCHED_MUT_MIXSLOT']),
          'vm_commit':(0,['OT_VM_BANK_MUT_EARLY_COMMIT'])}
LOCK=Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
def coordinator():
    # A staged remote run carries a byte-for-byte copy via --coordinator-lock.
    d=json.loads(LOCK.read_text())
    if str(d.get('owner','')).lower()!='codex':raise SystemExit('STOP: coordinator is not codex')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources(root, macro):
    tree=ast.parse((root/'tools/s81_suhc/hc_gate.py').read_text())
    rtl=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RTL' for t in n.targets))
    fp=['rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_f12.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv']
    names=re.search(r'FILES="([^"]+)"',(root/'tools/s81_vm/static_core_gate.sh').read_text()).group(1).split()
    paths=[root/x for x in fp+[x for x in rtl if '/hdc/' in x]]
    paths += [root/'rtl/dsrom_sys/s81_ph/vm'/n for n in names if n not in ('tb_dsfd_vm_static_core.sv','ot_sram_1r1w_512x128_m4_r2c2.v')]
    paths += [macro]
    paths += [root/x for x in ['rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv','rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv','rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']]
    paths += [ROOT/'rtl/dsrom_sys/engram/mix'/f'{TOP}.sv']
    return list(dict.fromkeys(paths))
def main():
    global LOCK
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--fixture-dir',type=Path,required=True);p.add_argument('--macro',type=Path)
    p.add_argument('--execute',action='store_true');p.add_argument('--lint-only',action='store_true')
    p.add_argument('--variants',nargs='+',choices=VARIANTS,default=list(VARIANTS))
    p.add_argument('--reuse-base-objects',action='store_true',help='Deep-copy completed base build as an incremental build seed; every variant still rebuilds and runs')
    p.add_argument('--jobs',type=int,default=1);p.add_argument('--define',action='append',default=[]);p.add_argument('--write-scatter-pipe',type=int,choices=(0,1),default=1);p.add_argument('--coordinator-lock',type=Path,default=LOCK)
    p.add_argument('--verilator',default=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
    a=p.parse_args();LOCK=a.coordinator_lock;coordinator()
    root=a.source_root.resolve();out=a.out.resolve();fixture=a.fixture_dir.resolve()
    macro=(a.macro or root/'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v').resolve()
    src=sources(root,macro)
    missing=[str(x) for x in src if not x.is_file()]
    if missing:raise SystemExit('Missing source files: '+json.dumps(missing))
    for name in ('cfg','h','k','w','v','y'):
        if not (fixture/f'{name}.mem').is_file():raise SystemExit(f'Missing CPU fixture {name}.mem')
    manifest={'schema':'opentallas.s81.engram.native-vm-plan.v1','scope':'Native RTL arithmetic, READ_PIPE4 VM with 128 functional SRAM models; external SU preload and SRAM readback',
        'source_sha256':{str(x):sha(x) for x in src},'fixture_sha256':{x.name:sha(x) for x in fixture.glob('*.mem')},
        'read_latency_elapsed_edges':16,'returned_commit_latency_elapsed_edges':11+a.write_scatter_pipe,'rs':5,
        'expected':dict(mix_reads=4161,mix_writes=640,answers=20480,preload_rows=3521,su_readback_rows=640),'variants':{},'executed':False}
    for name in a.variants:
        mut,defines=VARIANTS[name];obj=out/f'obj_{name}'
        cmd=[a.verilator,'--lint-only' if a.lint_only else '--binary','--timing','-O1','-Wno-fatal','--top-module',TOP,'--Mdir',str(obj),'-j',str(a.jobs),'-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0',f'-GMUT={mut}',f'-GWSCATTER_PIPE={a.write_scatter_pipe}',f'-GWRITE_COMMIT_LAT={11+a.write_scatter_pipe}',*[f'+define+{d}' for d in defines+a.define],*map(str,src)]
        manifest['variants'][name]={'build':cmd,'run':[str(obj/f'V{TOP}'),f'+dir={fixture}'],'expected_pass':name=='base'}
    coordinator();out.mkdir(parents=True,exist_ok=True)
    (out/'native_vm_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if not a.execute:print(json.dumps({'plan':str(out/'native_vm_manifest.json'),'executed':False}));return
    def unchanged():
        if any(sha(Path(x))!=h for x,h in manifest['source_sha256'].items()):raise SystemExit('STOP: source changed during gate')
        if any(sha(fixture/x)!=h for x,h in manifest['fixture_sha256'].items()):raise SystemExit('STOP: fixture changed during gate')
    for name,v in manifest['variants'].items():
        coordinator();unchanged()
        obj=out/f'obj_{name}'
        if a.reuse_base_objects and name!='base' and not obj.exists():
            seed=out/'obj_base'
            if not (seed/f'V{TOP}').is_file():raise SystemExit('Missing completed base build seed')
            shutil.copytree(seed,obj) # Independent files: never hardlink mutable generated C++/objects.
            v['incremental_seed']=str(seed)
        with (out/f'build_{name}.log').open('w') as f:r=subprocess.run(v['build'],stdout=f,stderr=subprocess.STDOUT)
        unchanged()
        if r.returncode:raise SystemExit(f'BUILD FAIL {name}; see {out}/build_{name}.log')
        if a.lint_only:continue
        coordinator()
        with (out/f'run_{name}.log').open('w') as f:r=subprocess.run(v['run'],stdout=f,stderr=subprocess.STDOUT)
        unchanged()
        log=(out/f'run_{name}.log').read_text();passed=r.returncode==0 and 'PASS MIX4_NATIVE_VM128' in log
        rejected=r.returncode!=0 and any(x in log for x in ['DUT fault','mismatch','commit count'])
        if (name=='base' and not passed) or (name!='base' and not rejected):raise SystemExit(f'GATE FAIL {name}; see {out}/run_{name}.log')
        v.update(returncode=r.returncode,pass_marker=passed,mutant_rejected=rejected)
    manifest['executed']=True;manifest['lint_only']=a.lint_only
    coordinator();(out/'native_vm_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('NATIVE_VM_LINT PASS' if a.lint_only else 'NATIVE_VM_GATE PASS')
if __name__=='__main__':main()
