#!/usr/bin/env python3
"""Rebuild semantic constant operands from actual all40 CROM manifests; never export as runnable."""
import argparse,gzip,hashlib,json,pathlib,subprocess
import w11_dsrom_full_tp_program as F
import w11_dsrom_full_tp_program_constants as W
ROOT=pathlib.Path(__file__).resolve().parents[1];EVIDENCE='70f73928f';DIR='results/uarch/w11_dsrom_crom_writer_20261001/'
def object_bytes(path):return subprocess.check_output(['git','show',EVIDENCE+':'+DIR+path],cwd=ROOT)
def intake():
 raw=gzip.decompress(object_bytes('manifest.json.gz'));m=json.loads(raw)
 assert m['writer_sha256']==hashlib.sha256((ROOT/'tools/w11_dsrom_full_tp_program_constants.py').read_bytes()).hexdigest()
 assert hashlib.sha256(gzip.decompress(object_bytes('source_manifest.json.gz'))).hexdigest()==m['source_manifest_sha256']
 for r in m['rank_images']:
  data=gzip.decompress(object_bytes(r['image']+'.gz'))
  assert hashlib.sha256(data).hexdigest()==r['image_sha256'] and len(data)==r['image_bytes']
  assert r['used_words']==508800 and len(r['constants'])==409
 return m,hashlib.sha256(raw).hexdigest()
def names(layer):
 p=f'layers.{layer}.'
 return {f'L{layer}.'+k:p+v for k,v in {'attn_norm':'attn_norm.weight','ffn_norm':'ffn_norm.weight','q_norm':'attn.q_norm.weight','kv_norm':'attn.kv_norm.weight','attn_sink':'attn.attn_sink','gate_bias':'ffn.gate.bias','hc_attn_scale':'hc_attn_scale','hc_attn_base':'hc_attn_base','hc_ffn_scale':'hc_ffn_scale','hc_ffn_base':'hc_ffn_base','cnorm':'attn.compressor.norm.weight','knorm':'attn.indexer.k_norm.weight'}.items()}
class BoundBuilder(F.FullLayerBuilder):
 def __init__(self,layer,record):
  super().__init__(layer);self.record=record;self.roles=names(layer)
  self.lay.constant_bases={k:record['constants'][v]['base_word'] for k,v in self.roles.items() if v in record['constants']}
 def rms_out(self,src,n,r,w,dst,tag,pred=0,sq=None):
  if tag.endswith('.attn_norm'):key='attn_norm'
  elif tag.endswith('.ffn_norm'):key='ffn_norm'
  elif src=='QA' and dst=='QR':key='q_norm'
  elif src=='KVA' and dst=='KVN':key='kv_norm'
  elif src in ('POOL','CKA') and dst=='LAT':key='cnorm'
  elif src=='IKA' and dst=='IKN':key='knorm'
  else:raise ValueError(f'unresolved norm semantic role {src}/{dst}/{tag}')
  name=self.roles[f'L{self.layer}.{key}'];entry=self.record['constants'][name]
  if entry['word_count']!=n:raise ValueError('norm coefficient extent mismatch')
  return super().rms_out(src,n,r,entry['base_word'],dst,tag,pred,sq)
def operand_bindings(inst,record,layer):
 out=[];unbound=[]
 for i,op in enumerate(inst):
  if op['unit']!=F.I.UNIT_SU:continue
  for axis in 'abcd':
   source=op.get(axis+'_src',F.I.SRC_VM)
   if source not in (F.I.SRC_CLO,F.I.SRC_CHI):continue
   base=op.get(axis+'_base',0);tag=op.get('_tag','')
   if (base>>28) in (2,3):
    if axis not in 'bd' or not op.get('c_pair'):raise ValueError('unrecognized RoPE address selector')
    out.append(dict(instruction=i,operand=axis,kind='held_HBM_RoPE_cache',selector=base>>28,actual_address=base,provider_bound=False));continue
   if tag==f'L{layer}.engram' and axis=='b':
    unbound.append(dict(instruction=i,operand=axis,reason='FP32(q_weight*k_weight) generated coefficient not in409CROMtensors',elements=20480,actual_base=None));continue
   if op.get(axis+'_d',0) or op.get(axis+'_ind',0):raise ValueError('dynamic unbound CROM operand')
   extent=(op.get('su_nout',1)-1)*op.get(axis+'_so',0)+(op.get('su_nin',1)-1)*op.get(axis+'_si',0)+1
   hits=[(name,e) for name,e in record['constants'].items() if e['base_word']<=base and base+extent<=e['end_word_exclusive']]
   if len(hits)!=1:raise ValueError(f'CROM operand not inside unique tensor {tag}/{axis}/{base}/{extent}')
   name,e=hits[0];out.append(dict(instruction=i,operand=axis,kind='checkpoint_CROM',tensor=name,actual_address=base,offset=base-e['base_word'],extent_words=extent,tensor_base=e['base_word'],tensor_end=e['end_word_exclusive'],source_sha256=e['source_sha256'],output_slice_sha256=e['output_slice_sha256']))
 return out,unbound
def validate_encoded(words, bindings):
 for binding in bindings:
  op=F.I.decode(words[binding['instruction']],full_shape=True)
  axis=binding['operand']
  if op['unit']!=F.I.UNIT_SU or op[axis+'_base']!=binding['actual_address']:
   raise ValueError('encoded CROM operand differs from authoritative semantic binding')
  if binding['kind']=='checkpoint_CROM':
   # These immutable checkpoint operands are direct, static low-FP32 reads.
   # Held RoPE-cache operands have a separate provider and are not qualified here.
   if op[axis+'_src']!=F.I.SRC_CLO:
    raise ValueError('encoded CROM source class differs from checkpoint binding')
   flags=[axis+'_d','su_d_nout','su_d_nin']
   if axis=='a':flags+=['a_ind']
   if axis=='b':flags+=['b_half']
   flags+=['c_pair']
   if any(op.get(k,0)!=0 for k in flags):
    raise ValueError('dynamic or paired addressing on static checkpoint CROM operand')
   no,ni=op['su_nout'],op['su_nin']
   if no<1 or ni<1:raise ValueError('invalid static CROM iteration extent')
   extent=(no-1)*op[axis+'_so']+(ni-1)*op[axis+'_si']+1
   if extent!=binding['extent_words']:
    raise ValueError('decoded CROM extent differs from authoritative binding')
   base=op[axis+'_base']
   if not binding['tensor_base']<=base or base+extent>binding['tensor_end']:
    raise ValueError('encoded CROM extent outside tensor')
 return True

def build():
 F.source_pins();F.G.set_arith('chunk8');F.G.set_fuse('');manifest,msha=intake();ranks=[];binaries={};old=F.I.SU_LANES;F.I.SU_LANES=8
 try:
  for record in manifest['rank_images']:
   rank=record['rank'];stages=[];raw=bytearray();unbound=[];count=0;bound=0;cache=0
   for layer in range(40):
    b=BoundBuilder(layer,record);inst=b.build_layer();bindings,missing=operand_bindings(inst,record,layer)
    stages.append(dict(layer=layer,instruction_count=len(inst),bindings=bindings,unbound=missing));unbound.extend(dict(layer=layer,**x) for x in missing)
    original=F.FullLayerBuilder(layer).build_layer();assert len(original)==len(inst)
    words=[]
    for index,op in enumerate(inst):
     oldword=F.I.encode(full_shape=True,**original[index]);mask=0
     for binding in bindings:
      if binding['instruction']==index and binding['kind']=='checkpoint_CROM':
       off,width=F.I.FULL_LAYOUT[binding['operand']+'_base'];mask|=((1<<width)-1)<<off
     word=F.I.encode(full_shape=True,**op);decoded=F.I.decode(word,full_shape=True)
     for k,v in op.items():
      if not k.startswith('_'):assert decoded[k]==(F.I.FULL_DYN[v] if isinstance(v,(str,tuple)) else v),(layer,k)
     assert (oldword & ~mask)==(word & ~mask),'non-CROM instruction change'
     words.append(word);raw.extend(word.to_bytes(256,'little'));count+=1
    validate_encoded(words,bindings)
    bound+=sum(x['kind']=='checkpoint_CROM' for x in bindings);cache+=sum(x['kind']=='held_HBM_RoPE_cache' for x in bindings)
   head=F.head_descriptors();head=[dict(x) for x in head];patched=0
   for op in head:
    if op.get('c_src')==F.I.SRC_CLO:
     assert op.get('su_nin')==5120 and op.get('c_base',0)==0
     op['c_base']=record['constants']['norm.weight']['base_word'];patched+=1
   assert patched==1
   hb,hm=operand_bindings(head,record,'head');assert not hm
   headwords=[F.I.encode(full_shape=True,**op) for op in head];validate_encoded(headwords,hb)
   for word in headwords:raw.extend(word.to_bytes(256,'little'));count+=1
   bound+=sum(x['kind']=='checkpoint_CROM' for x in hb)
   ranks.append(dict(rank=rank,CROM_image_sha256=record['image_sha256'],stages=stages,head_bindings=hb,encoded_instruction_count=count,encoded_template_sha256=hashlib.sha256(raw).hexdigest(),bound_checkpoint_operands=bound,RoPE_cache_operands=cache,unbound_generated_operands=unbound))
   binaries[rank]=bytes(raw)
 finally:F.I.SU_LANES=old
 return dict(status='PASS_BOUND_CHECKPOINT_CROM_STATIC_LEGALITY_NOT_RUNNABLE',manifest_pin=EVIDENCE,manifest_path=DIR+'manifest.json.gz',manifest_uncompressed_sha256=msha,source_pins=F.source_pins(),ranks=ranks,non_CROM_encoded_bits_unchanged=True,word_bits=2048,codec='little-endian256bytes per2048-bit instruction',hardware_admission=False,full_program_executable=False,scope='All40/head checkpoint CROM semantic operands regenerated and encoding checked. Engram generated q*k, pre0/state, heldRoPE provider, matrices, collectives, boundaries and runtime completion remain separate unbound prerequisites; no fulltoken arithmetic/runtime qualification'),binaries
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();r,b=build();assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True)
 for rank,raw in b.items():
  path=a.out.with_name(a.out.stem+f'.rank{rank}.templates.bin.gz');assert not path.exists();path.write_bytes(gzip.compress(raw,mtime=0))
 a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps([dict(rank=x['rank'],instructions=x['encoded_instruction_count'],bound=x['bound_checkpoint_operands'],unbound=len(x['unbound_generated_operands'])) for x in r['ranks']],indent=2))
