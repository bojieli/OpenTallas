import sys,json,collections,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import textbook_lint as T
p=Path(sys.argv[2]);g,top=T.flatten(T.parse_verilog(p.read_text()),'qfd_native59_svc');a=T.build(g,None)
clocks=set()
for i,(typ,name,pins) in enumerate(g.cells):
 if a['kind'][i]=='ff':
  for pn in T.SEQ_CLK_PINS:clocks.update(pins.get(pn,[]))
records=[];off=[]
markers=['u_kvn','g_ctl_pub','g_x3_slot_pub','rst_cp_x3']
for net,driver in a['driver'].items():
 i,pin=driver
 if net in clocks or net<=3 or(i>=0 and a['kind'][i] in ['buf','tie']):continue
 n,ff,ex=T.bufinv_fanout(g,a,net,clocks)
 label=T.net_label(g,a,net)
 if any(k in label for k in markers):records.append({'net':label,'loads':n,'ffloads':ff})
 if n<=32:continue
 todo=collections.deque([net]);seen=set();orig=[]
 while todo:
  x=todo.popleft()
  if x in seen:continue
  seen.add(x);d=a['driver'].get(x)
  if d is None:continue
  j,pn=d
  if j<0:orig.append('PORT '+pn);continue
  ty,na,ps=g.cells[j]
  if a['kind'][j] in ['ff','macro']:orig.append(na+'/'+pn);continue
  for q,bs in ps.items():
   if a['pin_dir'][j].get(q)=='in':todo.extend(bs)
 sinks=[];fw=[net];fseen=set()
 while fw:
  x=fw.pop()
  if x in fseen:continue
  fseen.add(x)
  for ci,pn,_ in a['loads'].get(x,[]):
   if a['kind'][ci]=='buf':fw.extend(T._out_nets(g,a,ci))
   elif any(k in g.cells[ci][1] for k in markers):sinks.append(g.cells[ci][1]+'/'+pn)
 if sinks or any(any(k in q for k in markers) for q in orig):off.append({'net':label,'loads':n,'origins':sorted(set(orig)),'direct_marker_sinks':sorted(set(sinks))})
records.sort(key=lambda r:-r['loads'])
out={'schema':'n59.kvn.target.all_origins.v1','native_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'all_marker_drivers':records,'offending_drivers_with_marker_origin_or_direct_sink':off,'limitations':['Topology only; no nativecell functional model or physical coordinates','Reverse traces stop only at FF/macro/ports, with no origin truncation']}
Path(sys.argv[3]).write_text(json.dumps(out,indent=2)+'\n');print('TARGET_AUDIT',len(records),'max',records[:2],'offenders',len(off))
