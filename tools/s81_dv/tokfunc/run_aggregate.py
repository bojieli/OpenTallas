#!/usr/bin/env python3
"""Build once: actual local-ri_e XS4/six-frame/CAP cone, A/B and matched drop.

Must run under fleet admission. It preserves every build object, raw simulator
log, and ROM open syscall. No global HOST/KS/END or physical phase is admitted.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['kit','local-cone','bench','replay','inventory','fixtures','out']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage-only',action='store_true')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    inventory=json.loads(a.inventory.read_text());kit=json.loads((a.kit/'kit.json').read_text())
    local=json.loads((a.local_cone/'local_cone.json').read_text())
    assert not local['changed_master_bodies'] and local['frame_X_XK_XO_return_transport_preserved']
    assert inventory['die_sha256']==local['source_die_sha256']
    available={f['sha256'] for f in kit['files']}
    for rel,rec in inventory['sources'].items():assert rec['sha256'] in available,('shipping body absent from functional closure',rel,rec['sha256'])
    pins={f['path']:sha(a.kit/'src'/f['path']) for f in kit['files']}
    assert all(pins[f['path']]==f['sha256'] for f in kit['files'])
    top=a.local_cone/'cut/s0N_aggregate.sv';tb=a.bench/'tb_s0N_aggregate.sv'
    assert sha(top)==local['local_cone_sv_sha256']
    bench=json.loads((a.bench/'bench.json').read_text());assert sha(tb)==bench['bench_sha256']
    for half in ['A','B']:
        rec=json.loads((a.replay/half/'replay.json').read_text())
        assert rec['inventory_sha256']==sha(a.inventory), 'replay bound to another selected source inventory'
        assert rec['ordering_guard']['first_gather_edge']>rec['ordering_guard']['window_open_model_edge']
        assert rec['ordering_guard']['last_gather_edge']<rec['ordering_guard']['prime_pin_edge']
        for name,digest in rec['production_ROM_images'].items():assert sha(a.replay/half/'rom'/name)==digest
    receipt=dict(schema='opentallas.s81.actual_local_aggregate.v1',status='SOURCE_STAGED',
        inventory_sha256=sha(a.inventory),functional_kit_sha256=sha(a.kit/'kit.json'),source_sha256=pins,
        local_cone_sha256=sha(a.local_cone/'local_cone.json'),top_sha256=sha(top),bench_sha256=sha(tb),
        replay_sha256={h:sha(a.replay/h/'replay.json') for h in ['A','B']},clocks=bench['named_root_clocks'],
        defines=kit['defines'],selected_source_correction=inventory.get('source_selection_correction'),
        source_grade='actual selected local-ri_e source component only',physical_phase_qualified=False,
        global_epoch_bound=False,HOST_KS_assumed=False,global_END_sealed=False,cases={})
    def save():(a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    save()
    if a.stage_only:return
    assert shutil.which('strace'),'ROM load syscall capture requires strace; no silent fallback'
    lines=[]
    for line in (a.kit/'kit.f').read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('//'):continue
        if line.startswith('+') or line.startswith('-'):lines.append(line)
        elif not line.startswith('src/top/'):lines.append(str((a.kit/line).resolve()))
    lines += [str(top.resolve()),str(tb.resolve())]
    source_list=a.out/'compile.f';source_list.write_text('\n'.join(lines)+'\n')
    obj=a.out/'obj';v=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    cmd=[str(v),'--binary','--timing','-O1','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-WIDTH',
        '--top-module','tb_s0N_aggregate','-Mdir',str(obj.resolve()),'-j','2','--output-groups','32',
        '--output-split','10000','--output-split-cfuncs','500','-f',str(source_list.resolve()),'-CFLAGS','-O1']
    receipt.update(status='BUILDING',argv=cmd);save()
    with (a.out/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:receipt.update(status='BUILD_FAIL',exit_code=r.returncode);save();sys.exit(1)
    gd=Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
    sys.path.insert(0,str(gd));import verilator_nba_guard as G
    guard=G.scan(str(obj));(a.out/'nba_guard.json').write_text(json.dumps(guard,indent=1)+'\n')
    if guard['findings']:receipt['status']='NBA_GUARD_FAIL';save();sys.exit(86)
    binary=(obj/'Vtb_s0N_aggregate').resolve();receipt['binary_sha256']=sha(binary)
    for name,half,mut in [('A_positive','A',0),('B_positive','B',0),('A_drop_actual_XQ0','A',1)]:
        directory=a.out/name;directory.mkdir()
        syscall=directory/'rom_opens.log'
        args=['strace','-f','-e','trace=openat','-o',str(syscall.resolve()),str(binary),
            f'+DIR={(a.replay/half).resolve()}',f'+OT_ROM_DIR={(a.replay/half/"rom").resolve()}',f'+MUT={mut}','+T=5000']
        with (directory/'raw.log').open('w') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
        text=(directory/'raw.log').read_text()
        rec=json.loads((a.replay/half/'replay.json').read_text())
        opens=syscall.read_text()
        opened={Path(path).name for path in re.findall(r'openat\([^\n]*?"([^"\n]+\.viamap\.hex)"[^\n]*?=\s*\d+',opens)}
        missing=sorted(set(rec['production_ROM_images'])-opened)
        warnings=[line for line in text.splitlines() if re.search(r'Warning|Error|not found|cannot open|readmem',line,re.I)]
        counts=re.search(r'AGG_COUNTS raw=(\d+) ctl=(\d+) gather=(\d+) is=(\d+) cfg=(\d+) windows=(\d+) table=(\d+) macro=(\d+) cap=(\d+) bad=(\d+) mut=(\d+)',text)
        case=dict(exit_code=r.returncode,argv=args,rawlog_sha256=sha(directory/'raw.log'),rom_opens_sha256=sha(syscall),
            intended_ROM_files=len(rec['production_ROM_images']),opened_ROM_files=len(opened),
            intended_ROM_missing=missing,unfiltered_ROM_warnings=warnings,
            counts=list(map(int,counts.groups())) if counts else None)
        if mut:
            case['passed']=bool(r.returncode and 'AGGREGATE_SOURCE_FAIL' in text and counts and int(counts[1])==79 and int(counts[3])==79)
        else:
            case['passed']=bool(not r.returncode and 'AGGREGATE_SOURCE_COUNTS_PASS' in text and not missing)
            # Open the checkpoint only after the actual run. Values never
            # enter the packet/ROM/bench stimulus files.
            import struct
            files=json.loads((a.fixtures/'files.json').read_text());rel='ops/attn.a_proj.bin'
            assert sha(a.fixtures/rel)==files[rel]['sha256']
            raw=(a.fixtures/rel).read_bytes();expected_values=struct.unpack('<'+'I'*(len(raw)//4),raw)
            actual=[(face,int(port),int(address),int(data,16)) for _,face,port,address,data in
                re.findall(r'AGG_CAP t=([0-9.]+) face=([SN]) port=(\d+) address=(\d+) data=([0-9a-fA-F]+)',text)]
            wanted=[];cfg=rec['capture']['cfg'];base=cfg['rbase']
            for row in rec['capture']['rows']:
                relative=(1<<14)+row['rank_row']-base;column,element=divmod(relative,64)
                leaf,block=column%5,column//5;addr=cfg['obase']+64*block+element
                face='S' if leaf<3 else 'N';port=2*(leaf if face=='S' else leaf-3)+((addr>>2)&1)
                wanted.append((face,port,addr,expected_values[row['golden_output_index']]))
            case['scoreboard_only']=dict(source_sha256=files[rel]['sha256'],expected_values_used_as_input=False,
                actual_CAP=actual,expected_CAP=wanted,exact=sorted(actual)==sorted(wanted))
            case['passed'] &= case['scoreboard_only']['exact']
        receipt['cases'][name]=case;save()
        if not case['passed']:receipt.update(status='CASE_FAIL',failed_case=name);save();sys.exit(1)
    receipt['status']='PASS_ACTUAL_LOCAL_AGGREGATE_SOURCE_COMPONENT';save()
    print(json.dumps(dict(status=receipt['status'],cases={n:v['passed'] for n,v in receipt['cases'].items()})))


if __name__=='__main__':main()
