#!/usr/bin/env python3
"""Link the single-store STREAM4 layer host with its REQUIRED native row hook.

Source/archives are supplied by their sole owners. This tool never builds RTL,
regenerates models, launches a DUT or supplies memory responses.
"""
import argparse
import json
from pathlib import Path
import subprocess
import qwen_rom_combined_link_source_defaults as retained
import qwen_rom_combined_nearbaseline_link as hierarchy
import qwen_rom_combined_stream4_access as access
import qwen_rom_combined_stream4_runtime_emit as emitter

ROOT=Path(__file__).resolve().parents[1]


def require_models(build,die,hbm, *, dspark=False):
    d,c,h,t=(retained.resolved_parameters(build,k) for k in ('die','coll','hbm','tile'))
    retained.require(all(d.get(k)==v for k,v in dict(G=6144,SW=64,NW=18,SNW=18,D=4,REAL_MEM=1,
                         NEAR_HBM=1,HBM_STREAM4=1,NSTK=4,WBW=4).items()), 'actual STREAM4 near die geometry required')
    retained.require(all(h.get(k)==v for k,v in dict(NSTK=4,NPC=128,TAGW=9,TTAGW=13).items()),
                     'actual single four-stack STREAM4 model required; old ACK models refused')
    retained.require(h['MEM_WORDS']==d['HBM_LAYERS']*131072 and h['CORE_FS']>=2 and h['CTL_FS']>0,
                     'compiled STREAM4 memory extent/clocks')
    retained.require(c.get('N')==4 and c.get('TAGW')==44, 'actual TAG44 collective required')
    top='ot_qwen_rom_combined_dspark_die' if dspark else emitter.TOP
    if dspark:
        retained.require(all(d.get(k)==v for k,v in dict(DSPARK=1,ACCEPT_COMMIT=1,VPMAX=4,VWA=16,
                         VM_ELEMS=1048576,NPROG=1024,NDESC=64).items()), 'actual ACCEPT_COMMIT1 VPOS model required')
    for directory,top in ((die,top),(hbm,'ot_qwen_hbm_stream4_tagged')):
        files=list(Path(directory).glob('*__verFiles.dat'))
        retained.require(any(top in p.read_text() for p in files), 'actual selected model top missing: '+top)
    # Preserve the generated hierarchy list checks with the new top explicitly.
    import re,shlex
    text=(die/'Vdie_hier.mk').read_text().replace('\\\n',' ')
    found=re.findall(r'^VM_HIER_LIBS\s*:=\s*(.*)$',text,re.MULTILINE)
    retained.require(len(found)==1, 'actual generated hierarchy required')
    names=shlex.split(found[0]);retained.require(len(names)==len(set(names)), 'duplicate hierarchy library')
    for name in ['Vdie__ALL.a',*names]:
        p=Path(name)
        retained.require(not p.is_absolute() and '..' not in p.parts and p.suffix=='.a','hierarchy archive path')
        with (die/p).open('rb') as stream:retained.require(stream.read(8)==b'!<arch>\n','missing actual archive')
    return d,c,h,t


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('die-build','hbm-build','coll-build','reuse-build','baseline','compiled-params','verilator-root','out','native-tagged-source'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--native-tagged-sha256',required=True)
    p.add_argument('--dspark',action='store_true')
    p.add_argument('--full-decoder',action='store_true')
    p.add_argument('--require-adopted',action='store_true')
    a=p.parse_args();retained.require(not a.full_decoder or a.dspark,'full decoder requires DSpark');retained.require(not a.out.exists(),'immutable output exists')
    retained.require(retained.sha(a.native_tagged_source)==a.native_tagged_sha256,
                     'required Claude native tagged-row source changed')
    build=json.loads(a.compiled_params.read_text());d,c,h,t=require_models(build,a.die_build,a.hbm_build,dspark=a.dspark)
    retained.require(not a.full_decoder or d['HBM_LAYERS']==36,'full decoder requires actual 36-layer HBM extent')
    if a.require_adopted:
        retained.require(a.dspark and a.full_decoder and d.get('SEQ_LA')==1 and
                         d.get('MP_COMMIT_NATIVE')==1,'final adopted host requires actual LA1/native MP commit model')
    top='ot_qwen_rom_combined_dspark_die' if a.dspark else emitter.TOP
    old=json.loads((a.reuse_build/'build_params.json').read_text())
    retained.require(retained.params(old['tile'])==t,'retained tile parameter identity differs')
    frozen=json.loads(a.baseline.read_text())
    retained.require(frozen.get('status')=='pass' and frozen.get('source_stable') is True,'retained tile receipt required')
    for path in retained.baseline.TILE_RTL:
        retained.require(frozen['source_sha256'].get(str(path.relative_to(ROOT)))==retained.sha(path),'retained tile source changed')
    dirs=[a.die_build,a.hbm_build,a.coll_build,a.reuse_build/'tile'];archives=[]
    include={ROOT/'rtl/test/qwen_runtime',ROOT/'tools/runtime/qwen_combined',a.out,
             a.verilator_root/'include',a.verilator_root/'include/vltstd',a.native_tagged_source.parent}
    for directory,prefix in zip(dirs,('die','hbm','coll','tile')):
        retained.require((directory/f'V{prefix}__ALL.a').is_file(),'actual model archive missing')
        archives+=sorted(directory.rglob('*.a'));include.add(directory)
        include.update(p.parent for p in directory.rglob('V*.h'))
    before={str(p):retained.sha(p) for p in archives}
    a.out.mkdir()
    access.emit(a.die_build/'Vdie___024root.h',dirs[-1]/'Vtile___024root.h',a.hbm_build/'Vhbm___024root.h',a.out,
                nport=d['G']>>d['SMIN'],scale_banks=d['SCALE_BANKS'],code_banks=t['CODE_BANKS'],
                crom_words=d['CROM_WORDS'],hbm_layers=d['HBM_LAYERS'],embed_rom=d['EMBED_ROM'],top=top)
    cpp=a.out/'qwen_rom_combined.cpp';cpp.write_text(emitter.emit(ROOT,dspark=a.dspark,full_decoder=a.full_decoder));exe=a.out/'qwen_rom_combined'
    macros=dict(GROUPS=d['G'],COUNTWIDTH=d['NW'],SWIDTH=d['SW'],SMAXB=d['SMAX'],TCUTL=d['TCUT'],
                NWSD=d['NWS'],XVMD=d['XVM'],TPD=d['D'],CBANKS=t['CODE_BANKS'],SMINV=d['SMIN'],STREAM4_CORE_FS=h['CORE_FS'])
    command=['g++','-std=c++20','-O2','-pthread',*(f'-D{k}={v}' for k,v in macros.items()),
             *(f'-I{p}' for p in sorted(include)),str(cpp),str(a.native_tagged_source),
             '-Wl,-z,defs','-Wl,--start-group',*map(str,archives),'-Wl,--end-group',
             *(str(a.verilator_root/'include'/name) for name in ('verilated.cpp','verilated_threads.cpp','verilated_dpi.cpp')),
             '-o',str(exe)]
    with (a.out/'link.log').open('x') as log:rc=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
    record=dict(returncode=rc,command=command,runtime_abi=emitter.ABI,top=top,dspark_enabled=a.dspark,
                resolved_parameters=dict(die=d,coll=c,hbm=h,tile=t),compiled_cli={k:build[k] for k in ('die','coll','hbm','tile')},
                source_defaults=build.get('source_defaults',{}),compiled_params_sha256=retained.sha(a.compiled_params),
                native_tagged_source=str(a.native_tagged_source.resolve()),native_tagged_sha256=a.native_tagged_sha256,
                archive_sha256=before,archives_stable=before=={str(p):retained.sha(p) for p in archives},
                generated_runtime_sha256=retained.sha(cpp),full_decoder=a.full_decoder,adopted_required=a.require_adopted,maximum_stages=37 if a.full_decoder else (2 if a.dspark else 1),
                scope='Actual single-array STREAM4 host link; no numerical/physical/rate verdict')
    if exe.exists():record['executable_sha256']=retained.sha(exe)
    (a.out/'link.json').write_text(json.dumps(record,indent=2)+'\n')
    retained.require(record['archives_stable'],'model archives changed during link')
    return rc


if __name__=='__main__':raise SystemExit(main())
