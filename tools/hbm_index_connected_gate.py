#!/usr/bin/env python3
"""One connected native index run; captured references are comparison-only.

extract performs lossless copies/bit packing from retained native inputs and
captured pre-mask scores. It never executes an arithmetic/golden model.
"""
import argparse, hashlib, json, os, pickle, subprocess
from pathlib import Path
from hbm_index_path_sources import RTL
ROOT=Path(__file__).resolve().parents[1]
TB='rtl/test/hbm_accel/tb_hbm_index_connected.sv'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def extract(a):
    import numpy as np
    a.out.mkdir(parents=True,exist_ok=False)
    snap=pickle.loads(a.snapshot.read_bytes())['L20.op14.index_scores']
    ids=np.asarray(snap['key_idx'],dtype=np.int64)
    scores=np.asarray(snap['after']['is_v'],dtype=np.float32).view(np.uint32)
    if len(ids)!=10928 or np.any(scores&65535):raise ValueError('retained complete rank0 BF16 scores required')
    if not np.array_equal(ids,8*(96*(np.arange(len(ids))//8))+(np.arange(len(ids))%8)):raise ValueError('literal TP96 rank0 order required')
    parts=[[int(s,16) for s in (a.parts/f'L20_p{p}'/'arr_k.mem').read_text().split()] for p in range(8)]
    if any(len(p)!=171*8 for p in parts):raise ValueError('retained full rank0 source layout required')
    source=[]
    for t in range(171):
        for p in range(8):source.extend(parts[p][t*8:t*8+8])
    keys=[]
    for ordinal in range(len(ids)):
        v=source[ordinal]
        if not (v>>576)&1 or ((v>>546)&((1<<30)-1))!=ordinal:raise ValueError('encoded retained key ordinal differs')
        # Preserve actual encoded key and refusal. Raw pre-mask scoring uses all
        # keys; archived post-candidate keep bits are NOT runtime stimuli.
        keys.append((v&((1<<544)-1))|1<<544|((v>>545)&1)<<545|int(ids[ordinal])<<546|1<<566)
    reordered=[]
    for beat in range(171):
        for q in range(4):
            for lane in range(16):
                ordinal=q*342*8+beat*16+lane
                reordered.append(keys[ordinal] if ordinal<min((q+1)*342*8,len(keys)) else 0)
    (a.out/'keys.mem').write_text(''.join(f'{v:0142x}\n' for v in reordered))
    (a.out/'scores.mem').write_text(''.join(f'{int(v)>>16:04x}\n' for v in scores))
    pins={str(a.snapshot):sha(a.snapshot)}
    for p in range(8):
        f=a.parts/f'L20_p{p}'/'arr_k.mem';pins[str(f)]=sha(f)
    record={'scope':'Retained actual encoded key operands + captured pre-candidate-mask BF16 comparison scores, rank0 at1M. No arithmetic/reference producer rerun; expected score file cannot supply DUT data.',
        'source_pins':pins,'source_operation':snap['op'],'rank':0,'keys':len(ids),'beats':171,'quarter_block_limit':342,
        'quarter_source_ranges':'owned ordinal q*342..min((q+1)*342,1366)-1; original key bytes/globalID order preserved',
        'archived_keep_bits_used_as_operands':False,'runtime_keep':'all true for actual initial unmasked index scoring',
        'outputs':{n:sha(a.out/n) for n in ['keys.mem','scores.mem']}}
    (a.out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
def key(v):return 0x8000 if v&0x7fff==0 else (~v&65535) if v&0x8000 else v|0x8000
def compare(out,inputs):
    scores=[int(s,16) for s in (inputs/'scores.mem').read_text().split()]
    # Independent comparator membership; never supplies gather or DUT inputs.
    wanted=set(sorted(range(len(scores)),key=lambda j:(-key(scores[j]),j))[:512])
    selected=[]
    for ln in (out/'topk.txt').read_text().splitlines():
        gid,val=ln.split();gid=int(gid);val=int(val,16);j=(gid//8//96)*8+gid%8
        if gid//8%96 or j>=len(scores) or val!=scores[j]:raise ValueError('actual local topk payload/source mismatch')
        selected.append(j)
    if len(selected)!=512 or len(set(selected))!=512 or set(selected)!=wanted:raise ValueError('local top512/tie membership differs from captured scores')
    blocks=[]
    for ln in (out/'candidates.txt').read_text().splitlines():
        block,val=ln.split();block=int(block);val=int(val,16);j=block//96
        if block%96 or j>=1366:raise ValueError('actual candidate global block/source mismatch')
        group=scores[j*8:j*8+8];expected=max(group,key=key)
        if val!=expected:raise ValueError(f'actual candidate score mismatch block{block}: {val:x}!={expected:x}')
        blocks.append(j)
    if len(blocks)!=1366 or len(set(blocks))!=1366:raise ValueError('actual candidates missing/duplicated')
    return {'scope':'Native VM query/full NS16NK4 scorer/native local top512 and1366 block candidates, rank0 retained1M operands. Final collective gather/actual production VM/SRAM/SSFF remain unqualified.',
        'topk_exact':512,'candidate_exact':1366,'full_index_qualified':False,'full_token_qualified':False,'SS_FF_closed':False}
def run(a):
    a.out.mkdir(parents=True,exist_ok=False);a.out=a.out.resolve()
    inputs=a.inputs.resolve();original=a.original.resolve();native=a.native.resolve()
    pins={n:sha(ROOT/n) for n in RTL+[TB]}
    rec={'source_pins':pins,'inputs':{str(p):sha(p) for p in [inputs/'keys.mem',inputs/'scores.mem',inputs/'inputs.json',original,native]},'NS':16,'NK':4,'SOURCE_VM_ENABLE':1,'reference_operands':False,'complete_index_qualified':False,'SS_FF_closed':False}
    (a.out/'source.json').write_text(json.dumps(rec,indent=2)+'\n')
    obj=a.out/'obj';vl=os.environ.get('VERILATOR','verilator')
    argv=[vl,'--binary','--timing','-j','16','-O2','--output-split','20000','--output-split-cfuncs','20000','-Wno-fatal','--top-module','tb_hbm_index_connected','-Mdir',str(obj),*[str(ROOT/n) for n in RTL+[TB]]]
    (a.out/'build_argv.json').write_text(json.dumps(argv,indent=2)+'\n')
    with (a.out/'build.log').open('w') as f:rc=subprocess.call(argv,stdout=f,stderr=subprocess.STDOUT)
    (a.out/'build.exit').write_text(str(rc)+'\n')
    if rc:return rc
    argv=[str(obj/'Vtb_hbm_index_connected'),f'+ORIGINAL={original}',f'+NATIVE={native}',f'+KEYS={inputs/"keys.mem"}',f'+SCORES={inputs/"scores.mem"}']
    with (a.out/'runtime.log').open('w') as f:rc=subprocess.call(argv,cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
    (a.out/'runtime.exit').write_text(str(rc)+'\n')
    if rc:return rc
    try:r=compare(a.out,inputs)
    except Exception as e:
        (a.out/'comparison_failure.txt').write_text(str(e)+'\n');return 1
    r['actual_output_hashes']={n:sha(a.out/n) for n in ['topk.txt','candidates.txt','runtime.log']}
    (a.out/'comparison.json').write_text(json.dumps(r,indent=2)+'\n');return 0
if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    e=sub.add_parser('extract');e.add_argument('--snapshot',type=Path,required=True);e.add_argument('--parts',type=Path,required=True);e.add_argument('--out',type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--inputs',type=Path,required=True);r.add_argument('--original',type=Path,required=True);r.add_argument('--native',type=Path,required=True);r.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.mode=='extract':extract(a)
    else:raise SystemExit(run(a))
