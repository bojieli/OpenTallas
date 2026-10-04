#!/usr/bin/env python3
"""One-shot terminal continuation for the existing NP4 GPU producer.

Transfers its completed input record, selects exact cached entering embeddings,
and extracts shipped embedding rows only for actual uncached draft tokens.
No producer restart, model, inference, DUT or feature-file transfer occurs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()


def completed(record):
    p=record.get('position');draft=record.get('step1_draft',{});block=record.get('step1',{})
    if not (record.get('schema')=='opentallas.qwen-dspark-oracle-gpu.v1' and
            record.get('mode')=='first_block_inputs' and record.get('tp')==4 and
            record.get('groups')==6144 and record.get('su_width')==1024 and record.get('kv_format')=='fp8' and
            record.get('status')=='actual_draft_inputs_ready' and type(p) is int and 0<p<=8188 and
            record.get('feature_shape')==[p,20480] and record.get('feature_layers')==[1,9,17,25,33] and
            record.get('captured_positions_per_layer')==[p]*5 and record.get('target_feature_sha256') and
            draft.get('start')==p and draft.get('anchor')==record.get('anchor') and
            draft.get('S')==3 and draft.get('kv')=='fp8' and
            block.get('P')==p and block.get('positions')==list(range(p,p+4)) and
            block.get('block_tokens')==[record.get('anchor'),*draft.get('draft_tokens',[])] and
            len(block['block_tokens'])==4 and all(type(t) is int and 0<=t<151936 for t in block['block_tokens'])):
        raise ValueError('producer is not a complete actual NP4 feature/draft input record')
    return block['block_tokens']


def choose_slots(tokens,position,caches):
    """Match both literal position and actual token; missing rows are explicit."""
    chosen=[];missing=[]
    for slot,token in enumerate(tokens):
        match=next((root for root,book in caches if book.get('per_position',{}).get(str(position+slot),{}).get('token')==token),None)
        chosen.append(match)
        if match is None:missing.append(token)
    if chosen[0] is None:raise ValueError('pending input has no original entering-history authority')
    return chosen,sorted(set(missing))


REMOTE_QUERY=r'''
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);receipt=json.loads((root/'actual-producer.json').read_text())
base=json.loads((root/'inputs.json').read_text())
caches=[]
for path,pin in dict(zip(base['oracle_roots'],base['oracle_sha256'])).items():
 p=Path(path)/'oracle.json'
 import hashlib
 assert hashlib.sha256(p.read_bytes()).hexdigest()==pin,'cached input producer changed'
 caches.append((path,json.loads(p.read_text())))
tokens=receipt['step1']['block_tokens'];pos=receipt['position']
missing=sorted(set(token for i,token in enumerate(tokens) if not any(book['per_position'].get(str(pos+i),{}).get('token')==token for _,book in caches)))
assert receipt['prompt_tokens_sha256']==caches[0][1]['tokens_sha256'],'actual prompt/history differs'
assert caches[0][1]['per_position'][str(pos)]['token']==tokens[0],'entering pending/history differs'
print(json.dumps(missing))
'''

REMOTE_PREP=r'''
import hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools'))
import qwen_rom_combined_stream4_layer_prepare as prep
root=Path(sys.argv[1]);receipt_path=root/'actual-producer.json'
r=json.loads(receipt_path.read_text());base=json.loads((root/'inputs.json').read_text())
rows=json.loads((root/'regenerated_rows.json').read_text())
assert rows['release_sha256']==prep.selected.sha(receipt_path)
candidates=[]
for path,pin in dict(zip(base['oracle_roots'],base['oracle_sha256'])).items():
 p=Path(path)/'oracle.json';assert prep.selected.sha(p)==pin
 candidates.append((Path(path),json.loads(p.read_text())))
tokens=r['step1']['block_tokens'];position=r['position'];roots=[];fallback={}
for slot,token in enumerate(tokens):
 found=next((p for p,b in candidates if b['per_position'].get(str(position+slot),{}).get('token')==token),None)
 if found is None:
  assert slot>0,'original pending/history cannot be replaced'
  row=rows['rows'][str(token)];assert row['token']==token
  codes=bytes.fromhex(row['codes_hex']);assert len(codes)==4096
  scale=struct.unpack('<f',struct.pack('<I',int(row['scale_bf16'],16)<<16))[0]
  words=[struct.unpack('<I',struct.pack('<f',(v if v<128 else v-256)*scale))[0] for v in codes]
  fallback[position+slot]=(token,words,row);found=root/'released_embedding_cache'
 roots.append(found)
if fallback:
 cache=root/'released_embedding_cache';cache.mkdir()
 frames={}
 for position_slot,(token,words,row) in fallback.items():
  d=cache/f'P{position_slot}';d.mkdir();p=d/'x_preload.hex'
  p.write_text('@1000\n'+''.join(f'{w:08x}\n' for w in words))
  (d/'embedding_row.json').write_text(json.dumps(row)+'\n')
  frames[str(position_slot)]={'token':token,'x_preload_sha256':prep.selected.sha(p)}
 (cache/'oracle.json').write_text(json.dumps(dict(tp=4,groups=6144,layers=1,per_position=frames,
  status='actual_entering_embedding_bytes',scope='Shipped embedding row lookup only; no target outputs or inference',
  release_sha256=prep.selected.sha(receipt_path),provider_source_sha256=rows['provider_source_sha256']))+'\n')
head=Path('/srv/opentallas-scratch/claude/qwen-dspark-system/img_p4/verify_head_images.json')
# Use the exact original manifest pin already committed with the input bundle.
assert prep.selected.sha(head)==base['input_sha256'][str(head)]
pack=prep.pack_cached_slots(oracle_root=roots[0],oracle_sha256=prep.selected.sha(roots[0]/'oracle.json'),
 slot_oracle_roots=roots,slot_oracle_sha256=[prep.selected.sha(p/'oracle.json') for p in roots],
 position=position,layer=0,head_manifest=head,head_manifest_sha256=prep.selected.sha(head),output=root/'actual_release_inputs')
images=Path('/srv/opentallas-scratch/claude/qwen-dspark-system/img_p4')
result=prep.prepare_accept_head(release=receipt_path,release_sha256=prep.selected.sha(receipt_path),step='step1',
 decoder_sources=[images/f'L0-d{i}' for i in range(4)],decoder_images=[root/f'images/L0-d{i}' for i in range(4)],
 head_images=[images/f'head-d{i}' for i in range(4)],head_manifest=head,head_manifest_sha256=prep.selected.sha(head),
 preload=Path(pack['preload']),preload_sha256=pack['preload_sha256'],history=Path(pack['history']),
 layer=0,output=root/'actual_release_plan',oracle_root=roots[0],oracle_sha256=prep.selected.sha(roots[0]/'oracle.json'),
 slot_oracle_roots=roots,slot_oracle_sha256=[prep.selected.sha(p/'oracle.json') for p in roots])
print(json.dumps(result))
'''


def remote(args,code):
    command='source ~/.opentallas-env && cd '+shlex.quote(str(args.remote_source))+' && python3 - '+shlex.quote(str(args.remote_root))
    return subprocess.run(['ssh',args.host,command],input=code,text=True,capture_output=True,check=True).stdout


def run(args):
    # A single wait on the existing producer receipt. Never spawn a producer.
    lock=args.control/'continuation.lock'
    with lock.open('x') as stream:stream.write(str(os.getpid())+'\n')
    while not args.exit_file.exists():
        if not (Path('/proc')/str(args.producer_pid)).exists():
            time.sleep(1)
            if not args.exit_file.exists():raise RuntimeError('producer vanished without a terminal receipt')
        time.sleep(30)
    if args.exit_file.read_text().strip()!='0':raise RuntimeError('producer failed; preserved outputs; no retry')
    receipt=args.producer_root/'oracle.json';record=json.loads(receipt.read_text());tokens=completed(record)
    if (Path(record['target_feature_file']).resolve()!=(args.producer_root/'target_features.npy').resolve() or
            sha(Path(record['target_feature_file']))!=record['target_feature_sha256']):
        raise ValueError('completed feature digest differs; no input preparation')
    for name,digest in record['source_sha256'].items():
        if sha(args.source_root/name)!=digest:raise ValueError('producer source pin differs: '+name)
    subprocess.run(['scp',str(receipt),args.host+':'+str(args.remote_root/'actual-producer.json')],check=True)
    missing=json.loads(remote(args,REMOTE_QUERY))
    rows={};provider_pins={}
    if missing:
        # Static row extraction only, after the GPU producer has completed.
        # No target/draft model, inference, GPU allocation or kernel is created.
        for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
            os.environ[key]='1'
        sys.path.insert(0,str(args.source_root/'tools'))
        import torch
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        from hdc_qwen_int8_image import shipped_vocab_rows
        for token in missing:
            row=shipped_vocab_rows(args.snapshot,'embedding',start=token,count=1)
            rows[str(token)]=dict(token=token,codes_hex=row['codes'].view(torch.uint8).numpy().tobytes().hex(),
                                 scale_bf16=f"{int(row['scales'].view(torch.int16).numpy().reshape(-1)[0])&65535:04x}",
                                 snapshot=str(args.snapshot),source='model.embed_tokens.weight',global_start=token,count=1)
        provider_pins={name:sha(args.source_root/name) for name in ('tools/hdc_qwen_int8_image.py','tools/qwen3_deployment_quality.py')}
        provider_pins[str(args.snapshot/'model.safetensors.index.json')]=sha(args.snapshot/'model.safetensors.index.json')
    exported=args.control/'regenerated_rows.json'
    exported.write_text(json.dumps(dict(release_sha256=sha(receipt),rows=rows,provider_source_sha256=provider_pins))+'\n')
    subprocess.run(['scp',str(exported),args.host+':'+str(args.remote_root/'regenerated_rows.json')],check=True)
    result=remote(args,REMOTE_PREP);print(result,flush=True)
    (args.control/'continuation.result.json').write_text(result)
    with Path('/tmp/claude-review-20261003/codex_notes.txt').open('a') as stream:
        stream.write('\nDEWEY NP4 actual terminal continuation READY: '+result+'\nNo DUT/model launched; feature array retained local, actual input receipt transferred.\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--producer-pid',type=int,default=29297)
    p.add_argument('--producer-root',type=Path,default=Path('/home/ubuntu/dewey-qwen-np4-producer-P8187-r1'))
    p.add_argument('--control',type=Path,default=Path('/tmp/dewey-qwen-np4-producer-inputs'))
    p.add_argument('--exit-file',type=Path,default=Path('/tmp/dewey-qwen-np4-producer-inputs/producer.exit'))
    p.add_argument('--host',default='ot-epyc1tb')
    p.add_argument('--source-root',type=Path,default=Path('/home/ubuntu/OpenTallas-qwen-np4-producer-7fb3770d8'))
    p.add_argument('--remote-source',type=Path,default=Path('/srv/opentallas/repos/dewey-qwen-np4-prep-20261004'))
    p.add_argument('--remote-root',type=Path,default=Path('/srv/opentallas-scratch/codex/qwen-tagged-P8187-np4-inputs-r1'))
    p.add_argument('--snapshot',type=Path,default=Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218')
    run(p.parse_args())

if __name__=='__main__':main()
