#!/usr/bin/env python3
"""Opt-in retained TP4 program recovery and source emitter identity. No execution."""
import argparse, base64, gzip, hashlib, json, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT/'results/rtl/qwen_rom_TP4_terminal_20261002/capture.json'
TERM = CAP.with_name('original_terminal.json')
def sha(b): return hashlib.sha256(b).hexdigest()
def encoded(b): return {'base64':base64.b64encode(b).decode(), 'sha256':sha(b)}
def decoded(v):
    b=base64.b64decode(v['base64'], validate=True)
    if sha(b)!=v['sha256']: raise ValueError('archive byte identity')
    return b

def validate(packet, terminal):
    if set(packet['stages']) != {f'{s}/die{r}' for s in [f'L{i}' for i in range(36)]+['head'] for r in range(4)}:
        raise ValueError('complete 37x4 stage coverage')
    for key, rec in packet['stages'].items():
        stage, rank=key.split('/'); rank=int(rank[3:])
        man=json.loads(decoded(rec['metadata']))
        if man['die']!=rank or man['tp']!=4 or (stage!='head' and man['layer']!=int(stage[1:])):
            raise ValueError('metadata owner')
        for name in ('program.hex','segments.hex'):
            if sha(decoded(rec[name]))!=terminal['stage_image_sha256'][key+'/'+name]:
                raise ValueError('retained program/descriptor pin')
        sw=json.loads(decoded(rec['program_sw.json']))
        if sw['program_sha256']!=rec['program.hex']['sha256'] or sw['su_width']!=64:
            raise ValueError('retained SU width/program identity')
        for name in ('matrix_int8.hex','matrix_scale_bf16.hex','crom.hex'):
            expected=terminal['stage_image_sha256'][key+'/'+name]
            # Head manifest predates its constant-ROM wrapper; do not invent a pin.
            if name in man['image_sha256'] and man['image_sha256'][name]!=expected:
                raise ValueError('historical payload manifest identity')
    return {'stages':148,'layers':36,'ranks':4,'fresh_payload_rehash':False,
            'accepted_KV_journal_present':False,'physical_adoption':False}

REMOTE = r'''
import base64,hashlib,json,pathlib
req=json.load(__import__('sys').stdin); out={}
def read(p):
 p=pathlib.Path(p); a=p.read_bytes(); b=p.read_bytes()
 if a!=b: raise ValueError('unstable source')
 return {'base64':base64.b64encode(a).decode(),'sha256':hashlib.sha256(a).hexdigest()}
for key,path in req.items():
 stage,rank=key.split('/'); rank=int(rank[3:]); p=pathlib.Path(path)
 man=pathlib.Path('/home/ubuntu/w12/img_tp4')/(stage+'-d'+str(rank))/('head_rom.json' if stage=='head' else 'layer'+stage[1:]+'_rom.json')
 out[key]={n:read(p/n) for n in ('program.hex','segments.hex','program_sw.json')}
 out[key]['metadata']=read(man)
print(json.dumps(out,sort_keys=True))
'''
def collect(out):
    cap=json.loads(CAP.read_text()); rows=decoded(cap['files']['stages.txt']).decode().splitlines()
    req={}
    for row in rows:
        fields=row.split()
        if not fields: continue
        for r,p in enumerate(fields[1:5]): req[f'{fields[0]}/die{r}']=p
    # The remote command reads only small program/descriptor/metadata files.
    command='python3 -c '+__import__('shlex').quote(REMOTE)
    result=subprocess.run(['ssh','-o','BatchMode=yes','ot-pve1',command],input=json.dumps(req),text=True,capture_output=True,check=True)
    packet={'schema':'qwen-retained-program-identity-v1','capture_sha256':sha(CAP.read_bytes()),
            'terminal_sha256':sha(TERM.read_bytes()),'stages':json.loads(result.stdout)}
    packet['qualification']=validate(packet,json.loads(TERM.read_text()))
    with out.open('xb') as f: f.write(gzip.compress((json.dumps(packet,sort_keys=True)+'\n').encode(),mtime=0))

def emit_worker(rec):
    import hdc_qwen_fullshape_program_w12 as FP
    man=json.loads(decoded(rec['metadata']))
    if 'geometry' in man:
        geo=dict(man['geometry']);geo['scale_base']=0
        p=FP.profile_lm_head(man['die'],geo,0)
    else: p=FP.profile(man['die'],matrix_rows=man['matrix_layout'],post_scale_bases=man['post_tp_scale_bases'])
    return {n:'\n'.join(p[k])+'\n' for n,k in [('program.hex','program_hex'),('segments.hex','descriptor_hex')]}

def replay(archive,out,su,ar):
    packet=json.loads(gzip.decompress(archive.read_bytes()))
    if packet['capture_sha256']!=sha(CAP.read_bytes()) or packet['terminal_sha256']!=sha(TERM.read_bytes()):
        raise ValueError('capture root changed')
    if su not in (64,1024) or ar not in (128,256): raise ValueError('bounded reviewed program dimensions')
    qualification=validate(packet,json.loads(TERM.read_text()))
    env=dict(os.environ,QWEN_O4_TP='4',QWEN_O4_GROUPS='6144',HDC_SU_WIDTH=str(su),QWEN_O4_AR_WORDS=str(ar))
    stages={}; all_exact=True
    for key,rec in sorted(packet['stages'].items()):
        p=subprocess.run([sys.executable,__file__,'worker'],input=json.dumps(rec),env=env,text=True,capture_output=True,check=True)
        files=json.loads(p.stdout)
        exact={n:sha(v.encode())==rec[n]['sha256'] for n,v in files.items()}
        all_exact=all_exact and all(exact.values())
        import hdc_isa as I
        from hdc_qwen_fullshape_isa_w12 import decode_instruction
        fs=[decode_instruction(int(w,16)) for w in files['program.hex'].split()]
        stages[key]={'files':{n:encoded(v.encode()) for n,v in files.items()},'retained_exact':exact,
                     'ME_PC':[pc for pc,f in enumerate(fs) if f['unit']==I.UNIT_ME],
                     'KV_SU_PC':[pc for pc,f in enumerate(fs) if f['unit']==I.UNIT_SU and f['dst']==I.DST_KV]}
    source_paths=['tools/hdc_qwen_fullshape_program_w12.py','tools/hdc_qwen_fullshape_isa_w12.py','tools/hdc_qwen_fullshape_placement_w12.py','tools/hdc_program.py','tools/hdc_isa.py','tools/qwen_rom_program_identity.py','compiler/models/qwen3-8b/config.json','compiler/models/qwen3-8b/checkpoint_source.json']
    record={'schema':'qwen-source-program-build-v1','source_sha256':{p:sha((ROOT/p).read_bytes()) for p in source_paths},
            'archive_sha256':sha(archive.read_bytes()),'su_width':su,'ar_words':ar,'TP':4,'groups':6144,
            'qualification':qualification,'retained_programs_byte_exact':all_exact,
            'status':'PASS_RETAINED_PROGRAM_REPRODUCTION' if all_exact else 'SOURCE_PROGRAM_DIFF_REQUIRES_REVIEW',
            'actual_accepted_ME_count':None,'actual_KV_state':None,'numerical_successor_qualified':False,'stages':stages}
    with out.open('x') as f: json.dump(record,f,sort_keys=True,indent=1);f.write('\n')

def materialize(archive,out):
    bundle=json.loads(gzip.decompress(archive.read_bytes()))
    if any(sha((ROOT/p).read_bytes())!=v for p,v in bundle['source_sha256'].items()): raise ValueError('source emitter identity')
    terminal=json.loads(TERM.read_text())
    out.mkdir(exist_ok=False)
    for key,rec in sorted(bundle['stages'].items()):
        d=out/key;d.mkdir(parents=True)
        for name,value in rec['files'].items(): (d/name).write_bytes(decoded(value))
        refs={n:terminal['stage_image_sha256'][key+'/'+n] for n in ('matrix_int8.hex','matrix_scale_bf16.hex','crom.hex')}
        (d/'payload-required.json').write_text(json.dumps({'historical_payload_sha256':refs,'complete_runtime_image':False,'physical_qualified':False},sort_keys=True)+'\n')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['collect','replay','worker','materialize']);ap.add_argument('--archive',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--su',type=int,default=64);ap.add_argument('--ar',type=int,default=128);a=ap.parse_args()
    if a.mode=='worker': print(json.dumps(emit_worker(json.load(sys.stdin))));return
    if a.mode=='materialize': materialize(a.archive,a.out); return
    if a.mode=='collect': collect(a.out)
    else: replay(a.archive,a.out,a.su,a.ar)
if __name__=='__main__':main()
