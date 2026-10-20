#!/usr/bin/env python3
"""Private mapped-source SHLK control prototype. Never clones unreset state.

Every replica is an actual same-master cell with identical input pins. A chunk
is retargeted through an independently replicated original BUF/INV path; BUF
and INV are transparent in the census. No new sequential edge or tie value is
introduced. Reset FF replicas are conditional on a common assertion and remain
explicitly reported as needing first-observation authority. This is not an
RTL-to-native qualification or a production closure helper.

LIMITATION: concat macro pins remain aggregate; rd_out directions are unknown.
The census covers scalar primitive sinks only and cannot prove full closure.
"""
import argparse, collections, hashlib, json, pathlib, re
CELL=re.compile(r'^\s+(\w+)\s+(\\?\S+)\s*\(\s*\n(.*?)^\s*\);',re.M|re.S)
OUT={'Y','Q','QN','Z','H','L'}
CLOCK={'CLK','CK'}
def parse(s):
 cells={}
 for m in CELL.finditer(s):
  typ,inst,body=m.groups(); pins=dict((k,v.strip()) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',body))
  cells[inst]={'master':typ,'pins':pins}
 return cells

def census(cells):
 sinks=collections.defaultdict(list);drivers={}
 for i,c in cells.items():
  for p,n in c['pins'].items():
   if p in OUT:drivers[n]=(i,p)
   elif p not in CLOCK|{'VDD','VSS'}:sinks[n].append((i,p))
 def walk(n,path=(),seen=frozenset()):
  if n in seen:raise ValueError('transparent cycle '+n)
  found=[]
  for i,p in sinks[n]:
   c=cells[i]
   if c['master'].startswith(('BUF','INV')):
    op=[q for q in c['pins'] if q in OUT]
    if len(op)!=1:raise ValueError('nonunary transparent cell '+i)
    found+=walk(c['pins'][op[0]],path+((i,p,op[0]),),seen|{n})
   else:found.append((i,p,path))
  return found
 terminals={n:walk(n) for n in drivers}
 return drivers,sinks,terminals

def main():
 ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('out');ap.add_argument('--max-loads',type=int,default=32);ap.add_argument('--reset-ff',action='store_true');a=ap.parse_args()
 src=pathlib.Path(a.source);s=src.read_text();cells=parse(s);original={i:json.loads(json.dumps(c)) for i,c in cells.items()};out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
 replicas=[];retargets=[];wires=[];seq=0
 def clone(inst,op,inputs=None):
  nonlocal seq
  c=cells[inst];seq+=1;name=f'ot_shlk_rep_{seq:06d}';net=f'ot_shlk_repnet_{seq:06d}';p=dict(c['pins']);p[op]=net
  if inputs:p.update(inputs)
  cells[name]={'master':c['master'],'pins':p};wires.append(net);replicas.append({'replica':name,'source':inst,'master':c['master'],'output_pin':op,'source_output_net':c['pins'][op],'output_net':net,'input_pins':{k:v for k,v in p.items() if k!=op},'reset_ff':c['master'].startswith('DFF')});return name,net
 blocked=[]
 for iteration in range(64):
  drivers,sinks,term=census(cells);changes=0;blocked=[]
  for net,(inst,op) in list(drivers.items()):
   c=cells[inst];typ=c['master'];ts=term[net]
   if len(ts)<=a.max_loads or typ.startswith(('BUF','INV')):continue
   allowed=not typ.startswith(('DFF','ot_sram')) or (a.reset_ff and typ.startswith('DFFASR'))
   if not allowed:
    blocked.append({'net':net,'instance':inst,'master':typ,'terminal_loads':len(ts),'reason':'unreset-state/opaque-master authority not established'});continue
   for offset in range(a.max_loads,len(ts),a.max_loads):
    _,newnet=clone(inst,op)
    path_cache={}
    for ti,tp,path in ts[offset:offset+a.max_loads]:
     local=newnet
     for bi,bip,bop in path:
      key=(bi,local)
      if key not in path_cache:path_cache[key]=clone(bi,bop,{bip:local})[1]
      local=path_cache[key]
     old=cells[ti]['pins'][tp];cells[ti]['pins'][tp]=local;retargets.append({'instance':ti,'pin':tp,'before':old,'after':local,'root':inst})
   changes+=1
  if not changes:break
 else:raise RuntimeError('replication did not converge')
 # Remove dead transparent branches so an unused branch does not inflate input
 # loading. Rooted cell logic, state, and every original nontransparent cell stay.
 for _ in range(64):
  _,sinks,_=census(cells);dead=[i for i,c in cells.items() if c['master'].startswith(('BUF','INV')) and all(not sinks[n] and not re.match(r'\\?(t_host|s_hw_[we]|jd_o|pw_o|pl_o|tw_o|cf_o|fault|ks_o|t_kd|s_j|vo_s|rn_o)(\[|$)',n) for p,n in c['pins'].items() if p in OUT)]
  if not dead:break
  for i in dead:del cells[i]
 drivers,sinks,term=census(cells)
 # Structural clone relation is checked before output, including every input
 # retarget: substitute ancestor nets until the old network is recovered.
 ancestor={r['output_net']:r['source_output_net'] for r in replicas}
 redirects={r['after']:r['before'] for r in retargets}
 def root(n):
  seen=set()
  while n in ancestor:
   if n in seen:raise ValueError('ancestor cycle')
   seen.add(n);n=ancestor[n]
  return n
 clone_mismatches=[]
 source_instance={r['replica']:r['source'] for r in replicas}
 def original_instance(i):
  seen=set()
  while i in source_instance:
   if i in seen:raise ValueError('instance ancestor cycle')
   seen.add(i);i=source_instance[i]
  return i
 for inst,now in cells.items():
  oi=original_instance(inst);base=original[oi]
  if now['master']!=base['master']:clone_mismatches.append([inst,'master'])
  if set(now['pins'])!=set(base['pins']):clone_mismatches.append([inst,'pinset'])
  for pin,value in now['pins'].items():
   if root(value)!=base['pins'][pin]:clone_mismatches.append([inst,pin,value,base['pins'][pin]])
 if clone_mismatches:raise ValueError('quotient input changed '+str(clone_mismatches[:3]))
 header=s[:CELL.search(s).start()];tail=s[s.rfind('endmodule'):]
 def emit(i,c):
  return '  (* keep = 1, dont_touch = 1 *) '+c['master']+' '+i+' (\n'+',\n'.join('    .'+p+'('+n+' )' for p,n in c['pins'].items())+'\n  );\n'
 result=header+'\n'+''.join('  wire '+n+';\n' for n in wires)+''.join(emit(i,c) for i,c in cells.items())+tail
 (out/'successor.v').write_text(result)
 remaining=[dict(net=n,instance=i,master=cells[i]['master'],terminal_loads=len(term[n]))for n,(i,p) in drivers.items() if len(term[n])>a.max_loads]
 raw=[dict(net=n,loads=len(x))for n,x in sinks.items() if n not in drivers and len(x)>a.max_loads and not n.startswith(('1\'',"1'h"))]
 report={'scope':'PRIVATE_SCALAR_PRIMITIVE_SOURCE_PROTOTYPE_NOT_CLOSED','source_sha256':hashlib.sha256(s.encode()).hexdigest(),'successor_sha256':hashlib.sha256(result.encode()).hexdigest(),'max_loads':a.max_loads,'source_cells':len(original),'successor_cells':len(cells),'added_cells_net':len(cells)-len(original),'replicas':replicas,'retargets':retargets,'remaining':remaining,'unowned_or_raw_input_loads':raw,'clone_structural_input_mismatches':clone_mismatches,'reset_ff_requires_common_assertion_and_first_observation_authority':a.reset_ff,'whole_closure':False,'macro_pin_census_complete':False,'FF_added':sum(r['reset_ff'] and r['replica'] in cells for r in replicas),'PG_terms_added':2*(len(cells)-len(original)),'added_data_edges':0}
 (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('replicas','retargets','remaining')},indent=2));print('REMAINING',len(remaining));print('TOP',sorted(remaining,key=lambda r:-r['terminal_loads'])[:15])
if __name__=='__main__':main()
