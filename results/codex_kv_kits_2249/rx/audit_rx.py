import json,sys
s=json.load(open(sys.argv[1]));n=json.load(open(sys.argv[2]));top='qkd_hr_core_rx';a=s['modules'][top];b=n['modules'][top];count=0
for name,c in a['cells'].items():
 if c['type'] not in ('$dff','$adff') or not int(c.get('attributes',{}).get('keep','0'),2):
  assert b['cells'][name]==c,(name,'nonkept cell changed');continue
 w=len(c['connections']['Q'])
 for i in range(w):
  nc=b['cells'][name+'_facebit_'+str(i)];m=n['modules'][nc['type']];ff=m['cells']['u_ff'];assert ff['type']==c['type']
  assert ff['parameters']['CLK_POLARITY']==c['parameters']['CLK_POLARITY']
  for p,v in c['connections'].items():assert nc['connections'][p]==([v[i]] if p in ('D','Q') else v),(name,p)
  if c['type']=='$adff':
   assert ff['parameters']['ARST_POLARITY']==c['parameters']['ARST_POLARITY'];assert ff['parameters']['ARST_VALUE']==c['parameters']['ARST_VALUE'][::-1][i]
  count+=1
for p,v in a['ports'].items():
 if p!='deferred':assert b['ports'][p]==v,(p,'port changed')
def drivers(m):
 return {x:(c,p,i) for c in m['cells'].values() for p,d in c['port_directions'].items() if d=='output' for i,x in enumerate(c['connections'][p])}
da,db=drivers(a),drivers(b);domains=set()
def support(x,drv,advance):
 if isinstance(x,str):assert x in ('0','1');return set() if x=='0' else {'TRUE'}
 c,p,i=drv[x]
 if c['type'] in ('$reduce_or','$reduce_bool','$logic_or'):
  return set().union(*(support(t,drv,advance) for p,d in c['port_directions'].items() if d=='input' for t in c['connections'][p]))
 if advance:
  assert c['type']=='$adff';assert c['parameters']['ARST_VALUE'][::-1][i]=='0'
  domains.add((tuple(c['connections']['CLK']),c['parameters']['CLK_POLARITY'],tuple(c['connections']['ARST']),c['parameters']['ARST_POLARITY']))
  return {c['connections']['D'][i]}-{'0'}
 return {x}
want=support(a['ports']['deferred']['bits'][0],da,True)
face=b['cells']['hrface_retime_deferred_facebit_0'];got=support(face['connections']['D'][0],db,False)
assert want==got,(want,got);assert len(domains)==1
ck,cp,rn,rp=next(iter(domains));ff=n['modules'][face['type']]['cells']['u_ff'];assert face['connections']['CLK']==list(ck) and face['connections']['ARST']==list(rn)
assert ff['parameters']['CLK_POLARITY']==cp and ff['parameters']['ARST_POLARITY']==rp and ff['parameters']['ARST_VALUE']=='0'
print(json.dumps({'verdict':'PASS','existing_ff_bits_literal_identity':count,'unchanged_all_other_source_cells':True,'retimed_OR_next_state_support_equal':len(want),'same_clock_reset':True,'added_cycles':0}))
