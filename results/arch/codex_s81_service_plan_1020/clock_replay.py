import sys,json,re,shutil,os
from pathlib import Path
orig=Path(sys.argv[1]);out=Path(sys.argv[2]);src=orig.parent/'src'
sys.path[:0]=[str(src/'tools'),str(src/'tools/s81_dv'),str(Path(__file__).parent)]
import die_port_bind as DPB
from clock_roles import contract_clock_nets
meta=json.load(open(orig/'case.json'));T=json.load(open(src/meta['bind_table']))
net,tin,tout,insts=DPB.parse_die(Path(meta['bind_dir'])/'die.v','dv_die');insts=[i for i in insts if i[0]!='__assign__']
bits={nm:{p:DPB.expr_bits(e,net) for p,e in cm.items()} for mst,nm,_,cm in insts}
m2m={m.get('module'):k for k,m in T['masters'].items() if m.get('module')}
known={n for n in set(tin)|set(tout) if n.startswith('ck_')};directions={};libpaths={}
for mst,nm,_,cm in insts:
 lp=orig/'views'/f'rv_{nm[2:]}.lib'
 if not lp.exists():lp=orig/'views/sta'/f'{mst}_tt.lib'
 if lp.exists():
  text=lp.read_text();directions[mst]={m[0]:m[1] for m in re.findall(r'(?:pin|bus)\s*\(\s*"?([^"\s()]+)"?\s*\)\s*\{[^{}]*?direction\s*:\s*(input|output)',text)};libpaths[nm]=lp
 tm=T['masters'].get(m2m.get(mst,''),{})
 ps=[tm.get('clk')]+[c['port'] for c in tm.get('clk_peer',[])]
 if mst.startswith(('dsfd_dvrlyh_','dsfd_dvrly_')):ps=['ck','ck_o']
 elif mst.startswith('dsfd_dvland_'):ps=['ck_f','ck']
 elif nm.startswith('fwd_'):ps=['CLK','GCLK','A','Y']
 for p in ps:
  known|={n for n,_ in bits[nm].get(p,[]) if n not in ('CONST','Z','UNDECL')}
clocknets,sinks=contract_clock_nets(insts,bits,T['masters'],m2m,directions,known)
# Actual Liberty source proof: all declared source clock outputs must have
# immutable combinational clock arcs, not sequential data-launch arcs.
proof=[]
sink_nets={n for inst,cp in sinks for n,_ in bits[inst][cp] if n not in ('CONST','Z','UNDECL')}
def group(text,port):
 m=re.search(r'\b(?:pin|bus)\s*\(\s*"?'+re.escape(port)+r'"?\s*\)\s*\{',text)
 if not m:raise ValueError('missing Liberty pin '+port)
 depth=1;i=m.end()
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return m.start(),i,text[m.start():i]
for mst,nm,_,cm in insts:
 tm=T['masters'].get(m2m.get(mst,''),{})
 for row in tm.get('ports',{}).values():
  if not isinstance(row,dict) or not row.get('ck'):continue
  cp=row['ck']
  if not sink_nets & {n for n,_ in bits[nm][cp]}:continue
  lp=libpaths[nm];g=group(lp.read_text(),cp)[2]
  if 'rising_edge' in g or 'falling_edge' in g or not re.search(r'related_pin\s*:\s*"'+re.escape(tm['clk'])+'"',g) or not re.search(r'timing_sense\s*:\s*(positive_unate|negative_unate)',g):
   raise ValueError(f'Actual Liberty is not a source clock forwarding arc: {nm}.{cp} {lp}')
  proof.append(f'{nm}.{cp} -> {lp}')
out.mkdir(parents=True,exist_ok=False)
shutil.copytree(orig/'views',out/'views');shutil.copytree(orig/'dcc',out/'dcc')
(out/'out').mkdir();(out/'sta').mkdir();os.link(orig/'out/grt.odb',out/'out/grt.odb')
for n in ('case.json','pairs.json','landing.sdc','classify.py','die.v'):shutil.copy2(orig/n,out/n)
changed=[];probes=[]
for nm,cp in sinks:
 lp=out/'views'/f'rv_{nm[2:]}.lib'
 if not lp.exists():continue # native closed Liberty immutable
 text=lp.read_text();i,j,g=group(text,cp)
 header=g[:g.index('{')+1]
 if 'bus_type' in g:header+=' bus_type : '+re.search(r'bus_type\s*:\s*([^ ;]+)',g)[1]+' ;'
 replacement=header+' direction : input ; clock : true ; capacitance : 1.0 ; }'
 lp.write_text(text[:i]+replacement+text[j:]);changed.append(nm+'.'+cp)
 width=len(bits[nm][cp]);probes += [f'{nm}/{cp}[{k}]' for k in range(width)] if width>1 else [f'{nm}/{cp}']
for corner in ('tt','ff'):
 text=(orig/f'sta_{corner}.tcl').read_text()
 probe='\nset role_miss 0\n'
 for pin in probes:
  probe+=f'set role_p [get_pins -quiet {{{pin}}}]; if {{![llength $role_p] || ![llength [get_property $role_p clocks]]}} {{ puts "CLOCK_ROLE_MISSING {pin}"; incr role_miss }}\n'
 probe+='puts "CLOCK_ROLE_PROBE missing=$role_miss"\nif {$role_miss} {error "unreached contract input clocks"}\n'
 text=text.replace('puts "OT_STA_WNS_SETUP"',probe+'puts "OT_STA_WNS_SETUP"',1)
 (out/f'sta_{corner}.tcl').write_text(text)
json.dump(dict(scope='STA_MODEL_DIAGNOSTIC_ONLY',original=str(orig),changed=changed,source_liberty_proof=proof,probed_inputs=len(probes)),open(out/'clock_role_patch.json','w'),indent=2)
print('CLOCK_ROLE_PATCH',len(changed),'inputs',len(probes),'sources',len(proof))
