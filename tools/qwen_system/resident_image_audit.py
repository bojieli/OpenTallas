"""Streaming immutable released-stage inventory; never modifies source images."""
import argparse,hashlib,json,time
from pathlib import Path
import hdc_isa as ISA

def decode_instruction(word):
    # Same two reserved me_row0 high bits as the fullshape ISA, without
    # importing the unrelated full model/program builder during an inventory.
    fields=ISA.decode(word)
    offset,width=ISA.LAYOUT['me_row0']
    high=offset+width+ISA.LAYOUT['me_amc'][1]
    fields['me_row0']|=((word>>high)&3)<<16
    return fields

def file_record(path):
    sha=hashlib.sha256();count=0;lo=None;hi=0;total=0
    before=path.stat()
    with path.open('rb') as f:
        for line in f:
            sha.update(line);total+=len(line);word=line.strip()
            if not word:continue
            if word.translate(None,b'0123456789abcdefABCDEF'):
                raise ValueError(f'invalid hex payload {path}:{count+1}')
            count+=1;lo=len(word) if lo is None else min(lo,len(word));hi=max(hi,len(word))
    after=path.stat()
    if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
        raise ValueError(f'image changed during inventory: {path}')
    return dict(path=str(path),real_path=str(path.resolve()),sha256=sha.hexdigest(),
        bytes=total,words=count,hex_width_min=lo,hex_width_max=hi,mtime_ns=after.st_mtime_ns)

def audit(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    record=dict(schema='opentallas.qwen-released-resident-image-audit.v1',
        checkpoint_payload_modified=False,root=str(root),tp=4,groups=6144,
        source_contract='original released stage images; resident packing not adopted',
        stage_count=37,embedding_source='separate HBM contract',stages=[],
        code_capacity_words=5*4096,scale_capacity_words=48*4096,
        capacity_basis='code native5banks; scale proposed48banks needs actual physical inventory join',
        remaining=['derive an exact resident address permutation for the actual pinned ISA',
                   'prove same released payload and golden reduction order before selecting compact compiler'])
    # Progress is incremental so a partial inventory remains reviewable.
    with (out/'progress.jsonl').open('x') as progress:
      for name in [f'L{x}' for x in range(36)]+['head']:
        for die in range(4):
          stage=dict(stage=name,die=die,files={})
          directory=root/f'{name}-d{die}'
          for fname in ['matrix_int8.hex','matrix_scale_bf16.hex','crom.hex','program.hex','segments.hex']:
            entry=file_record(directory/fname);stage['files'][fname]=entry
            event=dict(stage=name,die=die,file=fname,**entry)
            progress.write(json.dumps(event)+'\n');progress.flush()
            print(f'PINNED {name} die{die} {fname} words={entry["words"]} width={entry["hex_width_min"]}:{entry["hex_width_max"]} bytes={entry["bytes"]}',flush=True)
          stage['instructions']=[decode_instruction(int(s,16)) for s in (directory/'program.hex').read_text().split()]
          record['stages'].append(stage)
    totals={}
    for die in range(4):
      ss=[s for s in record['stages'] if s['die']==die]
      totals[die]=dict(code=sum(s['files']['matrix_int8.hex']['words'] for s in ss),
        scale=sum(s['files']['matrix_scale_bf16.hex']['words'] for s in ss))
    record['uncompressed_resident_words_per_die']=totals
    record['uncompressed_fits_current_macros']=all(t['code']<=record['code_capacity_words'] and t['scale']<=record['scale_capacity_words'] for t in totals.values())
    (out/'inventory.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS immutable source inventory; resident_fit='+str(record['uncompressed_fits_current_macros']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();audit(a.root,a.out)
