#!/usr/bin/env python3
"""Fail-closed final two-token software gate: actual RC, marker, KV and reader.

No arithmetic is rerun. Compressed raw records must reproduce original bytes.
"""
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
import numpy as np
from qwen_hbm_complete_program import compile_program

def load(directory,name):
    path=Path(directory)/name
    data=gzip.decompress(path.read_bytes()) if name.endswith('.gz') else path.read_bytes()
    return json.loads(data)

def verify_reader(reader,index,config,lock):
    expected={x['path']:x['sha256'] for x in lock['expected_files'] if x['path'].endswith('.safetensors')}
    if reader['verified_shards']!=expected or reader['checkpoint_revision']!=lock['revision']:raise ValueError('locked shard reader provenance')
    if reader['max_source_rows_per_read']!=256 or reader['images_written'] or reader['downloads'] or reader['actual_hardware_memory_provider']:raise ValueError('reader qualification boundary')
    records=defaultdict(list)
    h=config['hidden_size'];hd=config['head_dim'];ff=config['intermediate_size'];v=config['vocab_size']
    shapes={'model.embed_tokens.weight':[v,h],'lm_head.weight':[v,h],'model.norm.weight':[h]}
    for layer in range(config['num_hidden_layers']):
        prefix=f'model.layers.{layer}'
        for name in ('input_layernorm','post_attention_layernorm'):shapes[prefix+'.'+name+'.weight']=[h]
        for name in ('q','k'):shapes[prefix+f'.self_attn.{name}_norm.weight']=[hd]
        for name,rows in [('q',config['num_attention_heads']*hd),('k',config['num_key_value_heads']*hd),('v',config['num_key_value_heads']*hd),('o',h)]:shapes[prefix+f'.self_attn.{name}_proj.weight']=[rows,h]
        for name in ('gate','up'):shapes[prefix+f'.mlp.{name}_proj.weight']=[ff,h]
        shapes[prefix+'.mlp.down_proj.weight']=[h,ff]
    if set(index['weight_map'])!=set(shapes):raise ValueError('checkpoint tensor index geometry')
    for row in reader['reads']:
        key=row['tensor'];shape=row['shape']
        if key not in shapes or shape!=shapes[key] or row['shard']!=index['weight_map'][key]:raise ValueError('read source/shape binding')
        if not re.fullmatch('[0-9a-f]{64}',row['sha256']):raise ValueError('source slice SHA')
        start,stop=row['row_start'],row['row_stop']
        if start is None:
            if stop is not None or len(shape)!=1 or row['bytes']!=shape[0]*2:raise ValueError('vector reader bytes')
            records[key].append((0,shape[0]))
        else:
            if len(shape)!=2 or not 0<=start<stop<=shape[0] or stop-start>256 or row['bytes']!=(stop-start)*shape[1]*2:raise ValueError('bounded matrix reader bytes')
            records[key].append((start,stop))
    if set(records)!=set(shapes):raise ValueError('missing actual checkpoint tensor reads')
    for key,intervals in records.items():
        if key=='model.embed_tokens.weight':
            if set(intervals)!={(9707,9708),(11,12)}:raise ValueError('executed embedding row coverage')
            continue
        cursor=0
        for start,stop in sorted(intervals):
            if start>cursor:raise ValueError('source row coverage gap '+key)
            cursor=max(cursor,stop)
        if cursor!=shapes[key][0]:raise ValueError('incomplete source row coverage '+key)
    return dict(source_reads=len(reader['reads']),bounded_matrix_row_reads=sum(row['row_start'] is not None for row in reader['reads']),whole_constant_vector_reads=sum(row['row_start'] is None for row in reader['reads']),max_matrix_rows_per_read=256,tensors=len(records),full_non_embedding_tensors=len(records)-1,verified_locked_shards=len(expected))

def verify(directory,repo=None):
    directory=Path(directory);r=load(directory,'receipt.json')
    for name,digest in r['artifacts_sha256'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('archive byte hash '+name)
    for name,record in r['original_raw_sha256'].items():
        data=(directory/name).read_bytes();data=gzip.decompress(data) if record['gzip'] else data
        if hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('original worker raw byte identity')
    rc=load(directory,'execution_rc.json');terminal=load(directory,'terminal.json');identity=load(directory,'identity.json');admission=load(directory,'admission.json')
    if rc['actual_returncode']!=0 or rc['guard_breach'] is not None:raise ValueError('actual process RC/guard failure')
    if (rc['pid'],rc['start_ticks'])!=(identity['pid'],identity['start_ticks']):raise ValueError('terminal process identity')
    if not rc['source_commit']==identity['source_commit']==admission['source_commit']==r['source_commit']:raise ValueError('terminal source pin')
    if rc['peak_owned_RSS_bytes']>admission['RSS_limit_bytes']:raise ValueError('owned RSS admission exceeded')
    text=(directory/'run.log').read_text()
    if re.search(r'FATAL|TIMEOUT|Traceback',text):raise ValueError('late fault in actual log')
    try:last=json.loads(text.strip().splitlines()[-1])
    except (ValueError,IndexError):raise ValueError('missing positive terminal marker')
    if last!=terminal or terminal['status']!='CHECKPOINT_SOFTWARE_COMPLETE' or terminal['tokens_completed']!=2 or terminal['layers_per_token']!=36 or not terminal['head_executed']:raise ValueError('missing positive terminal marker')
    old=(directory/r['token0_archive']).resolve();first=load(old,'token0_execution.json');second=load(directory,'token1_execution.json.gz')
    if hashlib.sha256((old/'token0_execution.json').read_bytes()).hexdigest()!=r['token0_execution_sha256']:raise ValueError('immutable token0 dependency')
    if second['post_execution_comparisons'][:39]!=first['post_execution_comparisons'] or len(first['post_execution_comparisons'])!=39 or len(second['post_execution_comparisons'])!=78:raise ValueError('39 comparisons per token cumulative boundary')
    expected=compile_program()['instructions']
    for position,(token,comparisons) in enumerate([(first,first['post_execution_comparisons']),(second,second['post_execution_comparisons'][39:])]):
        if token['position']!=position or token['status']!='SOFTWARE_PROGRAM_COMPLETED' or not token['complete_program_executed'] or not token['fullshape'] or token['instructions_retired']!=1737 or len(token['trace'])!=1737:raise ValueError('complete token instruction retirement')
        for actual,wanted in zip(token['trace'],expected):
            if any(actual[k]!=wanted[k] for k in ('id','opcode','dependencies')) or actual['cycles'] is not None:raise ValueError('instruction/dependency binding')
        if {c['register'] for c in comparisons}!={f'L{layer}.X' for layer in range(36)}|{'head.norm','head.d0.scaled','head.d1.scaled'} or any(c['bit_mismatches'] or c['actual_nonfinite'] or c['reference_nonfinite'] for c in comparisons):raise ValueError('token independent exactness boundaries')
    if first['input_token']!=9707 or second['input_token']!=first['next_token'] or second['next_token']!=terminal['next_token']:raise ValueError('actual autoregressive token chain')
    if second['memory_events'][:len(first['memory_events'])]!=first['memory_events']:raise ValueError('persistent KV event prefix')
    expected_counts={'write_accepted_not_published':72,'software_backing_commit_and_publication':72,'persistent_KV_read':72,'software_reader_lease_acquired':72,'software_consumer_done_after_result':144,'software_reader_lease_released':72}
    for position,events in enumerate([first['memory_events'],second['memory_events'][len(first['memory_events']):]]):
        if dict(Counter(e['event'] for e in events))!=expected_counts:raise ValueError('actual KV publications and leases per token')
        for event in events:
            if event['cycles'] is not None:raise ValueError('software memory assigned hardware clocks')
            if event['event']=='persistent_KV_read' and (event['positions']!=position+1 or event['bytes']!=1024*(position+1)):raise ValueError('second token did not read persistent two-position KV')
    active={};pending={};published=set()
    for event in second['memory_events']:
        kind=event['event']
        if kind=='write_accepted_not_published':
            if event['tag'] in pending:raise ValueError('duplicate write ticket')
            pending[event['tag']]=(event['layer'],event['die'],event['position'])
        elif kind=='software_backing_commit_and_publication':
            if event['tag'] not in pending:raise ValueError('publication before actual software backing')
            published.add(pending.pop(event['tag']))
        elif kind=='persistent_KV_read':
            if any((event['layer'],event['die'],position) not in published for position in range(event['positions'])):raise ValueError('persistent KV read before generation publication')
        elif kind=='software_reader_lease_acquired':
            key=(event['layer'],event['die'],event['position'])
            if key not in published or event['lease'] in active:raise ValueError('reader before generation publication')
            active[event['lease']]=set()
        elif kind=='software_consumer_done_after_result':
            if event['lease'] not in active or event['stage'] in active[event['lease']]:raise ValueError('consumer lease completion')
            active[event['lease']].add(event['stage'])
        elif kind=='software_reader_lease_released':
            if active.get(event['lease'])!={'SCORES','PV'}:raise ValueError('reader released before both consumers')
            del active[event['lease']]
    if active or pending or len(published)!=144:raise ValueError('outstanding persistent KV generation leases')
    hashes=load(directory,'token1_layer_source_npy_sha256.json')
    with zipfile.ZipFile(directory/'token1_layer_outputs.npz') as archive:
        if len(hashes)!=36 or set(archive.namelist())!=set(hashes) or any(hashlib.sha256(archive.read(name)).hexdigest()!=digest for name,digest in hashes.items()):raise ValueError('second token raw layer byte identity')
    with np.load(directory/'token1_layer_outputs.npz',allow_pickle=False) as arrays:
        if any(arrays[name].shape!=(4096,) or not np.isfinite(arrays[name]).all() for name in arrays.files):raise ValueError('second token full layer shape/finite')
    head=[np.load(directory/f'token1_head.d{die}.scaled.npy',allow_pickle=False) for die in range(2)]
    if any(a.shape!=(75968,) or not np.isfinite(a).all() for a in head) or int(np.argmax(np.concatenate(head)))!=second['next_token']:raise ValueError('second token independent full head argmax')
    config=load(directory,'checkpoint_config.json');index=load(directory,'checkpoint_index.json');lock=load(directory,'checkpoint_lock.json')
    for name,original in [('checkpoint_config.json','config.json'),('checkpoint_index.json','model.safetensors.index.json')]:
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=next(x['sha256'] for x in lock['expected_files'] if x['path']==original):raise ValueError('locked checkpoint metadata')
    coverage=verify_reader(load(directory,'checkpoint_reader_provenance.json.gz'),index,config,lock)
    output=load(directory,'instruction_output_hashes.json.gz')
    if {row['position'] for row in output}!={0,1} or any({row['instruction'] for row in output if row['position']==position}!=set(range(1737)) for position in (0,1)):raise ValueError('actual per-operation output hashes')
    outputs={(row['position'],row['register']):row for row in output}
    for position,folder in [(0,old),(1,directory)]:
        with np.load(folder/f'token{position}_layer_outputs.npz',allow_pickle=False) as arrays:
            for layer in range(36):
                a=arrays[f'L{layer:02d}'];row=outputs[position,f'L{layer}.X']
                if row['shape']!=list(a.shape) or row['sha256']!=hashlib.sha256(a.tobytes()).hexdigest():raise ValueError('layer bytes vs actual output trace')
        for die in range(2):
            a=np.load(folder/f'token{position}_head.d{die}.scaled.npy',allow_pickle=False);row=outputs[position,f'head.d{die}.scaled']
            if row['shape']!=list(a.shape) or row['sha256']!=hashlib.sha256(a.tobytes()).hexdigest():raise ValueError('head bytes vs actual output trace')
    if r['actual_RTL_executed'] or r['token_cycles'] is not None or r['token_rate'] is not None or terminal['actual_RTL_executed'] or terminal['fulltoken_RTL']:raise ValueError('software/RTL qualification boundary')
    if repo is not None:
        for name,digest in r['source_sha256'].items():
            if hashlib.sha256(subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=repo)).hexdigest()!=digest:raise ValueError('immutable worker source pin')
    return dict(actual_checkpoint_two_token_software='PASS',actual_returncode=0,layers_each=36,head_each=151936,instructions_each=1737,comparisons_each=39,next_tokens=[first['next_token'],second['next_token']],bit_mismatches=0,source_read_coverage=coverage,persistent_KV_publications=144,reader_leases_released=144,actual_RTL_executed=False,token_cycles=None,token_rate=None)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--repo',type=Path)
    args=parser.parse_args();print(json.dumps(verify(args.archive,args.repo)))
