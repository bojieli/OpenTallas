#!/usr/bin/env python3
"""Prepare and check real-checkpoint connected HBROM component campaigns.

Preparation copies only physical ROM images and activation/config runtime inputs.
The checker reads golden artifacts after simulation; they never feed the DUT.
Build/run hooks target the full selected tile, never a whole-model simulation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(campaign, out, pair_count):
    campaign=Path(campaign).resolve();out=Path(out).resolve()
    data=json.loads(campaign.read_text()); cases=data['cases']
    if pair_count<=0 or pair_count%4:raise ValueError('four pairs per bankgroup required')
    if not cases:raise ValueError('empty campaign')
    if out.exists():raise FileExistsError('Preserve existing campaign '+str(out))
    out.mkdir(parents=True)
    from mem_compiler.rom_gen import RomSpec, via_map
    rom_spec=RomSpec('ot_rom_4096x274_m8',4096,274,8)
    config=[];xwords=[];occupied=set();refs=[];images={}
    for i,c in enumerate(cases):
        directory=campaign.parent/f'op{i:02d}'
        # Confirm inputs and independent references still match source-bound generation.
        for name,want in c['files_sha256'].items():
            if digest(directory/name)!=want:raise ValueError('changed vector '+str(directory/name))
        if c['bankgroup_base']+c['bankgroups']>pair_count//4:
            raise ValueError('selected physical tile cannot contain campaign bankgroups')
        loaded={p.name:[int(v,16) for v in p.read_text().split()] for p in directory.glob('rom_g*_s*_p*.hex')}
        base=c.get('physical_base_record',c['bankgroup_base']*8192)
        for record in range(base,base+c['physical_records']):
            if record in occupied:raise ValueError('physical ROM record ownership overlap')
            occupied.add(record)
            bg,local=divmod(record,8192);parity=(local//8)%2;row=(local//16)*8+local%8
            for stream in range(4):
                name=f'rom_g{bg}_s{stream}_p{parity}.hex'
                images.setdefault(name,{})[row]=loaded[name][row]
        # No checker-only file copied to runtime directory.
        cfg=[int(s,16) for s in (directory/'cfg.hex').read_text().split()]
        cfg[6]=base;cfg[7]=c['physical_records']
        config.extend(cfg);xwords.extend((directory/'x.hex').read_text().split())
        refs.append(dict(operation=i,manifest=os.path.relpath(directory/'manifest.json',out),
                         expected_fp32=os.path.relpath(directory/'expected_fp32.hex',out),expected_sha256=digest(directory/'expected_fp32.hex'),
                         manifest_sha256=digest(directory/'manifest.json'),rows=len(c['source_rows']),
                         issued_records=c['issued_records'],format=c['format'],logical_K=c['logical_K']))
    # Unused full physical tile macros remain instantiated and have defined
    # simulation contents. Zero fill is only a sim initialization, never a synth substitute.
    for bg in range(pair_count//4):
        for s in range(4):
            for p in range(2):
                path=out/f'rom_g{bg}_s{s}_p{p}.hex'
                owned=images.get(path.name,{})
                lines=[f'{owned.get(row,0):069x}' for row in range(max(owned,default=-1)+1)]
                if len(lines)>4096:raise ValueError('ROM macro overflow')
                full=lines+['0'*69]*(4096-len(lines))
                path.write_text('\n'.join(full)+'\n')
                vias=via_map(rom_spec,[int(v,16) for v in full])
                (out/(path.stem+'.viamap.hex')).write_text(''.join(f'{v:0548x}\n' for v in vias))
    (out/'config.hex').write_text(''.join(f'{v:08x}\n' for v in config))
    (out/'activations.hex').write_text('\n'.join(xwords)+'\n')
    record=dict(schema='opentallas.hbrom.connected_preparation.v1',pair_count=pair_count,
                operations=len(cases),input_campaign=os.path.relpath(campaign,out),input_campaign_sha256=digest(campaign),
                cases=refs,runtime_files_sha256={p.name:digest(p) for p in out.iterdir()},
                claim='Runtime vectors prepared; RTL/build/physical qualification not implied')
    (out/'preparation.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def verify(preparation, output):
    prep=json.loads(Path(preparation).read_text());seen={};meta={};errors=[]
    for name,want in prep.get('runtime_files_sha256',{}).items():
        if digest(Path(preparation).parent/name)!=want:errors.append('runtime input changed: '+name)
    for line in Path(output).read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='R':
            if len(fields)!=4:raise ValueError('malformed result')
            op,row=int(fields[1]),int(fields[2]);value=int(fields[3],16)
            if (op,row) in seen:errors.append(f'duplicate result {op}:{row}')
            seen[op,row]=value
        elif fields[0]=='M':
            op=int(fields[1]);meta[op]={fields[i]:int(fields[i+1]) for i in range(2,len(fields),2)}
        elif fields[0]=='FAIL':errors.append(line)
        else:raise ValueError('unknown result record '+fields[0])
    cases=[];expected_ids=set()
    for c in prep['cases']:
        op=c['operation']
        golden_path=Path(preparation).resolve().parent/c['expected_fp32']
        manifest_path=Path(preparation).resolve().parent/c['manifest']
        if digest(golden_path)!=c['expected_sha256']:raise ValueError('golden reference changed')
        if digest(manifest_path)!=c['manifest_sha256']:raise ValueError('source manifest changed')
        gold=[int(v,16) for v in golden_path.read_text().split()]
        if len(gold)!=c['rows']:raise ValueError('golden row count')
        expected_ids.update((op,r) for r in range(len(gold)))
        missing=[r for r in range(len(gold)) if (op,r) not in seen]
        mismatch=[r for r,v in enumerate(gold) if (op,r) in seen and seen[op,r]!=v]
        m=meta.get(op,{})
        required={'requests':c['issued_records'],'responses':c['issued_records'],
                  'consumed':c['issued_records'],'results':c['rows'],'fault':0,'feed_fault':0,
                  'released':1,'macro_spacing_failures':0,'capture_count':4*c['issued_records']}
        bad={k:dict(expected=v,observed=m.get(k)) for k,v in required.items() if m.get(k)!=v}
        if missing or mismatch or bad:errors.append(f'operation {op} incomplete or mismatch')
        cases.append(dict(operation=op,format=c['format'],logical_K=c['logical_K'],rows=c['rows'],
                          missing=missing,mismatched_rows=mismatch,counter_failures=bad,measured=m))
    unexpected=sorted(set(seen)-expected_ids)
    if unexpected:errors.append('unexpected result identities')
    return dict(schema='opentallas.hbrom.connected_verdict.v1',status='PASS' if not errors else 'FAIL',
                errors=errors,unexpected_results=unexpected,cases=cases,
                preparation_sha256=digest(preparation),output_sha256=digest(output),
                scope='Connected selected-tile fullK arithmetic and ROM service simulation only; no timing closure claim')


def source_paths():
    # Reuse source closure from existing successor gate; no arithmetic substitute.
    import hbm_accel_sm_v_gate as gate
    return [p for p in gate.SRC if p!='rtl/test/tb_hbm_accel_sm_v.sv']+[
        'rtl/hbrom/ot_hbrom_rom_feed.sv',
        'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v',
        'tests/rtl/hbrom_compute_tb.sv']


def build(out, pair_count, operations, jobs, verilator='verilator'):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    paths=source_paths()
    for p in paths:
        if not (ROOT/p).is_file():raise FileNotFoundError(ROOT/p)
    cmd=[verilator,'--binary','--timing','-Wno-fatal','--top-module','hbrom_compute_tb',
         '--Mdir',str(out),'-j',str(jobs),f'-GPAIR_COUNT={pair_count}',f'-GNOPS={operations}',
         *[str(ROOT/p) for p in paths]]
    inventory=dict(command=cmd,source_sha256={p:digest(ROOT/p) for p in paths},
                   pair_count=pair_count,operations=operations,build_jobs=jobs)
    (out/'source_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    with (out/'build.log').open('x') as log:
        completed=subprocess.run(['/usr/bin/time','-v','-o',str(out/'build_resources.txt'),*cmd],
                                 cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    inventory['returncode']=completed.returncode
    inventory['generated_cpp']=[dict(path=p.name,bytes=p.stat().st_size) for p in out.glob('*.cpp')]
    (out/'build_terminal.json').write_text(json.dumps(inventory,indent=2)+'\n')
    if completed.returncode:raise RuntimeError('Build failed; immutable evidence retained')
    return out/'Vhbrom_compute_tb'


def run(executable, preparation, stall=0):
    preparation=Path(preparation).resolve();directory=preparation.parent
    if (directory/'out.txt').exists() or (directory/'runtime.log').exists():
        raise FileExistsError('Preserve previous runtime evidence; prepare a new runtime directory')
    command=[str(Path(executable).resolve()),f'+DIR={directory}',f'+OT_ROM_DIR={directory}',f'+STALL={stall}']
    with (directory/'runtime.log').open('x') as log:
        process=subprocess.run(['/usr/bin/time','-v','-o',str(directory/'runtime_resources.txt'),*command],
                               cwd=directory,stdout=log,stderr=subprocess.STDOUT)
    terminal=dict(command=command,returncode=process.returncode,preparation_sha256=digest(preparation))
    (directory/'runtime_terminal.json').write_text(json.dumps(terminal,indent=2)+'\n')
    if process.returncode:raise RuntimeError('Simulation failed; terminal evidence retained')
    result=verify(preparation,directory/'out.txt')
    with (directory/'verdict.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    if result['status']!='PASS':raise RuntimeError('Exact connected gate failed; verdict preserved')
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);sp=ap.add_subparsers(dest='mode',required=True)
    p=sp.add_parser('prepare');p.add_argument('--campaign',required=True);p.add_argument('--out',required=True);p.add_argument('--pairs',type=int,required=True)
    p=sp.add_parser('verify');p.add_argument('--preparation',required=True);p.add_argument('--output',required=True);p.add_argument('--record',required=True)
    p=sp.add_parser('build');p.add_argument('--out',required=True);p.add_argument('--pairs',type=int,required=True);p.add_argument('--operations',type=int,required=True);p.add_argument('--jobs',type=int,required=True);p.add_argument('--verilator',default='verilator')
    p=sp.add_parser('run');p.add_argument('--exe',required=True);p.add_argument('--preparation',required=True);p.add_argument('--stall',type=int,choices=[0,1],default=0)
    a=ap.parse_args()
    if a.mode=='prepare':prepare(a.campaign,a.out,a.pairs)
    elif a.mode=='build':build(a.out,a.pairs,a.operations,a.jobs,a.verilator)
    elif a.mode=='run':run(a.exe,a.preparation,a.stall)
    else:
        result=verify(a.preparation,a.output)
        with Path(a.record).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
