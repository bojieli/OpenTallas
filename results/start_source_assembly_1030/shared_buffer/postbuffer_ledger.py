import json,sys
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-s81-start-data-1030/tools/die_plan')
from start_data_emit import pin,distance
p=json.load(open(R/'shared_buffer/buffered.json'))['modules']['ot_die_start_stages'];h=json.load(open(R/'shared_buffer/head_homes.json'));caps=json.load(open(R/'attempt_833/actual_input_caps.json'));L=json.load(open('/srv/opentallas-scratch/claude/codex-flow-s81phy-1030/exactA/stage_lib.json'))['corners'];homes=json.load(open(R/'source_homes_candidatePG.json'));srcs={(s['region'],s['signal']):s for s in homes['source_records']};lib=json.load(open(R/'library_all.json'))['cell_library']
for c in ['TT','FF']:caps[c]['cells']['BUFx8_ASAP7_75t_R']={'A':dict(max_cap_ff=L[c]['cells']['BUFx8_ASAP7_75t_R']['cap_ff'])}
loads={}
for n,c in p['cells'].items():
 if c['type']=='$scopeinfo':continue
 for pn,bs in c['connections'].items():
  if pn in ('Y','QN','SN','CON'):continue
  for b in bs:loads.setdefault(b,[]).append(dict(kind='iterm',instance=n,pin=pn,master=c['type'],input_cap_ff={co:caps[co]['cells'][c['type']][pn]['max_cap_ff']for co in ['TT','FF']}))
for n,v in p['ports'].items():
 if v['direction']=='output':
  for b in v['bits']:loads.setdefault(b,[]).append(dict(kind='bterm',name=n,input_cap_ff=None,hold='actual native receiver loading/entryhome absent'))
for hd in h['heads']:
 source=srcs[hd['region'],hd['signal']];il=loads[hd['input_bit']];assert len(il)==1 and il[0]['instance']==hd['instance']and il[0]['pin']=='A'
 hd.update(source_inv_actual_loads=il,source_ff_instance=source['ff_instance'],source_qn_pin_um=source['qn_pin_um'],source_inv_A_um=source['input_pin_um'],source_inv_Y_um=source['output_pin_um'],qn_to_inv_um=source['qn_to_inv_um'])
 hd['head_actual_loads']=loads.get(hd['output_bit'],[])
 for t in hd['head_actual_loads']:
  if t.get('instance')in homes['cells']:
   t['pin_um']=pin(homes['cells'][t['instance']],t['pin'],lib);t['direct_point_wire_um']=distance(hd['output_pin_um'],t['pin_um'])
 hd['head_known_static_load_ff']={co:sum(t['input_cap_ff'][co]for t in hd['head_actual_loads']if t['input_cap_ff']is not None)for co in ['TT','FF']}
 hd['head_unknown_native_load']=any(t['kind']=='bterm'for t in hd['head_actual_loads'])
h['holds']+=['long outgoing posthead DATA requiresregisteredrecompose under405, notonlyrepeaters','8heads beyondoriginal8.64x.81capacitytile needexplicitbayrefinement/nativePG/STDoccupancycheck']
(R/'shared_buffer/postbuffer_ledger.json').write_text(json.dumps(h,indent=2)+'\n');print('heads',len(h['heads']),'SRCBUF8caps',{c:caps[c]['cells']['BUFx8_ASAP7_75t_R']['A']['max_cap_ff']for c in ['TT','FF']})
