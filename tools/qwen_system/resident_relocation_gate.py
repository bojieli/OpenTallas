"""Construct a byte-preserving resident image from the pinned released ISA.

No checkpoint quantization or numerical operation occurs here.  The relocation
changes only ROM code bases; padded scale bases stay identical to the release.
"""
import argparse, hashlib, json
from pathlib import Path

GROUPS, W, IL = 6144, 16, 8
CODE_ROWS, SCALE_ROWS = 512, 1056
CODE_CAPACITY, SCALE_CAPACITY = 20480, 48*4096

def mapping(stage):
    instructions=[d for d in stage['instructions'] if d['me_nout'] and not d['me_wsrc']]
    if len(instructions)!=4: raise ValueError('expected four released ROM matrices')
    maps=[];newbase=0
    for d in instructions:
        if d['me_mmode'] or d['me_js']!=1 or d['me_ks']!=IL or d['me_ts']!=d['me_k']*IL:
            raise ValueError('unexpected released ROM addressing contract')
        count=d['me_tiles']*d['me_k']*IL
        target=d['me_wbase'] if stage['stage']=='head' else newbase
        maps.append(dict(old=d['me_wbase'],new=target,count=count,fields=d))
        newbase=target+count
    expected=1584 if stage['stage']=='head' else CODE_ROWS
    if newbase!=expected: raise ValueError('incorrect native code capacity')
    return maps

def read_addresses(maps, code_count, scale_count):
    reads=0;maxscale=0
    for m in maps:
        d=m['fields']; ports=GROUPS//(1<<d['me_split'])
        for t in range(d['me_tiles']):
          for j in range(IL):
            for k in range(d['me_k']):
                old=d['me_wbase']+t*d['me_ts']+k*d['me_ks']+j
                new=m['new']+t*d['me_ts']+k*d['me_ks']+j
                if not(m['old']<=old<m['old']+m['count'] and 0<=new<code_count):
                    raise ValueError('code read out of bounds')
                if old-m['old']!=new-m['new']:raise ValueError('code order changed')
                reads+=1
            # Exact captured native scale predicate: last && !wsrc &&
            # GID<ports && nb+GID*W*IL<nout.  Remaining lane masks stay intact.
            nb=t*ports*W*IL+j*W
            for gid in range(ports):
                if nb+gid*W*IL<d['me_nout']:
                    sa=d['me_wcs']+nb//W+gid*IL
                    if not(0<=sa<scale_count):raise ValueError('active scale read out of bounds')
                    maxscale=max(maxscale,sa)
    return reads,maxscale

def pack_file(entry, spans, destination):
    source=Path(entry['real_path']);before=source.stat();full=hashlib.sha256();packed=hashlib.sha256()
    selected=0;words=0
    with source.open('rb') as f, destination.open('xb') as out:
      for index,line in enumerate(f):
        full.update(line);words+=1
        if any(lo<=index<hi for lo,hi in spans):
            payload=bytes.fromhex(line.decode().strip())
            out.write(payload);packed.update(payload);selected+=1
    after=source.stat()
    if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
        raise ValueError('source image changed')
    if full.hexdigest()!=entry['sha256'] or words!=entry['words']:raise ValueError('released image pin mismatch')
    if selected!=sum(hi-lo for lo,hi in spans):raise ValueError('missing selected payload')
    return dict(file=str(destination),sha256=packed.hexdigest(),rows=selected,bytes=destination.stat().st_size,
                source_sha256=entry['sha256'],source_spans=spans)

def run(inventory,out):
    manifest=json.loads(Path(inventory).read_text());out=Path(out);out.mkdir(parents=True,exist_ok=True)
    results=[]
    for stage in manifest['stages']:
        maps=mapping(stage);ncode=1584 if stage['stage']=='head' else CODE_ROWS
        nscale=2376 if stage['stage']=='head' else SCALE_ROWS
        reads,maxscale=read_addresses(maps,ncode,nscale)
        name=f"{stage['stage']}-d{stage['die']}"
        code=pack_file(stage['files']['matrix_int8.hex'],[(m['old'],m['old']+m['count']) for m in maps],out/(name+'.code.bin'))
        scale=pack_file(stage['files']['matrix_scale_bf16.hex'],[(0,nscale)],out/(name+'.scale.bin'))
        # The stream emits each mapped contiguous region in native address order.
        # All active fetches are covered above, including all head continuation chunks.
        result=dict(stage=stage['stage'],die=stage['die'],maps=maps,code=code,scale=scale,
                    code_reads_checked=reads,max_active_scale_address=maxscale)
        results.append(result)
        with (out/'progress.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
        print('PASS',name,'code',ncode,'scale',nscale,'active_max',maxscale,flush=True)
    code_total=36*CODE_ROWS+1584;scale_total=36*SCALE_ROWS+2376
    assert code_total<=CODE_CAPACITY and scale_total<=SCALE_CAPACITY
    # Negative capacity guards must reject the old released all-resident recipe.
    if 36*1056+1584<=CODE_CAPACITY:raise ValueError('old code capacity negative escaped')
    try:read_addresses(mapping(manifest['stages'][0]),CODE_ROWS,SCALE_ROWS-33)
    except ValueError:pass
    else:raise ValueError('truncated scale bounds negative escaped')
    record=dict(schema='opentallas.qwen-native-resident-relocation.v1',verdict='PASS',
        inventory_sha256=hashlib.sha256(Path(inventory).read_bytes()).hexdigest(),stages=results,
        code_rows_per_die=code_total,scale_rows_per_die=scale_total,
        code_capacity_rows=CODE_CAPACITY,scale_capacity_rows=SCALE_CAPACITY,
        code_word_bits=GROUPS*W*8,scale_word_bits=W*16,
        code_bits_per_die=code_total*GROUPS*W*8,scale_bits_per_die=scale_total*W*16,
        relocation='code old0/96/384/768 to0/64/112/368; scale padded bases unchanged',
        checkpoint_requantized=False,all_numerical_fields_and_reduction_order_unchanged=True,
        negatives=['old all-resident code exceeds20480','truncated active scale bounds rejected'],
        limits=['source views and complete native system port binding remain required',
                'controller opt-in must use released padded scale bases0/96/384/768',
                'scale capacity48banks still needs measured physical inventory join'])
    (out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS all148 released stage/rank byte-preserving payload relocations;',code_total,scale_total,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.inventory,a.out)
