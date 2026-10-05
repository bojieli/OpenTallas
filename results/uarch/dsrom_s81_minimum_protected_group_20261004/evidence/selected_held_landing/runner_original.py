import sys,json,subprocess,re,copy
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/dsrom-s81-minimum-protected-group-20261004/tools')
from dsrom_s81_leaf_fanout_construct import construct,verilog,digest
src=Path('/tmp/dsrom-s81-minimum-w6-leaves-20261004-r3');out=Path('/tmp/dsrom-s81-minimum-w6-held-landing-20261004-r1');out.mkdir()
results={}
for leaf in ('encode','decode','equal83','merge256'):
 j=json.loads((src/leaf/'mapped.json').read_text());m=j['modules']['leaf'];cells=m['cells'];nextbit=max(b for v in cells.values() for bs in v['connections'].values() for b in bs if isinstance(b,int))+1
 def cell(typ,ports):
  name=f'held_{len(cells)}';cells[name]={'type':typ,'parameters':{},'attributes':{'keep':'1'},'port_directions':{p:'output' if p in ('Y','QN') else 'input' for p in ports},'connections':{p:[b] for p,b in ports.items()}}
 def node():
  global nextbit
  b=nextbit;nextbit+=1;return b
 en=node();enb=node();m['ports']['capture_en']={'direction':'input','bits':[en]};cell('INVx1_ASAP7_75t_R',{'A':en,'Y':enb})
 inputs=set(m['ports']['din']['bits']);n=0
 for name,v in list(cells.items()):
  if 'DFFHQ' in v['type'] and v['connections']['D'][0] not in inputs:
   d=v['connections']['D'][0];q=node();fb1=node();fb2=node();a=node();b=node();mux=node()
   cell('INVx1_ASAP7_75t_R',{'A':v['connections']['QN'][0],'Y':q})
   cell('BUFx4_ASAP7_75t_R',{'A':q,'Y':fb1});cell('BUFx4_ASAP7_75t_R',{'A':fb1,'Y':fb2})
   cell('NAND2x1_ASAP7_75t_R',{'A':d,'B':en,'Y':a});cell('NAND2x1_ASAP7_75t_R',{'A':fb2,'B':enb,'Y':b});cell('NAND2x1_ASAP7_75t_R',{'A':a,'B':b,'Y':mux});v['connections']['D']=[mux];n+=1
 j,proof=construct(j,capture_buffer=True)
 work=out/leaf;work.mkdir();v=work/'held.v';s=verilog(j).replace('module leaf(clk,din,q);','module leaf(clk,din,q,capture_en);').replace('input clk;','input clk;\ninput capture_en;');v.write_text(s)
 (work/'held.json').write_text(json.dumps(j,sort_keys=True)+'\n');timing={}
 for c in ('ss','ff'):
  t=work/(c+'.tcl');t.write_text(re.sub(r'read_verilog [^\n]+',f'read_verilog {v}',(src/leaf/(c+'.tcl')).read_text()).replace('set_input_transition 20 [get_ports din*]','set_input_transition 20 [get_ports {din* capture_en}]'))
  log=work/(c+'.log')
  with log.open('x') as f:r=subprocess.run(['sta','-exit',str(t)],stdout=f,stderr=subprocess.STDOUT)
  tx=log.read_text();assert not re.search(r'^Error:',tx,re.M)
  sl=[float(x) for x in re.findall(r'([-\d.]+)\s+slack',tx)];assert len(sl)==2
  timing[c]={'setup_slack_ps':sl[0],'hold_slack_ps':sl[1],'electrical_violations':re.findall(r'^.*\(VIOLATED\).*$',tx.split('max slew',1)[-1],re.M),'log_sha256':digest(log)}
 counts={}
 for c in j['modules']['leaf']['cells'].values():counts[c['type']]=counts.get(c['type'],0)+1
 results[leaf]={'retained_map_sha256':digest(src/leaf/'mapped.json'),'held_netlist_sha256':digest(v),'held_output_bits':n,'construction':proof,'cell_counts':counts,'timing':timing}
r={'schema':'dsrom.s81.native_leaf.held_landing.v1','target_GHz':.9,'wire_CTS_included':False,'results':results,'runner_sha256':digest(__file__)};(out/'record.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r,indent=2))
