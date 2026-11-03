from pathlib import Path
import odb,json,hashlib,re,gzip
r=Path('/case');k=Path('/work');p=k/'run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base/3_place.odb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(p)=='9ba70335e4f85dc5bd467e67629ab9a1db18143f8c319ea86656e531d3f9586f';db=odb.read_db(odb.dbDatabase.create(),str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();box=lambda q:[q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u];d={'saved_ODB_sha256':sha(p),'outline':box(b.getDieArea()),'ports':{},'sequential':{},'no_STA_solver_CTS':True}
for pt in b.getBTerms():
 n=pt.getNet();groups=[]
 for bp in pt.getBPins():groups.append([{'layer':z.getTechLayer().getName(),'box':box(z)} for z in bp.getBoxes()])
 d['ports'][pt.getName()]={'net':n.getName() if n else None,'direction':str(pt.getIoType()),'role':str(pt.getSigType()),'BPin_groups':groups}
for inst in b.getInsts():
 terms=inst.getITerms();clocks=[t for t in terms if str(t.getSigType())=='CLOCK' or t.getMTerm().getName() in ('CLK','CK','CP')]
 if not clocks:continue
 row={'master':inst.getMaster().getName(),'box':box(inst.getBBox()),'pins':{}}
 for t in terms:
  if str(t.getSigType()) in ('POWER','GROUND'):continue
  xy=t.getAvgXY();assert len(xy)==3 and xy[0],(inst.getName(),t.getMTerm().getName(),xy);n=t.getNet();row['pins'][t.getMTerm().getName()]={'xy':[xy[1]/u,xy[2]/u],'net':n.getName() if n else None,'direction':str(t.getIoType()),'role':str(t.getSigType())}
 d['sequential'][inst.getName()]=row
assert len(d['sequential'])==8994;(r/'CURRENT_ODB_STATIC.json.gz').write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode()))
# Parse exact current loaded Liberty source, not an older clock model.
def block(s,start):
 pos=s.index('{',start);depth=1;i=pos+1;quote=False
 while depth:
  c=s[i]
  if c=='"' and (i==0 or s[i-1]!='\\'):quote=not quote
  if not quote:
   if c=='{':depth+=1
   elif c=='}':depth-=1
  i+=1
 return s[pos+1:i-1]
counts=json.loads((r/'CLOCK_MASTER_COUNTS.json').read_text());caps={}
for name in json.loads((r/'LIB_PATHS.json').read_text()):
 p=Path(name);s=gzip.decompress(p.read_bytes()).decode() if name.endswith('.gz') else p.read_text();s=re.sub(r'/\*.*?\*/','',s,flags=re.S);s=re.sub(r'//[^\n]*','',s);unit=re.search(r'capacitive_load_unit\s*\(\s*([\d.eE+-]+)\s*,\s*(\w+)\s*\)',s);assert unit;factor=float(unit[1])*{'ff':1,'pf':1000,'nf':1e6}[unit[2].lower()];rows={}
 for master in counts['PLACE']:
  m=re.search(r'\bcell\s*\(\s*"?'+re.escape(master)+r'"?\s*\)',s);assert m,master;cell=block(s,m.end());pin=re.search(r'\bpin\s*\(\s*"?CLK"?\s*\)',cell);assert pin;body=block(cell,pin.end());v={}
  for key in ['capacitance','rise_capacitance','fall_capacitance']:
   x=re.search(r'(?m)^\s*'+key+r'\s*:\s*([\d.eE+-]+)\s*;',body);v[key+'_fF']=float(x[1])*factor if x else None
  assert v['capacitance_fF'] is not None;rows[master]=v
 total={phase:sum(n*rows[m]['capacitance_fF'] for m,n in c.items()) for phase,c in counts.items()};caps[name]={'sha256':sha(p),'unit':unit[0],'clock_pin':'CLK','masters':rows,'total_clock_pin_cap_fF':total,'PLACE_minus_SYNTH_fF':total['PLACE']-total['SYNTH']}
(r/'CURRENT_CLOCK_CAPS.json').write_text(json.dumps(caps,indent=2)+'\n');print('STATIC_CURRENT_ODB8994_AND_CURRENT_TT_FF_CLOCK_CAPS_PASS')
