#!/usr/bin/env python3
"""Reuse the exact cached P8191 input preparer with the STREAM4 source selection."""
import argparse
import json
import sys
from pathlib import Path
import qwen_rom_combined_nearbaseline_layer_prepare as predecessor
import qwen_rom_combined_stream4_runtime_emit as runtime
import qwen_rom_combined_stream4_selection as selected


def _cached_slot_frames(oracle_root,oracle_sha256,slot_roots,slot_hashes,position,npos,layer):
    """Bind each entering slot independently; never splice a draft receipt."""
    selected.require(type(position) is int and type(npos) is int and
                     1<=npos<=4 and 0<=position and position+npos<=8192,
                     'actual slot block exceeds 8192-position storage')
    selected.require(type(layer) is int and 0<=layer<36,'actual decoder layer required')
    roots=list(slot_roots) if slot_roots is not None else [oracle_root]*npos
    hashes=list(slot_hashes) if slot_hashes is not None else [oracle_sha256]*npos
    selected.require(len(roots)==len(hashes)==npos and
                     Path(roots[0]).resolve()==Path(oracle_root).resolve() and hashes[0]==oracle_sha256,
                     'one pinned cache per slot; first slot owns entering history')
    roots=[Path(p).resolve(strict=True) for p in roots];paths=[];frames=[]
    for slot,(directory,digest) in enumerate(zip(roots,hashes)):
        path=directory/'oracle.json'
        selected.require(selected.sha(path)==digest,'actual cached slot producer changed')
        record=json.loads(path.read_text())
        selected.require(record.get('tp')==4 and record.get('groups')==6144 and
                         layer<record.get('layers',0),'actual cached TP4 layer inputs required')
        frame=record.get('per_position',{}).get(str(position+slot))
        selected.require(isinstance(frame,dict) and type(frame.get('token')) is int and
                         0<=frame['token']<(1<<18),'actual cached position/token input missing')
        paths.append(path);frames.append(frame)
    return roots,paths,frames


def pack_cached_slots(*,oracle_root,oracle_sha256,slot_oracle_roots,slot_oracle_sha256,
                      position,layer,head_manifest,head_manifest_sha256,output):
    """Lossless entering-X/KV packing only. This does not authorize ACCEPT.

    Different cached runs can supply embeddings of different draft tokens.
    Only slot zero supplies entering history; later-run KV and current-layer
    outputs are never copied. A separate real drafter output is still required.
    """
    import numpy as np
    output=Path(output);head_manifest=Path(head_manifest)
    selected.require(not output.exists(),'fresh cached-slot output required')
    selected.require(selected.sha(head_manifest)==head_manifest_sha256,'actual HEAD manifest changed')
    head=json.loads(head_manifest.read_text());npos=head.get('p')
    roots,paths,frames=_cached_slot_frames(oracle_root,oracle_sha256,slot_oracle_roots,
                                         slot_oracle_sha256,position,npos,layer)
    entries=head.get('head',[])
    selected.require(len(entries)==4 and sorted(h.get('die') for h in entries)==list(range(4)),
                     'all four actual HEAD rank layouts required')
    bases=entries[0].get('x_bases')
    selected.require(isinstance(bases,list) and len(bases)==npos and
                     all(type(b) is int and 0<=b and b+4096<=1048576 for b in bases) and
                     all(h.get('x_bases')==bases for h in entries) and
                     all(abs(a-b)>=4096 for i,a in enumerate(bases) for b in bases[i+1:]),
                     'literal HEAD slot addresses overlap or differ across ranks')
    pins={str(p.resolve()):selected.sha(p) for p in [head_manifest,*paths]}
    slots=[]
    for slot,(directory,frame) in enumerate(zip(roots,frames)):
        variants=[]
        for rank in range(4 if layer else 1):
            incoming=directory/f'P{position+slot}'/('x_preload.hex' if layer==0 else f'L{layer-1:02d}_die{rank}_x.hex')
            pin=frame['x_preload_sha256'] if layer==0 else frame['layer_x_sha256'][f'L{layer-1}_die{rank}']
            selected.require(selected.sha(incoming)==pin,'actual entering producer changed')
            words=[w for w in incoming.read_text().split() if not w.startswith('@')]
            selected.require(len(words)==4096 and all(len(w)<=8 and 0<=int(w,16)<(1<<32) for w in words),
                             'actual entering X must contain 4096 raw32 words')
            variants.append([int(w,16) for w in words]);pins[str(incoming.resolve())]=pin
        selected.require(all(v==variants[0] for v in variants),'rank entering-X differs')
        slots.append(variants[0])
    histories=[]
    for rank in range(4):
        source=roots[0]/f'P{position}'/'kv_pre'/f'L{layer}_die{rank}.npy'
        pin=frames[0]['kv_pre_sha256'][f'L{layer}_die{rank}']
        selected.require(selected.sha(source)==pin,'actual entering KV source changed')
        array=np.load(source,mmap_mode='r',allow_pickle=False)
        selected.require(array.dtype==np.dtype('<u4') and array.flags.c_contiguous and array.nbytes==16777216,
                         'actual little-endian contiguous full KV extent required')
        histories.append(array);pins[str(source.resolve())]=pin
    # All source checks precede materialization. This is byte packing, not inference.
    output.mkdir();history=output/'history';history.mkdir()
    preload=output/'x_preload.hex'
    preload.write_text(''.join(f'@{base:x}\n'+''.join(f'{w:08x}\n' for w in words)
                               for base,words in zip(bases,slots)))
    for rank,array in enumerate(histories):
        path=history/f'L{layer}_die{rank}.bin'
        with path.open('wb') as stream:stream.write(memoryview(array).cast('B'))
        predecessor.raw_matches_npy(path,roots[0]/f'P{position}'/'kv_pre'/f'L{layer}_die{rank}.npy')
    selected.require(all(selected.sha(p)==digest for p,digest in pins.items()),'cached source changed during packing')
    result=dict(status='actual_cached_slots_ready',position=position,layer=layer,
                tokens=[frame['token'] for frame in frames],npos=npos,
                preload=str(preload.resolve()),preload_sha256=selected.sha(preload),
                history=str(history.resolve()),oracle_roots=list(map(str,roots)),
                oracle_sha256=[selected.sha(p) for p in paths],input_sha256=pins,
                scope='Entering bytes only; released drafter output absent; no ACCEPT authorization or expected outputs')
    (output/'inputs.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def prepare_accept_head(*, release, release_sha256, step, decoder_sources,
                        decoder_images, head_images, head_manifest,
                        head_manifest_sha256, preload, preload_sha256,
                        history, layer, output, oracle_root, oracle_sha256, root=runtime.ROOT,
                        slot_oracle_roots=None, slot_oracle_sha256=None):
    """Prepare actual VPOS inputs only; no model/run or numerical computation.

    Pending/drafts come from the retained released-drafter step receipt or a
    pinned pending-only cached input record, never argmax/expected-head fields.
    The original and near-rewritten decoder words
    plus the owner's HEAD manifest establish the matching physical X layout.
    """
    release,head_manifest,preload,history,output=map(Path,(release,head_manifest,preload,history,output))
    root=Path(root)
    selected.require(not output.exists() and step in ('step1','step2') and 0<=layer<36,
                     'fresh output, actual released step and decoder layer required')
    selected.require(selected.sha(release)==release_sha256,'released draft receipt changed')
    record=json.loads(release.read_text())
    if record.get('schema')=='opentallas.qwen-rom-dspark-drafter-golden.v1':
        # Actual retained released-checkpoint drafter receipt (P49), not the
        # verify-head oracle. Its produced FP8 S3 tokens are valid input only
        # with the SAME cached context/entering payload; never migrate to P8191.
        runs=[r for r in record.get('steps',[]) if r.get('S')==3 and r.get('kv')=='fp8']
        selected.require(len(runs)==1 and runs[0].get('tokens_equal') is True,
                         'retained released FP8 S3 producer receipt missing')
        actual_drafts=runs[0].get('golden_tokens')
        source={'P':record.get('start')}
        tokens=[record.get('anchor'),*(actual_drafts or [])]
    elif record.get('status')=='actual_input_bytes_ready':
        # A one-position checkpoint has no drafts. Reuse the existing pinned
        # cached producer's pending token and entering frame, not a target or
        # a fabricated speculative step receipt.
        selected.require(record.get('layer')==layer and
                         Path(record.get('oracle','')).resolve()==(Path(oracle_root)/'oracle.json').resolve() and
                         record.get('oracle_sha256')==oracle_sha256 and
                         Path(record.get('preload','')).resolve()==preload.resolve() and
                         record.get('preload_sha256')==preload_sha256,
                         'actual single-position cached producer binding differs')
        source={'P':record.get('position')}
        tokens=[record.get('token')];actual_drafts=[]
    else:
        source=record.get(step);draft=record.get(step+'_draft')
        selected.require(isinstance(source,dict) and isinstance(draft,dict),
                         'released pending/draft step receipt absent; targets cannot supply drafts')
        tokens=source.get('block_tokens');actual_drafts=draft.get('draft_tokens')
        selected.require(record.get('schema')=='opentallas.qwen-dspark-oracle-gpu.v1' and
                         draft.get('start')==source.get('P') and isinstance(tokens,list) and tokens and
                         draft.get('anchor')==tokens[0] and draft.get('kv')=='fp8' and
                         draft.get('S')==len(tokens)-1,
                         'actual drafter start/anchor/precision differs from verify inputs')
    selected.require(isinstance(tokens,list) and 1<=len(tokens)<=4 and
                     all(type(t) is int and 0<=t<(1<<18) for t in tokens) and
                     tokens[1:]==actual_drafts,'actual pending/draft identity or VPMAX4 extent differs')
    position=source.get('P')
    selected.require(type(position) is int and 0<=position and position+len(tokens)<=8192,
                     'released verify block exceeds actual 8192-position storage')
    oracle_roots,oracle_paths,frames=_cached_slot_frames(
        oracle_root,oracle_sha256,slot_oracle_roots,slot_oracle_sha256,
        position,len(tokens),layer)
    for slot,token in enumerate(tokens):
        selected.require(frames[slot].get('token')==token,
                         'released pending/draft has no matching cached position/token input')
    selected.require(selected.sha(head_manifest)==head_manifest_sha256 and
                     selected.sha(preload)==preload_sha256,'actual HEAD manifest/entering payload changed')
    head=json.loads(head_manifest.read_text())
    selected.require(head.get('p')==len(tokens) and len(head.get('head',[]))==4,
                     'actual HEAD position count differs; single-position head cannot be relabelled')
    selected.require(len(decoder_sources)==len(decoder_images)==len(head_images)==4,
                     'four source/decoder/HEAD ranks required')
    old_path=sys.path[:]
    try:
        sys.path.insert(0,str(root))
        from tools.runtime.qwen_combined import attention_descriptors_vp as descriptors
        from tools import hdc_isa as isa
    finally:sys.path[:]=old_path
    pins={str(p.resolve()):selected.sha(p) for p in (release,head_manifest,preload,*oracle_paths)}
    def hex_memory(path):
        words={};address=0
        for word in Path(path).read_text().split():
            if word.startswith('@'):address=int(word[1:],16);continue
            selected.require(len(word)<=8 and address not in words,'actual preload word/duplicate address')
            words[address]=int(word,16);address+=1
        return words
    entered=hex_memory(preload)
    decoder_dirs=[];head_dirs=[]
    for rank,(original,near,hdir) in enumerate(zip(decoder_sources,decoder_images,head_images)):
        original,near,hdir=map(lambda p:Path(p).resolve(strict=True),(original,near,hdir))
        words,desc,slots=descriptors.derive(
            [int(w,16) for w in (original/'program.hex').read_text().split()],
            [int(w,16) for w in (original/'segments.hex').read_text().split()],
            npos=len(tokens),enable=True)
        selected.require(words==[int(w,16) for w in (near/'program.hex').read_text().split()] and
                         desc==[int(w,16) for w in (near/'segments.hex').read_text().split()],
                         'actual near decoder differs from retained VPOS source')
        selected.require([((s['attn_base']<<24)|s['qr_base']) for s in slots]==
                         [int(w,16) for w in (near/'near_slot_bases.hex').read_text().split()],
                         'actual near slot layout differs')
        h=next((entry for entry in head['head'] if entry['die']==rank),None)
        selected.require(h is not None and selected.sha(hdir/'program.hex')==h['program_sha256'] and
                         selected.sha(hdir/'segments.hex')==h['segments_sha256'], 'actual HEAD source pins differ')
        # The real normalization instruction reads each carried decoder X.
        # Require its literal address for every POS_OFF slot, not a range check.
        decoder_x={};head_x={}
        for path,found in ((original/'program.hex',decoder_x),(hdir/'program.hex',head_x)):
            for word in map(lambda w:int(w,16),path.read_text().split()):
                op=isa.decode(word);slot=(word>>900)&7
                if op['unit']==isa.UNIT_SU and slot not in found:
                    found[slot]=op['a_base']
        selected.require([decoder_x.get(i) for i in range(len(tokens))]==h['x_bases'] and
                         [head_x.get(i) for i in range(len(tokens))]==h['x_bases'],
                         'literal decoder/HEAD entering X layout differs')
        for slot,base in enumerate(h['x_bases']):
            frame=frames[slot];posdir=oracle_roots[slot]/f'P{position+slot}'
            incoming=posdir/('x_preload.hex' if layer==0 else f'L{layer-1:02d}_die{rank}_x.hex')
            expected_pin=frame['x_preload_sha256'] if layer==0 else frame['layer_x_sha256'][f'L{layer-1}_die{rank}']
            selected.require(selected.sha(incoming)==expected_pin,'actual entering slot producer changed')
            original_x=list(hex_memory(incoming).values())
            selected.require(len(original_x)==4096 and
                             [entered.get(base+i) for i in range(4096)]==original_x,
                             'prepared slot bytes differ from actual entering producer')
            pins[str(incoming.resolve())]=selected.sha(incoming)
        for name in ('matrix_int8.hex','matrix_scale_bf16.hex','crom.hex'):
            selected.require((near/name).resolve()==(original/name).resolve(),
                             'decoder matrix/constants must retain actual source homes')
        for directory in (original,near,hdir):
            for name in ('program.hex','segments.hex','matrix_int8.hex','matrix_scale_bf16.hex','crom.hex'):
                pins[str(directory/name)]=selected.sha(directory/name)
        pins[str(near/'near_slot_bases.hex')]=selected.sha(near/'near_slot_bases.hex')
        raw=history/f'L{layer}_die{rank}.bin'
        selected.require(raw.stat().st_size==16777216,'actual full raw KV history required')
        npy=oracle_roots[0]/f'P{position}'/'kv_pre'/f'L{layer}_die{rank}.npy'
        selected.require(selected.sha(npy)==frames[0]['kv_pre_sha256'][f'L{layer}_die{rank}'],
                         'entering KV context source differs')
        predecessor.raw_matches_npy(raw,npy)
        pins[str(npy.resolve())]=selected.sha(npy)
        pins[str(raw.resolve())]=selected.sha(raw)
        decoder_dirs.append(str(near));head_dirs.append(str(hdir))
    output.mkdir()
    stages=output/'stages.txt'
    stages.write_text('ACCEPT '+' '.join(map(str,tokens))+'\n'+
                      ' '.join([f'L{layer}',*decoder_dirs,'0'])+'\n'+
                      ' '.join(['head',*head_dirs,'0'])+'\n')
    inputs=dict(status='prepared',position=position,token=tokens[0],npos=len(tokens),
                stages=str(stages.resolve()),preload=str(preload.resolve()),history=str(history.resolve()),
                input_sha256=pins,scope='Actual pending-only cached decoder->HEAD input preparation; unexecuted'
                if record.get('status')=='actual_input_bytes_ready' else
                'Actual released-draft decoder->HEAD input preparation only; unexecuted')
    (output/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    return inputs


def prepare_full_decoder(*, prepared_inputs, decoder_stage_list, full_history_inputs, output):
    """Extend authorized L0->HEAD inputs; carry RTL X through all 36 layers.

    Decoder sources are the existing owner VPOS compiler's per-layer images.
    Only past KV is consumed from the existing fulltoken cache receipt. No
    cached current-layer X or expected HEAD value enters this plan.
    """
    prepared_inputs,decoder_stage_list,full_history_inputs,output=map(
        Path,(prepared_inputs,decoder_stage_list,full_history_inputs,output))
    selected.require(not output.exists(),'fresh full decoder output required')
    entered=json.loads(prepared_inputs.read_text())
    selected.require(entered['status']=='prepared','authorized L0/HEAD inputs required')
    for path,pin in entered['input_sha256'].items():
        selected.require(selected.sha(path)==pin,'authorized entering input changed: '+path)
    plan=Path(entered['stages']).read_text().splitlines()
    selected.require(len(plan)==3 and plan[0].split()[0]=='ACCEPT' and
                     plan[1].split()[0]=='L0' and plan[2].split()[0]=='head',
                     'existing actual ACCEPT/L0/HEAD plan required')
    tokens=list(map(int,plan[0].split()[1:]));npos=len(tokens)
    selected.require(npos==entered['npos'] and 1<=npos<=4 and
                     tokens[0]==entered['token'] and entered['position']+npos<=8192,
                     'authorized slot extent differs')
    history=json.loads(full_history_inputs.read_text())
    selected.require(history['schema']=='opentallas.qwen-rom-full36-inputs.v1' and
                     history['position']==entered['position'] and history['token']==entered['token'],
                     'full history must match actual pending position/token')
    selected.require(set(history['history'])=={f'L{l}_die{r}' for l in range(36) for r in range(4)},
                     'all 144 actual past-history bindings required')
    rawdir=Path(history['history_directory']).resolve(strict=True)
    oracle=Path(history['oracle']['root'])/'oracle.json'
    selected.require(selected.sha(oracle)==history['oracle']['sha256'],'past history source changed')
    frame=json.loads(oracle.read_text())['per_position'][str(entered['position'])]
    selected.require(frame['token']==tokens[0],'past history pending token differs')
    for rank in range(4):
        key=f'L0_die{rank}'
        selected.require(selected.sha(Path(entered['history'])/(key+'.bin'))==
                         history['history'][key]['raw_sha256'], 'L0 history differs from authorized inputs')
    pins=dict(entered['input_sha256'])
    pins[str(oracle.resolve())]=history['oracle']['sha256']
    for path in (prepared_inputs,decoder_stage_list,full_history_inputs,Path(entered['stages'])):
        pins[str(path.resolve())]=selected.sha(path)
    for key,binding in history['history'].items():
        raw=Path(binding['raw']).resolve(strict=True)
        selected.require((rawdir/(key+'.bin')).resolve(strict=True)==raw and
                         raw.stat().st_size==16777216 and selected.sha(raw)==binding['raw_sha256'] and
                         binding['source_sha256']==frame['kv_pre_sha256'][key],
                         'actual full history raw binding differs: '+key)
        pins[str(raw)]=binding['raw_sha256']
    rows=[line.split() for line in decoder_stage_list.read_text().splitlines() if line.strip()]
    selected.require(len(rows)==36 and all(len(row)==6 and row[0]==f'L{l}' and row[-1]=='0'
                     for l,row in enumerate(rows)), 'actual L0..L35 source list, no KV reset, required')
    sys.path.insert(0,str(runtime.ROOT))
    try:
        from tools.runtime.qwen_combined import attention_descriptors_vp as descriptors
        from tools import hdc_isa as isa
    finally:sys.path.pop(0)
    def x_bases(path):
        found={}
        for word in map(lambda w:int(w,16),path.read_text().split()):
            op=isa.decode(word);slot=(word>>900)&7
            if op['unit']==isa.UNIT_SU and slot not in found:found[slot]=op['a_base']
        return [found.get(slot) for slot in range(npos)]
    heads=plan[2].split()[1:5]
    carried=[x_bases(Path(directory)/'program.hex') for directory in heads]
    selected.require(all(None not in bases for bases in carried),'actual HEAD slot X bases required')
    # Preflight literal per-layer X layout before materializing any images.
    for row in rows:
        for rank,directory in enumerate(row[1:5]):
            selected.require(x_bases(Path(directory)/'program.hex')==carried[rank],
                             'decoder entering X does not match carried slot layout: '+row[0])
            for name in ('program.hex','segments.hex','matrix_int8.hex','matrix_scale_bf16.hex','crom.hex'):
                path=Path(directory)/name;pins[str(path.resolve())]=selected.sha(path)
    output.mkdir()
    lines=[plan[0]]
    for layer,row in enumerate(rows):
        directories=[]
        for rank,source in enumerate(row[1:5]):
            destination=output/'images'/f'L{layer}'/f'die{rank}'
            descriptors.emit(source,destination,npos=npos,enable=True)
            # Layer zero must be the exact already-authorized component image.
            if layer==0:
                old=Path(plan[1].split()[rank+1])
                for name in ('program.hex','segments.hex','near_slot_bases.hex'):
                    selected.require((old/name).read_bytes()==(destination/name).read_bytes(),
                                     'full decoder L0 differs from authorized producer binding')
            directories.append(str(destination.resolve()))
        lines.append(' '.join([f'L{layer}',*directories,'0']))
    lines.append(plan[2])
    stages=output/'stages.txt';stages.write_text('\n'.join(lines)+'\n')
    result=dict(entered,stages=str(stages.resolve()),history=str(rawdir),input_sha256=pins,
                full_decoder=True,layers=list(range(36)),
                scope='Actual entering embeddings + past KV; RTL X carry L0..L35/HEAD; unexecuted')
    (output/'inputs.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def prepare(*args,**kwargs):
    old_runtime,old_selection=predecessor.runtime,predecessor.selected
    try:
        predecessor.runtime=runtime;predecessor.selected=selected
        return predecessor.prepare(*args,**kwargs)
    finally:
        predecessor.runtime=old_runtime;predecessor.selected=old_selection


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full-decoder',action='store_true')
    for key in ('prepared-inputs','decoder-stage-list','full-history-inputs'):p.add_argument('--'+key,type=Path)
    p.add_argument('--accept-head',action='store_true')
    p.add_argument('--pack-cached-slots',action='store_true')
    p.add_argument('--position',type=int)
    p.add_argument('--slot-oracle-roots',nargs='+',type=Path)
    p.add_argument('--slot-oracle-sha256',nargs='+')
    for key in ('selection','oracle-root','history','output'):p.add_argument('--'+key,type=Path,required=key=='output')
    p.add_argument('--oracle-sha256');p.add_argument('--layer',type=int)
    p.add_argument('--images',nargs=4,type=Path)
    for key in ('release','head-manifest','preload'):p.add_argument('--'+key,type=Path)
    for key in ('release-sha256','head-manifest-sha256','preload-sha256'):p.add_argument('--'+key)
    p.add_argument('--step',choices=('step1','step2'),default='step1')
    p.add_argument('--decoder-sources',nargs=4,type=Path);p.add_argument('--head-images',nargs=4,type=Path)
    a=p.parse_args()
    if not a.full_decoder and a.layer is None:p.error('actual --layer required')
    if a.full_decoder:
        if a.accept_head or a.pack_cached_slots:p.error('full decoder extends an existing prepared plan')
        for key in ('prepared_inputs','decoder_stage_list','full_history_inputs'):
            if getattr(a,key) is None:p.error('actual --'+key.replace('_','-')+' required')
        print(json.dumps(prepare_full_decoder(prepared_inputs=a.prepared_inputs,
            decoder_stage_list=a.decoder_stage_list,full_history_inputs=a.full_history_inputs,output=a.output)))
    elif a.pack_cached_slots:
        if a.accept_head:p.error('pack entering bytes separately from ACCEPT authorization')
        for key in ('position','head_manifest','head_manifest_sha256','oracle_root','oracle_sha256',
                    'slot_oracle_roots','slot_oracle_sha256'):
            if getattr(a,key) is None:p.error('actual --'+key.replace('_','-')+' required')
        print(json.dumps(pack_cached_slots(oracle_root=a.oracle_root,oracle_sha256=a.oracle_sha256,
            slot_oracle_roots=a.slot_oracle_roots,slot_oracle_sha256=a.slot_oracle_sha256,
            position=a.position,layer=a.layer,head_manifest=a.head_manifest,
            head_manifest_sha256=a.head_manifest_sha256,output=a.output)))
    elif a.accept_head:
        for key in ('release','release_sha256','head_manifest','head_manifest_sha256','preload','preload_sha256','history',
                    'decoder_sources','head_images','oracle_root','oracle_sha256','images'):
            if getattr(a,key) is None:p.error('actual --'+key.replace('_','-')+' required')
        print(json.dumps(prepare_accept_head(release=a.release,release_sha256=a.release_sha256,step=a.step,
            decoder_sources=a.decoder_sources,decoder_images=a.images,head_images=a.head_images,
            head_manifest=a.head_manifest,head_manifest_sha256=a.head_manifest_sha256,
            preload=a.preload,preload_sha256=a.preload_sha256,history=a.history,layer=a.layer,output=a.output,
            oracle_root=a.oracle_root,oracle_sha256=a.oracle_sha256,
            slot_oracle_roots=a.slot_oracle_roots,slot_oracle_sha256=a.slot_oracle_sha256)))
    else:
        if not(a.selection and a.oracle_root and a.oracle_sha256 and a.images and a.history):p.error('actual selection/oracle pins required')
        command,_=prepare(selection=a.selection,oracle_root=a.oracle_root,oracle_sha256=a.oracle_sha256,
            history=a.history,output=a.output,layer=a.layer,images=a.images)
        print(json.dumps(dict(command=command,status='prepared')))
