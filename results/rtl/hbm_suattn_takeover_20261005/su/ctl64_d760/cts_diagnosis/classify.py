import pathlib,re,json,collections,hashlib,sys
root=pathlib.Path(sys.argv[1]);phase=sys.argv[2] if len(sys.argv)>2 else 'before_repair';out={}
for corner,delay in [('BC','min'),('WC','max'),('WC','min'),('BC','max')]:
 p=root/f'{phase}_{corner}_{delay}.rpt'
 groups={};total=0
 for s in re.split(r'(?=^Startpoint:)',p.read_text(),flags=re.M):
  a=re.search(r'^Startpoint: (.*)',s,re.M);b=re.search(r'^Endpoint: (.*)',s,re.M);v=re.search(r'([-\d.]+)\s+slack \(VIOLATED\)',s)
  if not(a and b and v):continue
  ep=b[1];slack=float(v[1]);total+=1
  cls=re.sub(r'\[\d+\]','[]',ep.replace('\\',''))
  clk=[float(m[1]) for m in re.finditer(r'^\s*[-\d.]+\s+([-\d.]+)\s+.*?/CLK \(',s,re.M)]
  vals={}
  for label in ['clock uncertainty','clock reconvergence pessimism','library hold time','library setup time','data arrival time','data required time']:
   m=re.search(r'^\s*([-\d.]+)(?:\s+([-\d.]+))?\s+'+re.escape(label)+r'\s*$',s,re.M)
   if m:vals[label]=float(m[1])
  row={'startpoint':a[1],'endpoint':ep,'slack_ps':slack,'launch_clock_insertion_ps':clk[0] if len(clk)>0 else None,'capture_clock_insertion_ps':clk[1] if len(clk)>1 else None,'path_terms_ps':vals}
  g=groups.setdefault(cls,{'count':0,'worst':row});g['count']+=1
  if slack<g['worst']['slack_ps']:g['worst']=row
 out[f'{corner}_{delay}']={'path_count':total,'all_endpoint_classes':groups,'report_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(root/(phase+'_classes.json')).write_text(json.dumps(out,indent=2)+'\n')
for k,d in out.items():
 print(k,d['path_count'],len(d['all_endpoint_classes']))
 print(json.dumps(sorted(((c,v['count'],v['worst']['slack_ps']) for c,v in d['all_endpoint_classes'].items()),key=lambda r:-r[1])[:20]))
