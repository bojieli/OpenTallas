#!/usr/bin/env python3
"""Link the real combined runtime against owner's compiled models and cached tile."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import qwen_rom_combined_access as access
import qwen_rom_combined_runtime_emit as emitter
import qwen_rom_rt_token_w12_rm as baseline
from qwen_rom_combined_launch import sha, require

ROOT=Path(__file__).resolve().parents[1]


def params(values):
    return {v[2:].split('=',1)[0]:int(v.split('=',1)[1]) for v in values if v.startswith('-G')}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('die-build','hbm-build','coll-build','reuse-build','baseline','compiled-params','verilator-root','out'):
        ap.add_argument('--'+key,type=Path,required=True)
    a=ap.parse_args()
    require(not a.out.exists(),'immutable link output exists')
    build=json.loads(a.compiled_params.read_text())
    d,c,h,t=(params(build[k]) for k in ('die','coll','hbm','tile'))
    require(all(d.get(k)==v for k,v in {'G':6144,'SW':64,'NW':18,'SNW':18,'D':4,'REAL_MEM':1,'NPC':32}.items()),
            'compiled fullshape die parameters')
    require(c.get('N')==4 and c.get('TAGW')==44,'compiled fullwidth TP4 collective')
    require(all(h.get(k)==v for k,v in {'NPC':32,'AW':24,'DW':256,'TAGW':13,'LENW':5,'BEATW':4,'PC_RDY':1,'WR_ACK':1}.items()),
            'compiled real four-stack HBM parameters')
    require(h.get('MEM_WORDS')==d['HBM_LAYERS']*131072 and h.get('CLK_PS',0)>0,'actual HBM extent/clock')
    frozen=json.loads(a.baseline.read_text())
    require(frozen.get('status')=='pass' and frozen.get('source_stable') is True,'passing cached tile baseline')
    old=json.loads((a.reuse_build/'build_params.json').read_text())
    require(params(old['tile'])==t,'cached tile parameter identity changed')
    for p in baseline.TILE_RTL:
        require(frozen['source_sha256'].get(str(p.relative_to(ROOT)))==sha(p),'cached tile source differs: '+str(p))
    dirs=[a.die_build,a.hbm_build,a.coll_build,a.reuse_build/'tile']
    archives=[]
    includes={ROOT/'rtl/test/qwen_runtime',ROOT/'tools/runtime/qwen_combined',a.out,
              a.verilator_root/'include',a.verilator_root/'include/vltstd'}
    for path,prefix in zip(dirs,('die','hbm','coll','tile')):
        require((path/f'V{prefix}__ALL.a').is_file(),'actual compiled model missing: '+str(path))
        archives+=sorted(path.rglob('*.a'));includes.add(path)
        includes.update(p.parent for p in path.rglob('V*.h'))
    before={str(p):sha(p) for p in archives}
    a.out.mkdir(parents=True)
    access.emit(a.die_build/'Vdie___024root.h',dirs[-1]/'Vtile___024root.h',a.hbm_build/'Vhbm___024root.h',a.out,
                nport=d['G']>>d['SMIN'],scale_banks=d['SCALE_BANKS'],code_banks=t['CODE_BANKS'],
                crom_words=d['CROM_WORDS'],hbm_layers=d['HBM_LAYERS'],embed_rom=d['EMBED_ROM'])
    cpp=a.out/'qwen_rom_combined.cpp';cpp.write_text(emitter.emit())
    macros={'GROUPS':d['G'],'COUNTWIDTH':d['NW'],'SWIDTH':d['SW'],'SMAXB':d['SMAX'],'TCUTL':d['TCUT'],
            'NWSD':d['NWS'],'XVMD':d['XVM'],'TPD':d['D'],'CBANKS':t['CODE_BANKS'],'SMINV':d['SMIN'],
            'HBM_CLOCK_PS':h['CLK_PS']}
    exe=a.out/'qwen_rom_combined'
    cmd=['g++','-std=c++20','-O2','-pthread',*(f'-D{k}={v}' for k,v in macros.items()),
         *(f'-I{p}' for p in sorted(includes)),str(cpp),'-Wl,--start-group',*map(str,archives),'-Wl,--end-group',
         *(str(a.verilator_root/'include'/name) for name in ('verilated.cpp','verilated_threads.cpp','verilated_dpi.cpp')),
         '-o',str(exe)]
    with (a.out/'link.log').open('x') as log:
        rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
    record={'command':cmd,'returncode':rc,'archive_sha256':before,
            'archives_stable':before=={str(p):sha(p) for p in archives},'generated_runtime_sha256':sha(cpp)}
    if exe.exists():record['executable_sha256']=sha(exe)
    (a.out/'link.json').write_text(json.dumps(record,indent=2)+'\n')
    require(record['archives_stable'],'compiled archive changed during link')
    return rc


if __name__=='__main__':raise SystemExit(main())
