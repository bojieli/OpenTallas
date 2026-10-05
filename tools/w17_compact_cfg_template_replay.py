#!/usr/bin/env python3
"""Metadata-only exact loader encoding replay; synthetic identities are not checkpoint payload."""
import argparse,ast,collections,gzip,hashlib,json,math,pathlib,subprocess,types
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
PINS={'candidate':('0fb58ac09c4415b4f143c97fed1fbfa4a5486aa9','results/quality/w16_w17_integer_residency_20261001/candidate.json.gz'),'images':('1c4c5aefdfbbdd41dee75772761a95a3446104cc','tools/v41_die_images_w17w10.py'),'order':('42e2471cf20dc081ea59f8f43478435848dc7256','tools/v41_rom_ksplit_bankmap.py'),'pair':('76ffc2aa0df086016c57edc2abb128a29a05099c','rtl/v41die/ot_v41_pair_w17w10.sv'),'scalar':('a2f76583279a984a1ce99d29fe1cbea537c5fbb9','results/rtl/w17_connected_token_preparation_20261001/integer_candidate_scalar_replay.json'),'element':('76ffc2aa0df086016c57edc2abb128a29a05099c','rtl/v41rom/ot_v41_rom_elem_w10.sv')}
def blob(pin):return subprocess.check_output(['git','show',pin[0]+':'+pin[1]],cwd=ROOT)
def functions(raw,names,env):
 tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert len(nodes)==len(names)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'<immutable exact encoding>','exec'),env);return env

def patch(words,delta):
 out=words.copy()
 for i in range(8):
  if out[i]:
   old=(out[i]>>29)&8191;assert old+delta<8192
   out[i]=(out[i]&~(8191<<29))|((old+delta)<<29)
 if any(out[8:16]):
  old=(out[16]>>6)&8191;assert old+delta<8192
  out[16]=(out[16]&~(8191<<6))|((old+delta)<<6)
 return out

def main(out):
 raw={k:blob(p) for k,p in PINS.items()};c=json.loads(gzip.decompress(raw['candidate']))
 assert hashlib.sha256(raw['scalar']).hexdigest()=='4d9bc2c10bf00d428a065090ce5616c622ed3d698c9ac63035215129437c45eb'
 assert json.loads(raw['scalar'])['template_cells_checked']==143360
 assert b'<= cfg_d_e[41:29]' in raw['element'] and b'pbase <= cfg_d_e[19:6]' in raw['element']
 funcs=['unit_range','unit_halves','segment_order','element_order','seg_units']
 env=functions(raw['order'],funcs,dict(math=math,CHUNK_EL=256,IL=8));S=types.SimpleNamespace(**{k:env[k] for k in funcs})
 # Phase-cycle model result is outside this encoding-only replay; it cannot receive timing credit.
 S.IL=8
 S.phase_cycles=lambda _:None
 placed=[]
 def place(field,mats):return [dict(x) for x in placed],[dict(off=0,s=1,segs=[])],None
 env=functions(raw['images'],['add_phase','phase_words'],dict(Field=object,Mat=object,S=S,NSEG=8,NCH=16,NCHB=8,CW=25,SENT=32768,_place=place))
 stride={int(p):n for p,n in c['pair_stride'].items()};prefix=collections.defaultdict(int);templates={};negative=[];count=0;domains=set()
 for f in ('w1','w3','w2'):
  t=c['templates'][f];placed.clear()
  for p in t['pairs']:
   for sg in p['segments']:placed.append(dict(pair=p['pair'],mi=0,tensor=f,fmt='fp4',row=sg['row'],seg=sg['segment'],nseg=sg['segments_per_row'],e0=sg['first_K'],elems=sg['K_elements']))
  # Unique symbolic block identity, no float arithmetic and no checkpoint payload IO.
  mat=types.SimpleNamespace(fmt='fp4',K=t['K'],rows=t['rank_rows'],name=f,r0=0,k0=0,block_word=lambda row,chunk,block:1+(row<<16)+(chunk<<4)+block)
  def encode(slot):
   field=types.SimpleNamespace(np=8192,pp=True,fast=True,depth=8192,add_latency=8,fill=np.zeros(8192,dtype=np.int64),words=[{} for _ in range(16384)],cfg=[],stream=[],phases=[])
   for p,n in stride.items():field.fill[p]=slot*n+prefix[p]
   ph=env['add_phase'](field,[mat]);return field,ph
  zero,ph=encode(0);last,lp=encode(c['experts_per_stage_capacity']-1)
  assert zero.stream==last.stream and len(zero.stream)==t['stream_issue_cycles']
  w0,w1=env['phase_words'](ph);assert ((w0>>30)&65535)==0
  cfg=[]
  for p in t['pairs']:
   pair=p['pair'];words=zero.cfg[0][pair];delta=(c['experts_per_stage_capacity']-1)*stride[pair]
   assert patch(words,delta)==last.cfg[0][pair]
   # Existing PP read order and loader tags preserved at every actual populated word.
   for mate in (0,1):
    for address,value in zero.words[2*pair+mate].items():assert last.words[2*pair+mate][address+delta]==value
   cfg.append(dict(pair=pair,words=words,triplet_stride=stride[pair],family_prefix=prefix[pair]))
   for i in list(range(8))+[16]:
    if i<8 and not words[i]:continue
    if i==16 and not any(words[8:16]):continue
    base=(words[i]>>(29 if i<8 else 6))&8191;domains.add((base,stride[pair]))
   prefix[pair]+=p['logical_words_per_mate'];count+=25
  templates[f]=dict(cfg=cfg,stream=zero.stream,phase_words=[w0,w1],symbolic_ROM_identity=True)
  pair=cfg[0]['pair'];delta=(c['experts_per_stage_capacity']-1)*stride[pair];good=patch(zero.cfg[0][pair],delta)
  for name,idx in (('stale_segment_base',0),('stale_PP_base',16),('corrupt_row_tag',17)):
   bad=good.copy();bad[idx]=zero.cfg[0][pair][idx] if idx!=17 else good[idx]^1
   assert bad!=last.cfg[0][pair];negative.append(f+':'+name)
 assert dict(prefix)==stride
 checked=0
 for base,n in domains:
  for slot in range(c['experts_per_stage_capacity']):assert base+slot*n<8192;checked+=1
 try:patch(templates['w1']['cfg'][0]['words'],8192)
 except AssertionError:negative.append('base_overflow')
 else:raise AssertionError('overflow admitted')
 # Inactive/BF pairs must receive zero descriptors each q phase; stale act is not legal.
 assert all(zero.cfg[0][p]==[0]*25 for p in range(8192) if p not in {x['pair'] for x in c['templates']['w2']['pairs']})
 out.parent.mkdir(parents=True,exist_ok=True);artifact=out.with_name('compact_cfg_stream_templates.json.gz')
 assert not out.exists() and not artifact.exists()
 artifact.write_bytes(gzip.compress(json.dumps(templates,separators=(',',':')).encode(),mtime=0))
 receipt=dict(verdict='PASS_METADATA_CLASS_A_ENCODER_REPLAY_ONLY',source_pins={k:dict(commit=p[0],path=p[1],sha256=hashlib.sha256(raw[k]).hexdigest()) for k,p in PINS.items()},cfg_words_encoded=count,stream_words=sum(len(t['stream']) for t in templates.values()),affine_base_domain_slot_checks=checked,negative_cases_rejected=negative,template_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),both_segment_base_bits='41:29',PP_base_bits='19:6 actual RTL14bit field; logical8192 aperture patches lower13 bits18:6, preserves bit19',inactive_pair_zero_clear_required=True,actual_loader_CW=25,existing_loader_service_cycles=27,candidate_affine_service_cycles=6,candidate_family_cfg_cycles=33,scope='Exact immutable add_phase/phase_words encoding plus symbolic ROM address identities; no actual numeric checkpoint values, arithmetic RTL gate, SS/FF or complete residency proof',required_interface='slot9 plus family2 local template selection; patch BOTH segment base and PP base, retain row/class/subblock fields; explicit zero clear for inactive/BF pairs; family-local stream base0',PHW6_full_residency_pass=False,launch_allowed=False,adopt=False)
 out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();main(a.out)
