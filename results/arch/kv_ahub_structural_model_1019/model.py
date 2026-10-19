#!/usr/bin/env python3
"""Bounded AHUB source-pinned analytical model; no EDA or closure inference."""
import collections,gzip,hashlib,json,math,re
from pathlib import Path
P=Path(__file__).resolve().parent; E=P/'evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
M=json.loads(gzip.decompress((E/'reparsed.json.gz').read_bytes()))['modules']['qkd_ahub_static_dw_safe_native']
A=json.loads((E/'area.json').read_text())['new']; graph={};cells=M['cells']; drv={}
for n,c in cells.items():
 for p,bits in c['connections'].items():
  if c['port_directions'][p]=='output':
   for b in bits:drv[b]=n
memo={};active=set()
def depth(n):
 if n in memo:return memo[n]
 if n in active:raise ValueError('comb loop '+n)
 c=cells[n]
 if c['type'].startswith('DFF') or c['type']in('ot_nhb_zh','ot_qkh_recip_leaf'):return (0,[n])
 active.add(n);q=[depth(drv[b])for p,bs in c['connections'].items()if c['port_directions'][p]=='input'for b in bs if b in drv];d,path=max(q,default=(0,[]),key=lambda x:x[0]);active.remove(n);memo[n]=(d+1,path+[n]);return memo[n]
stages=[]
for n,c in cells.items():
 if c['type'].startswith('DFF'):
  for b in c['connections']['D']:
   if b in drv:
    d,path=depth(drv[b]); stages.append({'end':n,'depth':d,'path':path+[n]})
stages.sort(key=lambda x:x['depth'],reverse=True)
# Every physical signal contact rectangle, grouped by exact nearest full face.
contacts={}
for name in ['ot_nhb_zh','ot_qkh_recip_leaf']:
 s=(E/(name+'.lef')).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',s).groups());faces=collections.defaultdict(list)
 for match in re.finditer(r'  PIN (\S+)\n(.*?)  END \1',s,re.S):
  pin,body=match.groups();layer=None
  for line in body.splitlines():
   m=re.search(r'LAYER (\S+)\s*;',line)
   if m:layer=m[1]
   m=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',line)
   if m:
    x0,y0,x1,y1=map(float,m.groups());x=(x0+x1)/2;y=(y0+y1)/2;f=min({'W':x,'E':w-x,'S':y,'N':h-y},key=lambda k:{'W':x,'E':w-x,'S':y,'N':h-y}[k]);faces[f].append({'pin':pin,'layer':layer,'rect':[x0,y0,x1,y1],'coordinate':x if f in 'NS'else y,'use':'power'if 'USE POWER' in body or 'USE GROUND'in body else'signal'})
 out={}
 for f,rows in faces.items():
  sig=[r for r in rows if r['use']=='signal'];ds=[]
  for layer in set(r['layer']for r in sig):
   coords=sorted(r['coordinate']for r in sig if r['layer']==layer);ds +=[round(b-a,9)for a,b in zip(coords,coords[1:])if b>a]
  out[f]={'all_contacts':rows,'signal_count':len(sig),'face_length_um':w if f in 'NS'else h,'full_face_density':len(sig)/(w if f in 'NS'else h),'minimum_same_layer_contact_pitch_um':min(ds)if ds else None,'local_inverse_pitch_per_um':1/min(ds)if ds else None}
 clocks={}
 for corner in ['tt','ff','ss']:
  lib=(E/(name+'_'+corner+'.lib')).read_text();c=lib[lib.index('pin("clk")'):];c=c[:c.index('    pin(',1)]if '    pin('in c[1:]else c
  clocks[corner]={}
  for typ in ['min_clock_tree_path','max_clock_tree_path']:
   z=re.search('timing_type : '+typ+r';(.*?)(?=timing\(\)|\Z)',c,re.S)
   clocks[corner][typ]=[float(v)for v in re.findall(r'values\("([\d.]+)"\)',z.group(1))][:2]if z else None
 contacts[name]={'lef_sha256':sha(E/(name+'.lef')),'size_um':[w,h],'faces':out,'clock_libs':clocks}
# Each channel is a coherent word. Constants stay explicit, not data ring state.
channels=[('hs',165)]+[(f'ap{i}',43)for i in range(4)]+[(f'am{i}',35)for i in range(4)]+[('fr',145),('hf',1)]+[(f'zh{i}_{d}',w)for i in range(4)for d,w in [('in',268),('out',68)]]+[('recip_in',33),('recip_out',34)]
rows=[]
for name,w in channels:
 chunks=[min(32,w-i)for i in range(0,w,32)]
 rows.append({'name':name,'width':w,'chunks':chunks,'ring_slot_bits':4*w,'capture_bits':w,'control_ff':12*len(chunks),'reset_landing_ff':2*len(chunks),'fixed_latency_edges':3,'max_ring_bank_bits':4*max(chunks)})
W=sum(r['width']for r in rows); B=sum(len(r['chunks'])for r in rows);data=5*W;control=14*B
kit=gzip.decompress((E/'kit_source.v.gz').read_bytes()).decode();ties=re.findall(r'(TIE(?:HI|LO)\w+)\s+(\S+)\s*\(\s*\.([A-Z]+)\(([^)]+)\)\s*\);',kit);wordcount=collections.Counter(re.findall(r'\b_\d+_\b',kit));tie_loads=collections.Counter(wordcount[x[3]]-2 for x in ties)
result={'schema':'opentallas.ahub.structural_model.v1','status':'MODEL_HOLD_NOT_BUILD_READY','source_area_um2':A['standard_cell_area_um2'],'source_ff':A['flip_flops'],'mapped_cells_by_master':A['cells'],'source_graph_sha256':sha(E/'reparsed.json.gz'),'all_driver_summary':json.loads((E/'every_driver_summary.json').read_text()),'kit_ties':{'count':len(ties),'by_master':dict(collections.Counter(x[0]for x in ties)),'loads_per_tie_histogram':dict(tie_loads),'method':'exact emitted identifier occurrences minus sole declaration and driver; every tie net has one sink including concat pins'},'maximum_D_comb_depth':stages[0]['depth'],'D_stages_over20':sum(r['depth']>20 for r in stages),'deepest20_stages':stages[:20],'child_contacts':contacts,'transport_candidate':{'kind':'independent local child/face collars; compact central source-logic region; static 4-slot rings, <=32bit independently controlled banks','channels':rows,'total_bits':W,'banks':B,'data_ff':data,'control_reset_ff':control,'added_ff':data+control,'source_plus_transport_ff':3420+data+control,'added_data_area_um2':data*.2916,'added_control_reset_area_um2':control*.37908,'total_source_plus_transport_ffarea_um2':A['standard_cell_area_um2']+data*.2916+control*.37908,'additional_comb_clock_pg_area_um2':None,'area_complete':False,'copy_fixedpoint_proven':False,'notes':'Control topology charges independent modulo4 write/read pointers(4FF), registered one-hot write/read phase(8FF), reset landing(2FF) per bank. No shared enables across banks. Ring slots4W and captureW charged in full; no reuse credited. Boolean pointer/control mapping and corner timing unresolved.'},'floorplan_candidate':{'outline_um':[691.2,496.8],'children':[{'inst':'zh0','xy':[43.2,43.2],'size':[151.2,151.2]},{'inst':'zh1','xy':[237.6,43.2],'size':[151.2,151.2]},{'inst':'zh2','xy':[43.2,280.8],'size':[151.2,151.2]},{'inst':'zh3','xy':[237.6,280.8],'size':[151.2,151.2]},{'inst':'recip','xy':[432,259.2],'size':[216,216]}],'connected_std_region':'full-width band y199.8..253.8 with connected width43.2 vertical collars around every child; arithmetic core x216..345.6,y216..253.8 (exclude child boxes); actual rows/PG/vias and 40-60pct occupied placement region need final area','source_only_logic_area_at_50pct_um2':2*A['standard_cell_area_um2'],'macro_area_um2':4*151.2**2+216**2,'known_macro_plus_source_transport_fill':(4*151.2**2+216**2+A['standard_cell_area_um2']+data*.2916+control*.37908)/(691.2*496.8),'physical_safe':False},'calendar_candidate':{'existing_recip_return_edges':71,'existing_pub_after_recip_issue':75,'new_child_roundtrip_edges':6,'six_level_reduction_extra_edges':30,'external_command_landing':3,'external_export_landing':3,'illustrative_SU_layer_added_edges':42,'hypothesis':'six nonoverlapping issue levels retain order; five level gaps each grow6; reciprocal roundtrip grows6; hs/fr grow3 each. Actual calendar phases/boot/native/hf collection still required. Not a compiled or qualified schedule.','MU_schedule_added_edges':None,'token_added_edges':None,'fault_collection_cutoff':None},'checklist':{'pins':'source functional face identities PASS; exact constants preserved; new landing proof OPEN','reach':'candidate local regions and forwarded hops; exact driver-to-endpoint geometry OPEN','fanout':'existing functional FF/comb/input<=24, reset2; kit743ties each1. Candidate bank32 architecture only, mapped fixedpoint OPEN','depth':'native D-cone max16 logical levels; physical TT failure includes inserted clock/hold/repair networks, no region timing credit','storage':'candidate four-slot rings128bits maxbank, no >=3 FF shift chains; existing child internals not requalified','floorplan':'all candidate R0 origins43.2 lattice; child local pitch/OBS/PG/vias FAIL/OPEN','clock':'independent collar roots referenced to actual corner-specific child flop intervals; TT/FF<=80 unproved','schedule':'all transport state charged; real SU/MU/compiler/reset/continuous health timeline OPEN'}}
(P/'model.json').write_text(json.dumps(result,indent=2)+'\n');(P/'source_manifest.json').write_text(json.dumps({str(p.relative_to(P)):sha(p)for p in sorted(E.iterdir())if p.is_file()},indent=2)+'\n')
print(json.dumps({'depth':result['maximum_D_comb_depth'],'stages_over20':result['D_stages_over20'],'bits':W,'banks':B,'added_ff':data+control,'area':result['transport_candidate']['total_source_plus_transport_ffarea_um2'],'contacts':{n:{f:{k:v for k,v in r.items()if k!='all_contacts'}for f,r in c['faces'].items()}for n,c in contacts.items()},'clock':{n:c['clock_libs']for n,c in contacts.items()}},indent=2))
