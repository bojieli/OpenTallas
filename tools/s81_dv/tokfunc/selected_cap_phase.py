"""Source-bound explicit local MAT/CAP phase; no HOST dates or residency."""
import hashlib,json,re
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def configured_profile(receipt,root):
 r=json.loads(Path(receipt).read_text());root=Path(root)
 assert r['selected_source_ref']=='8a495768f02316a7a8ad2e2bafef2f4d3741b741'
 assert r['cases']['s0N_aggregate']['exit_code']==0
 assert r['defines']==['DSFD_PQ_STATIC_X2','OT_COLL_NATIVE32','OT_COLL_NATIVE32_OFF','S81CTRL_SRAM_FIFO','S81CTRL_SRAM_P192','S81CTRL_NATIVE32']
 files={k[4:]:v for k,v in r['staged_files_sha256'].items() if k.startswith('src/')}
 assert len(files)==192 #191sourcefiles + exact actualtop
 for rel,h in files.items():assert sha(root/rel)==h,('configured source drift',rel)
 def module(name):
  hits=[]
  for rel,h in files.items():
   text=(root/rel).read_text()
   if re.search(r'\bmodule\s+'+re.escape(name)+r'\b',text):hits.append({'module':name,'source':rel,'sha256':h})
  assert len(hits)==1,(name,hits)
  return hits[0]
 bindings={n:module(n) for n in ['ot_s81sl_slice_c1x_k8_cap5r_lp','ot_s81sl_xgt_xo','ot_s81sl_rstopt_xo','ot_s81sl_xrt1','ot_s81sl_xrt','ot_s81sl_xs4','ot_s81sl_xs4_cal','col_h9_l4_lp','ot_s81sl_capc5r','ot_s81sl_cap_rt','ot_s81sl_vp']}
 assert bindings['ot_s81sl_xs4']['sha256']=='50485a59b26517eb34e2ae4c0918f8480ae0c5e0c96f6246b93c30c6b7970808'
 return {'receipt_sha256':sha(receipt),'source_ref':r['selected_source_ref'],'defines':r['defines'],'files_sha256':files,'bindings':bindings,'clock_reset_ports':r['actual_top_clock_ports'],'actual_top_sha256':r['actual_top_sha256'],'qualification':'Configured191source/6define syntax-only profile; no executed programme, global phase or physical qualification.'}

def explicit_capture(inventory,fx,L,rows,tensor,flags=1):
 assert len(rows)==24 and rows==list(range(rows[0],rows[0]+24)),'minimum selected6frame phase must have24contiguous realrows'
 allrows=L.a_proj_rows(fx);assert all(0<=r<len(allrows) and allrows[r][0]==tensor for r in rows)
 actual=inventory['selected_ownership']['B'];assert len(actual)==6
 frames=[dict(x,rows=rows[4*i:4*i+4]) for i,x in enumerate(actual)]
 assert all(x['master']=='col_h9_l4_lp' for x in frames)
 cfg=dict(obase=0,ops=0,np=0,fmt=2,rbase=(flags<<14)+rows[0],rcnt=len(rows),rsplit=0,lo32=0,hi32=0)
 word=(2<<27)|(cfg['rbase']<<29)|(cfg['rcnt']<<45)
 desc=[]
 for r in rows:
  name,tr,outidx=allrows[r];e=r-rows[0];chunk=e>>6;leaf=chunk%5;wa=64*(chunk//5)+(e&63)
  desc.append(dict(rank_row=r,tensor=name,tensor_row=tr,golden_output_index=outidx,
   leaf=leaf,word_address=wa,capture_port=(wa>>2)&1,native128_row=wa>>2,word_lane=wa&3,
   word_mask4=1<<(wa&3),bit_mask128=f'{((1<<32)-1)<<(32*(wa&3)):032x}',
   value_format='SCALAR32_BF16_RNE_EXPANDED_LOW16ZERO',producer_cycle=None,store_commit_cycle=None,
   lifetime_start=None,lifetime_end=None,residency_admitted=False))
 return dict(scope='EXPLICIT_NEW_COMPONENT_PHASE_NOT_NATIVE_DENSE2_OWNERSHIP',admitted=False,
  slice=inventory['selected_slice'],slice_index=int(inventory['selected_instances'][inventory['selected_slice']]['conns']['sid'].split("'d")[-1]),
  cfg=cfg,cfg_d=f'{word:040x}',flags=flags,frames=frames,rows=desc,
  producer_added_phases=1,producer_added_edges=None,source_to_cap_ages=None,
  KV_completeness=dict(actual_captured=0,selected_fragment=len(rows),rank_required=128,global_required=512,complete=False),
  requires=['actual selected-source programme execution and acceptedVQreadset','all6frame return/FIN/CAP trace','actualleaf macrocommit trace','immutable consumerlease/globalepoch'])

def local_programme(sid,sl,phases,capture,profile):
 import xs_calendar as XC
 from pq_calendar import viamap
 P,S=phases;assert len(P)==2
 cal=XC.compile_phase(P,S,0,sid)
 commands=[(int(t),2,int(w)) for t,w in cal['iss'].items()]+[(XC.GW_IT-1,3,int(capture['cfg_d'],16))]
 commands.sort();assert len({t for t,_,_ in commands})==len(commands)
 desc=[]
 for t,target,word in commands:
  payload=(1<<sid)|(target<<16)|(word<<26)
  assert payload<(1<<186)
  desc.append(dict(target=target,relative_pin_edge=t,body160=f'{word:040x}',payload186=f'{payload:047x}',
   source_pin='u_s_0N.ri_e',epoch='EXPLICIT_COMPONENT_LOCAL_ORIGIN_ONLY'))
 packed=cal['packed'];stream=S+[0]*(16384-len(S));assert len(P)<=4096 and len(S)<=16384
 images={'pq_phase0.viamap.hex':viamap(P+[0]*(4096-len(P))),
  'pq_calendar_action.viamap.hex':viamap([v&((1<<72)-1) for v in packed]),'pq_calendar_time.viamap.hex':viamap([v>>72 for v in packed])}
 for b in range(4):images[f'pq_stream{b}.viamap.hex']=viamap(stream[4096*b:4096*(b+1)])
 manifest=dict(schema='opentallas.s81.selected_local_cap_phase.v1',status='SOURCE_ONLY_UNEXECUTED',slice=sl,
  source_profile=profile,selected_slice_source=dict(streamer='ot_s81sl_xs4',streamer_sha256=profile['bindings']['ot_s81sl_xs4']['sha256'],streamer_added_capture_edges=1),
  command_descriptors=desc,capture=capture,actual_gather_data_emitted=False,synthetic_frame_returns_emitted=False,
  HOST_KS_assumed=False,global_epoch_bound=False,lifetime_qualified=False,source_frame_minimum=None,retire_not_before=None,
  source_model_obligations=dict(raw_ri_e_to_is_postNBA_edges=4,raw_ri_e_to_is_posedge_observation_edges=5,
   evidence=['RSTOPT inputreg99→dl_w378/394','XRT wb172→tg229→is_v517/is_d533'],
   issuer='XS4 capture648→isv_b659→due664→entrywrite675..679→pop695→o_gw733; actualselectedtrace required',
   return_FIN_CAP='No1219/origin/RET/END age imported; actualframe/landing/CAP trace required'),
  images={n:hashlib.sha256(s.encode()).hexdigest() for n,s in images.items()})
 prefix='prog/xs/selected_local/'+sl;files={prefix+'/'+n:s for n,s in images.items()};files[prefix+'/programme.json']=json.dumps(manifest,indent=1)+'\n'
 return dict(files=files,manifest=manifest)

def produced_fixture(directory,producer_path):
 """Load only real weights/meta and actual VN trace values, never op checkpoints."""
 import numpy as np
 directory=Path(directory);producer=json.loads(Path(producer_path).read_text())
 assert producer['status']=='ACTUAL_COMPOSITIONAL_NORM_PRODUCER_COMPONENT_ONLY'
 assert producer['expected_norm_input'] is False
 files=json.loads((directory/'files.json').read_text());meta=json.loads((directory/'meta.json').read_text())
 weights={}
 for name in ['wq_a','wkv']:
  arrays=[]
  for suffix in ['.bin','.scale.bin']:
   rel='weights/'+name+suffix;info=files[rel];assert sha(directory/rel)==info['sha256']
   arrays.append(np.fromfile(directory/rel,dtype=np.dtype(info['dtype'])).reshape(info['shape']))
  weights[name]=tuple(arrays)
 words=[];contexts=sorted(producer['actual_leaf_outputs'],key=lambda c:5*c['sid']+c['leaf']);assert len(contexts)==80
 for index,c in enumerate(contexts):
  assert 5*c['sid']+c['leaf']==index and c['exit_code']==0
  ys=sorted(c['y'],key=lambda y:y['i']);assert [y['i'] for y in ys]==list(range(8))
  for y in ys:
   v=int(y['data256'],16);words.extend((v>>(32*i))&0xffffffff for i in range(8))
 assert len(words)==5120
 return dict(meta=meta,x=np.asarray(words,dtype=np.uint32).view(np.float32),w=weights,files=files),dict(receipt_sha256=sha(producer_path),actual_Y_words=5120,actual_VQ_fragments=320,ops_checkpoint_opened=False,qualification='Same legitimate measured component producer; no global16slice epoch qualification')

class ComponentDie:
 """Actual die/plan frame membership only; constructs no route-age model."""
 def __init__(self,die_v,plan,D):
  raw=Path(die_v).read_bytes();self.raw_die=raw.decode();self.die_sha=hashlib.sha256(raw).hexdigest();self.plan_sha256=sha(plan);self.inst={}
  for line in raw.decode().splitlines():
   m=D.INST_RE.match(line)
   if not m or m[1] in ['module','wire','input','output','assign','reg']:continue
   master,params,name,body=m.groups();assert name not in self.inst
   self.inst[name]=dict(master=master,params=params or '',conns={c[1]:c[2].strip() for c in D.CONN_RE.finditer(body)})
  self.blocks={b['name']:b for b in json.loads(Path(plan).read_text())['blocks']}
 def strap(self,name,port):
  text=self.inst[name]['conns'].get(port,'');m=re.fullmatch(r"\d+'([dh])([0-9a-fA-F]+)",text);assert m,(name,port,text)
  return int(m[2],16 if m[1]=='h' else 10)
 def slices(self):return {n:dict(sid=self.strap(n,'sid')) for n,x in self.inst.items() if n.startswith('u_s_') and x['master'].startswith('ot_s81sl_slice')}
 def frames_of(self,name):
  group=self.blocks[name[2:]]['group']
  return sorted('u_'+n for n,b in self.blocks.items() if b['kind']=='frame' and b.get('group')==group and 'u_'+n in self.inst)

 def native_lane_routes(self):
  """Exact i/o instance/alias chains only; no station-count latency inference."""
  def wire_node(expr):
   m=re.fullmatch(r'(\w+)(?:\[275:0\])?',expr.strip());return m[1] if m else None
  def lanes(expr):
   words=[wire_node(x) for x in expr.split(',')]
   return list(reversed(words)) if len(words)==4 and all(words) else []
  steps={}
  for n,x in self.inst.items():
   if not (x['master'].startswith('dsfd_dvrlyh_276') or x['master']=='dsfd_dvland_276'):continue
   c=x['conns']
   ni,no=wire_node(c.get('i','')),wire_node(c.get('o',''))
   if ni and no:
    steps.setdefault(ni,[]).append(dict(instance=n,module=x['master'],params=x['params'],input=ni,output=no,input_expression=c['i'],output_expression=c['o'],clocks={k:v for k,v in c.items() if k.startswith('ck') or k in ['rs','rst_n']}))
  for m in re.finditer(r'\bassign\s+(\w+)\s*=\s*(\w+)\s*;',self.raw_die):
   steps.setdefault(m[2],[]).append(dict(instance=None,module='EXACT_NET_ALIAS',input=m[2],output=m[1],clocks={}))
  sinks={}
  for n in self.slices():
   for port in ['ri_w','ri_e']:
    for i,net in enumerate(lanes(self.inst[n]['conns'].get(port,''))):sinks.setdefault(net,[]).append(dict(instance=n,port=port,lane=i))
  routes=[]
  for n in self.slices():
   for port in ['ro_w','ro_e']:
    for i,net in enumerate(lanes(self.inst[n]['conns'].get(port,''))):
     start=net;chain=[];visited=set();reason=None
     while net not in sinks:
      if net in visited:reason='CYCLE';break
      visited.add(net);nexts=steps.get(net,[])
      if len(nexts)!=1:reason='NO_UNIQUE_EXACT_I_O_CHAIN';break
      chain.append(nexts[0]);net=nexts[0]['output']
     routes.append(dict(source=dict(instance=n,port=port,lane=i,net=start),destination=sinks.get(net) if not reason else None,chain=chain,unbound=reason,age_edges=None,clock_phase_qualified=False))
  return routes

def require_selected_profile(profile,bindings,readset):
 """Refuse ambiguous/mismatched prospective source before MAT legalisation."""
 from layer_prog.kv_operand_feed import source_profile_files
 selected=source_profile_files(readset,bindings)
 for name,binding in profile['bindings'].items():
  rel=binding['source']
  if rel.startswith('rtl_extra/'):rel=rel.split('/',2)[2]
  if selected.get(rel)!=binding['sha256']:
   raise ValueError('prospective selected module body is unbound or differs from component basis: '+name+' '+rel)
 return selected
