import json,re,pathlib,gzip,collections,itertools
# Reuse the source-pinned native parser and interpolation, running in the fleet snapshot.
exec(compile(open('electrical_model.py').read(),'electrical_model.py','exec'))
def tables(b):
 out={}
 for k in ['cell_rise','cell_fall','rise_transition','fall_transition']:
  a=list(blocks(b,k))
  if a:out[k]={'x':vec(a[0][1],'index_1'),'y':vec(a[0][1],'index_2'),'v':vec(a[0][1],'values')}
 return out
def valrange(s,key):
 r=re.search(key+r': ([\d.]+)(?:-([\d.]+))?',s);a=float(r[1]);return [a,float(r[2]) if r[2] else a]
def slews(s,pin):
 r=re.search(re.escape(pin)+r' \^ ([\d.]+):([\d.]+) v ([\d.]+):([\d.]+)',s)
 return {'rise':[float(r[1]),float(r[2])],'fall':[float(r[3]),float(r[4])]}
def caprange(pb):
 vals=[scalar(pb,k) for k in ['capacitance','rise_capacitance','fall_capacitance']];vals=[x for x in vals if x is not None];return [min(vals),max(vals)]
def evaluate(arcs,xs,ys):
 values=collections.defaultdict(list);unsupported=[]
 for arc in arcs:
  for k,t in arc['tables'].items():
   for x,y in itertools.product(xs,ys):
    v=interp(t,x,y)
    if v is None:unsupported.append([arc['related_pin'],k,x,y])
    else:values[k].append(v)
 return {'range_ps':{k:[min(v),max(v)] for k,v in values.items()},'unsupported':unsupported}
native={}
for co in ['TT','FF']:
 native[co]={}
 for f in pathlib.Path('input/native_libs').glob('*'+co+'*'):
  s=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
  for n,b in blocks(s,'cell'):
   if n not in ['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R','INVx6_ASAP7_75t_R','NAND2xp33_ASAP7_75t_R','NAND2x2_ASAP7_75t_R']:continue
   ps=dict(blocks(b,'pin'));out=ps.get('QN',ps.get('Y'));arcs=[]
   for _,t in blocks(out,'timing'):
    rp=re.search(r'related_pin\s*:\s*"([^"]+)"',t)
    if not rp or ('QN' in ps and rp[1]!='CLK'):continue
    tb=tables(t)
    if tb:arcs.append({'related_pin':rp[1],'tables':tb})
   native[co][n]={'caps':{pn:caprange(pb) for pn,pb in ps.items() if scalar(pb,'capacitance') is not None},'arcs':arcs}
result={}
for co in ['TT','FF']:
 text=pathlib.Path('electrical_model/source_probe_'+co+'.log').read_text();src={}
 for mm in re.finditer(r'^SOURCE ([^\n]+)\n(.*?)(?=^SOURCE |^CONE |\Z)',text,re.M|re.S):
  pn,t=mm[1],mm[2];src[pn]={'pin':pn,'total_ff':valrange(t,'Total capacitance'),'wire_ff':valrange(t,'Wire capacitance'),'qn_slew_ps':slews(t,pn),'clock_slew_ps':slews(t,pn.rsplit('/',1)[0]+'/CLK')}
 results=[]
 # Boundary FF loading: actual original source-wire capacitance remains frozen.
 for b in boundary:
  z=b['upstream_drivers'][0];pn=z['cell']+'/'+z['pin'];r=src[pn];master=z['master'];old=native[co]['INVx1_ASAP7_75t_R']['caps']['A'];new=native[co]['INVx6_ASAP7_75t_R']['caps']['A']
  loads=[r['total_ff'][i]-old[i]+new[i] for i in range(2)];ff=native[co][master]['arcs'];xs=r['clock_slew_ps']['rise'];e=evaluate(ff,xs,loads)
  olde=evaluate(ff,xs,r['total_ff']);out={'source':r,'source_master':master,'new_total_ff':loads,'old_ff':olde,'new_ff':e}
  if not e['unsupported']:
   inp=[min(e['range_ps']['rise_transition'][0],e['range_ps']['fall_transition'][0]),max(e['range_ps']['rise_transition'][1],e['range_ps']['fall_transition'][1])]
   out['new_INV6_at_worst_measured114p8_ff']=evaluate(native[co]['INVx6_ASAP7_75t_R']['arcs'],inp,[114.8])
  results.append(out)
 cones_out={}
 for mm in re.finditer(r'^CONE (\d+)\n(.*?)(?=^CONE |^GATE_INPUT |\Z)',text,re.M|re.S):
  cn,t=mm[1],mm[2];c=cones[int(cn)];d=next(z for z in c['native_pins'] if z['direction']=='output');oldmaster=d['master'];newmaster='INVx6_ASAP7_75t_R' if oldmaster.startswith('INV') else 'NAND2x2_ASAP7_75t_R';load=valrange(t,'Total capacitance');changes=[]
  old_inputs=[];new_inputs=[]
  for u in c['drivers_upstream']:
   ip=u['pin'];pn=d['cell']+'/'+ip;old_slew=slews(text,pn);old_inputs.extend(v for vs in old_slew.values() for v in vs)
   for z in u['drivers']:
    qp=z['cell']+'/'+z['pin'];r=src[qp];ca=native[co][oldmaster]['caps'][ip];cb=native[co][newmaster]['caps'][ip];nl=[r['total_ff'][i]-ca[i]+cb[i] for i in range(2)];ff=native[co][z['master']]['arcs'];a=evaluate(ff,r['clock_slew_ps']['rise'],r['total_ff']);b=evaluate(ff,r['clock_slew_ps']['rise'],nl)
    changes.append({'pin':ip,'source':r,'new_total_ff':nl,'old_ff':a,'new_ff':b})
    if not b['unsupported']:
     for edge in ['rise','fall']:
      # Preserve measured original source-to-input slew increment, conditional on unchanged placement RC.
      for i in range(2):new_inputs.append(b['range_ps'][edge+'_transition'][i]+old_slew[edge][i]-r['qn_slew_ps'][edge][i])
  a=evaluate(native[co][oldmaster]['arcs'],[min(old_inputs),max(old_inputs)],load);b=evaluate(native[co][newmaster]['arcs'],[min(new_inputs),max(new_inputs)],load) if new_inputs else None
  slacks={}
  for path in re.split(r'(?=Startpoint:)',t):
   mm2=re.search(r'Path Type: (min|max)',path);ss=re.search(r'(-?[\d.]+)\s+slack \(',path)
   if mm2 and ss:slacks.setdefault(mm2[1],[]).append(float(ss[1]))
  cones_out[cn]={'old_master':oldmaster,'candidate':newmaster,'actual_load_ff':load,'actual_input_slew_ps':[min(old_inputs),max(old_inputs)],'conditional_new_input_slew_ps':[min(new_inputs),max(new_inputs)] if new_inputs else None,'sources':changes,'old_gate':a,'new_gate':b,'existing_native_slack_minimum_ps':{k:min(v) for k,v in slacks.items()}}
 result[co]={'boundary_sources':results,'changed_cones':cones_out}
json.dump(result,open('electrical_model/source_bound.json','w'),indent=2)
print('BOUND_OK',len(result['TT']['boundary_sources']),len(result['FF']['boundary_sources']))
