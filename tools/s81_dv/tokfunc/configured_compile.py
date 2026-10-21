#!/usr/bin/env python3
"""Stage the selected G9 source overlay; lint/elaborate only, never simulate."""
import argparse
import hashlib
import json
import re
import subprocess
import tarfile
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def spans(text):
    # Mask comments and strings without moving offsets; never rewrite a chosen
    # module body. Projection only removes overridden companion definitions.
    masked=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',lambda m:''.join('\n' if c=='\n' else ' ' for c in m[0]),text,flags=re.S)
    return [(m[1],m.start(),m.end()) for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',masked,re.S)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['basis-kit','local-cone','manifest','override-tar','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--stage-only',action='store_true')
    p.add_argument('--resume-staged',action='store_true')
    a=p.parse_args()
    for n in ['basis_kit','local_cone','manifest','override_tar','out']:setattr(a,n,getattr(a,n).resolve())
    m=json.loads(a.manifest.read_text());assert sha(a.manifest)=='120ce473f90bddeb40ee35c4fe28cf7ec3ab3b127f46fc95351d97cf4da66b75'
    assert m['selected_source_ref']=='8a495768f02316a7a8ad2e2bafef2f4d3741b741'
    assert m['defines']==['DSFD_PQ_STATIC_X2','OT_COLL_NATIVE32','OT_COLL_NATIVE32_OFF','S81CTRL_SRAM_FIFO','S81CTRL_SRAM_P192','S81CTRL_NATIVE32']
    kit=json.loads((a.basis_kit/'kit.json').read_text());assert sha(a.basis_kit/'kit.json')=='45b62b506148366e284a49cc767f4b5f8b540a6f2575f7c278bb00cbe2d9e94f'
    assert not kit['problems'] and len(kit['files'])==179
    top=a.local_cone/'cut/s0N_aggregate.sv';cone=json.loads((a.local_cone/'local_cone.json').read_text())
    assert sha(top)==cone['local_cone_sv_sha256']==kit['top_sha256']
    if a.resume_staged:
        receipt=json.loads((a.out/'receipt.json').read_text());assert receipt['status']=='STAGED_COMPILE_ONLY_NOT_EXECUTED'
        assert receipt['manifest_sha256']==sha(a.manifest) and receipt['runner_sha256']==sha(Path(__file__))
        for rel,h in receipt['staged_files_sha256'].items():assert sha(a.out/rel)==h,('staged source drift',rel)
    else:
        a.out.mkdir(parents=True,exist_ok=False)
        pool={};origins={}
        for f in kit['files']:
            path=a.basis_kit/'src'/f['path'];assert sha(path)==f['sha256']
            pool[f['path']]=path.read_bytes();origins[f['path']]=dict(kind='exact recorded PB basis',sha256=f['sha256'],origin=f['origin'])
        overrides={}
        with tarfile.open(a.override_tar) as archive:
            for item in archive.getmembers():
                if item.isdir():continue
                assert item.isfile() and not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
                assert item.name in m['explicit_override_sha256'],('unselected override',item.name)
                payload=archive.extractfile(item).read();assert digest(payload)==m['explicit_override_sha256'][item.name]
                overrides[item.name]=payload
        assert set(overrides)==set(m['explicit_override_sha256']) and len(overrides)==27
        override_names={name for text in overrides.values() for name,lo,hi in spans(text.decode())}
        projections={}
        for rel,payload in list(pool.items()):
            if rel in overrides:continue
            text=payload.decode();remove=[(n,lo,hi) for n,lo,hi in spans(text) if n in override_names]
            if remove:
                projections[rel]=dict(original_file_sha256=digest(payload),removed_companion_bodies={n:digest(text[lo:hi].encode()) for n,lo,hi in remove},
                    reason='explicit selected canonical override wins; selected bodies copied verbatim, no RTL logic edits')
                for name,lo,hi in reversed(remove):text=text[:lo]+''.join('\n' if c=='\n' else ' ' for c in text[lo:hi])+text[hi:]
                pool[rel]=text.encode()
        for rel,payload in overrides.items():
            pool[rel]=payload;origins[rel]=dict(kind='explicit owner-selected override',sha256=digest(payload),origin=m['explicit_override_ref'])
        for rel,payload in pool.items():
            dest=a.out/'src'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload)
        dest=a.out/'src/top/s0N_aggregate.sv';dest.parent.mkdir(parents=True);dest.write_bytes(top.read_bytes())
        # The old file list decides include-vs-compilation-unit treatment;
        # explicit selected overrides are compilation units, including the
        # exact physical macro API declaration. No functional macro claim.
        units=[]
        for line in (a.basis_kit/'kit.f').read_text().splitlines():
            if line.startswith('src/') and not line.startswith('src/top/'):units.append(line[4:])
        units=list(dict.fromkeys([*overrides,*units]))
        includes=sorted({str((a.out/'src'/rel).parent) for rel in pool})
        lines=['+incdir+'+d for d in includes]+['+define+'+d for d in m['defines']]+[str(a.out/'src'/r) for r in units]+[str(dest)]
        (a.out/'compile.f').write_text('\n'.join(lines)+'\n')
        inventory={str(path.relative_to(a.out)):sha(path) for path in a.out.rglob('*') if path.is_file()}
        receipt=dict(schema='opentallas.s81.g9_configured_compile_only.v1',status='STAGED_COMPILE_ONLY_NOT_EXECUTED',
            runner_sha256=sha(Path(__file__)),manifest_sha256=sha(a.manifest),selected_source_ref=m['selected_source_ref'],
            basis_kit_sha256=sha(a.basis_kit/'kit.json'),basis_files=179,override_files=27,
            source_origins=origins,projections=projections,staged_files_sha256=inventory,defines=m['defines'],
            actual_top_sha256=sha(top),actual_top_clock_ports=cone['clock_inputs'],local_cone_sha256=sha(a.local_cone/'local_cone.json'),
            tops={'s0N_aggregate':dict(params={},scope='unchanged actual0N/sixh9 cone, all actual clocks/forwarded paths/returns'),
                'ot_s81sl_slice_kv512':dict(params=m['tops']['kv_top_params'],child_params=m['tops']['kv_child_params'],clock_reset=m['tops']['kv_clock_reset'])},
            physical_macro_BB_scope='exact selected 16x340_p192 macro port declaration supports compile/API check only, no functional simulation',
            compiler_or_simulator_run=False,simulation_forbidden=True,G8_equivalence_claimed=False,
            global_programme_qualified=False,physical_adoption=False,cases={})
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
        print('STAGED',len(pool),'source files',len(projections),'companion projections',flush=True)
    if a.stage_only:return
    verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    receipt.update(status='ELABORATING_COMPILE_ONLY',compiler_or_simulator_run='Verilator lint/elaboration only; no binary/C++ compiler/simulator')
    def save():(a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    save()
    for topname in receipt['tops']:
        output=a.out/(topname+'_obj');log=a.out/(topname+'_elab.log')
        argv=[str(verilator),'--lint-only','--timing','-Wno-fatal','-Wno-WIDTH','--top-module',topname,'-Mdir',str(output),'-f',str(a.out/'compile.f')]
        with log.open('w') as stream:result=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT)
        text=log.read_text();receipt['cases'][topname]=dict(argv=argv,exit_code=result.returncode,rawlog_sha256=sha(log),
            errors=[line for line in text.splitlines() if line.startswith('%Error')],warnings=[line for line in text.splitlines() if line.startswith('%Warning')])
        save()
        if result.returncode:receipt['status']='COMPILE_ELAB_FAIL';save();raise SystemExit(1)
    receipt['status']='CONFIGURED_COMPILE_ELAB_PASS_NO_RUNTIME';save();print(receipt['status'])


if __name__=='__main__':main()
