"""Exact register split/replication for row-1 scorer inputs; original modules immutable."""
import copy,json,hashlib,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-2249');OUT=R/'row1';OUT.mkdir(exist_ok=True)
source=Path('/srv/opentallas-scratch2/claude/die-hbm-29/b29d/out/asbuilt.json')
y=json.load(source.open());m=y['modules'];top=m['hbm_current_native_top'];oldtop=copy.deepcopy(top)
analysis=json.load((R/'scorer_source_analysis.json').open());rows={r['path']:r for r in analysis}
manifest=json.load(open('/srv/opentallas-scratch2/claude/die-hbm-29/b29d/asbuilt.json'));mapping=json.load(open(manifest['map_file']))
receipt=[]
for side in ('NE','NW'):
 prefix=f'hb_idx__s_{side}';pc=top['cells'][prefix];oldwrapper=pc['type'];wrapper=copy.deepcopy(m[oldwrapper]);wrappername=f'ot_native_row1_wrap_{side}';m[wrappername]=wrapper;pc['type']=wrappername
 oldscorer=wrapper['cells']['scorer']['type'];scorer=copy.deepcopy(m[oldscorer]);newscorer=f'ot_native_row1_scorer_{side}';m[newscorer]=scorer;wrapper['cells']['scorer']['type']=newscorer
 original=copy.deepcopy(m[oldscorer]);cells=scorer['cells'];leaf=cells['ge[1].gc[0].leaf'];oldleaf=copy.deepcopy(leaf)
 maxbit=max(b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b,int))+1
 replacement={};newnames=[];split={}
 for path,row in rows.items():
  if not path.startswith(prefix+'.scorer.'):continue
  name=path[len(prefix+'.scorer.'):];old=cells[name];assert old['type']=='$dff';idx=[r['bit'] for r in row['hits']];assert len(idx)==row['selected_bits']
  newname='native_row1_'+name.replace('$','_');assert newname not in cells
  new=copy.deepcopy(old);new['parameters']['WIDTH']=format(len(idx),'032b');new['attributes']['keep']='1';new['connections']['D']=[old['connections']['D'][i] for i in idx]
  if row['width']==4396:
   assert row['selected_bits']==2176 and set(row['Q_load_counts'])=={row['destination']}
   new['connections']['Q']=[old['connections']['Q'][i] for i in idx]
   keep=[i for i in range(row['width']) if i not in set(idx)];cells[name]=copy.deepcopy(old);cells[name]['parameters']['WIDTH']=format(len(keep),'032b')
   for port in ('D','Q'):cells[name]['connections'][port]=[old['connections'][port][i] for i in keep]
   split[name]=dict(row1=idx,keep=keep)
   assert sorted(new['connections']['Q']+cells[name]['connections']['Q'])==sorted(old['connections']['Q'])
  else:
   newbits=list(range(maxbit,maxbit+len(idx)));maxbit+=len(idx);new['connections']['Q']=newbits
   replacement.update({old['connections']['Q'][i]:b for i,b in zip(idx,newbits)})
   assert cells[name]==original['cells'][name]
  cells[newname]=new;newnames.append(newname)
  assert new['connections']['CLK']==old['connections']['CLK']
  assert new['connections']['D']==[old['connections']['D'][i] for i in idx]
  mapping['parts'][prefix+'.scorer.'+newname]=row['destination']
  receipt.append(dict(side=side,original=path,new=prefix+'.scorer.'+newname,home=row['destination'],width=len(idx),kind='split' if row['width']==4396 else 'replica',source_bits=idx,clock=old['connections']['CLK']))
 changes=[]
 for port,bs in leaf['connections'].items():
  if leaf['port_directions'][port]!='input':continue
  nb=[replacement.get(b,b) for b in bs]
  if nb!=bs:changes.append(dict(port=port,bits=sum(a!=b for a,b in zip(bs,nb))));leaf['connections'][port]=nb
 assert sum(x['bits'] for x in changes)==570,changes
 # Verify every original cell is unchanged except split source + exact row1 input substitutions.
 for n,c in original['cells'].items():
  if n in split:continue
  if n=='ge[1].gc[0].leaf':
   expected=copy.deepcopy(c)
   for pn,bs in expected['connections'].items():
    if expected['port_directions'][pn]=='input':expected['connections'][pn]=[replacement.get(b,b) for b in bs]
   assert cells[n]==expected
  else:assert cells[n]==c,n
 scorer.setdefault('netnames',{}).update({n+'_Q':dict(hide_name=0,bits=cells[n]['connections']['Q'],attributes={'keep':'1'}) for n in newnames})
 # No module externally observable ports or source definitions changed.
 assert scorer['ports']==original['ports']
 assert m[oldwrapper]['cells']['scorer']['type']==oldscorer
expectedtop=copy.deepcopy(oldtop)
for side in ('NE','NW'):expectedtop['cells'][f'hb_idx__s_{side}']['type']=f'ot_native_row1_wrap_{side}'
assert top==expectedtop
netfile=OUT/'asbuilt.json';netfile.write_text(json.dumps(y,separators=(',',':')))
mapfile=OUT/'map.json';mapfile.write_text(json.dumps(mapping,indent=1));manifest['map_file']=str(mapfile);manifest['note']='CODEX exact row1 input FF locality candidate; original modules preserved, +570FF/hub and zero cycles. '+manifest['note'];(OUT/'manifest.json').write_text(json.dumps(manifest,indent=1))
rep=dict(schema='opentallas.hbm.row1_source.v1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(netfile.read_bytes()).hexdigest(),added_ff=1140,cycles_added=0,original_module_count=len(m)-4,rows=receipt,terminal_rewrite_invariant='PASS',changed_top_cells=['hb_idx__s_NE','hb_idx__s_NW'])
(OUT/'receipt.json').write_text(json.dumps(rep,indent=1));print(json.dumps({k:v for k,v in rep.items() if k!='rows'}),flush=True)
