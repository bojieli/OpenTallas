#!/usr/bin/env python3
"""Actual VN partial trace -> actual XFIN16 -> same actual VN/VQ contexts.

No golden rstd/y/q is read as stimulus. The ring and context epochs are explicit
component models; die clock/transport/global schedule qualification stays held.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import shutil
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--leaf-run',type=Path,required=True)
    p.add_argument('--native-programme',type=Path,required=True)
    p.add_argument('--fixtures',type=Path,required=True,help='scoreboard comparison only; never simulator stimulus')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();leaf=json.loads((a.leaf_run/'receipt.json').read_text())
    assert leaf['status']=='ACTUAL_LEAF_PARTIALS_COLLECTED_COMPONENT_ONLY'
    assert len(leaf['actual_partials'])==80
    assert leaf['native_programme_sha256']==sha(a.native_programme)
    native=json.loads(a.native_programme.read_text());assert native['eps_fp32_bits']=='1e3ce508'
    for rel,d in leaf['source_sha256'].items():assert sha(a.source_root/rel)==d
    a.out.mkdir(parents=True,exist_ok=False)
    partials={5*c['sid']+c['leaf']:c for c in leaf['actual_partials']}
    assert set(partials)==set(range(80))
    for context in leaf['contexts']:
        log=Path(context['directory'])/'partial.log'
        assert sha(log)==partials[context['global_beat']]['log_sha256']
    (a.out/'actual_partials80.hex').write_text(''.join(partials[i]['data32']+'\n' for i in range(80)))
    (a.out/'eps_actual_config.hex').write_text(native['eps_fp32_bits']+'\n')
    bench=Path(__file__).with_name('tb_norm_xfin_source.sv');obj=a.out/'obj'
    receipt=dict(schema='opentallas.s81.norm_compositional_producer.v1',status='BUILDING',
        leaf_receipt_sha256=sha(a.leaf_run/'receipt.json'),native_programme_sha256=sha(a.native_programme),
        source_sha256=leaf['source_sha256'],bench_sha256=sha(bench),NS=16,NVL=5,LM=5,LA=6,
        eps_fp32_bits=native['eps_fp32_bits'],partial_input_sha256=sha(a.out/'actual_partials80.hex'),
        expected_norm_input=False,actual_vn_partials=True,ring_transport='one registered edge per neighbour; COMPONENT MODEL ONLY',
        die_clock_qualified=False,global_epoch_qualified=False,actual_rstd=[],actual_leaf_outputs=[],
        leaf_input_component_cycles=dict(reset_release=32,native_sw128=[64+2*i for i in range(49)],
            HLOAD=192,GAIN=224,NORMR=248,actual_rstd_replay=800),
        XFIN_input_component_cycles=dict(reset_release=32,go=64,partial_leaf=[96+2*i for i in range(5)]))
    def save():(a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    v=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    cmd=[str(v),'--binary','--timing','-O1','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-WIDTH',
        '--top-module','tb_norm_xfin_source','-Mdir',str(obj.resolve()),'-j','2',
        '--output-groups','16','--output-split','10000','--output-split-cfuncs','1000',
        *[str((a.source_root/s).resolve()) for s in receipt['source_sha256']],str(bench.resolve()),'-CFLAGS','-O1']
    receipt['argv']=cmd;save()
    with (a.out/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:receipt.update(status='BUILD_FAIL',exit_code=r.returncode);save();sys.exit(1)
    gd=Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
    sys.path.insert(0,str(gd));import verilator_nba_guard as G
    guard=G.scan(str(obj));(a.out/'nba_guard.json').write_text(json.dumps(guard,indent=1)+'\n')
    if guard['findings']:receipt['status']='NBA_GUARD_FAIL';save();sys.exit(86)
    # Same leaf binary, one deliberate source-input corruption. Preserve the
    # positive input directory and prove a real causal change in its partial.
    context=next(c for c in leaf['contexts'] if c['sid']==1 and c['leaf']==0)
    altered=a.out/'negative_zero_h_sid1_leaf0';shutil.copytree(context['directory'],altered)
    data=(altered/'native_sw128.hex').read_text().splitlines()
    data[:32]=['0'*32]*32
    (altered/'native_sw128.hex').write_text('\n'.join(data)+'\n')
    leaf_binary=(a.leaf_run/'obj/Vtb_norm_leaf_source').resolve()
    neg=subprocess.run([str(leaf_binary),f'+DIR={altered.resolve()}','+SID=1','+LEAF=0'],capture_output=True,text=True)
    neglog=neg.stdout+neg.stderr;(altered/'causal.log').write_text(neglog)
    actual=re.findall(r'LEAF_PARTIAL .*data=([0-9a-fA-F]+)',neglog)
    assert neg.returncode==0 and len(actual)==1 and actual[0]!=partials[5]['data32']
    receipt['causal_input_mutation']=dict(status='REFERENCE_PARTIAL_REJECTED',mutation='zero native H rows0..31 only',
        sid=1,leaf=0,same_binary_sha256=sha(leaf_binary),exit_code=neg.returncode,
        positive_partial32=partials[5]['data32'],mutant_partial32=actual[0],
        mutant_input_sha256=sha(altered/'native_sw128.hex'),rawlog_sha256=sha(altered/'causal.log'),
        simulator_terminal_failure_claimed=False)
    save()
    for name,mut in [('positive',0),('negative_duplicate_sid',1)]:
        r=subprocess.run([str((obj/'Vtb_norm_xfin_source').resolve()),f'+DIR={a.out.resolve()}',f'+MUT={mut}'],capture_output=True,text=True)
        log=r.stdout+r.stderr;(a.out/(name+'.log')).write_text(log)
        if mut:
            assert r.returncode and 'XFIN_SOURCE_FAIL' in log
            receipt['matched_negative']=dict(exit_code=r.returncode,log_sha256=sha(a.out/(name+'.log')))
        else:
            assert not r.returncode and 'XFIN_SOURCE_PASS' in log
            values=re.findall(r'ACTUAL_XFIN_RSTD sid=(\d+) cycle=(\d+) data=([0-9a-fA-F]+) eps=([0-9a-fA-F]+)',log)
            assert len(values)==16 and {int(v[0]) for v in values}==set(range(16))
            assert len({v[2] for v in values})==1 and {v[3] for v in values}=={native['eps_fp32_bits']}
            receipt['actual_rstd']=[dict(sid=int(s),cycle=int(c),data32=d) for s,c,d,e in values]
            (a.out/'actual_rstd.hex').write_text(values[0][2]+'\n')
            receipt['positive_run']=dict(exit_code=r.returncode,rawlog_sha256=sha(a.out/(name+'.log')))
        save()
    # Reuse the existing immutable leaf binary and legitimate input contexts.
    binary=(a.leaf_run/'obj/Vtb_norm_leaf_source').resolve()
    for context in leaf['contexts']:
        args=[str(binary),f'+DIR={context["directory"]}',f'+SID={context["sid"]}',
              f'+LEAF={context["leaf"]}',f'+ACTUAL_RSTD={(a.out/"actual_rstd.hex").resolve()}']
        r=subprocess.run(args,capture_output=True,text=True);log=r.stdout+r.stderr
        path=a.out/f'sid{context["sid"]}_leaf{context["leaf"]}.log';path.write_text(log)
        assert not r.returncode and 'LEAF_SOURCE_PASS' in log
        pv=re.findall(r'LEAF_PARTIAL .*data=([0-9a-fA-F]+)',log)
        assert pv==[partials[context['global_beat']]['data32']]
        yy=re.findall(r'LEAF_Y sid=(\d+) leaf=(\d+) cycle=(\d+) i=(\d+) data=([0-9a-fA-F]+)',log)
        xx=re.findall(r'LEAF_XF sid=(\d+) leaf=(\d+) cycle=(\d+) first=([01]) data=([0-9a-fA-F]+)',log)
        assert len(yy)==8 and [int(x[3]) for x in yy]==list(range(8)) and len(xx)==4
        receipt['actual_leaf_outputs'].append(dict(sid=context['sid'],leaf=context['leaf'],
            log_sha256=sha(path),exit_code=r.returncode,y=[dict(cycle=int(c),i=int(i),data256=d) for s,k,c,i,d in yy],
            xf=[dict(cycle=int(c),first=int(f),data276=d) for s,k,c,f,d in xx]))
        save()
    # Expectations are opened only after all simulator runs have finished.
    # No expected value is ever placed in a simulator input/replay directory.
    import struct
    records=json.loads((a.fixtures/'files.json').read_text())
    wanted={}
    for rel in ['ops/attn.norm.rsqrt.bin','ops/attn.norm.scale.bin']:
        assert sha(a.fixtures/rel)==records[rel]['sha256']
        wanted[rel]=list(struct.unpack('<'+'I'*((a.fixtures/rel).stat().st_size//4),(a.fixtures/rel).read_bytes()))
    mismatches=[]
    for rec in receipt['actual_rstd']:
        if int(rec['data32'],16)!=wanted['ops/attn.norm.rsqrt.bin'][0]:mismatches.append(dict(kind='rstd',actual=rec))
    for context in receipt['actual_leaf_outputs']:
        base=320*context['sid']+64*context['leaf']
        for beat in context['y']:
            word=int(beat['data256'],16)
            for lane in range(8):
                ix=base+8*beat['i']+lane;actual=(word>>(32*lane))&0xffffffff
                if actual!=wanted['ops/attn.norm.scale.bin'][ix]:
                    mismatches.append(dict(kind='y',index=ix,actual=f'{actual:08x}',expected=f'{wanted["ops/attn.norm.scale.bin"][ix]:08x}'))
    receipt['scoreboard_only']=dict(opened_after_simulation=True,expected_values_used_as_input=False,
        source_sha256={rel:records[rel]['sha256'] for rel in wanted},rstd_words=16,y_words=5120,
        mismatches=mismatches)
    receipt['status']='SCOREBOARD_FAIL' if mismatches else 'ACTUAL_COMPOSITIONAL_NORM_PRODUCER_COMPONENT_ONLY'
    save()
    print(json.dumps(dict(status=receipt['status'],contexts=len(receipt['actual_leaf_outputs']))))
    if mismatches:sys.exit(1)


if __name__=='__main__':main()
