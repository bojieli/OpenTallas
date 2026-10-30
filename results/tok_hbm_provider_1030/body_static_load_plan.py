import sys,json,collections,hashlib,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/hbm_next'))
ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--image',type=Path,required=True);a=ap.parse_args()
from isa_loader import load_isa
IR,IC=load_isa()
rp=a.manifest;manifest_raw=rp.read_bytes();meta=json.loads(manifest_raw);raw=a.image.read_bytes();recs=IC.decode_all(raw)
pair=json.loads(Path(__file__).with_name('body_static_source_pair.json').read_text())
if hashlib.sha256(manifest_raw).hexdigest()not in pair['manifest_sha256'] or hashlib.sha256(raw).hexdigest()!=pair['image_sha256']:
 raise ValueError('manifest/image does not match the explicit reviewed selected source pair; publish a new pair before lowering another image')
if len(recs)!=len(meta['records']) or len(recs)!=meta['native_commands'] or len(recs)!=pair['native_commands']:
 raise ValueError('manifest/image record count mismatch')
if meta['source_sha256']!=pair['source_sha256']:raise ValueError('original source image association mismatch')
for (off,rec,rx,encoded),entry in zip(recs,meta['records']):
 if entry['offset']!=off or entry['bytes']!=len(encoded):raise ValueError('manifest/image decoded record offset or size mismatch')
runs=[];holds=[];counts=collections.Counter();rows=0;words=0
for i,((off,r,rx,_),m)in enumerate(zip(recs,meta['records'])):
 if m['kind']!='body' or(r.unit,r.op)!=('DMA','LOAD'):continue
 a,o=r.desc['A'],r.desc['O'];
 if a.space!='HBM' or o.space!='VM':raise ValueError(('unsupported LOAD spaces',i))
 counts[a.fmt+'->'+o.fmt]+=1
 if a.indexed or o.indexed or any(getattr(a,f,0)or getattr(o,f,0)for f in('dyn_sel','n_sel','lstride','l1stride'))or(rx and rx.rsel):
  holds.append(dict(resident_command=i,source_record=m.get('source_record'),offset=off,source_format=a.fmt,base=a.base,layout_code=a.base>>37,base_stack=a.base>>35&3,indexed=bool(a.indexed),I=vars(r.desc['I'])if'I'in r.desc else None,reason='actual runtime index/physical Engram resolver required before resolved227/window assignment'));continue
 if (a.fmt,o.fmt)not in(('FP32','FP32'),('U32','U32'))or a.m!=1 or o.m!=1 or a.n!=o.n or a.ibcast or o.ibcast or a.istride not in(0,1)or o.istride not in(0,1):raise ValueError(('unsupported static shape',i))
 for row,(_,scalar)in enumerate(IR.expand(r,rx)):
  aa,oo=scalar.desc['A'],scalar.desc['O'];src,dst,n=aa.base,oo.base,aa.n;rows+=1;words+=n
  if src>>37 or src%4 or not 0<=dst<dst+n<=262144:raise ValueError(('source/VM domain',i,row))
  while n:
   count=min(n,(2048-src%2048)//4);fmt=0 if a.fmt=='FP32' else 5
   if count==0:raise ValueError('nonword halfwindow')
   start_stack=src>>35&3;local=src&((1<<35)-1)
   if local+count*4>22500000000:raise ValueError(('physical capacity',i,row))
   sector=local>>5;half=((sector>>6)^(sector>>11)^(sector>>16))&1
   desc=(fmt<<2)|(src<<5)|(1<<77)|(1<<93)|(fmt<<95)|(dst<<98)|(1<<170)|(1<<186)|(count<<206)
   # Exact inverse of every field; source/dest first and last preserve scalar row.
   assert(desc>>5&((1<<40)-1))==src and(desc>>98&((1<<40)-1))==dst and(desc>>206)==count
   runs.append(dict(resident_command=i,source_record=m.get('source_record'),ROWX_row=row,source_byte=src,destination_word=dst,n=count,format=a.fmt,stack=start_stack,row=sector>>15,col=sector>>8&15,half=half,effective227=f'{desc:057x}'))
   src+=count*4;dst+=count;n-=count
result=dict(scope='Source-only static original-body LOAD lowering. No epoch reuse, physical dates or fullstack provider adoption; exact native per-record/row order preserved.',image_sha256=hashlib.sha256(raw).hexdigest(),manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),source_pair='body_static_source_pair.json',body_LOAD_records=sum(counts.values()),by_format=dict(counts),static_records=sum(counts.values())-len(holds),static_ROWX_rows=rows,static_words=words,static_effective227_runs=len(runs),source_stacks=sorted(set(r['stack']for r in runs)),sequence_rule='Each source body LOAD is a barrier: complete its ordered scalar rows/window-safe runs before next resident body/STORE; no cross-body reordering. Caller must begin/fill/owned block_ready/release all8 each used buffer epoch.',remaining_indexed_records=len(holds),held=holds,runs=runs)
print(json.dumps(result,indent=1))
