from pathlib import Path
import json,re,collections
r=Path(__file__).resolve().parent

def nets(path):
 s=path.read_text();names=dict(re.findall(r'^\*(\d+) (\S+)$',s,re.M))
 def expand(v):return re.sub(r'\*(\d+)',lambda m:names.get(m[1],m[0]),v)
 out={}
 for sec in re.findall(r'\*D_NET .*?\*END',s,re.S):
  nm=expand(sec.split()[1]);res=[];adj=collections.defaultdict(set)
  for line in sec.split('*RES\n')[1].split('*END')[0].splitlines():
   _,a,b,v=line.split();a,b=expand(a),expand(b);res.append((a,b,float(v)));adj[a].add(b);adj[b].add(a)
  out[nm]=dict(res=res,adj=adj,Cwire_ff=float(sec.split()[2])*1000)
 return out

def connected(n,required):
 seen={required[0]};todo=list(seen)
 for a in todo:
  for b in n['adj'][a]:
   if b not in seen:seen.add(b);todo.append(b)
 assert all(x in seen for x in required),(required,seen)
 return dict(connected_terminals=required,resistor_edges=len(n['res']),Rsum_ohm=sum(v for _,_,v in n['res']),Cwire_ff=n['Cwire_ff'])
forms={}
for form in ['near','east']:
 o=r/f'joint_N1_mesh_{form}';n=nets(o/'route.spef');counts=list(map(int,re.findall(r'Number of violations = (\d+)',(o/'route.log').read_text())));assert counts[-1]==0
 analog=connected(n['ck_mesh'],['M0_0:Y','M0_1:Y','L_clk:A','mesh_contact']);feed=connected(n['n_N1'],['N1:Y','M0_0:A','M0_1:A']);arr={}
 for corner in ['TT','FF']:
  rows={line.split()[0]:list(map(float,line.split()[1:]))for line in(o/f'joint_N1_arr_{corner}.txt').read_text().splitlines()}
  assert all(all(abs(v)<1e8 for v in vals)for vals in rows.values())
  arr[corner]=dict(rows=rows,actual_driver_A_rise_skew_ps=abs(rows['M0_0/A'][0]-rows['M0_1/A'][0]),actual_driver_A_fall_skew_ps=abs(rows['M0_0/A'][3]-rows['M0_1/A'][3]))
 forms[form]=dict(drc=0,iterations=counts,actual_source_fanout=feed,actual_mesh_contacts=analog,measured_relative_source_readout=arr)
receipt=dict(verdict='ACTUAL_N1_COMPLETE_FANOUT_FIXED_MESH_COMPONENT_PASS',forms=forms,source=dict(cell='N1',master='BUFx24_ASAP7_75t_R',period_ps=833,input_transition_ps=40,xy_local_um=[316.224,270.0],complete_actual_fanout=['M0_0/A','M0_1/A'],omitted_source_loads=[]),scope='One actual N1 source fork to both actual BUFx24 inputs through physically routed source net, then actual two driver outputs to regular FIXED mesh and actual BUFx4f/A buffer input. All actual PG/hard-core obstacles retained. Two distinct nets across real driver cells; no parser multi-driver bypass.',phase_scope='Source-relative component only. TT/FF readout stops at actual driver A pins; timing through analog mesh not asserted by single-driver STA. Native macro108K/current G10/reset/66START/CA/wholefeed event unqualified.',handled_markers='Near DRC0 initial; east2 initial markers repaired normally byDRT to0 without input/rule waiver.',release_qualified=False)
(r/'joint_N1_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:dict(drc=v['drc'],TT_A_skew_ps=v['measured_relative_source_readout']['TT']['actual_driver_A_rise_skew_ps'],FF_A_skew_ps=v['measured_relative_source_readout']['FF']['actual_driver_A_rise_skew_ps'])for k,v in forms.items()},indent=2))
