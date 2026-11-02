from pathlib import Path
import json,re,hashlib,importlib.util,sys
R=Path('/home/ubuntu/coord/tmp/codex-hhp-historical-boundary-0600');C=R/'capsule_r4';S=Path('/srv/opentallas-scratch/claude/wt/codex-hhp-historical-boundary-0600');spec=importlib.util.spec_from_file_location('HP35',R/'hard_pinreg_35fc.py');HP=importlib.util.module_from_spec(spec);spec.loader.exec_module(HP)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def decls(txt):
 out={}
 for dr,hi,lo,n in re.findall(r'\b(input|output)\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?(\w+)',txt):
  for i in ([None] if not hi else range(int(lo),int(hi)+1)):out[n+(f'[{i}]' if i is not None else '')]=dr
 return out
src=(C/'pc_EN_0/rtl/qkd_kvs_pc.sv').read_text();src=src[:src.index(');')];rtl=decls(src);native=decls((R/'ACTUAL_NATIVE_PC_DECLS.txt').read_text());assert rtl==native and len(rtl)==4133
lef={};pg=set();cur=None;direction=None;use=None
for l in (R/'views/qkd_kvs_pc.lef').read_text().splitlines():
 m=re.match(r'\s*PIN\s+(\S+)',l)
 if m:cur=m[1];direction=None;use=None
 if cur:
  m=re.search(r'\bDIRECTION\s+(\w+)',l)
  if m:direction=m[1].lower()
  m=re.search(r'\bUSE\s+(\w+)',l)
  if m:use=m[1]
  if re.match(r'\s*END\s+'+re.escape(cur)+r'\s*$',l):
   if use not in ('POWER','GROUND'):lef[cur]=direction
   else:pg.add(cur)
   cur=None
assert lef==rtl
pd={}
for n,d in rtl.items():
 b=re.sub(r'\[\d+\]$','',n);pd.setdefault(b,{'dir':d,'n':0});pd[b]['n']+=1
corners={}
for corner in ('tt','ff'):
 f=R/f'views/qkd_kvs_pc_{corner}.lib';c={k:v for k,v in HP.parse_lib(f)['qkd_kvs_pc'].items() if k not in pg}
 assert {k for k,v in c.items() if v['dir'] in ('input','output')}==set(pd), ({k for k,v in c.items() if v['dir'] in ('input','output')}-set(pd),set(pd)-{k for k,v in c.items() if v['dir'] in ('input','output')})
 for b,v in pd.items():assert c[b]['dir']==v['dir'] and c[b]['width']==v['n'],(corner,b,c[b],v)
 ck=[k for k,v in c.items() if v['clock']];assert ck==['ck'] or ck==['ck[0]'],ck
 corners[corner]={'sha256':sha(f),'clock_ports':ck,'ports':len(c),'bus_direction_width_join':True}
# Exact current P1..P7 key physical-source counterpart, no borrowed full proof.
e=json.loads(Path('/home/ubuntu/coord/tmp/codex-pc-p3-event-0005/full_event_r1/event.json').read_text());keys={}
for n in ('qkd_ctrl_pc_nc.sv','qkd_static_kv_pc_path_nc.sv','qkd_kv_pc_chain_station_b.sv','qkd_static_kv_pc_path_fan_nc_b.sv'):
 h=sha(R/'actual_pc/rtl'/n);assert h==next(x['after_sha256'] for x in e['files'] if x['file']==n);keys[n]=h
for part in ('pc_EN_0','pc_WN_0'):
 d=C/part;records=json.loads((d/'SOURCE_BOUNDARY.json').read_text());sites=json.loads((R/'geometry/selected_plan.json').read_text())
 reg={'module':'kv3_pc__cl5a95b461','outline_um':sites['outline_um'],'children':{'qkd_kvs_pc':'/srv/opentallas-scratch2/claude/codex-hhp-historical-boundary-0600/actual_views'},'blocks':[{'inst':'u_core_'+h['inst'],'master':'qkd_kvs_pc','x':h['origin_um'][0]+h['track_offset_um'][0],'y':h['origin_um'][1]+h['track_offset_um'][1],'orient':h['orient']} for h in sites['hard_cores'] if h['module']=='qkd_kvs_pc'],'static_rows':True,'qualification':'PC_NOT_SIGNED','source_equivalence':'FULL_EVENT_PARENT_HOLD; actual mapped post proof pending','cohort':'PRIVATE_HISTORICAL_D25_FULLM25'}
 (d/'normal_hard_children_PREP.json').write_text(json.dumps(reg,indent=2)+'\n')
report={'status':'EXACT_NATIVE_INTERFACE_JOIN_PREP_ONLY','qualified':False,'module':'qkd_kvs_pc','native_hdl_vs_prepared_hdl_vs_LEF_signal_bits':len(rtl),'source_clock_parameters':{'CORE_CLOCK':1,'MU':1,'pc_identity':'runtime pc__pc[4:0], no header parameter substitution'},'corners':corners,'lef_sha256':sha(R/'views/qkd_kvs_pc.lef'),'unchanged_full_event_key_source_sha256':keys,'native_core_metadata_sha256':{p.name:sha(p) for p in (R/'actual_pc').iterdir() if p.is_file()},'native_views_qualification':'PC_NOT_SIGNED TT-15.30/FF+8.07/DRV100+31; own-final-post-LEC/provenance HOLD','normal_registration_API':'gen_core_kit_kv --hard-children JSON, exact real master/view files and actual u_core_kvpc1/2/3 placements; not invoked','no_synthetic_blackbox_or_renamed_master':True,'no_new_CAD_or_proof':True}
(R/'NATIVE_VIEW_JOIN.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS4133 exact HDL/LEF/TTFF signalbit/dir/width join; clockck only; source4keyfiles exact; PC_NOT_SIGNED')
